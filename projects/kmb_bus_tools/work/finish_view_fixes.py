"""Remove baked OMSI weather overlays and frame car-local exterior views."""
from pathlib import Path
import configparser,json,math,shutil,datetime
import numpy as np
from kn5_tools import Kn5

ROOT=Path(__file__).resolve().parent.parent
for label in ['E200','E6M']:
 car=ROOT/f'outputs/{label}_playable/content/cars/kmb_{label.lower()}_drivable'
 p=car/(car.name+'.kn5');k=Kn5(p);disabled=[]
 if label=='E6M':
  for _,n in k.root.walk():
   if n.kind!=2:continue
   maps=k.materials[n.material_id]['maps']
   if any(m['texture'].lower() in ['regen.tga','rain_static.tga','rain_anim.tga'] for m in maps):
    n.active=False;disabled.append(n.name)
  k.write(p)
 report=json.loads((ROOT/f'outputs/{label}_playable/cockpit_systems_report.json').read_text())
 lo,hi=np.array(report['body_bounds']);center=(lo+hi)/2
 cp=configparser.ConfigParser();cp.optionxform=str;cp.read(car/'data/cameras.ini')
 def view(i,pos,target):
  f=np.array(target)-pos;f/=np.linalg.norm(f);up=np.array([0.,1,0]);up-=f*np.dot(f,up);up/=np.linalg.norm(up)
  fmt=lambda v:','.join(f'{x:.6f}' for x in v)
  cp[f'CAMERA_{i}'].update(POSITION=fmt(pos),FORWARD=fmt(f),UP=fmt(up))
 # Use the vertical FOV and aspect ratio to frame the complete bus with margins.
 height=hi[1]-lo[1];length=hi[2]-lo[2]
 frontDistance=max(4.,height/(2*math.tan(math.radians(28)))*1.25)
 sideDistance=max(5.,length/(2*math.tan(math.radians(28))*16/9)*1.20)
 view(2,np.array([center[0],center[1],hi[2]+frontDistance]),center)
 view(3,np.array([hi[0]+sideDistance,center[1],center[2]]),center)
 view(4,np.array([lo[0]-sideDistance,center[1],center[2]]),center)
 view(5,np.array([center[0],center[1],lo[2]-frontDistance]),center)
 with (car/'data/cameras.ini').open('w') as f:cp.write(f,space_around_delimiters=False)
 (ROOT/f'outputs/{label}_playable/view_fixes_report.json').write_text(json.dumps({'disabled_baked_weather_meshes':disabled,'camera_config':str(car/'data/cameras.ini'),'runtime_test':'pending user test'},indent=2))
 print(label,'exterior views reframed;',len(disabled),'baked weather meshes disabled')
