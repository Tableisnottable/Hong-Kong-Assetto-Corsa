"""Prepare route-wide LandsD scenery with spatial batches and mipmapped DDS.

All source files remain unchanged. Output coordinates use the shared local
metre origin. Imported geometry is visual-only; the test road stays separate.
"""
from pathlib import Path
import sys,json,hashlib,collections,argparse,io,struct,math
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parents[1]/'work/python_deps'))
import numpy as np
from PIL import Image
import shapely
from shapely.geometry import LineString,box
from prepare_csdi_scenery import primitives,SOURCE,ORIGIN
OUT=ROOT/'driving_test/route_scenery'

def repair_uv(vertices,uv):
    """Repair missing source UVs from the nearest valid vertex in this batch."""
    bad=~np.isfinite(uv).all(axis=1)
    if not bad.any():return uv,0
    uv=uv.copy();valid=np.flatnonzero(~bad)
    for index in np.flatnonzero(bad):
        if len(valid):
            nearest=valid[int(np.argmin(((vertices[valid]-vertices[index])**2).sum(axis=1)))];uv[index]=uv[nearest]
        else:uv[index]=(.5,.5)
    return uv,int(bad.sum())

def dds_mips(image,path):
    """Use Pillow's BC1 encoder, with a complete legacy DDS mip chain."""
    levels=[];im=image.convert('RGB');width,height=im.size
    while True:
        b=io.BytesIO();im.save(b,format='DDS',pixel_format='DXT1');data=b.getvalue()
        expected=((im.width+3)//4)*((im.height+3)//4)*8
        if len(data)-128!=expected:raise RuntimeError('Unexpected BC1 encoder size')
        levels.append(data)
        if im.size==(1,1):break
        im=im.resize((max(1,im.width//2),max(1,im.height//2)),Image.Resampling.LANCZOS)
    header=bytearray(levels[0][:128]);flags=struct.unpack_from('<I',header,8)[0]
    struct.pack_into('<I',header,8,flags|0x20000)
    struct.pack_into('<I',header,20,((width+3)//4)*((height+3)//4)*8)
    struct.pack_into('<I',header,28,len(levels));struct.pack_into('<I',header,108,0x1000|0x8|0x400000)
    temp=path.with_suffix('.partial')
    with temp.open('wb') as f:
        f.write(header)
        for data in levels:f.write(data[128:])
    temp.replace(path)
    with Image.open(path) as check:check.load()
    return len(levels),path.stat().st_size-128

def prepare_sheet(sheet,source_record):
    destination=OUT/'per_sheet'/(sheet+'.json');destination.parent.mkdir(parents=True,exist_ok=True)
    (OUT/'meshes').mkdir(exist_ok=True);(OUT/'textures').mkdir(exist_ok=True)
    route=np.load(ROOT/'driving_test/route_geometry.npz')['center'];line=LineString(route[:,:2])
    protected=line.buffer(11,join_style=2);near_area=line.buffer(190,join_style=2)
    shapely.prepare(protected);shapely.prepare(near_area)
    tile=box(*[v-o for v,o in zip(source_record['bounds_epsg2326'],[826000,833000,826000,833000])])
    shapely.prepare(tile)
    meshes=[];materials={};texture_cache={};missing=[];excluded=[];stats=collections.Counter();removed=collections.Counter();uv_repairs=[]
    def texture(j,p,path,category,cap):
        material=j.get('materials',[])[p.get('material',0)];pm=material.get('pbrMetallicRoughness',{});ref=pm.get('baseColorTexture')
        src=None
        if ref:
            import urllib.parse
            src=path.parent/urllib.parse.unquote(j['images'][j['textures'][ref['index']]['source']]['uri'])
        key=(str(src),cap) if src else ('fallback',tuple(pm.get('baseColorFactor',[.65,.65,.65,1])))
        if key in texture_cache:return texture_cache[key]
        if src and src.is_file():
            raw=src.read_bytes();content=hashlib.sha256(raw).hexdigest()
            with Image.open(io.BytesIO(raw)) as original:
                size=original.size
                dims=tuple(max(4,2**int(math.floor(math.log2(max(4,min(s,cap)))))) for s in size)
                im=original.convert('RGB').resize(dims,Image.Resampling.LANCZOS)
        else:
            if src:missing.append(str(src.relative_to(ROOT)).replace('\\','/'))
            color=pm.get('baseColorFactor',[.65,.65,.65,1]);im=Image.new('RGB',(4,4),tuple(round(max(0,min(1,c))*255) for c in color[:3]));size=im.size;dims=im.size;content=hashlib.sha256(str(color).encode()).hexdigest()
        name='R3_'+hashlib.sha256((content+str(dims)).encode()).hexdigest()[:20];path_dds=OUT/'textures'/(name+'.dds')
        if path_dds.is_file():
            try:
                with Image.open(path_dds) as cached:cached.load()
                header=path_dds.read_bytes()[:128];levels=struct.unpack_from('<I',header,28)[0];payload=path_dds.stat().st_size-128
            except (OSError,ValueError):levels,payload=dds_mips(im,path_dds)
        else:levels,payload=dds_mips(im,path_dds)
        materials[name]={'name':name,'texture':path_dds.name,'source_texture':str(src.relative_to(ROOT)).replace('\\','/') if src else None,'original_dimensions':list(size),'dimensions':list(dims),'encoding':'DDS DXT1/BC1 RGB','mip_levels':levels,'gpu_payload_bytes':payload,'source_sha256':content}
        texture_cache[key]=name;return name
    for path in sorted((SOURCE/sheet).rglob('*.gltf')):
        category=path.relative_to(SOURCE/sheet).parts[0]
        for pi,(j,p,v,uv,f) in enumerate(primitives(path)):
            stats[category]+=len(f)
            valid=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)>1e-6
            removed['degenerate']+=int((~valid).sum());f=f[valid]
            if not len(f):continue
            tri=shapely.polygons(v[f,:2]);blocked=shapely.intersects(protected,tri)
            if category=='BUILDING':
                bounds=v.min(axis=0),v.max(axis=0);distance=line.distance(box(bounds[0][0],bounds[0][1],bounds[1][0],bounds[1][1]))
                if distance>190:removed['outside_detail_radius']+=len(f);continue
                if blocked.any():excluded.append(path.stem);removed['road_corridor']+=len(f);continue
                cap=2048 if distance<80 else 1024
            else:
                keep=~blocked
                if category!='TERRAIN(TB)':keep&=shapely.intersects(near_area,tri)
                removed['road_corridor']+=int(blocked.sum());removed['outside_detail_radius']+=int((~keep&~blocked).sum());f=f[keep]
                if not len(f):continue
                cap=2048
            mat=texture(j,p,path,category,cap)
            centers=v[f,:2].mean(axis=1)
            if category=='BUILDING':buckets={(0,0):np.arange(len(f))}
            else:
                spatial=np.floor(centers/150).astype(int);buckets=collections.defaultdict(list)
                for ii,key in enumerate(spatial):buckets[tuple(key)].append(ii)
            for (ex,ny),indices in buckets.items():
                ff=f[indices];used,index=np.unique(ff,return_inverse=True);vv=v[used];uuv=uv[used]
                name=f'{sheet}_{category.replace("(","_").replace(")","")}_{path.stem}_{pi:02d}_{ex}_{ny}'
                uuv,repaired=repair_uv(vv,uuv)
                if repaired:uv_repairs.append({'name':name,'vertices':repaired,'method':'nearest valid source UV in spatial batch; centre fallback only if none valid'})
                file=OUT/'meshes'/(name+'.npz');np.savez_compressed(file,vertices=vv.astype(np.float32),uv=uuv.astype(np.float32),faces=index.reshape(-1,3).astype(np.int32))
                center=vv[:,:2].mean(axis=0);distance=line.distance(shapely.Point(center));ratio=.55 if category=='GENERIC' and distance<65 else .28 if category=='GENERIC' else .55 if category=='VEGETATION(TB)' and distance<65 else .30 if category=='VEGETATION(TB)' else 1.
                meshes.append({'name':name,'sheet':sheet,'category':category,'source_model':path.stem,'file':str(file.relative_to(OUT)).replace('\\','/'),'material':mat,'triangles_before_decimation':len(ff),'decimate_ratio':ratio,'distance_to_route_m':distance,'bounds_local':[vv.min(axis=0).tolist(),vv.max(axis=0).tolist()]})
        print('PREPARED_ROUTE',sheet,category,path.stem,flush=True)
    report={'sheet':sheet,'bounds_epsg2326':source_record['bounds_epsg2326'],'source_record':source_record,'detail_radius_m':190,'road_exclusion_buffer_m':11,'source_triangles':dict(stats),'removed_triangles':dict(removed),'excluded_buildings':excluded,'missing_source_textures':missing,'uv_repairs':uv_repairs,'meshes':meshes,'materials':list(materials.values()),'texture_gpu_bytes':sum(m['gpu_payload_bytes'] for m in materials.values())}
    destination.write_text(json.dumps(report,indent=2),encoding='utf-8');print('SHEET_PREPARED',sheet,len(meshes),len(materials),report['texture_gpu_bytes'],flush=True)

def finalise():
    source=json.loads((OUT/'source_manifest.json').read_text());records=[];materials={};meshes=[];missing=[];model_owner={};deduplicated=0
    # Later source revision wins for duplicate individual buildings across sheets.
    for record in sorted(source['sheets'],key=lambda r:r['revision_epoch_ms'] or 0,reverse=True):
        path=OUT/'per_sheet'/(record['sheet']+'.json')
        if not path.is_file():raise RuntimeError('Sheet not prepared: '+record['sheet'])
        prepared=json.loads(path.read_text());records.append({k:v for k,v in prepared.items() if k not in ['meshes','materials']});materials.update({m['name']:m for m in prepared['materials']});missing.extend(prepared['missing_source_textures'])
        for mesh in prepared['meshes']:
            if mesh['category']=='BUILDING':
                owner=model_owner.setdefault(mesh['source_model'],mesh['sheet'])
                if owner!=mesh['sheet']:deduplicated+=1;continue
            meshes.append(mesh)
    used={m['material'] for m in meshes};materials={k:v for k,v in materials.items() if k in used}
    report={'version':'0.3-route-scenery','dataset':'3D Visualisation Map (Individualised models)','sheets':[r['sheet'] for r in records],'origin_epsg2326':ORIGIN[:2].tolist(),'metres_per_unit':1,'detail_radius_m':190,'road_exclusion_buffer_m':11,'source_sheet_records':records,'duplicate_building_parts_removed':deduplicated,'missing_source_textures':sorted(set(missing)),'materials':list(materials.values()),'meshes':meshes,'texture_gpu_payload_bytes_with_mips':sum(m['gpu_payload_bytes'] for m in materials.values()),'material_count':len(materials)}
    if report['texture_gpu_payload_bytes_with_mips']>1800*1024*1024:raise RuntimeError('Texture budget exceeded: lower distant texture resolution')
    (OUT/'prepared_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('ROUTE_SCENERY_PREPARED',len(meshes),len(materials),report['texture_gpu_payload_bytes_with_mips'],flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--sheet');p.add_argument('--finalise',action='store_true');a=p.parse_args();source=json.loads((OUT/'source_manifest.json').read_text())
    if a.sheet:
        rec=next(r for r in source['sheets'] if r['sheet']==a.sheet);prepare_sheet(a.sheet,rec)
    else:
        for rec in source['sheets']:
            if not (OUT/'per_sheet'/(rec['sheet']+'.json')).is_file():prepare_sheet(rec['sheet'],rec)
    if a.finalise:finalise()

if __name__=='__main__':main()
