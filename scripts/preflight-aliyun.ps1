# Pre-flight checks: HTTP port 80 + SSH port 22
# Usage: .\scripts\preflight-aliyun.ps1 -TargetHost <public-ip> -KeyPath C:\path\to\key.pem

param(
    [Parameter(Mandatory = $true)]
    [string]$TargetHost,
    [string]$KeyPath = "",
    [string]$User = "root",
    [int]$HttpPort = 80,
    [switch]$HttpOnly
)

$ErrorActionPreference = "Continue"
$SshOpts = @("-o", "ConnectTimeout=15", "-o", "StrictHostKeyChecking=accept-new")
if ($KeyPath) {
    if (-not (Test-Path $KeyPath)) {
        Write-Host "FAIL: Key file not found: $KeyPath" -ForegroundColor Red
        exit 1
    }
    $SshOpts += @("-i", $KeyPath)
}

Write-Host "==> [1/2] HTTP  http://${TargetHost}:${HttpPort}/"
try {
    $html = (Invoke-WebRequest -Uri "http://${TargetHost}:${HttpPort}/" -TimeoutSec 10 -UseBasicParsing).Content
    if ($html -match "ARIA") {
        Write-Host "OK: Page contains ARIA (may already be deployed)" -ForegroundColor Green
    } elseif ($html -match "8D") {
        Write-Host "WARN: Port ${HttpPort} serves another app (8D platform), not ARIA" -ForegroundColor Yellow
        Write-Host "      Try another port or stop the conflicting service" -ForegroundColor Yellow
    } else {
        Write-Host "WARN: Port ${HttpPort} responds but site is not recognized as ARIA" -ForegroundColor Yellow
    }
} catch {
    Write-Host "INFO: HTTP unreachable - $($_.Exception.Message)" -ForegroundColor Gray
}

try {
    $health = Invoke-RestMethod -Uri "http://${TargetHost}:${HttpPort}/api/v1/health" -TimeoutSec 10
    if ($health.status -eq "ok") {
        Write-Host "OK: ARIA health - mock_llm=$($health.mock_llm) mock_rag=$($health.mock_rag)" -ForegroundColor Green
    }
} catch {
    Write-Host "INFO: /api/v1/health is not ARIA or not ready yet" -ForegroundColor Gray
}

if ($HttpOnly) {
    exit 0
}

Write-Host "==> [2/2] SSH   ${User}@${TargetHost}:22"
$sshTest = & ssh @SshOpts -o BatchMode=yes "${User}@${TargetHost}" "echo ssh_ok" 2>&1
if ($LASTEXITCODE -eq 0 -and ($sshTest -match "ssh_ok")) {
    Write-Host "OK: SSH login works" -ForegroundColor Green
    exit 0
}

Write-Host "FAIL: SSH unreachable" -ForegroundColor Red
if ($sshTest) { Write-Host "      $sshTest" -ForegroundColor Red }
Write-Host "Check in Aliyun console:" -ForegroundColor Yellow
Write-Host "  - Instance is Running" -ForegroundColor Yellow
Write-Host "  - Security group: inbound 22/TCP (your IP), 80/TCP (demo access)" -ForegroundColor Yellow
Write-Host "  - Public IP / EIP attached" -ForegroundColor Yellow
Write-Host "  - Key pair matches instance; .pem path is correct on Windows" -ForegroundColor Yellow
Write-Host "If SSH stays blocked, use ECS Workbench + manual deploy (docs/aliyun-demo-deploy.md, method B)" -ForegroundColor Yellow
exit 1
