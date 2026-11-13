"""Prepare a small continuous driving-test loop from retained OSM/DTM data.
The geometry is a deliberately simplified greybox, not surveyed road detail.
"""
from pathlib import Path
import json,math,sys,shutil
ROOT=Path(__file__).resolve().parents[1]
deps=ROOT.parents[1]/'work/python_deps'
if deps.exists():sys.path.insert(0,str(deps))
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import LineString,Polygon,box,Point
from shapely import constrained_delaunay_triangles,prepare,points,line_locate_point,distance
sys.stdout.reconfigure(encoding='utf-8')
CFG=json.loads((ROOT/'project.json').read_text(encoding='utf-8'));R=CFG['first_region']
OX,OY=R['origin_easting_m'],R['origin_northing_m']
BUILD=ROOT/'driving_test';BUILD.mkdir(exist_ok=True)
for name in ('textures','reports','source'):(BUILD/name).mkdir(exist_ok=True)
source=BUILD/'source/test_loop_source.json'
if not source.exists():shutil.copy2(ROOT.parents[1]/'work/test_loop_candidate.json',source)
src=json.loads(source.read_text(encoding='utf-8'));xy=np.asarray(src['xy'][:-1],float)
dtm=np.load(ROOT/'gis/region_terrain_5m.npz');ZZ=dtm['z'];tx,ty,cell=float(dtm['x0']),float(dtm['y0']),float(dtm['cell'])

def dtm_height(p):
    p=np.asarray(p);fx=(p[...,0]-tx)/cell;fy=(ty-p[...,1])/cell
    c=np.clip(np.floor(fx).astype(int),0,ZZ.shape[1]-2);r=np.clip(np.floor(fy).astype(int),0,ZZ.shape[0]-2)
    a=fx-c;b=fy-r
    return ZZ[r,c]*(1-a)*(1-b)+ZZ[r,c+1]*a*(1-b)+ZZ[r+1,c]*(1-a)*b+ZZ[r+1,c+1]*a*b

def fillet(points,radius=14):
    """Round OSM polyline bends locally while retaining the route's metre scale."""
    out=[]
    for i,p in enumerate(points):
        a=points[i-1];b=points[(i+1)%len(points)];u=p-a;v=b-p;la=np.linalg.norm(u);lb=np.linalg.norm(v);u/=la;v/=lb
        turn=math.atan2(u[0]*v[1]-u[1]*v[0],np.dot(u,v))
        if abs(turn)<.025 or abs(turn)>2.7:out.append(p);continue
        d=min(radius*math.tan(abs(turn)/2),la*.42,lb*.42);rad=d/math.tan(abs(turn)/2)
        start=p-u*d;end=p+v*d;normal=np.array([-u[1],u[0]])*np.sign(turn);center=start+normal*rad
        angle=math.atan2(start[1]-center[1],start[0]-center[0]);n=max(2,int(math.ceil(rad*abs(turn)/.8)))
        out.extend(center+rad*np.array([math.cos(angle+turn*j/n),math.sin(angle+turn*j/n)]) for j in range(n+1))
    return np.asarray(out)

simple=LineString(np.vstack((xy,xy[0]))).simplify(1.5,preserve_topology=True)
smooth=fillet(np.asarray(simple.coords)[:-1])
line=LineString(np.vstack((smooth,smooth[0])))
if not line.is_simple:raise RuntimeError('Smoothed loop crosses itself')
length=line.length;n=int(math.ceil(length/2));ds=length/n
# Put the pit bay around the source agent's recommended long straight.
target=Point(src['recommended_start']['interpolated_xy']);start=(line.project(target)-45)%length
dist=(start+np.arange(n)*ds)%length
center=np.asarray([[line.interpolate(float(d)).x,line.interpolate(float(d)).y] for d in dist])
tangent=np.roll(center,-1,axis=0)-np.roll(center,1,axis=0);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
normal=np.column_stack((-tangent[:,1],tangent[:,0]))
# Smooth the dated 5 m DTM along the loop to remove non-road terrain noise.
raw=dtm_height(center);sigma=22/ds;radius=int(math.ceil(4*sigma));kernel=np.exp(-.5*(np.arange(-radius,radius+1)/sigma)**2);kernel/=kernel.sum()
height=sum(w*np.roll(raw,k) for k,w in zip(range(-radius,radius+1),kernel))+.30
grade=(np.roll(height,-1)-np.roll(height,1))/(2*ds)
turn=np.arccos(np.clip(np.sum(tangent*np.roll(tangent,-1,axis=0),axis=1),-1,1));curvature=turn/ds
def ease(a):a=np.clip(a,0,1);return a*a*(3-2*a)
s=np.arange(n)*ds;pit_extra=5*ease(s/20)*ease((100-s)/20)
trackline=LineString(np.vstack((center,center[0])))
main_asphalt=trackline.buffer(3.5,quad_segs=6)
# Separate pit apron on the left of a straight. Its merge tapers are synthetic
# test infrastructure and do not represent the actual public-road junction.
mask=(s>=0)&(s<=100);right_pit=center[mask]+normal[mask]*3.25
left_pit=center[mask]+normal[mask]*(3.5+pit_extra[mask])[:,None]
pit_poly=Polygon(np.vstack((right_pit,left_pit[::-1]))).buffer(.05)
asphalt=main_asphalt.union(pit_poly)
pit_poly=asphalt.difference(main_asphalt)
footprint=asphalt.buffer(4.5,quad_segs=6)
if not footprint.is_valid or footprint.geom_type!='Polygon':raise RuntimeError('Road corridor is not a valid single ring')
prepare(footprint)

# Original 20 m terrain is cut away under the entire driving corridor.
# The corridor's outer vertices sample these same planar triangles.
xmin,ymin,xmax,ymax=R['bounds_epsg2326'];step=20;nx=(xmax-xmin)//step+1;ny=(ymax-ymin)//step+1
gx=np.arange(xmin,xmax+1,step);gy=np.arange(ymin,ymax+1,step)
terrain_z=dtm_height(np.stack(np.meshgrid(gx,gy),axis=-1))
def mesh_height(p):
    p=np.asarray(p);fx=(p[...,0]-xmin)/step;fy=(p[...,1]-ymin)/step
    c=np.clip(np.floor(fx).astype(int),0,nx-2);r=np.clip(np.floor(fy).astype(int),0,ny-2);a=np.clip(fx-c,0,1);b=np.clip(fy-r,0,1)
    z00=terrain_z[r,c];z10=terrain_z[r,c+1];z01=terrain_z[r+1,c];z11=terrain_z[r+1,c+1]
    return np.where(a>=b,z00*(1-a)+z10*(a-b)+z11*b,z00*(1-b)+z11*a+z01*(b-a))

def road_z(p):
    p=np.asarray(p);q=points(p[:,0],p[:,1]);loc=(line_locate_point(line,q)-start)%length
    hh=np.interp(loc,s,height,period=length);dd=distance(trackline,q)
    return hh-.055*np.minimum(dd/3.5,1)

def shoulder_z(p):
    p=np.asarray(p);q=points(p[:,0],p[:,1]);da=distance(asphalt,q);df=distance(footprint.boundary,q)
    a=np.clip(da/np.maximum(da+df,1e-8),0,1)
    return road_z(p)*(1-a)+mesh_height(p)*a

def polygon_mesh(poly,zfun,spacing=4):
    prepare(poly);vv=[];ff=[]
    ax,ay,bx,by=poly.bounds
    for x in np.arange(math.floor(ax/spacing)*spacing,bx,spacing):
        for y in np.arange(math.floor(ay/spacing)*spacing,by,spacing):
            cellpoly=box(x,y,x+spacing,y+spacing)
            if not poly.intersects(cellpoly):continue
            g=poly.intersection(cellpoly)
            if g.area<1e-7:continue
            for tri in constrained_delaunay_triangles(g).geoms:
                if tri.area<1e-7:continue
                p=np.asarray(tri.exterior.coords)[:-1];base=len(vv);z=zfun(p)
                vv.extend(zip(p[:,0]-OX,p[:,1]-OY,z))
                area=(p[1,0]-p[0,0])*(p[2,1]-p[0,1])-(p[1,1]-p[0,1])*(p[2,0]-p[0,0])
                ff.append((base,base+1,base+2) if area>0 else (base,base+2,base+1))
    return np.asarray(vv,dtype=np.float32),np.asarray(ff,dtype=np.int32)

surface_arrays={}
for name,poly,zfun in [('road',main_asphalt,road_z),('pit',pit_poly,road_z),('shoulder',footprint.difference(asphalt),shoulder_z)]:
    print('Meshing '+name,flush=True)
    vv,ff=polygon_mesh(poly,zfun);surface_arrays[name+'_vertices']=vv;surface_arrays[name+'_faces']=ff
wallpoly=asphalt.buffer(1.4,quad_segs=4)
wallrings=[np.asarray(wallpoly.exterior.coords)]+[np.asarray(r.coords) for r in wallpoly.interiors]
for i,ring in enumerate(wallrings):
    ringline=LineString(ring);count=int(math.ceil(ringline.length/3));dswall=ringline.length/count
    p=np.asarray([[ringline.interpolate(j*dswall).x,ringline.interpolate(j*dswall).y] for j in range(count)])
    z=shoulder_z(p);surface_arrays[f'wall_ring_{i}']=np.column_stack((p[:,0]-OX,p[:,1]-OY,z))
np.savez_compressed(BUILD/'surfaces.npz',**surface_arrays)
np.savez_compressed(BUILD/'route_geometry.npz',center=np.column_stack((center[:,0]-OX,center[:,1]-OY,height)),normal=normal,tangent=tangent,s=s,ds=ds,pit_extra=pit_extra)
from shapely.geometry import mapping
(BUILD/'source/corridor_epsg2326.geojson').write_text(json.dumps(mapping(footprint)),encoding='utf-8')

terrain_vertices=[];terrain_faces=[];cut_cells=0
for iy,y in enumerate(gy[:-1]):
    if iy%50==0:print(f'Terrain row {iy}/{ny-1}',flush=True)
    for ix,x in enumerate(gx[:-1]):
        for coords in (((x,y),(x+step,y),(x+step,y+step)),((x,y),(x+step,y+step),(x,y+step))):
            tri=Polygon(coords)
            if footprint.intersects(tri):
                diff=tri.difference(footprint)
                if diff.is_empty:continue
                tris=constrained_delaunay_triangles(diff)
                pieces=[list(g.exterior.coords)[:-1] for g in tris.geoms if g.area>1e-7]
                cut_cells+=1
            else:pieces=[coords]
            for pp in pieces:
                pp=np.asarray(pp);base=len(terrain_vertices);z=mesh_height(pp)
                terrain_vertices.extend(zip(pp[:,0]-OX,pp[:,1]-OY,z))
                # Constrained triangulation can return clockwise rings.
                area=(pp[1,0]-pp[0,0])*(pp[2,1]-pp[0,1])-(pp[1,1]-pp[0,1])*(pp[2,0]-pp[0,0])
                terrain_faces.append((base,base+1,base+2) if area>0 else (base,base+2,base+1))
np.savez_compressed(BUILD/'terrain_cut.npz',vertices=np.asarray(terrain_vertices,dtype=np.float32),faces=np.asarray(terrain_faces,dtype=np.int32))

# New procedural textures; no prior track assets are copied.
rng=np.random.default_rng(134)
def noise_texture(name,base,amount,size=512):
    noise=rng.normal(0,amount,(size,size,1));rgb=np.clip(np.asarray(base)[None,None,:]+noise,0,255).astype('uint8');Image.fromarray(rgb).save(BUILD/'textures'/name)
noise_texture('hk_test_asphalt.png',(69,72,73),5)
noise_texture('hk_test_ground.png',(83,103,70),8)
noise_texture('hk_test_concrete.png',(174,176,161),5)
noise_texture('hk_test_building.png',(166,165,151),2,256)
Image.new('RGB',(32,32),(236,235,212)).save(BUILD/'textures/hk_test_white.png')
Image.new('RGB',(32,32),(242,167,47)).save(BUILD/'textures/hk_test_yellow.png')
im=Image.open(BUILD/'textures/hk_test_building.png');d=ImageDraw.Draw(im)
for y in range(22,256,48):
    for x in range(18,256,52):d.rectangle((x,y,x+24,y+25),fill=(77,95,101));d.line((x+12,y,x+12,y+25),fill=(135,141,135),width=2)
im.save(BUILD/'textures/hk_test_building.png')
font='C:/Windows/Fonts/segoeuib.ttf';sign=Image.new('RGB',(1024,512),(21,69,48));d=ImageDraw.Draw(sign)
d.rounded_rectangle((15,15,1008,496),radius=22,outline=(230,239,221),width=10)
d.text((55,43),'KAM TIN',font=ImageFont.truetype(font,100),fill=(245,246,231))
d.text((55,160),'DRIVING TEST',font=ImageFont.truetype(font,75),fill=(245,246,231))
d.text((55,280),'KEEP LEFT',font=ImageFont.truetype(font,66),fill=(255,206,88))
d.text((55,395),'GREYBOX 0.1  /  SOLO PRACTICE',font=ImageFont.truetype(font,34),fill=(230,239,221))
sign.save(BUILD/'textures/hk_test_sign.png')
chev=Image.new('RGB',(256,256),(235,192,55));d=ImageDraw.Draw(chev);d.polygon([(40,20),(100,20),(220,128),(100,236),(40,236),(160,128)],fill=(30,35,34));chev.save(BUILD/'textures/hk_test_chevron.png')

# Package metadata and maps are derived from exactly this generated loop.
TRACK='hk01_kam_tin_test';package=ROOT/'release/content/tracks'/TRACK
for name in ('data','ui'):(package/name).mkdir(parents=True,exist_ok=True)
route_local=center-np.array([OX,OY]);mins=route_local.min(axis=0)-70;maxs=route_local.max(axis=0)+70
W,H=512,1024;scale=min((W-32)/(maxs[0]-mins[0]),(H-32)/(maxs[1]-mins[1]));cx=(mins[0]+maxs[0])/2;cy=(mins[1]+maxs[1])/2
def mappt(p):return (W/2+(p[0]-cx)*scale,H/2-(p[1]-cy)*scale)
mapimg=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(mapimg)
d.line([mappt(p) for p in np.vstack((route_local,route_local[0]))],fill=(255,255,255,255),width=8)
mapimg.save(package/'map.png')
testmap=Image.new('RGB',(W,H),(24,37,45));testmap.paste(mapimg,(0,0),mapimg)
d=ImageDraw.Draw(testmap);d.text((22,22),'KAM TIN TEST LOOP',font=ImageFont.truetype(font,26),fill=(236,239,224))
for idx in range(0,n,max(1,n//12)):
    p=np.asarray(mappt(route_local[idx]));v=tangent[idx]*np.array([1,-1]);q=p+v*12;side=np.array([-v[1],v[0]])
    d.polygon([tuple(q),tuple(p-v*7+side*6),tuple(p-v*7-side*6)],fill=(118,218,191))
p=mappt(route_local[int(45/ds)]);d.ellipse((p[0]-7,p[1]-7,p[0]+7,p[1]+7),fill=(249,191,67));testmap.save(BUILD/'reports/test_route_map.png')
one_over_scale=1/scale
mapini=f'[PARAMETERS]\nWIDTH={W}\nHEIGHT={H}\nMARGIN=0\nSCALE_FACTOR={one_over_scale:.9f}\nMAX_SIZE={H}\nX_OFFSET={W/(2*scale)-cx:.9f}\nZ_OFFSET={H/(2*scale)+cy:.9f}\nDRAWING_SIZE=10\n'
(package/'data/map.ini').write_text(mapini,encoding='ascii')
ui={'name':'Hong Kong — Kam Tin Driving Test','description':f'Solo driving greybox v0.1. {length/1000:.2f} km loop following Kam Po, Shek Tin, Kam Sheung and Tung Wui roads. Approximate smoothed heights, temporary 7 m road width, test barriers and simplified scenery. Practice mode, one car. No AI traffic. © OpenStreetMap contributors; terrain: Lands Department HKSAR Government.','tags':['Hong Kong','real location','test','freeroam'],'geotags':['22.430','114.071'],'country':'Hong Kong','city':'Kam Tin','length':f'{length:.0f} m','width':'7 m test surface','pitboxes':'1','run':'clockwise' if Polygon(center).exterior.is_ccw is False else 'counter-clockwise','author':'HK 1:1 Project','version':'0.1-test','url':''}
(package/'ui/ui_track.json').write_text(json.dumps(ui,ensure_ascii=False,indent=2),encoding='utf-8')
meta={'track_id':TRACK,'display_name':ui['name'],'length_m':length,'sample_spacing_m':ds,'samples':n,'source_length_m':src['length_m'],'road_width_m':7,'standardized_width_is_temporary':True,'elevation_min_m':float(height.min()),'elevation_max_m':float(height.max()),'max_longitudinal_grade_percent':float(np.max(np.abs(grade))*100),'minimum_centerline_turn_radius_estimate_m':float(1/max(curvature.max(),1e-8)),'road_footprint_valid':footprint.is_valid,'terrain_triangles':len(terrain_faces),'terrain_clipped_triangles':cut_cells,'pit_spawn_sample':int(45/ds),'start_sample':int(140/ds),'hotlap_sample':int(110/ds),'timing_samples':[int((150+k*length/3)/ds)%n for k in range(3)],'data_sources':['OpenStreetMap Geofabrik Hong Kong extract 2026-11-12T21:23:05Z','Lands Department 5m DTM, historical terrain data'],'limitations':['Approximate greybox widths, smooth test profile and synthetic safety barriers; not finished real-world scenery.','Only selected loop is open for this test; other road references are excluded.','No driving AI or traffic; use solo Practice.','User will perform the actual game driving test.']}
(BUILD/'reports/route_build.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
print(json.dumps(meta,indent=2),flush=True)
