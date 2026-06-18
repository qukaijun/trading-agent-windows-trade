param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8787,
    [string]$Stdout = "",
    [string]$Stderr = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = $OutputEncoding
[Console]::InputEncoding = $OutputEncoding

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

Set-Location $Root

if ($Stdout -and $Stderr) {
    $process = Start-Process -FilePath $VenvPython `
        -ArgumentList @("-m", "agent_host", "--host", $HostAddress, "--port", "$Port") `
        -WorkingDirectory $Root `
        -RedirectStandardOutput $Stdout `
        -RedirectStandardError $Stderr `
        -PassThru
    $process.WaitForExit()
    exit $process.ExitCode
}
else {
    & $VenvPython -m agent_host --host $HostAddress --port "$Port"
}
