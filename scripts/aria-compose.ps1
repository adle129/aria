function Get-AriaRoot {
    $scriptsDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
    return (Resolve-Path (Join-Path $scriptsDir "..")).Path
}

function Get-AriaComposeFile {
    param(
        [ValidateSet("dev", "prod", "cn", "dev-fast")]
        [string]$Profile = "dev"
    )
    switch ($Profile) {
        "prod" { return "docker-compose.prod.yml" }
        "cn" { return "docker-compose.cn.yml" }
        "dev-fast" { return "docker-compose.dev.yml" }
        default { return "docker-compose.yml" }
    }
}

function Import-AriaDotEnv {
    param([string]$EnvFile)
    if (-not (Test-Path $EnvFile)) { return $false }
    Get-Content $EnvFile -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { return }
        $name = $line.Substring(0, $eq).Trim()
        $value = $line.Substring($eq + 1).Trim()
        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        elseif ($value -match '#') {
            $value = ($value -split '#', 2)[0].Trim()
        }
        Set-Item -Path "env:$name" -Value $value
    }
    return $true
}

function Initialize-AriaEnv {
    param(
        [string]$Root = (Get-AriaRoot),
        [switch]$LocalHostPaths
    )
    $envFile = Join-Path $Root ".env"
    if (-not (Import-AriaDotEnv $envFile)) {
        & (Join-Path $Root "scripts\ensure-env.ps1") -Profile dev | Out-Null
        Import-AriaDotEnv $envFile | Out-Null
    }
    if ($LocalHostPaths) {
        $map = @{
            "/app/data/knowledge_base" = Join-Path $Root "backend\data\knowledge_base"
            "/app/data/uploads"        = Join-Path $Root "backend\data\uploads"
            "/app/data/outputs"        = Join-Path $Root "backend\data\outputs"
            "/app/data/templates"      = Join-Path $Root "backend\data\templates"
            "/app/data/chroma_db"      = Join-Path $Root "backend\data\chroma_db"
        }
        foreach ($key in @("KNOWLEDGE_BASE_PATH", "UPLOAD_PATH", "OUTPUT_PATH", "TEMPLATE_PATH", "CHROMA_PATH")) {
            $cur = [Environment]::GetEnvironmentVariable($key)
            if ($cur -and $map.ContainsKey($cur)) {
                Set-Item -Path "env:$key" -Value $map[$cur]
            }
        }
        if (-not $env:OLLAMA_BASE_URL -or $env:OLLAMA_BASE_URL -match "host\.docker\.internal") {
            $env:OLLAMA_BASE_URL = "http://localhost:11434"
        }
    }
}

function Test-AriaDockerReady {
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker is not running. Start Docker Desktop and retry."
    }
}

function Invoke-AriaOllamaPreflight {
    param([string]$Root = (Get-AriaRoot))
    if ($env:MOCK_LLM -eq "true") { return }
    $url = if ($env:OLLAMA_BASE_URL) { $env:OLLAMA_BASE_URL } else { "http://localhost:11434" }
    $url = $url -replace "host\.docker\.internal", "localhost"
    try {
        Invoke-RestMethod -Uri "$url/api/tags" -TimeoutSec 5 | Out-Null
        Write-Host "[OK] Ollama reachable at $url"
    }
    catch {
        Write-Warning "Ollama not reachable at $url (MOCK_LLM=false). Run scripts/setup_ollama.ps1 or set MOCK_LLM=true."
    }
}

function Wait-AriaComposeHealthy {
    param(
        [string]$ComposeFile,
        [int]$TimeoutSeconds = 180
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $required = @("aria-postgres", "aria-backend", "aria-worker", "aria-frontend", "aria-nginx")
    while ((Get-Date) -lt $deadline) {
        $ps = docker compose -f $ComposeFile ps --format "{{.Name}}|{{.State}}" 2>$null
        $map = @{}
        foreach ($line in ($ps -split "`n")) {
            if ($line -match "^(.+)\|(.+)$") {
                $map[$matches[1]] = $matches[2]
            }
        }
        $allUp = $true
        foreach ($name in $required) {
            if ($map[$name] -notmatch "running") { $allUp = $false; break }
        }
        if ($allUp) {
            try {
                Invoke-RestMethod -Uri "http://localhost/api/v1/health" -TimeoutSec 5 | Out-Null
                $frontend = Invoke-WebRequest -Uri "http://localhost/rfq" -UseBasicParsing -TimeoutSec 10
                if ($frontend.StatusCode -ge 500) { throw "frontend proxy returned $($frontend.StatusCode)" }
                Write-Host "[OK] http://localhost/api/v1/health"
                Write-Host "[OK] http://localhost/rfq"
                return
            }
            catch {
                Start-Sleep -Seconds 3
                continue
            }
        }
        Start-Sleep -Seconds 3
    }
    throw "Timed out waiting for ARIA stack. Run: docker compose -f $ComposeFile logs backend worker"
}

function Invoke-AriaDbInit {
    param([string]$BackendPath)
    Push-Location $BackendPath
    try {
        python -c "from app.database import init_db; init_db(); print('DB init OK')"
        if ($LASTEXITCODE -ne 0) { throw "init_db failed" }
    }
    finally {
        Pop-Location
    }
}
