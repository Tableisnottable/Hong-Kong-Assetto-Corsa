"""Render actual per-skin E200 Content Manager thumbnails from local assets."""
import bpy,sys,math,json
from pathlib import Path
import numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'work'))
from kn5_tools import Kn5
CAR=ROOT/'outputs/E200_playable/content/cars/kmb_e200_drivable'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'outputs/E200_playable/preview/KMB_E200_AAU_preview.blend'))
scene=bpy.context.scene
scene.render.threads_mode='FIXED';scene.render.threads=8
scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=32
scene.render.resolution_x=1022;scene.render.resolution_y=575;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='JPEG';scene.render.image_settings.quality=92
old=Kn5(ROOT/'outputs/E200_playable/backups/before_route_displays/kmb_e200_drivable.kn5')
remove={n.name for _,n in old.root.walk() if n.kind==2 and ('SuperNewHanoverSystem_Head__' in n.name or ('SuperNewHanoverSystem_Side__' in n.name and n.material_id==19))}
for obj in list(scene.objects):
 if obj.name in remove or obj.name.startswith('KMB_DESTINATION_'):bpy.data.objects.remove(obj,do_unlink=True)
for obj in scene.objects:
 if 'dash_driverseat__' in obj.name:obj.location.y-=.30
model=Kn5(CAR/'kmb_e200_drivable.kn5')
panels={}
for _,n in model.root.walk():
 if n.kind!=2 or not n.name.startswith('KMB_DESTINATION_'):continue
 face=n.name.removeprefix('KMB_DESTINATION_').lower()
 v=n.vertices
 idx=np.frombuffer(n.payload,dtype='<u2',count=n.index_count,offset=n.vertex_offset+n.vertex_count*n.vertex_stride+4).reshape(-1,3)
 points=v[:,:3][:,[0,2,1]]*[-1,1,1]
 mesh=bpy.data.meshes.new(n.name);mesh.from_pydata(points.tolist(),[],idx.tolist());mesh.update()
 uv=mesh.uv_layers.new(name='UVMap');coords=v[:,6:8][idx.flatten()].copy();coords[:,1]=1-coords[:,1]
 uv.data.foreach_set('uv',coords.flatten())
 material=bpy.data.materials.new(n.name+'_preview');material.use_nodes=True
 bsdf=material.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Roughness'].default_value=.8
 tex=material.node_tree.nodes.new('ShaderNodeTexImage');tex.interpolation='Closest'
 material.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
 material.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Emission Color']);bsdf.inputs['Emission Strength'].default_value=.5
 mesh.materials.append(material)
 obj=bpy.data.objects.new(n.name,mesh);scene.collection.objects.link(obj)
 panels[face]=tex
assert len(panels)==3
camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=7.4
target=Vector((0,0,.1));camera.location=target+Vector((11,17,6))
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.film_transparent=False
for skin in sorted((CAR/'skins').iterdir()):
 if not skin.is_dir():continue
 for face,tex in panels.items():
  tex.image=bpy.data.images.load(str(skin/f'kmb_destination_{face}.dds'),check_existing=False)
 scene.render.filepath=str(skin/'preview.jpg')
 bpy.ops.render.render(write_still=True)
 print('SKIN_PREVIEW_COMPLETE',skin.name,flush=True)
