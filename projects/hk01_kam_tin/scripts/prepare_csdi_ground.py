"""Cut a visual ground underlay; retain original physical ground unchanged."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parents[1]/'work/python_deps'))
import numpy as np
import shapely
from shapely.geometry import box,LineString
from PIL import Image,ImageDraw,ImageFont
from prepare_csdi_scenery import primitives,SOURCE,SHEET
OUT=ROOT/'driving_test/csdi_sample'
tile=box(-1250,-600,-500,0)
route=np.load(ROOT/'driving_test/route_geometry.npz')['center']
keep=box(-10000,-10000,10000,10000).difference(tile).union(LineString(route[:,:2]).buffer(42,join_style=2))
shapely.prepare(keep)
terrain=np.load(ROOT/'driving_test/terrain_cut.npz');v=terrain['vertices'];f=terrain['faces']
tri=shapely.polygons(v[f,:2]);inside=shapely.covers(keep,tri);partial=shapely.intersects(keep,tri)&~inside
vv=[];ff=[]
for face in f[inside]:
    start=len(vv);vv.extend(v[face].tolist());ff.append((start,start+1,start+2))
for face in f[partial]:
    p=v[face];intersection=shapely.Polygon(p[:,:2]).intersection(keep)
    parts=shapely.get_parts(shapely.constrained_delaunay_triangles(intersection))
    for polygon in parts:
        if polygon.is_empty:continue
        xy=np.asarray(polygon.exterior.coords)[:-1,:2]
        if len(xy)!=3:continue
        ab=np.column_stack((p[1,:2]-p[0,:2],p[2,:2]-p[0,:2]))
        bary=np.linalg.solve(ab,(xy-p[0,:2]).T).T
        z=p[0,2]+bary[:,0]*(p[1,2]-p[0,2])+bary[:,1]*(p[2,2]-p[0,2])
        xyz=np.column_stack((xy,z))
        if np.linalg.det(np.column_stack((xy[1]-xy[0],xy[2]-xy[0])))<0:xyz=xyz[[0,2,1]]
        start=len(vv);vv.extend(xyz.tolist());ff.append((start,start+1,start+2))
np.savez_compressed(OUT/'visible_ground.npz',vertices=np.asarray(vv,dtype=np.float32),faces=np.asarray(ff,dtype=np.int32))
p=next((SOURCE/SHEET/'TERRAIN(TB)').rglob('*.gltf'));j,pr,rv,uv,rf=next(primitives(p))
np.savez_compressed(OUT/'source_terrain_reference.npz',vertices=rv.astype(np.float32),faces=rf)

# Source credit is visible in the game at the start information board.
im=Image.new('RGB',(1536,768),(20,66,49));d=ImageDraw.Draw(im)
d.rounded_rectangle((20,20,1516,748),20,outline=(230,236,216),width=10)
def text(y,t,size,color=(245,245,225)):d.text((65,y),t,font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',size),fill=color)
text(50,'KAM TIN',110);text(185,'DRIVING TEST 0.2',82);text(310,'KEEP LEFT / SOLO PRACTICE',58,(255,216,80))
text(405,'Real scenery sample: 750 x 600 m',38)
with Image.open(SOURCE/'landsd_logo_fb.jpg') as logo:
    logo=logo.convert('RGB');logo.thumbnail((365,220),Image.Resampling.LANCZOS);im.paste(logo,(70,490))
d.text((475,500),'Map from Lands Department',font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',34),fill=(245,245,225))
d.text((475,550),'© Government of the Hong Kong SAR',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',29),fill=(245,245,225))
d.text((475,595),'3d.map.gov.hk  |  Source data ownership retained',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',27),fill=(245,245,225))
d.text((475,640),'Road reference: © OpenStreetMap contributors',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',27),fill=(245,245,225))
im.save(OUT/'textures/csdi_test_sign.png')
print(json.dumps({'visible_ground_triangles':len(ff),'original_physical_ground_triangles':len(f),'source_terrain_triangles':len(rf)}))
