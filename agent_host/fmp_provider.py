from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agent_host.data_source_registry import first_token, get_source
from agent_host.markets import NormalizedSymbol, symbol_for_provider
from agent_host.provider_utils import customer_error_message, get_json


BASE_URL = "https://financialmodelingprep.com/stable"


def fetch_fmp_snapshot(symbol: NormalizedSymbol) -> dict[str, Any]:
    source = get_source("fmp")
    token = first_token(source) if source else ""
    mapped_symbol = symbol_for_provider(symbol, "fmp")
    base = _base_payload(symbol, mapped_symbol)
    if not token:
        return {
            **base,
            "status": "blocked",
            "message": "FMP 尚未配置 Token，无法生成报告。请先完成数据源配置。",
            "missing_fields": ["Token"],
        }

    quote_status, quote_data, quote_error = get_json(f"{BASE_URL}/quote", {"symbol": mapped_symbol, "apikey": token})
    quote = _first_dict(quote_data)
    if quote_status != 200 or not quote or _looks_like_error(quote):
        return _blocked(base, quote_status, quote_error, quote_data)

    profile_status, profile_data, profile_error = get_json(f"{BASE_URL}/profile", {"symbol": mapped_symbol, "apikey": token})
    profile = _first_dict(profile_data)
    history_status, history_data, history_error = get_json(f"{BASE_URL}/historical-price-eod/full", {"symbol": mapped_symbol, "apikey": token, "from": "2026-06-01"})
    history = history_data if isinstance(history_data, list) else []
    income_status, income_data, income_error = get_json(f"{BASE_URL}/income-statement", {"symbol": mapped_symbol, "apikey": token, "period": "annual", "limit": 1})
    income = _first_dict(income_data)
    metrics_status, metrics_data, metrics_error = get_json(f"{BASE_URL}/key-metrics", {"symbol": mapped_symbol, "apikey": token, "period": "annual", "limit": 1})
    metrics = _first_dict(metrics_data)

    failed = [
        item for item in [
            (profile_status, profile_error, profile_data, "公司资料"),
            (history_status, history_error, history_data, "日线"),
            (income_status, income_error, income_data, "财务"),
            (metrics_status, metrics_error, metrics_data, "关键指标"),
        ]
        if item[0] != 200 or _looks_like_error(_first_dict(item[2]))
    ]
    if failed and mapped_symbol.upper() == "PDD":
        status_code, error, payload, field = failed[0]
        return {
            **base,
            "status": "blocked",
            "message": f"FMP 当前订阅权限不足，无法获取 PDD 的{field}等报告字段。请切换 EODHD 生成基础行情版，或升级 FMP 套餐后重试。",
            "used_fields": ["公司资料"] if profile else [],
            "missing_fields": ["最新行情", "日线", "财务", "关键指标"],
            "capability_level": "不可用于 PDD 本次报告",
            "data_timestamp": _checked_at(),
        }
    if failed:
        status_code, error, payload, field = failed[0]
        return {
            **base,
            "status": "error",
            "message": customer_error_message("FMP", status_code, error),
            "missing_fields": [field],
            "data_timestamp": _checked_at(),
        }

    latest_history = history[-1] if history else {}
    close = _num(quote.get("price") or quote.get("close") or latest_history.get("close"))
    previous_close = _num(quote.get("previousClose"))
    used = ["最新价格", "前收盘价", "成交量", "日线", "最新交易日", "公司资料", "财务", "关键指标"]
    missing = ["新闻"]
    return {
        **base,
        "status": "ok",
        "message": "FMP 已返回行情、公司资料、日线、财务和关键指标，可生成较完整基础报告。",
        "latest_date": str(latest_history.get("date") or quote.get("timestamp") or ""),
        "latest_close": close,
        "previous_close": previous_close,
        "day_change_pct": _pct(close, previous_close),
        "volume_latest": _int(quote.get("volume")),
        "rows": len(history),
        "used_fields": used,
        "missing_fields": missing,
        "quote": quote,
        "profile": profile,
        "daily": history,
        "income": income,
        "metrics": metrics,
        "data_timestamp": str(quote.get("timestamp") or latest_history.get("date") or ""),
        "capability_level": "较完整基础报告",
        "roles": _roles(used, missing),
    }


def _base_payload(symbol: NormalizedSymbol, mapped_symbol: str) -> dict[str, Any]:
    return {
        "source": "FMP",
        "source_key": "fmp",
        "symbol": symbol.to_dict(),
        "mapped_symbol": mapped_symbol,
        "used_fields": [],
        "missing_fields": [],
        "data_timestamp": "",
        "capability_level": "较完整基础报告",
    }


def _blocked(base: dict[str, Any], status_code: int, error: str, payload: Any) -> dict[str, Any]:
    mapped_symbol = str(base.get("mapped_symbol") or "")
    if mapped_symbol.upper() == "PDD":
        message = "FMP 当前订阅权限不足，无法获取 PDD 的行情、历史或财务字段。请切换 EODHD 生成基础行情版，或升级 FMP 套餐后重试。"
    else:
        message = customer_error_message("FMP", status_code, error)
    return {
        **base,
        "status": "blocked",
        "message": message,
        "missing_fields": ["最新行情", "日线", "财务", "关键指标"],
        "data_timestamp": _checked_at(),
    }


def _checked_at() -> str:
    return f"检测时间：{datetime.now(timezone.utc).isoformat(timespec='seconds')}"


def _roles(used: list[str], missing: list[str]) -> list[dict[str, str]]:
    return [
        {"name": "市场分析师", "status": "可用", "detail": "已获取行情和日线数据"},
        {"name": "技术分析师", "status": "可用", "detail": "可基于历史价格观察趋势"},
        {"name": "基本面分析师", "status": "可用", "detail": "已获取公司资料、财务和关键指标"},
        {"name": "新闻分析师", "status": "字段不足", "detail": "当前主数据源未提供新闻字段"},
        {"name": "风险分析师", "status": "可用", "detail": "可结合价格波动、财务字段和数据缺口提示风险"},
        {"name": "研究经理", "status": "可用", "detail": "汇总本次较完整基础报告"},
    ]


def _first_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    if isinstance(value, dict):
        return value
    return {}


def _looks_like_error(value: dict[str, Any]) -> bool:
    if not value:
        return False
    error_keys = {"error", "Error Message", "message", "Message"}
    text = " ".join(str(value.get(key, "")) for key in error_keys if key in value).lower()
    return any(word in text for word in ["restricted", "subscription", "not available", "forbidden", "limit"])


def _num(value: Any) -> float | None:
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _pct(new_value: float | None, old_value: float | None) -> float | None:
    if new_value is None or old_value in (None, 0):
        return None
    return round((new_value / old_value - 1) * 100, 2)
