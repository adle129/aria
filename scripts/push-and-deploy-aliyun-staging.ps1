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
    [switch]$SkipModelPull,
    [switch]$SkipPublicHealthCheck
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Assert-NativeSuccess {
    param([string]$Step)
    if ($LASTEXITCODE -ne 0) {
        Write-Error "$Step failed (exit $LASTEXITCODE)"
    }
}

if ($KeyPath -and -not (Test-Path $KeyPath)) {
    Write-Error "Key file not found: $KeyPath`nExample: C:\Users\<you>\Downloads\nancy-test-llm.pem"
}

$SshOpts = @("-o", "ConnectTimeout=20", "-o", "StrictHostKeyChecking=accept-new")
if ($KeyPath) {
    $SshOpts += @("-i", $KeyPath)
}

$Target = "${User}@${TargetHost}"
$Archive = Join-Path $env:TEMP "aria-staging.tar.gz"
$HealthUrl = "http://${TargetHost}:${HttpPort}/api/v1/health"

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

$ExpectedSha = $null
$stampPath = Join-Path $Root "deploy-stamp.txt"
if (Test-Path $stampPath) {
    foreach ($line in Get-Content $stampPath) {
        if ($line -match '^deploy_sha=(.+)$') {
            $ExpectedSha = $Matches[1].Trim()
        }
    }
}

Write-Host "==> Preparing remote dir ${RemoteDir} ..."
ssh @SshOpts $Target "sudo mkdir -p $RemoteDir && sudo chown ${User}:${User} $RemoteDir"
Assert-NativeSuccess "Remote mkdir $RemoteDir"

Write-Host "==> Uploading to ${Target}:${RemoteDir} ..."
scp @SshOpts $Archive "${Target}:/tmp/aria-staging.tar.gz"
Assert-NativeSuccess "scp aria-staging.tar.gz"
ssh @SshOpts $Target "tar -xzf /tmp/aria-staging.tar.gz -C $RemoteDir && rm -f /tmp/aria-staging.tar.gz"
Assert-NativeSuccess "Remote extract tarball"

$skipEnv = if ($SkipModelPull) { "SKIP_MODEL_PULL=true" } else { "SKIP_MODEL_PULL=false" }
Write-Host "==> Running deploy-aliyun-staging.sh on remote host..."
Write-Host "    (first run may take 20–60 min: model pull + docker build)"
Write-Host "    Remote deploy includes verify-staging-deploy.sh (containers + /health)."
ssh @SshOpts $Target "chmod +x $RemoteDir/scripts/deploy-aliyun-staging.sh $RemoteDir/scripts/verify-staging-deploy.sh $RemoteDir/deploy/scripts/start.sh && ARIA_ROOT=$RemoteDir $skipEnv bash $RemoteDir/scripts/deploy-aliyun-staging.sh"
Assert-NativeSuccess "Remote deploy-aliyun-staging.sh"

if (-not $SkipPublicHealthCheck) {
    Write-Host "==> Public health-check: $HealthUrl"
    $health = $null
    $lastErr = $null
    for ($i = 1; $i -le 15; $i++) {
        try {
            $health = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 10
            break
        } catch {
            $lastErr = $_.Exception.Message
            Write-Host "    attempt $i/15 not ready: $lastErr"
            Start-Sleep -Seconds 2
        }
    }
    if (-not $health) {
        Write-Error "Public health unreachable: $HealthUrl ($lastErr)"
    }

    Write-Host "    status=$($health.status) deploy_sha=$($health.deploy_sha)"
    Write-Host "    mock_llm=$($health.mock_llm) mock_rag=$($health.mock_rag)"
    Write-Host "    ollama_reachable=$($health.ollama_reachable) model_ready=$($health.ollama_model_ready) embed_ready=$($health.embedding_model_ready)"

    if ($health.status -ne "ok") {
        Write-Error "Health status='$($health.status)' (expected ok)"
    }
    if ($ExpectedSha -and $health.deploy_sha -ne $ExpectedSha) {
        Write-Error "Health deploy_sha='$($health.deploy_sha)' != package stamp '$ExpectedSha'"
    }
    if ($health.mock_llm -ne $false) {
        Write-Error "Staging requires mock_llm=false (got $($health.mock_llm))"
    }
    if ($health.mock_rag -ne $false) {
        Write-Error "Staging requires mock_rag=false (got $($health.mock_rag))"
    }
    if ($health.ollama_reachable -ne $true) {
        Write-Error "Staging requires ollama_reachable=true (got $($health.ollama_reachable))"
    }
    if ($health.ollama_model_ready -ne $true) {
        Write-Error "Staging requires ollama_model_ready=true (got $($health.ollama_model_ready))"
    }
    if ($health.embedding_model_ready -ne $true) {
        Write-Error "Staging requires embedding_model_ready=true (got $($health.embedding_model_ready))"
    }
    if ($health.aria_ui_profile -ne "r1") {
        Write-Error "Staging requires aria_ui_profile=r1 (got $($health.aria_ui_profile)); local .env may have been packaged"
    }
    if ($health.kb_debug_enabled -ne $false) {
        Write-Error "Staging requires kb_debug_enabled=false (got $($health.kb_debug_enabled))"
    }
    Write-Host "==> Public health-check OK" -ForegroundColor Green
}

Write-Host ""
Write-Host "==> Deploy + health-check passed." -ForegroundColor Green
Write-Host "  Browser:  http://${TargetHost}/"
Write-Host "  Health:   $HealthUrl"
Write-Host "  Remote:   ssh ... 'cd $RemoteDir && bash scripts/verify-staging-deploy.sh'"
Write-Host "  Docs:     docs/aliyun-staging-deploy.md"
