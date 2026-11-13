"""Read-only static KN5/package verifier. Does not run Assetto Corsa.

Parses the serialized file, validates texture payloads and triangles, compares
physical meshes with a baseline, and checks the imported road-clear corridor.
This is not an engine/shader/FPS test.
"""
from pathlib import Path
import sys,json,struct,hashlib,io,argparse,configparser,math,collections
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parents[1]/'work/python_deps'))
import numpy as np
from PIL import Image
import shapely
from shapely.geometry import LineString

class Reader:
    def __init__(self,path):self.path=path;self.file=path.open('rb');self.size=path.stat().st_size
    def read(self,n):
        b=self.file.read(n)
        if len(b)!=n:raise ValueError('Unexpected end of KN5')
        return b
    def unpack(self,fmt):return struct.unpack('<'+fmt,self.read(struct.calcsize('<'+fmt)))
    def u32(self):return self.unpack('I')[0]
    def string(self):
        n=self.u32()
        if n>1048576:raise ValueError('Invalid string length')
        return self.read(n).decode('utf-8')
    def skip(self,n):
        if n<0 or self.file.tell()+n>self.size:raise ValueError('Invalid byte range')
        self.file.seek(n,1)

def support(point,triangles):
    if not len(triangles):return None
    xyz=np.asarray(point);lo=triangles[:,:,[0,2]].min(axis=1);hi=triangles[:,:,[0,2]].max(axis=1)
    mask=((lo<=xyz[[0,2]]+.001)&(hi>=xyz[[0,2]]-.001)).all(axis=1);tri=triangles[mask]
    if not len(tri):return None
    a,b,c=tri[:,0],tri[:,1],tri[:,2];den=(b[:,2]-c[:,2])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,2]-c[:,2]);good=abs(den)>1e-10;den=np.where(good,den,1)
    u=((b[:,2]-c[:,2])*(xyz[0]-c[:,0])+(c[:,0]-b[:,0])*(xyz[2]-c[:,2]))/den
    v=((c[:,2]-a[:,2])*(xyz[0]-c[:,0])+(a[:,0]-c[:,0])*(xyz[2]-c[:,2]))/den;w=1-u-v;good&=(u>=-1e-5)&(v>=-1e-5)&(w>=-1e-5)
    heights=(a[:,1]*u+b[:,1]*v+c[:,1]*w)[good]
    if not len(heights):return None
    height=float(heights[np.argmin(abs(heights-xyz[1]))]);return {'surface_y_m':height,'clearance_m':float(xyz[1]-height)}

def scan(path,full=True,road_corridor=None,require_spawns=True,drive_corridor=None):
    reader=Reader(path);errors=[];textures={};materials=[];physical={};logical={};meshes=[];roads=[];pits=[];degenerate=0;blocked=0;gpu_bytes=0;source_triangles=0;duplicate_names=set();names=set();missing_emissive=[];nonzero_emissive=[];alpha_textures={};detail_blocked=0;detail_triangles=0
    try:
        if reader.read(6)!=b'sc6969':raise ValueError('Invalid KN5 signature')
        version=reader.u32()
        if version!=5:raise ValueError('This static-track verifier expects KN5 version 5')
        for i in range(reader.u32()):
            active=reader.u32();name=reader.string();n=reader.u32()
            if name in textures:errors.append('Duplicate texture '+name)
            payload=reader.read(n)
            if full:
                try:
                    with Image.open(io.BytesIO(payload)) as image:
                        dimensions=image.size;image.load()
                        if max(dimensions)>2048:errors.append('Texture exceeds 2048 pixel cap: '+name)
                        if 'A' in image.getbands():alpha_textures[name]=image.getchannel('A').getextrema()
                    if payload.startswith(b'DDS '):
                        h,w=struct.unpack_from('<II',payload,12);count=struct.unpack_from('<I',payload,28)[0];fourcc=payload[84:88]
                        if fourcc!=b'DXT1':errors.append('Unexpected DDS format '+name)
                        expected=0;ww,hh=w,h
                        for level in range(max(1,count)):
                            expected+=((ww+3)//4)*((hh+3)//4)*8;ww=max(1,ww//2);hh=max(1,hh//2)
                        if expected+128!=len(payload):errors.append('DDS mip byte length mismatch '+name)
                        if count!=int(math.log2(max(w,h)))+1:errors.append('DDS mip chain incomplete '+name)
                        gpu_bytes+=expected
                    else:gpu_bytes+=dimensions[0]*dimensions[1]*4
                except Exception as e:errors.append('Invalid texture '+name+': '+str(e))
            textures[name]={'bytes':n,'active':active}
        for i in range(reader.u32()):
            name=reader.string();shader=reader.string();reader.read(6);properties={}
            for p in range(reader.u32()):
                prop=reader.string();values=reader.unpack('10f');properties[prop]=values
                if not all(math.isfinite(x) for x in values):errors.append('Invalid material property '+name+'/'+prop)
            if 'ksEmissive' not in properties:missing_emissive.append(name)
            elif any(abs(v)>1e-8 for v in properties['ksEmissive']):nonzero_emissive.append(name)
            slots=[]
            for p in range(reader.u32()):
                sampler=reader.string();slot=reader.u32();target=reader.string();slots.append((sampler,slot,target))
                if target not in textures:errors.append('Missing material texture '+target)
            if full and shader=='ksPerPixelAT':
                diffuse=[t for sampler,slot,t in slots if sampler=='txDiffuse']
                if len(diffuse)!=1 or diffuse[0] not in alpha_textures:errors.append('Alpha-test material lacks RGBA texture: '+name)
                elif alpha_textures[diffuse[0]][0]>=alpha_textures[diffuse[0]][1]:errors.append('Alpha-test texture has no cutout variation: '+name)
            materials.append({'name':name,'shader':shader,'textures':slots})
        def node(parent,ancestor_active=True):
            nonlocal degenerate,blocked,source_triangles,detail_blocked,detail_triangles
            kind=reader.u32();name=reader.string();children=reader.u32();active=bool(reader.unpack('B')[0]) and ancestor_active
            if name in names:duplicate_names.add(name)
            names.add(name)
            matrix=parent
            if kind==1:
                local=np.asarray(reader.unpack('16f')).reshape(4,4,order='F');matrix=parent@local
                if not np.isfinite(matrix).all():errors.append('Nonfinite node matrix '+name)
                logical[name]={'matrix':matrix.flatten(order='F').tolist(),'active':active}
            elif kind==2:
                cast,visible,transparent=reader.unpack('3B');vertices=reader.u32();rawv=reader.read(vertices*44);indices=reader.u32();rawi=reader.read(indices*2);mat,layer=reader.unpack('2I');lodin,lodout,cx,cy,cz,radius=reader.unpack('6f');render=reader.unpack('B')[0]
                if not 0<vertices<=65535 or indices%3:errors.append('Invalid mesh count '+name)
                if mat>=len(materials):errors.append('Invalid material index '+name)
                attrs=np.frombuffer(rawv,dtype='<f4').reshape(-1,11);idx=np.frombuffer(rawi,dtype='<u2').reshape(-1,3)
                if not np.isfinite(attrs).all():errors.append('Nonfinite vertex attributes '+name)
                if len(idx) and int(idx.max())>=vertices:raise ValueError('Invalid triangle index '+name)
                xyz=attrs[:,:3].astype(np.float64);xyz=xyz@parent[:3,:3].T+parent[:3,3];tri=xyz[idx]
                cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);bad=int((np.linalg.norm(cross,axis=1)<2e-8).sum());degenerate+=bad
                if bad:errors.append(f'{bad} degenerate triangles: '+name)
                if not all(math.isfinite(v) for v in [lodin,lodout,cx,cy,cz,radius]) or lodin<0 or lodout<0 or radius<0:errors.append('Invalid LOD/bounds '+name)
                if len(xyz) and np.linalg.norm(xyz-[cx,cy,cz],axis=1).max()>radius+.03:errors.append('Mesh bounds exclude vertices '+name)
                if len(xyz) and np.abs(xyz).max()>100000:errors.append('Map-grid coordinates passed to game '+name)
                if name[:1].isdigit():
                    physical[name]=hashlib.sha256(rawv+rawi).hexdigest()
                    if name.startswith('1ROAD') and active:roads.append(tri)
                    if name.startswith('1PITLANE') and active:pits.append(tri)
                elif full and name.startswith(('CSDI_','NATIVE_VEG_')) and not name.startswith('CSDI_TERRAIN') and road_corridor is not None:
                    xy=tri[:,:,[0,2]]*np.array([1,-1]);blocked+=int(shapely.intersects(road_corridor,shapely.polygons(xy)).sum());source_triangles+=len(tri)
                elif full and name.startswith('ROAD_DETAIL_') and drive_corridor is not None:
                    xy=tri[:,:,[0,2]]*np.array([1,-1]);detail_blocked+=int(shapely.intersects(drive_corridor,shapely.polygons(xy)).sum());detail_triangles+=len(tri)
                meshes.append({'name':name,'vertices':vertices,'triangles':len(idx),'visible':bool(visible),'renderable':bool(render),'material':mat})
            else:raise ValueError('Unexpected node class '+str(kind))
            for k in range(children):node(matrix,active)
        node(np.eye(4))
        if reader.file.tell()!=reader.size:errors.append('Unparsed trailing data')
    finally:reader.file.close()
    if duplicate_names:errors.append('Duplicate node names: '+str(sorted(duplicate_names)[:5]))
    if blocked:errors.append(str(blocked)+' scenery triangles intersect protected road corridor')
    if detail_blocked:errors.append(str(detail_blocked)+' road-detail triangles intersect the drivable road/pit corridor')
    required={}
    for name in (['AC_PIT_0','AC_START_0','AC_HOTLAP_START_0'] if require_spawns else []):
        if name not in logical:errors.append('Missing required node '+name);continue
        transform=np.asarray(logical[name]['matrix']).reshape(4,4,order='F');triangles=pits if name.startswith('AC_PIT') else roads
        check=support(transform[:3,3],np.vstack(triangles) if triangles else np.empty((0,3,3)));required[name]={'matrix':logical[name]['matrix'],'surface_support':check}
        if check is None or not -.01<=check['clearance_m']<=.15:errors.append('Invalid spawn support '+name)
    return {'passed':not errors,'errors':errors,'file_bytes':path.stat().st_size,'kn5_sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),'version':version,'mesh_nodes':len(meshes),'triangles':sum(m['triangles'] for m in meshes),'degenerate_triangles':degenerate,'embedded_texture_count':len(textures),'material_count':len(materials),'shader_counts':dict(collections.Counter(m['shader'] for m in materials)),'material_audit':{'missing_explicit_emissive':missing_emissive,'nonzero_emissive':nonzero_emissive,'alpha_test_materials_checked':sum(m['shader']=='ksPerPixelAT' for m in materials) if full else 0},'texture_gpu_payload_bytes':gpu_bytes,'physical_mesh_hashes':physical,'logical_nodes':logical,'required_nodes':required,'scenery_triangles_checked':source_triangles,'scenery_triangles_in_protected_corridor':blocked,'road_detail_triangles_checked':detail_triangles,'road_detail_triangles_in_drivable_corridor':detail_blocked,'scope':'Static binary, image and geometry checks; actual engine driving/FPS untested'}

def main():
    p=argparse.ArgumentParser();p.add_argument('kn5',type=Path);p.add_argument('--baseline',type=Path);p.add_argument('--report',type=Path,required=True);p.add_argument('--models-ini',type=Path);a=p.parse_args()
    route=np.load(ROOT/'driving_test/route_geometry.npz')['center'];corridor=LineString(route[:,:2]).buffer(10.5,join_style=2);shapely.prepare(corridor)
    surfaces=np.load(ROOT/'driving_test/surfaces.npz');pit=shapely.union_all(shapely.polygons(surfaces['pit_vertices'][surfaces['pit_faces']][:,:,:2])).buffer(.1);drive_corridor=shapely.union_all([LineString(route[:,:2]).buffer(3.65,join_style=2),pit]);shapely.prepare(drive_corridor)
    result=scan(a.kn5,road_corridor=corridor,drive_corridor=drive_corridor)
    if a.baseline:
        baseline=scan(a.baseline,full=False);result['baseline_kn5_sha256']=baseline['kn5_sha256'];result['physical_meshes_compared']=len(baseline['physical_mesh_hashes']);result['physical_meshes_unchanged']=result['physical_mesh_hashes']==baseline['physical_mesh_hashes'];result['spawn_timing_nodes_unchanged']=result['logical_nodes']==baseline['logical_nodes']
        if not result['physical_meshes_unchanged'] or not result['spawn_timing_nodes_unchanged']:result['errors'].append('Baseline physics/spawn comparison failed')
    if a.models_ini:
        ini=configparser.ConfigParser();ini.read(a.models_ini,encoding='utf-8');models=[]
        for section in ini.sections():
            file=a.models_ini.parent/ini.get(section,'FILE')
            if file.resolve()==a.kn5.resolve():part={**result,'errors':list(result['errors'])}
            else:part=scan(file,road_corridor=corridor,require_spawns=False,drive_corridor=drive_corridor)
            models.append({'filename':file.name,**{k:v for k,v in part.items() if k not in ['physical_mesh_hashes','logical_nodes','required_nodes','models']}})
            if not part['passed']:result['errors'].extend([file.name+': '+e for e in part['errors']])
            if file.resolve()!=a.kn5.resolve() and part['physical_mesh_hashes']:result['errors'].append('Scenery file unexpectedly contains physical meshes: '+file.name)
        result['models']=models;result['model_files']=len(models);result['total_model_bytes']=sum(m['file_bytes'] for m in models);result['total_triangles']=sum(m['triangles'] for m in models);result['total_mesh_nodes']=sum(m['mesh_nodes'] for m in models);result['total_texture_gpu_payload_bytes']=sum(m['texture_gpu_payload_bytes'] for m in models);result['total_scenery_triangles_checked']=sum(m['scenery_triangles_checked'] for m in models)
    result['passed']=not result['errors'];a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['physical_mesh_hashes','logical_nodes']},indent=2))
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
