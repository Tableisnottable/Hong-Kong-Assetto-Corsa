"""Map local E200/E6M geometry and OMSI gauge curves to AC/CSP cockpit systems.

Only modifies staged cars. Installation is a separate verified step.
"""
from pathlib import Path
from datetime import datetime
import io,json,math,shutil,struct,re,copy
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from kn5_tools import Kn5,Node

ROOT=Path(__file__).resolve().parent.parent
OMSI=Path('A:/SteamLibrary/steamapps/common/OMSI 2/Vehicles')

def bound(n):
    p=n.vertices[:,:3];c=(p.min(0)+p.max(0))/2;r=np.linalg.norm(p-c,axis=1).max()
    off=n.vertex_offset+n.vertex_count*n.vertex_stride+4+n.index_count*2+16
    struct.pack_into('<4f',n.payload,off,*c,float(r))

def mesh_material(n,mid):
    n.material_id=mid
    off=n.vertex_offset+n.vertex_count*n.vertex_stride+4+n.index_count*2
    struct.pack_into('<I',n.payload,off,mid)

def scalar(x):return (float(x),)+(0.,)*9
def material(name,texture,emissive=0):
    return {'name':name,'shader':'ksPerPixel','blend':0,'alpha_test':0,'depth':0,
            'props':{'ksAmbient':scalar(.35),'ksDiffuse':scalar(.45),'ksSpecular':scalar(.05),
                     'ksSpecularEXP':scalar(20),'ksEmissive':(0.,0.,0.,emissive,emissive,emissive,0.,0.,0.,0.)},
            'maps':[{'name':'txDiffuse','slot':0,'texture':texture}]}

def dds(im):
    out=io.BytesIO();im.convert('RGBA').save(out,format='DDS',pixel_format='DXT5');return out.getvalue()

def curve(path,name,mult=1):
    text=path.read_text(encoding='cp950',errors='replace')
    match=re.search(r'\[newcurve\]\s*'+re.escape(name)+r'\s*(.*?)(?=\[newcurve\]|\[const\]|\Z)',text,re.S)
    assert match,name
    return [[float(x),float(y)*mult] for x,y in re.findall(r'\[pnt\]\s*([-\d.]+)\s+([-\d.]+)',match[1])]

def edit(path,values):
    text=path.read_text(encoding='utf-8-sig')
    for key,value in values.items():
        text,count=re.subn(r'(?m)^'+re.escape(key)+r'=.*$',key+'='+str(value),text)
        assert count==1,(path,key)
    path.write_text(text,encoding='utf-8')

for label in ('E200','E6M'):
    package=ROOT/f'outputs/{label}_playable';car=package/f'content/cars/kmb_{label.lower()}_drivable'
    modelpath=car/(car.name+'.kn5');k=Kn5(modelpath)
    assert not any(n.name=='KMB_DRIVER_LCD' for _,n in k.root.walk()),'Already patched'
    backup=package/'backups'/('before_cockpit_systems_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    backup.mkdir(parents=True);shutil.copy2(modelpath,backup/modelpath.name)
    for folder in ('data','extension'):shutil.copytree(car/folder,backup/folder)
    nodes={n.name:n for _,n in k.root.walk()}
    cfg=(car/'data/car.ini').read_text();eyes=np.array([float(x) for x in re.search(r'DRIVEREYES=(.*)',cfg)[1].split(',')])
    updates={};log={'car':car.name,'backup':str(backup),'in_game_test':'Pending user test'}
    mirror_names=(['E200_mirror__m1','E200_dash_obj__m2','E200_mirror__m7'] if label=='E200'
                  else ['Mirror_Left__geo_004','Mirror_Center__geo_002','emirror1p3__geo_003'])
    # AC binds the live reflection to the named mesh, not its assembly dummy.
    # Give each mirror its own UV range; CSP renders the separate reflected view.
    for name in mirror_names:
        n=nodes[name];v=n.vertices;p=v[:,:3];center=p.mean(0)
        _,_,vh=np.linalg.svd(p-center,full_matrices=False);normal=vh[-1]
        if np.dot(normal,eyes-center)<0:normal=-normal
        up=np.array([0.,1.,0.]);right=np.cross(up,normal);right/=np.linalg.norm(right)
        vertical=np.cross(normal,right);vertical/=np.linalg.norm(vertical)
        u=p@right;w=p@vertical
        v[:,6]=(u-u.min())/np.ptp(u);v[:,7]=(w.max()-w)/np.ptp(w)
        v[:,3:6]=normal;v[:,8:11]=right
        idxoff=n.vertex_offset+n.vertex_count*n.vertex_stride+4
        idx=np.frombuffer(n.payload,dtype='<u2',count=n.index_count,offset=idxoff).reshape(-1,3)
        for tri in idx:
            a,b,c=p[tri]
            if np.dot(np.cross(b-a,c-a),normal)<0:tri[1],tri[2]=int(tri[2]),int(tri[1])
        mat=k.materials[n.material_id]
        mat['props']['ksEmissive']=(0.,)*10
        mat['props']['ksAmbient']=scalar(.4);mat['props']['ksDiffuse']=scalar(.4)
        # Remove the frozen OMSI scenery used as a fallback texture.
        for mapping in mat['maps']:
            if mapping['name']=='txDiffuse':updates[mapping['texture']]=dds(Image.new('RGB',(32,32),(30,34,36)))
    if label=='E6M':nodes['Mirror_Right'].active=False # inactive alternative left mirror was overlapping
    (car/'data/mirrors.ini').write_text('\n\n'.join(f'[MIRROR_{i}]\nNAME={name}' for i,name in enumerate(mirror_names))+'\n')
    log['mirrors']=mirror_names
    # Replace overlapping OMSI LCD page layers with a single telemetry surface.
    screen_source=nodes['E200_Logen_Mon__m11' if label=='E200' else 'Logen_Mon__geo_011']
    screen=copy.deepcopy(screen_source);screen.name='KMB_DRIVER_LCD';screen.active=True
    for _,n in k.root.walk():
        if n.name=='Logen_Mon':n.active=False
    p=screen.vertices[:,:3];_,_,vh=np.linalg.svd(p-p.mean(0),full_matrices=False);normal=vh[-1]
    if np.dot(normal,eyes-p.mean(0))<0:normal=-normal
    screen.vertices[:,:3]+=normal*.004
    screen.vertices[:,3:6]=normal
    screen.vertices[:,6]=(p[:,0].max()-p[:,0])/np.ptp(p[:,0])
    screen.vertices[:,7]=(p[:,1].max()-p[:,1])/np.ptp(p[:,1])
    idxoff=screen.vertex_offset+screen.vertex_count*screen.vertex_stride+4
    idx=np.frombuffer(screen.payload,dtype='<u2',count=screen.index_count,offset=idxoff).reshape(-1,3)
    for tri in idx:
        a,b,c=screen.vertices[tri,:3]
        if np.dot(np.cross(b-a,c-a),normal)<0:tri[1],tri[2]=int(tri[2]),int(tri[1])
    fallback=Image.new('RGB',(512,256),(12,28,22));draw=ImageDraw.Draw(fallback)
    font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',40)
    draw.text((28,24),'KMB',font=font,fill=(155,204,160));draw.text((28,114),'SPEED   GEAR   FUEL',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',26),fill=(155,204,160))
    tex='kmb_driver_lcd.dds';updates[tex]=dds(fallback)
    mid=len(k.materials);k.materials.append(material('KMB_DRIVER_LCD',tex,.7));mesh_material(screen,mid);bound(screen)
    k.root.children.append(screen)
    # Native AC remains responsible for steering. Gauge rotation is delegated to
    # a child dummy so the original dial plane/pivot orientation remains intact.
    for native,newname in [('ARROW_SPEED','KMB_SPEED_MOTION'),('ARROW_RPM','KMB_RPM_MOTION')]:
        n=nodes[native];n.children=[Node.dummy(newname,n.children)]
    (car/'data/analog_instruments.ini').write_text('[RPM_INDICATOR]\nOBJECT_NAME=ARROW_RPM\nZERO=0\nMIN_VALUE=0\nSTEP=0\n[SPEED_INDICATOR]\nOBJECT_NAME=ARROW_SPEED\nZERO=0\nSTEP=0\n')
    # Add a temperature pivot with the same local dial axes as the other gauges.
    temp=nodes['dash_panel_water'];base=nodes['ARROW_RPM'].matrix.copy()
    center=np.array([-.7972,.2501,4.4210]) if label=='E200' else np.array([-.886,.276,4.217])
    base[3,:3]=center;rotation=base[:3,:3]
    for n in temp.children:
        if n.kind!=2:continue
        v=n.vertices;v[:,:3]=(v[:,:3]-center)@rotation.T
        v[:,3:6]=v[:,3:6]@rotation.T;v[:,8:11]=v[:,8:11]@rotation.T;bound(n)
    temp.payload=bytearray(base.astype('<f4').tobytes());temp.children=[Node.dummy('KMB_TEMP_MOTION',temp.children)]
    # Give pedal and handbrake groups their measured source pivots.
    motions={}
    if label=='E200':
        motions={'dash_brake':([0.,-.3685,4.4349],'KMB_BRAKE_MOTION'),
                 'dash_throttle':([0.,-.3685,4.4877],'KMB_GAS_MOTION'),
                 'dash_hb2':([-1.1392,.1937,4.0816],'KMB_HANDBRAKE_MOTION'),
                 'wiperl':([-.8116,-.0810,4.8829],'KMB_WIPER_L'),
                 'wiperr':([.7608,-.0810,4.8829],'KMB_WIPER_R')}
    for name,(pivot,newname) in motions.items():
        n=nodes[name]
        for child in n.children:
            if child.kind==2:child.vertices[:,:3]-=pivot;bound(child)
        n.payload=bytearray(Node.dummy(name,translation=pivot).payload)
        n.children=[Node.dummy(newname,n.children)]
    source=(OMSI/'ADL_E200_KMB_AAU_with_OrangePai/Script/cockpit_constfile.txt' if label=='E200'
            else ROOT/'work/source/ADL_E500MMC_KMB_E6M/Script/cockpit_constfile.txt')
    speedcurve=curve(source,'cockpit_tacholinie');rpmcurve=curve(source,'cockpit_oeldruck',45)
    tempcurve=curve(source,'cockpit_engine_temperature')
    log['gauge_curves']={'source':str(source),'speed':speedcurve,'rpm':rpmcurve,'temperature':tempcurve}
    indicators=({'handbrake':['E200_dash_panel__m3'],'battery':['E200_dash_panel__m4'],
                 'warning':['E200_dash_panel__m6'],'turn':['E200_dash_panel__m7'],
                 'highbeam':['E200_dash_panel__m8'],'abs':['E200_dash_panel__m9']} if label=='E200' else
                {'handbrake':['dashlight_hb__geo_000'],'battery':['dashlight_rc__geo_000'],
                 'warning':['dashlight_rw__geo_000'],'left':['dashlight_left__geo_000'],
                 'right':['dashlight_right__geo_000'],'highbeam':['dashlight_highlight__geo_000'],
                 'lights':['dashlight_sidelight__geo_000']})
    backlit=[n.name for par,n in k.root.walk() if n.kind==2 and par in ['ARROW_SPEED','ARROW_RPM','KMB_SPEED_MOTION','KMB_RPM_MOTION']]
    # Capture meshes before writing to allow the runtime to bind only valid names.
    gears={str(g):[n.name for _,n in k.root.walk() if n.kind==2 and
                  n.name.startswith(('E200_dash_button_gear_'+g+'__') if label=='E200' else ('dash_button_gear'+g+'__'))]
           for g in ['N','D','R']}
    buttons={'headlights':'dash_button_headlamp' if label=='E200' else 'dash_panel_button_mainlight',
             'hazards':'dash_button_warn' if label=='E200' else 'dash_panel_button_warntoggle',
             'left':'dash_button_ll' if label=='E200' else 'dash_panel_button_leftlight',
             'right':'dash_button_rl' if label=='E200' else 'dash_panel_button_rightlight',
             'neutral':'dash_button_gear_N' if label=='E200' else 'dash_button_gearN'}
    buttonmeshes={key:next(c.name for c in nodes[name].children if c.kind==2) for key,name in buttons.items()}
    bindings={'car':label,'speedCurve':speedcurve,'rpmCurve':rpmcurve,'tempCurve':tempcurve,
              'indicators':indicators,'gearMeshes':gears,'buttons':buttonmeshes,
              'backlit':backlit,'hasPedals':label=='E200'}
    (car/'extension/cockpit_bindings.json').write_text(json.dumps(bindings,ensure_ascii=False,indent=2),encoding='utf-8')
    # All viewpoints are car-local. Rear cameras must clear the full bus body.
    pts=[]
    def world(n,w=np.eye(4),active=True):
        active=active and n.active
        if n.kind==1:w=n.matrix@w
        if n.kind==2 and active:pts.append((np.c_[n.vertices[:,:3],np.ones(n.vertex_count)]@w)[:,:3])
        for child in n.children:world(child,w,active)
    world(k.root);p=np.concatenate(pts);lo=p.min(0);hi=p.max(0)
    rear=float(lo[2]-.35);front=float(hi[2]+.20)
    def vec(v):return ','.join(f'{float(x):.6f}' for x in v)
    edit(car/'data/car.ini',{'MIRROR_POSITION':vec([0,1.1,rear]),'BUMPER_CAMERA_POS':vec([0,.25,front]),
                           'ONBOARD_EXPOSURE':'1','OUTBOARD_EXPOSURE':'1'})
    edit(car/'data/dash_cam.ini',{'EXP':'1'})
    pitch=float(re.search(r'ON_BOARD_PITCH_ANGLE=(.*)',cfg)[1]);rad=math.radians(pitch)
    cameras=[('Driver',eyes,[0,math.sin(rad),math.cos(rad)],0),
             ('Rear view',[0,.9,rear],[0,0,-1],1),
             ('Front exterior',[0,.9,front+1.5],[0,-.05,-1],1),
             ('Left exterior',[float(hi[0]+3),.8,0],[-1,-.04,0],1),
             ('Right exterior',[float(lo[0]-3),.8,0],[1,-.04,0],1),
             ('Rear exterior',[0,1.3,rear-4],[0,-.05,1],1)]
    text=[]
    for i,(name,pos,fwd,extsound) in enumerate(cameras):
        direction=np.array(fwd,dtype=float);direction/=np.linalg.norm(direction)
        up=np.array([0.,1,0]);up-=direction*np.dot(up,direction);up/=np.linalg.norm(up)
        text.append(f'; {name}\n[CAMERA_{i}]\nPOSITION={vec(pos)}\nFORWARD={vec(direction)}\nUP={vec(up)}\nFOV=56\nEXPOSURE=1\nEXTERNAL_SOUND={extsound}\n')
    (car/'data/cameras.ini').write_text('\n'.join(text))
    log['cameras']=[{'name':n,'position':list(map(float,pos)),'direction':list(map(float,d))} for n,pos,d,_ in cameras]
    log['body_bounds']=[lo.tolist(),hi.tolist()]
    ext=(car/'extension/ext_config.ini').read_text()
    # Preserve existing E6M tag axle script. The new display script uses the
    # documented script.update hook and handles its own cockpit bindings.
    ext+='\n; AC cockpit telemetry and interactive lighting controls\n'
    ext+='\n'.join(f'[REAL_MIRROR_{i}]\nFOV=35\nASPECT_MULT=1\n' for i in range(3))
    ext+='\n[SCRIPTABLE_DISPLAY_0]\nMESHES=KMB_DRIVER_LCD\nRESOLUTION=512,256\nDISPLAY_POS=0,0\nDISPLAY_SIZE=512,256\nSKIP_FRAMES=0\nSCRIPT=cockpit.lua\n'
    (car/'extension/ext_config.ini').write_text(ext,encoding='utf-8')
    shutil.copy2(ROOT/'work/bus_cockpit.lua',car/'extension/cockpit.lua')
    # Make bindings available without relying on JSON helpers or file IO in CSP.
    def lua(v):
        if isinstance(v,bool):return 'true' if v else 'false'
        if isinstance(v,str):return json.dumps(v,ensure_ascii=False)
        if isinstance(v,(float,int)):return str(v)
        if isinstance(v,list):return '{'+','.join(lua(x) for x in v)+'}'
        return '{'+','.join('['+lua(key)+']='+lua(value) for key,value in v.items())+'}'
    script=(car/'extension/cockpit.lua').read_text()
    (car/'extension/cockpit.lua').write_text('local bindings = '+lua(bindings)+'\n'+script,encoding='utf-8')
    k.rebuild_prefix(updates);k.write(modelpath)
    log['limits']=['CSP cockpit script requires Custom Shaders Patch','OMSI passenger, ticketing, door and air-system simulations are not ported',
                  'Native chase cameras use the player camera settings; added car-local F6 exterior views are checked separately']
    (package/'cockpit_systems_report.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
    print(label,'cockpit systems staged;',len(mirror_names),'mirror glass meshes;',len(cameras),'views')
