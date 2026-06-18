param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8787,
    [switch]$NoBrowser,
    [switch]$SkipConfigure,
    [switch]$NonInteractive,
    [switch]$ForegroundService
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = $OutputEncoding
[Console]::InputEncoding = $OutputEncoding

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$RuntimeDir = Join-Path $Root "runtime"
$LogDir = Join-Path $Root "logs"
$PidFile = Join-Path $RuntimeDir "trading-agent.pid"
$ConfigPath = Join-Path $env:USERPROFILE ".trading-agent-assistant\.env"
$ConfigureScript = Join-Path $ScriptDir "configure.ps1"
$InstallScript = Join-Path $ScriptDir "install-offline.ps1"
$ServeScript = Join-Path $ScriptDir "serve.ps1"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

function Wait-BeforeExit {
    param([int]$Code = 1)

    if ($NonInteractive) {
        exit $Code
    }

    Write-Host ""
    Write-Host "按回车关闭此窗口..."
    try {
        [void](Read-Host)
    }
    catch {
        Start-Sleep -Seconds 10
    }
    exit $Code
}

trap {
    Write-Host ""
    Write-Host "启动失败：本地运行环境或服务状态未准备完成。"
    Write-Host "请先从开始菜单点击“修复本地运行环境”，完成后重新打开工作台。"
    Write-Host "如果仍无法启动，请点击“导出售后诊断日志”，把导出的压缩包发给服务人员。"
    Wait-BeforeExit 1
}

function Test-Health {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
        return ($response.StatusCode -eq 200)
    }
    catch {
        return $false
    }
}

function Get-PortOwnerPids {
    param([int]$LocalPort)

    $owners = @()
    $lines = & netstat -ano -p tcp 2>$null
    foreach ($line in $lines) {
        if ($line -match "^\s*TCP\s+\S+:$LocalPort\s+\S+\s+LISTENING\s+(\d+)\s*$") {
            $owners += [int]$Matches[1]
        }
    }
    return @($owners | Select-Object -Unique)
}

function Stop-PortOwners {
    param([int]$LocalPort)

    $owners = Get-PortOwnerPids -LocalPort $LocalPort
    foreach ($ownerPid in $owners) {
        try {
            Stop-Process -Id $ownerPid -Force -ErrorAction Stop
            Write-Host "已停止占用端口 $LocalPort 的旧服务。PID: $ownerPid"
        }
        catch {
            throw "端口 $LocalPort 已被其他程序占用，且无法自动停止。请重启电脑后再打开 Trading Agent 投研工作台。"
        }
    }
}

function Repair-ProcessPathEnvironment {
    $processEnv = [Environment]::GetEnvironmentVariables("Process")
    $pathKeys = @($processEnv.Keys | Where-Object { [string]$_ -ieq "Path" })
    if ($pathKeys.Count -le 1) {
        return
    }

    $pathValue = $env:Path
    if (-not $pathValue) {
        $pathValue = [string]$processEnv[$pathKeys[0]]
    }

    foreach ($key in $pathKeys) {
        [Environment]::SetEnvironmentVariable([string]$key, $null, "Process")
    }
    [Environment]::SetEnvironmentVariable("Path", $pathValue, "Process")
    $env:Path = $pathValue
}

New-Item -ItemType Directory -Force -Path $RuntimeDir, $LogDir | Out-Null

if (-not (Test-Path $VenvPython)) {
    if (-not (Test-Path $InstallScript)) {
        throw "本地运行环境安装组件缺失。"
    }

    Write-Step "首次启动正在安装本地运行环境，可能需要几分钟，请不要关闭窗口"
    & $InstallScript
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPython)) {
        throw "本地运行环境安装失败。"
    }
}

if (-not $SkipConfigure -and -not (Test-Path $ConfigPath)) {
    Write-Step "正在打开首次配置向导"
    & $ConfigureScript
    if ($LASTEXITCODE -ne 0) {
        throw "首次配置未完成。"
    }
}

$LocalHealthHost = $HostAddress
if ($HostAddress -eq "0.0.0.0" -or $HostAddress -eq "::") {
    $LocalHealthHost = "127.0.0.1"
}
$HealthUrl = "http://$LocalHealthHost`:$Port/health"
$HomeUrl = "http://$LocalHealthHost`:$Port/"

if (Test-Path $PidFile) {
    $existingPid = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($existingPid) {
        $existingProcess = Get-Process -Id ([int]$existingPid) -ErrorAction SilentlyContinue
        if ($existingProcess -and (Test-Health $HealthUrl)) {
            Write-Host "Trading Agent 投研工作台已在运行。PID: $existingPid"
            if (-not $NoBrowser) {
                Start-Process $HomeUrl
            }
            exit 0
        }
    }
}

if (Test-Health $HealthUrl) {
    Write-Step "检测到旧服务占用端口，正在重启本地服务"
    Stop-PortOwners -LocalPort $Port
    for ($i = 1; $i -le 10; $i++) {
        if (-not (Test-Health $HealthUrl)) {
            break
        }
        Start-Sleep -Seconds 1
    }
}

Write-Step "正在启动 Trading Agent 本地投研服务"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$stdout = Join-Path $LogDir "trading-agent-$timestamp.out.log"
$stderr = Join-Path $LogDir "trading-agent-$timestamp.err.log"

Repair-ProcessPathEnvironment

if ($ForegroundService) {
    Set-Content -Path $PidFile -Value $PID -Encoding ASCII
    if (-not $NoBrowser) {
        $openCommand = "Start-Sleep -Seconds 5; Start-Process '$HomeUrl'"
        Start-Process -FilePath (Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe") `
            -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $openCommand) `
            -WindowStyle Hidden | Out-Null
    }
    $ErrorActionPreference = "Continue"
    & $VenvPython -m agent_host --host $HostAddress --port "$Port" *>> $stdout
    exit $LASTEXITCODE
}

$PowerShellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$process = Start-Process -FilePath $PowerShellExe `
    -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $ServeScript,
        "-HostAddress",
        $HostAddress,
        "-Port",
        "$Port",
        "-Stdout",
        $stdout,
        "-Stderr",
        $stderr
    ) `
    -WorkingDirectory $Root `
    -WindowStyle Hidden `
    -PassThru

Set-Content -Path $PidFile -Value $process.Id -Encoding ASCII
Write-Host "PID: $($process.Id)"

Write-Step "正在检查服务状态"
$ready = $false
for ($i = 1; $i -le 30; $i++) {
    if (Test-Health $HealthUrl) {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $ready) {
    Write-Host "服务未能按时启动，请导出售后诊断日志交给服务人员。"
    throw "本地服务启动超时。"
}

Start-Sleep -Seconds 5
if (-not (Test-Health $HealthUrl)) {
    throw "本地服务启动后未能保持运行。请从开始菜单点击 导出售后诊断日志，并把导出的压缩包发给服务人员。"
}

Write-Host "Trading Agent 投研工作台已启动：$HomeUrl"
if (-not $NoBrowser) {
    Start-Process $HomeUrl
}
