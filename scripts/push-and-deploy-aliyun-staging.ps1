# Push ARIA R1 staging from Windows to Aliyun GPU ECS and run remote deploy
# Usage:
#   .\scripts\preflight-aliyun.ps1 -TargetHost <IP> -KeyPath C:\path\to\key.pem -User ecs-user -HttpPort 80
#   .\scripts\push-and-deploy-aliyun-staging.ps1 -TargetHost <IP> -KeyPath C:\path\to\key.pem
#
# Prereq: security group allows 22 and 80; GPU ECS; data disk at /data

param(
    [Parameter(Mandatory = $true)]
    [string]$TargetHost,
    [string]$User = "ecs-user",
    [string]$KeyPath = "",
    [string]$RemoteDir = "/opt/aria",
    [int]$HttpPort = 80,
    [switch]$SkipPreflight,
    [switch]$SkipModelPull
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if ($KeyPath -and -not (Test-Path $KeyPath)) {
    Write-Error "Key file not found: $KeyPath`nExample: C:\Users\<you>\Downloads\nancy-test-llm.pem"
}

$SshOpts = @("-o", "ConnectTimeout=20", "-o", "StrictHostKeyChecking=accept-new")
if ($KeyPath) {
    $SshOpts += @("-i", $KeyPath)
}

$Target = "${User}@${TargetHost}"
$Archive = Join-Path $env:TEMP "aria-staging.tar.gz"

if (-not $SkipPreflight) {
    Write-Host "==> Pre-flight checks..."
    & "$PSScriptRoot/preflight-aliyun.ps1" -TargetHost $TargetHost -KeyPath $KeyPath -User $User -HttpPort $HttpPort
    if ($LASTEXITCODE -ne 0) {
        Write-Error @"
SSH pre-flight failed. Fix security group / key, or use manual deploy:
  .\scripts\package-aliyun-staging.ps1
  See docs/aliyun-staging-deploy.md
"@
    }
}

Write-Host "==> Packaging R1 staging..."
& "$PSScriptRoot/package-aliyun-staging.ps1" -OutFile $Archive
if ($LASTEXITCODE -ne 0) {
    Write-Error "package-aliyun-staging.ps1 failed"
}

Write-Host "==> Uploading to ${Target}:${RemoteDir} ..."
ssh @SshOpts $Target "mkdir -p $RemoteDir"
scp @SshOpts $Archive "${Target}:/tmp/aria-staging.tar.gz"
ssh @SshOpts $Target "tar -xzf /tmp/aria-staging.tar.gz -C $RemoteDir && rm -f /tmp/aria-staging.tar.gz"

$skipEnv = if ($SkipModelPull) { "SKIP_MODEL_PULL=true" } else { "SKIP_MODEL_PULL=false" }
Write-Host "==> Running deploy-aliyun-staging.sh on remote host..."
Write-Host "    (first run may take 20–60 min: model pull + docker build)"
ssh @SshOpts $Target "chmod +x $RemoteDir/scripts/deploy-aliyun-staging.sh $RemoteDir/scripts/verify-staging-deploy.sh $RemoteDir/deploy/scripts/start.sh && ARIA_ROOT=$RemoteDir $skipEnv bash $RemoteDir/scripts/deploy-aliyun-staging.sh"

Write-Host ""
Write-Host "==> Done. Verify:" -ForegroundColor Green
Write-Host "  Browser:  http://${TargetHost}/"
Write-Host "  Health:   http://${TargetHost}/api/v1/health  (check deploy_sha)"
Write-Host "  Remote:   ssh ... 'cd $RemoteDir && bash scripts/verify-staging-deploy.sh'"
Write-Host "  Docs:     docs/aliyun-staging-deploy.md"
