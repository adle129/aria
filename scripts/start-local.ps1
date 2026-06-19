# 本地开发（无需 Docker）
# Phase 0 健康检查与前端页面验证

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "==> Installing minimal backend deps (if needed)..."
pip install -q fastapi uvicorn pydantic-settings httpx python-multipart

Write-Host "==> Starting backend on http://localhost:8000 ..."
$env:PYTHONPATH = Join-Path $Root "backend"
$backendJob = Start-Job -ScriptBlock {
    param($backendPath)
    Set-Location $backendPath
    $env:PYTHONPATH = $backendPath
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
} -ArgumentList (Join-Path $Root "backend")

Write-Host "==> Starting frontend on http://localhost:3000 ..."
$env:NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000/api/v1"
Set-Location (Join-Path $Root "frontend")
if (-not (Test-Path "node_modules")) {
    npm install
}
$frontendJob = Start-Job -ScriptBlock {
    param($frontendPath, $apiBase)
    Set-Location $frontendPath
    $env:NEXT_PUBLIC_API_BASE_URL = $apiBase
    npm run dev
} -ArgumentList (Join-Path $Root "frontend"), "http://localhost:8000/api/v1"

Write-Host ""
Write-Host "ARIA local dev running:"
Write-Host "  Frontend:  http://localhost:3000"
Write-Host "  Health:    http://localhost:8000/api/v1/health"
Write-Host ""
Write-Host "Press Ctrl+C to stop."

try {
    while ($true) { Start-Sleep -Seconds 3600 }
}
finally {
    Stop-Job $backendJob, $frontendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob, $frontendJob -Force -ErrorAction SilentlyContinue
}
