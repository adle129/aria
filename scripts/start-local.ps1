# Local dev without Docker: backend + worker + frontend (loads .env)
param(
    [switch]$SkipOllamaCheck,
    [switch]$BackendOnly
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\aria-compose.ps1"
$Root = Get-AriaRoot
Set-Location $Root

Initialize-AriaEnv -LocalHostPaths
$BackendPath = Join-Path $Root "backend"
$FrontendPath = Join-Path $Root "frontend"

@(
    (Join-Path $Root "backend\data\uploads"),
    (Join-Path $Root "backend\data\outputs"),
    (Join-Path $Root "backend\data\knowledge_base"),
    (Join-Path $Root "backend\data\templates"),
    (Join-Path $Root "backend\data\app\feedback")
) | ForEach-Object {
    New-Item -ItemType Directory -Force -Path $_ | Out-Null
}

Write-Host "==> DB init..."
Invoke-AriaDbInit -BackendPath $BackendPath

if ($env:MOCK_LLM -eq "false" -and -not $SkipOllamaCheck) {
    Write-Host "==> Ollama check (MOCK_LLM=false)..."
    & "$Root\scripts\check_ollama.ps1" -OllamaUrl $env:OLLAMA_BASE_URL -LlmModel $env:OLLAMA_MODEL
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Ollama not ready. Fix or set MOCK_LLM=true in .env"
    }
}

Write-Host "==> Starting backend http://localhost:8000 ..."
$backend = Start-Process -FilePath "python" `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000") `
    -WorkingDirectory $BackendPath -PassThru -WindowStyle Hidden

$worker = $null
if ($env:TASK_WORKER_INLINE -ne "true") {
    Write-Host "==> Starting worker (TASK_WORKER_INLINE=false)..."
    $worker = Start-Process -FilePath "python" `
        -ArgumentList @("-m", "app.worker") `
        -WorkingDirectory $BackendPath -PassThru -WindowStyle Hidden
}

$frontend = $null
if (-not $BackendOnly) {
    if (-not (Test-Path (Join-Path $FrontendPath "node_modules"))) {
        Write-Host "==> npm install (first run)..."
        Push-Location $FrontendPath
        npm install
        Pop-Location
    }
    Write-Host "==> Starting frontend http://localhost:3000 ..."
    $frontend = Start-Process -FilePath "cmd.exe" `
        -ArgumentList @("/c", "npm run dev") `
        -WorkingDirectory $FrontendPath -PassThru -WindowStyle Hidden
}

Write-Host ""
Write-Host "ARIA local dev running:"
Write-Host "  Frontend:  http://localhost:3000"
Write-Host "  Backend:   http://localhost:8000"
Write-Host "  Health:    http://localhost:8000/api/v1/health"
if ($worker) { Write-Host "  Worker:    background (python -m app.worker)" }
Write-Host ""
Write-Host "Press Ctrl+C to stop all processes."

try {
    while ($true) {
        foreach ($proc in @($backend, $worker, $frontend) | Where-Object { $_ }) {
            if ($proc.HasExited) {
                throw "Process $($proc.Id) exited with code $($proc.ExitCode)"
            }
        }
        Start-Sleep -Seconds 2
    }
}
finally {
    foreach ($proc in @($frontend, $worker, $backend) | Where-Object { $_ -and -not $_.HasExited }) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
}
