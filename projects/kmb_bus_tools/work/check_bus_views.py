"""Render and probe each staged AC car-local view using its current KN5."""
import bpy,sys,json,math,runpy,configparser
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent
label=sys.argv[sys.argv.index('--')+1]
car=ROOT/f'outputs/{label}_playable/content/cars/kmb_{label.lower()}_drivable'
out=ROOT/f'outputs/{label}_playable/preview/ac_views';out.mkdir(exist_ok=True)
sys.argv=['preview_kn5.py','--',str(car),str(out),'--quick']
runpy.run_path(str(ROOT/'work/preview_kn5.py'),run_name='__main__')
scene=bpy.context.scene;camera=scene.camera;camera.data.type='PERSP'
config=configparser.ConfigParser();config.read(car/'data/cameras.ini')
deps=bpy.context.evaluated_depsgraph_get();reports=[]
for section in config.sections():
 c=config[section];pos=[float(x) for x in c['POSITION'].split(',')];d=[float(x) for x in c['FORWARD'].split(',')]
 position=Vector((-pos[0],pos[2],pos[1]));direction=Vector((-d[0],d[2],d[1])).normalized()
 origin=position.copy();hits=[]
 for _ in range(8):
  hit,p,normal,idx,obj,matrix=scene.ray_cast(deps,origin,direction,distance=20)
  if not hit:break
  hits.append({'mesh':obj.name,'distance':(p-position).length})
  origin=p+direction*.003
 if section=='CAMERA_0':
  assert not any('driverseat' in h['mesh'] for h in hits),'Cockpit is inside seat'
  assert not any(h['distance']<.10 for h in hits),'Geometry clips cockpit camera'
 if section=='CAMERA_1':
  assert not any(h['mesh']!='PREVIEW_Ground' for h in hits),'Rear view is blocked by bus'
 camera.location=position;camera.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
 camera.data.sensor_fit='VERTICAL';camera.data.sensor_height=24
 camera.data.lens=24/(2*math.tan(math.radians(float(c['FOV']))/2))
 scene.render.filepath=str(out/(section.lower()+'.png'));bpy.ops.render.render(write_still=True)
 reports.append({'view':section,'position':pos,'forward':d,'ray_hits':hits,'render':scene.render.filepath})
# Check the driver's useful side glances and native bumper direction too.
graphics=configparser.ConfigParser();graphics.read(car/'data/car.ini');g=graphics['GRAPHICS']
eye=[float(x) for x in g['DRIVEREYES'].split(',')]
for name,yaw in [('look_left',65),('look_right',-65)]:
 rad=math.radians(yaw);camera.location=Vector((-eye[0],eye[2],eye[1]))
 direction=Vector((-math.sin(rad),math.cos(rad),-.08)).normalized()
 camera.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
 scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
 reports.append({'view':name,'render':scene.render.filepath})
def render_view(name,pos,direction,fov=56):
 camera.location=Vector((-pos[0],pos[2],pos[1]));direction=Vector((-direction[0],direction[2],direction[1])).normalized()
 camera.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
 camera.data.lens=24/(2*math.tan(math.radians(fov)/2))
 scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
 reports.append({'view':name,'position':list(pos),'render':scene.render.filepath})
bumper=[float(x) for x in g['BUMPER_CAMERA_POS'].split(',')]
render_view('bumper',bumper,[0,0,1])
bonnet=[float(x) for x in g['BONNET_CAMERA_POS'].split(',')];rad=math.radians(float(g['BONNET_CAMERA_PITCH']))
render_view('bonnet',bonnet,[0,math.sin(rad),math.cos(rad)])
dash=configparser.ConfigParser();dash.read(car/'data/dash_cam.ini');d=dash['DASH_CAM'];rad=math.radians(float(d['PITCH_ANGLE']))
render_view('dashboard',[float(x) for x in d['POS'].split(',')],[0,math.sin(rad),math.cos(rad)])
render_view('cockpit_look_back',eye,[0,0,-1])
mirror=[float(x) for x in g['MIRROR_POSITION'].split(',')]
render_view('virtual_mirror_origin',mirror,[0,0,-1])
# Nominal straight-ahead placement of the installed CSP base camera variant.
# Dynamic yaw/lag depend on motion and are not reproduced by Blender.
for i,(distance,height) in enumerate([(12.5,2.4),(16,3.2)] if label=='E200' else [(14,2.8),(18,3.8)]):
 pos=Vector((0,height,-distance));target=Vector((0,1,1));direction=(target-pos).normalized()
 # Base camera applies its default pitch correction around the car right axis.
 from mathutils import Quaternion
 pitch=math.radians((2 if i==0 else -1)-5);direction=Quaternion(Vector((-1,0,0)),pitch)@direction
 render_view('chase_'+str(i),pos,direction,60)
(out/'views_report.json').write_text(json.dumps({'status':'PASS','views':reports,'limits':'Offline geometry/camera checks; AC and CSP runtime verification remains pending'},indent=2))
print('ALL_VIEWS_QA_COMPLETE',label,flush=True)
