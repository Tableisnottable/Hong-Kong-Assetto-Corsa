"""Build a separate local E6M driving prototype; never modify its source mod."""
import configparser
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import struct

import numpy as np
from kn5_tools import Kn5, Node

ROOT = Path(__file__).resolve().parent.parent
AC = Path('A:/SteamLibrary/steamapps/common/assettocorsa')
SOURCE = AC / 'content/cars/kmb_e6m_traffic'
CAR_ID = 'kmb_e6m_drivable'
PACKAGE = ROOT / 'outputs/E6M_playable'
CAR = PACKAGE / 'content/cars' / CAR_ID
CG_Y = 1.20
FRONT_Z, DRIVE_Z = 3.1324145, -1.6285136
TYRE_RADIUS = 0.9985 / 2
ENGINE_CURVE = [(0, 0), (700, 900), (1200, 1500), (1400, 1500),
                (1600, 1430), (1700, 1300), (1800, 1230),
                (2100, 1136), (2350, 0)]
SHIFT = np.array([0, CG_Y, (FRONT_Z + DRIVE_Z)/2])
WB = FRONT_Z - DRIVE_Z
CAR.mkdir(parents=True, exist_ok=True)
(CAR/'data').mkdir(exist_ok=True)
(CAR/'sfx').mkdir(exist_ok=True)
(CAR/'ui').mkdir(exist_ok=True)
(CAR/'extension').mkdir(exist_ok=True)


def put(name, text):
    (CAR/name).write_text(text.strip()+'\n', encoding='utf-8')


def ini(name, changes, remove=()):
    p = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=(';',), strict=False)
    p.optionxform = str
    p.read(SOURCE/'data'/name, encoding='utf-8-sig')
    for section in remove:
        p.remove_section(section)
    for section, values in changes.items():
        if not p.has_section(section):p.add_section(section)
        for key, value in values.items():p.set(section, key, str(value))
    with (CAR/'data'/name).open('w',encoding='utf-8') as f:p.write(f, space_around_delimiters=False)


def bound(n):
    v=n.vertices[:,:3]
    center=(v.min(0)+v.max(0))/2
    radius=float(np.linalg.norm(v-center,axis=1).max())
    offset=n.vertex_offset+n.vertex_count*n.vertex_stride+4+n.index_count*2+4+4+8
    struct.pack_into('<4f',n.payload,offset,*center,radius)


model=Kn5(SOURCE/'kmb_e6m_traffic.kn5')
buckets={}
original_active=[]


def flatten(n, world=np.eye(4), ancestors=(), active=True):
    active=active and n.active
    if n.kind==1:world=n.matrix@world
    else:
        if n.kind!=2:raise ValueError('Unexpected skinned mesh')
        n=copy.deepcopy(n)
        n.active=active
        v=n.vertices
        v[:,:3]=(np.c_[v[:,:3],np.ones(len(v))]@world)[:,:3]-SHIFT
        normal_matrix=np.linalg.inv(world[:3,:3]).T
        for sl in (slice(3,6),slice(8,11)):
            transformed=v[:,sl]@normal_matrix
            lengths=np.linalg.norm(transformed,axis=1)
            transformed/=np.maximum(lengths[:,None],1e-10)
            v[:,sl]=transformed
        bound(n)
        group=next((a for a in reversed(ancestors) if not a.startswith(('WHEEL_','HUB_')) and a!=model.root.name), 'body')
        buckets.setdefault(group,[]).append(n)
    for child in n.children:flatten(child,world,ancestors+(n.name,),active)


flatten(model.root)
newroot=Node.dummy(CAR_ID)
wheel_report={}
wheel_defs=[('LF','whl0','whl0_hub1'),('RF','whl1','whl1_hub1'),
            ('LR','whl2_w',None),('RR','whl2r_w',None)]
for suffix,group,hub in wheel_defs:
    meshes=buckets.pop(group)
    if hub:meshes+=buckets.pop(hub,[])
    p=np.concatenate([n.vertices[:,:3] for n in meshes])
    # Use the tyre group's measured center, before adding hub covers.
    center=(p.min(0)+p.max(0))/2
    for n in meshes:n.vertices[:,:3]-=center;bound(n)
    wheel=Node.dummy('WHEEL_'+suffix,meshes)
    # AC expects HUB to carry the center, with WHEEL and SUSP underneath it.
    newroot.children.append(Node.dummy('HUB_'+suffix,[Node.dummy('SUSP_'+suffix),wheel],center))
    wheel_report[suffix]=center.tolist()
for suffix,group,hub in [('LR','whl3','whl3_hub1'),('RR','whl3r','whl3r_hub1')]:
    meshes=buckets.pop(group)+buckets.pop(hub,[])
    p=np.concatenate([n.vertices[:,:3] for n in meshes]);center=(p.min(0)+p.max(0))/2
    for n in meshes:n.vertices[:,:3]-=center;bound(n)
    newroot.children.append(Node.dummy('E6M_TAG_'+suffix,meshes,center))


def instrument(group, name, pivot_world, axis=None):
    meshes=buckets.pop(group,[])
    if not meshes:return
    p=np.concatenate([n.vertices[:,:3] for n in meshes])
    center=np.array(pivot_world)-SHIFT
    if axis is None:
        _,_,vh=np.linalg.svd(p-p.mean(0),full_matrices=False)
        axis=vh[-1]
        if axis[2]<0:axis=-axis
    axis=np.array(axis,dtype=float);axis/=np.linalg.norm(axis)
    x=np.array([1.,0.,0.]);y=np.cross(axis,x);y/=np.linalg.norm(y);x=np.cross(y,axis)
    rotation=np.array([x,y,axis])
    matrix=np.eye(4,dtype='<f4');matrix[:3,:3]=rotation;matrix[3,:3]=center
    for n in meshes:
        v=n.vertices;v[:,:3]=(v[:,:3]-center)@rotation.T
        v[:,3:6]=v[:,3:6]@rotation.T;v[:,8:11]=v[:,8:11]@rotation.T;bound(n)
    newroot.children.append(Node(1,name,True,bytearray(matrix.tobytes()),meshes))


instrument('dash_strw','STEER_HR',[-.7505,1.6505,4.7441])
instrument('dash_speedo','ARROW_SPEED',[-.5633,1.5454,5.01311])
instrument('dash_rpm','ARROW_RPM',[-.8702,1.5454,5.01311])
for name,meshes in buckets.items():newroot.children.append(Node.dummy(name,meshes))
model.root=newroot
model.write(CAR/(CAR_ID+'.kn5'))

# Adapt the existing simple collision hull to the new model origin and body size.
collider=Kn5(SOURCE/'collider.kn5')
for _,n in collider.root.walk():
    if n.kind==1:n.payload=bytearray(np.eye(4,dtype='<f4').tobytes())
    else:
        v=n.vertices[:,:3];lo=v.min(0).copy();hi=v.max(0).copy()
        v[:]=(v-lo)/(hi-lo)*(np.array([2.48,3.95,10.55]))+np.array([-1.24,.30,-5.40])-SHIFT
        bound(n)
collider.write(CAR/'collider.kn5')

for f in ['body_shadow.png','tyre_0_shadow.png','tyre_1_shadow.png','tyre_2_shadow.png','tyre_3_shadow.png','logo.png']:
    if (SOURCE/f).exists():shutil.copy2(SOURCE/f,CAR/f)
shutil.copytree(SOURCE/'skins/0_kmb',CAR/'skins/0_kmb',dirs_exist_ok=True)
# Its donor skin contains old Volvo textures/config; all correct E6M textures are embedded.
for f in (CAR/'skins/0_kmb').glob('3asv_*.dds'):f.unlink()
for f in ['ext_config.ini','cm_skin.json']:
    if (CAR/'skins/0_kmb'/f).exists():(CAR/'skins/0_kmb'/f).unlink()
skin={'skinname':'KMB E6M','drivername':'','country':'Hong Kong','number':''}
(CAR/'skins/0_kmb/ui_skin.json').write_text(json.dumps(skin,indent=2),encoding='utf-8')

# Retain a complete valid base schema and change only the prototype parameters.
for f in SOURCE.joinpath('data').glob('*.lut'):shutil.copy2(f,CAR/'data'/f.name)
for f in ['ambient_shadows.ini','mirrors.ini','sounds.ini']:
    shutil.copy2(SOURCE/'data'/f,CAR/'data'/f)
put('data/mirrors.ini','''[MIRROR_0]
NAME=Mirror_Left

[MIRROR_1]
NAME=Mirror_Center

[MIRROR_2]
NAME=Mirror_Right''')
ini('car.ini',{
 'INFO':{'SCREEN_NAME':'KMB E6M Playable Prototype'},
 'BASIC':{'GRAPHICS_OFFSET':'0,0,0','TOTALMASS':14800,'INERTIA':'2.50,4.30,11.38'},
 'GRAPHICS':{'DRIVEREYES':f'-.755,{2.18-CG_Y:.6f},{4.50-SHIFT[2]:.6f}',
  'ON_BOARD_PITCH_ANGLE':0,'ONBOARD_EXPOSURE':30,'OUTBOARD_EXPOSURE':30,
  'BUMPER_CAMERA_POS':f'0,.65,{5.65-SHIFT[2]:.6f}',
  'BONNET_CAMERA_POS':f'-.755,{2.2-CG_Y:.6f},{5.1-SHIFT[2]:.6f}',
  'BUMPER_CAMERA_PITCH':0,'BONNET_CAMERA_PITCH':0,'SHAKE_MUL':.25,'USE_ANIMATED_SUSPENSIONS':0},
 'CONTROLS':{'STEER_LOCK':720,'STEER_RATIO':-20,'FFMULT':.12},
 'FUEL':{'FUEL':50,'MAX_FUEL':350},
 'FUELTANK':{'POSITION':'0,-.35,-1.5'},
})
ini('suspensions.ini',{
 'BASIC':{'WHEELBASE':f'{WB:.7f}','CG_LOCATION':.5},
 'ARB':{'FRONT':80000,'REAR':50000},
 'FRONT':{'BASEY':f'{.501975-CG_Y:.6f}','TRACK':2.213236,'ROD_LENGTH':.135,
   'HUB_MASS':170,'SPRING_RATE':260000,'BUMP_STOP_RATE':800000,
   'BUMPSTOP_UP':.18,'BUMPSTOP_DN':.16,'PACKER_RANGE':.25,
   'DAMP_BUMP':17000,'DAMP_REBOUND':24000,'DAMP_FAST_BUMP':10000,'DAMP_FAST_REBOUND':14000},
 'REAR':{'BASEY':f'{.5005155-CG_Y:.6f}','TRACK':1.986462,'ROD_LENGTH':.087,
   'HUB_MASS':300,'SPRING_RATE':400000,'BUMP_STOP_RATE':1000000,
   'BUMPSTOP_UP':.18,'BUMPSTOP_DN':.16,'PACKER_RANGE':.25,
   'DAMP_BUMP':23000,'DAMP_REBOUND':32000,'DAMP_FAST_BUMP':14000,'DAMP_FAST_REBOUND':19000},
 'DAMAGE':{'DEBUG_LOG':0},
},remove=['HEAVE_FRONT','HEAVE_REAR'])
ini('tyres.ini',{
 'FRONT':{'NAME':'Bus road','SHORT_NAME':'BUS','WIDTH':.315,'RADIUS':TYRE_RADIUS,'RIM_RADIUS':.28575,
  'ANGULAR_INERTIA':13,'DAMP':2500,'RATE':1200000,'FZ0':34500,'DY_REF':.92,'DX_REF':.95,
  'DY0':.92,'DX0':.95,'SPEED_SENSITIVITY':.001,'RELAXATION_LENGTH':.32,
  'PRESSURE_STATIC':120,'PRESSURE_IDEAL':120,'RADIUS_ANGULAR_K':.001,
  'LS_EXPY':.94,'LS_EXPX':.96},
 'REAR':{'NAME':'Bus road','SHORT_NAME':'BUS','WIDTH':.55,'RADIUS':TYRE_RADIUS,'RIM_RADIUS':.28575,
  'ANGULAR_INERTIA':24,'DAMP':4000,'RATE':1800000,'FZ0':34500,'DY_REF':.92,'DX_REF':.95,
  'DY0':.92,'DX0':.95,'SPEED_SENSITIVITY':.001,'RELAXATION_LENGTH':.38,
  'PRESSURE_STATIC':120,'PRESSURE_IDEAL':120,'RADIUS_ANGULAR_K':.001,
  'LS_EXPY':.94,'LS_EXPX':.96},
})
ini('drivetrain.ini',{
 'GEARS':{'COUNT':6,'GEAR_R':-4.235,'GEAR_1':3.364,'GEAR_2':1.909,'GEAR_3':1.421,
  'GEAR_4':1.,'GEAR_5':.720,'GEAR_6':.615,'FINAL':6.20},
 'GEARBOX':{'SUPPORTS_SHIFTER':0,'CHANGE_UP_TIME':250,'CHANGE_DN_TIME':300,'AUTO_CUTOFF_TIME':250},
 'CLUTCH':{'MAX_TORQUE':2500},
 'AUTOCLUTCH':{'MIN_RPM':800,'MAX_RPM':1200,'FORCED_ON':1},
 'AUTO_SHIFTER':{'UP':2150,'DOWN':1100,'GAS_CUTOFF_TIME':.25},
 'DIFFERENTIAL':{'POWER':.15,'COAST':.10,'PRELOAD':20},
})
ini('engine.ini',{'ENGINE_DATA':{'LIMITER':2350,'LIMITER_HZ':30,'MINIMUM':700,'INERTIA':2},
 'COAST_REF':{'RPM':2100,'TORQUE':250},},remove=['TURBO_0'])
put('data/power.lut','\n'.join(f'{rpm}|{torque}' for rpm,torque in ENGINE_CURVE))
put('data/coast.lut','0|0\n2400|285')
put('data/brakes.ini','''[HEADER]
VERSION=1
[DATA]
MAX_TORQUE=26000
FRONT_SHARE=0.52
HANDBRAKE_TORQUE=18000
COCKPIT_ADJUSTABLE=0
ADJUST_STEP=0.1''')
ini('electronics.ini',{'ABS':{'PRESENT':1,'ACTIVE':1},'TRACTION_CONTROL':{'PRESENT':0,'ACTIVE':0}})
ini('aero.ini',{'WING_0':{'CHORD':4.15,'SPAN':2.5,'POSITION':'0,0,0','CD_GAIN':.72,'CL_GAIN':0}})
put('data/lods.ini',f'''[COCKPIT_HR]
DISTANCE_SWITCH=0
[LOD_0]
FILE={CAR_ID}.kn5
IN=0
OUT=2000''')
put('data/dash_cam.ini',f'[DASH_CAM]\nPOS=-.755,{2.18-CG_Y:.6f},{4.50-SHIFT[2]:.6f}\nEXP=30')
put('data/colliders.ini',f'''[COLLIDER_0]
CENTRE=0,{2.275-CG_Y:.6f},{-.125-SHIFT[2]:.6f}
SIZE=2.48,3.95,10.55
GROUND_ENABLE=1''')
put('data/analog_instruments.ini','''[RPM_INDICATOR]
OBJECT_NAME=ARROW_RPM
ZERO=0
MIN_VALUE=0
STEP=0.0833333
[SPEED_INDICATOR]
OBJECT_NAME=ARROW_SPEED
ZERO=0
STEP=2.0833333''')
put('data/lights.ini','[HEADER]\nVERSION=3')
put('data/setup.ini','''[DISPLAY_METHOD]
SHOW_CLICKS=0
[FUEL]
SHOW_CLICKS=0
TAB=GENERIC
NAME=Fuel
MIN=5
MAX=350
STEP=5
POS_X=0
POS_Y=0''')
ini('ai.ini',{'GEARS':{'UP':2150,'DOWN':1100},'STEER':{'STEER_GAIN':1.2}})
# Hide the generic race driver below the bus; no mismatched donor animation is used.
put('data/driver3d.ini','[MODEL]\nNAME=driver\nPOSITION=0,-20,0')
shutil.copy2(SOURCE/'sfx/kmb_e6m_traffic.bank',CAR/'sfx'/f'{CAR_ID}.bank')
guids=(SOURCE/'sfx/GUIDs.txt').read_text(encoding='utf-8-sig')
put('sfx/GUIDs.txt',guids.replace('kmb_e6m_traffic',CAR_ID))
put('extension/ext_config.ini','''; The original KN5 already contains its corrected glass materials.
; Tag axle is visual only: native physics uses front and middle driven axle.
[BASIC]
IS_HIGH_BEAM_SUPPORTED=0
[SCRIPT_...]
SCRIPT="
local car = ac.getCar()
if not car then return end
local root = ac.findNodes('carRoot:' .. car.index)
if not root then return end
local left = root:findNodes('E6M_TAG_LR')
local right = root:findNodes('E6M_TAG_RR')
local angle = 0
function update(dt)
  if not car then return end
  angle = (angle + car.speedKmh / 3.6 / 0.49925 * dt) % (2 * math.pi)
  if left then left:setRotation(vec3(1, 0, 0), angle) end
  if right then right:setRotation(vec3(1, 0, 0), angle) end
end
"''')
ui={'name':'KMB E6M Playable Prototype','brand':'Alexander Dennis','country':'United Kingdom',
 'description':'Assetto Corsa conversion using the supplied OMSI E6M engine, axle and gearbox data. Physics are adapted to AC; the OMSI 69-71 km/h governor is omitted. The third axle is visual, and OMSI controls, ticketing and passengers are not converted.',
 'tags':['bus','KMB','Hong Kong','E6M','prototype'],'class':'street',
 'specs':{'bhp':'335 bhp','torque':'1500 Nm','weight':'14800 kg','topspeed':'~110 km/h (gearing; governor omitted)','acceleration':'Prototype','pwratio':'44 kg/hp'},
 'torqueCurve':[list(point) for point in ENGINE_CURVE],
 'powerCurve':[[rpm,round(t*rpm/7127,1)] for rpm,t in ENGINE_CURVE]}
(CAR/'ui/ui_car.json').write_text(json.dumps(ui,indent=2),encoding='utf-8')

all_nodes=[n for _,n in model.root.walk()]
report={'car_id':CAR_ID,'source_sha256':hashlib.file_digest(open(SOURCE/'kmb_e6m_traffic.kn5','rb'),'sha256').hexdigest(),
 'model_origin_shift':SHIFT.tolist(),'wheelbase':WB,'native_wheel_centers':wheel_report,
 'mesh_count':sum(n.kind==2 for n in all_nodes),'triangles':sum(n.index_count//3 for n in all_nodes),
 'native_physics_axles':['front','middle driven'],'third_axle':'visual CSP animation',
 'omsi_source_values':{'mass_kg':14800,'wheel_diameter_m':0.9985,'wheel_radius_m':TYRE_RADIUS,
  'engine_curve_rpm_nm':ENGINE_CURVE,'source_engine_governor_kmh':[69,71],
  'ac_governor':'omitted by design'},
 'status':'Built from OMSI source data; in-game handling and CSP animation not verified','limitations':['Approximate physics; rear two axles represented by one physical axle',
 'No OMSI script runtime, ticketing, passengers, kneeling, door logic or clickable dashboard',
 'Existing installed bus audio reused for this local prototype; no redistribution package']}
(PACKAGE/'build_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'package':str(PACKAGE),'car':str(CAR),'wheelbase':WB,'wheel_centers':wheel_report,'meshes':report['mesh_count'],'triangles':report['triangles']}))
