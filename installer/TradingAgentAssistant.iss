; Inno Setup script for Trading Agent Chinese research workbench.
; Build with: iscc installer\TradingAgentAssistant.iss

#define MyAppName "Trading Agent Assistant"
#define MyAppChineseName "Trading Agent 投研工作台"
#define MyAppVersion "0.2.2-p0-candidate-20260613"
#define MyAppPublisher "Trading Agent 服务交付"
#define MyAppURL "https://github.com/"

[Setup]
AppId={{5B4A7A5A-3A42-45AC-9B91-69C76E62B784}
AppName={#MyAppChineseName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\TradingAgentAssistant
DefaultGroupName={#MyAppChineseName}
DisableProgramGroupPage=yes
DisableReadyMemo=yes
OutputDir=..\release
OutputBaseFilename=TradingAgentAssistant-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
SetupLogging=yes

[Languages]
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"

[Files]
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements-runtime.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements-lock.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\scripts\*.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "..\scripts\*.vbs"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "..\agent_host\*.py"; DestDir: "{app}\agent_host"; Flags: ignoreversion recursesubdirs
Source: "..\mt5_ea\*.mq5"; DestDir: "{app}\mt5_ea"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\docs\*.md"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs
Source: "..\wheelhouse\*.whl"; DestDir: "{app}\wheelhouse"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\runtime\python312\*"; DestDir: "{app}\runtime\python312"; Excludes: "__pycache__\*,*.pyc,*.pyo"; Flags: ignoreversion recursesubdirs skipifsourcedoesntexist
Source: "..\runtime\python-installer\*.exe"; DestDir: "{app}\runtime\python-installer"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\vendor\upstream\TradingAgents\*"; DestDir: "{app}\vendor\upstream\TradingAgents"; Excludes: ".git\*,.venv\*,build\*,dist\*,tests\*,__pycache__\*,*.pyc,*.pyo,*.egg-info\*"; Flags: ignoreversion recursesubdirs skipifsourcedoesntexist

[Dirs]
Name: "{app}\logs"
Name: "{app}\runtime"
Name: "{app}\runtime\python312"
Name: "{app}\vendor\upstream"

[Icons]
Name: "{group}\启动 Trading Agent 投研工作台"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\scripts\launch.vbs"""; WorkingDir: "{app}"
Name: "{group}\停止本地服务"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\scripts\stop-hidden.vbs"""; WorkingDir: "{app}"
Name: "{group}\修复本地运行环境"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\scripts\repair-hidden.vbs"""; WorkingDir: "{app}"
Name: "{group}\导出售后诊断日志"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\scripts\export-logs-hidden.vbs"""; WorkingDir: "{app}"
Name: "{group}\打开使用文档"; Filename: "{app}\docs"
Name: "{group}\打开 MT5 模拟盘 EA"; Filename: "{app}\mt5_ea"
Name: "{group}\项目说明 README"; Filename: "{app}\README.md"
Name: "{userdesktop}\Trading Agent 投研工作台"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\scripts\launch.vbs"""; WorkingDir: "{app}"

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -NoProfile -File ""{app}\scripts\install-offline.ps1"""; WorkingDir: "{app}"; StatusMsg: "正在安装本地运行环境，可能需要几分钟，请不要关闭安装窗口..."; Flags: runhidden waituntilterminated
Filename: "{sys}\wscript.exe"; Parameters: """{app}\scripts\launch.vbs"""; WorkingDir: "{app}"; Description: "启动 Trading Agent 投研工作台"; Flags: postinstall skipifsilent nowait

[UninstallDelete]
Type: files; Name: "{app}\runtime\trading-agent.pid"

[InstallDelete]
Type: files; Name: "{userdesktop}\Trading Agent 投研工作台.lnk"
Type: files; Name: "{userdesktop}\Trading Agent Assistant.lnk"
Type: files; Name: "{group}\启动 Trading Agent 投研工作台.lnk"
Type: files; Name: "{group}\Start Trading Agent Assistant.lnk"
