# Install Ollama (if missing) and pull ARIA recommended models.
param(
    [ValidateSet("dev", "demo")]
    [string]$Profile = "dev",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "ollama_lib.ps1")

$LlmDev = "qwen2.5:7b"
$LlmDemo = "qwen2.5:14b"
$Embed = "nomic-embed-text"
$LlmModel = if ($Profile -eq "demo") { $LlmDemo } else { $LlmDev }

Write-Host ""
Write-Host "ARIA Ollama setup (profile: $Profile, LLM: $LlmModel)"
Write-Host ""

if (-not $SkipInstall) {
    $ollamaExe = Resolve-OllamaExe
    if (-not $ollamaExe) {
        Write-Host "Ollama not found. Attempting install via winget..."
        winget install Ollama.Ollama --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "winget install failed. Please install manually:"
            Write-Host "  https://ollama.com/download"
            exit 1
        }
        Write-Host ""
        Write-Host "Ollama installed. Please:"
        Write-Host "  1. Open Ollama from Start menu (wait for tray icon)"
        Write-Host "  2. Run: .\scripts\setup_ollama.ps1 -SkipInstall"
        Write-Host "  (If ollama still not found, close and reopen PowerShell)"
        exit 0
    }
}

$ollamaExe = Resolve-OllamaExe
if (-not $ollamaExe) {
    Write-Host "[FAIL] ollama.exe not found." -ForegroundColor Red
    Write-Host "Open Ollama from Start menu, then rerun with -SkipInstall"
    exit 1
}
Write-Host "Using: $ollamaExe"
Write-Host ""

Write-Host "Pulling LLM model: $LlmModel (may take several minutes)..."
Invoke-Ollama pull $LlmModel

Write-Host "Pulling embedding model: $Embed ..."
Invoke-Ollama pull $Embed

Write-Host ""
Write-Host "Done. Running check..."
& (Join-Path $ScriptDir "check_ollama.ps1") -LlmModel $LlmModel
