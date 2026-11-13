"""Replace raised photo-mesh residuals with source-positioned authored trees."""
from pathlib import Path
import sys,json,math,hashlib,collections
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from kn5_test_writer import export
FULL=ROOT/'driving_test/route_scenery';Q=ROOT/'driving_test/quality_pass';REPORTS=Q/'reports';OUT=ROOT/'release_quality_v04/content/tracks/hk01_kam_tin_test';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/HK01_KamTin_FULL_LOOP_TEST.blend'));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;prepared=json.loads((FULL/'prepared_manifest.json').read_text(encoding='utf-8'));byname={'CSDI_'+m['name']:m for m in prepared['meshes']};dtm=np.load(ROOT/'gis/region_terrain_5m.npz');zz=dtm['z'];x0=float(dtm['x0'])-826000;y0=float(dtm['y0'])-833000;cell=float(dtm['cell'])
def height(xy):
    fx=(xy[:,0]-x0)/cell;fy=(y0-xy[:,1])/cell;c=np.clip(fx.astype(int),0,zz.shape[1]-2);r=np.clip(fy.astype(int),0,zz.shape[0]-2);a=fx-c;b=fy-r
    return zz[r,c]*(1-a)*(1-b)+zz[r,c+1]*a*(1-b)+zz[r+1,c]*(1-a)*b+zz[r+1,c+1]*a*b
def arrays(ob):
    me=ob.data;me.calc_loop_triangles();v=np.empty((len(me.vertices),3),dtype=np.float32);me.vertices.foreach_get('co',v.ravel());li=np.empty(len(me.loops),dtype=np.int32);me.loops.foreach_get('vertex_index',li);loops=np.empty((len(me.loop_triangles),3),dtype=np.int32);me.loop_triangles.foreach_get('loops',loops.ravel());uv=np.zeros((len(me.loops),2),dtype=np.float32)
    if me.uv_layers.active:me.uv_layers.active.uv.foreach_get('vector',uv.ravel())
    return v,li,loops,uv
def fingerprint(ob):
    a=arrays(ob);return hashlib.sha256(a[0].tobytes()+a[1].tobytes()).hexdigest()
physics_before={o.name:fingerprint(o) for o in scene.objects if o.type=='MESH' and o.name.startswith('1')};spawns_before={o.name:list(o['ac_matrix']) for o in scene.objects if o.type=='EMPTY' and 'ac_matrix' in o}
removed=collections.Counter();changed=[]
for ob in list(scene.objects):
    item=byname.get(ob.name)
    if not item:continue
    if item['category']=='VEGETATION(TB)':removed['vegetation_meshes']+=1;bpy.data.objects.remove(ob,do_unlink=True);continue
    if item['category']!='GENERIC':continue
    v,li,loops,uv=arrays(ob);faces=li[loops];mid=v[faces].mean(axis=1);keep=(mid[:,2]-height(mid[:,:2]))<=1.25;removed['raised_generic_triangles']+=int((~keep).sum())
    if keep.all():continue
    if not keep.any():bpy.data.objects.remove(ob,do_unlink=True);continue
    selected=loops[keep].ravel();vv=v[li[selected]];ff=np.arange(len(vv)).reshape(-1,3);nd=bpy.data.meshes.new(ob.name+'_GROUND_ONLY');nd.from_pydata(vv.tolist(),[],ff.tolist());nd.materials.append(ob.data.materials[0]);nd.uv_layers.new(name='UVMap').uv.foreach_set('vector',uv[selected].ravel());ob.data=nd;changed.append(ob.name)
    print('CLEANED_PHOTOMESH',ob.name,int((~keep).sum()),flush=True)
# Terrain-only support tree prevents putting replacement trunks on photo canopies.
gv=[];gf=[];base=0
for ob in scene.objects:
    item=byname.get(ob.name)
    if ob.type!='MESH' or not (ob.name=='VISUAL_GROUND_CSDI_TRANSITION' or item and item['category']=='TERRAIN(TB)'):continue
    v,li,loops,_=arrays(ob);gv.append(v);gf.append(li[loops]+base);base+=len(v)
tree=BVHTree.FromPolygons(np.vstack(gv).tolist(),np.vstack(gf).tolist(),all_triangles=True)
# Retained photo ground must not leave jagged canopy stumps. Project only this
# visual GENERIC layer onto the terrain; retain buildings/infrastructure in 3D.
projected=0
for ob in scene.objects:
    item=byname.get(ob.name)
    if ob.type!='MESH':continue
    if item and item['category']=='GENERIC':
        v,_,_,_=arrays(ob);xy,inverse=np.unique(v[:,:2],axis=0,return_inverse=True);ground=np.empty(len(xy),dtype=np.float32)
        for j,(x,y) in enumerate(xy):
            hit=tree.ray_cast(Vector((float(x),float(y),1000)),Vector((0,0,-1)),2000)[0]
            ground[j]=hit.z if hit is not None else float(height(np.array([[x,y]]))[0])
        v[:,2]=ground[inverse]+.012;ob.data.vertices.foreach_set('co',v.ravel());ob.data.update();projected+=len(v)
    if (item and item['category'] in ['GENERIC','TERRAIN(TB)']) or ob.name=='VISUAL_GROUND_CSDI_TRANSITION':
        ob.data.polygons.foreach_set('use_smooth',np.ones(len(ob.data.polygons),dtype=bool))
print('PROJECTED_VISUAL_GROUND_VERTICES',projected,flush=True)
def material(name,file):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;bs=mat.node_tree.nodes['Principled BSDF'];bs.inputs['Roughness'].default_value=.95;tex=mat.node_tree.nodes.new('ShaderNodeTexImage');im=bpy.data.images.load(str(Q/'textures'/file));im.pack();tex.image=im;mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);return mat
leaf=material('HK_NATIVE_LEAF','hk_native_leaf.png');bark=material('HK_NATIVE_BARK','hk_native_bark.png')
for name in ['ASPHALT','CONCRETE','GROUND','WHITE','YELLOW']:
    mat=bpy.data.materials['HK_TEST_'+name];path=Q/'textures'/('hk_test_'+name.lower()+'.png');image=bpy.data.images.load(str(path));image.pack()
    for node in mat.node_tree.nodes:
        if node.type=='TEX_IMAGE':node.image=image
def tree_variant(seed):
    rng=np.random.default_rng(seed);lv=[];lf=[];lu=[];bv=[];bf=[];bu=[]
    def branch(a,b,r1,r2):
        a=np.asarray(a);b=np.asarray(b);t=b-a;t=t/np.linalg.norm(t);n=np.cross(t,[0,1,0]);n/=np.linalg.norm(n);m=np.cross(t,n);start=len(bv)
        for p,r in [(a,r1),(b,r2)]:
            for j in range(7):bv.append(p+(n*math.cos(j*math.tau/7)+m*math.sin(j*math.tau/7))*r);bu.append((j/7,p[2]))
        for j in range(7):k=(j+1)%7;bf.extend([(start+j,start+k,start+7+k),(start+j,start+7+k,start+7+j)])
    branch((0,0,0),(.035,-.02,.68),.024,.008)
    for j in range(12):
        ang=j*math.tau/12+rng.uniform(-.3,.3);end=np.array([math.cos(ang)*rng.uniform(.15,.27),math.sin(ang)*rng.uniform(.15,.27),rng.uniform(.58,.82)]);branch((0,0,.34+j*.018),end,.009,.0018)
    for j in range(95):
        direction=rng.normal(size=3);direction/=np.linalg.norm(direction);radius=rng.uniform(.48,1)**(1/3);center=np.array([direction[0]*.30*radius,direction[1]*.30*radius,.71+direction[2]*.27*radius]);branch(center*.65+np.array([0,0,.25]),center,.0014,.0004)
        for k in range(6):
            p=center+rng.normal(0,.024,3);ang=rng.uniform(0,math.tau);axis=np.array([math.cos(ang),math.sin(ang),rng.uniform(-.7,.7)]);axis/=np.linalg.norm(axis);cross=np.cross(axis,[0,0,1]);cross/=np.linalg.norm(cross);length=rng.uniform(.042,.063);width=length*.43;start=len(lv)
            lv.extend([p-axis*length,p+cross*width,p+axis*length,p-cross*width,p+np.array([0,0,.009])]);tile=int(rng.integers(0,8));u0=tile%4/4;v0=tile//4/2
            lu.extend([(u0+.125,v0+.01),(u0+.01,v0+.25),(u0+.125,v0+.49),(u0+.24,v0+.25),(u0+.125,v0+.25)])
            for q in range(4):face=(start+q,start+(q+1)%4,start+4);lf.extend([face,face[::-1]])
    return tuple(np.asarray(a,dtype=np.float32 if i%3!=1 else np.int32) for i,a in enumerate([lv,lf,lu,bv,bf,bu]))
variants=[tree_variant(884+j) for j in range(5)];batches=collections.defaultdict(lambda:[[],[],[],0]);locations=json.loads((Q/'tree_locations.json').read_text(encoding='utf-8'));placed=[]
for i,loc in enumerate(locations):
    x,y=loc['xy'];hit=tree.ray_cast(Vector((x,y,1000)),Vector((0,0,-1)),2000)[0]
    if hit is None:continue
    h=float(np.clip(loc['canopy_top_z_m']-hit.z,5.5,12));rng=np.random.default_rng(1200+i);angle=rng.uniform(0,math.tau);scale=np.diag([h*rng.uniform(.86,1.10),h*rng.uniform(.86,1.10),h]);rotation=np.array([[math.cos(angle),-math.sin(angle),0],[math.sin(angle),math.cos(angle),0],[0,0,1]])@scale;origin=np.array([x,y,hit.z-.035]);variant=variants[i%5]
    for material_id,offset in [('LEAF',0),('BARK',3)]:
        v,f,uv=variant[offset:offset+3];key=(int(x//150),int(y//150),material_id);batch=batches[key];batch[0].append(v@rotation.T+origin);batch[1].append(f+batch[3]);batch[2].append(uv);batch[3]+=len(v)
    placed.append({**loc,'ground_z_m':hit.z,'height_m':h})
for (x,y,kind),batch in batches.items():
    vv=np.vstack(batch[0]);ff=np.vstack(batch[1]);uv=np.vstack(batch[2]);me=bpy.data.meshes.new(f'NATIVE_VEG_{kind}_{x}_{y}');me.from_pydata(vv.tolist(),[],ff.tolist());me.materials.append(leaf if kind=='LEAF' else bark);li=np.empty(len(me.loops),dtype=np.int32);me.loops.foreach_get('vertex_index',li);me.uv_layers.new(name='UVMap').uv.foreach_set('vector',uv[li].ravel());ob=bpy.data.objects.new(me.name,me);scene.collection.objects.link(ob);ob['lodout']=950 if kind=='LEAF' else 1000
physics_after={o.name:fingerprint(o) for o in scene.objects if o.type=='MESH' and o.name.startswith('1')};spawns_after={o.name:list(o['ac_matrix']) for o in scene.objects if o.type=='EMPTY' and 'ac_matrix' in o};assert physics_before==physics_after and spawns_before==spawns_after
objects=[o for o in scene.objects if o.type=='MESH'];groups=[('hk01_kam_tin_test.kn5',[o for o in objects if not o.name.startswith(('CSDI_','NATIVE_VEG_'))],list(spawns_after.items()))]
for sheet in prepared['sheets']:groups.append(('scenery_'+sheet+'.kn5',[o for o in objects if o.get('source_sheet')==sheet],[]))
groups.append(('native_vegetation.kn5',[o for o in objects if o.name.startswith('NATIVE_VEG_')],[]));exports=[];settings={}
for file,obs,dummies in groups:
    if not obs:continue
    names=sorted({o.data.materials[0].name for o in obs});mats=[];textures={}
    for name in names:
        mat=bpy.data.materials[name];image=next(n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image);path=Path(bpy.path.abspath(image.filepath));mats.append((name,path.name));textures[path.name]=path
        ambient,diffuse,specular=(.34,.25,0) if name.startswith('R3_') else (.35,.40,.015)
        if name=='HK_TEST_ASPHALT':ambient,diffuse,specular=.32,.42,.025
        if name in ['HK_TEST_CONCRETE','HK_TEST_WHITE','HK_TEST_GROUND']:ambient,diffuse,specular=.30,.35,0
        if name=='HK_NATIVE_LEAF':ambient,diffuse,specular=.36,.32,.01
        settings[name]={'ambient':ambient,'diffuse':diffuse,'specular':specular,'emissive':0}
    record=export(OUT/file,obs,mats,sorted(textures.items()),dummies,material_settings=settings);record.pop('nodes');record['sha256']=hashlib.file_digest((OUT/file).open('rb'),'sha256').hexdigest();exports.append(record);print('QUALITY_MODEL_EXPORTED',file,record['triangles'],flush=True)
(OUT/'models.ini').write_text('\n'.join(f'[MODEL_{i}]\nFILE={Path(r["file"]).name}\nPOSITION=0,0,0\nROTATION=0,0,0\n' for i,r in enumerate(exports)),encoding='utf-8')
report={'removed':dict(removed),'projected_visual_ground_vertices':projected,'authored_trees':len(placed),'models':exports,'material_settings':settings,'physical_meshes_unchanged':True,'spawn_timing_nodes_unchanged':True,'user_graphics_settings_changed':False,'trees_are_source_positioned_authored_assets_not_surveyed_species':True};(REPORTS/'quality_build.json').write_text(json.dumps(report,indent=2),encoding='utf-8');(Q/'placed_trees.json').write_text(json.dumps(placed,indent=2),encoding='utf-8')
scene['stage']='0.4 QUALITY PASS — USER APPEARANCE REVIEW REQUIRED';bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/HK01_KamTin_QUALITY_v04.blend'),compress=True)
scene.render.engine='CYCLES';scene.cycles.samples=12;scene.render.resolution_x=1200;scene.render.resolution_y=750;scene.render.resolution_percentage=100;cam=scene.camera;cam.data.type='PERSP';cam.data.lens=32
route=np.load(ROOT/'driving_test/route_geometry.npz')['center'];checkpoints=json.loads((FULL/'checkpoints.json').read_text(encoding='utf-8'))
for cp in [1,2,3,4,5,6,7,8]:
    index=checkpoints[cp-1]['route_sample'];p=route[index];t=route[(index+3)%len(route)]-route[(index-3)%len(route)];t[2]=0;t/=np.linalg.norm(t);cam.location=Vector(p)-Vector(t)*5+Vector((0,0,1.7));target=Vector(p)+Vector(t)*30+Vector((0,0,.7));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(REPORTS/f'checkpoint_{cp:02d}.png');bpy.ops.render.render(write_still=True)
print('QUALITY_BUILD_COMPLETE',len(placed),sum(r['triangles'] for r in exports),flush=True)
