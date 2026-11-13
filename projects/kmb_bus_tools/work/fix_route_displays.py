"""Restore exterior signs in the local AC prototypes using installed OMSI art.

Changes sign geometry/UVs/materials only; source OMSI files are read-only.
Destination is selected with an ordinary AC skin, so the embedded default works
without CSP Lua or the OMSI scripting engine. No game session is started.
"""
from pathlib import Path
import io,struct,json,shutil,hashlib,copy,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps
from kn5_tools import Kn5,Node,string_bytes,read_string,read_u32

ROOT=Path(__file__).resolve().parent.parent
ANZEIGEN=Path('A:/SteamLibrary/steamapps/common/OMSI 2/Vehicles/Anzeigen')
ROUTES=[('not_in_service','Not in Service / 暫停服務',None),
        ('51_tai_mo_shan','51 - Tai Mo Shan / 大帽山 巔峰之旅','51Y_2.bmp'),
        ('51_sheung_tsuen','51 - Sheung Tsuen / 上村','51Z.bmp'),
        ('51_nina_tower','51 - Tsuen Wan (Nina Tower) / 荃灣（如心廣場）','51Y.bmp')]

def texture_bytes(im):
    f=io.BytesIO();im.convert('RGBA').save(f,format='DDS',pixel_format='DXT5');return f.getvalue()

def prefix(model,added):
    f=io.BytesIO(model.prefix);f.seek(6);ver=read_u32(f)
    if ver>5:extra=read_u32(f)
    tex=[]
    for _ in range(read_u32(f)):
        active=read_u32(f);name=read_string(f);size=read_u32(f);data=f.read(size)
        tex.append((active,name,added.get(name,data)))
    existing={name for _,name,_ in tex}
    tex.extend((1,name,data) for name,data in added.items() if name not in existing)
    out=io.BytesIO();out.write(b'sc6969'+struct.pack('<I',ver))
    if ver>5:out.write(struct.pack('<I',extra))
    out.write(struct.pack('<I',len(tex)))
    for active,name,data in tex:out.write(struct.pack('<I',active)+string_bytes(name)+struct.pack('<I',len(data))+data)
    out.write(struct.pack('<I',len(model.materials)))
    for m in model.materials:
        out.write(string_bytes(m['name'])+string_bytes(m['shader'])+struct.pack('<BBI',m['blend'],m['alpha_test'],m['depth']))
        out.write(struct.pack('<I',len(m['props'])))
        for name,values in m['props'].items():out.write(string_bytes(name)+struct.pack('<10f',*values))
        out.write(struct.pack('<I',len(m['maps'])))
        for t in m['maps']:out.write(string_bytes(t['name'])+struct.pack('<I',t['slot'])+string_bytes(t['texture']))
    return out.getvalue()

def node(name,v,idx,mat):
    v=np.asarray(v,dtype='<f4');idx=np.asarray(idx,dtype='<u2')
    center=(v[:,:3].min(0)+v[:,:3].max(0))/2
    radius=np.linalg.norm(v[:,:3]-center,axis=1).max()
    data=bytearray(struct.pack('<???I',False,True,False,len(v)))
    data+=v.tobytes()+struct.pack('<I',idx.size)+idx.tobytes()
    data+=struct.pack('<II2f4f?',mat,0,0.,2000.,*center,float(radius),True)
    return Node(2,name,True,data,[],len(v),7,44,idx.size,mat)

def artwork(label,folder,filename,face,size):
    # Use the installed OMSI pixels, including its native rear KMB logo for NIS.
    # HongLong_Green matches the green E6M NIS reference supplied by the user.
    if filename is None and label=='E6M':
        path=ANZEIGEN/'HongLong_Green/Lantau_North/NIS.bmp'
        crop=(416,0,675,128) if face=='rear' else (0,0,416,128)
    else:
        path=ANZEIGEN/folder/('KMBVC/'+filename if filename else 'Lantau_North/NIS.bmp')
        crop={'front':(0,0,416,128),'side':(0,144,512,240),
              'rear':(64,256,208,416) if filename else (0,256,272,416)}[face]
    atlas=Image.open(path).convert('RGB')
    assert 0<=crop[0]<crop[2]<=atlas.width and 0<=crop[1]<crop[3]<=atlas.height
    image=atlas.crop(crop)
    # Match the physical panel ratio without compressing glyphs; pad with black.
    result=Image.new('RGB',size,'black')
    fit=ImageOps.contain(image,size,Image.Resampling.NEAREST)
    result.paste(fit,((size[0]-fit.width)//2,(size[1]-fit.height)//2))
    assert np.asarray(result).max()>0, 'Blank OMSI display: '+str(path)
    return result,{'source':str(path),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                   'crop':list(crop),'source_panel':face,'output_pixels':list(size)}

labels=tuple(sys.argv[1:]) if len(sys.argv)>1 else ('E6M',)
if any(label not in ('E6M','E200') for label in labels):
    raise SystemExit('Choose E6M and/or E200')
reports=[]
for label in labels:
    car=ROOT/f'outputs/{label}_playable/content/cars/kmb_{label.lower()}_drivable'
    package=car.parents[2];modelpath=car/(car.name+'.kn5')
    backup=package/'backups/before_route_displays';backup.mkdir(parents=True,exist_ok=True)
    source=backup/modelpath.name
    if not source.exists():shutil.copy2(modelpath,source)
    # Preserve subsequent model fixes instead of restoring an old entire KN5.
    model=Kn5(modelpath)
    assert prefix(model,{})==model.prefix,'Unchanged prefix round trip failed'
    current={face:next((n for _,n in model.root.walk() if n.name=='KMB_DESTINATION_'+face.upper()),None)
             for face in ('front','side','rear')}
    has_panels=all(n is not None for n in current.values())
    old=[]
    for _,parent in list(model.root.walk()):
        retained=[]
        for n in parent.children:
            match=(label=='E6M' and n.name=='HanoverSystem__geo_000') or (label=='E200' and n.kind==2 and ('SuperNewHanoverSystem_Head__' in n.name or ('SuperNewHanoverSystem_Side__' in n.name and n.material_id==19)))
            if match and not has_panels:old.append(n)
            else:retained.append(n)
        parent.children=retained
    assert old or has_panels,'No original sign geometry matched'
    faces={'front':[],'side':[],'rear':[]}
    for n in old:
        v=n.vertices.copy()
        idx=np.frombuffer(n.payload,dtype='<u2',count=n.index_count,offset=n.vertex_offset+n.vertex_count*44+4).reshape(-1,3)
        for tri in idx:
            normal=v[tri,3:6].mean(0)
            face='side' if normal[0]>.7 else 'front' if normal[2]>.7 else 'rear' if normal[2]<-.7 else None
            if face is None:raise ValueError('Unexpected sign plane '+n.name+str(normal))
            faces[face].append(v[tri])
    if has_panels:
        for face,n in current.items():faces[face]=[n.vertices.copy()]
    added={};panels=[];provenance=[];previews={r[0]:[] for r in ROUTES}
    folder='HANOVER_WHITE_FULL' if label=='E6M' else 'HANOVER_ORANGE_FULL'
    for face,chunks in faces.items():
        v=np.concatenate(chunks);p=v[:,:3];lo=p.min(0);hi=p.max(0)
        if face=='front':u=p[:,0]
        elif face=='rear':u=-p[:,0]
        else:u=-p[:,2]
        # Viewed from outside, screen-right is +X at the front, -X at the
        # rear and -Z at the left side board.
        v[:,6]=(u-u.min())/(u.max()-u.min())
        v[:,7]=(hi[1]-p[:,1])/(hi[1]-lo[1])
        # Keep the original slightly curved/angled panels and triangle winding.
        aspect=float((u.max()-u.min())/(hi[1]-lo[1]))
        size=(1024,max(64,int(round(1024/aspect/4))*4))
        texname=f'kmb_destination_{face}.dds'
        artface='front' if face=='front' else 'side' if face=='side' and label=='E6M' else 'rear'
        for route_id,route_label,filename in ROUTES:
            im,origin=artwork(label,folder,filename,artface,size)
            provenance.append({'skin':route_id,'face':face,**origin})
            skin=car/'skins'/route_id;skin.mkdir(parents=True,exist_ok=True)
            (skin/texname).write_bytes(texture_bytes(im))
            if route_id=='not_in_service':
                default_skin=car/'skins/0_kmb';default_skin.mkdir(parents=True,exist_ok=True)
                (default_skin/texname).write_bytes(texture_bytes(im))
            if route_id==ROUTES[0][0]:added[texname]=texture_bytes(im)
            previews[route_id].append(im)
        material={'name':'KMB_DESTINATION_'+face.upper(),'shader':'ksPerPixel','blend':0,'alpha_test':0,'depth':0,
            'props':{'ksAmbient':(.3,0,0,0,0,0,0,0,0,0),'ksDiffuse':(.4,0,0,0,0,0,0,0,0,0),
                     'ksSpecular':(0,)*10,'ksEmissive':(0,0,0,1.5,1.5,1.5,0,0,0,0)},
            'maps':[{'name':'txDiffuse','slot':0,'texture':texname}]}
        if has_panels:
            new=current[face]
            new.vertices[:,6:8]=v[:,6:8]
        else:
            mat=len(model.materials);model.materials.append(material)
            new=node('KMB_DESTINATION_'+face.upper(),v,np.arange(len(v)).reshape(-1,3),mat)
            model.root.children.append(new)
        panels.append({'face':face,'node':new.name,'texture':texname,'bounds':[lo.tolist(),hi.tolist()],'aspect':aspect,'pixels':list(size)})
    model.prefix=prefix(model,added);model.write(modelpath)
    for route_id,route_label,filename in ROUTES:
        skin=car/'skins'/route_id
        (skin/'ui_skin.json').write_text(json.dumps({'skinname':'KMB | '+route_label,'drivername':'','country':'Hong Kong','number':'51' if filename else ''},ensure_ascii=False,indent=2),encoding='utf-8')
        shutil.copy2(car/'skins/0_kmb/skin.ini',skin/'skin.ini')
        shutil.copy2(car/'skins/0_kmb/livery.png',skin/'livery.png')
    (car/'skins/0_kmb/ui_skin.json').write_text(json.dumps({'skinname':'KMB | NIS','drivername':'','country':'Hong Kong','number':'NIS'},ensure_ascii=False,indent=2),encoding='utf-8')
    for route_id,ims in previews.items():
        sheet=Image.new('RGB',(1100,170+sum(im.height for im in ims)),(25,25,25));d=ImageDraw.Draw(sheet)
        font=ImageFont.truetype('C:/Windows/Fonts/msjh.ttc',25)
        route=next(r for r in ROUTES if r[0]==route_id)
        d.text((30,15),label+' | '+route[1],font=font,fill='white')
        y=70
        for panel,im in zip(panels,ims):
            d.text((30,y),panel['face'],fill='white');sheet.paste(im,(30,y+20));y+=im.height+35
        path=package/'preview'/('sign_'+route_id+'.png');path.parent.mkdir(exist_ok=True);sheet.save(path)
    # Correct the unsafe raw source E200 camera that was inside its seat back.
    # This adjustment is local to E200; the user's latest E6M view is preserved.
    camera_fix=None
    if label=='E200':
        oldeye='-0.720000,0.800000,3.444297';neweye='-0.720000,0.800000,3.654297'
        for name in ['car.ini','dash_cam.ini','cameras.ini']:
            p=car/'data'/name;text=p.read_text()
            if oldeye in text:
                dest=backup/name
                if not dest.exists():shutil.copy2(p,dest)
                p.write_text(text.replace(oldeye,neweye),encoding='utf-8')
        camera_fix={'initial_build_correction':neweye,'later_user_camera_adjustments_preserved':True}
    report={'car':str(car),'original_sign_meshes':len(old),'preserved_existing_panels':has_panels,'panels':panels,
            'default':ROUTES[0][1],'default_skin':'0_kmb',
            'selection':'Content Manager skin selection before starting a session',
            'artwork_source':str(ANZEIGEN/folder/'KMBVC'),
            'all_destination_artwork_from_omsi':True,'artwork_provenance':provenance,
            'route_labels_checked_against_actual_bitmap':True,'hof_mapping_warning':'Original HOF 51Y/51Z labels are reversed relative to the bitmap wording; bitmap wording is used.',
            'route_data_reference':str(ROOT/'work/kmb_route51_official.json'),
            'camera_fix':camera_fix,'limits':'Static destinations selected by skin; no OMSI keypad/passenger/script conversion; game testing left to user',
            'model_sha256':hashlib.sha256(modelpath.read_bytes()).hexdigest()}
    (package/'route_display_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    reports.append(report)
print(json.dumps([{k:r[k] for k in ['car','default','original_sign_meshes','panels','camera_fix']} for r in reports],indent=2))
