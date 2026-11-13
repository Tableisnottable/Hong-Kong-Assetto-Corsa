"""Select source canopy locations and author restrained surface/leaf textures."""
from pathlib import Path
import sys,json,collections,math
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT.parents[1]/'work/python_deps'))
import numpy as np,shapely
from shapely.geometry import LineString,box
from PIL import Image,ImageDraw,ImageFilter
FULL=ROOT/'driving_test/route_scenery';OUT=ROOT/'driving_test/quality_pass';OUT.mkdir(exist_ok=True);(OUT/'textures').mkdir(exist_ok=True);(OUT/'reports').mkdir(exist_ok=True)

def main():
    p=json.loads((FULL/'prepared_manifest.json').read_text(encoding='utf-8'));mats={m['name']:m for m in p['materials']};route=np.load(ROOT/'driving_test/route_geometry.npz')['center'];line=LineString(route[:,:2]);dtm=np.load(ROOT/'gis/region_terrain_5m.npz');z=dtm['z'];x0=float(dtm['x0'])-826000;y0=float(dtm['y0'])-833000;cell=float(dtm['cell'])
    def height(xy):
        fx=(xy[:,0]-x0)/cell;fy=(y0-xy[:,1])/cell;c=np.clip(fx.astype(int),0,z.shape[1]-2);r=np.clip(fy.astype(int),0,z.shape[0]-2);a=fx-c;b=fy-r
        return z[r,c]*(1-a)*(1-b)+z[r,c+1]*a*(1-b)+z[r+1,c]*(1-a)*b+z[r+1,c+1]*a*b
    building=[];cells=collections.defaultdict(list);cache={}
    for mesh in p['meshes']:
        if mesh['category']=='BUILDING':
            lo,hi=mesh['bounds_local'];building.append(box(lo[0]-2,lo[1]-2,hi[0]+2,hi[1]+2))
        if mesh['category'] not in ['GENERIC','VEGETATION(TB)']:continue
        with np.load(FULL/mesh['file']) as a:v=a['vertices'];uv=a['uv'];f=a['faces']
        centers=v[f].mean(axis=1);high=centers[:,2]-height(centers[:,:2])>2.8
        idx=np.flatnonzero(high)[::3]
        if not len(idx):continue
        file=mats[mesh['material']]['texture']
        if file not in cache:
            with Image.open(FULL/'textures'/file) as im:cache[file]=np.asarray(im.convert('RGB').resize((512,512)))
        image=cache[file];tuv=uv[f[idx]].mean(axis=1);px=np.clip((tuv[:,0]*511).astype(int),0,511);py=np.clip(((1-tuv[:,1])*511).astype(int),0,511);rgb=image[py,px].astype(float)
        green=(rgb[:,1]>rgb[:,0]*1.035)&(rgb[:,1]>rgb[:,2]*1.09)&(rgb[:,1]>24)&(rgb[:,0]<200)
        for xyz in centers[idx[green]][::2]:cells[tuple(np.floor(xyz[:2]/10).astype(int))].append(xyz)
    forbidden=shapely.union_all(building);candidates=[]
    for key,points in cells.items():
        if len(points)<3:continue
        points=np.asarray(points);xy=np.median(points[:,:2],axis=0);point=shapely.Point(xy);distance=line.distance(point)
        if not 18<distance<155 or forbidden.covers(point):continue
        candidates.append({'xy':xy.tolist(),'canopy_top_z_m':float(np.quantile(points[:,2],.88)),'source_samples':len(points),'distance_to_route_m':distance})
    candidates.sort(key=lambda r:(r['distance_to_route_m'],-r['source_samples']));selected=[];occupied=collections.defaultdict(list)
    for c in candidates:
        xy=np.asarray(c['xy']);key=tuple(np.floor(xy/10).astype(int))
        if any(np.linalg.norm(xy-q)<8.0 for dx in range(-1,2) for dy in range(-1,2) for q in occupied[(key[0]+dx,key[1]+dy)]):continue
        occupied[key].append(xy);selected.append(c)
        if len(selected)>=1200:break
    (OUT/'tree_locations.json').write_text(json.dumps(selected,indent=2),encoding='utf-8')
    rng=np.random.default_rng(20261114);size=1024
    def noise(scale):
        a=rng.normal(0,1,(scale,scale));a=(a-a.min())/(a.max()-a.min());return np.asarray(Image.fromarray(np.uint8(a*255)).resize((size,size),Image.Resampling.BICUBIC)).astype(float)/255-.5
    n=noise(1024)*8+noise(128)*5+noise(24)*7+noise(5)*7
    for name,color,amount in [('hk_test_asphalt.png',[58,60,61],1),('hk_test_concrete.png',[127,129,122],.65),('hk_test_ground.png',[61,78,45],1.25)]:
        Image.fromarray(np.uint8(np.clip(np.asarray(color)+n[:,:,None]*amount,0,255))).save(OUT/'textures'/name)
    for name,color in [('hk_test_white.png',(190,190,181)),('hk_test_yellow.png',(180,149,34))]:Image.new('RGB',(64,64),color).save(OUT/'textures'/name)
    atlas=Image.new('RGB',(512,256));draw=ImageDraw.Draw(atlas)
    colors=[(44,66,29),(52,77,31),(37,58,25),(64,82,35),(47,72,35),(58,75,28),(40,65,31),(64,86,42)]
    for i,col in enumerate(colors):
        x=i%4*128;y=i//4*128;draw.rectangle((x,y,x+127,y+127),fill=col);draw.line((x+64,y,x+64,y+128),fill=tuple(min(255,c+14) for c in col),width=2)
        for q in range(16,118,16):
            draw.line((x+64,y+q,x+5,y+q+18),fill=tuple(min(255,c+7) for c in col),width=1);draw.line((x+64,y+q,x+122,y+q+18),fill=tuple(min(255,c+7) for c in col),width=1)
    atlas.save(OUT/'textures/hk_native_leaf.png')
    b=np.asarray([74,62,45])+noise(128)[:,:,None]*25+noise(12)[:,:,None]*16;Image.fromarray(np.uint8(np.clip(b,0,255))).save(OUT/'textures/hk_native_bark.png')
    report={'tree_candidates':len(candidates),'selected_tree_locations':len(selected),'source_location_method':'green elevated source triangles; 10 m cells; 8 m minimum spacing; individual building exclusion','trees_are_authored_replacements_not_surveyed_species':True,'physical_meshes_to_change':0,'source_archives_to_change':0}
    (OUT/'reports/preparation.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
