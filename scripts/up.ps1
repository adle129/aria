# One-click dev: bootstrap .env (if missing) + docker compose up --build
param(
    [switch]$Cn,
    [switch]$DevFast,
    [switch]$Detached,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ComposeArgs
)

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

& "$Root\scripts\ensure-env.ps1" -Profile dev

$ComposeFile = "docker-compose.yml"
if ($Cn) { $ComposeFile = "docker-compose.cn.yml" }
if ($DevFast) { $ComposeFile = "docker-compose.dev.yml" }

$Args = @("-f", $ComposeFile, "up", "--build")
if ($Detached) { $Args += "-d" }
if ($ComposeArgs) { $Args += $ComposeArgs }

if (-not $Cn -and -not $DevFast) {
    Write-Host "Tip: If pip/npm downloads fail during build, use -Cn for China mirrors." -ForegroundColor DarkYellow
}

Write-Host "==> docker compose $($Args -join ' ')"
docker compose @Args
