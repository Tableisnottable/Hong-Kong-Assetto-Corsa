"""Validate geospatial invariants and draw source-derived map previews."""
from pathlib import Path
import collections, json, math, sys
ROOT=Path(__file__).resolve().parents[1]
deps=ROOT.parents[1]/'work/python_deps'
if deps.exists():sys.path.insert(0,str(deps))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer
from shapely.geometry import LineString,shape,box
from shapely import prepare

cfg=json.loads((ROOT/'project.json').read_text(encoding='utf-8'))
region=cfg['first_region']; rb=region['bounds_epsg2326']
allroads=json.loads((ROOT/'gis/hk_roads_grid.json').read_text(encoding='utf-8'))['roads']
roads=json.loads((ROOT/'gis/region_roads_grid.json').read_text(encoding='utf-8'))['roads']
ctx=json.loads((ROOT/'gis/context_grid.json').read_text(encoding='utf-8'))
stats=json.loads((ROOT/'reports/data_inventory.json').read_text(encoding='utf-8'))
boundary=shape(ctx['boundary'])
terrain=np.load(ROOT/'gis/region_terrain_5m.npz')

errors=[]
for kind,items,clip in [('master',allroads,boundary),('region',roads,box(*rb))]:
    clip_tolerance=clip.buffer(.01);prepare(clip_tolerance)
    for rec in items:
        xy=np.asarray(rec['xy'])
        if len(xy)<2 or not np.isfinite(xy).all():errors.append(f'{kind} invalid coordinates {rec["osm_id"]}')
        if len(rec['node_refs'])!=len(xy):errors.append(f'{kind} mismatched node refs {rec["osm_id"]}')
        if not clip_tolerance.covers(LineString(xy)):errors.append(f'{kind} out of boundary {rec["osm_id"]}')
        if rec['width_m']<=0:errors.append(f'{kind} non-positive width {rec["osm_id"]}')
        if abs(LineString(xy).length-rec['length_m'])>.05:errors.append(f'{kind} length mismatch {rec["osm_id"]}')
if np.any(terrain['z']==float(terrain['nodata'])):errors.append('Regional terrain contains nodata; requires fill review')
back=Transformer.from_crs(2326,4326,always_xy=True);forward=Transformer.from_crs(4326,2326,always_xy=True)
x,y=forward.transform(*back.transform(region['origin_easting_m'],region['origin_northing_m']))
roundtrip=math.hypot(x-region['origin_easting_m'],y-region['origin_northing_m'])
if roundtrip>.05:errors.append('CRS round trip exceeds 5 cm numerical tolerance')

parent={}
def find(a):
    parent.setdefault(a,a)
    while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
    return a
def union(a,b):
    a,b=find(a),find(b)
    if a!=b:parent[a]=b
for j,r in enumerate(roads):
    if r['access_state']!='public_candidate':continue
    refs=[str(ref) if ref is not None else f'clip_{j}_{i}' for i,ref in enumerate(r['node_refs'])]
    for a,b in zip(refs,refs[1:]):union(a,b)
comps=collections.Counter(find(n) for n in parent)
validation={'passed':not errors,'errors':errors,'coordinate_roundtrip_error_m':roundtrip,'regional_public_candidate_components_by_shared_osm_nodes':len(comps),'largest_component_node_count':max(comps.values(),default=0),'road_parts_checked':len(roads)+len(allroads),'grade_separated_geometry':'unresolved; explicitly excluded from playable claims','validation_scope':'data integrity, clipping and local coordinates; no game performance, collision or completeness validation'}
(ROOT/'reports/validation.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
print(json.dumps(validation,indent=2))
if errors:raise RuntimeError('Geodata validation failed')

FONT=Path('C:/Windows/Fonts/segoeui.ttf');BOLD=Path('C:/Windows/Fonts/segoeuib.ttf')
def font(s,b=False):return ImageFont.truetype(str(BOLD if b else FONT),s)
BG='#111b24';PANEL='#182630';TEXT='#e6edf2';MUTED='#a7b7c2';ACCENT='#78d6c1';AMBER='#edb261';VIOLET='#d88fc8'
def transform(bounds,rect):
    xmin,ymin,xmax,ymax=bounds;l,t,r,b=rect;s=min((r-l)/(xmax-xmin),(b-t)/(ymax-ymin));cx=(l+r)/2;cy=(t+b)/2
    return lambda x,y:(cx+(x-(xmin+xmax)/2)*s,cy-(y-(ymin+ymax)/2)*s)
def draw_lines(d,items,pt,region_only=False):
    for rec in sorted(items,key=lambda r:r['highway'] in ('motorway','trunk','primary')):
        t=rec['tags'];grade=t.get('bridge','no')!='no' or t.get('tunnel','no')!='no' or t.get('layer','0')!='0'
        color=VIOLET if grade and region_only else (ACCENT if rec['access_state']=='public_candidate' else AMBER)
        width=3 if rec['highway'] in ('motorway','trunk','primary','secondary') and region_only else 2 if region_only else 1
        d.line([pt(*p) for p in rec['xy']],fill=color,width=width)
def scale(d,pt,x,y,length):
    a=pt(x,y);b=pt(x+length,y)
    d.line([a,b],fill=TEXT,width=3)
    for p in (a,b):d.line([(p[0],p[1]-5),(p[0],p[1]+5)],fill=TEXT,width=2)
    d.text((a[0],a[1]+12),f'{length/1000:g} km',font=font(19),fill=TEXT)

im=Image.new('RGB',(1800,1150),BG);d=ImageDraw.Draw(im)
d.text((54,34),'HONG KONG / 1:1',font=font(45,True),fill=TEXT)
d.text((55,94),'New regional Assetto Corsa project  |  Geospatial foundation',font=font(23),fill=MUTED)
d.rounded_rectangle((50,150,860,1000),radius=18,fill=PANEL)
d.rounded_rectangle((890,150,1750,1000),radius=18,fill=PANEL)
d.text((76,172),'HONG KONG MASTER ROAD INVENTORY',font=font(23,True),fill=TEXT)
d.text((915,172),'HK01  /  KAM TIN — SHEK KONG',font=font(23,True),fill=TEXT)
xy=np.vstack([np.asarray(r['xy']) for r in allroads]);extent=(xy[:,0].min()-1000,xy[:,1].min()-1000,xy[:,0].max()+1000,xy[:,1].max()+1000)
left=transform(extent,(74,235,840,870));right=transform(rb,(920,250,1720,960))
for line in ctx['coastlines']:
    if len(line)>1:
        clipped=LineString(line).intersection(box(*extent))
        parts=[clipped] if clipped.geom_type=='LineString' else list(clipped.geoms) if hasattr(clipped,'geoms') else []
        for p in parts:
            if p.geom_type=='LineString' and not p.is_empty:d.line([left(*xy) for xy in p.coords],fill='#344c5c',width=1)
draw_lines(d,allroads,left)
a=left(rb[0],rb[3]);b=left(rb[2],rb[1]);d.rectangle([a,b],outline='#ffffff',width=3)
d.rounded_rectangle((a[0],a[1]-32,a[0]+65,a[1]-3),radius=4,fill=BG)
d.text((a[0]+5,a[1]-31),'HK01',font=font(20,True),fill=TEXT)
for x in range(rb[0],rb[2]+1,1000):d.line([right(x,rb[1]),right(x,rb[3])],fill='#30414c',width=1)
for y in range(rb[1],rb[3]+1,1000):d.line([right(rb[0],y),right(rb[2],y)],fill='#30414c',width=1)
draw_lines(d,roads,right,True)
d.text((1620,211),'N ↑',font=font(24,True),fill=TEXT)
d.text((80,904),f"{stats['master_road_parts']:,} mapped road parts",font=font(27,True),fill=TEXT)
d.text((80,948),'Road inventory is not a completed drivable map.',font=font(21),fill=MUTED)
d.text((915,211),'6 × 6 km  |  Grid spacing: 1 km  |  One unit = one metre',font=font(20),fill=MUTED)
for i,(color,label) in enumerate([(ACCENT,'Public-road candidates'),(AMBER,'Access / road-type review'),(VIOLET,'Bridge / tunnel / layer review')]):
    x=65+i*570;d.line([(x,1040),(x+35,1040)],fill=color,width=5);d.text((x+48,1024),label,font=font(22),fill=TEXT)
d.text((60,1092),'© OpenStreetMap contributors (ODbL)  |  Source snapshot: 2026-11-12 21:23 UTC  |  Not playable yet',font=font(18),fill=MUTED)
im.save(ROOT/'previews/HK_project_overview.png')
