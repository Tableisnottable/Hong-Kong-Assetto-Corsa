"""Blender background: build, export and render the solo driving-test track."""
from pathlib import Path
import sys,json,math,collections
import bpy,numpy as np
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from kn5_test_writer import export
BUILD=ROOT/'driving_test';TRACK='hk01_kam_tin_test';OUT=ROOT/'release/content/tracks'/TRACK
cfg=json.loads((ROOT/'project.json').read_text(encoding='utf-8'));OX=cfg['first_region']['origin_easting_m'];OY=cfg['first_region']['origin_northing_m']
route=np.load(BUILD/'route_geometry.npz');C=route['center'];N=route['normal'];T=route['tangent'];S=route['s'];DS=float(route['ds']);COUNT=len(C)
meta=json.loads((BUILD/'reports/route_build.json').read_text(encoding='utf-8'));surfaces=np.load(BUILD/'surfaces.npz');terrain=np.load(BUILD/'terrain_cut.npz')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene['track_id']=TRACK;scene['stage']='SOLO DRIVING TEST 0.1 — USER DRIVING VALIDATION PENDING';scene['horizontal_crs']='EPSG:2326';scene['origin_easting_m']=OX;scene['origin_northing_m']=OY
scene['source_attribution']='© OpenStreetMap contributors; Lands Department, HKSAR Government'
collections_by_name={}
def collection(name):
    if name not in collections_by_name:
        c=bpy.data.collections.new(name);scene.collection.children.link(c);collections_by_name[name]=c
    return collections_by_name[name]
materials=[];textures=[]
def mat(name,texture):
    m=bpy.data.materials.new(name);m.use_nodes=True
    im=bpy.data.images.load(str(BUILD/'textures'/texture),check_existing=True);im.pack()
    bs=m.node_tree.nodes.get('Principled BSDF');tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im;m.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=.9
    materials.append((name,texture));textures.append((texture,BUILD/'textures'/texture));return m
asphalt=mat('HK_TEST_ASPHALT','hk_test_asphalt.png');ground=mat('HK_TEST_GROUND','hk_test_ground.png');concrete=mat('HK_TEST_CONCRETE','hk_test_concrete.png');building=mat('HK_TEST_BUILDING','hk_test_building.png');white=mat('HK_TEST_WHITE','hk_test_white.png');yellow=mat('HK_TEST_YELLOW','hk_test_yellow.png');signmat=mat('HK_TEST_SIGN','hk_test_sign.png');chevron=mat('HK_TEST_CHEVRON','hk_test_chevron.png')
export_objects=[]
def mesh(name,v,f,material,group,uvscale=5,smooth=False):
    v=np.asarray(v,dtype=np.float32);f=np.asarray(f,dtype=np.int32)
    if not len(f):return None
    a=v[f[:,1]]-v[f[:,0]];b=v[f[:,2]]-v[f[:,0]];valid=np.linalg.norm(np.cross(a,b),axis=1)>.000001;f=f[valid]
    if not len(f):return None
    data=bpy.data.meshes.new(name);data.from_pydata(v.tolist(),[],f.tolist());data.update()
    ob=bpy.data.objects.new(name,data);collection(group).objects.link(ob);data.materials.append(material)
    uv=data.uv_layers.new(name='UVMap')
    for face in data.polygons:
        face.use_smooth=smooth
        for loop in face.loop_indices:
            p=v[data.loops[loop].vertex_index];uv.data[loop].uv=(p[0]/uvscale,p[1]/uvscale)
    ob['lodout']=8000;export_objects.append(ob);return ob

def tiled_mesh(prefix,v,f,material,group,tile=250,smooth=False):
    centers=v[f].mean(axis=1);keys=np.floor(centers[:,:2]/tile).astype(int);buckets=collections.defaultdict(list)
    for i,key in enumerate(keys):buckets[tuple(key)].append(i)
    for (x,y),ii in sorted(buckets.items()):
        ff=f[ii];used,index=np.unique(ff,return_inverse=True);mesh(f'{prefix}_E{x}_N{y}',v[used],index.reshape(-1,3),material,group,smooth=smooth)

for name,prefix,material in [('road','1ROAD',asphalt),('pit','1PITLANE',asphalt),('shoulder','1SHOULDER',concrete)]:
    tiled_mesh(prefix,surfaces[name+'_vertices'],surfaces[name+'_faces'],material,'01_DRIVABLE_SURFACES',tile=150,smooth=True)
tiled_mesh('1GRASS',terrain['vertices'],terrain['faces'],ground,'02_PHYSICAL_TERRAIN',tile=500,smooth=True)

for key in surfaces.files:
    if not key.startswith('wall_ring_'):continue
    pts=surfaces[key];vv=[];ff=[]
    # Closed 0.22 m-thick concrete test barriers, safely outside road edges.
    for i,p in enumerate(pts):
        tangent=pts[(i+1)%len(pts),:2]-pts[i-1,:2];tangent/=np.linalg.norm(tangent);n=np.array([-tangent[1],tangent[0]])*.11
        for z in (-.10,.75):
            for side in (-1,1):vv.append((p[0]+side*n[0],p[1]+side*n[1],p[2]+z))
    for i in range(len(pts)):
        a=i*4;b=((i+1)%len(pts))*4
        ff.extend([(a,b,b+2),(a,b+2,a+2),(a+1,a+3,b+3),(a+1,b+3,b+1),(a+2,b+2,b+3),(a+2,b+3,a+3)])
    tiled_mesh('1WALL_TEST_'+key,np.asarray(vv),np.asarray(ff),concrete,'03_TEST_SAFETY_BARRIERS',tile=150)

def at(s):
    u=(s%meta['length_m'])/DS;i=int(u)%COUNT;t=u-math.floor(u);j=(i+1)%COUNT
    c=C[i]*(1-t)+C[j]*t;v=T[i]*(1-t)+T[j]*t;v/=np.linalg.norm(v);n=np.array([-v[1],v[0]])
    return c,v,n
def strip(name,start,end,lateral,width,material):
    samples=max(2,int(math.ceil((end-start)/2))+1);vv=[]
    for s in np.linspace(start,end,samples):
        p,t,n=at(s)
        for off in (lateral-width/2,lateral+width/2):
            q=p.copy();q[:2]+=n*off;q[2]-=.055*min(abs(off)/3.5,1);q[2]+=.012;vv.append(q)
    ff=[]
    for i in range(samples-1):a=i*2;ff.extend([(a,a+2,a+3),(a,a+3,a+1)])
    ob=mesh(name,vv,ff,material,'04_VISUAL_MARKINGS',uvscale=5);ob['cast_shadows']=False

for j,s in enumerate(np.arange(105,meta['length_m'],12)):strip(f'LINE_CENTER_{j:03d}',s,min(s+4,meta['length_m']),0,.12,white)
for side in (-1,1):strip(f'LINE_EDGE_{side}',105,meta['length_m']+100,side*3.25,.11,white)
strip('PIT_BOUNDARY',20,80,3.5,.13,yellow)
def transverse_mark(s):
    p,t,n=at(s);vv=[]
    for a,b in ((-.22,-3.5),(.22,-3.5),(.22,3.5),(-.22,3.5)):
        q=p.copy();q[:2]+=t*a+n*b;q[2]-=.055*min(abs(b)/3.5,1);q[2]+=.014;vv.append(q)
    mesh('START_FINISH_STRIPE',vv,[(0,1,2),(0,2,3)],white,'04_VISUAL_MARKINGS')
transverse_mark(150)

# Retain only simplified context buildings clear of the driving corridor.
# Grid-based quick distance rejection avoids adding scenery over the test road.
building_data=json.loads((ROOT/'gis/region_buildings_grid.json').read_text(encoding='utf-8'))['buildings']
from mathutils.bvhtree import BVHTree
# Nearest road centre samples suffice for conservative scenery exclusion here.
groups=collections.defaultdict(lambda:[[],[]]);removed_buildings=0;included_buildings=0
for b in building_data:
    g=b['geometry'];polygons=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']] if g['type']=='Polygon' else []
    for rings in polygons:
        if len(rings)!=1:continue
        ring=np.asarray(rings[0][:-1],float);ring[:,:2]-=np.array([OX,OY])
        if len(ring)<3:continue
        mid=ring.mean(axis=0);dist2=((C[:,:2]-mid[:2])**2).sum(axis=1);nearest=int(dist2.argmin())
        size=float(np.linalg.norm(ring-mid,axis=1).max())
        if math.sqrt(float(dist2[nearest]))<size+18:removed_buildings+=1;continue
        if math.sqrt(float(dist2[nearest]))>500:continue
        tags=b['tags'];h=9
        try:h=float(tags.get('height',str(float(tags.get('building:levels','3'))*3)).replace(' m',''))
        except (ValueError,TypeError):pass
        h=min(80,max(3,h));rawz=float(C[nearest,2])-.3
        # Use source terrain from the saved foundation via a nearest terrain ray.
        xy=ring[:,:2];zbase=[]
        d=np.load(ROOT/'gis/region_terrain_5m.npz') if False else None
        # Terrain sample is loaded once below through a simple bilinear helper.
        if 'terrain_source' not in globals():
            terrain_source=np.load(ROOT/'gis/region_terrain_5m.npz');zz=terrain_source['z'];tx=float(terrain_source['x0']);ty=float(terrain_source['y0']);cell=float(terrain_source['cell'])
        for x,y in xy:
            fx=(x+OX-tx)/cell;fy=(ty-y-OY)/cell;cc=max(0,min(zz.shape[1]-2,int(fx)));rr=max(0,min(zz.shape[0]-2,int(fy)));aa=fx-cc;bb=fy-rr
            zbase.append(float(zz[rr,cc]*(1-aa)*(1-bb)+zz[rr,cc+1]*aa*(1-bb)+zz[rr+1,cc]*(1-aa)*bb+zz[rr+1,cc+1]*aa*bb))
        base=min(zbase)-.2;roof=max(zbase)+h
        area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,np.roll(ring,-1,axis=0)))
        if area<0:ring=ring[::-1]
        group=groups[(int(mid[0]//200),int(mid[1]//200))];v,f=group;offset=len(v);num=len(ring)
        v.extend((x,y,base) for x,y in ring);v.extend((x,y,roof) for x,y in ring)
        # Native Blender triangulation handles concave building roofs.
        from mathutils.geometry import tessellate_polygon
        rv=[Vector((float(x),float(y),roof)) for x,y in ring];mapping={tuple(p):i for i,p in enumerate(rv)}
        for tri in tessellate_polygon([rv]):f.append(tuple(offset+num+(p if isinstance(p,int) else mapping[tuple(p)]) for p in tri))
        for i in range(num):j=(i+1)%num;f.extend([(offset+i,offset+j,offset+j+num),(offset+i,offset+j+num,offset+i+num)])
        included_buildings+=1
for (x,y),(v,f) in groups.items():mesh(f'BUILDING_MASS_E{x}_N{y}',v,f,building,'05_SIMPLE_CONTEXT_BUILDINGS',uvscale=12)

def board(name,s,lateral,width=4,height=2,material=signmat):
    p,t,n=at(s);p[:2]+=n*lateral;p[2]+=.9
    vv=[]
    for side,z in ((-1,0),(1,0),(1,height),(-1,height)):
        q=p.copy();q[:2]+=n*width/2*side;q[2]+=z;vv.append(q)
    ob=mesh(name,vv,[(0,1,2),(0,2,3),(2,1,0),(3,2,0)],material,'06_TEST_ROUTE_SIGNS')
    # One rectangle uses explicit UVs in the native and exported scene.
    uv=ob.data.uv_layers.active
    front_uv=[(1,0),(0,0),(0,1),(1,1)];back_uv=[(0,0),(1,0),(1,1),(0,1)]
    for face in ob.data.polygons:
        coords=front_uv if face.normal.x*t[0]+face.normal.y*t[1]<0 else back_uv
        for li in face.loop_indices:uv.data[li].uv=coords[ob.data.loops[li].vertex_index]
    # Posts stand beside the route; collision is covered by outer barriers.
    return ob
board('TEST_START_INFORMATION',100,6.8)
for j,s in enumerate(np.arange(400,meta['length_m'],450)):board(f'CHEVRON_GUIDE_{j}',float(s),4.8,width=1.1,height=1.1,material=chevron)

dummies=[];spawn_info=[]
def special(name,s,lateral=0):
    p,t,n=at(s);p[:2]+=n*lateral;p[2]-=.055*min(abs(lateral)/3.5,1);p[2]+=.03
    dx,dz=float(t[0]),float(-t[1]);px,py,pz=float(p[0]),float(p[2]),float(-p[1])
    matrix=(dz,0,-dx,0,0,1,0,0,dx,0,dz,0,px,py,pz,1)
    dummies.append((name,matrix));ob=bpy.data.objects.new(name,None);collection('07_AC_SPAWN_AND_TIMING').objects.link(ob);ob.location=p;ob.rotation_euler=Vector((t[0],t[1],0)).to_track_quat('-Y','Z').to_euler();ob.empty_display_type='ARROWS';ob.empty_display_size=2;ob['ac_matrix']=list(matrix)
    spawn_info.append({'name':name,'route_distance_m':s,'lateral_m':lateral,'blender_position':p.tolist(),'ac_position':[px,py,pz],'ac_forward':[dx,0,dz]})
special('AC_PIT_0',45,6)
special('AC_START_0',140,1.6)
special('AC_HOTLAP_START_0',110,1.6)
for gate,sample in enumerate(meta['timing_samples']):
    for side,off in [('L',4.0),('R',-4.0)]:special(f'AC_TIME_{gate}_{side}',float(sample)*DS,off)
special('AC_CREW_0',45,8)

report=export(OUT/(TRACK+'.kn5'),export_objects,materials,textures,dummies)
report['spawn_and_timing_nodes']=spawn_info;report['simple_context_buildings']=included_buildings;report['buildings_excluded_near_route']=removed_buildings
(BUILD/'reports/kn5_export.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

# Independent geometric checks on the exact scene sent to the binary writer.
from mathutils.bvhtree import BVHTree
physics=[o for o in export_objects if o.name.startswith(('1ROAD','1PITLANE','1SHOULDER'))]
vv=[];ff=[]
for ob in physics:
    base=len(vv);vv.extend(tuple(v.co) for v in ob.data.vertices);ff.extend(tuple(base+i for i in p.vertices) for p in ob.data.polygons)
tree=BVHTree.FromPolygons(vv,ff,all_triangles=True)
hits=[];errors=[]
for spec in spawn_info:
    if not spec['name'].startswith(('AC_PIT','AC_START','AC_HOTLAP')):continue
    p=np.asarray(spec['blender_position']);fwd=np.asarray(spec['ac_forward'])[[0,2]]*np.array([1,-1]);side=np.array([-fwd[1],fwd[0]])
    wheel=[]
    for longitudinal in (-1.5,1.5):
        for lateral in (-.9,.9):
            q=p.copy();q[:2]+=fwd*longitudinal+side*lateral;hit,norm,idx,dist=tree.ray_cast(Vector((q[0],q[1],q[2]+3)),Vector((0,0,-1)),8)
            if hit is None or norm.z<.8:errors.append(f'{spec["name"]} missing or steep wheel support')
            wheel.append({'hit':None if hit is None else list(hit),'up_normal':None if norm is None else norm.z})
    hits.append({'node':spec['name'],'wheel_support':wheel})
samples=[]
for i,p in enumerate(C):
    hit,norm,idx,dist=tree.ray_cast(Vector((p[0],p[1],p[2]+2)),Vector((0,0,-1)),5)
    if hit is None:errors.append(f'Route sample {i} has no collision')
    elif abs(hit.z-p[2])>.10 or norm.z<.85:errors.append(f'Route sample {i} collision mismatch or steep normal')
validation={'passed':not errors,'errors':errors,'route_samples_with_surface_check':len(C),'spawn_checks':hits,'validation_scope':'scene collision ray tests and tyre-footprint support; user must still run game driving test'}
(BUILD/'reports/scene_collision_verification.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
if errors:raise RuntimeError('Collision validation failed: '+str(errors[:5]))

# Save an editable test scene in addition to the installable package.
camdata=bpy.data.cameras.new('Test_Loop_Overview');cam=bpy.data.objects.new('Test_Loop_Overview',camdata);scene.collection.objects.link(cam);target=Vector((float(C[:,0].mean()),float(C[:,1].mean()),15));cam.location=target+Vector((1200,-1550,1550));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=2350;camdata.clip_end=15000;scene.camera=cam
ld=bpy.data.lights.new('Sun','SUN');ld.energy=3;ld.angle=.15;lo=bpy.data.objects.new('Sun',ld);scene.collection.objects.link(lo);lo.rotation_euler=(.5,-.4,-.5)
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.6,.7,.8,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.7
scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='MATERIAL';scene.view_settings.view_transform='AgX'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.clip_end=15000;area.spaces.active.region_3d.view_location=target;area.spaces.active.region_3d.view_distance=1900
readme=bpy.data.texts.new('TEST_TRACK_README.txt');readme.write('Kam Tin Driving Test 0.1\nSolo Practice, one car. Approximate 3.5 km road loop.\nSynthetic 7m test width, smoothed elevation, safety barriers, simple scenery.\nThis is the editable scene behind release/content/tracks/hk01_kam_tin_test.\nGeometric and binary validation passed; actual user driving test pending.\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/HK01_KamTin_DRIVING_TEST.blend'),compress=True)
scene.render.engine='CYCLES';scene.cycles.samples=20;scene.render.filepath=str(BUILD/'reports/test_track_overview.png');bpy.ops.render.render(write_still=True)
p,t,n=at(43);cam.location=Vector(p)+Vector((t[0],t[1],0))*-12+Vector((0,0,7));target=Vector(p)+Vector((t[0],t[1],0))*28;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='PERSP';camdata.lens=32;scene.render.filepath=str(BUILD/'reports/test_track_start.png');bpy.ops.render.render(write_still=True)
print('TEST_BUILD_COMPLETE',json.dumps({k:v for k,v in report.items() if k!='nodes'}),flush=True)
