"""Set the requested E200 view and move its seat to keep that view clear."""
from pathlib import Path
from datetime import datetime
import re,shutil,json,sys,struct
import numpy as np
from kn5_tools import Kn5

ROOT=Path(__file__).resolve().parent.parent
PACKAGE=ROOT/'outputs/E200_playable'
CAR=PACKAGE/'content/cars/kmb_e200_drivable'
INSTALLED=Path('A:/SteamLibrary/steamapps/common/assettocorsa/content/cars/kmb_e200_drivable')
EYES='-0.720000,0.800000,3.354297'
backup=PACKAGE/'backups'/('before_camera_back_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
backup.mkdir(parents=True)
changes={
 'data/car.ini':{'DRIVEREYES':EYES,'BONNET_CAMERA_POS':EYES},
 'data/dash_cam.ini':{'POS':EYES},
 'data/cameras.ini':{'POSITION':EYES},
}
old= (CAR/'data/car.ini').read_text()
assert 'DRIVEREYES=-0.720000,0.800000,3.654297' in old,'Adjustment already applied or camera changed'
files=list(changes)+['kmb_e200_drivable.kn5']
for label,folder in [('staged',CAR),('installed',INSTALLED)]:
 for rel in files:
  saved=backup/label/rel;saved.parent.mkdir(parents=True,exist_ok=True)
  shutil.copy2(folder/rel,saved)
for rel,keys in changes.items():
 text=(CAR/rel).read_text(encoding='utf-8-sig')
 for key,value in keys.items():
  text,count=re.subn(r'(?m)^'+re.escape(key)+r'=.*$',key+'='+value,text)
  assert count==1,key
 (CAR/rel).write_text(text,encoding='utf-8')
model=Kn5(CAR/'kmb_e200_drivable.kn5')
seats=[n for _,n in model.root.walk() if n.kind==2 and 'E200_dash_driverseat__' in n.name]
assert len(seats)==2
for n in seats:
 n.vertices[:,2]-=.30
 # Keep the KN5 bounding-sphere center in step with its vertices.
 sphere=n.vertex_offset+n.vertex_count*n.vertex_stride+4+n.index_count*2+16
 center=np.frombuffer(n.payload,dtype='<f4',count=4,offset=sphere)
 center[2]-=.30
model.write(CAR/'kmb_e200_drivable.kn5')
for rel in files:
 shutil.copy2(CAR/rel,INSTALLED/rel)
 assert (CAR/rel).read_bytes()==(INSTALLED/rel).read_bytes()
report={'camera_ac':[-.72,.8,3.354297],'camera_moved_back_m':.30,
 'seat_moved_back_m':.30,'height_and_pitch':'unchanged','backup':str(backup),
 'installed_path':str(INSTALLED),'files':files,'in_game_test':'Pending user test'}
(PACKAGE/'camera_adjustment_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
