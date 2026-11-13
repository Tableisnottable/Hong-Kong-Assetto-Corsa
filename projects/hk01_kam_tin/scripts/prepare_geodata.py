"""Build a reproducible 1:1 GIS foundation; no game installation or launch.
Requires osmium, pyproj, shapely, numpy, Pillow. Run from any directory.
"""
from pathlib import Path
import argparse, collections, csv, hashlib, json, math, re, sys, zipfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parents[1]
FALLBACK_DEPS = HERE.parents[1] / 'work/python_deps'
if FALLBACK_DEPS.exists(): sys.path.insert(0, str(FALLBACK_DEPS))
import numpy as np
import osmium
from pyproj import Transformer
from shapely.geometry import LineString, Polygon, box, mapping, shape
from shapely.ops import transform as geom_transform, polygonize, unary_union
from shapely import make_valid, prepare

sys.stdout.reconfigure(encoding='utf-8')
CONFIG = json.loads((HERE/'project.json').read_text(encoding='utf-8'))
REG = CONFIG['first_region']
BBOX = box(*REG['bounds_epsg2326'])
TO_GRID = Transformer.from_crs(4326, 2326, always_xy=True)
TO_WGS = Transformer.from_crs(2326, 4326, always_xy=True)
REG_WGS_BOUNDS=geom_transform(TO_WGS.transform,BBOX.buffer(250)).bounds
HW = set('motorway motorway_link trunk trunk_link primary primary_link secondary secondary_link tertiary tertiary_link unclassified residential living_street service road track'.split())
WIDTHS = {'motorway':10.5,'trunk':10.5,'primary':7,'secondary':7,'tertiary':6.5,'unclassified':5.5,'residential':5.5,'living_street':4,'service':4,'road':5.5,'track':3.5}

def line_parts(g):
    if g.is_empty: return []
    if g.geom_type == 'LineString': return [g] if g.length > 0.1 else []
    if hasattr(g,'geoms'): return [p for c in g.geoms for p in line_parts(c)]
    return []

def access_state(t):
    val = next((t[k] for k in ('motorcar','motor_vehicle','vehicle','access') if k in t), '')
    if val in ('no','private','agricultural','forestry','delivery','customers','permit','military','emergency'):
        return 'restricted_review'
    if t.get('highway') in ('track','road','pedestrian','footway','path') or any(':conditional' in k for k in t):
        return 'review'
    return 'public_candidate'

def road_width(t):
    try:
        value = float(t.get('width','').replace(' m',''))
        if 1 <= value <= 40: return value, 'osm_width'
    except ValueError: pass
    try:
        lanes = int(t.get('lanes',''))
        if 1 <= lanes <= 8: return lanes*3.2, 'estimated_from_lanes'
    except ValueError: pass
    hw = t['highway']
    return (4.5 if hw.endswith('_link') else WIDTHS.get(hw,4)), 'estimated_from_class'

class ReadOSM(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.roads=[]; self.buildings=[]; self.coast=[]; self.places=[]; self.boundary=None
        self.invalid_ways=0
        self.building_relations_skipped=0
    def relation(self,r):
        if r.tags.get('building') and r.tags.get('building')!='no': self.building_relations_skipped+=1
    def node(self,n):
        t=dict(n.tags)
        if t.get('place') in ('city','town','suburb','village','island') and t.get('name'):
            self.places.append({'name':t.get('name:en',t['name']), 'xy':TO_GRID.transform(n.location.lon,n.location.lat), 'type':t['place']})
    def way(self,w):
        t=dict(w.tags); h=t.get('highway','')
        motor_access=next((t[k] for k in ('motorcar','motor_vehicle','vehicle','access') if k in t),'')
        is_road = h in HW or (h in ('pedestrian','footway','path') and motor_access in ('yes','permissive','destination'))
        is_coast=t.get('natural')=='coastline'
        is_building=t.get('building') and t.get('building')!='no' and len(w.nodes)>=4 and w.nodes[0].ref==w.nodes[-1].ref
        if not is_road and not is_coast and not is_building: return
        try:
            ll=[(n.lon,n.lat) for n in w.nodes]
            if len(ll)<2: return
            if is_building and not is_road and not is_coast:
                minx=min(p[0] for p in ll);maxx=max(p[0] for p in ll);miny=min(p[1] for p in ll);maxy=max(p[1] for p in ll)
                if maxx<REG_WGS_BOUNDS[0] or minx>REG_WGS_BOUNDS[2] or maxy<REG_WGS_BOUNDS[1] or miny>REG_WGS_BOUNDS[3]:return
            xy=list(zip(*TO_GRID.transform(*zip(*ll))))
            g=LineString(xy)
        except Exception:
            self.invalid_ways+=1; return
        if is_coast: self.coast.append(g)
        if is_road and t.get('area')!='yes': self.roads.append((w.id,t,g,[n.ref for n in w.nodes]))
        if is_building:
            poly=Polygon(xy)
            if not poly.is_valid:poly=make_valid(poly)
            if poly.intersects(BBOX):self.buildings.append({'osm_type':'way','osm_id':w.id,'tags':t,'geometry':mapping(poly.intersection(BBOX))})

def read_complete_boundary(path):
    """Assemble only the explicitly downloaded administrative boundary."""
    root=ET.parse(path).getroot()
    nodes={int(n.get('id')):(float(n.get('lon')),float(n.get('lat'))) for n in root.findall('node')}
    ways={int(w.get('id')):[nodes[int(n.get('ref'))] for n in w.findall('nd')] for w in root.findall('way')}
    relation=next(r for r in root.findall('relation') if r.get('id')=='913110')
    outer=[];inner=[]
    for m in relation.findall('member'):
        if m.get('type')!='way' or m.get('role') not in ('outer','inner',''):continue
        coords=ways[int(m.get('ref'))]
        (inner if m.get('role')=='inner' else outer).append(LineString(coords))
    boundary=unary_union(list(polygonize(outer)))
    if inner:boundary=boundary.difference(unary_union(list(polygonize(inner))))
    if boundary.is_empty or not boundary.is_valid:raise RuntimeError('Incomplete or invalid full Hong Kong boundary')
    return geom_transform(TO_GRID.transform,boundary)

def terrain_crop(source_zip):
    """Stream ASCII rows; keep a regional 5 m crop and a coarse 100 m overview."""
    with zipfile.ZipFile(source_zip) as z:
        n=next(n for n in z.namelist() if n.lower().endswith('.asc'))
        with z.open(n) as f:
            header={}
            for _ in range(6):
                k,v=f.readline().decode().split(); header[k.lower()]=float(v)
            nc,nr=int(header['ncols']),int(header['nrows']); cell=header['cellsize']
            x0=header['xllcorner']+cell/2; ytop=header['yllcorner']+(nr-.5)*cell
            xmin,ymin,xmax,ymax=REG['bounds_epsg2326']
            # One cell margin makes bilinear sampling valid at each regional edge.
            c0=max(0,int(math.floor((xmin-x0)/cell))-1); c1=min(nc,int(math.ceil((xmax-x0)/cell))+2)
            r0=max(0,int(math.floor((ytop-ymax)/cell))-1); r1=min(nr,int(math.ceil((ytop-ymin)/cell))+2)
            region=np.empty((r1-r0,c1-c0),np.float32); overview=[]
            for r in range(nr):
                raw=f.readline()
                if r0<=r<r1 or r%20==0:
                    row=np.fromstring(raw.decode('ascii'),sep=' ',dtype=np.float32)
                    if len(row)!=nc: raise ValueError(f'DTM row {r} has {len(row)} values; expected {nc}')
                    if r0<=r<r1: region[r-r0]=row[c0:c1]
                    if r%20==0: overview.append(row[::20])
            meta={**header,'crop_x_first':x0+c0*cell,'crop_y_first':ytop-r0*cell,'crop_shape':list(region.shape)}
            np.savez_compressed(HERE/'gis/region_terrain_5m.npz',z=region,x0=meta['crop_x_first'],y0=meta['crop_y_first'],cell=cell,nodata=header['nodata_value'])
            np.savez_compressed(HERE/'gis/hk_terrain_100m.npz',z=np.asarray(overview),x0=x0,y0=ytop,cell=cell*20,nodata=header['nodata_value'])
            return meta

def feature(g,p): return {'type':'Feature','properties':p,'geometry':mapping(geom_transform(TO_WGS.transform,g))}
def savejson(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':')),encoding='utf-8')

def main():
    p=argparse.ArgumentParser(); p.add_argument('--source-dir',type=Path,default=HERE/'source'); a=p.parse_args()
    for d in ('gis','reports','blender','previews'): (HERE/d).mkdir(exist_ok=True)
    osm=a.source_dir/'hong-kong-latest.osm.pbf'
    print('Reading OSM roads and regional building footprints...',flush=True)
    read=ReadOSM(); read.apply_file(str(osm),locations=True,idx='flex_mem')
    read.boundary=read_complete_boundary(a.source_dir/'hong-kong-boundary-913110.osm')
    prepare(read.boundary)
    print(f'Clipping {len(read.roads)} source road ways to Hong Kong...',flush=True)
    records=[]; features=[]; region=[]; regional_features=[]; qa=[]; totals=collections.Counter(); classes=collections.Counter()
    for osm_id,t,g,refs in read.roads:
        if not read.boundary.intersects(g):continue
        clipped=g if read.boundary.covers(g) else g.intersection(read.boundary)
        ref_by_xy={(round(x,3),round(y,3)):ref for (x,y),ref in zip(g.coords,refs)}
        for part_i,part in enumerate(line_parts(clipped)):
            state=access_state(t); width,wsrc=road_width(t)
            props={'osm_id':osm_id,'part':part_i,'highway':t['highway'],'name':t.get('name:en',t.get('name','')),'access_state':state,'width_m':width,'width_source':wsrc,'length_m':round(part.length,2),'tags':t}
            partxy=[[round(x,3),round(y,3)] for x,y in part.coords]
            records.append({**props,'xy':partxy,'node_refs':[ref_by_xy.get(tuple(p)) for p in partxy],'clipped_at_boundary':not part.equals(g)})
            features.append(feature(part,props)); totals[state]+=part.length; classes[t['highway']]+=1
            for j,rp in enumerate(line_parts(part.intersection(BBOX))):
                rxy=[[round(x,3),round(y,3)] for x,y in rp.coords]
                regional={**props,'regional_part':j,'length_m':round(rp.length,2),'xy':rxy,'node_refs':[ref_by_xy.get(tuple(p)) for p in rxy],'clipped_at_region':not rp.equals(g)}
                region.append(regional); regional_features.append(feature(rp,{k:v for k,v in regional.items() if k!='xy'}))
                issues=[]
                if t.get('bridge','no')!='no': issues.append('bridge_deck_height_unverified')
                if t.get('tunnel','no')!='no': issues.append('tunnel_profile_unverified')
                if wsrc!='osm_width': issues.append('width_estimated')
                if state!='public_candidate': issues.append(state)
                if t.get('layer','0')!='0': issues.append('layer_requires_3D_review')
                if issues: qa.append({'osm_id':osm_id,'name':props['name'],'highway':t['highway'],'issues':'; '.join(issues),'osm_url':f'https://www.openstreetmap.org/way/{osm_id}'})
    # Network and terrain are data foundations, never assert these are finished road surfaces.
    savejson(HERE/'gis/hk_roads.geojson',{'type':'FeatureCollection','features':features})
    savejson(HERE/'gis/region_roads.geojson',{'type':'FeatureCollection','features':regional_features})
    savejson(HERE/'gis/hk_boundary.geojson',{'type':'FeatureCollection','features':[feature(read.boundary,{'source':'OSM relation 913110'})]})
    savejson(HERE/'gis/hk_roads_grid.json',{'crs':'EPSG:2326','units':'metres','roads':records})
    savejson(HERE/'gis/region_roads_grid.json',{'crs':'EPSG:2326','units':'metres','origin':[REG['origin_easting_m'],REG['origin_northing_m']],'roads':region})
    savejson(HERE/'gis/region_buildings_grid.json',{'crs':'EPSG:2326','buildings':read.buildings})
    savejson(HERE/'gis/context_grid.json',{'crs':'EPSG:2326','boundary':mapping(read.boundary),'coastlines':[list(g.coords) for g in read.coast],'places':read.places})
    with (HERE/'reports/region_review_queue.csv').open('w',encoding='utf-8-sig',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=['osm_id','name','highway','issues','osm_url']);wr.writeheader();wr.writerows(qa)
    tiles=collections.Counter()
    for rec in records:
        g=LineString(rec['xy']); xmin,ymin,xmax,ymax=g.bounds
        for x in range(int(xmin//1000),int(xmax//1000)+1):
            for y in range(int(ymin//1000),int(ymax//1000)+1):
                length=g.intersection(box(x*1000,y*1000,(x+1)*1000,(y+1)*1000)).length
                if length>0: tiles[(x,y)]+=length
    savejson(HERE/'gis/authoring_tiles.json',{'crs':'EPSG:2326','tile_size_m':1000,'purpose':'authoring and export grouping; not runtime streaming','tiles':[{'id':f'E{x}_N{y}','bounds':[x*1000,y*1000,(x+1)*1000,(y+1)*1000],'road_line_km':round(v/1000,3)} for (x,y),v in sorted(tiles.items())]})
    print('Cropping the terrain grid...',flush=True)
    dtm_meta=terrain_crop(a.source_dir/'Whole_HK_DTM_5m.zip')
    header=osmium.io.Reader(str(osm)); stamp=header.header().get('osmosis_replication_timestamp');header.close()
    regcounts=collections.Counter(r['access_state'] for r in region)
    stats={'osm_data_timestamp_utc':stamp,'boundary_relation':913110,'master_road_parts':len(records),'master_road_line_km_by_access':{k:round(v/1000,2) for k,v in totals.items()},'road_parts_by_highway':dict(classes),'authoring_tiles_with_roads':len(tiles),'region_road_parts':len(region),'region_road_parts_by_access':dict(regcounts),'region_road_line_km_by_access':{k:round(sum(r['length_m'] for r in region if r['access_state']==k)/1000,2) for k in regcounts},'region_building_areas':len(read.buildings),'source_building_relations_deferred':read.building_relations_skipped,'region_qa_rows':len(qa),'invalid_source_ways_skipped':read.invalid_ways,'dtm':dtm_meta,'limitations':['Line lengths are mapped OSM line lengths: divided carriageways count separately, not official network mileage.','OSM is a starting inventory, not proof all Hong Kong roads are present.','Private/motor-access-restricted and track roads remain separate review data.','OSM layer and bridge/tunnel flags are not measured elevations.','Building blockout uses simple closed OSM ways; complex building relations are deferred.','No road mesh, collision, AI, traffic, or KN5 release has been validated.']}
    savejson(HERE/'reports/data_inventory.json',stats)
    provenance={'created_local_date':CONFIG['created_local_date'],'sources':CONFIG['sources'],'files':[]}
    for f in a.source_dir.iterdir():
        if f.is_file(): provenance['files'].append({'name':f.name,'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
    savejson(HERE/'reports/source_manifest.json',provenance)
    print(json.dumps({k:v for k,v in stats.items() if k not in ('road_parts_by_highway','dtm')},indent=2))

if __name__=='__main__': main()
