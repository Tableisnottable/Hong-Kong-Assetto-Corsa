[CmdletBinding()]
param(
    [string] $ConfigDirectory = (Join-Path $PSScriptRoot "cfg")
)

$ErrorActionPreference = "Stop"
$serverConfig = Join-Path $ConfigDirectory "server_cfg.ini"
$entryList = Join-Path $ConfigDirectory "entry_list.ini"

foreach ($requiredPath in @($serverConfig, $entryList)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required file not found: $requiredPath"
    }
}

$configText = Get-Content -LiteralPath $serverConfig -Raw
$requiredSettings = @{
    "NAME" = "Hong Kong 1:1 Freeroam"
    "TRACK" = "hong_kong_1to1"
    "UDP_PORT" = "9600"
    "TCP_PORT" = "9600"
}

foreach ($setting in $requiredSettings.GetEnumerator()) {
    $pattern = "(?m)^\s*" + [regex]::Escape($setting.Key) + "\s*=\s*" + [regex]::Escape($setting.Value) + "\s*$"
    if ($configText -notmatch $pattern) {
        throw "Missing or incorrect setting: $($setting.Key)=$($setting.Value)"
    }
}

$carSections = ([regex]::Matches((Get-Content -LiteralPath $entryList -Raw), "(?m)^\[CAR_\d+\]")).Count
if ($carSections -lt 1) {
    throw "entry_list.ini must contain at least one [CAR_n] section."
}

Write-Host "Configuration valid: $carSections car slot(s), track hong_kong_1to1."
