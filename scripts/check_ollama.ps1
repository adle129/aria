# Verify Ollama install, models, and ARIA backend connectivity.
param(
    [string]$OllamaUrl = "http://localhost:11434",
    [string]$LlmModel = "qwen2.5:7b",
    [string]$EmbedModel = "nomic-embed-text"
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$env:PYTHONPATH = Join-Path $ProjectRoot "backend"
. (Join-Path $ScriptDir "ollama_lib.ps1")

Write-Host ""
Write-Host "================================================"
Write-Host "  ARIA - Ollama Environment Check"
Write-Host "================================================"
Write-Host ""

# 1. CLI
$ollamaExe = Resolve-OllamaExe
if (-not $ollamaExe) {
    Write-Host "[FAIL] ollama command not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install steps (Windows):"
    Write-Host "  1. Download: https://ollama.com/download"
    Write-Host "  2. Or run:    winget install Ollama.Ollama"
    Write-Host "  3. Open Ollama from Start menu, then run: .\scripts\setup_ollama.ps1 -SkipInstall"
    Write-Host "  4. Or restart PowerShell if PATH was not refreshed"
    Write-Host ""
    exit 1
}
Write-Host "[OK]   ollama CLI: $ollamaExe" -ForegroundColor Green
$modelsPath = Get-OllamaModelsPath
Write-Host "[INFO] Model storage: $modelsPath"

# 2. Service
try {
    $tags = Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -TimeoutSec 5
    Write-Host "[OK]   Ollama API: $OllamaUrl" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Ollama API not reachable at $OllamaUrl" -ForegroundColor Red
    Write-Host "       Start Ollama app from Start menu, then retry."
    Write-Host "       Error: $($_.Exception.Message)"
    exit 1
}

# 3. Models
$names = @($tags.models | ForEach-Object { $_.name })
Write-Host ""
Write-Host "Installed models:"
if ($names.Count -eq 0) {
    Write-Host "  (none) - run .\scripts\setup_ollama.ps1 to pull models"
} else {
    $names | ForEach-Object { Write-Host "  - $_" }
}

function Test-ModelPresent($target) {
    $base = $target.Split(":")[0]
    return $names | Where-Object { $_ -eq $target -or $_.StartsWith("${base}:") }
}

Write-Host ""
if (Test-ModelPresent $LlmModel) {
    Write-Host "[OK]   LLM model ready: $LlmModel" -ForegroundColor Green
} else {
    Write-Host "[WARN] LLM model missing: $LlmModel" -ForegroundColor Yellow
    Write-Host "       Run: .\scripts\setup_ollama.ps1 -SkipInstall"
}

if (Test-ModelPresent $EmbedModel) {
    Write-Host "[OK]   Embedding model ready: $EmbedModel" -ForegroundColor Green
} else {
    Write-Host "[WARN] Embedding model missing: $EmbedModel (needed when MOCK_RAG=false)" -ForegroundColor Yellow
    Write-Host "       Run: .\scripts\setup_ollama.ps1 -SkipInstall"
}

# 4. Python probe (same as /health)
Write-Host ""
Write-Host "Backend probe (ollama_service):"
python -c @"
from app.services.ollama_service import probe_ollama
r = probe_ollama('$OllamaUrl', '$LlmModel', '$EmbedModel')
print('  reachable:', r['ollama_reachable'])
print('  llm ready:', r['ollama_model_ready'])
print('  embed ready:', r['embedding_model_ready'])
if r.get('ollama_error'):
    print('  error:', r['ollama_error'])
"@

Write-Host ""
Write-Host "Next steps to enable real LLM in ARIA:"
Write-Host "  Docker:  set in .env -> MOCK_LLM=false, OLLAMA_BASE_URL=http://host.docker.internal:11434"
Write-Host "  Local:   copy .env.local.example -> .env, MOCK_LLM=false"
Write-Host "  Then:    docker compose restart backend"
Write-Host "================================================"
