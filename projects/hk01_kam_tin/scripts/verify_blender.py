"""Read-back verification of the saved .blend. Makes no edits."""
from pathlib import Path
import bpy,json,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'project.json').read_text(encoding='utf-8'));R=CFG['first_region']
xmin,ymin,xmax,ymax=R['bounds_epsg2326'];s=R['terrain_mesh_spacing_m'];ox=R['origin_easting_m'];oy=R['origin_northing_m']
nx=int((xmax-xmin)/s)+1;ny=int((ymax-ymin)/s)+1
terrain=bpy.data.objects['TERRAIN_REFERENCE_20m'];coords=np.empty(len(terrain.data.vertices)*3,dtype=np.float64);terrain.data.vertices.foreach_get('co',coords);grid=coords.reshape(-1,3)[:,2].reshape(ny,nx)
def mh(x,y):
    fx=(x+ox-xmin)/s;fy=(y+oy-ymin)/s
    c=np.clip(np.floor(fx).astype(int),0,nx-2);r=np.clip(np.floor(fy).astype(int),0,ny-2)
    a=np.clip(fx-c,0,1);b=np.clip(fy-r,0,1)
    z00=grid[r,c];z10=grid[r,c+1];z01=grid[r+1,c];z11=grid[r+1,c+1]
    return np.where(a>=b,z00*(1-a)+z10*(a-b)+z11*b,z00*(1-b)+z11*a+z01*(b-a))

errors=[];road_count=0;tri_count=0;clearance_min=math.inf;clearance_max=-math.inf;finite=True;building_roof_min=math.inf;degenerate=0
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    vv=np.empty(len(ob.data.vertices)*3,dtype=np.float64);ob.data.vertices.foreach_get('co',vv);vv=vv.reshape(-1,3)
    if not np.isfinite(vv).all():finite=False;errors.append(f'Nonfinite mesh: {ob.name}')
    if ob.name.startswith('REF_'):
        road_count+=1;ob.data.calc_loop_triangles();tt=np.empty(len(ob.data.loop_triangles)*3,dtype=np.int32);ob.data.loop_triangles.foreach_get('vertices',tt);tt=tt.reshape(-1,3)
        if not len(tt):errors.append(f'Empty road faces: {ob.name}');continue
        tri_count+=len(tt);v=vv[tt];cent=v.mean(axis=1);delta=cent[:,2]-mh(cent[:,0],cent[:,1]);clearance_min=min(clearance_min,float(delta.min()));clearance_max=max(clearance_max,float(delta.max()))
        area=np.linalg.norm(np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]),axis=1)/2;degenerate+=int((area<1e-9).sum())
        if delta.min()<.20:errors.append(f'Road terrain intersection: {ob.name}, clearance={delta.min():.6f}')
    elif ob.name.startswith('MASS_'):
        roof=vv[vv[:,2]==vv[:,2].max()];clearance=roof[:,2]-mh(roof[:,0],roof[:,1]);building_roof_min=min(building_roof_min,float(clearance.min()))
        if clearance.min()<1.9:errors.append(f'Building roof buried: {ob.name}')
if bpy.context.scene.unit_settings.scale_length!=1.0:errors.append('Unit scale is not one metre')
if degenerate:errors.append(f'{degenerate} zero-area road triangles')
if road_count!=len(json.loads((ROOT/'gis/region_roads_grid.json').read_text(encoding='utf-8'))['roads']):errors.append('Road object count does not match input')
out={'passed':not errors,'errors':errors,'saved_file':bpy.data.filepath,'unit_scale':bpy.context.scene.unit_settings.scale_length,'mesh_coordinates_finite':finite,'road_objects_verified':road_count,'road_triangle_centroids_checked':tri_count,'minimum_road_surface_clearance_m':clearance_min,'maximum_road_surface_clearance_m':clearance_max,'minimum_building_roof_clearance_at_footprint_vertices_m':building_roof_min,'zero_area_road_triangles':degenerate,'scope':'Saved Blender data integrity and reference-mesh terrain alignment; no game/physics/FPS validation'}
(ROOT/'reports/blender_verification.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('VERIFICATION',json.dumps(out),flush=True)
if errors:raise RuntimeError('Saved Blender scene verification failed')
