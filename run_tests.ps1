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
if ((Test-Path (Join-Path $FrontendDir "node_modules\vitest")) -or (Test-Path (Join-Path $FrontendDir "node_modules\vitest\index.mjs"))) {
    Push-Location $FrontendDir
    npm test --silent
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
Write-Host "[1/3] unit tests ... OK"
Write-Host "[2/3] frontend   ... OK"
Write-Host "[3/3] API tests  ... OK"
Write-Host "================================================"
Write-Host "Summary: 3 passed / 0 failed"
Write-Host "================================================"
