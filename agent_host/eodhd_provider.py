from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agent_host.data_source_registry import first_token, get_source
from agent_host.markets import NormalizedSymbol, symbol_for_provider
from agent_host.provider_utils import customer_error_message, get_json


BASE_URL = "https://eodhd.com/api"


def fetch_eodhd_snapshot(symbol: NormalizedSymbol) -> dict[str, Any]:
    source = get_source("eodhd")
    token = first_token(source) if source else ""
    mapped_symbol = symbol_for_provider(symbol, "eodhd")
    base = _base_payload(symbol, mapped_symbol)
    if not token:
        return {
            **base,
            "status": "blocked",
            "message": "EODHD 尚未配置 Token，无法生成报告。请先完成数据源配置。",
            "missing_fields": ["Token"],
        }

    quote_status, quote, quote_error = get_json(f"{BASE_URL}/real-time/{mapped_symbol}", {"api_token": token, "fmt": "json"})
    if quote_status != 200 or not isinstance(quote, dict) or not quote:
        return {
            **base,
            "status": "error",
            "message": customer_error_message("EODHD", quote_status, quote_error),
            "missing_fields": ["最新行情", "日线"],
            "data_timestamp": _checked_at(),
        }

    eod_status, eod, eod_error = get_json(
        f"{BASE_URL}/eod/{mapped_symbol}",
        {"api_token": token, "fmt": "json", "period": "d", "from": "2026-06-01"},
    )
    if eod_status != 200 or not isinstance(eod, list) or not eod:
        return {
            **base,
            "status": "error",
            "message": customer_error_message("EODHD", eod_status, eod_error),
            "missing_fields": ["日线"],
            "data_timestamp": _checked_at(),
        }

    latest_eod = eod[-1] if _is_ascending(eod) else eod[0]
    close = _num(quote.get("close") or latest_eod.get("close"))
    previous_close = _num(quote.get("previousClose"))
    used = ["最新价格", "前收盘价", "成交量", "日线", "最新交易日"]
    missing = ["公司资料", "财务", "新闻", "估值指标"]
    return {
        **base,
        "status": "ok",
        "message": "EODHD 已返回最新行情和日线数据，可生成基础行情版报告。",
        "latest_date": str(latest_eod.get("date") or quote.get("timestamp") or ""),
        "latest_close": close,
        "previous_close": previous_close,
        "day_change_pct": _pct(close, previous_close),
        "volume_latest": _int(quote.get("volume") or latest_eod.get("volume")),
        "rows": len(eod),
        "used_fields": used,
        "missing_fields": missing,
        "quote": quote,
        "daily": eod,
        "data_timestamp": str(quote.get("timestamp") or latest_eod.get("date") or ""),
        "capability_level": "基础行情版",
        "roles": _roles(used, missing),
    }


def _base_payload(symbol: NormalizedSymbol, mapped_symbol: str) -> dict[str, Any]:
    return {
        "source": "EODHD",
        "source_key": "eodhd",
        "symbol": symbol.to_dict(),
        "mapped_symbol": mapped_symbol,
        "used_fields": [],
        "missing_fields": [],
        "data_timestamp": "",
        "capability_level": "基础行情版",
    }


def _checked_at() -> str:
    return f"检测时间：{datetime.now(timezone.utc).isoformat(timespec='seconds')}"


def _is_ascending(rows: list[dict[str, Any]]) -> bool:
    if len(rows) < 2:
        return True
    return str(rows[0].get("date", "")) <= str(rows[-1].get("date", ""))


def _roles(used: list[str], missing: list[str]) -> list[dict[str, str]]:
    return [
        {"name": "市场分析师", "status": "可用", "detail": "已获取行情和日线数据"},
        {"name": "技术分析师", "status": "可用", "detail": "可基于日线价格和成交量观察趋势"},
        {"name": "基本面分析师", "status": "字段不足", "detail": "当前主数据源未提供完整财务和公司资料"},
        {"name": "新闻分析师", "status": "字段不足", "detail": "当前主数据源未提供新闻字段"},
        {"name": "风险分析师", "status": "可用", "detail": "可基于价格波动和数据缺口给出风险提示"},
        {"name": "研究经理", "status": "可用", "detail": "汇总本次基础行情版报告"},
    ]


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
