# ARIA one-click start — default Docker Compose (dev/prod same 5-service topology)
param(
    [switch]$Local,
    [switch]$Docker,
    [ValidateSet("dev", "prod", "cn", "dev-fast")]
    [string]$Profile = "dev",
    [switch]$Detached,
    [switch]$SkipPreflight,
    [switch]$SkipOllamaCheck,
    [switch]$BackendOnly,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ComposeArgs
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\aria-compose.ps1"
$Root = Get-AriaRoot
Set-Location $Root

if ($Local) {
    Write-Host "==> Mode: local host (pytest/dev-only, not R1 parity)" -ForegroundColor Yellow
    & "$PSScriptRoot\start-local.ps1" -SkipOllamaCheck:$SkipOllamaCheck -BackendOnly:$BackendOnly
    exit $LASTEXITCODE
}

Write-Host "==> Mode: Docker Compose (profile=$Profile)" -ForegroundColor Cyan
& "$PSScriptRoot\up.ps1" -Profile $Profile -Detached:$Detached -SkipPreflight:$SkipPreflight @ComposeArgs
exit $LASTEXITCODE
