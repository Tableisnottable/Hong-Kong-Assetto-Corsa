"""Offline Blender QA for a native KN5 car and its configured cockpit camera."""
import bpy,sys,io,json,math,struct
from pathlib import Path
from mathutils import Vector
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from kn5_tools import Kn5,read_u32,read_string

ROOT=Path(__file__).resolve().parent.parent
args=sys.argv[sys.argv.index('--')+1:]
car=Path(args[0]).resolve();out=Path(args[1]).resolve();out.mkdir(parents=True,exist_ok=True)
modelpath=next(p for p in car.glob('*.kn5') if p.name!='collider.kn5')
k=Kn5(modelpath)
texdir=ROOT/'work/preview_textures'/car.name;texdir.mkdir(parents=True,exist_ok=True)
with modelpath.open('rb') as f:
    f.seek(6);version=read_u32(f)
    if version>5:f.seek(4,1)
    for _ in range(read_u32(f)):
        active=read_u32(f);name=read_string(f);length=read_u32(f)
        target=texdir/Path(name).name;target.write_bytes(f.read(length))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE'
if '--quick' in args:scene.eevee.taa_render_samples=24
scene.render.threads_mode='FIXED';scene.render.threads=8
scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
images={};materials=[]
for data in k.materials:
    m=bpy.data.materials.new(data['name']);m.use_nodes=True;m.use_backface_culling=True
    shader=m.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.6
    shader.inputs['Specular IOR Level'].default_value=.25
    tex=next((x['texture'] for x in data['maps'] if x['name']=='txDiffuse'),None)
    if tex:
        path=texdir/Path(tex).name
        if path.exists():
            if tex not in images:images[tex]=bpy.data.images.load(str(path))
            node=m.node_tree.nodes.new('ShaderNodeTexImage');node.image=images[tex]
            m.node_tree.links.new(node.outputs['Color'],shader.inputs['Base Color'])
            if data['blend'] or data['alpha_test']:
                m.node_tree.links.new(node.outputs['Alpha'],shader.inputs['Alpha']);m.surface_render_method='DITHERED'
            emissive=data['props'].get('ksEmissive',(0,)*10)
            if max(emissive)>0:
                m.node_tree.links.new(node.outputs['Color'],shader.inputs['Emission Color'])
                shader.inputs['Emission Strength'].default_value=max(emissive[3:6]) or emissive[0]
    materials.append(m)

def to_bl(v):return np.asarray(v)[:,[0,2,1]]*np.array([-1.,1.,1.])
points=[]
def visit(n,w=np.eye(4),active=True):
    active=active and n.active
    if n.kind==1:w=n.matrix@w
    elif n.kind==2 and active and n.vertex_count:
        v=n.vertices
        p=(np.c_[v[:,:3],np.ones(n.vertex_count)]@w)[:,:3]
        p=to_bl(p);points.append(p)
        idxoff=n.vertex_offset+n.vertex_count*44+4
        idx=np.frombuffer(n.payload,dtype='<u2',count=n.index_count,offset=idxoff).reshape(-1,3)
        mesh=bpy.data.meshes.new(n.name);mesh.from_pydata(p.tolist(),[],idx.tolist());mesh.update()
        mesh.materials.append(materials[n.material_id]);mesh.polygons.foreach_set('use_smooth',[True]*len(idx))
        uv=mesh.uv_layers.new(name='UVMap')
        uvdata=v[:,6:8][idx.flatten()].copy();uvdata[:,1]=1-uvdata[:,1]
        uv.data.foreach_set('uv',uvdata.flatten())
        normals=v[:,3:6]@np.linalg.inv(w[:3,:3]).T
        normals=to_bl(normals);normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-10)
        # Blender 5.1 crashes in mesh_set_custom_normals_from_verts on some
        # imported OMSI degenerate faces. Preview uses geometry-derived normals;
        # the actual native KN5 normals are preserved and not changed here.
        obj=bpy.data.objects.new(n.name,mesh);scene.collection.objects.link(obj)
        obj['native_kn5_node']=n.name
    for child in n.children:visit(child,w,active)
visit(k.root)
p=np.concatenate(points);lo=p.min(0);hi=p.max(0);center=Vector(((lo+hi)/2).tolist())
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,float(lo[2])-.02));floor=bpy.context.object;floor.name='PREVIEW_Ground'
floor_mat=bpy.data.materials.new('PREVIEW_Ground');floor_mat.diffuse_color=(.18,.19,.21,1);floor.data.materials.append(floor_mat)
world=bpy.data.worlds.new('PREVIEW_World');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.72,.82,1);world.node_tree.nodes['Background'].inputs[1].default_value=.8;scene.world=world
for name,offset,energy,size in [('Key',(5,8,10),1800,8),('Fill',(-8,1,6),1400,9),('Rim',(3,-8,6),1800,7)]:
    light=bpy.data.lights.new('PREVIEW_'+name,'AREA');light.energy=energy;light.shape='DISK';light.size=size
    obj=bpy.data.objects.new(light.name,light);scene.collection.objects.link(obj);obj.location=center+Vector(offset);obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
camera_data=bpy.data.cameras.new('Cockpit_QA');camera=bpy.data.objects.new(camera_data.name,camera_data);scene.collection.objects.link(camera);scene.camera=camera
camera_data.clip_start=.03;camera_data.clip_end=2000
camera_data.type='ORTHO';camera_data.ortho_scale=max(hi-lo)*1.20
camera.location=center+Vector((12,16,8));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(out/'front.png');bpy.ops.render.render(write_still=True)
camera_data.ortho_scale=2.4
sign=next(n for _,n in k.root.walk() if n.name=='KMB_DESTINATION_FRONT')
sign_center=to_bl(sign.vertices[:,:3]).mean(0)
camera.location=Vector(sign_center.tolist())+Vector((.2,4,.4));camera.rotation_euler=(Vector(sign_center.tolist())-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(out/'front_sign.png');bpy.ops.render.render(write_still=True)
side=next(n for _,n in k.root.walk() if n.name=='KMB_DESTINATION_SIDE')
side_center=Vector(to_bl(side.vertices[:,:3]).mean(0).tolist())
camera_data.ortho_scale=2.4;camera.location=side_center+Vector((-4,0,.2));camera.rotation_euler=(side_center-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(out/'side_sign.png');bpy.ops.render.render(write_still=True)
rear=next(n for _,n in k.root.walk() if n.name=='KMB_DESTINATION_REAR')
rear_center=Vector(to_bl(rear.vertices[:,:3]).mean(0).tolist())
camera.location=rear_center+Vector((0,-4,.2));camera.rotation_euler=(rear_center-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(out/'rear_sign.png');bpy.ops.render.render(write_still=True)
import configparser
config=configparser.ConfigParser(interpolation=None);config.read(car/'data/car.ini')
eyes=[float(x) for x in config['GRAPHICS']['DRIVEREYES'].split(',')]
pitch=float(config['GRAPHICS']['ON_BOARD_PITCH_ANGLE'])
position=Vector((-eyes[0],eyes[2],eyes[1]));direction=Vector((0,math.cos(math.radians(pitch)),math.sin(math.radians(pitch))))
camera_data.type='PERSP';camera_data.sensor_fit='VERTICAL';camera_data.sensor_height=24;camera_data.lens=24/(2*math.tan(math.radians(56)/2))
camera.location=position;camera.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(out/'cockpit.png');bpy.ops.render.render(write_still=True)
if 'e200' in car.name:
    for image in bpy.data.images:
        if image.source=='FILE':image.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'KMB_E200_AAU_preview.blend'),compress=True)
(out/'render_report.json').write_text(json.dumps({'model':str(modelpath),'camera':eyes,'pitch':pitch,'geometry_bounds':[lo.tolist(),hi.tolist()],'mesh_count':len(points),'status':'Offline model renders; not an in-game test'},indent=2))
print('PREVIEW_COMPLETE',str(out),flush=True)
