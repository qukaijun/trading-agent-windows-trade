from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from agent_host.data_source_registry import record_detection
from agent_host.eodhd_provider import fetch_eodhd_snapshot
from agent_host.fmp_provider import fetch_fmp_snapshot
from agent_host.markets import NormalizedSymbol


@dataclass(frozen=True)
class MarketSnapshot:
    status: str
    source: str
    source_key: str
    symbol: dict[str, str]
    mapped_symbol: str
    latest_date: str = ""
    latest_close: float | None = None
    previous_close: float | None = None
    day_change_pct: float | None = None
    change_5d_pct: float | None = None
    change_20d_pct: float | None = None
    high_20d: float | None = None
    low_20d: float | None = None
    volume_latest: int | None = None
    volume_avg_20d: int | None = None
    rows: int = 0
    message: str = ""
    used_fields: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    data_timestamp: str = ""
    capability_level: str = ""
    roles: tuple[dict[str, str], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_market_snapshot(symbol: NormalizedSymbol, data_source: str = "yfinance") -> dict[str, Any]:
    source_key = (data_source or "yfinance").strip().lower()
    if source_key == "eodhd":
        snapshot = fetch_eodhd_snapshot(symbol)
        record_detection(symbol, source_key, snapshot)
        return snapshot
    if source_key == "fmp":
        snapshot = fetch_fmp_snapshot(symbol)
        record_detection(symbol, source_key, snapshot)
        return snapshot
    snapshot = _get_yfinance_snapshot(symbol)
    record_detection(symbol, source_key, snapshot)
    return snapshot


def _get_yfinance_snapshot(symbol: NormalizedSymbol) -> dict[str, Any]:
    source_name = "yfinance"
    try:
        import yfinance as yf

        frame = yf.Ticker(symbol.yfinance).history(period="3mo", interval="1d", auto_adjust=False)
        if frame is None or frame.empty:
            return MarketSnapshot(
                status="empty",
                source=source_name,
                source_key="yfinance",
                symbol=symbol.to_dict(),
                mapped_symbol=symbol.yfinance,
                message=f"未取到 {symbol.display} 的近 3 个月日线行情。请确认代码、交易市场和网络环境后重试。",
                missing_fields=("日线",),
            ).to_dict()

        frame = frame.dropna(subset=["Close"])
        if frame.empty:
            return MarketSnapshot(
                status="empty",
                source=source_name,
                source_key="yfinance",
                symbol=symbol.to_dict(),
                mapped_symbol=symbol.yfinance,
                message=f"{symbol.display} 行情缺少收盘价字段，暂时无法生成行情快照。",
                missing_fields=("最新价格",),
            ).to_dict()

        close = frame["Close"]
        volume = frame["Volume"] if "Volume" in frame else None
        rows = len(frame.index)
        latest_close = _num(close.iloc[-1])
        previous_close = _num(close.iloc[-2]) if rows >= 2 else None
        latest_date = _date_text(frame.index[-1])
        tail_20 = frame.tail(20)

        return MarketSnapshot(
            status="ok",
            source=source_name,
            source_key="yfinance",
            symbol=symbol.to_dict(),
            mapped_symbol=symbol.yfinance,
            latest_date=latest_date,
            latest_close=latest_close,
            previous_close=previous_close,
            day_change_pct=_pct(latest_close, previous_close),
            change_5d_pct=_period_pct(close, 5),
            change_20d_pct=_period_pct(close, 20),
            high_20d=_num(tail_20["High"].max()) if "High" in tail_20 else None,
            low_20d=_num(tail_20["Low"].min()) if "Low" in tail_20 else None,
            volume_latest=_int(volume.iloc[-1]) if volume is not None and rows >= 1 else None,
            volume_avg_20d=_int(volume.tail(20).mean()) if volume is not None and len(volume.tail(20)) else None,
            rows=rows,
            message=f"已取到 {symbol.display} 的近 3 个月日线行情。",
            used_fields=("最新价格", "日线", "最新交易日", "成交量"),
            missing_fields=("公司资料", "财务", "新闻", "估值指标"),
            data_timestamp=latest_date,
            capability_level="基础行情版",
            roles=tuple(_basic_roles("已获取行情和日线数据")),
        ).to_dict()
    except Exception:  # noqa: BLE001
        return MarketSnapshot(
            status="error",
            source=source_name,
            source_key="yfinance",
            symbol=symbol.to_dict(),
            mapped_symbol=symbol.yfinance,
            message="yfinance 暂时无法访问，可能是网络或第三方服务限制。请稍后重试，或导出诊断包交给服务人员。",
            missing_fields=("最新行情", "日线"),
        ).to_dict()


def format_snapshot_markdown(snapshot: dict[str, Any] | None) -> str:
    if not snapshot:
        return "未生成行情快照。"
    status = snapshot.get("status", "")
    if status != "ok":
        return str(snapshot.get("message") or "行情快照不可用。")

    lines = [
        f"- 主数据源：{snapshot.get('source')}",
        f"- 映射代码：{snapshot.get('mapped_symbol') or '未知'}",
        f"- 数据时间：{snapshot.get('data_timestamp') or snapshot.get('latest_date') or '未知'}",
        f"- 最新价格：{_fmt_number(snapshot.get('latest_close'))}",
        f"- 单日涨跌幅：{_fmt_pct(snapshot.get('day_change_pct'))}",
        f"- 最新成交量：{_fmt_int(snapshot.get('volume_latest'))}",
        f"- 样本行数：{snapshot.get('rows', 0)}",
        f"- 已用字段：{', '.join(snapshot.get('used_fields') or []) or '暂无'}",
        f"- 缺失字段：{', '.join(snapshot.get('missing_fields') or []) or '无'}",
    ]
    return "\n".join(lines)


def _basic_roles(detail: str) -> list[dict[str, str]]:
    return [
        {"name": "市场分析师", "status": "可用", "detail": detail},
        {"name": "技术分析师", "status": "可用", "detail": "可基于日线价格和成交量观察趋势"},
        {"name": "基本面分析师", "status": "字段不足", "detail": "当前主数据源未提供完整财务字段"},
        {"name": "新闻分析师", "status": "字段不足", "detail": "当前主数据源未提供新闻字段"},
        {"name": "风险分析师", "status": "可用", "detail": "可基于价格波动和数据缺口提示风险"},
        {"name": "研究经理", "status": "可用", "detail": "汇总本次基础行情版报告"},
    ]


def _period_pct(close: Any, days: int) -> float | None:
    if len(close) <= days:
        return None
    return _pct(_num(close.iloc[-1]), _num(close.iloc[-days - 1]))


def _pct(new_value: float | None, old_value: float | None) -> float | None:
    if new_value is None or old_value in (None, 0):
        return None
    return round((new_value / old_value - 1) * 100, 2)


def _num(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, 4)


def _int(value: Any) -> int | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return int(number)


def _date_text(value: Any) -> str:
    if hasattr(value, "date"):
        return value.date().isoformat()
    return str(value)


def _fmt_number(value: Any) -> str:
    if value is None:
        return "暂无"
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "暂无"
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return str(value)


def _fmt_int(value: Any) -> str:
    if value is None:
        return "暂无"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)
