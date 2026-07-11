# 从国内镜像拉取 Docker 基础镜像并打 tag，解决 Docker Hub 直连失败
# 用法: .\scripts\pull-images-cn.ps1
# 然后: docker compose up --build

$ErrorActionPreference = "Stop"

# 可按网络情况调整镜像源（任选一个能通的）
$Mirrors = @(
    "docker.1ms.run",
    "docker.m.daocloud.io",
    "docker.xuanyuan.me"
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
