# One-click Docker: preflight + compose up --build (+ health verify when detached)
param(
    [ValidateSet("dev", "prod", "cn", "dev-fast")]
    [string]$Profile = "dev",
    [switch]$Cn,
    [switch]$DevFast,
    [switch]$Detached,
    [switch]$SkipPreflight,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ComposeArgs
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\aria-compose.ps1"
$Root = Get-AriaRoot
Set-Location $Root

if ($Cn) { $Profile = "cn" }
if ($DevFast) { $Profile = "dev-fast" }

if ($Profile -eq "prod") {
    & "$Root\scripts\ensure-env.ps1" -Profile prod | Out-Null
}
else {
    & "$Root\scripts\ensure-env.ps1" -Profile dev | Out-Null
}
Initialize-AriaEnv

$ComposeFile = Get-AriaComposeFile -Profile $Profile

if (-not $SkipPreflight) {
    Test-AriaDockerReady
    if ($Profile -ne "dev-fast") {
        Invoke-AriaOllamaPreflight -Root $Root
    }
}

# Prefer local base images (node/python). DaoCloud mirror often EOF on manifest HEAD.
# Pre-pull when missing: .\scripts\pull-images-cn.ps1
$Args = @("-f", $ComposeFile, "up", "--build", "--pull", "never")
if ($Detached) { $Args += "-d" }
if ($ComposeArgs) { $Args += $ComposeArgs }

if ($Profile -eq "dev-fast") {
    Write-Host "WARN: dev-fast stack lacks pgvector/worker — not for R1 testing." -ForegroundColor Yellow
}
elseif ($Profile -ne "cn") {
    Write-Host "Tip: pip/npm slow? use -Profile cn" -ForegroundColor DarkYellow
}

Write-Host "==> docker compose $($Args -join ' ')"
docker compose @Args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($Detached -and $Profile -ne "dev-fast") {
    Write-Host "==> Waiting for stack health..."
    Wait-AriaComposeHealthy -ComposeFile $ComposeFile
    Write-Host ""
    Write-Host "ARIA started:" -ForegroundColor Green
    Write-Host "  App:    http://localhost"
    Write-Host "  Health: http://localhost/api/v1/health"
    Write-Host "  Logs:   docker compose -f $ComposeFile logs -f backend worker"
    if ($Profile -eq "prod") {
        Write-Host "  First login: python deploy/scripts/create_admin.py (if not done)"
    }
}
