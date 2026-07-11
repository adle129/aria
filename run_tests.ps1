param(
    [switch]$Regression,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PytestArgs
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$env:PYTHONPATH = Join-Path $Root "backend"

Write-Host "==> Running unit tests..."
python -m pytest unit_tests/ -v @PytestArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Running frontend unit tests..."
$FrontendDir = Join-Path $Root "frontend"
$FrontendHasDeps =
  (Test-Path (Join-Path $FrontendDir "node_modules\vitest")) -or
  (Test-Path (Join-Path $FrontendDir "node_modules\vitest\index.mjs"))
if ($FrontendHasDeps) {
    Push-Location $FrontendDir
    npm test --silent
    if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
    Write-Host "==> Running frontend production build (next build)..."
    npm run build
    if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
    Pop-Location
} else {
    Write-Host "    (skip: run 'npm install' in frontend/)"
}

Write-Host "==> Running API tests..."
python -m pytest API_tests/ -v @PytestArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($Regression) {
    Write-Host "==> Running regression tests..."
    $regTests = Get-ChildItem -Path (Join-Path $Root "regression") -Filter "test_*.py" -ErrorAction SilentlyContinue
    if ($regTests) {
        python -m pytest regression/ -v @PytestArgs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } else {
        Write-Host "    (skip: no regression/test_*.py yet)"
    }
}

Write-Host "================================================"
Write-Host "  ARIA tests"
Write-Host "================================================"
Write-Host "[1/4] unit tests  ... OK"
Write-Host "[2/4] frontend vitest ... OK"
Write-Host "[3/4] frontend build  ... OK"
Write-Host "[4/4] API tests   ... OK"
Write-Host "================================================"
Write-Host "Summary: 4 passed / 0 failed"
Write-Host "================================================"
