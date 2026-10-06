import bpy

def export_ac_fbx():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    if "AC_START_0" not in bpy.data.objects:
        dummy = bpy.data.objects.new("AC_START_0", None)
        bpy.context.collection.objects.link(dummy)

    out_path = bpy.path.abspath("//build/map.fbx")
    bpy.ops.export_scene.fbx(
        filepath=out_path,
        use_selection=False,
        axis_forward='Y',
        axis_up='Z',
        apply_unit_scale=True
    )
    print("FBX Export Completed.")

if __name__ == "__main__":
    export_ac_fbx()
