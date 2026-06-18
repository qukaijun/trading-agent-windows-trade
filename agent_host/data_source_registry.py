from __future__ import annotations

import os
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_host.markets import NormalizedSymbol, market_name, symbol_for_provider


CONFIG_PATH = Path.home() / ".trading-agent-assistant" / ".env"
ROOT = Path(__file__).resolve().parents[1]
CHECK_CACHE_PATH = ROOT / "runtime" / "data_source_checks.json"


@dataclass(frozen=True)
class DataSourceCapability:
    key: str
    name: str
    markets: tuple[str, ...]
    status: str
    abilities: tuple[str, ...]
    token_required: bool
    token_envs: tuple[str, ...] = ()
    report_usable: bool = False
    recommended_for: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["markets"] = list(self.markets)
        data["market_names"] = [market_name(item) for item in self.markets]
        data["abilities"] = list(self.abilities)
        data["token_envs"] = list(self.token_envs)
        data["token_configured"] = token_configured(self)
        data["runtime_status"] = runtime_status(self)
        return data


DATA_SOURCES: tuple[DataSourceCapability, ...] = (
    DataSourceCapability("akshare", "Akshare", ("A", "HK"), "已集成", ("行情", "日线", "指标"), False, report_usable=False, recommended_for="A股/港股公开数据补充，本轮不作为 PDD 演示主源。"),
    DataSourceCapability("tushare", "Tushare Pro", ("A",), "需 Token", ("行情", "日线", "公司资料", "财务"), True, ("TUSHARE_TOKEN",), report_usable=False, recommended_for="A股增强数据，本轮不作为 PDD 演示主源。"),
    DataSourceCapability("yfinance", "yfinance", ("HK", "US", "CRYPTO", "COMMODITY"), "已集成", ("行情", "日线"), False, report_usable=True, recommended_for="美股/港股/加密货币/贵金属基础行情候选源；受网络和第三方限制影响。"),
    DataSourceCapability("alpha_vantage", "Alpha Vantage", ("US",), "需 Token", ("行情", "日线", "公司资料", "技术指标"), True, ("ALPHA_VANTAGE_API_KEY",), report_usable=False, recommended_for="美股候选源，本轮仅展示状态。"),
    DataSourceCapability("eodhd", "EODHD", ("US",), "需复测", ("行情", "日线"), True, ("EODHD_API_KEY", "EOD_API_KEY"), report_usable=True, recommended_for="历史曾测通 PDD.US 行情/日线；当前 PDD 路径需重新检测通过后才能作为主源。", note="最新 PDD 真实复测未通过，不能仅凭历史测通视为当前可交付。"),
    DataSourceCapability("fmp", "FMP", ("US",), "部分可用", ("行情", "日线", "公司资料", "财务", "关键指标"), True, ("FMP_API_KEY", "FINANCIAL_MODELING_PREP_API_KEY"), report_usable=True, recommended_for="NVDA/TSM 等标的较完整基础报告候选源；PDD 当前套餐权限不足。", note="必须使用 /stable/... 新接口；PDD quote/history/financial 当前返回权限不足。"),
    DataSourceCapability("twelve_data", "Twelve Data", ("US",), "已测通", ("行情", "日线"), True, ("TWELVE_DATA_API_KEY", "TWELVEDATA_API_KEY"), report_usable=False, recommended_for="美股行情候选源，本轮不作为 PDD 主报告源。"),
)


def all_sources() -> list[DataSourceCapability]:
    return list(DATA_SOURCES)


def get_source(key: str) -> DataSourceCapability | None:
    normalized = (key or "").strip().lower()
    for source in DATA_SOURCES:
        if source.key == normalized:
            return source
    return None


def sources_for_market(market: str) -> list[DataSourceCapability]:
    return [source for source in DATA_SOURCES if market in source.markets]


def report_sources_for_market(market: str) -> list[DataSourceCapability]:
    return [source for source in sources_for_market(market) if source.report_usable]


def validate_source_for_symbol(symbol: NormalizedSymbol, source_key: str) -> tuple[bool, str]:
    source = get_source(source_key)
    if not source:
        return False, "请选择一个可用的数据源。"
    if symbol.market not in source.markets:
        return False, f"当前标的识别为{market_name(symbol.market)}，不能使用{source.name}生成报告。请切换为{market_name(symbol.market)}数据源。"
    if source.token_required and not token_configured(source):
        return False, f"{source.name} 尚未配置 Token，无法生成报告。请先完成数据源配置或选择其他可用数据源。"
    known = known_symbol_block(symbol, source.key)
    if known:
        return False, known
    if not source.report_usable:
        return False, f"{source.name} 当前仅用于状态展示或后续评估，暂不能作为本次报告主数据源。"
    return True, ""


def audit_snapshot_for_block(
    symbol: NormalizedSymbol,
    source_key: str,
    message: str,
    *,
    status: str = "blocked",
    used_fields: list[str] | None = None,
    missing_fields: list[str] | None = None,
    data_timestamp: str = "",
) -> dict[str, Any]:
    source = get_source(source_key)
    source_name = source.name if source else (source_key or "未选择")
    mapped_symbol = symbol_for_provider(symbol, source_key) if source else symbol.canonical
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "status": status,
        "source": source_name,
        "source_key": source_key,
        "symbol": symbol.to_dict(),
        "mapped_symbol": mapped_symbol,
        "message": message,
        "used_fields": used_fields or [],
        "missing_fields": missing_fields if missing_fields is not None else missing_fields_for_block(symbol, source_key, message),
        "data_timestamp": data_timestamp or f"检测时间：{checked_at}",
        "checked_at": checked_at,
        "capability_level": "阻断：当前数据源不满足本次报告最低要求",
    }


def missing_fields_for_block(symbol: NormalizedSymbol, source_key: str, message: str) -> list[str]:
    lower = message.lower()
    if "token" in lower:
        return ["Token", "最新行情", "日线", "最新交易日"]
    if source_key == "fmp" and symbol.market == "US" and symbol.canonical.upper() == "PDD":
        return ["最新行情", "日线", "财务", "关键指标"]
    if "网络" in message or "无法访问" in message:
        return ["最新行情", "日线", "最新交易日"]
    if "权限" in message or "订阅" in message:
        return ["最新行情", "日线", "财务", "关键指标"]
    if "市场" in message or "不能使用" in message:
        return ["匹配市场的数据源"]
    return ["报告最低字段"]


def source_payload_for_symbol(symbol: NormalizedSymbol) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {"A": [], "HK": [], "US": []}
    for source in DATA_SOURCES:
        item = source.to_dict()
        item["mapped_symbol"] = symbol_for_provider(symbol, source.key) if symbol.market in source.markets else ""
        selectable, reason, status = selectability_for_symbol(symbol, source)
        item["selectable_for_current_symbol"] = selectable
        item["selectable_reason"] = reason
        item["current_symbol_status"] = status
        item["last_check"] = last_check_for_symbol(symbol, source.key)
        for market in source.markets:
            grouped.setdefault(market, []).append(item)
    return {
        "symbol": symbol.to_dict(),
        "market_name": market_name(symbol.market),
        "grouped": grouped,
        "available_for_report": [
            source.to_dict()
            for source in report_sources_for_market(symbol.market)
            if selectability_for_symbol(symbol, source)[0]
        ],
    }


def selectability_for_symbol(symbol: NormalizedSymbol, source: DataSourceCapability) -> tuple[bool, str, str]:
    if symbol.market not in source.markets:
        return False, f"当前标的是{market_name(symbol.market)}，该数据源不支持该市场。", "市场不匹配"
    if not source.report_usable:
        return False, "该数据源本轮仅用于状态展示或后续评估，不能作为报告主源。", "暂不可用于报告"
    if source.token_required and not token_configured(source):
        return False, "尚未配置 Token，配置并检测通过后才能作为本次报告主源。", "需配置 Token"
    known = known_symbol_block(symbol, source.key)
    if known:
        return False, known, "权限不足"
    cached = last_check_for_symbol(symbol, source.key)
    if cached:
        status = str(cached.get("status") or "")
        message = str(cached.get("message") or "")
        checked_at = str(cached.get("checked_at") or "")
        if status == "ok":
            return True, f"最近检测通过：{checked_at}", "可用于本次报告"
        return False, f"最近检测未通过：{message or '请重新检测'}", "需重新检测"
    if source.token_required:
        return False, "已配置 Token，但当前标的尚未检测通过；请先检测数据源。", "需重新检测"
    return True, "无需 Token，可尝试用于基础行情报告。", "可尝试"


def known_symbol_block(symbol: NormalizedSymbol, source_key: str) -> str:
    canonical = symbol.canonical.upper()
    if source_key == "fmp" and symbol.market == "US" and canonical == "PDD":
        return "FMP 当前订阅权限不足，不能作为 PDD 本次报告主数据源。"
    return ""


def record_detection(symbol: NormalizedSymbol, source_key: str, snapshot: dict[str, Any]) -> None:
    source = get_source(source_key)
    if not source:
        return
    cache = _read_check_cache()
    key = _check_key(symbol, source_key)
    cache[key] = {
        "source_key": source_key,
        "source_name": source.name,
        "symbol": symbol.to_dict(),
        "mapped_symbol": snapshot.get("mapped_symbol") or symbol_for_provider(symbol, source_key),
        "status": snapshot.get("status") or "unknown",
        "message": snapshot.get("message") or "",
        "used_fields": snapshot.get("used_fields") or [],
        "missing_fields": snapshot.get("missing_fields") or [],
        "data_timestamp": snapshot.get("data_timestamp") or snapshot.get("latest_date") or "",
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    _write_check_cache(cache)


def last_check_for_symbol(symbol: NormalizedSymbol, source_key: str) -> dict[str, Any] | None:
    cache = _read_check_cache()
    item = cache.get(_check_key(symbol, source_key))
    return item if isinstance(item, dict) else None


def token_configured(source: DataSourceCapability) -> bool:
    if not source.token_required:
        return True
    return any(bool(_config_value(env_name)) for env_name in source.token_envs)


def first_token(source: DataSourceCapability) -> str:
    for env_name in source.token_envs:
        value = _config_value(env_name)
        if value:
            return value
    return ""


def runtime_status(source: DataSourceCapability) -> str:
    if source.token_required and not token_configured(source):
        return "需配置 Token"
    if source.key == "fmp":
        return "已配置，NVDA/TSM 可用于较完整基础报告；PDD 当前权限不足"
    if source.key == "eodhd":
        return "已配置；PDD 当前需重新检测，不能仅凭历史测通视为可交付"
    if source.key == "twelve_data":
        return "已配置，行情类候选源"
    return source.status


def _check_key(symbol: NormalizedSymbol, source_key: str) -> str:
    mapped = symbol_for_provider(symbol, source_key)
    return f"{source_key}|{symbol.market}|{mapped.upper()}"


def _read_check_cache() -> dict[str, Any]:
    if not CHECK_CACHE_PATH.exists():
        return {}
    try:
        data = json.loads(CHECK_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return data if isinstance(data, dict) else {}


def _write_check_cache(cache: dict[str, Any]) -> None:
    CHECK_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECK_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _config_value(key: str) -> str:
    value = os.getenv(key, "").strip()
    if value:
        return value
    if not CONFIG_PATH.exists():
        return ""
    try:
        for raw_line in CONFIG_PATH.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            env_key, env_value = line.split("=", 1)
            if env_key.strip() == key:
                return env_value.strip()
    except OSError:
        return ""
    return ""
