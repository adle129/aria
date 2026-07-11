# Package ARIA R1 staging tarball (no upload). For ECS Workbench / manual scp.
# Usage: .\scripts\package-aliyun-staging.ps1
#        .\scripts\package-aliyun-staging.ps1 -OutFile e:\tmp\aria-staging.tar.gz

param(
    [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $OutFile) {
    $OutFile = Join-Path $Root "aria-staging.tar.gz"
}

$required = @(
    "docker-compose.aliyun-staging.yml",
    ".env.aliyun-staging.example",
    "scripts\deploy-aliyun-staging.sh",
    "deploy\scripts\start.sh",
    "frontend\src\app\rfq\page.tsx"
)
foreach ($rel in $required) {
    $p = Join-Path $Root $rel
    if (-not (Test-Path $p)) {
        Write-Error "Missing required file: $rel"
    }
}

$stampPath = Join-Path $Root "deploy-stamp.txt"
$stamp = @"
packaged_at=$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ss')
profile=aliyun-staging
compose=docker-compose.aliyun-staging.yml
"@
[System.IO.File]::WriteAllText($stampPath, $stamp)

Write-Host "==> Packaging R1 staging to $OutFile"
tar -czf $OutFile `
    --exclude=node_modules `
    --exclude=.git `
    --exclude=.next `
    --exclude=__pycache__ `
    --exclude=.venv `
    --exclude=backend/data/chroma_db `
    --exclude=backend/data/uploads `
    --exclude=backend/data/outputs `
    --exclude=backend/data/aria_local.db `
    --exclude=aria-deploy.tar.gz `
    --exclude=aria-staging.tar.gz `
    -C $Root .

$mb = [math]::Round((Get-Item $OutFile).Length / 1MB, 2)
Write-Host "==> Done ($mb MB)"
Write-Host ""
Write-Host "Upload aria-staging.tar.gz to ECS /tmp/ then on ECS:"
Write-Host "  sudo mkdir -p /opt/aria"
Write-Host "  sudo tar -xzf /tmp/aria-staging.tar.gz -C /opt/aria"
Write-Host "  cd /opt/aria && bash scripts/deploy-aliyun-staging.sh"
Write-Host ""
Write-Host "Verify tarball:"
Write-Host "  tar -tzf /tmp/aria-staging.tar.gz | grep deploy-stamp.txt"
Write-Host "  tar -tzf /tmp/aria-staging.tar.gz | grep docker-compose.aliyun-staging.yml"
