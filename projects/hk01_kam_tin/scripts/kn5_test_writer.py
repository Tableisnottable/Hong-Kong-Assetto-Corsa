"""Small static-scene KN5 v5 writer for this new track.
Binary field order checked against AcTools/Kn5File/Kn5Writer.cs and the local
Assetto Corsa SDK-compatible reader. No prior track assets are imported.
"""
import struct
import numpy as np
IDENTITY=(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1)
def pack(fmt,*v):return struct.pack('<'+fmt,*v)
def string(s):
    b=s.encode('utf-8');return pack('I',len(b))+b
def dummy(name,children=0,matrix=IDENTITY):return pack('I',1)+string(name)+pack('IB16f',children,1,*matrix)
def material(name,texture,ambient=.45,diffuse=.65,specular=.03):
    props={'ksAmbient':ambient,'ksDiffuse':diffuse,'ksSpecular':specular,'ksSpecularEXP':15,'ksAlphaRef':.5}
    b=string(name)+string('ksPerPixel')+pack('BBII',0,0,0,len(props))
    for k,v in props.items():b+=string(k)+pack('10f',v,*([0]*9))
    return b+pack('I',1)+string('txDiffuse')+pack('I',0)+string(texture)

def mesh_arrays(obj):
    mesh=obj.data;mesh.calc_loop_triangles();p=np.empty((len(mesh.vertices),3),dtype='<f4');mesh.vertices.foreach_get('co',p.ravel())
    m=np.asarray(obj.matrix_world,dtype=np.float32);p=p@m[:3,:3].T+m[:3,3]
    p=(p[:,(0,2,1)]*np.array([1,1,-1])).astype('<f4')
    normal=np.empty((len(mesh.loops),3),dtype='<f4');mesh.corner_normals.foreach_get('vector',normal.ravel());normal=normal@np.linalg.inv(m[:3,:3]);normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-8);normal=(normal[:,(0,2,1)]*np.array([1,1,-1])).astype('<f4')
    uv=np.zeros((len(mesh.loops),2),dtype='<f4')
    if mesh.uv_layers.active:mesh.uv_layers.active.uv.foreach_get('vector',uv.ravel());uv[:,1]=1-uv[:,1]
    vi=np.empty(len(mesh.loops),dtype=np.int32);mesh.loops.foreach_get('vertex_index',vi)
    tris=np.empty((len(mesh.loop_triangles),3),dtype=np.int32);mesh.loop_triangles.foreach_get('loops',tris.ravel())
    return np.column_stack((p[vi],normal,uv)).astype('<f4'),tris

def mesh_blob(name,attr,tris,material_id,cast_shadows=True,visible=True,lodout=8000):
    flat=np.ascontiguousarray(attr[tris.ravel()]);_,selected,indices=np.unique(flat.view('V32').ravel(),return_index=True,return_inverse=True)
    if len(selected)>65535:raise ValueError('KN5 vertex limit exceeded')
    vv=np.zeros((len(selected),11),dtype='<f4');vv[:,:8]=flat[selected]
    # Orthogonal unit tangent; ksPerPixel does not use a normal-map tangent.
    normal=vv[:,3:6];t=np.cross(np.tile([0,0,1.],(len(vv),1)),normal);bad=np.linalg.norm(t,axis=1)<1e-5;t[bad]=np.cross(np.tile([1,0,0.],(int(bad.sum()),1)),normal[bad]);t/=np.maximum(np.linalg.norm(t,axis=1,keepdims=True),1e-8);vv[:,8:11]=t
    center=(vv[:,:3].min(axis=0)+vv[:,:3].max(axis=0))/2;radius=float(np.linalg.norm(vv[:,:3]-center,axis=1).max())
    return pack('I',2)+string(name)+pack('IB3BI',0,1,int(cast_shadows),int(visible),0,len(vv))+vv.tobytes()+pack('I',len(indices))+indices.astype('<u2').tobytes()+pack('II6fB',material_id,0,0,lodout,*center,radius,1)

def export(path,objects,materials,textures,dummies):
    mat_ids={name:i for i,(name,texture) in enumerate(materials)}
    blobs=[];report=[]
    for ob in objects:
        attr,tris=mesh_arrays(ob)
        if not len(tris):continue
        # Visual GIS cuts and decimation can collapse tiny fragments at float32
        # precision. Keep physical meshes byte-for-byte unchanged.
        if not ob.name[:1].isdigit():
            xyz=attr[tris,:3].astype(np.float64)
            valid=np.linalg.norm(np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),axis=1)>2e-8
            tris=tris[valid]
            if not len(tris):continue
        mat=ob.data.materials[0].name
        # 5k triangles per node bounds the worst-case unique vertices at15k.
        for j in range(0,len(tris),5000):
            part=tris[j:j+5000];name=ob.name if len(tris)<=5000 else f'{ob.name}_{j//5000:03d}'
            blobs.append(mesh_blob(name,attr,part,mat_ids[mat],bool(ob.get('cast_shadows',True)),bool(ob.get('renderable',True)),float(ob.get('lodout',8000))))
            report.append({'name':name,'triangles':len(part),'material':mat})
    with path.open('wb') as f:
        f.write(b'sc6969'+pack('II',5,len(textures)))
        for name,p in textures:
            b=p.read_bytes();f.write(pack('I',1)+string(name)+pack('I',len(b))+b)
        f.write(pack('I',len(materials)))
        for name,texture in materials:f.write(material(name,texture))
        f.write(dummy('HK01_KamTin_Test',len(blobs)+len(dummies)))
        for name,matrix in dummies:f.write(dummy(name,0,matrix))
        for blob in blobs:f.write(blob)
    return {'file':str(path),'bytes':path.stat().st_size,'mesh_nodes':len(blobs),'triangles':sum(x['triangles'] for x in report),'materials':len(materials),'embedded_textures':len(textures),'nodes':report}
