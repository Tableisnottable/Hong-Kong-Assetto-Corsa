# Auto-Elevate to Administrator if required
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Requesting Administrator privileges..." -ForegroundColor Yellow
    $powershell = [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
    Start-Process $powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    Exit
}

$ErrorActionPreference = "Continue"
$targetDir = "C:\Users\Table\Documents\GitHub\Hong-Kong-Assetto-Corsa\auto\v1"
Set-Location $targetDir

$BLENDER_EXE = "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
$PROJECT_DIR = $PSScriptRoot
$BUILD_DIR   = Join-Path $PROJECT_DIR "build"
$FBX_PATH    = Join-Path $BUILD_DIR "map.fbx"
$KN5_PATH    = Join-Path $BUILD_DIR "hk_road.kn5"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " RUNNING AUTO BUILD (LOCAL REPO OUTPUT ONLY)     " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

Write-Host "`n[1/3] Running CSDI Data Processing..." -ForegroundColor Yellow
if (Test-Path "$PROJECT_DIR\scripts\process_csdi.py") {
    python "$PROJECT_DIR\scripts\process_csdi.py"
}

Write-Host "`n[2/3] Exporting FBX via Blender..." -ForegroundColor Yellow
if (Test-Path "$PROJECT_DIR\map_source.blend") {
    & $BLENDER_EXE -b "$PROJECT_DIR\map_source.blend" -P "$PROJECT_DIR\scripts\blender_export.py"
}

Write-Host "`n[3/3] Converting FBX to KN5 in Local Build Directory..." -ForegroundColor Yellow
if (Test-Path "$PROJECT_DIR\tools\kn5-conv.exe") {
    & "$PROJECT_DIR\tools\kn5-conv.exe" --input $FBX_PATH --output $KN5_PATH
}

Write-Host "`n==================================================" -ForegroundColor Green
Write-Host " SUCCESS! Local build saved in auto/v1/build/" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

Write-Host "`n"
Read-Host -Prompt "Press Enter to exit"