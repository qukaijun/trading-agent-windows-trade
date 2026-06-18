param(
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = $OutputEncoding
[Console]::InputEncoding = $OutputEncoding

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$StopScript = Join-Path $ScriptDir "stop.ps1"
$InstallScript = Join-Path $ScriptDir "install-offline.ps1"

Write-Host "正在停止旧服务..."
& $StopScript

Write-Host ""
Write-Host "正在修复本地运行环境..."
if ($Python) {
    & $InstallScript -Python $Python -Force
}
else {
    & $InstallScript -Force
}

Write-Host ""
Write-Host "修复完成。"
