"""Check native donor structure and preservation of every mesh world transform."""
from pathlib import Path
import json,numpy as np
from kn5_tools import Kn5
ROOT=Path(__file__).resolve().parent.parent
def world(k):
 result={}
 def visit(n,w=np.eye(4)):
  if n.kind==1:w=n.matrix@w
  if n.kind==2:result[n.name]=(np.c_[n.vertices[:,:3],np.ones(n.vertex_count)]@w)[:,:3]
  for c in n.children:visit(c,w)
 visit(k.root);return result
for label in ['E200','E6M']:
 package=ROOT/f'outputs/{label}_playable';car=package/f'content/cars/kmb_{label.lower()}_drivable'
 r=json.loads((package/'missing_parts_report.json').read_text());old=Kn5(Path(r['backup'])/(car.name+'.kn5'));new=Kn5(car/(car.name+'.kn5'))
 a,b=world(old),world(new);assert a.keys()==b.keys()
 error=max(float(np.abs(a[name]-b[name]).max()) for name in a);assert error<1e-6,error
 nodes={n.name:n for _,n in new.root.walk()}
 for suffix in ['LF','RF','LR','RR']:
  hub=nodes['HUB_'+suffix];wheel=nodes['WHEEL_'+suffix]
  assert wheel in hub.children and nodes['SUSP_'+suffix] in hub.children
  assert np.allclose(wheel.matrix,np.eye(4))
  assert wheel.children
 (package/'wheel_hierarchy_validation.json').write_text(json.dumps({'status':'PASS','world_mesh_max_change_m':error,'all_meshes_preserved':len(a),'native_hierarchy':'HUB > WHEEL and SUSP, matching working AC bus donor','runtime_test':'pending AC reload'},indent=2))
 print(label,'wheel hierarchy PASS;',len(a),'mesh world transforms preserved')
