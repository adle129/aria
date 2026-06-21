# Move Ollama model storage to another drive (e.g. D:) to save C: space.
param(
    [string]$ModelsPath = "D:\ollama\models",
    [switch]$MigrateExisting,
    [switch]$MachineScope
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "ollama_lib.ps1")

$DefaultModels = Join-Path $env:USERPROFILE ".ollama\models"
$drive = Split-Path $ModelsPath -Qualifier
if ($drive -and -not (Test-Path $drive)) {
    Write-Host "[FAIL] Drive not found: $drive" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "ARIA — Configure Ollama model path"
Write-Host "  Target: $ModelsPath"
Write-Host ""

# 1. Create target directory
New-Item -ItemType Directory -Force -Path $ModelsPath | Out-Null

# 2. Optional migrate from C:\Users\<you>\.ollama\models
if ($MigrateExisting -and (Test-Path $DefaultModels)) {
    $items = Get-ChildItem $DefaultModels -Force -ErrorAction SilentlyContinue
    if ($items) {
        Write-Host "Migrating existing models from $DefaultModels ..."
        Write-Host "(This may take several minutes for large models)"
        robocopy $DefaultModels $ModelsPath /E /MOVE /R:1 /W:1 /NFL /NDL /NJH /NJS | Out-Null
        if ($LASTEXITCODE -ge 8) {
            Write-Host "[WARN] robocopy exit code $LASTEXITCODE — verify files in $ModelsPath" -ForegroundColor Yellow
        } else {
            Write-Host "[OK]   Migration finished" -ForegroundColor Green
        }
    } else {
        Write-Host "[SKIP] Default models folder is empty"
    }
}

# 3. Persist environment variable (User or Machine)
$scope = if ($MachineScope) { "Machine" } else { "User" }
[Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $ModelsPath, $scope)
$env:OLLAMA_MODELS = $ModelsPath

Write-Host "[OK]   OLLAMA_MODELS set ($scope scope): $ModelsPath" -ForegroundColor Green

Write-Host ""
Write-Host "IMPORTANT — restart Ollama for the change to take effect:"
Write-Host "  1. Right-click Ollama tray icon -> Quit"
Write-Host "  2. Start Ollama from Start menu again"
Write-Host "  3. Close and reopen PowerShell (refresh env)"
Write-Host ""
Write-Host "Then pull or verify models:"
Write-Host "  .\scripts\setup_ollama.ps1 -SkipInstall"
Write-Host "  .\scripts\check_ollama.ps1"
Write-Host ""
Write-Host "Default C: location (before move): $DefaultModels"
Write-Host "Ollama program stays on C:; only model files use D:."
Write-Host ""
