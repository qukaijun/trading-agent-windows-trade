param(
    [string]$ISCC = "",
    [switch]$SkipPreflight
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = $OutputEncoding
[Console]::InputEncoding = $OutputEncoding

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$InstallerScript = Join-Path $Root "installer\TradingAgentAssistant.iss"
$Wheelhouse = Join-Path $Root "wheelhouse"
$PythonInstaller = Join-Path $Root "runtime\python-installer\python-3.12.10-amd64.exe"
$BundledPythonDir = Join-Path $Root "runtime\python312"
$BundledPython = Join-Path $BundledPythonDir "python.exe"
$ReleaseDir = Join-Path $Root "release"
$Upstream = Join-Path $Root "vendor\upstream\TradingAgents"

function Find-ISCC {
    if ($ISCC) {
        return $ISCC
    }

    $command = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $candidates = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    throw "ISCC.exe not found. Install Inno Setup 6 or pass -ISCC."
}

function Test-Python312Runtime {
    param([string]$PythonExe)

    if (-not (Test-Path $PythonExe)) {
        return $false
    }

    try {
        & $PythonExe -c "import sys, venv, ensurepip; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" | Out-Null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Prepare-BundledPythonRuntime {
    if (Test-Python312Runtime $BundledPython) {
        Write-Host "Bundled Python runtime ready: $BundledPython"
        return
    }

    $existingRuntime = Find-ExistingPythonRuntime
    if ($existingRuntime) {
        Copy-PythonRuntime -SourceDir $existingRuntime -DestinationDir $BundledPythonDir
        if (Test-Python312Runtime $BundledPython) {
            Write-Host "Bundled Python runtime copied from local Python 3.12: $existingRuntime"
            return
        }
    }

    if (-not (Test-Path $PythonInstaller)) {
        throw "Missing bundled Python installer: $PythonInstaller"
    }

    $signature = Get-AuthenticodeSignature $PythonInstaller
    if ($signature.Status -ne "Valid") {
        throw "Bundled Python installer signature is not valid: $($signature.Status)"
    }

    $tempRuntime = Join-Path $env:TEMP ("TradingAgentAssistant-python312-{0}" -f (Get-Date -Format "yyyyMMddHHmmss"))
    if (Test-Path $tempRuntime) {
        Remove-Item -Recurse -Force -LiteralPath $tempRuntime
    }
    New-Item -ItemType Directory -Force -Path $tempRuntime | Out-Null

    Write-Host "Preparing bundled Python runtime in temporary path: $tempRuntime"
    $arguments = @(
        "/quiet",
        "InstallAllUsers=0",
        "TargetDir=$tempRuntime",
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
    $process = Start-Process -FilePath $PythonInstaller -ArgumentList $arguments -Wait -WindowStyle Hidden -PassThru
    if ($process.ExitCode -eq 0 -and (Test-Python312Runtime (Join-Path $tempRuntime "python.exe"))) {
        Copy-PythonRuntime -SourceDir $tempRuntime -DestinationDir $BundledPythonDir
    }
    else {
        $existingRuntime = Find-ExistingPythonRuntime
        if ($existingRuntime) {
            Copy-PythonRuntime -SourceDir $existingRuntime -DestinationDir $BundledPythonDir
        }
    }

    if (Test-Path $tempRuntime) {
        Remove-Item -Recurse -Force -LiteralPath $tempRuntime -ErrorAction SilentlyContinue
    }

    if (-not (Test-Python312Runtime $BundledPython)) {
        throw "Failed to prepare bundled Python runtime for installer."
    }
}

function Find-ExistingPythonRuntime {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312"),
        "C:\Program Files\Python312",
        "C:\Program Files (x86)\Python312"
    )

    foreach ($candidate in $candidates) {
        $pythonExe = Join-Path $candidate "python.exe"
        if (Test-Python312Runtime $pythonExe) {
            return $candidate
        }
    }
    return ""
}

function Copy-PythonRuntime {
    param(
        [string]$SourceDir,
        [string]$DestinationDir
    )

    if (Test-Path $DestinationDir) {
        Remove-Item -Recurse -Force -LiteralPath $DestinationDir
    }
    New-Item -ItemType Directory -Force -Path $DestinationDir | Out-Null
    Copy-Item -Path (Join-Path $SourceDir "*") -Destination $DestinationDir -Recurse -Force
}

if (-not (Test-Path $InstallerScript)) {
    throw "Installer script not found: $InstallerScript"
}

if (-not $SkipPreflight) {
    if (-not (Test-Path $Wheelhouse)) {
        throw "Missing wheelhouse directory: $Wheelhouse"
    }
    $wheelCount = (Get-ChildItem $Wheelhouse -Filter "*.whl").Count
    if ($wheelCount -lt 1) {
        throw "No wheel files found in $Wheelhouse"
    }
    Write-Host "Wheel files: $wheelCount"

    if (-not (Test-Path (Join-Path $Wheelhouse "tradingagents-0.2.5-py3-none-any.whl"))) {
        Write-Host "Warning: tradingagents wheel not found. install-offline.ps1 will fall back to local upstream source."
    }

    if (-not (Test-Path $PythonInstaller)) {
        throw "Missing bundled Python installer: $PythonInstaller"
    }
    $signature = Get-AuthenticodeSignature $PythonInstaller
    if ($signature.Status -ne "Valid") {
        throw "Bundled Python installer signature is not valid: $($signature.Status)"
    }
    Write-Host "Bundled Python installer: $PythonInstaller"
    Prepare-BundledPythonRuntime

    if (-not (Test-Path $Upstream)) {
        throw "Missing upstream TradingAgents source: $Upstream"
    }
}

New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
$compiler = Find-ISCC
Write-Host "Using Inno Setup compiler: $compiler"

& $compiler $InstallerScript
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup build failed."
}

Write-Host ""
Write-Host "Installer build completed. Output directory: $ReleaseDir"
