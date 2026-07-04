# Split aria-deploy.tar.gz for Workbench upload (when single file fails with INTERNAL_SERVER_ERROR)
# Usage:
#   .\scripts\package-aliyun-deploy.ps1
#   .\scripts\split-deploy-package.ps1
#
# On ECS after uploading all parts to /tmp/:
#   bash scripts/combine-deploy-package.sh
#   sudo tar -xzf /tmp/aria-deploy.tar.gz -C /opt/aria

param(
    [string]$Archive = "",
    [int]$ChunkKB = 400
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $Archive) {
    $Archive = Join-Path $Root "aria-deploy.tar.gz"
}
if (-not (Test-Path $Archive)) {
    Write-Error "Archive not found: $Archive (run package-aliyun-deploy.ps1 first)"
}

$partPrefix = Join-Path (Split-Path $Archive) "aria-deploy.part"
Get-ChildItem "$(Split-Path $Archive)\aria-deploy.part*" -ErrorAction SilentlyContinue | Remove-Item -Force

$bytes = [System.IO.File]::ReadAllBytes($Archive)
$chunkSize = $ChunkKB * 1024
$index = 0
for ($offset = 0; $offset -lt $bytes.Length; $offset += $chunkSize) {
    $len = [Math]::Min($chunkSize, $bytes.Length - $offset)
    $partPath = "{0}{1:D2}" -f $partPrefix, $index
    [System.IO.File]::WriteAllBytes($partPath, $bytes[$offset..($offset + $len - 1)])
    $index++
}

Write-Host "==> Split $(Split-Path $Archive -Leaf) into $index part(s) (~${ChunkKB}KB each)"
Get-ChildItem "$(Split-Path $Archive)\aria-deploy.part*" | ForEach-Object {
    $kb = [math]::Round($_.Length / 1KB, 1)
    Write-Host "    $($_.Name)  ${kb} KB"
}
Write-Host ""
Write-Host "Upload aria-deploy.part00, part01, ... to ECS /tmp/ via Workbench, then:"
Write-Host "  bash /opt/aria/scripts/combine-deploy-package.sh"
