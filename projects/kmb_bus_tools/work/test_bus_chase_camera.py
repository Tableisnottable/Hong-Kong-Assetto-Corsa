"""Exercise the actual CSP chase script with nominal stationary car transforms."""
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).parent/'test_runtime'))
from lupa import LuaRuntime
ROOT=Path(__file__).resolve().parent.parent
MOCK=r'''
local V={};V.__index=V
function vec3(x,y,z) return setmetatable({x=x or 0,y=y or 0,z=z or 0},V) end
function V.__add(a,b)return vec3(a.x+b.x,a.y+b.y,a.z+b.z)end
function V.__sub(a,b)return vec3(a.x-b.x,a.y-b.y,a.z-b.z)end
function V.__unm(a)return vec3(-a.x,-a.y,-a.z)end
function V.__mul(a,b)if type(a)=='number'then a,b=b,a end return vec3(a.x*b,a.y*b,a.z*b)end
function V.__div(a,b)return a*(1/b)end
function V.__len(a)return math.sqrt(a.x*a.x+a.y*a.y+a.z*a.z)end
function V.__eq(a,b)return a.x==b.x and a.y==b.y and a.z==b.z end
function V:normalize()local l=#self;if l>0 then self.x,self.y,self.z=self.x/l,self.y/l,self.z/l end return self end
function V:rotate(q)
 local c,s=math.cos(q.angle),math.sin(q.angle);local v=self*c+math.cross(q.axis,self)*s+q.axis*(math.dot(q.axis,self)*(1-c))
 self.x,self.y,self.z=v.x,v.y,v.z;return self
end
function math.cross(a,b)return vec3(a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x)end
function math.dot(a,b)return a.x*b.x+a.y*b.y+a.z*b.z end
function math.normalize(a)return a:normalize()end
function math.clamp(v,a,b)return math.max(a,math.min(b,v))end
math.radians=math.rad
function math.pow(a,b)return a^b end
function math.sign(x)return x<0 and -1 or 1 end
quat={fromAngleAxis=function(angle,axis)return {angle=angle,axis=axis}end}
smoothing=setmetatable({setDT=function()end},{__call=function(_,v)return {val=v,update=function(self,x)self.val=x end,updateIfNew=function(self,x)self.val=x end}end})
car={index=0};script={};lookLeft=false;lookRight=false;lookBack=false;busID=''
ac={Camera={}}
function ac.getCarID()return busID end
function ac.getCameraParameters(i)return {distance=i==1 and 3 or 3.9,height=i==1 and 1.4 or 1.9,pitch=i==1 and 2 or -1}end
function ac.getCarPosition()return vec3()end
function ac.getCarDirection()return vec3(0,0,1)end
function ac.getCarUp()return vec3(0,1,0)end
function ac.getCarVelocity()return vec3()end
function ac.getJoystickLook()return nil end
function ac.looksLeft()return lookLeft end
function ac.looksRight()return lookRight end
function ac.looksBehind()return lookBack end
'''
runtime=LuaRuntime(unpack_returned_tuples=True);runtime.execute(MOCK)
runtime.execute((ROOT/'work/bus_chase_camera.lua').read_text(encoding='utf-8'));g=runtime.globals()
checks=[]
for label in ['E200','E6M']:
 g.busID=f'kmb_{label.lower()}_drivable'
 for index in [1,2]:
  for look in ['forward','left','right','back']:
   g.lookLeft=look=='left';g.lookRight=look=='right';g.lookBack=look=='back'
   g.script.update(.016,index);p=g.ac.Camera.position;d=g.ac.Camera.direction
   assert abs(d.x*d.x+d.y*d.y+d.z*d.z-1)<1e-6
   assert (p.x*p.x+p.z*p.z)**.5>=12.5
   checks.append({'car':label,'camera':index,'look':look,'position':[p.x,p.y,p.z]})
g.busID='unrelated_car';g.lookLeft=False;g.lookRight=False;g.lookBack=False;g.script.update(.016,1)
assert abs(g.ac.Camera.position.z+4.6)<1e-6
(ROOT/'outputs/chase_camera_validation.json').write_text(json.dumps({'status':'PASS','checks':checks,'unrelated_cars':'base placement preserved','limits':'Mocked CSP APIs; in-game yaw smoothing and rendering pending'},indent=2))
print('Chase camera PASS: both buses, both cameras, four look directions; unrelated base placement preserved')
