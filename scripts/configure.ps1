param(
    [ValidateSet("", "qwen-cn", "deepseek", "kimi-cn", "glm-cn", "minimax-cn", "siliconflow-cn", "openai", "openrouter", "ollama", "custom-openai")]
    [string]$Provider = "",
    [string]$Model = "",
    [string]$ApiKey = "",
    [string]$BaseUrl = "",
    [string]$TushareToken = "",
    [string]$ConfigDir = (Join-Path $env:USERPROFILE ".trading-agent-assistant"),
    [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = $OutputEncoding
[Console]::InputEncoding = $OutputEncoding

$Providers = @(
    [PSCustomObject]@{
        Key = "qwen-cn"
        Label = "通义千问 / DashScope 国内站"
        ApiKeyEnv = "DASHSCOPE_CN_API_KEY"
        BaseUrlEnv = "DASHSCOPE_CN_BASE_URL"
        DefaultModel = "qwen-plus-latest"
        DefaultBaseUrl = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        RequiresKey = $true
    },
    [PSCustomObject]@{
        Key = "deepseek"
        Label = "DeepSeek"
        ApiKeyEnv = "DEEPSEEK_API_KEY"
        BaseUrlEnv = "DEEPSEEK_BASE_URL"
        DefaultModel = "deepseek-chat"
        DefaultBaseUrl = "https://api.deepseek.com/v1"
        RequiresKey = $true
    },
    [PSCustomObject]@{
        Key = "kimi-cn"
        Label = "月之暗面 Kimi"
        ApiKeyEnv = "MOONSHOT_API_KEY"
        BaseUrlEnv = "MOONSHOT_BASE_URL"
        DefaultModel = "kimi-k2-0711-preview"
        DefaultBaseUrl = "https://api.moonshot.cn/v1"
        RequiresKey = $true
    },
    [PSCustomObject]@{
        Key = "glm-cn"
        Label = "智谱 GLM 国内站"
        ApiKeyEnv = "ZHIPU_CN_API_KEY"
        BaseUrlEnv = "ZHIPU_CN_BASE_URL"
        DefaultModel = "glm-4.6"
        DefaultBaseUrl = "https://open.bigmodel.cn/api/paas/v4"
        RequiresKey = $true
    },
    [PSCustomObject]@{
        Key = "minimax-cn"
        Label = "MiniMax 国内站"
        ApiKeyEnv = "MINIMAX_CN_API_KEY"
        BaseUrlEnv = "MINIMAX_CN_BASE_URL"
        DefaultModel = "MiniMax-M2"
        DefaultBaseUrl = "https://api.minimaxi.com/v1"
        RequiresKey = $true
    },
    [PSCustomObject]@{
        Key = "siliconflow-cn"
        Label = "硅基流动 SiliconFlow"
        ApiKeyEnv = "SILICONFLOW_API_KEY"
        BaseUrlEnv = "SILICONFLOW_BASE_URL"
        DefaultModel = "Qwen/Qwen3-32B"
        DefaultBaseUrl = "https://api.siliconflow.cn/v1"
        RequiresKey = $true
    },
    [PSCustomObject]@{
        Key = "openai"
        Label = "OpenAI"
        ApiKeyEnv = "OPENAI_API_KEY"
        BaseUrlEnv = "OPENAI_BASE_URL"
        DefaultModel = "gpt-5.5-instant"
        DefaultBaseUrl = "https://api.openai.com/v1"
        RequiresKey = $true
    },
    [PSCustomObject]@{
        Key = "openrouter"
        Label = "OpenRouter"
        ApiKeyEnv = "OPENROUTER_API_KEY"
        BaseUrlEnv = "OPENROUTER_BASE_URL"
        DefaultModel = "deepseek/deepseek-chat"
        DefaultBaseUrl = "https://openrouter.ai/api/v1"
        RequiresKey = $true
    },
    [PSCustomObject]@{
        Key = "ollama"
        Label = "Ollama 本地模型"
        ApiKeyEnv = ""
        BaseUrlEnv = "OLLAMA_BASE_URL"
        DefaultModel = "qwen2.5:14b"
        DefaultBaseUrl = "http://localhost:11434/v1"
        RequiresKey = $false
    },
    [PSCustomObject]@{
        Key = "custom-openai"
        Label = "自定义 OpenAI 兼容接口"
        ApiKeyEnv = "CUSTOM_OPENAI_API_KEY"
        BaseUrlEnv = "CUSTOM_OPENAI_BASE_URL"
        DefaultModel = "your-model-name"
        DefaultBaseUrl = "https://your-endpoint.example.com/v1"
        RequiresKey = $true
    }
)

function ConvertFrom-SecureText {
    param([System.Security.SecureString]$Secure)
    if (-not $Secure) {
        return ""
    }
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

function Select-Provider {
    Write-Host ""
    Write-Host "请选择大模型供应商："
    for ($i = 0; $i -lt $Providers.Count; $i++) {
        $index = $i + 1
        Write-Host "  [$index] $($Providers[$i].Label)"
    }
    Write-Host ""
    $choice = Read-Host "输入数字，直接回车默认选择 1"
    if ([string]::IsNullOrWhiteSpace($choice)) {
        return $Providers[0]
    }
    $number = 0
    if (-not [int]::TryParse($choice, [ref]$number) -or $number -lt 1 -or $number -gt $Providers.Count) {
        throw "无效的供应商选择：$choice"
    }
    return $Providers[$number - 1]
}

function Read-Optional {
    param(
        [string]$Prompt,
        [string]$Default = ""
    )
    if ($Default) {
        $value = Read-Host "$Prompt，直接回车使用 [$Default]"
        if ([string]::IsNullOrWhiteSpace($value)) {
            return $Default
        }
        return $value.Trim()
    }
    $raw = Read-Host "$Prompt，直接回车跳过"
    return $raw.Trim()
}

$ConfigPath = Join-Path $ConfigDir ".env"

if ((Test-Path $ConfigPath) -and -not $Force) {
    Write-Host "配置已存在：$ConfigPath"
    Write-Host "如需覆盖，请加 -Force。"
    exit 0
}

if ($Provider) {
    $Selected = $Providers | Where-Object { $_.Key -eq $Provider } | Select-Object -First 1
    if (-not $Selected) {
        throw "不支持的供应商：$Provider"
    }
}
else {
    Write-Host ""
    Write-Host "Trading Agent 助手首次配置"
    Write-Host "配置路径：$ConfigPath"
    Write-Host "API Key 只会保存在本机配置文件中。"
    $Selected = Select-Provider
}

if (-not $Model) {
    $Model = if ($Provider) { $Selected.DefaultModel } else { Read-Optional -Prompt "模型名称" -Default $Selected.DefaultModel }
}

if (-not $BaseUrl) {
    $BaseUrl = if ($Provider) { $Selected.DefaultBaseUrl } else { Read-Optional -Prompt "Base URL" -Default $Selected.DefaultBaseUrl }
}

if ($Selected.RequiresKey -and -not $ApiKey) {
    if ($Provider) {
        throw "$($Selected.Label) 需要 -ApiKey。"
    }
    $secure = Read-Host "请输入 $($Selected.Label) 的 API Key" -AsSecureString
    $ApiKey = ConvertFrom-SecureText -Secure $secure
}

if (-not $Provider -and -not $TushareToken) {
    $secureTushare = Read-Host "可选：请输入 Tushare Token，直接回车跳过" -AsSecureString
    $TushareToken = ConvertFrom-SecureText -Secure $secureTushare
}

New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null

$RuntimeProvider = $Selected.Key
$RuntimeApiKeyEnv = $Selected.ApiKeyEnv
$RuntimeBaseUrlEnv = $Selected.BaseUrlEnv
$OpenAICompatibleViaOpenRouter = @("kimi-cn", "siliconflow-cn", "custom-openai")
if ($OpenAICompatibleViaOpenRouter -contains $Selected.Key) {
    $RuntimeProvider = "openrouter"
    $RuntimeApiKeyEnv = "OPENROUTER_API_KEY"
    $RuntimeBaseUrlEnv = "OPENROUTER_BASE_URL"
}

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("TRADINGAGENTS_LLM_PROVIDER=$RuntimeProvider")
$lines.Add("TRADINGAGENT_DISPLAY_PROVIDER=$($Selected.Key)")
$lines.Add("TRADINGAGENTS_DEEP_THINK_LLM=$Model")
$lines.Add("TRADINGAGENTS_QUICK_THINK_LLM=$Model")
$lines.Add("TRADINGAGENTS_OUTPUT_LANGUAGE=简体中文")
$lines.Add("TRADINGAGENTS_MAX_DEBATE_ROUNDS=1")
$lines.Add("TRADINGAGENTS_MAX_RISK_ROUNDS=1")
$lines.Add("TRADINGAGENTS_TEMPERATURE=0.0")
if ($Selected.ApiKeyEnv -and $ApiKey) {
    $lines.Add("$($Selected.ApiKeyEnv)=$ApiKey")
}
if ($RuntimeApiKeyEnv -and $ApiKey -and $RuntimeApiKeyEnv -ne $Selected.ApiKeyEnv) {
    $lines.Add("$RuntimeApiKeyEnv=$ApiKey")
}
if ($Selected.BaseUrlEnv -and $BaseUrl) {
    $lines.Add("$($Selected.BaseUrlEnv)=$BaseUrl")
}
if ($RuntimeBaseUrlEnv -and $BaseUrl -and $RuntimeBaseUrlEnv -ne $Selected.BaseUrlEnv) {
    $lines.Add("$RuntimeBaseUrlEnv=$BaseUrl")
}
if ($BaseUrl) {
    $lines.Add("TRADINGAGENTS_LLM_BACKEND_URL=$BaseUrl")
}
if ($TushareToken) {
    $lines.Add("TUSHARE_TOKEN=$TushareToken")
}
$lines.Add("TRADINGAGENT_MARKETS=A,HK,US")
$lines.Add("TRADINGAGENT_ENABLE_LIVE_TRADING=0")

Set-Content -Path $ConfigPath -Value (($lines -join [Environment]::NewLine) + [Environment]::NewLine) -Encoding UTF8

Write-Host ""
Write-Host "配置完成：$ConfigPath"
Write-Host "供应商：$($Selected.Label)"
Write-Host "模型：$Model"


