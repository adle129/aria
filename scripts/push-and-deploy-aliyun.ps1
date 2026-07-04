# Push ARIA from Windows to Aliyun ECS and run remote deploy
# Usage:
#   .\scripts\preflight-aliyun.ps1 -TargetHost <IP> -KeyPath C:\path\to\key.pem
#   .\scripts\push-and-deploy-aliyun.ps1 -TargetHost <IP> -KeyPath C:\path\to\key.pem
#
# Prereq: security group allows 22 and 80; SSH login works

param(
    [Parameter(Mandatory = $true)]
    [string]$TargetHost,
    [string]$User = "root",
    [string]$KeyPath = "",
    [string]$RemoteDir = "/opt/aria",
    [int]$HttpPort = 0,
    [switch]$SkipPreflight
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if ($KeyPath -and -not (Test-Path $KeyPath)) {
    Write-Error "Key file not found: $KeyPath`nExample: C:\Users\<you>\Downloads\key.pem"
}

$SshOpts = @("-o", "ConnectTimeout=20", "-o", "StrictHostKeyChecking=accept-new")
if ($KeyPath) {
    $SshOpts += @("-i", $KeyPath)
}

$Target = "${User}@${TargetHost}"
$Archive = Join-Path $env:TEMP "aria-deploy.tar.gz"

if (-not $SkipPreflight) {
    Write-Host "==> Pre-flight checks..."
    $preflightPort = if ($HttpPort -gt 0) { $HttpPort } else { 8080 }
    & "$PSScriptRoot/preflight-aliyun.ps1" -TargetHost $TargetHost -KeyPath $KeyPath -User $User -HttpPort $preflightPort
    if ($LASTEXITCODE -ne 0) {
        Write-Error @"
SSH pre-flight failed. Fix security group / key, or use manual deploy:
  .\scripts\package-aliyun-deploy.ps1
  See docs/aliyun-demo-deploy.md (method B)
"@
    }
}

Write-Host "==> Packaging project..."
if (Get-Command tar -ErrorAction SilentlyContinue) {
    tar -czf $Archive `
        --exclude=node_modules `
        --exclude=.git `
        --exclude=.next `
        --exclude=__pycache__ `
        --exclude=.venv `
        --exclude=backend/data/chroma_db `
        --exclude=backend/data/uploads `
        --exclude=backend/data/outputs `
        --exclude=aria-deploy.tar.gz `
        -C $Root .
} else {
    Write-Error "tar is required (included in Windows 10+)."
}

Write-Host "==> Uploading to ${Target}:${RemoteDir} ..."
ssh @SshOpts $Target "mkdir -p $RemoteDir"
scp @SshOpts $Archive "${Target}:/tmp/aria-deploy.tar.gz"
ssh @SshOpts $Target "tar -xzf /tmp/aria-deploy.tar.gz -C $RemoteDir && rm -f /tmp/aria-deploy.tar.gz"

Write-Host "==> Running deploy-aliyun-demo.sh on remote host..."
ssh @SshOpts $Target "chmod +x $RemoteDir/scripts/deploy-aliyun-demo.sh && ARIA_ROOT=$RemoteDir bash $RemoteDir/scripts/deploy-aliyun-demo.sh"

Write-Host ""
Write-Host "==> Done. Verify:" -ForegroundColor Green
if ($HttpPort -gt 0) {
    Write-Host "  Browser:  http://${TargetHost}:${HttpPort}/"
    Write-Host "  Health:   http://${TargetHost}:${HttpPort}/api/v1/health"
} else {
    Write-Host "  Browser:  http://${TargetHost}:<ARIA_DEMO_HTTP_PORT>/  (see .env on ECS, default 8080 in example)"
    Write-Host "  Health:   http://${TargetHost}:<port>/api/v1/health"
}
Write-Host "  Rehearsal: docs/demo-rehearsal-guide.md"
