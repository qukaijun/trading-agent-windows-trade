Option Explicit

Dim shell, fso, scriptDir, rootDir, ps, command, exitCode, logDir, message

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
rootDir = fso.GetParentFolderName(scriptDir)
logDir = rootDir & "\logs"
ps = shell.ExpandEnvironmentStrings("%SystemRoot%") & "\System32\WindowsPowerShell\v1.0\powershell.exe"

command = """" & ps & """ -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & scriptDir & "\export-logs.ps1"""
exitCode = shell.Run(command, 0, True)

If exitCode = 0 Then
    message = "售后诊断日志已导出。" & vbCrLf & vbCrLf & "已为你打开导出目录，请把最新的 support-logs 压缩包发给服务人员。"
    MsgBox message, vbInformation, "导出完成"
    shell.Run "explorer.exe """ & logDir & """", 1, False
Else
    MsgBox "诊断日志导出失败，请联系服务人员远程协助。", vbExclamation, "导出失败"
End If
