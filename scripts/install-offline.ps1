param(
    [string]$Python = "",
    [string]$VenvDir = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = $OutputEncoding
[Console]::InputEncoding = $OutputEncoding

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
if (-not $VenvDir) {
    $VenvDir = Join-Path $Root ".venv"
}

$RuntimeDir = Join-Path $Root "runtime"
$BundledPythonDir = Join-Path $RuntimeDir "python312"
$BundledPython = Join-Path $BundledPythonDir "python.exe"
$PythonInstaller = Join-Path $RuntimeDir "python-installer\python-3.12.10-amd64.exe"
$Wheelhouse = Join-Path $Root "wheelhouse"
$RuntimeRequirements = Join-Path $Root "requirements-runtime.txt"
$Upstream = Join-Path $Root "vendor\upstream\TradingAgents"
$LogDir = Join-Path $Root "logs"
$LogFile = Join-Path $LogDir ("install-offline-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

function Throw-CustomerSetupError {
    param([string]$Message)
    throw $Message
}

function Test-Python312 {
    param([string]$PythonCommand)

    if (-not $PythonCommand) {
        return $false
    }

    try {
        & $PythonCommand -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" | Out-Null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Install-BundledPython {
    if (-not (Test-Path $PythonInstaller)) {
        Throw-CustomerSetupError "本地 Python 运行组件缺失，请重新下载安装包后覆盖安装。"
    }

    Write-Step "Installing bundled Python 3.12 runtime"
    if (Test-Path $BundledPythonDir) {
        Remove-Item -Recurse -Force -LiteralPath $BundledPythonDir
    }
    New-Item -ItemType Directory -Force -Path $BundledPythonDir | Out-Null
    $arguments = @(
        "/quiet",
        "InstallAllUsers=0",
        "TargetDir=$BundledPythonDir",
        "Include_launcher=0",
        "InstallLauncherAllUsers=0",
        "AssociateFiles=0",
        "PrependPath=0",
        "Include_test=0",
        "Include_doc=0",
        "Include_tcltk=0",
        "Include_pip=1",
        "Include_venv=1",
        "Shortcuts=0",
        "SimpleInstall=1"
    )
    $process = Start-Process -FilePath $PythonInstaller `
        -ArgumentList $arguments `
        -Wait `
        -WindowStyle Hidden `
        -PassThru
    if ($process.ExitCode -ne 0) {
        Throw-CustomerSetupError "本地 Python 运行环境安装失败，请点击“修复本地运行环境”后重试。"
    }
    if (-not (Test-Python312 $BundledPython)) {
        Throw-CustomerSetupError "本地 Python 运行环境未准备完成，请点击“修复本地运行环境”后重试。"
    }
    return $BundledPython
}

function Find-SystemPython312 {
    $candidates = @(
        "python",
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"),
        "C:\Program Files\Python312\python.exe",
        "C:\Program Files (x86)\Python312\python.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Python312 $candidate) {
            return $candidate
        }
    }
    return ""
}

function Resolve-Python {
    if ($Python) {
        if (-not (Test-Python312 $Python)) {
            Throw-CustomerSetupError "指定的 Python 版本不符合要求，请使用安装包自带运行环境或 Python 3.12。"
        }
        return $Python
    }

    if (Test-Python312 $BundledPython) {
        return $BundledPython
    }

    $systemPython = Find-SystemPython312
    if ($systemPython) {
        return $systemPython
    }

    if (Test-Path $PythonInstaller) {
        return (Install-BundledPython)
    }

    Throw-CustomerSetupError "未找到可用的本地 Python 运行环境，请重新下载安装包后覆盖安装。"
}

New-Item -ItemType Directory -Force -Path $RuntimeDir, $LogDir | Out-Null
Start-Transcript -Path $LogFile -Append | Out-Null

try {
    Write-Step "Checking offline package files"
    if (-not (Test-Path $Wheelhouse)) {
        Throw-CustomerSetupError "离线依赖包缺失，请重新下载安装包后覆盖安装。"
    }
    if (-not (Test-Path $RuntimeRequirements)) {
        Throw-CustomerSetupError "运行环境清单缺失，请重新下载安装包后覆盖安装。"
    }
    if (-not (Test-Path $Upstream)) {
        Throw-CustomerSetupError "投研分析核心组件缺失，请重新下载安装包后覆盖安装。"
    }

    $wheelCount = (Get-ChildItem $Wheelhouse -Filter "*.whl").Count
    if ($wheelCount -lt 1) {
        throw "No wheel files found in $Wheelhouse"
    }
    Write-Host "Wheel files: $wheelCount"

    Write-Step "Checking Python version"
    $Python = Resolve-Python
    $version = & $Python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
    Write-Host "Python: $version"
    Write-Host "Python path: $Python"

    if ($Force -and (Test-Path $VenvDir)) {
        Write-Step "Removing existing virtual environment"
        $resolvedRoot = (Resolve-Path $Root).Path
        $resolvedVenv = (Resolve-Path $VenvDir).Path
        if (-not $resolvedVenv.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            Throw-CustomerSetupError "修复路径异常，已停止操作，请联系服务人员远程协助。"
        }
        Remove-Item -Recurse -Force -LiteralPath $VenvDir
    }

    if (-not (Test-Path $VenvDir)) {
        Write-Step "Creating virtual environment"
        & $Python -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) {
            Throw-CustomerSetupError "本地虚拟运行环境创建失败，请点击“修复本地运行环境”后重试。"
        }
    }

    $VenvPython = Join-Path $VenvDir "Scripts\python.exe"

    Write-Step "Installing upstream TradingAgents"
    $TradingAgentsWheel = Get-ChildItem $Wheelhouse -Filter "tradingagents-*.whl" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($TradingAgentsWheel) {
        & $VenvPython -m pip install --no-index --find-links $Wheelhouse $TradingAgentsWheel.FullName
    }
    else {
        & $VenvPython -m pip install --no-index --find-links $Wheelhouse $Upstream
    }
    if ($LASTEXITCODE -ne 0) {
        Throw-CustomerSetupError "投研分析核心组件安装失败，请点击“修复本地运行环境”后重试。"
    }

    Write-Step "Installing Windows wrapper dependencies"
    & $VenvPython -m pip install --no-index --find-links $Wheelhouse -r $RuntimeRequirements
    if ($LASTEXITCODE -ne 0) {
        Throw-CustomerSetupError "工作台运行依赖安装失败，请点击“修复本地运行环境”后重试。"
    }

    Write-Step "Checking dependency consistency"
    & $VenvPython -m pip check
    if ($LASTEXITCODE -ne 0) {
        Throw-CustomerSetupError "本地运行依赖检查未通过，请点击“修复本地运行环境”后重试。"
    }

    Write-Step "Checking Python imports"
& $VenvPython -c "import tradingagents, fastapi, uvicorn, yfinance, docx, reportlab"
    if ($LASTEXITCODE -ne 0) {
        Throw-CustomerSetupError "本地运行环境检查未通过，请点击“修复本地运行环境”后重试。"
    }

    Write-Host ""
    Write-Host "Offline installation completed."
    Write-Host "Log: $LogFile"
}
finally {
    Stop-Transcript | Out-Null
}
