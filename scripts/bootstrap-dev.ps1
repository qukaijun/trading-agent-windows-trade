param(
    [string]$Python = "python",
    [string]$IndexUrl = "https://pypi.tuna.tsinghua.edu.cn/simple",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$VenvDir = Join-Path $Root ".venv"
$Upstream = Join-Path $Root "vendor\upstream\TradingAgents"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

if (-not (Test-Path $Upstream)) {
    throw "Missing upstream source: $Upstream. Run scripts\fetch-upstream.ps1 first."
}

if ($Force -and (Test-Path $VenvDir)) {
    Write-Step "Removing existing virtual environment"
    Remove-Item -Recurse -Force -LiteralPath $VenvDir
}

if (-not (Test-Path $VenvDir)) {
    Write-Step "Creating virtual environment"
    & $Python -m venv $VenvDir
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

Write-Step "Upgrading pip"
& $VenvPython -m pip install -i $IndexUrl --upgrade pip

Write-Step "Installing upstream TradingAgents in editable mode"
& $VenvPython -m pip install -i $IndexUrl -e $Upstream

Write-Step "Installing Windows product wrapper dependencies"
& $VenvPython -m pip install -i $IndexUrl -r (Join-Path $Root "requirements-runtime.txt")

Write-Host ""
Write-Host "Development environment is ready."

