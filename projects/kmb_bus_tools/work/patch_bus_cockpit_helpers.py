import json,struct
import numpy as np
def bound(n):
 p=n.vertices[:,:3];c=(p.min(0)+p.max(0))/2;r=np.linalg.norm(p-c,axis=1).max()
 off=n.vertex_offset+n.vertex_count*n.vertex_stride+4+n.index_count*2+16
 struct.pack_into('<4f',n.payload,off,*c,float(r))
def lua(v):
 if isinstance(v,bool):return 'true' if v else 'false'
 if isinstance(v,str):return json.dumps(v,ensure_ascii=False)
 if isinstance(v,(float,int)):return str(v)
 if isinstance(v,list):return '{'+','.join(lua(x) for x in v)+'}'
 return '{'+','.join('['+lua(key)+']='+lua(value) for key,value in v.items())+'}'
