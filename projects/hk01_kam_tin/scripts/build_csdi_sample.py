"""Build a separately staged CSDI scenery sample without launching the game."""
from pathlib import Path
import sys,json,math,hashlib,collections
import bpy,numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from kn5_test_writer import export
FULL_ROUTE='--full-route' in sys.argv
BUILD=ROOT/'driving_test';SAMPLE=BUILD/('route_scenery' if FULL_ROUTE else 'csdi_sample');REPORTS=SAMPLE/'reports'
REPORTS.mkdir(exist_ok=True)
TRACK='hk01_kam_tin_test'
OUT=ROOT/('release_route_scenery/content/tracks' if FULL_ROUTE else 'release_csdi_sample/content/tracks')/TRACK;OUT.mkdir(parents=True,exist_ok=True)
prepared=json.loads((SAMPLE/'prepared_manifest.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/HK01_KamTin_DRIVING_TEST.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
from mathutils.bvhtree import BVHTree
base_ground=np.load(BUILD/'terrain_cut.npz')
base_ground_tree=BVHTree.FromPolygons(base_ground['vertices'].tolist(),base_ground['faces'].tolist(),all_triangles=True)
source_ground=np.load(SAMPLE/'source_terrain_reference.npz')
source_ground_tree=BVHTree.FromPolygons(source_ground['vertices'].tolist(),source_ground['faces'].tolist(),all_triangles=True)
route_points=np.load(BUILD/'route_geometry.npz')['center']
route_cells=collections.defaultdict(list)
for p in route_points:route_cells[tuple(np.floor(p[:2]/30).astype(int))].append(p[:2])
route_cells={k:np.asarray(v) for k,v in route_cells.items()}
if FULL_ROUTE:
    coverage=json.loads((SAMPLE/'coverage.json').read_text())
    tile_bounds=[[v-o for v,o in zip(r['bounds_epsg2326'],[826000,833000,826000,833000])] for r in prepared['source_sheet_records']]
    geometry=coverage['source_union_geometry'];polygons=geometry['coordinates'] if geometry['type']=='MultiPolygon' else [geometry['coordinates']]
    boundary_segments=[(np.asarray(a),np.asarray(b)) for poly in polygons for ring in poly for a,b in zip(ring,ring[1:])]
else:
    tile_bounds=[[-1250,-600,-500,0]];boundary_segments=[]
def inside_sources(x,y):return any(a-.001<=x<=c+.001 and b-.001<=y<=d+.001 for a,b,c,d in tile_bounds)
def boundary_distance(x,y):
    if not FULL_ROUTE:return max(0,min(x+1250,-500-x,y+600,-y))
    q=np.array([x,y]);best=1e20
    for a,b in boundary_segments:
        delta=b-a;t=max(0,min(1,float(np.dot(q-a,delta)/max(1e-10,np.dot(delta,delta)))))
        best=min(best,float(np.linalg.norm(q-(a+t*delta))))
    return best
def road_distance(x,y):
    key=(int(math.floor(x/30)),int(math.floor(y/30)));best=10000.
    for dx in range(-2,3):
        for dy in range(-2,3):
            ar=route_cells.get((key[0]+dx,key[1]+dy))
            if ar is not None:best=min(best,float(((ar-np.array([x,y]))**2).sum(axis=1).min()))
    return math.sqrt(best)
def smooth(t):t=max(0.,min(1.,t));return t*t*(3-2*t)
def ground_transition(vertices,source_mesh=False):
    vertices=vertices.copy();count=0
    for i,(x,y,z) in enumerate(vertices):
        if not inside_sources(x,y):continue
        boundary=boundary_distance(x,y)
        w=max(1-smooth((road_distance(x,y)-11)/(13 if FULL_ROUTE else 27)),1-smooth(boundary/35))
        if source_mesh and w<1e-6:continue
        a=base_ground_tree.ray_cast(Vector((float(x),float(y),1000)),Vector((0,0,-1)),2000)[0]
        b=source_ground_tree.ray_cast(Vector((float(x),float(y),1000)),Vector((0,0,-1)),2000)[0]
        if a is None or b is None:continue
        vertices[i,2]=b.z+(a.z-b.z)*w-(0 if source_mesh else .035);count+=1
    return vertices,count
def fingerprint(ob):
    v=np.empty(len(ob.data.vertices)*3,dtype='<f4');ob.data.vertices.foreach_get('co',v)
    loops=np.empty(len(ob.data.loops),dtype='<i4');ob.data.loops.foreach_get('vertex_index',loops)
    return hashlib.sha256(v.tobytes()+loops.tobytes()).hexdigest()
physics_before={o.name:fingerprint(o) for o in scene.objects if o.type=='MESH' and o.name.startswith('1')}
spawns_before={o.name:list(o.get('ac_matrix',[])) for o in scene.objects if o.type=='EMPTY' and o.name.startswith('AC_')}

# Remove whole connected placeholder buildings whose centres are in this tile.
# Connected components prevent chopping a mass in half at the tile boundary.
source_building_bounds=[(np.asarray(item['bounds_local'][0]),np.asarray(item['bounds_local'][1]))
                        for item in prepared['meshes'] if item['category']=='BUILDING']
removed_buildings=0
for ob in list(scene.objects):
    if not ob.name.startswith('BUILDING_MASS_'):continue
    data=ob.data;parents=list(range(len(data.vertices)))
    def root(i):
        while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
        return i
    for face in data.polygons:
        rr=root(face.vertices[0])
        for vi in face.vertices[1:]:parents[root(vi)]=rr
    groups=collections.defaultdict(list)
    for i in range(len(parents)):groups[root(i)].append(i)
    remove=set()
    for ids in groups.values():
        coords=np.array([data.vertices[i].co[:] for i in ids]);mid=(coords.min(axis=0)+coords.max(axis=0))/2
        replace=inside_sources(mid[0],mid[1])
        if replace:
            fallback_min=coords.min(axis=0);fallback_max=coords.max(axis=0)
            fallback_area=max(0.,fallback_max[0]-fallback_min[0])*max(0.,fallback_max[1]-fallback_min[1])
            replace=False
            if fallback_area>1.:
                for source_min,source_max in source_building_bounds:
                    overlap_x=max(0.,min(fallback_max[0],source_max[0])-max(fallback_min[0],source_min[0]))
                    overlap_y=max(0.,min(fallback_max[1],source_max[1])-max(fallback_min[1],source_min[1]))
                    source_area=max(0.,source_max[0]-source_min[0])*max(0.,source_max[1]-source_min[1])
                    if overlap_x*overlap_y/max(1.,min(fallback_area,source_area))>=.35:
                        replace=True;break
        if FULL_ROUTE:replace=replace and float(np.linalg.norm(route_points[:,:2]-mid[:2],axis=1).min())<200
        if replace:remove.update(ids);removed_buildings+=1
    if not remove:continue
    if len(remove)==len(data.vertices):bpy.data.objects.remove(ob,do_unlink=True);continue
    keep=[i for i in range(len(data.vertices)) if i not in remove];mapping={old:new for new,old in enumerate(keep)}
    vv=[tuple(data.vertices[i].co) for i in keep];ff=[];uvs=[]
    for face in data.polygons:
        if face.vertices[0] in remove:continue
        ff.append(tuple(mapping[i] for i in face.vertices));uvs.extend(tuple(data.uv_layers.active.data[i].uv) for i in face.loop_indices)
    nd=bpy.data.meshes.new(ob.name+'_CSDI_CUT');nd.from_pydata(vv,[],ff);nd.materials.append(data.materials[0]);nd.uv_layers.new(name='UVMap').uv.foreach_set('vector',np.asarray(uvs,dtype=np.float32).ravel());ob.data=nd

# Preserve exact terrain collision triangles but hide their placeholder colour.
# A separate visual underlay exposes real terrain inside the source tile.
for ob in scene.objects:
    if ob.name.startswith('1GRASS'):ob['renderable']=False;ob['cast_shadows']=False;ob.hide_render=True
visual=np.load(SAMPLE/'visible_ground.npz');gv,ground_transition_vertices=ground_transition(visual['vertices'])
gm=bpy.data.meshes.new('CSDI_Visual_Ground_Transition');gm.from_pydata(gv.tolist(),[],visual['faces'].tolist());gm.materials.append(bpy.data.materials['HK_TEST_GROUND'])
go=bpy.data.objects.new('VISUAL_GROUND_CSDI_TRANSITION',gm);scene.collection.objects.link(go);go['lodout']=8000
gloops=np.empty(len(gm.loops),dtype=np.int32);gm.loops.foreach_get('vertex_index',gloops);gm.uv_layers.new(name='UVMap').uv.foreach_set('vector',(gv[gloops,:2]/5).ravel())
for face in gm.polygons:face.use_smooth=True
sign_image=bpy.data.images.load(str(SAMPLE/'textures'/('route_test_sign.png' if FULL_ROUTE else 'csdi_test_sign.png')),check_existing=True);sign_image.pack()
for node in bpy.data.materials['HK_TEST_SIGN'].node_tree.nodes:
    if node.type=='TEX_IMAGE':node.image=sign_image
if FULL_ROUTE:
    marker_material=bpy.data.materials.new('HK_TEST_CHECKPOINTS');marker_material.use_nodes=True
    image=bpy.data.images.load(str(SAMPLE/'textures/test_checkpoint_atlas.png'));image.pack()
    tex=marker_material.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image;marker_material.node_tree.links.new(tex.outputs['Color'],marker_material.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    checkpoints=json.loads((SAMPLE/'checkpoints.json').read_text())
    for cp in checkpoints:
        i=cp['route_sample'];p=route_points[i].copy();t=route_points[(i+2)%len(route_points)]-route_points[(i-2)%len(route_points)];t[2]=0;t/=np.linalg.norm(t);n=np.array([-t[1],t[0],0])
        center=p+n*5.3+np.array([0,0,1.2]);vv=[center+n*a+np.array([0,0,z]) for a,z in [(-.45,0),(.45,0),(.45,.9),(-.45,.9)]]
        me=bpy.data.meshes.new('TEST_CP_'+str(cp['checkpoint']));me.from_pydata(vv,[],[(2,1,0),(3,2,0),(0,1,2),(0,2,3)]);me.materials.append(marker_material);ob=bpy.data.objects.new(me.name,me);scene.collection.objects.link(ob);ob['lodout']=700
        u0=((cp['checkpoint']-1)%4)/4;u1=u0+.25;v1=1-((cp['checkpoint']-1)//4)/2;v0=v1-.5
        coords=[(u1,v0),(u0,v0),(u0,v1),(u1,v1)];uv=me.uv_layers.new(name='UVMap')
        for face in me.polygons:
            for li in face.loop_indices:uv.data[li].uv=coords[me.loops[li].vertex_index]
        bpy.ops.mesh.primitive_cube_add(size=1,location=tuple(center-np.array([0,0,.55])))
        post=bpy.context.object;post.name='TEST_CP_POST_'+str(cp['checkpoint']);post.scale=(.06,.06,1.25);post.data.materials.append(bpy.data.materials['HK_TEST_CONCRETE']);post['lodout']=700

collection=bpy.data.collections.new('08_CSDI_REAL_SCENERY_SAMPLE');scene.collection.children.link(collection)
materials={}
for item in prepared['materials']:
    mat=bpy.data.materials.new(item['name']);mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.95;bs.inputs['Metallic'].default_value=0
    im=bpy.data.images.load(str(SAMPLE/'textures'/item['texture']),check_existing=True);im.pack()
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im;mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    materials[item['name']]=mat
counts=collections.Counter();records=[]
for item in prepared['meshes']:
    ar=np.load(SAMPLE/item['file']);v=ar['vertices'];f=ar['faces'];uv=ar['uv']
    if item['category']=='TERRAIN(TB)':v,_=ground_transition(v,source_mesh=True)
    me=bpy.data.meshes.new('CSDI_'+item['name']);me.from_pydata(v.tolist(),[],f.tolist());me.update()
    ob=bpy.data.objects.new('CSDI_'+item['name'],me);collection.objects.link(ob);me.materials.append(materials[item['material']])
    li=np.empty(len(me.loops),dtype=np.int32);me.loops.foreach_get('vertex_index',li)
    me.uv_layers.new(name='UVMap').uv.foreach_set('vector',uv[li].ravel())
    for face in me.polygons:face.use_smooth=item['category'] in ['GENERIC','VEGETATION(TB)','TERRAIN(TB)']
    ob['source_dataset']='LandsD 3D Visualisation Map (Individualised models)';ob['source_sheet']=item.get('sheet',prepared.get('sheet',''));ob['source_model']=item['source_model'];ob['visual_scenery_only']=True
    ob['lodout']=(1100 if FULL_ROUTE else 1800) if item['category']!='TERRAIN(TB)' else 5000
    ratio=item['decimate_ratio']
    if ratio<1 and len(f)>300:
        bpy.context.view_layer.objects.active=ob;ob.select_set(True)
        # Weld shared positions while retaining per-corner UVs before collapse.
        mod=ob.modifiers.new('CSDI_Weld','WELD');mod.merge_threshold=.001
        bpy.ops.object.modifier_apply(modifier=mod.name)
        mod=ob.modifiers.new('CSDI_Sample_Budget','DECIMATE');mod.ratio=ratio;mod.use_collapse_triangulate=True
        bpy.ops.object.modifier_apply(modifier=mod.name);ob.select_set(False)
    me=ob.data;me.calc_loop_triangles();count=len(me.loop_triangles);counts[item['category']]+=count
    records.append({'name':ob.name,'category':item['category'],'triangles':count,'before_decimation':len(f)})
    print('IMPORTED',ob.name,count,flush=True)

physics_after={o.name:fingerprint(o) for o in scene.objects if o.type=='MESH' and o.name.startswith('1')}
spawns_after={o.name:list(o.get('ac_matrix',[])) for o in scene.objects if o.type=='EMPTY' and o.name.startswith('AC_')}
assert physics_before==physics_after,'Scenery import changed an established collision mesh'
assert spawns_before==spawns_after,'Scenery import changed a spawn/timing matrix'
if FULL_ROUTE:
    physical=[o for o in scene.objects if o.type=='MESH' and o.name.startswith(('1ROAD','1PITLANE','1SHOULDER'))]
    pv=[];pf=[]
    for ob in physical:
        base=len(pv);pv.extend(tuple(v.co) for v in ob.data.vertices);pf.extend(tuple(base+i for i in p.vertices) for p in ob.data.polygons)
    ptree=BVHTree.FromPolygons(pv,pf,all_triangles=True);checks=0;errors=[];max_error=0;source_hits=0
    route_ar=np.load(BUILD/'route_geometry.npz');normals=route_ar['normal']
    for i,p in enumerate(route_points):
        source_hits+=source_ground_tree.ray_cast(Vector((float(p[0]),float(p[1]),1000)),Vector((0,0,-1)),2000)[0] is not None
        for lateral in [-3.2,-2.,-1.,0.,1.,2.,3.2]:
            q=p.copy();q[:2]+=normals[i]*lateral;expected=p[2]-.055*min(abs(lateral)/3.5,1)
            hit,n,_,_=ptree.ray_cast(Vector((float(q[0]),float(q[1]),float(q[2]+4))),Vector((0,0,-1)),10);checks+=1
            if hit is None:errors.append([i,lateral,'missing road support'])
            else:
                error=abs(hit.z-expected);max_error=max(max_error,error)
                if error>.15 or n.z<.85:errors.append([i,lateral,'surface mismatch or steep normal',error])
    validation={'passed':not errors,'errors':errors,'route_samples':len(route_points),'lateral_surface_ray_checks':checks,'maximum_road_profile_error_m':max_error,'source_terrain_height_hits':int(source_hits),'source_terrain_height_samples':len(route_points),'physics_meshes_unchanged':True,'spawn_matrices_unchanged':True,'game_test':'pending user; no engine launch'}
    (REPORTS/'route_surface_verification.json').write_text(json.dumps(validation,indent=2))
    if errors:raise RuntimeError('Full-route physical surface validation failed: '+str(errors[:3]))
objects=[o for o in scene.objects if o.type=='MESH']
names=sorted({o.data.materials[0].name for o in objects})
export_materials=[];textures=[]
for name in names:
    mat=bpy.data.materials[name];images=[n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
    assert len(images)==1,(name,'expected a single diffuse map')
    file=Path(bpy.path.abspath(images[0].filepath));export_materials.append((name,file.name));textures.append((file.name,file))
dummies=[(o.name,tuple(o['ac_matrix'])) for o in scene.objects if o.type=='EMPTY' and 'ac_matrix' in o]
if FULL_ROUTE:
    texture_files={name:path for name,path in textures};mat_textures=dict(export_materials)
    groups=[(TRACK+'.kn5',[o for o in objects if not o.name.startswith('CSDI_')],dummies)]
    for sheet in prepared['sheets']:
        groups.append(('scenery_'+sheet+'.kn5',[o for o in objects if o.name.startswith('CSDI_') and o.get('source_sheet')==sheet],[]))
    model_reports=[];all_nodes=[]
    for file,model_objects,model_dummies in groups:
        if not model_objects:continue
        used=sorted({o.data.materials[0].name for o in model_objects});model_materials=[(name,mat_textures[name]) for name in used];model_textures=sorted({mat_textures[name] for name in used})
        part=export(OUT/file,model_objects,model_materials,[(name,texture_files[name]) for name in model_textures],model_dummies)
        part['sha256']=hashlib.file_digest((OUT/file).open('rb'),'sha256').hexdigest();all_nodes.extend(part.pop('nodes'));model_reports.append(part)
        print('EXPORTED_MODEL',file,part['bytes'],part['triangles'],flush=True)
    report={'file':str(OUT/(TRACK+'.kn5')),'bytes':sum(r['bytes'] for r in model_reports),'mesh_nodes':sum(r['mesh_nodes'] for r in model_reports),'triangles':sum(r['triangles'] for r in model_reports),'materials':len(export_materials),'embedded_textures':len(textures),'nodes':all_nodes,'model_files':model_reports,'separate_model_files':True}
    (OUT/'models.ini').write_text('\n'.join(f'[MODEL_{i}]\nFILE={Path(r["file"]).name}\nPOSITION=0,0,0\nROTATION=0,0,0\n' for i,r in enumerate(model_reports)),encoding='utf-8')
else:report=export(OUT/(TRACK+'.kn5'),objects,export_materials,textures,dummies)
report.update(source_sheet=prepared.get('sheet',prepared.get('sheets')),scenery_triangle_counts=dict(counts),source_scenery_objects=records,placeholder_buildings_removed=removed_buildings,
              physics_meshes_unchanged=True,physics_mesh_fingerprints=physics_after,spawn_matrices_unchanged=True,
              visual_ground_transition={'underlay_vertices_adjusted':ground_transition_vertices,'road_blend_distances_m':[11,24 if FULL_ROUTE else 38],'tile_edge_blend_distance_m':35,'source_terrain_changed_for_visual_blending_only':True},
              limitations=(['Scenery covers the test loop and its surroundings, not the full 6 x 6 km regional road network.','Temporary road widths/profile and synthetic barriers remain.','Photogrammetry is rough close up; imported scenery is visual-only.','Engine driving and FPS checks remain for the user.'] if FULL_ROUTE else ['Real scenery sample covers only one 750 x 600 m tile.','Source terrain and temporary road profile have different heights.','Source geometry is visual only; driving validation remains pending.']))
(REPORTS/'kn5_export.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
scene['stage']='0.3 FULL LOOP SCENERY; USER GAME TEST PENDING' if FULL_ROUTE else '0.2 CSDI REAL SCENERY SAMPLE — ONE TILE; USER GAME TEST PENDING'
scene['source_attribution']='Map from Lands Department; © HKSAR Government; https://3d.map.gov.hk/ ; © OpenStreetMap contributors'
scene['csdi_sample_sheet']=','.join(prepared['sheets']) if FULL_ROUTE else prepared['sheet'];scene['road_collision_unchanged']=True
text=bpy.data.texts.new('CSDI_SAMPLE_README.txt');text.write('CSDI real scenery sample: tile 6-NE-12D, 750 x 600 metres.\nMap from Lands Department; Government of the Hong Kong SAR owns source data IP.\nSource: https://3d.map.gov.hk/ and CSDI dataset landsd_rcd_1671676915450_88604.\nScenery is cropped 11 m from the temporary road centreline; all original collision and spawn data retained.\nVisual terrain is blended near the road and tile boundary to join the temporary profile; it is not a new surveyed road deck.\nIncomplete scenery coverage and rough photogrammetry remain.\nOptimised texture cap: 2048 pixels. Source missing texture is recorded in prepared_manifest.json.\nActual Assetto Corsa driving/FPS validation is pending the user.\n')
if FULL_ROUTE:
    text.clear();text.write('KAM TIN FULL LOOP TEST 0.3\n3.445 km connected route; 8 LandsD source tiles cover the entire loop.\nMap from Lands Department; source data © Government of the Hong Kong SAR.\nSource: https://3d.map.gov.hk/ . Roads © OpenStreetMap contributors.\nDDS BC1 textures include complete mip chains; all large assets remain local.\nOriginal road, pit, barrier collision and spawn/timing nodes are retained.\nVisual scenery is cropped away from the road; photogrammetry and terrain blends remain approximate.\nUse Practice, one car, clear daytime, start from pits. No AI or traffic.\nActual game loading/driving/FPS tests are pending the user.\n')
cam=scene.camera;cam.data.type='PERSP';cam.data.lens=35
target=Vector((-915,-275,10));cam.location=target+Vector((200,-350,250));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.clip_end=15000
if FULL_ROUTE:
    target=Vector((float(route_points[:,0].mean()),float(route_points[:,1].mean()),15));cam.location=target+Vector((1000,-1300,1350));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=2200
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='TEXTURE'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender'/('HK01_KamTin_FULL_LOOP_TEST.blend' if FULL_ROUTE else 'HK01_KamTin_CSDI_SAMPLE.blend')),compress=True)
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.filepath=str(REPORTS/'csdi_sample_overview.png');bpy.ops.render.render(write_still=True)
cam.data.type='PERSP'
route=np.load(BUILD/'route_geometry.npz')['center'];i=int(np.linalg.norm(route[:,:2]-np.array([-900,-50]),axis=1).argmin());p=route[i];t=route[(i+3)%len(route)]-route[i-3];t[2]=0;t/=np.linalg.norm(t)
cam.location=Vector(p)-Vector(t)*10+Vector((0,0,2.5));target=Vector(p)+Vector(t)*35+Vector((0,0,.5));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=32
scene.render.filepath=str(REPORTS/'csdi_sample_road.png');bpy.ops.render.render(write_still=True)
if FULL_ROUTE:
    scene.cycles.samples=8;scene.render.resolution_x=1000;scene.render.resolution_y=625
    for checkpoint,index in enumerate([c['route_sample'] for c in checkpoints]):
        p=route[index];t=route[(index+3)%len(route)]-route[(index-3)%len(route)];t[2]=0;t/=np.linalg.norm(t)
        cam.location=Vector(p)-Vector(t)*5+Vector((0,0,2.0));target=Vector(p)+Vector(t)*30+Vector((0,0,.7));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(REPORTS/f'checkpoint_{checkpoint+1:02d}.png');bpy.ops.render.render(write_still=True)
print('CSDI_BUILD_COMPLETE',json.dumps({k:v for k,v in report.items() if k not in ['nodes','source_scenery_objects','physics_mesh_fingerprints']}),flush=True)
