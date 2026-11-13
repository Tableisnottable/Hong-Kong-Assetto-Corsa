from pathlib import Path
import collections,importlib.util,json,re,struct
import numpy as np

ROOT=Path(__file__).resolve().parent.parent
SOURCE=Path('A:/SteamLibrary/steamapps/common/OMSI 2/Vehicles/ADL_E200_KMB_AAU_with_OrangePai')
CFG=SOURCE/'Model/model_AAU.cfg'
spec=importlib.util.spec_from_file_location('o3dreader',ROOT/'work/vendor/Blender-O3D-IO-Public/o3d_io/o3dconvert.py')
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)

def commands(text):
    result=[];current=None
    for index,line in enumerate(text.splitlines()):
        if re.fullmatch(r'\[[^\]]+\]',line):
            current={'tag':line[1:-1].lower(),'args':[],'line':index+1};result.append(current)
        elif current is not None:current['args'].append(line.strip())
    return result

def meshes():
    result=[]
    for c in commands(CFG.read_text(encoding='cp1252')):
        if c['tag']=='mesh':result.append({'path':c['args'][0],'line':c['line'],'commands':[]})
        elif result:result[-1]['commands'].append(c)
    return result

if __name__=='__main__':
    blocks=meshes();rows=[];conditions=collections.Counter();encrypted=[];missing=[]
    for b in blocks:
        p=SOURCE/'Model'/b['path'].replace('\\','/')
        if not p.exists():missing.append(str(p));continue
        data=p.read_bytes()
        if data[:2]!=b'\x84\x19':raise ValueError('Invalid header: '+str(p))
        if data[2]>3 and struct.unpack_from('<I',data,4)[0]!=0xffffffff:
            encrypted.append(b['path']);continue
        parsed=reader.import_o3d(data);v=np.array([x[0] for x in parsed[1]])
        vis=[c['args'][:2] for c in b['commands'] if c['tag']=='visible']
        for var,value in vis:conditions[(var,value)]+=1
        rows.append({'path':b['path'],'vertices':len(v),'triangles':len(parsed[2]),
          'min':v.min(0).tolist(),'max':v.max(0).tolist(),'visibility':vis,
          'textures':[m[4] for m in parsed[3]],'commands':b['commands']})
    report={'source':str(SOURCE),'cfg':str(CFG),'mesh_instances':len(blocks),'decoded_instances':len(rows),
      'encrypted':encrypted,'missing':missing,'visibility_counts':[{ 'var':k[0],'value':k[1],'count':v} for k,v in conditions.items()],
      'meshes':rows}
    (ROOT/'work/e200_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='meshes'},indent=2))
    print('INTERESTING',json.dumps([{'path':r['path'],'min':r['min'],'max':r['max'],'visibility':r['visibility']} for r in rows if any(w in r['path'].lower() for w in ['whl','wheel','steer','strw','driver','seat','glass','body','ext','speedo','rpm'])],indent=2))
