param(
    [string]$RepoDir = "C:\Users\Table\Documents\GitHub\Hong-Kong-Assetto-Corsa"
)

# 1. 自動檢查並下載開源 CLI KN5 Converter
$toolsDir = Join-Path $RepoDir "tools"
if (-not (Test-Path $toolsDir)) { New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null }

$converterExe = Join-Path $toolsDir "fbx2kn5.exe"

# 2. 自動搜尋或轉換 FBX 檔案
$carsRootDir = Join-Path $RepoDir "content\cars"
$carFolders  = Get-ChildItem -Path $carsRootDir -Directory

foreach ($folder in $carFolders) {
    $fbxFiles = Get-ChildItem -Path $folder.FullName -Filter "*.fbx"

    foreach ($fbx in $fbxFiles) {
        $kn5Name = $fbx.BaseName + ".kn5"
        $kn5Path = Join-Path $folder.FullName $kn5Name

        Write-Host "[>] Processing $fbx.Name -> $kn5Name..." -ForegroundColor Cyan
        
        if (Test-Path $converterExe) {
            Start-Process -FilePath $converterExe -ArgumentList "`"$($fbx.FullName)`" `"$kn5Path`"" -Wait -NoNewWindow
        }
    }
}

# 3. 儲存本腳本至 Repo 並同步 GitHub
$scriptSavePath = Join-Path $RepoDir "Convert-FBXToKN5.ps1"
$MyInvocation.MyCommand.ScriptBlock.ToString() | Set-Content -Path $scriptSavePath

Set-Location -Path $RepoDir
git add .
$status = git status --porcelain
if ($status) {
    git commit -m "Add fallback FBX to KN5 conversion script and update cars"
    git push origin main
    Write-Host "[?] 已成功儲存腳本並同步至 GitHub！" -ForegroundColor Green
} else {
    Write-Host "[i] 沒有變更需要同步。" -ForegroundColor Yellow
}

