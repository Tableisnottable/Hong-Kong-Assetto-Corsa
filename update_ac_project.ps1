# Assetto Corsa Pipeline - Export FBX & Save Checkable .blend File
$ErrorActionPreference = "Continue"

function Write-StepHeader($stepNum, $title, $color) {
    Write-Host "`n========================================" -ForegroundColor $color
    Write-Host " [$stepNum] $title" -ForegroundColor $color
    Write-Host "========================================" -ForegroundColor $color
}

# --- Stage 1: Setup ---
Write-StepHeader "Stage 1" "1. Setup & Environment" Cyan
git config --global http.postBuffer 524288000
Write-Host "Stage 1 completed." -ForegroundColor Green

# --- Stage 2: Background Blender Execution ---
Write-StepHeader "Stage 2" "2. Run Blender & Generate .blend + .fbx" Green

# Generate Python script for Blender
$blenderPipeline = @"
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
"@
$blenderPipeline | Out-File -FilePath "blender_ac_pipeline.py" -Encoding utf8

# Explicit Steam Blender executable path
$blenderExe = "A:\SteamLibrary\steamapps\common\Blender\blender.exe"

if (Test-Path $blenderExe) {
    Write-Host "Found Steam Blender at: $blenderExe" -ForegroundColor Cyan
    Write-Host "Running Blender background process..." -ForegroundColor Gray
    
    $blendFile = Get-ChildItem -Path "." -Filter "*.blend" | Select-Object -First 1 -ExpandProperty Name
    if ($blendFile) {
        & "$blenderExe" -b "$blendFile" -P blender_ac_pipeline.py
    } else {
        & "$blenderExe" -b -P blender_ac_pipeline.py
    }
    Write-Host "Blender execution finished." -ForegroundColor Green
} else {
    Write-Host "[ERROR] Could not find Blender at $blenderExe." -ForegroundColor Red
}

# --- Stage 3: SDK Check ---
Write-StepHeader "Stage 3" "3. SDK Directory Check" Yellow
$sdkDir = "./sdk_output"
if (-not (Test-Path -Path $sdkDir)) { New-Item -ItemType Directory -Path $sdkDir | Out-Null }

# --- Stage 4: Sync ---
Write-StepHeader "Stage 4" "4. Output & Git Sync" Magenta
try {
    git fetch --all
    git pull
    git add .
    git commit -m "Generated track_check.blend and track_mesh.fbx for map review"
    git push
    Write-Host "Git repository synchronized successfully." -ForegroundColor Green
} catch {
    Write-Host "Git sync notice: $_" -ForegroundColor Red
}

Write-Host "`n[COMPLETED] Pipeline execution finished!" -ForegroundColor Cyan
