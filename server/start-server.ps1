[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Container })]
    [string] $ServerRoot,

    [string] $ConfigDirectory = (Join-Path $PSScriptRoot "cfg")
)

$ErrorActionPreference = "Stop"
$serverExecutable = Join-Path $ServerRoot "acServer.exe"
$serverConfig = Join-Path $ConfigDirectory "server_cfg.ini"
$entryList = Join-Path $ConfigDirectory "entry_list.ini"

foreach ($requiredPath in @($serverExecutable, $serverConfig, $entryList)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required file not found: $requiredPath"
    }
}

Write-Host "Starting Hong Kong 1:1 Assetto Corsa server..."
& $serverExecutable "-c" $ConfigDirectory
if ($LASTEXITCODE -ne 0) {
    throw "acServer.exe exited with code $LASTEXITCODE."
}
