import bpy, os

def run_map_pipeline():
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1.0

    if len(bpy.data.objects) == 0 or not any(o.type == 'MESH' for o in bpy.data.objects):
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=100, y_subdivisions=100, size=500)
    
    mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
    for o in bpy.data.objects:
        o.select_set(False)
    
    target_obj = mesh_objs[0]
    target_obj.select_set(True)
    bpy.context.view_layer.objects.active = target_obj
    target_obj.name = '1ROAD_main'
    
    if not target_obj.modifiers.get('AC_Road_GeoNodes'):
        target_obj.modifiers.new(name='AC_Road_GeoNodes', type='NODES')

    # 1. Save .blend file for manual checking
    blend_output_path = os.path.abspath('./track_check.blend')
    bpy.ops.wm.save_as_mainfile(filepath=blend_output_path)
    print('[BLENDER SAVE SUCCESS] .blend file saved to:', blend_output_path)
            
    # 2. Export FBX for SDK
    export_path = os.path.abspath('./sdk_output/track_mesh.fbx')
    os.makedirs(os.path.dirname(export_path), exist_ok=True)
    
    bpy.ops.export_scene.fbx(
        filepath=export_path,
        use_selection=False,
        axis_forward='-Z',
        axis_up='Y'
    )
    print('[BLENDER EXPORT SUCCESS] FBX exported to:', export_path)

if __name__ == '__main__':
    run_map_pipeline()
