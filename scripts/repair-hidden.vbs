Option Explicit

Dim shell, fso, scriptDir, ps, command, exitCode, message

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
ps = shell.ExpandEnvironmentStrings("%SystemRoot%") & "\System32\WindowsPowerShell\v1.0\powershell.exe"

message = "即将修复本地运行环境，过程可能需要几分钟。" & vbCrLf & "请不要重复点击。"
MsgBox message, vbInformation, "修复本地运行环境"

command = """" & ps & """ -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & scriptDir & "\repair.ps1"""
exitCode = shell.Run(command, 0, True)

If exitCode = 0 Then
    MsgBox "修复完成。请重新启动 Trading Agent 投研工作台。", vbInformation, "修复完成"
Else
    MsgBox "修复失败。请点击“导出售后诊断日志”，把生成的压缩包发给服务人员。", vbExclamation, "修复失败"
End If
