"""Prepare an attributed, locally referenced sample of LandsD individualised models.

Original downloaded files remain untouched. Coordinates are transformed in
float64 before storing local float32 meshes. This sample is visual scenery;
the established test-route collision surfaces remain authoritative.
"""
from pathlib import Path
import sys, json, hashlib, collections, urllib.parse
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1] / 'work/python_deps'))
import numpy as np
from PIL import Image
import shapely
from shapely.geometry import LineString

SOURCE = ROOT/'source/csdi_individualised'
OUT = ROOT/'driving_test/csdi_sample'
SHEET = '6-NE-12D'
ORIGIN = np.array([826000., 833000., 0.])

def accessor(j, blobs, idx):
    a=j['accessors'][idx]; view=j['bufferViews'][a['bufferView']]
    dtype={5120:'i1',5121:'u1',5122:'<i2',5123:'<u2',5125:'<u4',5126:'<f4'}[a['componentType']]
    width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
    offset=view.get('byteOffset',0)+a.get('byteOffset',0)
    stride=view.get('byteStride',np.dtype(dtype).itemsize*width)
    ar=np.ndarray((a['count'],width),dtype=dtype,buffer=blobs[view['buffer']],offset=offset,strides=(stride,np.dtype(dtype).itemsize)).copy()
    if a.get('normalized') and a['componentType']!=5126:
        info=np.iinfo(dtype); ar=np.maximum(ar.astype(float)/info.max,-1)
    return ar

def node_matrix(node):
    if 'matrix' in node:return np.asarray(node['matrix'],float).reshape((4,4),order='F')
    m=np.eye(4);x,y,z,w=node.get('rotation',[0,0,0,1])
    m[:3,:3]=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
              [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
              [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
    m[:3,:3]*=np.asarray(node.get('scale',[1,1,1]))
    m[:3,3]=node.get('translation',[0,0,0]); return m

def primitives(path):
    j=json.loads(path.read_text(encoding='utf-8'))
    blobs=[(path.parent/urllib.parse.unquote(b['uri'])).read_bytes() for b in j['buffers']]
    def visit(i,parent):
        node=j['nodes'][i];m=parent@node_matrix(node)
        if 'mesh' in node:
            for p in j['meshes'][node['mesh']]['primitives']:
                if p.get('mode',4)!=4:raise ValueError('Expected GLTF triangle primitives')
                v=accessor(j,blobs,p['attributes']['POSITION']).astype(float)
                v=v@m[:3,:3].T+m[:3,3]
                # glTF +Y up, -Z north -> Blender +Z up, +Y north.
                v=v[:,[0,2,1]]*np.array([1,-1,1])-ORIGIN
                uv=accessor(j,blobs,p['attributes']['TEXCOORD_0'])
                uv[:,1]=1-uv[:,1]  # glTF top-left -> Blender bottom-left.
                f=accessor(j,blobs,p['indices']).reshape(-1,3).astype(np.int32)
                if np.linalg.det(m[:3,:3])<0:f=f[:,[0,2,1]]
                yield j,p,v,uv,f
        for k in node.get('children',[]):yield from visit(k,m)
    for i in j['scenes'][j.get('scene',0)]['nodes']:yield from visit(i,np.eye(4))

def main():
    (OUT/'meshes').mkdir(parents=True,exist_ok=True);(OUT/'textures').mkdir(exist_ok=True)
    route=np.load(ROOT/'driving_test/route_geometry.npz')['center']
    line=LineString(route[:,:2]);corridor=line.buffer(11,join_style=2)
    shapely.prepare(corridor)
    records=[];excluded=[];missing=[];materials={};texture_cache={};source_stats=collections.Counter();removed=collections.Counter()
    def texture(j,p,path,category):
        mat=j.get('materials',[])[p.get('material',0)]
        pm=mat.get('pbrMetallicRoughness',{});ref=pm.get('baseColorTexture')
        if ref:
            im=j['images'][j['textures'][ref['index']]['source']]
            source=path.parent/urllib.parse.unquote(im['uri'])
        else:source=None
        key=str(source) if source else 'fallback_'+str(pm.get('baseColorFactor',[.65,.65,.65,1]))
        if key in texture_cache:return texture_cache[key]
        name='CSDI_'+hashlib.sha256(key.encode()).hexdigest()[:16]
        dest=OUT/'textures'/(name+'.png')
        if source and source.is_file():
            with Image.open(source) as ii:
                original=ii.size
                im=None
                if dest.exists():
                    try:
                        with Image.open(dest) as cached:im=cached.copy()
                    except (OSError,ValueError):pass
                if im is None:
                    im=ii.convert('RGB')
                    # Keep close individual facades at 2K; cap photogrammetry atlases at 2K.
                    im.thumbnail((2048,2048),Image.Resampling.LANCZOS)
                    temp=dest.with_suffix('.partial');im.save(temp,format='PNG',compress_level=4);temp.replace(dest)
        else:
            if source:missing.append(str(source.relative_to(ROOT)))
            color=pm.get('baseColorFactor',[.65,.65,.65,1]);im=Image.new('RGB',(8,8),tuple(int(c*255) for c in color[:3]));original=im.size;im.save(dest)
        rec={'name':name,'texture':dest.name,'source':str(source.relative_to(ROOT)) if source else None,'original_dimensions':list(original),'dimensions':list(im.size),'rgba8_budget_bytes':im.width*im.height*4}
        materials[name]=rec;texture_cache[key]=name;return name
    for path in sorted((SOURCE/SHEET).rglob('*.gltf')):
        category=path.relative_to(SOURCE/SHEET).parts[0]
        for pi,(j,p,v,uv,f) in enumerate(primitives(path)):
            source_stats[category]+=len(f)
            valid=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)>1e-6
            removed['degenerate']+=int((~valid).sum());f=f[valid]
            if not len(f):continue
            triangles=shapely.polygons(v[f,:2])
            blocked=shapely.intersects(corridor,triangles)
            # Keep original whole individual buildings if they clear the route.
            # Tile meshes are cut at triangle edges to protect road/pit visibility.
            if category=='BUILDING' and blocked.any():
                excluded.append({'model':path.stem,'reason':'intersects conservative 11 m test-route corridor'});removed['road_corridor']+=len(f);continue
            removed['road_corridor']+=int(blocked.sum());f=f[~blocked]
            if not len(f):continue
            used,index=np.unique(f,return_inverse=True);v=v[used];uv=uv[used];f=index.reshape(-1,3).astype(np.int32)
            name=f'{category.replace("(","_").replace(")","")}_{path.stem}_{pi:02d}'
            file=OUT/'meshes'/(name+'.npz');np.savez_compressed(file,vertices=v.astype(np.float32),uv=uv.astype(np.float32),faces=f)
            mat=texture(j,p,path,category)
            ratio=.30 if category=='GENERIC' else .40 if category=='VEGETATION(TB)' else 1.
            records.append({'name':name,'category':category,'source_model':path.stem,'file':str(file.relative_to(OUT)).replace('\\','/'),'material':mat,'source_triangles':len(f),'decimate_ratio':ratio,'bounds_local':[v.min(axis=0).tolist(),v.max(axis=0).tolist()]})
        print('PREPARED',category,path.stem,flush=True)
    archive=SOURCE/(SHEET+'_GLTF.zip')
    report={'dataset':'3D Visualisation Map (Individualised models)','sheet':SHEET,'coverage_epsg2326':[824750,832400,825500,833000],
            'source_archive_bytes':archive.stat().st_size,'source_archive_sha256':hashlib.file_digest(archive.open('rb'),'sha256').hexdigest(),
            'sheet_revision':'2026-07-17 (index metadata; not a survey-date assertion)','origin_epsg2326':ORIGIN[:2].tolist(),'metres_per_unit':1,
            'source_triangle_counts':dict(source_stats),'removed_triangles':dict(removed),'excluded_models':excluded,'missing_source_textures':missing,
            'material_count':len(materials),'texture_rgba8_budget_bytes_without_mips':sum(m['rgba8_budget_bytes'] for m in materials.values()),
            'scenery_role':'visual only; all objects use non-physical names; test route collision is separate',
            'road_exclusion_buffer_m':11,'materials':list(materials.values()),'meshes':records}
    (OUT/'prepared_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['meshes','materials','excluded_models']},indent=2))

if __name__=='__main__':main()
