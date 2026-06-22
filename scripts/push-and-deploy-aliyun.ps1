# 从本机推送 ARIA 到阿里云 ECS 并一键部署（PowerShell）
# 用法:
#   .\scripts\push-and-deploy-aliyun.ps1 -Host 8.136.177.195 -User root -KeyPath C:\path\to\key.pem
# 前置: ECS 安全组放行 22、80；本机可 SSH 登录

param(
    [Parameter(Mandatory = $true)]
    [string]$Host,
    [string]$User = "root",
    [string]$KeyPath = "",
    [string]$RemoteDir = "/opt/aria"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$SshOpts = @()
if ($KeyPath) {
    $SshOpts += @("-i", $KeyPath)
}

$Target = "${User}@${Host}"
$Archive = Join-Path $env:TEMP "aria-deploy.tar.gz"

Write-Host "==> 打包项目（排除 node_modules、.git、构建缓存）..."
if (Get-Command tar -ErrorAction SilentlyContinue) {
    tar -czf $Archive `
        --exclude=node_modules `
        --exclude=.git `
        --exclude=.next `
        --exclude=__pycache__ `
        --exclude=.venv `
        --exclude=backend/data/chroma_db `
        --exclude=backend/data/uploads `
        --exclude=backend/data/outputs `
        -C $Root .
} else {
    Write-Error "需要 tar 命令（Windows 10+ 自带）。"
}

Write-Host "==> 上传到 $Target:$RemoteDir ..."
ssh @SshOpts $Target "mkdir -p $RemoteDir"
scp @SshOpts $Archive "${Target}:/tmp/aria-deploy.tar.gz"
ssh @SshOpts $Target "cd $RemoteDir && tar -xzf /tmp/aria-deploy.tar.gz && rm /tmp/aria-deploy.tar.gz"

if (-not (ssh @SshOpts $Target "test -f $RemoteDir/.env")) {
    Write-Host "==> 首次部署：创建 .env（请 SSH 登录修改 POSTGRES_PASSWORD 后重新运行本脚本）"
    ssh @SshOpts $Target "cd $RemoteDir && cp .env.aliyun-demo.example .env"
    Write-Host "请执行: ssh $Target"
    Write-Host "  nano $RemoteDir/.env   # 修改 POSTGRES_PASSWORD"
    Write-Host "  bash $RemoteDir/scripts/deploy-aliyun-demo.sh"
    exit 0
}

Write-Host "==> 远程执行 deploy-aliyun-demo.sh ..."
ssh @SshOpts $Target "chmod +x $RemoteDir/scripts/deploy-aliyun-demo.sh && ARIA_ROOT=$RemoteDir bash $RemoteDir/scripts/deploy-aliyun-demo.sh"

Write-Host "==> 完成。浏览器访问: http://${Host}/"
