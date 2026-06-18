param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8787,
    [int]$StartupTimeoutSeconds = 45
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = $OutputEncoding
[Console]::InputEncoding = $OutputEncoding

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$StartScript = Join-Path $Root "scripts\start.ps1"
$StopScript = Join-Path $Root "scripts\stop.ps1"
$ExportLogsScript = Join-Path $Root "scripts\export-logs.ps1"
$RuntimeDir = Join-Path $Root "runtime"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

function Assert-Path {
    param([string]$Path, [string]$Name)
    if (-not (Test-Path $Path)) {
        throw "Missing $Name`: $Path"
    }
    Write-Host "OK $Name`: $Path"
}

function Test-HttpOk {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 8
        return ($response.StatusCode -eq 200)
    }
    catch {
        return $false
    }
}

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

Write-Step "File layout"
Assert-Path $Python "Python venv"
Assert-Path $StartScript "start script"
Assert-Path $StopScript "stop script"
Assert-Path $ExportLogsScript "log export script"
Assert-Path (Join-Path $Root "agent_host\server.py") "server module"
Assert-Path (Join-Path $Root "agent_host\ui.py") "UI module"
Assert-Path (Join-Path $Root "vendor\upstream\TradingAgents") "upstream TradingAgents"
Assert-Path (Join-Path $Root "wheelhouse") "wheelhouse"

Write-Step "Python and dependency imports"
& $Python --version
if ($LASTEXITCODE -ne 0) {
    throw "Python version check failed."
}

& $Python -m pip check
if ($LASTEXITCODE -ne 0) {
    throw "pip check failed."
}

& $Python -c "import agent_host.server, fastapi, yfinance, docx, reportlab; print('imports ok')"
if ($LASTEXITCODE -ne 0) {
    throw "Python import smoke test failed."
}

Write-Step "Start local service"
& $StartScript -NoBrowser -SkipConfigure
if ($LASTEXITCODE -ne 0) {
    throw "start.ps1 failed."
}

$healthUrl = "http://$HostAddress`:$Port/health"
$homeUrl = "http://$HostAddress`:$Port/"
$docsUrl = "http://$HostAddress`:$Port/docs"

$ready = $false
for ($i = 1; $i -le ($StartupTimeoutSeconds * 2); $i++) {
    if (Test-HttpOk $healthUrl) {
        $ready = $true
        break
    }
    Start-Sleep -Milliseconds 500
}
if (-not $ready) {
    throw "Service did not become healthy: $healthUrl"
}

Write-Host "Health OK: $healthUrl"
if (-not (Test-HttpOk $homeUrl)) {
    throw "Home page did not return HTTP 200: $homeUrl"
}
Write-Host "Home OK: $homeUrl"
if (-not (Test-HttpOk $docsUrl)) {
    throw "API docs did not return HTTP 200: $docsUrl"
}
Write-Host "Docs OK: $docsUrl"

Write-Step "API smoke tests"
$symbols = @("600519", "000001", "00700.HK", "9988.HK", "AAPL", "NVDA")
foreach ($symbol in $symbols) {
    $url = "http://$HostAddress`:$Port/api/normalize-symbol?symbol=$([uri]::EscapeDataString($symbol))"
    $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 8
    if ($response.StatusCode -ne 200) {
        throw "Symbol normalization failed: $symbol"
    }
    Write-Host "Normalize OK: $symbol"
}

$diagnosticsUrl = "http://$HostAddress`:$Port/api/diagnostics"
$diagnostics = Invoke-WebRequest -UseBasicParsing -Uri $diagnosticsUrl -TimeoutSec 8
if ($diagnostics.StatusCode -ne 200) {
    throw "Diagnostics failed: $diagnosticsUrl"
}
Write-Host "Diagnostics OK: $diagnosticsUrl"

Write-Step "Stop local service"
& $StopScript
Write-Host "Entry point verification completed."
