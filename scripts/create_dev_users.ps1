param(
    [string]$EngineerUser = "engineer",
    [string]$EngineerPassword = "engineer123",
    [string]$AdminUser = "kbadmin",
    [string]$AdminPassword = "admin123"
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\aria-compose.ps1"
$Root = Get-AriaRoot
$Backend = Join-Path $Root "backend"
Initialize-AriaEnv -LocalHostPaths

if ($env:AUTH_ENABLED -ne "true") {
    Write-Host "AUTH_ENABLED is not true - skip user creation."
    exit 0
}

$env:PYTHONPATH = $Backend
Push-Location $Backend
try {
    python scripts/create_admin.py --username $EngineerUser --password $EngineerPassword --display-name "Quote Engineer" --role quote_engineer
    python scripts/create_admin.py --username $AdminUser --password $AdminPassword --display-name "KB Admin" --role kb_admin
}
finally {
    Pop-Location
}
Write-Host "Dev users ready: $EngineerUser (engineer) / $AdminUser (kb_admin)"
