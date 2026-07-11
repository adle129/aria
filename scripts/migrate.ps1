# SQLite/pytest only. Docker stacks run alembic via backend entrypoint.
param(
    [switch]$Docker,
    [ValidateSet("dev", "prod", "cn", "dev-fast")]
    [string]$Profile = "dev"
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\aria-compose.ps1"
$Root = Get-AriaRoot
Set-Location $Root

if ($Docker) {
    Write-Host "Docker migrate runs automatically in backend entrypoint on startup."
    Write-Host "To rebuild stack: .\scripts\up.ps1 -Profile $Profile -Detached"
    exit 0
}

Initialize-AriaEnv
$dbUrl = $env:DATABASE_URL
if ($dbUrl -match "^sqlite") {
    Write-Host "SQLite: skip alembic; init_db() on backend startup."
    Invoke-AriaDbInit -BackendPath (Join-Path $Root "backend")
    exit 0
}

Write-Host "==> alembic upgrade head (host)"
Push-Location (Join-Path $Root "backend")
$env:PYTHONPATH = (Join-Path $Root "backend")
try {
    alembic upgrade head
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}
