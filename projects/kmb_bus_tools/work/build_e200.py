"""Convert the local, unencrypted KMB E200 AAU model to a separate AC prototype.

Reads only the user's OMSI source. No OMSI scripts are executed. Uses native KN5,
driver hierarchy/animations, and AC data files; no installer or game UI control.
"""
from pathlib import Path
from collections import Counter
import configparser,copy,hashlib,io,json,math,re,shutil,struct
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from audit_e200 import ROOT,SOURCE,CFG,reader,commands,meshes
from kn5_tools import Kn5,Node,read_string,read_u32,string_bytes

ID='kmb_e200_drivable'
NAME='KMB E200 AAU Playable Prototype'
AC=Path('A:/SteamLibrary/steamapps/common/assettocorsa')
PACKAGE=ROOT/'outputs/E200_playable'
CAR=PACKAGE/'content/cars'/ID
DONOR=ROOT/'outputs/E6M_playable/content/cars/kmb_e6m_drivable'
CG_Y=1.2
FRONT_Z=(2.163111925125122+3.006110906600952)/2
REAR_Z=(-2.993833065032959-2.152578115463257)/2
SHIFT=np.array([0.,CG_Y,(FRONT_Z+REAR_Z)/2])
EYES=np.array([-.72,2.,3.45])-SHIFT
for p in ['data','sfx','skins/0_kmb','ui','extension','animations']:(CAR/p).mkdir(parents=True,exist_ok=True)
texture_files={}
for p in (SOURCE/'Texture').rglob('*'):
    if p.is_file():texture_files.setdefault(p.name.lower(),[]).append(p)
texture_cache={};textures={};material_cache={};materials=[]
missing_textures=[];dynamic_textures=[];skipped=[];mirror_meshes=[];mesh_report=[]
mirror_indices=Counter()
texlog=[]


def texture(name,rgba,glass=False):
    original=(name or '').replace('\\','/')
    key=(original.lower(),tuple(rgba),glass)
    if key in texture_cache:return texture_cache[key]
    basename=Path(original).name
    dynamic=bool(re.search(r'(?i)^(reflexion|texttexture)',basename))
    candidates=[SOURCE/'Texture'/original,SOURCE/'Model'/original]
    candidates+=texture_files.get(basename.lower(),[])
    source=next((p for p in candidates if p.is_file()),None)
    if source is None:
        if original and not dynamic:missing_textures.append(original)
        if dynamic:dynamic_textures.append(original)
        colour=(35,42,46,255) if dynamic else tuple(round(max(0,min(1,x))*255) for x in rgba)
        image=Image.new('RGBA',(8,8),colour)
    else:
        image=Image.open(source).convert('RGBA')
    if max(image.size)>2048:image.thumbnail((2048,2048),Image.Resampling.LANCZOS)
    # Source window alpha is rather dense. Preserve opaque frames and markings;
    # lighten only translucent texels in the separate glass texture variant.
    if glass:
        arr=np.array(image)
        mask=arr[:,:,3]<250
        arr[:,:,3][mask]=(arr[:,:,3][mask].astype(float)*.28).astype(np.uint8)
        image=Image.fromarray(arr)
    if rgba[3]<.999:
        a=np.asarray(image.getchannel('A')).astype(float)*max(0,rgba[3]);image.putalpha(Image.fromarray(a.astype('uint8')))
    digest=hashlib.sha1(repr(key).encode()).hexdigest()[:10]
    target=re.sub(r'[^a-zA-Z0-9_.-]','_',Path(basename or 'plain').stem)+'_'+digest+'.dds'
    stream=io.BytesIO();image.save(stream,format='DDS',pixel_format='DXT5')
    textures[target]=stream.getvalue();texture_cache[key]=target
    texlog.append({'source':str(source) if source else original,'embedded':target,'glass_variant':glass,'size':list(image.size)})
    return target


def material_options(block,raw):
    slots={};counts=Counter()
    for i,m in enumerate(raw):
        name=(m[4] or '').lower();slots[(name,counts[name])]=i;counts[name]+=1
    result={};active=None
    for c in block['commands']:
        args=c['args'];tag=c['tag']
        if tag in ('matl','matl_change') and len(args)>1:
            try:active=slots.get((args[0].lower(),int(args[1])))
            except ValueError:active=None
            if active is not None:result.setdefault(active,{})
        elif active is not None and tag in ('matl_alpha','alphascale','matl_nozwrite','matl_noztest','matl_transmap','useTextTexture'.lower()):
            result[active][tag]=args[:2]
    return result


def get_material(raw,options,is_glass):
    alpha=options.get('matl_alpha',['0'])[0]
    if is_glass and alpha=='0':alpha='2'
    name=raw[4] or ''
    rgba=tuple(raw[0]);key=(name.lower(),rgba,alpha,is_glass)
    if key in material_cache:return material_cache[key]
    diffuse=texture(name,rgba,is_glass)
    blend=1 if alpha=='2' or rgba[3]<.999 else 0
    alpha_test=1 if alpha=='1' else 0
    material_name='E200_M'+str(len(materials))+'_'+Path(name or 'plain').stem
    properties={'ksAmbient':.42,'ksDiffuse':.65,'ksSpecular':.10 if not is_glass else .35,
                'ksSpecularEXP':25 if not is_glass else 80,'ksAlphaRef':.5}
    materials.append({'name':material_name,'shader':'ksPerPixelAlpha' if blend or alpha_test else 'ksPerPixel',
        'blend':blend,'alpha_test':alpha_test,'depth':1 if blend else 0,
        'props':{k:(float(v),0.,0.,0.,0.,0.,0.,0.,0.,0.) for k,v in properties.items()},
        'maps':[{'name':'txDiffuse','slot':0,'texture':diffuse}]})
    index=len(materials)-1;material_cache[key]=index
    return index


def tangents(v,n,uv,idx):
    a,b,c=idx.T;e1=v[b]-v[a];e2=v[c]-v[a];t1=uv[b]-uv[a];t2=uv[c]-uv[a]
    det=t1[:,0]*t2[:,1]-t1[:,1]*t2[:,0]
    inv=np.divide(1.,det,out=np.zeros_like(det),where=abs(det)>1e-10)
    face=(e1*t2[:,1,None]-e2*t1[:,1,None])*inv[:,None]
    tangent=np.zeros_like(v)
    for corner in (a,b,c):np.add.at(tangent,corner,face)
    tangent-=n*(tangent*n).sum(1)[:,None]
    lengths=np.linalg.norm(tangent,axis=1)
    tangent[lengths<1e-10]=[1,0,0];lengths=np.linalg.norm(tangent,axis=1)
    return tangent/lengths[:,None]


def mesh_node(name,vertices,normals,uvs,indices,mat):
    used,newindices=np.unique(indices,return_inverse=True)
    vertices=vertices[used].copy();normals=normals[used].copy();uvs=uvs[used].copy()
    indices=newindices.reshape(-1,3).astype('<u2')
    if len(used)>65535:raise ValueError('Mesh exceeds native index range')
    packed=np.empty((len(used),11),dtype='<f4')
    packed[:,:3]=vertices;packed[:,3:6]=normals;packed[:,6:8]=uvs
    packed[:,8:11]=tangents(vertices,normals,uvs,indices)
    center=(vertices.min(0)+vertices.max(0))/2;radius=np.linalg.norm(vertices-center,axis=1).max()
    transparent=bool(materials[mat]['blend'])
    data=bytearray(struct.pack('<???I',not transparent,True,transparent,len(used)))
    data+=packed.tobytes()+struct.pack('<I',indices.size)+indices.tobytes()
    data+=struct.pack('<II2f4f?',mat,0,0.,2000.,*center,float(radius),True)
    return Node(2,name,True,data,[],len(used),7,44,indices.size,mat)


def recalc_bound(n):
    v=n.vertices[:,:3];c=(v.min(0)+v.max(0))/2;r=np.linalg.norm(v-c,axis=1).max()
    offset=n.vertex_offset+n.vertex_count*44+4+n.index_count*2+4+4+8
    struct.pack_into('<4f',n.payload,offset,*c,float(r))


root=Node.dummy(ID);wheel_parts={k:[] for k in ['LF','RF','LR','RR']};groups={}
seen=set();state={'cp_lenkrad_visible':1,'foglight':0,'dashupmon_mode':0}
for bi,block in enumerate(meshes()):
    path=block['path'];lower=path.lower()
    conditions=[c['args'][:2] for c in block['commands'] if c['tag']=='visible']
    if any(state.get(var,0)!=float(value) for var,value in conditions):
        skipped.append({'mesh':path,'reason':'Inactive static visibility condition'});continue
    if lower in seen:
        skipped.append({'mesh':path,'reason':'Repeated mesh instance'});continue
    seen.add(lower)
    if lower=='shadow.o3d':continue
    parsed=reader.import_o3d((SOURCE/'Model'/path.replace('\\','/')).read_bytes())
    vv=np.array([v[0] for v in parsed[1]],dtype=float);nn=np.array([v[1] for v in parsed[1]],dtype=float)
    uv=np.array([v[2] for v in parsed[1]],dtype=float)
    # O3D stores height in Y and forward in Z. Mirror X to native AC's left-
    # positive convention, and reverse triangle winding for that reflection.
    vv[:,0]*=-1;vv-=SHIFT;nn[:,0]*=-1
    nn/=np.maximum(np.linalg.norm(nn,axis=1)[:,None],1e-10)
    faces=np.array([t[0][::-1] for t in parsed[2]],dtype=int)
    face_mats=np.array([t[1] for t in parsed[2]],dtype=int)
    opts=material_options(block,parsed[3]);stem=Path(path).stem
    count=0
    for mi,raw in enumerate(parsed[3]):
        part=faces[face_mats==mi]
        if not len(part):continue
        option=opts.get(mi,{})
        dynamic_alpha=option.get('alphascale',[''])[0].lower()
        if any(s in dynamic_alpha for s in ['rain','wetness','dirt']):continue
        is_glass=('glass' in stem.lower() or stem.lower() in ('cpwin1','cpwin2')) and not re.search(r'(?i)(reflexion|reg\.bmp)',raw[4] or '')
        mat=get_material(raw,option,is_glass)
        if lower=='whl2_aau.o3d':
            centres=vv[part].mean(1)[:,0]
            for suffix,mask in [('LR',centres>=0),('RR',centres<0)]:
                if mask.any():wheel_parts[suffix].append(mesh_node(('TYRE_' if 'tyre' in (raw[4] or '').lower() else 'RIM_')+suffix+f'_m{mi}',vv,nn,uv,part[mask],mat))
        else:
            node=mesh_node('E200_'+stem+f'__m{mi}',vv,nn,uv,part,mat)
            if lower in ('whl0_aau.o3d','whl1_aau.o3d'):
                suffix='LF' if lower=='whl0_aau.o3d' else 'RF'
                node.name=('TYRE_' if 'tyre' in (raw[4] or '').lower() else 'RIM_')+suffix+f'_m{mi}'
                wheel_parts[suffix].append(node)
            else:groups.setdefault(stem,[]).append(node)
            if re.match(r'(?i)reflexion\d',raw[4] or ''):mirror_meshes.append(node.name)
        count+=len(part)
    mesh_report.append({'source':path,'triangles':count,'vertices':len(vv)})

wheel_centers={}
for suffix,parts in wheel_parts.items():
    if not parts:raise ValueError('Missing wheel '+suffix)
    p=np.concatenate([n.vertices[:,:3] for n in parts]);center=(p.min(0)+p.max(0))/2
    for n in parts:n.vertices[:,:3]-=center;recalc_bound(n)
    root.children.extend([Node.dummy('WHEEL_'+suffix,parts,center),Node.dummy('HUB_'+suffix,translation=center)])
    wheel_centers[suffix]=center.tolist()


def instrument(group,name,pivot):
    parts=groups.pop(group)
    points=np.concatenate([n.vertices[:,:3] for n in parts]);center=np.array(pivot)-SHIFT
    _,_,vh=np.linalg.svd(points-points.mean(0),full_matrices=False)
    axis=vh[-1]
    if axis[2]<0:axis=-axis
    x=np.array([1.,0,0]);y=np.cross(axis,x);y/=np.linalg.norm(y);x=np.cross(y,axis)
    rotation=np.array([x,y,axis]);m=np.eye(4,dtype='<f4');m[:3,:3]=rotation;m[3,:3]=center
    for n in parts:
        v=n.vertices;v[:,:3]=(v[:,:3]-center)@rotation.T;v[:,3:6]=v[:,3:6]@rotation.T;v[:,8:11]=v[:,8:11]@rotation.T;recalc_bound(n)
    root.children.append(Node(1,name,True,bytearray(m.tobytes()),parts))


instrument('dash_strw','STEER_HR',[-.6912,1.5467,4.2058])
instrument('dash_panel_speedo','ARROW_SPEED',[-.5257,1.5188,4.4740])
instrument('dash_panel_rpm','ARROW_RPM',[-.8302,1.5188,4.4740])
for name,parts in groups.items():root.children.append(Node.dummy(name,parts))

# Write a native KN5 prefix and hierarchy, then parse it with the independent
# reader used for the byte-identical E6M round-trip check.
prefix=io.BytesIO();prefix.write(b'sc6969'+struct.pack('<II',5,len(textures)))
for name,data in textures.items():prefix.write(struct.pack('<I',1)+string_bytes(name)+struct.pack('<I',len(data))+data)
prefix.write(struct.pack('<I',len(materials)))
for m in materials:
    prefix.write(string_bytes(m['name'])+string_bytes(m['shader'])+struct.pack('<BBI',m['blend'],m['alpha_test'],m['depth']))
    prefix.write(struct.pack('<I',len(m['props'])))
    for name,value in m['props'].items():prefix.write(string_bytes(name)+struct.pack('<10f',*value))
    prefix.write(struct.pack('<I',len(m['maps'])))
    for mapping in m['maps']:prefix.write(string_bytes(mapping['name'])+struct.pack('<I',mapping['slot'])+string_bytes(mapping['texture']))
with (CAR/(ID+'.kn5')).open('wb') as f:f.write(prefix.getvalue());root.write(f)
check=Kn5(CAR/(ID+'.kn5'));assert len(check.materials)==len(materials)
assert sum(n.index_count for _,n in check.root.walk())==sum(n.index_count for _,n in root.walk())

# Native AC data schema from the working E6M package, with E200-specific values.
for p in (DONOR/'data').glob('*'):
    if p.is_file():shutil.copy2(p,CAR/'data'/p.name)
def edit_ini(name,changes):
    p=configparser.ConfigParser(interpolation=None,strict=False,inline_comment_prefixes=(';',));p.optionxform=str;p.read(CAR/'data'/name,encoding='utf-8-sig')
    for section,values in changes.items():
        if not p.has_section(section):p.add_section(section)
        for key,value in values.items():
            if value is None:p.remove_option(section,key)
            else:p.set(section,key,str(value))
    with (CAR/'data'/name).open('w',encoding='utf-8') as f:p.write(f,space_around_delimiters=False)
def put(relative,text):(CAR/relative).write_text(text.strip()+'\n',encoding='utf-8')
eye=','.join(f'{v:.6f}' for v in EYES)
edit_ini('car.ini',{'INFO':{'SCREEN_NAME':NAME},'BASIC':{'TOTALMASS':10800,'INERTIA':'2.50,3.14,10.45'},
 'GRAPHICS':{'DRIVEREYES':eye,'BONNET_CAMERA_POS':eye,'ON_BOARD_PITCH_ANGLE':-9,'BONNET_CAMERA_PITCH':-9,
             'BUMPER_CAMERA_POS':'0,0.45,4.90'},'FUEL':{'FUEL':40,'MAX_FUEL':250},
 'CONTROLS':{'STEER_LOCK':720,'STEER_RATIO':-20}})
edit_ini('suspensions.ini',{'BASIC':{'WHEELBASE':FRONT_Z-REAR_Z,'CG_LOCATION':.5},
 'FRONT':{'BASEY':.4190483-CG_Y,'TRACK':2.223,'ROD_LENGTH':.123,'HUB_MASS':120,'SPRING_RATE':220000,'DAMP_BUMP':13000,'DAMP_REBOUND':18000},
 'REAR':{'BASEY':.4190502-CG_Y,'TRACK':1.98,'ROD_LENGTH':.09,'HUB_MASS':220,'SPRING_RATE':300000,'DAMP_BUMP':17000,'DAMP_REBOUND':23000},
 'ARB':{'FRONT':45000,'REAR':25000}})
edit_ini('tyres.ini',{'FRONT':{'RADIUS':.4211,'RIM_RADIUS':.24765,'WIDTH':.285,'FZ0':26500,'ANGULAR_INERTIA':9,'RATE':900000},
 'REAR':{'RADIUS':.4214,'RIM_RADIUS':.24765,'WIDTH':.50,'FZ0':26500,'ANGULAR_INERTIA':16,'RATE':1400000}})
edit_ini('drivetrain.ini',{'GEARS':{'COUNT':4,'GEAR_R':-2.8,'GEAR_1':2.4,'GEAR_2':1.36,'GEAR_3':1,'GEAR_4':.73,'GEAR_5':None,'GEAR_6':None,'FINAL':5.38},
 'CLUTCH':{'MAX_TORQUE':1700},'AUTOCLUTCH':{'MIN_RPM':800,'MAX_RPM':1200},'AUTO_SHIFTER':{'UP':2250,'DOWN':1050}})
edit_ini('engine.ini',{'ENGINE_DATA':{'LIMITER':2500,'MINIMUM':700,'INERTIA':2.5},'COAST_REF':{'RPM':2300,'TORQUE':180}})
put('data/power.lut','0|0\n50|0\n300|600\n700|814\n1100|850\n1600|850\n2300|697\n2500|0\n2700|0')
edit_ini('brakes.ini',{'DATA':{'MAX_TORQUE':18000,'FRONT_SHARE':.55,'HANDBRAKE_TORQUE':13000}})
edit_ini('aero.ini',{'WING_0':{'CHORD':2.9,'SPAN':2.5,'CD_GAIN':.65}})
put('data/lods.ini',f'[COCKPIT_HR]\nDISTANCE_SWITCH=0\n[LOD_0]\nFILE={ID}.kn5\nIN=0\nOUT=2000')
put('data/dash_cam.ini',f'[DASH_CAM]\nPOS={eye}\nPITCH_ANGLE=-9\nEXP=30')
put('data/cameras.ini',f'[CAMERA_0]\nPOSITION={eye}\nFORWARD=0,-0.156434,0.987688\nUP=0,0.987688,0.156434\nFOV=56\nEXPOSURE=30\nEXTERNAL_SOUND=0')
put('data/colliders.ini',f'[COLLIDER_0]\nCENTRE=0,{1.70-CG_Y:.6f},{-.24-SHIFT[2]:.6f}\nSIZE=2.45,2.80,10.30\nGROUND_ENABLE=1')
put('data/mirrors.ini','\n\n'.join(f'[MIRROR_{i}]\nNAME={name}' for i,name in enumerate(dict.fromkeys(mirror_meshes))))
put('data/ambient_shadows.ini','[SETTINGS]\nWIDTH=1.45\nLENGTH=5.4')
edit_ini('setup.ini',{'FUEL':{'MAX':250}})
edit_ini('ai.ini',{'GEARS':{'UP':2250,'DOWN':1050}})

# Rescale and center a simple local collision hull for this single-decker.
collider=Kn5(DONOR/'collider.kn5')
for _,n in collider.root.walk():
    if n.kind==1:n.payload=bytearray(np.eye(4,dtype='<f4').tobytes())
    else:
        v=n.vertices[:,:3];lo=v.min(0).copy();hi=v.max(0).copy()
        v[:]=(v-lo)/(hi-lo)*np.array([2.45,2.8,10.30])+np.array([-1.225,.30,-5.39])-SHIFT
        recalc_bound(n)
collider.write(CAR/'collider.kn5')
for filename in ['body_shadow.png','tyre_0_shadow.png','tyre_1_shadow.png','tyre_2_shadow.png','tyre_3_shadow.png']:
    shutil.copy2(DONOR/filename,CAR/filename)
shutil.copy2(DONOR/'sfx/kmb_e6m_drivable.bank',CAR/'sfx'/f'{ID}.bank')
put('sfx/GUIDs.txt',(DONOR/'sfx/GUIDs.txt').read_text().replace('kmb_e6m_drivable',ID))
put('extension/ext_config.ini','; Local E200 prototype. Glass and texture alpha are in the KN5.\n[BASIC]\nIS_HIGH_BEAM_SUPPORTED=0')

# Keep the successfully posed native driver, translating only its root to the
# E200 seat; do not leave an unposed default avatar at the centre of the bus.
pose_eyes=np.array(json.loads((ROOT/'outputs/E6M_playable/seat_fix_report.json').read_text())['camera'])
driver_delta=EYES-pose_eyes
data=bytearray((DONOR/'driver_base_pos.knh').read_bytes());f=io.BytesIO(data)
def shift_bone():
    name=read_string(f);off=f.tell();f.seek(64,1);count=read_u32(f)
    if name=='DRIVER:DRIVER':
        xyz=np.frombuffer(data,dtype='<f4',count=3,offset=off+48);xyz+=driver_delta
    for _ in range(count):shift_bone()
shift_bone();(CAR/'driver_base_pos.knh').write_bytes(data)
for path in (DONOR/'animations').glob('*.ksanim'):
    data=bytearray(path.read_bytes());f=io.BytesIO(data);version,count=struct.unpack('<ii',f.read(8));assert version==2
    for _ in range(count):
        name=read_string(f);frames=read_u32(f);offset=f.tell()
        if name=='DRIVER:DRIVER':
            values=np.ndarray((frames,10),dtype='<f4',buffer=data,offset=offset);values[:,4:7]+=driver_delta
        f.seek(frames*40,1)
    (CAR/'animations'/path.name).write_bytes(data)

logo=Image.new('RGB',(256,256),'white');draw=ImageDraw.Draw(logo)
font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',72);draw.text((32,78),'KMB',font=font,fill=(190,20,28));logo.save(CAR/'logo.png')
skin={'skinname':'KMB AAU source livery','drivername':'','country':'Hong Kong','number':''}
(CAR/'skins/0_kmb/ui_skin.json').write_text(json.dumps(skin,indent=2),encoding='utf-8')
put('skins/0_kmb/skin.ini','[driver]\nSUIT=black\nGLOVES=black\nHELMET=black')
logo.resize((64,64)).save(CAR/'skins/0_kmb/livery.png')
ui={'name':NAME,'brand':'Alexander Dennis','country':'United Kingdom','class':'street',
 'description':'Local playable prototype converted from the installed KMB E200 AAU OMSI model. Native steering, brakes, four forward gears and autoclutch. Approximate physics and first gear; existing bus audio. OMSI passengers, ticketing, clickable controls and scripted systems are not converted.',
 'tags':['bus','KMB','Hong Kong','E200','AAU','prototype'],
 'specs':{'bhp':'225 bhp (source curve)','torque':'850 Nm','weight':'10800 kg','topspeed':'90 km/h (gearing)','acceleration':'Prototype','pwratio':'48 kg/hp'}}
(CAR/'ui/ui_car.json').write_text(json.dumps(ui,indent=2),encoding='utf-8')
report={'car_id':ID,'name':NAME,'source':str(SOURCE),'source_bus':'AAU.bus','configuration':str(CFG),
 'source_unchanged':True,'mesh_instances_included':len(mesh_report),'mesh_nodes':sum(n.kind==2 for _,n in root.walk()),
 'triangles':sum(n.index_count//3 for _,n in root.walk()),'textures':len(textures),'materials':len(materials),
 'wheelbase':FRONT_Z-REAR_Z,'model_origin_shift':SHIFT.tolist(),'wheel_centers':wheel_centers,
 'camera':EYES.tolist(),'camera_reference':'OMSI AAU.bus default forward view (camera 3)',
 'missing_textures':sorted(set(missing_textures)),'dynamic_textures':sorted(set(dynamic_textures)),
 'skipped_meshes':skipped,'texture_sources':texlog,'source_meshes':mesh_report,
 'limitations':['Physics and hydraulic gearbox approximated with native AC controls',
 'No converted OMSI scripts, passenger/ticketing logic, clickable dashboard or doors',
 'Existing local AC bus sound bank reused; not original OMSI audio',
 'Dynamic sign/text surfaces use static placeholders; local prototype, no redistribution clearance'],
 'status':'Built; awaiting visual/static validation. In-game test left to user.'}
(PACKAGE/'build_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['name','mesh_nodes','triangles','textures','materials','wheelbase','camera','missing_textures','status']},indent=2))
