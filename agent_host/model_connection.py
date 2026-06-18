from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from agent_host.config_manager import resolve_connection_config


def test_model_connection(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    config = resolve_connection_config(payload)
    if config["requires_key"] and not config["api_key"]:
        return {
            "status": "error",
            "provider": config["provider"],
            "model": config["model"],
            "message": "模型尚未配置 API Key。请先填写并保存模型配置，再测试连接。",
        }

    url = _chat_completions_url(str(config["base_url"]))
    body = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": "You are a connection test assistant."},
            {"role": "user", "content": "Reply with OK."},
        ],
        "temperature": 0,
        "max_tokens": 8,
    }
    headers = {"Content-Type": "application/json"}
    if config["api_key"]:
        headers["Authorization"] = f"Bearer {config['api_key']}"

    started = time.perf_counter()
    try:
        request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8", errors="replace")
            data = json.loads(raw) if raw else {}
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "status": "ok",
            "provider": config["provider"],
            "model": config["model"],
            "latency_ms": latency_ms,
            "message": "模型连接测试通过。",
            "reply_preview": _reply_preview(data),
        }
    except urllib.error.HTTPError:
        return _error_result(config, "模型服务返回错误，请检查 API Key、模型名称、服务地址或账号状态。")
    except Exception as exc:  # noqa: BLE001
        return _error_result(config, "模型连接失败，可能是网络、模型名称或 API Key 不可用。请检查配置，或导出诊断包交给服务人员。", detail=str(exc))


def _chat_completions_url(base_url: str) -> str:
    cleaned = base_url.strip().rstrip("/")
    if cleaned.endswith("/chat/completions"):
        return cleaned
    return f"{cleaned}/chat/completions"


def _reply_preview(data: dict[str, Any]) -> str:
    try:
        choices = data.get("choices") or []
        message = choices[0].get("message") or {}
        content = message.get("content") or ""
        return str(content)[:120]
    except Exception:  # noqa: BLE001
        return ""


def _error_result(config: dict[str, Any], message: str, detail: str = "") -> dict[str, Any]:
    return {
        "status": "error",
        "provider": config["provider"],
        "model": config["model"],
        "message": message,
        "technical_detail": detail[:1200],
    }
