# Pull Docker base images from China mirrors and retag (when Docker Hub is unreachable)
# Usage: .\scripts\pull-images-cn.ps1
# Then:  docker compose up --build

$ErrorActionPreference = "Stop"

# Mirror registry list — pick one that works on your network
# Prefer 1ms.run: daocloud often returns EOF on manifest HEAD during BuildKit resolve
$Mirrors = @(
    "docker.1ms.run",
    "docker.xuanyuan.me",
    "docker.m.daocloud.io"
)

$Images = @(
    @{ Source = "library/nginx:alpine"; Target = "nginx:alpine" },
    @{ Source = "library/postgres:16-alpine"; Target = "postgres:16-alpine" },
    @{ Source = "library/python:3.11-slim"; Target = "python:3.11-slim" },
    @{ Source = "library/node:20-alpine"; Target = "node:20-alpine" }
)

function Pull-With-Mirror {
    param([string]$Source, [string]$Target)

    foreach ($mirror in $Mirrors) {
        $full = "$mirror/$Source"
        Write-Host "Trying $full ..."
        docker pull $full 2>$null
        if ($LASTEXITCODE -eq 0) {
            docker tag $full $Target
            Write-Host "OK -> tagged as $Target"
            return $true
        }
    }
    return $false
}

foreach ($img in $Images) {
    if (-not (Pull-With-Mirror -Source $img.Source -Target $img.Target)) {
        Write-Error "Failed to pull $($img.Source). Try configuring Docker Desktop registry mirror (see README)."
    }
}

Write-Host ""
Write-Host "All base images ready. Run: docker compose up --build"
