# 第二台 Windows 测试验收单

测试日期：待填写

测试目标：验证 `TradingAgentAssistant-Setup-0.1.0-mvp-20260611.exe` 在非开发机上的真实安装体验，重点确认客户不需要手动安装 Python、Git、Docker、Node，也不需要访问 PyPI 或 GitHub 完成基础安装。

## 测试机器要求

- Windows 10/11 64-bit。
- 普通用户权限优先，必要时记录管理员权限差异。
- 未安装 Python 3.12。
- 未安装 Git、Docker、Node、Visual Studio 编译工具。
- 尽量使用干净虚拟机快照。

## 测试包信息

```text
File: TradingAgentAssistant-Setup-0.1.0-mvp-20260611.exe
Size: 114,834,929 bytes
SHA256: 51AFB8420CE0CCD262F002D37251EFFAE26CB8D7BFADD6467A0ED5A1BFCDD2BD
Signature: NotSigned
```

当前 MVP 安装包未做代码签名，Windows SmartScreen 或杀毒软件可能弹出风险提示。请截图记录，这不等同于安装包功能失败。

## 测试前记录

```text
Windows version:
VM software:
Network:
Python check result:
Antivirus / SmartScreen:
```

PowerShell 检查：

```powershell
python --version
where.exe python
```

## 安装步骤

1. 双击 `TradingAgentAssistant-Setup-0.1.0-mvp-20260611.exe`。
2. 使用默认安装路径。
3. 安装结束后保留 `Install local Python runtime and dependencies` 勾选。
4. 等待本地运行环境安装完成。
5. 首次配置向导可以暂不运行，先验证安装链路。

## 安装目录通过标准

安装目录中应存在：

```text
scripts/install-offline.ps1
scripts/start.ps1
scripts/stop.ps1
scripts/repair.ps1
scripts/export-logs.ps1
scripts/verify-entrypoints.ps1
wheelhouse/
vendor/upstream/TradingAgents/
.venv/Scripts/python.exe
agent_host/server.py
agent_host/ui.py
docs/虚拟机测试流程.md
```

## 入口冒烟测试

在安装目录打开 PowerShell：

```powershell
.\scripts\verify-entrypoints.ps1
```

通过标准：

- [ ] Python 版本检查通过。
- [ ] `pip check` 通过。
- [ ] 关键模块导入通过。
- [ ] `http://127.0.0.1:8787/health` 正常。
- [ ] `http://127.0.0.1:8787/` 首页正常。
- [ ] `http://127.0.0.1:8787/docs` 正常。
- [ ] A/HK/US 样例识别通过。
- [ ] 诊断接口正常。
- [ ] 服务可以停止。

## 手动界面验收

- [ ] 从开始菜单点击 `Start Trading Agent Assistant`。
- [ ] 浏览器打开 `http://127.0.0.1:8787/`。
- [ ] 首屏能看到“研究任务”和“投研报告”。
- [ ] 识别 `600519` 得到 `600519.SH`。
- [ ] 历史报告打开后能看到报告目录和分区。
- [ ] 长报告没有内部滚动条。
- [ ] 原始输出或错误信息附录默认折叠。
- [ ] 刷新诊断正常。

## 功能烟测

```powershell
Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8787/api/normalize-symbol?symbol=600519"
Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8787/api/normalize-symbol?symbol=00700.HK"
Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8787/api/normalize-symbol?symbol=AAPL"
Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8787/api/diagnostics"
```

## 失败时收集信息

优先运行：

```powershell
.\scripts\export-logs.ps1
```

记录：

```text
Windows version:
Install path:
Python preinstalled: yes/no
Error screenshot:
Exported log zip:
Symptom:
Root cause:
Fix:
```

如运行环境损坏，尝试：

```powershell
.\scripts\repair.ps1
```

## 测试结论

```text
Result: Pass / Fail
Tester:
Machine:
Blocking issues:
Notes:
```
