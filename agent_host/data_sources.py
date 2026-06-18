from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from agent_host.data_source_registry import all_sources, source_payload_for_symbol, token_configured
from agent_host.markets import NormalizedSymbol, market_name


@dataclass(frozen=True)
class DataSourceCheck:
    key: str
    name: str
    market_names: list[str]
    status: str
    message: str
    abilities: list[str]
    token_required: bool
    token_configured: bool
    report_usable: bool
    checked_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_data_sources(symbol: NormalizedSymbol, data_source: str | None = None) -> dict[str, Any]:
    selected = [source for source in all_sources() if not data_source or source.key == data_source]
    checks = [_check_static_source(source) for source in selected]
    payload = source_payload_for_symbol(symbol)
    return {
        "symbol": symbol.to_dict(),
        "market_name": market_name(symbol.market),
        "checks": [check.to_dict() for check in checks],
        "sources": payload,
        "ok": any(check.status in {"可用", "已配置"} for check in checks),
    }


def _check_static_source(source: Any) -> DataSourceCheck:
    configured = token_configured(source)
    if source.token_required and not configured:
        status = "需配置"
        message = f"{source.name} 需要 Token，配置后才能用于检测或报告生成。"
    elif source.report_usable:
        status = "可用"
        message = source.recommended_for or f"{source.name} 可用于当前支持的报告路径。"
    else:
        status = "后续评估"
        message = source.recommended_for or f"{source.name} 当前仅展示状态，本轮不作为报告主源。"
    return DataSourceCheck(
        key=source.key,
        name=source.name,
        market_names=[market_name(item) for item in source.markets],
        status=status,
        message=message,
        abilities=list(source.abilities),
        token_required=source.token_required,
        token_configured=configured,
        report_usable=source.report_usable,
        checked_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
