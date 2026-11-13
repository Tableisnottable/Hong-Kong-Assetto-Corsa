"""Build a reference-informed visual pass without importing the reference assets."""
from pathlib import Path
import sys,json,math,hashlib,collections
import bpy,numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from kn5_test_writer import export
Q=ROOT/'driving_test/finish_pass';REPORTS=Q/'reports';OUT=ROOT/'release_finish_v05/content/tracks/hk01_kam_tin_test';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/HK01_KamTin_QUALITY_v04.blend'));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
def fingerprint(ob):
    me=ob.data;v=np.empty(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',v);loops=np.empty(len(me.loops),dtype=np.int32);me.loops.foreach_get('vertex_index',loops);return hashlib.sha256(v.tobytes()+loops.tobytes()).hexdigest()
before={o.name:fingerprint(o) for o in scene.objects if o.type=='MESH' and o.name.startswith('1')};spawns={o.name:list(o['ac_matrix']) for o in scene.objects if o.type=='EMPTY' and 'ac_matrix' in o}
for ob in list(scene.objects):
    if ob.name.startswith('NATIVE_VEG_'):bpy.data.objects.remove(ob,do_unlink=True)
    elif ob.name.startswith('1WALL_TEST_'):ob['renderable']=False;ob['cast_shadows']=False;ob.hide_render=True
    elif ob.name.startswith(('LINE_','PIT_BOUNDARY','START_FINISH_STRIPE')):
        for v in ob.data.vertices:v.co.z-=.009
        ob['cast_shadows']=False
def set_image(mat,path,alpha=False):
    mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.88
    image=bpy.data.images.load(str(path),check_existing=True);image.pack();nodes=[n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE']
    tex=nodes[0] if nodes else mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image;mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    if alpha:
        cutoff=mat.node_tree.nodes.new('ShaderNodeMath');cutoff.operation='GREATER_THAN';cutoff.inputs[1].default_value=.45;mat.node_tree.links.new(tex.outputs['Alpha'],cutoff.inputs[0]);mat.node_tree.links.new(cutoff.outputs[0],bs.inputs['Alpha']);mat.surface_render_method='DITHERED'
    return mat
def material(name,file,alpha=False):return set_image(bpy.data.materials.new(name),Q/'textures'/file,alpha)
leaf=material('HK_FINISH_FOLIAGE','hk_foliage_sprays.png',True);bark=material('HK_FINISH_BARK','hk_bark_photo.png');steel=material('HK_FINISH_STEEL','hk_galvanised_steel.png');dark=material('HK_FINISH_POST','hk_post_dark.png');red=material('HK_FINISH_REFLECTOR_RED','hk_reflector_red.png');white=material('HK_FINISH_REFLECTOR_WHITE','hk_reflector_white.png')
for name,file,alpha in [('HK_TEST_ASPHALT','hk_asphalt_photo.png',False),('HK_TEST_GROUND','hk_ground_photo.png',False),('HK_TEST_WHITE','hk_worn_paint.png',True)]:set_image(bpy.data.materials[name],Q/'textures'/file,alpha)
# Weld only the visual terrain, whose original triangles had disconnected normals.
for ob in scene.objects:ob.select_set(False)
ground=scene.objects.get('VISUAL_GROUND_CSDI_TRANSITION')
if ground:
    bpy.context.view_layer.objects.active=ground;ground.select_set(True);mod=ground.modifiers.new('Visual terrain smooth normals','WELD');mod.merge_threshold=.001;bpy.ops.object.modifier_apply(modifier=mod.name);ground.select_set(False)
    ground.data.polygons.foreach_set('use_smooth',np.ones(len(ground.data.polygons),dtype=bool));uv=ground.data.uv_layers.active
    if uv:
        v=np.empty((len(ground.data.vertices),3),dtype=np.float32);ground.data.vertices.foreach_get('co',v.ravel());vi=np.empty(len(ground.data.loops),dtype=np.int32);ground.data.loops.foreach_get('vertex_index',vi);uv.uv.foreach_set('vector',(v[vi,:2]/75).ravel())
def tree_variant(seed):
    rng=np.random.default_rng(seed);lv=[];lf=[];lu=[];bv=[];bf=[];bu=[]
    def branch(a,b,r1,r2):
        a=np.array(a);b=np.array(b);t=b-a;t/=np.linalg.norm(t);n=np.cross(t,[0,1,0]);n/=np.linalg.norm(n);m=np.cross(t,n);start=len(bv)
        for p,r in [(a,r1),(b,r2)]:
            for j in range(7):bv.append(p+(n*math.cos(j*math.tau/7)+m*math.sin(j*math.tau/7))*r);bu.append((j/7,p[2]*15))
        for j in range(7):k=(j+1)%7;bf.extend([(start+j,start+k,start+7+k),(start+j,start+7+k,start+7+j)])
    branch((0,0,0),(.018,-.012,.7),.022,.006)
    for j in range(16):
        a=j*math.tau/16+rng.uniform(-.35,.35);end=np.array([math.cos(a)*rng.uniform(.18,.30),math.sin(a)*rng.uniform(.18,.30),rng.uniform(.58,.88)]);branch((0,0,.32+j*.019),end,.0075,.0012)
    crown=np.array([rng.uniform(.28,.34),rng.uniform(.26,.32),rng.uniform(.25,.32)])
    for j in range(400):
        d=rng.normal(size=3);d/=np.linalg.norm(d);center=d*crown*rng.uniform(.5,1)**(1/3)+np.array([0,0,.70]);a=rng.uniform(0,math.tau);pitch=rng.uniform(-.75,.75);normal=np.array([math.cos(a)*math.cos(pitch),math.sin(a)*math.cos(pitch),math.sin(pitch)]);side=np.cross(normal,[0,0,1]);side/=np.linalg.norm(side);axis=np.cross(side,normal);length=rng.uniform(.060,.082);width=length*rng.uniform(.7,.95);start=len(lv)
        lv.extend([center-axis*length-side*width,center-axis*length+side*width,center+axis*length+side*width,center+axis*length-side*width]);tile=int(rng.integers(0,4));u=tile%2*.5;v=tile//2*.5;lu.extend([(u+.003,v+.003),(u+.497,v+.003),(u+.497,v+.497),(u+.003,v+.497)])
        lf.extend([(start,start+1,start+2),(start,start+2,start+3),(start+2,start+1,start),(start+3,start+2,start)])
    return [np.asarray(a,dtype=np.int32 if i%3==1 else np.float32) for i,a in enumerate([lv,lf,lu,bv,bf,bu])]
variants=[tree_variant(5500+i) for i in range(8)];batches=collections.defaultdict(lambda:[[],[],[],0]);locations=json.loads((ROOT/'driving_test/quality_pass/placed_trees.json').read_text(encoding='utf-8'))
for i,loc in enumerate(locations):
    rng=np.random.default_rng(8400+i);x,y=loc['xy'];h=loc['height_m'];angle=rng.uniform(0,math.tau);scale=np.diag([h*rng.uniform(.88,1.12),h*rng.uniform(.88,1.12),h]);rot=np.array([[math.cos(angle),-math.sin(angle),0],[math.sin(angle),math.cos(angle),0],[0,0,1]])@scale;origin=np.array([x,y,loc['ground_z_m']-.035])
    for kind,offset in [('LEAF',0),('BARK',3)]:
        v,f,uv=variants[i%len(variants)][offset:offset+3];b=batches[(int(x//110),int(y//110),kind)];b[0].append(v@rot.T+origin);b[1].append(f+b[3]);b[2].append(uv);b[3]+=len(v)
def make_mesh(name,v,f,mat,uv=None,smooth=False,lod=800):
    me=bpy.data.meshes.new(name);me.from_pydata(np.asarray(v).tolist(),[],np.asarray(f).tolist());me.materials.append(mat)
    if uv is None:
        v=np.asarray(v);uv=v[:,:2]
    vi=np.empty(len(me.loops),dtype=np.int32);me.loops.foreach_get('vertex_index',vi);me.uv_layers.new(name='UVMap').uv.foreach_set('vector',np.asarray(uv,dtype=np.float32)[vi].ravel());me.polygons.foreach_set('use_smooth',np.full(len(me.polygons),smooth,dtype=bool));ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);ob['lodout']=lod;return ob
for (x,y,kind),b in batches.items():make_mesh(f'NATIVE_VEG_{kind}_{x}_{y}',np.vstack(b[0]),np.vstack(b[1]),leaf if kind=='LEAF' else bark,np.vstack(b[2]),kind=='BARK',650 if kind=='LEAF' else 750)
# New visual rails follow the existing safety-collision rings, without claiming
# surveyed real-world guardrail positions. Coarse original collision is retained.
surfaces=np.load(ROOT/'driving_test/surfaces.npz');route=np.load(ROOT/'driving_test/route_geometry.npz')['center'];posts=0;rail_length=0
rail_batches=collections.defaultdict(lambda:[[],[]])
def add_geom(kind,v,f):
    v=np.asarray(v);mid=v.mean(axis=0);b=rail_batches[(int(mid[0]//100),int(mid[1]//100),kind)];base=len(b[0]);b[0].extend(v.tolist());b[1].extend((np.asarray(f)+base).tolist())
def box(kind,p,t,n,half):
    v=[p+t*a+n*b+np.array([0,0,c]) for c in [-half[2],half[2]] for b in [-half[1],half[1]] for a in [-half[0],half[0]]]
    f=[(0,2,3),(0,3,1),(4,5,7),(4,7,6),(0,1,5),(0,5,4),(2,6,7),(2,7,3),(0,4,6),(0,6,2),(1,3,7),(1,7,5)];add_geom(kind,v,f)
for key in surfaces.files:
    if not key.startswith('wall_ring_'):continue
    pts=surfaces[key];closed=np.vstack([pts,pts[0]]);lengths=np.linalg.norm(np.diff(closed[:,:2],axis=0),axis=1);s=np.r_[0,np.cumsum(lengths)];rail_length+=s[-1]
    for i,p in enumerate(pts):
        q=pts[(i+1)%len(pts)];t=q-p;t[2]=0;t/=max(np.linalg.norm(t),1e-8);n=np.array([-t[1],t[0],0]);closest=route[np.argmin(((route[:,:2]-p[:2])**2).sum(axis=1))]
        if np.dot(n,closest-p)<0:n=-n
        # W-profile folded steel, double-sided for the static alpha-free shader.
        profile=[(.0,-.15),(.035,-.10),(.005,-.055),(-.035,0),(.005,.055),(.035,.10),(.0,.15)];v=[a+n*x+np.array([0,0,.62+z]) for a in [p,q] for x,z in profile];f=[]
        for j in range(6):f.extend([(j,j+7,j+8),(j,j+8,j+1),(j+8,j+7,j),(j+1,j+8,j)])
        add_geom('STEEL',v,f)
    for distance in np.arange(0,s[-1],3.8):
        i=min(int(np.searchsorted(s,distance,side='right')-1),len(pts)-1);a=pts[i];b=pts[(i+1)%len(pts)];p=a+(b-a)*((distance-s[i])/max(lengths[i],1e-8));t=b-a;t[2]=0;t/=max(np.linalg.norm(t),1e-8);n=np.array([-t[1],t[0],0]);closest=route[np.argmin(((route[:,:2]-p[:2])**2).sum(axis=1))]
        if np.dot(n,closest-p)<0:n=-n
        box('POST',p-n*.058+np.array([0,0,.34]),t,n,(.045,.032,.42));box('STEEL',p+n*.047+np.array([0,0,.62]),t,n,(.016,.009,.016))
        if posts%4==0:box('REFLECTOR_RED' if posts%8 else 'REFLECTOR_WHITE',p+n*.053+np.array([0,0,.75]),t,n,(.027,.009,.065))
        posts+=1
rail_materials={'STEEL':steel,'POST':dark,'REFLECTOR_RED':red,'REFLECTOR_WHITE':white}
for (x,y,kind),(v,f) in rail_batches.items():make_mesh(f'ROAD_DETAIL_{kind}_{x}_{y}',v,f,rail_materials[kind],lod=850)
after={o.name:fingerprint(o) for o in scene.objects if o.type=='MESH' and o.name.startswith('1')};after_spawns={o.name:list(o['ac_matrix']) for o in scene.objects if o.type=='EMPTY' and 'ac_matrix' in o};assert before==after and spawns==after_spawns
objects=[o for o in scene.objects if o.type=='MESH'];prepared=json.loads((ROOT/'driving_test/route_scenery/prepared_manifest.json').read_text(encoding='utf-8'));groups=[('hk01_kam_tin_test.kn5',[o for o in objects if not o.name.startswith(('CSDI_','NATIVE_VEG_','ROAD_DETAIL_'))],list(spawns.items()))]
for sheet in prepared['sheets']:groups.append(('scenery_'+sheet+'.kn5',[o for o in objects if o.get('source_sheet')==sheet],[]))
groups+=[('native_vegetation.kn5',[o for o in objects if o.name.startswith('NATIVE_VEG_')],[]),('road_detail.kn5',[o for o in objects if o.name.startswith('ROAD_DETAIL_')],[])]
settings={};exports=[]
for file,obs,dummies in groups:
    if not obs:continue
    mats=[];textures={}
    for name in sorted({o.data.materials[0].name for o in obs}):
        mat=bpy.data.materials[name];image=next(n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image);path=Path(bpy.path.abspath(image.filepath));mats.append((name,path.name));textures[path.name]=path
        a,d,s=(.34,.25,0) if name.startswith('R3_') else (.35,.40,.015);shader='ksPerPixel'
        if name=='HK_TEST_ASPHALT':a,d,s=.34,.46,.025
        if name=='HK_TEST_GROUND':a,d,s=.33,.38,0
        if name in ['HK_FINISH_FOLIAGE','HK_TEST_WHITE']:a,d,s=.40,.48,.015;shader='ksPerPixelAT'
        if name=='HK_FINISH_STEEL':a,d,s=.32,.38,.12
        settings[name]={'ambient':a,'diffuse':d,'specular':s,'emissive':0,'shader':shader,'alpha_ref':.45}
    record=export(OUT/file,obs,mats,sorted(textures.items()),dummies,material_settings=settings);record.pop('nodes');record['sha256']=hashlib.file_digest((OUT/file).open('rb'),'sha256').hexdigest();exports.append(record);print('FINISH_MODEL_EXPORTED',file,record['triangles'],flush=True)
(OUT/'models.ini').write_text('\n'.join(f'[MODEL_{i}]\nFILE={Path(r["file"]).name}\nPOSITION=0,0,0\nROTATION=0,0,0\n' for i,r in enumerate(exports)),encoding='utf-8')
report={'reference':'Route Twisk RWE / Repack Test, read-only','reference_assets_reused':False,'authored_trees':len(locations),'tree_variants':len(variants),'foliage_shader':'ksPerPixelAT','visual_guardrail_posts':posts,'visual_guardrail_length_m':float(rail_length),'physical_meshes_unchanged':True,'spawn_timing_nodes_unchanged':True,'coarse_safety_wall_collision_retained_behind_visual_rails':True,'surveyed_roadside_fidelity_claimed':False,'user_graphics_settings_changed':False,'models':exports,'material_settings':settings};(REPORTS/'quality_build.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
scene['stage']='0.5 REFERENCE-INFORMED FINISH PASS — USER QUALITY COMPARISON REQUIRED';bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/HK01_KamTin_FINISH_v05.blend'),compress=True)
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.render.resolution_x=1200;scene.render.resolution_y=750;scene.render.resolution_percentage=100;cam=scene.camera;cam.data.type='PERSP';cam.data.lens=32
checkpoints=json.loads((ROOT/'driving_test/route_scenery/checkpoints.json').read_text(encoding='utf-8'))
for cp in checkpoints:
    i=cp['route_sample'];p=route[i];t=route[(i+3)%len(route)]-route[(i-3)%len(route)];t[2]=0;t/=np.linalg.norm(t);cam.location=Vector(p)-Vector(t)*5+Vector((0,0,1.7));target=Vector(p)+Vector(t)*30+Vector((0,0,.7));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(REPORTS/f'checkpoint_{cp["checkpoint"]:02d}.png');bpy.ops.render.render(write_still=True)
print('FINISH_BUILD_COMPLETE',len(locations),sum(r['triangles'] for r in exports),flush=True)
