$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$env:PYTHONPATH = Join-Path $Root "backend"

Write-Host "==> Running unit tests..."
python -m pytest unit_tests/ -v @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Running API tests..."
python -m pytest API_tests/ -v @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "================================================"
Write-Host "  ARIA 测试执行"
Write-Host "================================================"
Write-Host "【1/2】单元测试 ... ✅ 全部通过"
Write-Host "【2/2】API 测试  ... ✅ 全部通过"
Write-Host "================================================"
Write-Host "测试汇总：2 组通过 / 0 组失败"
Write-Host "================================================"
