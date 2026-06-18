$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$PidFile = Join-Path $Root "runtime\trading-agent.pid"
$Port = 8787

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

$stopped = $false

if (Test-Path $PidFile) {
    $pidValue = Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pidValue) {
        $process = Get-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue
        if ($process) {
            Stop-Process -Id $process.Id -Force
            Write-Host "已停止 Trading Agent 助手。PID: $pidValue"
            $stopped = $true
        }
    }
}

foreach ($ownerPid in (Get-PortOwnerPids -LocalPort $Port)) {
    $process = Get-Process -Id $ownerPid -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $ownerPid -Force
        Write-Host "已停止占用端口 $Port 的服务。PID: $ownerPid"
        $stopped = $true
    }
}

Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue

if (-not $stopped) {
    Write-Host "未发现运行中的 Trading Agent 服务。"
}


