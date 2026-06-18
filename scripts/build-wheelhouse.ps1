param(
    [string]$Python = "python",
    [string]$IndexUrl = "https://pypi.tuna.tsinghua.edu.cn/simple",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = $OutputEncoding
[Console]::InputEncoding = $OutputEncoding

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$Wheelhouse = Join-Path $Root "wheelhouse"
$Upstream = Join-Path $Root "vendor\upstream\TradingAgents"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

if (-not (Test-Path $Upstream)) {
    throw "缺少上游源码：$Upstream。请先运行 scripts\fetch-upstream.ps1。"
}

if ($Force -and (Test-Path $Wheelhouse)) {
    Remove-Item -Recurse -Force -LiteralPath $Wheelhouse
}
New-Item -ItemType Directory -Force -Path $Wheelhouse | Out-Null

Write-Step "构建上游 TradingAgents 及运行依赖 wheel"
& $Python -m pip wheel -i $IndexUrl --wheel-dir $Wheelhouse $Upstream
if ($LASTEXITCODE -ne 0) {
    throw "构建上游依赖 wheel 失败。"
}

Write-Step "构建 Windows wrapper 运行依赖 wheel"
& $Python -m pip wheel -i $IndexUrl --wheel-dir $Wheelhouse -r (Join-Path $Root "requirements-runtime.txt")
if ($LASTEXITCODE -ne 0) {
    throw "构建 wrapper 依赖 wheel 失败。"
}

Write-Host ""
Write-Host "wheelhouse 已生成：$Wheelhouse"



