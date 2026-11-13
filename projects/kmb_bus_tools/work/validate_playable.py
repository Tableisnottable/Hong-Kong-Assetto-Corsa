import configparser
import hashlib
import json
from pathlib import Path
import re
import numpy as np
import sys
from kn5_tools import Kn5

ROOT=Path(__file__).resolve().parent.parent
label=sys.argv[1] if len(sys.argv)>1 else 'E6M'
PACKAGE=ROOT/f'outputs/{label}_playable'
CAR=PACKAGE/f'content/cars/kmb_{label.lower()}_drivable'
model=Kn5(CAR/(CAR.name+'.kn5'))
nodes=list(model.root.walk());names={n.name for _,n in nodes}
errors=[];warnings=[];references=[]
for p in (CAR/'data').glob('*.ini'):
    for raw in p.read_text(encoding='utf-8-sig').splitlines():
        line=raw.split(';')[0].strip()
        if '=' not in line:continue
        key,value=map(str.strip,line.split('=',1))
        if value.lower().endswith(('.lut','.kn5','.ksanim')):
            if value.lower().endswith('.ksanim'):
                target=CAR/'animations'/value
            elif value.lower().endswith('.kn5'):
                target=CAR/value
            else:
                target=p.parent/value
            references.append({'file':p.name,'key':key,'target':value,'exists':target.exists()})
            if not target.exists():errors.append(f'{p.name}: missing {value}')
        if key in ('OBJECT_NAME','NAME') and p.name in ('analog_instruments.ini','mirrors.ini') and value and value not in names:
            errors.append(f'{p.name}: unknown node {value}')
for parent,n in nodes:
    if n.kind!=2:continue
    if not np.isfinite(n.vertices).all():errors.append('nonfinite vertices: '+n.name)
    if n.material_id>=len(model.materials):errors.append('invalid material: '+n.name)
    idxoff=n.vertex_offset+n.vertex_count*n.vertex_stride+4
    indices=np.frombuffer(n.payload,dtype='<u2',count=n.index_count,offset=idxoff)
    if len(indices) and indices.max()>=n.vertex_count:errors.append('invalid index: '+n.name)
for name in ['WHEEL_LF','WHEEL_RF','WHEEL_LR','WHEEL_RR','STEER_HR','ARROW_SPEED','ARROW_RPM']:
    if sum(n.name==name for _,n in nodes)!=1:errors.append('missing/duplicate native node '+name)
for suffix in ['LF','RF','LR','RR']:
    hub=next((n for _,n in nodes if n.name=='HUB_'+suffix),None)
    if hub is None or not {'WHEEL_'+suffix,'SUSP_'+suffix}.issubset({c.name for c in hub.children}):
        errors.append('incomplete native HUB/WHEEL/SUSP hierarchy: '+suffix)
texture_names={t['name'].lower() for t in model.textures}
for m in model.materials:
    for tex in m['maps']:
        if tex['texture'].lower() not in texture_names:warnings.append('Embedded texture absent: '+tex['texture'])
guids=(CAR/'sfx/GUIDs.txt').read_text(encoding='utf-8-sig')
if f'event:/cars/{CAR.name}/engine' not in guids:errors.append('engine sound GUID absent')
if f'bank:/{CAR.name}' not in guids:errors.append('bank GUID absent')
physics={}
for name in ['car','suspensions','drivetrain','engine','tyres']:
    p=configparser.ConfigParser(interpolation=None,strict=False,inline_comment_prefixes=(';',));p.read(CAR/'data'/f'{name}.ini')
    physics[name]={s:dict(p[s]) for s in p.sections()}
assert physics['drivetrain']['GEARS']['count']==('4' if label=='E200' else '6')
assert float(physics['suspensions']['BASIC']['wheelbase'])>4
report={'errors':errors,'warnings':sorted(set(warnings)),'references':references,
 'mesh_count':sum(n.kind==2 for _,n in nodes),'triangles':sum(n.index_count//3 for _,n in nodes),
 'model_sha256':hashlib.file_digest(open(CAR/(CAR.name+'.kn5'),'rb'),'sha256').hexdigest(),
 'files':len(list(CAR.rglob('*'))),'status':'PASS' if not errors else 'FAIL'}
(PACKAGE/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
if errors:raise SystemExit(1)
