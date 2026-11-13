"""Repair wheel hierarchy and restore missing OMSI registration/glass details."""
from pathlib import Path
import copy,datetime,hashlib,io,json,shutil,struct
import numpy as np
from PIL import Image,ImageOps
from kn5_tools import Kn5,Node
from patch_bus_cockpit_helpers import bound

ROOT=Path(__file__).resolve().parent.parent
OMSI=Path('A:/SteamLibrary/steamapps/common/OMSI 2')
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

def dds(im):
 s=io.BytesIO();im.convert('RGBA').save(s,format='DDS',pixel_format='DXT5');return s.getvalue()

def font_text(fontname,text,size,color):
 folder=OMSI/'Fonts';lines=(folder/(fontname+'.oft')).read_text(encoding='cp1252').splitlines()
 i=lines.index('[newfont]');height=int(lines[i+4]);gap=int(lines[i+5]);glyphs={}
 atlas=Image.open(folder/lines[i+3]).convert('L')
 for j,line in enumerate(lines):
  if line=='[char]':glyphs[lines[j+1]]=(int(lines[j+2]),int(lines[j+3]),int(lines[j+4]))
 strips=[]
 for c in text:
  a,b,y=glyphs[c];strips.append(atlas.crop((a,y,b,y+height)))
 mask=Image.new('L',(sum(s.width+gap for s in strips),height),0);x=0
 for s in strips:mask.paste(s,(x,0));x+=s.width+gap
 mask=mask.crop(mask.getbbox());fit=ImageOps.contain(mask,(int(size[0]*.92),int(size[1]*.85)),Image.Resampling.LANCZOS)
 out=Image.new('RGBA',size,(0,0,0,0));ink=Image.new('RGBA',fit.size,color);ink.putalpha(fit)
 out.alpha_composite(ink,((size[0]-fit.width)//2,(size[1]-fit.height)//2));return out

for label in ['E200','E6M']:
 package=ROOT/f'outputs/{label}_playable';car=package/f'content/cars/kmb_{label.lower()}_drivable'
 p=car/(car.name+'.kn5');backup=package/f'backups/before_missing_parts_{stamp}';backup.mkdir(parents=True)
 shutil.copy2(p,backup/p.name)
 k=Kn5(p);nodes={n.name:n for _,n in k.root.walk()};rows=[]
 # Working AC donor: root > HUB > WHEEL/SUSP, with local wheel origin zero.
 for suffix in ['LF','RF','LR','RR']:
  wheel=nodes['WHEEL_'+suffix];hub=nodes['HUB_'+suffix]
  if wheel in hub.children:continue
  assert wheel in k.root.children and hub in k.root.children
  original=wheel.matrix.copy();hub.payload=bytearray(original.astype('<f4').tobytes())
  wheel.payload=bytearray(np.eye(4,dtype='<f4').tobytes())
  k.root.children.remove(wheel);hub.children.extend([Node.dummy('SUSP_'+suffix),wheel])
  rows.append({'hub':hub.name,'wheel':wheel.name,'world_origin':original[3,:3].tolist()})
 updates={}
 if label=='E200':
  source=OMSI/'Vehicles/ADL_E200_KMB_AAU_with_OrangePai'
  fleet,registration=(source/'REG_AAU.org').read_text().splitlines()[0].split(maxsplit=1)
  registration=' '.join(registration.split())
  # Render the real registration from OMSI's glyph atlas, not a substitute font.
  plate=font_text('HKLicenseHingLee_LCNE',registration,(620,150),(10,10,10,255))
  updates['kmb_registration.dds']=dds(plate)
  updates['kmb_fleet.dds']=dds(font_text('KMB_reg_LCNE',fleet,(500,180),(210,0,0,255)))
  base=k.materials[nodes['E200_reg__m0'].material_id]
  def assign(name,tex):
   n=nodes[name];m=copy.deepcopy(base);m['name']=name+'_identity';m['maps'][0]['texture']=tex
   n.material_id=len(k.materials);k.materials.append(m)
   off=n.vertex_offset+n.vertex_count*n.vertex_stride+4+n.index_count*2
   struct.pack_into('<I',n.payload,off,n.material_id)
  assign('E200_reg__m0','kmb_registration.dds')
  assign('E200_cablabel__m7','kmb_registration.dds')
  for name in ['E200_inner_glass__m10','E200_outer_glass__m7']:
   assign(name,'kmb_fleet.dds')
  # The old blanket 0.28 alpha multiplier made all E200 glass nearly invisible.
  # Restore the source alpha on body/glazing atlases, keeping frames and labels.
  report=json.loads((package/'build_report.json').read_text(encoding='utf-8'))
  restored=[]
  for entry in report['texture_sources']:
   if not entry['glass_variant']:continue
   if Path(entry['source']).name.lower() not in ['e2oo_s.tga','e2oo_b.tga','e2oo_f.tga','e2oo_spots.tga','glass.tga']:continue
   im=Image.open(entry['source']).convert('RGBA')
   if max(im.size)>2048:im.thumbnail((2048,2048),Image.Resampling.LANCZOS)
   updates[entry['embedded']]=dds(im);restored.append(entry['embedded'])
  rows.append({'registration':registration,'fleet':fleet,'source':str(source/'REG_AAU.org'),'restored_glass_alpha':restored})
 k.rebuild_prefix(updates);k.write(p)
 # Explicitly register interaction for the display's clickable controls.
 ext=car/'extension/ext_config.ini';text=ext.read_text(encoding='utf-8')
 if 'INTERACTIVE=1' not in text:text=text.replace('[SCRIPTABLE_DISPLAY_0]','[SCRIPTABLE_DISPLAY_0]\nINTERACTIVE=1\nKEEP_BACKGROUND=0')
 ext.write_text(text,encoding='utf-8')
 (package/'missing_parts_report.json').write_text(json.dumps({'backup':str(backup),'repairs':rows,'model_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'runtime_test':'pending reload in AC'},indent=2))
 print(label,'wheel hierarchy repaired;',len(updates),'texture updates')
