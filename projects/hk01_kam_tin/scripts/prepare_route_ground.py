"""Prepare a visual underlay and complete source-terrain reference for the loop."""
from pathlib import Path
import sys,json,collections
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parents[1]/'work/python_deps'))
import numpy as np,shapely
from shapely.geometry import box,LineString
from prepare_csdi_scenery import primitives,SOURCE
from PIL import Image,ImageDraw,ImageFont
OUT=ROOT/'driving_test/route_scenery'

def main():
    manifest=json.loads((OUT/'source_manifest.json').read_text());rectangles=[];reference_v=[];reference_f=[]
    for record in manifest['sheets']:
        bounds=[v-o for v,o in zip(record['bounds_epsg2326'],[826000,833000,826000,833000])];rectangles.append(box(*bounds))
        for path in sorted((SOURCE/record['sheet']/'TERRAIN(TB)').rglob('*.gltf')):
            for _,_,v,uv,f in primitives(path):
                base=sum(len(a) for a in reference_v);reference_v.append(v);reference_f.append(f+base)
    union=shapely.union_all(rectangles);route=np.load(ROOT/'driving_test/route_geometry.npz')['center'];line=LineString(route[:,:2])
    uncovered=int((~shapely.covers(union.buffer(.1),shapely.points(route[:,:2]))).sum())
    if uncovered:raise RuntimeError('Route coverage gap: '+str(uncovered))
    keep=box(-10000,-10000,10000,10000).difference(union).union(line.buffer(20,join_style=2))
    shapely.prepare(keep)
    terrain=np.load(ROOT/'driving_test/terrain_cut.npz');v=terrain['vertices'];f=terrain['faces'];tri=shapely.polygons(v[f,:2]);inside=shapely.covers(keep,tri);partial=shapely.intersects(keep,tri)&~inside
    vv=[];ff=[]
    for face in f[inside]:
        start=len(vv);vv.extend(v[face].tolist());ff.append((start,start+1,start+2))
    for face in f[partial]:
        p=v[face];intersection=shapely.Polygon(p[:,:2]).intersection(keep)
        for polygon in shapely.get_parts(shapely.constrained_delaunay_triangles(intersection)):
            if polygon.is_empty:continue
            xy=np.asarray(polygon.exterior.coords)[:-1,:2]
            if len(xy)!=3:continue
            ab=np.column_stack((p[1,:2]-p[0,:2],p[2,:2]-p[0,:2]))
            bary=np.linalg.solve(ab,(xy-p[0,:2]).T).T;z=p[0,2]+bary[:,0]*(p[1,2]-p[0,2])+bary[:,1]*(p[2,2]-p[0,2]);xyz=np.column_stack((xy,z))
            if np.linalg.det(np.column_stack((xy[1]-xy[0],xy[2]-xy[0])))<0:xyz=xyz[[0,2,1]]
            start=len(vv);vv.extend(xyz.tolist());ff.append((start,start+1,start+2))
    np.savez_compressed(OUT/'visible_ground.npz',vertices=np.asarray(vv,dtype=np.float32),faces=np.asarray(ff,dtype=np.int32))
    np.savez_compressed(OUT/'source_terrain_reference.npz',vertices=np.vstack(reference_v).astype(np.float32),faces=np.vstack(reference_f).astype(np.int32))
    coverage={'covered_route_samples':len(route),'total_route_samples':len(route),'uncovered_route_samples':uncovered,'route_coverage_percent':100.,'source_union_geometry':shapely.geometry.mapping(union),'source_sheet_count':len(rectangles),'source_terrain_triangles':sum(len(a) for a in reference_f),'visible_ground_triangles':len(ff),'temporary_visual_blend':'20 m protected ground underlay; road collision unchanged'}
    (OUT/'coverage.json').write_text(json.dumps(coverage,indent=2),encoding='utf-8')
    # Clear, attributed board for the user's test build.
    im=Image.new('RGB',(1536,768),(20,66,49));d=ImageDraw.Draw(im)
    d.rounded_rectangle((20,20,1516,748),20,outline=(230,236,216),width=10)
    def text(y,t,size,color=(245,245,225)):d.text((65,y),t,font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',size),fill=color)
    text(45,'KAM TIN',110);text(175,'FULL LOOP TEST 0.3',78);text(300,'KEEP LEFT / SOLO PRACTICE',58,(255,216,80));text(398,'3.445 km loop / 8 source scenery tiles',37)
    with Image.open(SOURCE/'landsd_logo_fb.jpg') as logo:
        logo=logo.convert('RGB');logo.thumbnail((365,220));im.paste(logo,(70,490))
    d.text((475,505),'Map from Lands Department',font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',34),fill=(245,245,225))
    d.text((475,554),'© Government of the Hong Kong SAR',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',29),fill=(245,245,225))
    d.text((475,600),'3d.map.gov.hk | Source ownership retained',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',27),fill=(245,245,225))
    d.text((475,645),'Roads: © OpenStreetMap contributors',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',27),fill=(245,245,225))
    im.save(OUT/'textures/route_test_sign.png')
    # Eight synthetic route markers make user-reported faults easy to locate.
    atlas=Image.new('RGB',(1024,512),(14,57,91));draw=ImageDraw.Draw(atlas)
    marker_data=[];length=float(json.loads((ROOT/'driving_test/reports/route_build.json').read_text())['length_m'])
    for cp in range(8):
        x=(cp%4)*256;y=(cp//4)*256
        draw.rounded_rectangle((x+8,y+8,x+248,y+248),16,fill=(18,69,105),outline='white',width=7)
        draw.text((x+30,y+20),'TEST POINT',font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',25),fill='white')
        draw.text((x+55,y+49),str(cp+1),font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',115),fill=(255,226,87))
        draw.text((x+42,y+195),'OF 8 / KEEP LEFT',font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',18),fill='white')
        distance=(150+cp*length/8)%length;index=int(round(distance/length*len(route)))%len(route)
        marker_data.append({'checkpoint':cp+1,'route_distance_m':distance,'route_sample':index,'local_xyz_m':route[index].tolist()})
    atlas.save(OUT/'textures/test_checkpoint_atlas.png');(OUT/'checkpoints.json').write_text(json.dumps(marker_data,indent=2))
    guide=Image.new('RGB',(1100,1500),(242,245,241));d=ImageDraw.Draw(guide)
    lo=route[:,:2].min(axis=0)-90;hi=route[:,:2].max(axis=0)+90;scale=min(900/(hi[0]-lo[0]),1180/(hi[1]-lo[1]))
    def project(p):return (int(100+(p[0]-lo[0])*scale),int(150+(hi[1]-p[1])*scale))
    d.text((55,30),'KAM TIN / FULL LOOP TEST 0.3',font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',40),fill=(15,55,45))
    d.text((57,87),'3.445 km | 8 checkpoints | solo Practice | north up',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',23),fill=(50,70,65))
    path=[project(p) for p in route];path.append(path[0]);d.line(path,fill=(70,80,76),width=18,joint='curve');d.line(path,fill=(240,235,218),width=3,joint='curve')
    for marker in marker_data:
        x,y=project(marker['local_xyz_m']);d.ellipse((x-23,y-23,x+23,y+23),fill=(18,69,105),outline='white',width=3)
        d.text((x-10,y-20),str(marker['checkpoint']),font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',28),fill='white')
    pit=route[int(round(45/length*len(route)))];x,y=project(pit);d.rectangle((x-8,y-8,x+8,y+8),fill=(30,145,86));d.text((x+16,y-5),'PITS',font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',20),fill=(15,85,50))
    d.text((55,1380),'Report the nearest checkpoint, direction, and what happened.',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',23),fill=(30,55,45))
    d.text((55,1420),'Road reference © OpenStreetMap contributors | test markers are synthetic.',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18),fill=(55,65,60))
    guide.save(OUT/'TEST_ROUTE_GUIDE.png')
    print(json.dumps({k:v for k,v in coverage.items() if k!='source_union_geometry'},indent=2))

if __name__=='__main__':main()
