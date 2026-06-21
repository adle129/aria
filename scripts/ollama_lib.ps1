# Shared helpers: resolve ollama.exe on Windows when PATH is not refreshed yet.

function Resolve-OllamaExe {
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
        "$env:ProgramFiles\Ollama\ollama.exe",
        "${env:ProgramFiles(x86)}\Ollama\ollama.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) {
            return $path
        }
    }
    return $null
}

function Invoke-Ollama {
    param(
        [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
        [string[]]$Args
    )
    $exe = Resolve-OllamaExe
    if (-not $exe) {
        throw "ollama not found. Open Ollama from Start menu, or restart PowerShell after install."
    }
    # Honor user-level OLLAMA_MODELS if set in registry but not in current shell
    if (-not $env:OLLAMA_MODELS) {
        $stored = [System.Environment]::GetEnvironmentVariable("OLLAMA_MODELS", "User")
        if ($stored) {
            $env:OLLAMA_MODELS = $stored
        }
    }
    & $exe @Args
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

function Get-OllamaModelsPath {
    if ($env:OLLAMA_MODELS) {
        return $env:OLLAMA_MODELS
    }
    $stored = [System.Environment]::GetEnvironmentVariable("OLLAMA_MODELS", "User")
    if ($stored) {
        return $stored
    }
    return Join-Path $env:USERPROFILE ".ollama\models"
}
