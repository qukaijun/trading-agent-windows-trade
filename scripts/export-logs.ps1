param(
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding
[Console]::InputEncoding = $OutputEncoding

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$RuntimeDir = Join-Path $Root "runtime"
$LogDir = Join-Path $Root "logs"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$PidFile = Join-Path $RuntimeDir "trading-agent.pid"
$HealthUrl = "http://127.0.0.1:8787/health"
$DiagnosticsTextUrl = "http://127.0.0.1:8787/api/diagnostics.txt"

if (-not $OutputDir) {
    $OutputDir = $LogDir
}

function Add-Line {
    param([string]$Path, [string]$Text = "")
    Add-Content -Path $Path -Value $Text -Encoding UTF8
}

function Get-SafeStatus {
    param([scriptblock]$Action, [string]$Fallback)
    try {
        return (& $Action)
    }
    catch {
        return $Fallback
    }
}

function Test-ZipReadable {
    param([string]$ZipPath)

    $testDir = Join-Path $RuntimeDir ("diag-zip-test-{0}" -f (Get-Date -Format "yyyyMMddHHmmssfff"))
    try {
        New-Item -ItemType Directory -Force -Path $testDir | Out-Null
        Expand-Archive -Path $ZipPath -DestinationPath $testDir -Force
        return ((Get-ChildItem -LiteralPath $testDir -Recurse -File -ErrorAction SilentlyContinue).Count -gt 0)
    }
    catch {
        return $false
    }
    finally {
        if (Test-Path $testDir) {
            Remove-Item -Recurse -Force -LiteralPath $testDir -ErrorAction SilentlyContinue
        }
    }
}

New-Item -ItemType Directory -Force -Path $RuntimeDir, $LogDir, $OutputDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ExportRoot = Join-Path $RuntimeDir "log-export"
$ZipPath = Join-Path $OutputDir "support-logs-$timestamp.zip"

if (Test-Path $ExportRoot) {
    Remove-Item -Recurse -Force -LiteralPath $ExportRoot
}
New-Item -ItemType Directory -Force -Path $ExportRoot | Out-Null

$InfoPath = Join-Path $ExportRoot "diagnostics-summary.txt"
Set-Content -Path $InfoPath -Encoding UTF8 -Value @(
    "Trading Agent 投研工作台售后诊断摘要"
    "生成时间：$(Get-Date -Format o)"
    "安装目录：已隐藏"
    "当前用户：已隐藏"
    "设备名称：已隐藏"
    "系统版本：$([System.Environment]::OSVersion.VersionString)"
    "PowerShell：$($PSVersionTable.PSVersion)"
    "实盘交易：未开放"
    ""
)

if (Test-Path $PidFile) {
    Add-Line $InfoPath "服务进程：已记录"
}
else {
    Add-Line $InfoPath "服务进程：未发现"
}

$health = Get-SafeStatus -Fallback "服务未响应或尚未启动" -Action {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $HealthUrl -TimeoutSec 2
    if ($response.StatusCode -eq 200) { "服务正常" } else { "服务状态异常" }
}
Add-Line $InfoPath "健康检查：$health"

if (Test-Path $VenvPython) {
    $pythonVersion = Get-SafeStatus -Fallback "Python 检查失败" -Action { (& $VenvPython --version 2>&1 | Select-Object -First 1) }
    Add-Line $InfoPath "Python：$pythonVersion"
    $pipStatus = Get-SafeStatus -Fallback "依赖检查失败" -Action {
        $output = & $VenvPython -m pip check 2>&1
        if ($LASTEXITCODE -eq 0) { "依赖检查通过" } else { "依赖检查未通过" }
    }
    Add-Line $InfoPath "依赖：$pipStatus"
}
else {
    Add-Line $InfoPath "Python：本地虚拟运行环境未建立"
}

$AppDiagnosticsPath = Join-Path $ExportRoot "app-diagnostics.txt"
$appDiagnostics = Get-SafeStatus -Fallback "应用诊断接口暂不可用。请先尝试重新打开工作台，仍失败时把本诊断包发给服务人员。" -Action {
    (Invoke-WebRequest -UseBasicParsing -Uri $DiagnosticsTextUrl -TimeoutSec 3).Content
}
Set-Content -Path $AppDiagnosticsPath -Encoding UTF8 -Value $appDiagnostics

$LogIndexPath = Join-Path $ExportRoot "log-index.txt"
Set-Content -Path $LogIndexPath -Encoding UTF8 -Value "日志文件清单（仅文件名、大小和时间；不包含原始日志内容）"
if (Test-Path $LogDir) {
    Get-ChildItem -LiteralPath $LogDir -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 30 |
        ForEach-Object {
            Add-Line $LogIndexPath ("- {0} | {1} bytes | {2}" -f $_.Name, $_.Length, $_.LastWriteTime.ToString("s"))
        }
}
else {
    Add-Line $LogIndexPath "- 暂无日志目录"
}

$ReadmePath = Join-Path $ExportRoot "README.txt"
Set-Content -Path $ReadmePath -Encoding UTF8 -Value @(
    "本压缩包用于售后排查。"
    "已默认隐藏本机用户名、安装目录和设备名称。"
    "不包含密钥、登录凭据、调试原文或内部开发目录。"
    "请不要另行粘贴密钥；如服务人员需要配置状态，请只通过工作台配置页重新检测。"
)

if (Test-Path $ZipPath) {
    Remove-Item -Force -LiteralPath $ZipPath
}
Compress-Archive -Path (Join-Path $ExportRoot "*") -DestinationPath $ZipPath -Force

$zipItem = Get-Item -LiteralPath $ZipPath -ErrorAction Stop
if ($zipItem.Length -lt 512 -or -not (Test-ZipReadable $ZipPath)) {
    Remove-Item -Force -LiteralPath $ZipPath -ErrorAction SilentlyContinue
    throw "诊断包生成失败，请联系服务人员远程协助。"
}

Write-Host "售后诊断日志已导出。"


