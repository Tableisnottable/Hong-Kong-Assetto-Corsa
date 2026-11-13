"""Blender --background --factory-startup --python build_blender.py
Creates a 1:1 regional geodata blockout. Never writes into an AC installation.
Road strips and building masses are reference geometry, not finished collision.
"""
from pathlib import Path
import bpy, json, math, sys
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'project.json').read_text(encoding='utf-8'))
REG=CFG['first_region']; OX=REG['origin_easting_m']; OY=REG['origin_northing_m']
XMIN,YMIN,XMAX,YMAX=REG['bounds_epsg2326']; STEP=REG['terrain_mesh_spacing_m']
roads=json.loads((ROOT/'gis/region_roads_grid.json').read_text(encoding='utf-8'))['roads']
buildings=json.loads((ROOT/'gis/region_buildings_grid.json').read_text(encoding='utf-8'))['buildings']
terrain=np.load(ROOT/'gis/region_terrain_5m.npz')
HEIGHTS=terrain['z']; TX=float(terrain['x0']); TY=float(terrain['y0']); CELL=float(terrain['cell']); NODATA=float(terrain['nodata'])
report={'stage':'Reference blockout, not playable','origin_hk1980':[OX,OY],'metres_per_blender_unit':1,'terrain_nodata_samples':0,'roads_built':0,'grade_separation_review':0,'buildings_built':0,'buildings_with_estimated_height':0,'buildings_with_courtyards_skipped':0,'empty_geometries':0,'road_degenerate_faces_removed':0}

def height(x,y):
    fx=(x-TX)/CELL; fy=(TY-y)/CELL
    c=max(0,min(HEIGHTS.shape[1]-2,int(math.floor(fx)))); r=max(0,min(HEIGHTS.shape[0]-2,int(math.floor(fy))))
    a=float(fx-c); b=float(fy-r); q=HEIGHTS[r:r+2,c:c+2]
    if np.any(q==NODATA):
        report['terrain_nodata_samples']+=1
        valid=q[q!=NODATA]
        return float(valid.mean()) if valid.size else 0.0
    return float(q[0,0]*(1-a)*(1-b)+q[0,1]*a*(1-b)+q[1,0]*(1-a)*b+q[1,1]*a*b)

# Reset only the newly launched factory-startup Blender process.
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene; scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1.0
scene['stage']='GEOREFERENCED BLOCKOUT — NOT PLAYABLE'
scene['horizontal_crs']='EPSG:2326';scene['vertical_datum']='Hong Kong Principal Datum'
scene['origin_easting_m']=OX;scene['origin_northing_m']=OY
scene['source_attribution']='© OpenStreetMap contributors; Lands Department, HKSAR Government'

def coll(name):
    c=bpy.data.collections.new(name);scene.collection.children.link(c);return c
ground=coll('01_TERRAIN_BLOCKOUT_20m')
public=coll('02_ROAD_ALIGNMENT_PUBLIC_CANDIDATES')
review=coll('03_ACCESS_REVIEW_NOT_PUBLICLY_VERIFIED')
grade=coll('04_BRIDGE_TUNNEL_PROFILE_UNRESOLVED')
blocks=coll('05_BUILDING_MASSING_NOT_FINAL_SCENERY')
guide=coll('06_REFERENCE_AND_ORIGIN')
camera_collection=coll('07_PREVIEW_CAMERAS')

def material(name,col,roughness=.9):
    m=bpy.data.materials.new(name);m.diffuse_color=(*col,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*col,1);bs.inputs['Roughness'].default_value=roughness
    return m
terrain_mat=material('Terrain | muted green',(.22,.30,.20))
road_mat=material('Road reference | charcoal',(.055,.065,.075))
review_mat=material('Access / track review | amber',(.6,.25,.055))
grade_mat=material('Bridge / tunnel unresolved | violet',(.5,.09,.32))
building_mat=material('Building blockout | warm grey',(.48,.46,.41))

def mesh_object(name,verts,faces,collection,mat):
    if name.startswith('REF_') and faces:
        # Float32 storage can collapse extremely thin clipped fragments.
        vv=np.asarray(verts,dtype=np.float32);tt=np.asarray(faces,dtype=np.int32);v=vv[tt]
        area=np.linalg.norm(np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]),axis=1)/2
        valid=area>=1e-8;report['road_degenerate_faces_removed']+=int((~valid).sum())
        faces=[face for face,keep in zip(faces,valid) if keep]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj)
    if mat: mesh.materials.append(mat)
    obj['export_status']='REFERENCE_ONLY_NOT_AC_COLLISION'
    return obj

nx=int((XMAX-XMIN)/STEP)+1;ny=int((YMAX-YMIN)/STEP)+1
grid=np.empty((ny,nx),dtype=np.float32)
verts=[]
for r in range(ny):
    for c in range(nx):
        x=XMIN+c*STEP;y=YMIN+r*STEP;z=height(x,y);grid[r,c]=z
        verts.append((x-OX,y-OY,z))
faces=[]
for r in range(ny-1):
    for c in range(nx-1):
        a=r*nx+c; faces.extend([(a,a+1,a+nx+1),(a,a+nx+1,a+nx)])
obj=mesh_object('TERRAIN_REFERENCE_20m',verts,faces,ground,terrain_mat)
for p in obj.data.polygons:p.use_smooth=True
report['terrain_vertices']=len(verts);report['terrain_triangles']=len(faces)

def mesh_height(x,y):
    # Sample exactly the planar triangles used above, avoiding strips poking
    # under terrain because the terrain and road interpolation disagree.
    fx=(x-XMIN)/STEP;fy=(y-YMIN)/STEP
    c=max(0,min(nx-2,int(math.floor(fx))));r=max(0,min(ny-2,int(math.floor(fy))))
    a=max(0,min(1,fx-c));b=max(0,min(1,fy-r));z00=grid[r,c];z10=grid[r,c+1];z01=grid[r+1,c];z11=grid[r+1,c+1]
    return float(z00*(1-a)+z10*(a-b)+z11*b) if a>=b else float(z00*(1-b)+z11*a+z01*(b-a))

def densify(xy,spacing):
    out=[]
    for a,b in zip(xy,xy[1:]):
        length=math.hypot(b[0]-a[0],b[1]-a[1]);n=max(1,int(math.ceil(length/spacing)))
        out.extend([(a[0]+(b[0]-a[0])*j/n,a[1]+(b[1]-a[1])*j/n) for j in range(n)])
    if xy:out.append(xy[-1])
    return out

def clip_halfplane(poly,a,b,c):
    """Clip a convex polygon to a*x+b*y >= c."""
    if not poly:return []
    out=[];prev=poly[-1];vp=a*prev[0]+b*prev[1]-c
    for cur in poly:
        vc=a*cur[0]+b*cur[1]-c
        pin=vp>=-1e-8;cin=vc>=-1e-8
        if pin!=cin:
            t=vp/(vp-vc)
            out.append((prev[0]+t*(cur[0]-prev[0]),prev[1]+t*(cur[1]-prev[1])))
        if cin:out.append(cur)
        prev=cur;vp=vc
    return out

def conform_triangle(tri,vertices,polys):
    """Split the reference strip on the exact 20 m terrain triangle edges.
    Sampling alone at strip vertices can bury triangle interiors on slopes.
    Each resulting face lies on one terrain plane at a 0.22 m offset.
    """
    c0=max(0,int(math.floor((min(p[0] for p in tri)-XMIN)/STEP)))
    c1=min(nx-2,int(math.floor((max(p[0] for p in tri)-XMIN)/STEP)))
    r0=max(0,int(math.floor((min(p[1] for p in tri)-YMIN)/STEP)))
    r1=min(ny-2,int(math.floor((max(p[1] for p in tri)-YMIN)/STEP)))
    for r in range(r0,r1+1):
        for c in range(c0,c1+1):
            x=XMIN+c*STEP;y=YMIN+r*STEP;p=tri
            for a,b,k in ((1,0,x),(-1,0,-x-STEP),(0,1,y),(0,-1,-y-STEP)):
                p=clip_halfplane(p,a,b,k)
                if len(p)<3:break
            if len(p)<3:continue
            for a,b,k in ((1,-1,x-y),(-1,1,y-x)):
                q=clip_halfplane(p,a,b,k)
                if len(q)<3:continue
                base=len(vertices)
                vertices.extend((vx-OX,vy-OY,mesh_height(vx,vy)+.22) for vx,vy in q)
                for j in range(1,len(q)-1):
                    aa,bb,cc=q[0],q[j],q[j+1]
                    if abs((bb[0]-aa[0])*(cc[1]-aa[1])-(bb[1]-aa[1])*(cc[0]-aa[0]))>1e-7:
                        polys.append((base,base+j,base+j+1))

for rec in roads:
    xy=densify(rec['xy'],REG['road_preview_sample_spacing_m'])
    if len(xy)<2:report['empty_geometries']+=1;continue
    t=rec['tags'];unresolved=t.get('bridge','no')!='no' or t.get('tunnel','no')!='no' or t.get('layer','0')!='0'
    col,mat=(grade,grade_mat) if unresolved else ((public,road_mat) if rec['access_state']=='public_candidate' else (review,review_mat))
    vertices=[];polys=[];strip=[];half=rec['width_m']/2
    for i,(x,y) in enumerate(xy):
        prev=xy[max(0,i-1)];nxt=xy[min(len(xy)-1,i+1)];dx=nxt[0]-prev[0];dy=nxt[1]-prev[1];d=math.hypot(dx,dy)
        if d<1e-8:dx,dy,d=1,0,1
        for side in (-1,1):
            vx=x-side*dy/d*half;vy=y+side*dx/d*half
            # No fabricated bridge or tunnel heights; review geometry is
            # draped on terrain and visibly marked as requiring 3D design.
            strip.append((vx,vy))
        if i:
            a=(i-1)*2
            conform_triangle([strip[a],strip[a+2],strip[a+3]],vertices,polys)
            conform_triangle([strip[a],strip[a+3],strip[a+1]],vertices,polys)
    name=f"REF_{rec['osm_id']}_{rec['part']}_{rec['regional_part']}_{rec['name'] or rec['highway']}"
    ob=mesh_object(name,vertices,polys,col,mat)
    ob['osm_way_id']=rec['osm_id'];ob['width_source']=rec['width_source'];ob['width_m']=rec['width_m'];ob['access_state']=rec['access_state']
    ob['source_tags_json']=json.dumps(t,ensure_ascii=False)
    ob['height_status']='UNRESOLVED_GRADE_SEPARATION' if unresolved else 'TERRAIN_DRAPED_NOT_ROAD_SURVEY'
    report['roads_built']+=1;report['grade_separation_review']+=int(unresolved)

def building_height(tags):
    for k in ('height','building:height'):
        try:
            v=float(tags.get(k,'').replace(' m',''))
            if 2<=v<=500:return v,False
        except ValueError: pass
    try:
        levels=float(tags.get('building:levels',''))
        if 1<=levels<=100:return levels*3.0,True
    except ValueError:pass
    return 9.0,True

for b in buildings:
    g=b['geometry'];polygons=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']] if g['type']=='Polygon' else []
    for part,rings in enumerate(polygons):
        if len(rings)>1:report['buildings_with_courtyards_skipped']+=1;continue
        ring=rings[0][:-1]
        if len(ring)<3:continue
        signed_area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]+ring[:1]))
        if signed_area<0:ring=list(reversed(ring))
        h,estimated=building_height(b['tags']);ground_z=[mesh_height(x,y) for x,y in ring]
        base=min(ground_z)-.2;roof=max(ground_z)+h
        vv=[(x-OX,y-OY,base) for x,y in ring]+[(x-OX,y-OY,roof) for x,y in ring]
        n=len(ring);ff=[tuple(reversed(range(n))),tuple(range(n,n*2))]
        for i in range(n):j=(i+1)%n;ff.append((i,j,j+n,i+n))
        ob=mesh_object(f"MASS_{b['osm_type']}_{b['osm_id']}_{part}",vv,ff,blocks,building_mat)
        ob['height_m']=h;ob['height_estimated']=estimated;ob['osm_id']=b['osm_id']
        ob['foundation_status']='APPROXIMATE_MIN_TERRAIN_TO_MAX_TERRAIN_PLUS_HEIGHT';ob['massing_total_height_m']=roof-base
        report['buildings_built']+=1;report['buildings_with_estimated_height']+=int(estimated)

origin=bpy.data.objects.new('HK1980_ORIGIN_E826000_N833000',None);guide.objects.link(origin);origin.empty_display_type='ARROWS';origin.empty_display_size=100
guide.hide_render=True
for x in range(XMIN,XMAX,1000):
    for y in range(YMIN,YMAX,1000):
        e=bpy.data.objects.new(f'TILE_E{x//1000}_N{y//1000}',None);guide.objects.link(e);e.location=(x-OX+500,y-OY+500,0);e.empty_display_type='CUBE';e.empty_display_size=500;e.hide_render=True

def camera(name,location,target,ortho):
    data=bpy.data.cameras.new(name);ob=bpy.data.objects.new(name,data);camera_collection.objects.link(ob)
    ob.location=location;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler();data.type='ORTHO';data.ortho_scale=ortho;data.clip_end=50000
    return ob
cam=camera('Overview_6km_Blockout',(6000,-7600,8500),(0,0,120),10000)
camera('Top_Down_1to1',(0,0,11000),(0,0,0),6800)
scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24
scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.world.color=(.4,.4,.4)
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.65,.73,.8,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.6
ld=bpy.data.lights.new('Sun','SUN');ld.energy=2.5;ld.angle=.2;lo=bpy.data.objects.new('Sun',ld);camera_collection.objects.link(lo);lo.rotation_euler=(.5,-.4,-.5)
scene.view_settings.view_transform='AgX'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active;space.clip_end=50000;space.shading.type='SOLID';space.shading.color_type='MATERIAL'
            space.region_3d.view_distance=8500;space.region_3d.view_location=Vector((0,0,150));space.region_3d.view_rotation=cam.rotation_euler.to_quaternion()

txt=bpy.data.texts.new('READ_ME_FIRST.txt');txt.write('Hong Kong 1:1 — Kam Tin / Shek Kong\n6 x 6 km geospatial BLOCKOUT. NOT a playable Assetto Corsa track.\n1 Blender unit = 1 metre. X east, Y north, Z up.\nEPSG:2326 local origin E826000 N833000. Elevation is HK Principal Datum.\nRoad widths mostly estimated; bridge/tunnel profiles unresolved and shown in violet.\nAmber roads require access/surface review. Grey buildings are approximate masses.\nNo final road surface, junction stitching, collision, AI or KN5 release.\n© OpenStreetMap contributors, ODbL 1.0. Terrain: Lands Department, HKSAR Government.\nSee README.md, ATTRIBUTION.md and reports/ for limitations and source records.\n')
path=ROOT/'blender/HK01_KamTin_ShekKong_FOUNDATION.blend'
# Keep the delivered scene openable even when Cycles is disabled in the
# user's Blender preferences; use Cycles only for this process's preview.
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
scene.render.engine='CYCLES'
report['mesh_objects']=sum(o.type=='MESH' for o in scene.objects)
report['total_vertices']=sum(len(o.data.vertices) for o in scene.objects if o.type=='MESH')
report['total_polygons']=sum(len(o.data.polygons) for o in scene.objects if o.type=='MESH')
(ROOT/'reports/blender_build.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BUILD_REPORT',json.dumps(report),flush=True)
scene.render.filepath=str(ROOT/'previews/HK01_blender_overview.png')
bpy.ops.render.render(write_still=True)
print('RENDER_COMPLETE',flush=True)
