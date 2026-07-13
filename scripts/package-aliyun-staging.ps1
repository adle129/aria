# Package ARIA R1 staging tarball (no upload). For ECS Workbench / manual scp.
# Usage: .\scripts\package-aliyun-staging.ps1
#        .\scripts\package-aliyun-staging.ps1 -OutFile e:\tmp\aria-staging.tar.gz

param(
    [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $OutFile) {
    $OutFile = Join-Path $Root "aria-staging.tar.gz"
}

$required = @(
    "docker-compose.aliyun-staging.yml",
    ".env.aliyun-staging.example",
    "scripts\deploy-aliyun-staging.sh",
    "scripts\verify-staging-deploy.sh",
    "deploy\scripts\start.sh",
    "frontend\src\app\rfq\page.tsx",
    "backend\app\utils\knowledge_paths.py"
)
foreach ($rel in $required) {
    $p = Join-Path $Root $rel
    if (-not (Test-Path $p)) {
        Write-Error "Missing required file: $rel"
    }
}

$gitSha = "nogit"
try {
    $full = (git -C $Root rev-parse HEAD 2>$null).Trim()
    $short = (git -C $Root rev-parse --short HEAD 2>$null).Trim()
    if ($short) { $gitSha = $short }
} catch {
    $full = ""
}
$packagedAt = Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ'
# Unique per package so same-commit rebuilds still invalidate COPY app / Next build layers
$deploySha = if ($gitSha -ne "nogit") { "${gitSha}-${packagedAt}" } else { "local-${packagedAt}" }

$stampPath = Join-Path $Root "deploy-stamp.txt"
$stamp = @"
deploy_sha=$deploySha
git_sha=$gitSha
git_sha_full=$full
packaged_at=$packagedAt
profile=aliyun-staging
compose=docker-compose.aliyun-staging.yml
"@
[System.IO.File]::WriteAllText($stampPath, ($stamp -replace "`r`n", "`n"))

# Windows core.autocrlf=true can leave CRLF in the working tree; ECS bash rejects them
# (e.g. seed-runtime-data.sh: set: pipefail). Force LF before packing.
Write-Host "==> Normalizing shell scripts to LF..."
$shDirs = @(
    (Join-Path $Root "scripts"),
    (Join-Path $Root "deploy\scripts")
)
$entrypoint = Join-Path $Root "backend\docker-entrypoint.sh"
$normalized = 0
foreach ($dir in $shDirs) {
    if (-not (Test-Path $dir)) { continue }
    Get-ChildItem -Path $dir -Filter "*.sh" -File -Recurse | ForEach-Object {
        $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
        $text = [System.Text.Encoding]::UTF8.GetString($bytes)
        if ($text.Contains("`r")) {
            $lf = $text -replace "`r`n", "`n" -replace "`r", "`n"
            $utf8NoBom = New-Object System.Text.UTF8Encoding $false
            [System.IO.File]::WriteAllText($_.FullName, $lf, $utf8NoBom)
            $normalized++
        }
    }
}
if (Test-Path $entrypoint) {
    $bytes = [System.IO.File]::ReadAllBytes($entrypoint)
    $text = [System.Text.Encoding]::UTF8.GetString($bytes)
    if ($text.Contains("`r")) {
        $lf = $text -replace "`r`n", "`n" -replace "`r", "`n"
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($entrypoint, $lf, $utf8NoBom)
        $normalized++
    }
}
Write-Host "    normalized $normalized file(s)"

Write-Host "==> Packaging R1 staging to $OutFile"
Write-Host "    deploy_sha=$deploySha"
tar -czf $OutFile `
    --exclude=node_modules `
    --exclude=.git `
    --exclude=.next `
    --exclude=__pycache__ `
    --exclude=.venv `
    --exclude=backend/data/chroma_db `
    --exclude=backend/data/uploads `
    --exclude=backend/data/outputs `
    --exclude=backend/data/aria_local.db `
    --exclude=aria-deploy.tar.gz `
    --exclude=aria-staging.tar.gz `
    -C $Root .

$mb = [math]::Round((Get-Item $OutFile).Length / 1MB, 2)
Write-Host "==> Done ($mb MB)"
Write-Host ""
Write-Host "Upload aria-staging.tar.gz to ECS /tmp/ then on ECS:"
Write-Host "  sudo mkdir -p /opt/aria"
Write-Host "  sudo tar -xzf /tmp/aria-staging.tar.gz -C /opt/aria"
Write-Host "  cd /opt/aria && bash scripts/deploy-aliyun-staging.sh"
Write-Host ""
Write-Host "Verify tarball:"
Write-Host "  tar -tzf /tmp/aria-staging.tar.gz | grep deploy-stamp.txt"
Write-Host "  tar -xOf /tmp/aria-staging.tar.gz deploy-stamp.txt"
Write-Host "After deploy: bash scripts/verify-staging-deploy.sh"
