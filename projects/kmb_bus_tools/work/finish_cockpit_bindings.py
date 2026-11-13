from pathlib import Path
import sys,json,re
import numpy as np
from kn5_tools import Kn5,Node
from patch_bus_cockpit_helpers import bound,lua

ROOT=Path(__file__).resolve().parent.parent
for label in ['E200','E6M']:
 car=ROOT/f'outputs/{label}_playable/content/cars/kmb_{label.lower()}_drivable'
 p=car/(car.name+'.kn5');k=Kn5(p);nodes={n.name:n for _,n in k.root.walk()}
 if label=='E6M':
  for name,pivot,newname in [('wiperl',[-.1382,1.299,4.13665],'KMB_WIPER_L'),
                            ('wiperr',[-1.0064,1.2995,4.09015],'KMB_WIPER_R')]:
   n=nodes[name]
   for child in n.children:
    child.vertices[:,:3]-=pivot;bound(child)
   n.payload=bytearray(Node.dummy(name,translation=pivot).payload)
   n.children=[Node.dummy(newname,n.children)]
  k.write(p)
 bindings=json.loads((car/'extension/cockpit_bindings.json').read_text())
 for key,name in [('wipers','dash_lever'),('highbeam','dash_leverh')]:
  bindings['buttons'][key]=next(n.name for n in nodes[name].children if n.kind==2)
 (car/'extension/cockpit_bindings.json').write_text(json.dumps(bindings,indent=2))
 script='local bindings = '+lua(bindings)+'\n'+(ROOT/'work/bus_cockpit.lua').read_text()
 (car/'extension/cockpit.lua').write_text(script,encoding='utf-8')
 ext=(car/'extension/ext_config.ini').read_text()
 ext=re.sub(r'\[SCRIPT_\.\.\.\]\s*SCRIPT=".*?"\s*(?=; AC cockpit)', '',ext,flags=re.S)
 (car/'extension/ext_config.ini').write_text(ext)
 print(label,'wiper and high-beam controls added; runtime uses script.update')
