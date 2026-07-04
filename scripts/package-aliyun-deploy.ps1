# Package ARIA as tar.gz only (no upload). For ECS Workbench / manual scp.
# Usage: .\scripts\package-aliyun-deploy.ps1

param(
    [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $OutFile) {
    $OutFile = Join-Path $Root "aria-deploy.tar.gz"
}

$stampPath = Join-Path $Root "deploy-stamp.txt"
$rfqPage = Join-Path $Root "frontend\src\app\rfq\page.tsx"
# ASCII marker: new RFQ page calls demo sample API (not local samples/rfq path)
$marker = "demo/rfq-samples"
if (-not (Test-Path $rfqPage)) {
    Write-Error "Missing frontend/src/app/rfq/page.tsx"
}
if (-not (Select-String -Path $rfqPage -Pattern $marker -Quiet)) {
    Write-Error "RFQ page missing '$marker' - stale tree, abort packaging"
}

$stamp = "packaged_at=$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ss')`nrfq_ui_marker=$marker"
[System.IO.File]::WriteAllText($stampPath, $stamp)

Write-Host "==> Packaging to $OutFile"
tar -czf $OutFile `
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

$mb = [math]::Round((Get-Item $OutFile).Length / 1MB, 2)
Write-Host "==> Done ($mb MB)"
Write-Host ""
Write-Host "Upload aria-deploy.tar.gz to ECS /tmp/ then on ECS:"
Write-Host "  sudo tar -xzf /tmp/aria-deploy.tar.gz -C /opt/aria"
Write-Host "  cd /opt/aria && sudo bash scripts/deploy-aliyun-demo.sh"
Write-Host ""
Write-Host "Verify tarball on ECS (note ./ path prefix):"
Write-Host "  tar -tzf /tmp/aria-deploy.tar.gz | grep deploy-stamp.txt"
Write-Host "  tar -xzf /tmp/aria-deploy.tar.gz -O ./frontend/src/app/rfq/page.tsx | grep demo/rfq-samples"
