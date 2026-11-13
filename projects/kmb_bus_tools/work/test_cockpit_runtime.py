"""Exercise CSP cockpit Lua with real KN5 bindings and controlled telemetry."""
from pathlib import Path
import sys,json,math
sys.path.insert(0,str(Path(__file__).parent/'test_runtime'))
from lupa import LuaRuntime
from kn5_tools import Kn5
ROOT=Path(__file__).resolve().parent.parent
MOCK=r'''
states, drawn, clickQueue, actions = {}, {}, {}, {}
function vec2(x,y) return {x=x,y=y} end
function vec3(x,y,z) return {x=x,y=y,z=z} end
function rgb(r,g,b) return {r=r,g=g,b=b} end
function rgbm(r,g,b,m) return {r=r,g=g,b=b,m=m} end
local function reference(name)
  assert(valid[name], 'Missing node or mesh: '..name)
  states[name] = states[name] or {}
  return {
    setRotation=function(self,axis,angle) states[name].rotation=angle end,
    ensureUniqueMaterials=function(self) return self end,
    setMaterialProperty=function(self,key,value) states[name][key]=value end
  }
end
ac={TurningLights={None=0,Left=1,Right=2,Hazards=3}}
function ac.findNodes(name)
 assert(name=='carRoot:0')
 return {findNodes=function(self,n) if n:find('KMB') or n:find('E6M') then
   if not valid[n] then return {setRotation=function() end} end
 end return reference(n) end,
 findMeshes=function(self,n) return reference(n) end}
end
function ac.setHeadlights(v) actions.headlights=v end
function ac.setTurningLights(v) actions.turn=v end
function ac.switchToNeutralGear() actions.neutral=true end
function ac.setHighBeams(v) actions.highbeam=v end
function ac.setWiperMode(v) actions.wipers=v end
display={}
function display.interactiveMesh(params)
 assert(valid[params.mesh], 'Invalid clickable mesh: '..params.mesh)
 return {clicked=function() return function()
  local v=clickQueue[params.mesh];clickQueue[params.mesh]=nil;return v==true
 end end}
end
function display.text(p) drawn[#drawn+1]=p.text end
function display.rect(p) end
script={}
car={index=0,speedKmh=0,rpm=0,waterTemperature=20,fuel=40,gear=0,handbrake=1,gas=0,brake=0,
 headlightsActive=false,highBeams=false,turningLeftLights=false,turningRightLights=false,
 turningLightsActivePhase=false,turningLeftOnly=false,turningRightOnly=false,hazardLights=false,
 absInAction=false,wiperProgress=0,wiperSelectedMode=0,wiperModes=1,distanceDrivenSessionKm=0,
 batteryVoltage=24}
'''
for label in ['E200','E6M']:
 package=ROOT/f'outputs/{label}_playable';carpath=package/f'content/cars/kmb_{label.lower()}_drivable'
 k=Kn5(carpath/(carpath.name+'.kn5'));valid={n.name:True for _,n in k.root.walk()}
 bindings=json.loads((carpath/'extension/cockpit_bindings.json').read_text())
 runtime=LuaRuntime(unpack_returned_tuples=True);g=runtime.globals();g.valid=runtime.table_from(valid)
 runtime.execute(MOCK);runtime.execute((carpath/'extension/cockpit.lua').read_text())
 g.script.update(.016)
 assert math.isclose(g.states.KMB_SPEED_MOTION.rotation,0,abs_tol=1e-8)
 hb=bindings['indicators']['handbrake'][0]
 assert g.states[hb].ksEmissive.r>0
 g.car.speedKmh=60;g.car.rpm=1400;g.car.gear=3;g.car.handbrake=0;g.car.gas=.5;g.car.brake=.3
 g.car.waterTemperature=90;g.car.headlightsActive=True;g.car.turningLeftLights=True;g.car.turningLightsActivePhase=True
 g.drawn=runtime.table();g.script.update(.016)
 assert math.isclose(g.states.KMB_SPEED_MOTION.rotation,math.radians(112),abs_tol=1e-7)
 assert g.states.KMB_RPM_MOTION.rotation>math.radians(100)
 assert math.isclose(g.states.KMB_TEMP_MOTION.rotation,math.radians(52.5),abs_tol=1e-6)
 assert g.states[hb].ksEmissive.r==0
 assert '060' in list(g.drawn.values()) and 'D3' in list(g.drawn.values())
 if label=='E200':assert math.isclose(g.states.KMB_GAS_MOTION.rotation,math.radians(12.5),abs_tol=1e-7)
 if label=='E6M':
  assert g.states.E6M_TAG_LR.rotation>0
  # Both last wheels advance by the measured radius, stop, and reverse.
  start=g.states.E6M_TAG_LR.rotation;g.car.speedKmh=18;g.script.update(.1)
  advanced=g.states.E6M_TAG_LR.rotation
  assert math.isclose(advanced-start,18/3.6/.49925*.1,abs_tol=1e-6)
  assert math.isclose(advanced,g.states.E6M_TAG_RR.rotation,abs_tol=1e-6)
  g.car.speedKmh=0;g.script.update(.5)
  assert g.states.E6M_TAG_LR.rotation==advanced
  g.car.speedKmh=-18;g.script.update(.1)
  assert math.isclose(g.states.E6M_TAG_LR.rotation,start,abs_tol=1e-6)
 # Telemetry may update in reverse, at the limiter, with lights and with hot coolant.
 g.car.gear=-1;g.car.speedKmh=-12;g.car.rpm=2500;g.car.waterTemperature=115
 g.script.update(.016)
 assert g.states[bindings['indicators']['warning'][0]].ksEmissive.r>0
 # Buttons change their actual AC functions; neutral is interlocked to stationary.
 for key,expected in [('headlights','headlights'),('hazards','turn'),('left','turn'),('right','turn'),('highbeam','highbeam')]:
  g.clickQueue[bindings['buttons'][key]]=True;g.script.update(.016)
  assert g.actions[expected] is not None,key
 g.clickQueue[bindings['buttons']['neutral']]=True;g.script.update(.016);assert g.actions.neutral is None
 g.car.speedKmh=0;g.clickQueue[bindings['buttons']['neutral']]=True;g.script.update(.016);assert g.actions.neutral
 g.clickQueue[bindings['buttons']['wipers']]=True;g.script.update(.016)
 for _ in range(40):g.script.update(.016)
 assert abs(g.states.KMB_WIPER_L.rotation)>.1
 g.clickQueue.KMB_DRIVER_LCD=True;g.drawn=runtime.table();g.script.update(.016)
 assert any('BATTERY' in s for s in g.drawn.values())
 report={'status':'PASS','type':'Lua runtime with mocked CSP API; not an in-game test',
         'verified':['all bound nodes/meshes exist','0 and 60 km/h gauge positions','RPM and temperature movement',
                     'gear and speed display','warning lamp transitions','light/indicator button actions',
                     'stationary neutral interlock','wiper motion','display page switching']+
                    (['both tag wheels rotate forward, stop, reverse at measured radius'] if label=='E6M' else [])}
 (package/'cockpit_runtime_validation.json').write_text(json.dumps(report,indent=2))
 print(label,'cockpit runtime PASS')
