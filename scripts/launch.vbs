Option Explicit

Dim shell, fso, scriptDir, ps, command

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
ps = shell.ExpandEnvironmentStrings("%SystemRoot%") & "\System32\WindowsPowerShell\v1.0\powershell.exe"

command = """" & ps & """ -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & scriptDir & "\start.ps1"" -SkipConfigure -NonInteractive"
shell.Run command, 0, False
WScript.Quit 0
