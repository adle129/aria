# Ensure project .env exists (bootstrap from example).
param(
    [ValidateSet("dev", "prod", "production", "r1")]
    [string]$Profile = "dev"
)

$Root = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $Root ".env"

if (Test-Path $EnvFile) {
    Write-Host "OK: .env exists"
    exit 0
}

$Src = switch ($Profile) {
    { $_ -in "prod", "production", "r1" } { Join-Path $Root ".env.production.example" }
    default { Join-Path $Root ".env.example" }
}

if (-not (Test-Path $Src)) {
    Write-Error "Template not found: $Src"
    exit 1
}

Copy-Item $Src $EnvFile
Write-Host "Created .env from $(Split-Path $Src -Leaf)"
if ($Profile -in "prod", "production", "r1") {
    Write-Warning "Edit POSTGRES_PASSWORD and OLLAMA_* in .env before customer go-live."
}
