from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


CONFIG_DIR = Path.home() / ".trading-agent-assistant"
CONFIG_PATH = CONFIG_DIR / ".env"


@dataclass(frozen=True)
class ConfigProvider:
    key: str
    label: str
    api_key_env: str
    base_url_env: str
    default_model: str
    default_base_url: str
    requires_key: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


PROVIDERS = [
    ConfigProvider("qwen-cn", "通义千问 / DashScope", "DASHSCOPE_CN_API_KEY", "DASHSCOPE_CN_BASE_URL", "qwen-plus-latest", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    ConfigProvider("deepseek", "DeepSeek", "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "deepseek-chat", "https://api.deepseek.com/v1"),
    ConfigProvider("openai", "OpenAI", "OPENAI_API_KEY", "OPENAI_BASE_URL", "gpt-5.5-instant", "https://api.openai.com/v1"),
    ConfigProvider("openrouter", "OpenRouter", "OPENROUTER_API_KEY", "OPENROUTER_BASE_URL", "deepseek/deepseek-chat", "https://openrouter.ai/api/v1"),
    ConfigProvider("custom-openai", "自定义 OpenAI 兼容接口", "CUSTOM_OPENAI_API_KEY", "CUSTOM_OPENAI_BASE_URL", "your-model-name", "https://your-endpoint.example.com/v1"),
    ConfigProvider("ollama", "Ollama 本地模型", "", "OLLAMA_BASE_URL", "qwen2.5:14b", "http://localhost:11434/v1", requires_key=False),
]

SERVICE_ENV_KEYS = {
    "service_provider": "TRADINGAGENT_SERVICE_PROVIDER",
    "service_name": "TRADINGAGENT_SERVICE_NAME",
    "support_contact": "TRADINGAGENT_SUPPORT_CONTACT",
    "support_email": "TRADINGAGENT_SUPPORT_EMAIL",
    "support_wechat": "TRADINGAGENT_SUPPORT_WECHAT",
    "service_note": "TRADINGAGENT_SERVICE_NOTE",
}

DATA_TOKEN_KEYS = {
    "eodhd_api_key": "EODHD_API_KEY",
    "fmp_api_key": "FMP_API_KEY",
    "alpha_vantage_api_key": "ALPHA_VANTAGE_API_KEY",
    "tushare_token": "TUSHARE_TOKEN",
}


def providers_payload() -> list[dict[str, Any]]:
    return [provider.to_dict() for provider in PROVIDERS]


def resolve_connection_config(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    saved = _read_env_file()
    provider_key = str(payload.get("provider") or saved.get("TRADINGAGENT_DISPLAY_PROVIDER") or saved.get("TRADINGAGENTS_LLM_PROVIDER") or "qwen-cn").strip()
    selected = _find_provider(provider_key) or _find_provider("qwen-cn")
    if not selected:
        raise ValueError(f"不支持的模型供应商：{provider_key}")

    model = str(payload.get("model") or saved.get("TRADINGAGENTS_DEEP_THINK_LLM") or selected.default_model).strip()
    base_url = str(payload.get("base_url") or _current_base_url(saved, selected) or selected.default_base_url).strip()
    api_key = str(payload.get("api_key") or "").strip()
    if not api_key and selected.api_key_env:
        api_key = saved.get(selected.api_key_env, "")

    return {
        "provider": selected.key,
        "label": selected.label,
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
        "api_key_env": selected.api_key_env,
        "requires_key": selected.requires_key,
    }


def read_config_status() -> dict[str, Any]:
    values = _read_env_file()
    provider = values.get("TRADINGAGENT_DISPLAY_PROVIDER") or values.get("TRADINGAGENTS_LLM_PROVIDER", "")
    selected = _find_provider(provider) or _find_provider("qwen-cn")
    api_key_env = selected.api_key_env if selected else ""
    api_key = values.get(api_key_env, "") if api_key_env else ""
    return {
        "config_path": str(CONFIG_PATH),
        "exists": CONFIG_PATH.exists(),
        "provider": provider or "",
        "runtime_provider": values.get("TRADINGAGENTS_LLM_PROVIDER", ""),
        "model": values.get("TRADINGAGENTS_DEEP_THINK_LLM", ""),
        "base_url": _current_base_url(values, selected),
        "api_key_env": api_key_env,
        "api_key_configured": bool(api_key) or (selected.requires_key is False if selected else False),
        "api_key_preview": _mask_secret(api_key),
        "markets": values.get("TRADINGAGENT_MARKETS", "A,HK,US"),
        "output_language": values.get("TRADINGAGENTS_OUTPUT_LANGUAGE", "简体中文"),
        "data_tokens": {
            "eodhd": bool(values.get("EODHD_API_KEY") or values.get("EOD_API_KEY")),
            "fmp": bool(values.get("FMP_API_KEY") or values.get("FINANCIAL_MODELING_PREP_API_KEY")),
            "alpha_vantage": bool(values.get("ALPHA_VANTAGE_API_KEY")),
            "tushare": bool(values.get("TUSHARE_TOKEN")),
        },
        "service": read_service_config(values),
    }


def read_service_config(values: dict[str, str] | None = None) -> dict[str, str]:
    env_values = values if values is not None else _read_env_file()
    return {key: env_values.get(env_name, "") for key, env_name in SERVICE_ENV_KEYS.items()}


def save_web_config(payload: dict[str, Any]) -> dict[str, Any]:
    provider_key = str(payload.get("provider") or "qwen-cn").strip()
    selected = _find_provider(provider_key)
    if not selected:
        raise ValueError(f"不支持的模型供应商：{provider_key}")

    model = str(payload.get("model") or selected.default_model).strip()
    base_url = str(payload.get("base_url") or selected.default_base_url).strip()
    api_key = str(payload.get("api_key") or "").strip()
    keep_existing_key = bool(payload.get("keep_existing_key", True))
    old_values = _read_env_file()

    lines: list[str] = [
        f"TRADINGAGENTS_LLM_PROVIDER={selected.key}",
        f"TRADINGAGENT_DISPLAY_PROVIDER={selected.key}",
        f"TRADINGAGENTS_DEEP_THINK_LLM={model}",
        f"TRADINGAGENTS_QUICK_THINK_LLM={model}",
        "TRADINGAGENTS_OUTPUT_LANGUAGE=简体中文",
        "TRADINGAGENTS_MAX_DEBATE_ROUNDS=1",
        "TRADINGAGENTS_MAX_RISK_ROUNDS=1",
        "TRADINGAGENTS_TEMPERATURE=0.0",
    ]

    _append_secret(lines, selected.api_key_env, api_key, old_values, keep_existing_key)
    if selected.base_url_env and base_url:
        lines.append(f"{selected.base_url_env}={base_url}")
        lines.append(f"TRADINGAGENTS_LLM_BACKEND_URL={base_url}")

    for payload_key, env_name in DATA_TOKEN_KEYS.items():
        value = str(payload.get(payload_key) or "").strip()
        _append_secret(lines, env_name, value, old_values, keep_existing_key)

    service = payload.get("service") if isinstance(payload.get("service"), dict) else {}
    for key, env_name in SERVICE_ENV_KEYS.items():
        value = str(service.get(key) if key in service else old_values.get(env_name, "")).strip()
        if value:
            lines.append(f"{env_name}={value}")

    lines.extend(["TRADINGAGENT_MARKETS=A,HK,US", "TRADINGAGENT_ENABLE_LIVE_TRADING=0"])
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return read_config_status()


def _append_secret(lines: list[str], env_name: str, new_value: str, old_values: dict[str, str], keep_existing: bool) -> None:
    if not env_name:
        return
    if new_value:
        lines.append(f"{env_name}={new_value}")
    elif keep_existing and old_values.get(env_name):
        lines.append(f"{env_name}={old_values[env_name]}")


def _read_env_file() -> dict[str, str]:
    if not CONFIG_PATH.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in CONFIG_PATH.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _find_provider(key: str) -> ConfigProvider | None:
    for provider in PROVIDERS:
        if provider.key == key:
            return provider
    return None


def _current_base_url(values: dict[str, str], provider: ConfigProvider | None) -> str:
    if provider and provider.base_url_env and values.get(provider.base_url_env):
        return values[provider.base_url_env]
    return values.get("TRADINGAGENTS_LLM_BACKEND_URL", "")


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"
