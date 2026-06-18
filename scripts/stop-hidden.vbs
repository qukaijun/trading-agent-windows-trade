Option Explicit

Dim shell, fso, scriptDir, ps, command, exitCode

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
ps = shell.ExpandEnvironmentStrings("%SystemRoot%") & "\System32\WindowsPowerShell\v1.0\powershell.exe"

command = """" & ps & """ -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & scriptDir & "\stop.ps1"""
exitCode = shell.Run(command, 0, True)

If exitCode = 0 Then
    MsgBox "本地服务已停止。", vbInformation, "停止本地服务"
Else
    MsgBox "停止服务时遇到问题。请稍后重试，或导出售后诊断日志。", vbExclamation, "停止失败"
End If
