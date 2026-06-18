param(
    [string]$UpstreamDir = "",
    [switch]$IncludeChineseReference
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
if (-not $UpstreamDir) {
    $UpstreamDir = Join-Path $Root "vendor\upstream"
}

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

function Sync-Repo {
    param(
        [string]$Url,
        [string]$Dir
    )

    if (Test-Path $Dir) {
        Write-Step "Updating $Dir"
        git -C $Dir pull --ff-only
        return
    }

    Write-Step "Cloning $Url"
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Dir) | Out-Null
    git clone --depth 1 $Url $Dir
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is required on the development machine. The final installer should not require Git."
}

Sync-Repo -Url "https://github.com/TauricResearch/TradingAgents.git" `
    -Dir (Join-Path $UpstreamDir "TradingAgents")

if ($IncludeChineseReference) {
    Sync-Repo -Url "https://github.com/hsliuping/TradingAgents-CN.git" `
        -Dir (Join-Path $UpstreamDir "TradingAgents-CN")
}

Write-Host ""
Write-Host "Upstream source is ready: $UpstreamDir"

