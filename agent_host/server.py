from __future__ import annotations
import os

from pathlib import Path

from dotenv import load_dotenv
from fastapi import Body, FastAPI, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from agent_host.app_meta import APP_VERSION, about_payload
from agent_host.capabilities import capabilities_payload, current_runtime
from agent_host.config_manager import providers_payload, read_config_status, resolve_connection_config, save_web_config
from agent_host.data_source_registry import audit_snapshot_for_block, source_payload_for_symbol, validate_source_for_symbol
from agent_host.data_sources import check_data_sources
from agent_host.diagnostics import build_diagnostics, diagnostics_text
from agent_host.market_snapshot import get_market_snapshot
from agent_host.markets import normalize_symbol
from agent_host.model_connection import test_model_connection
from agent_host.mt5_bridge import clear_signal, get_signal, save_signal
from agent_host.report_export import export_filename, export_report_docx, export_report_pdf
from agent_host.report_store import get_report_markdown, get_report_record, list_report_records
from agent_host.runner import analyze_with_tradingagents, upstream_status
from agent_host.ui import render_home


CONFIG_PATH = Path.home() / ".trading-agent-assistant" / ".env"
if CONFIG_PATH.exists():
    load_dotenv(CONFIG_PATH, override=True)

app = FastAPI(title="TradingAgents 中文服务工作台", version=APP_VERSION)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "TradingAgents 中文服务工作台"}


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return render_home(current_runtime())


@app.get("/api/capabilities")
def capabilities_api() -> dict[str, object]:
    return capabilities_payload()


@app.get("/api/about")
def about_api() -> dict[str, object]:
    return about_payload(read_config_status().get("service", {}))


@app.get("/api/diagnostics")
def diagnostics_api() -> dict[str, object]:
    return build_diagnostics()


@app.get("/api/diagnostics.txt", response_class=PlainTextResponse)
@app.get("/api/mt5/config")
def mt5_config_api() -> dict[str, object]:
    """查看 MT5 实盘配置状态。"""
    return {
        "live_enabled": os.getenv("MT5_LIVE_TRADING_ENABLED", "0") == "1",
        "max_live_volume": float(os.getenv("MT5_MAX_LIVE_VOLUME", "0.01")),
        "current_signal": get_signal().to_dict(),
    }

@app.get("/api/diagnostics.txt", response_class=PlainTextResponse)
def diagnostics_text_api() -> str:
    return diagnostics_text()


@app.get("/api/config")
def config_api() -> dict[str, object]:
    return {"config": read_config_status(), "providers": providers_payload()}


@app.post("/api/config")
def save_config_api(payload: dict[str, object] = Body(...)) -> dict[str, object]:
    try:
        config = save_web_config(payload)
        load_dotenv(CONFIG_PATH, override=True)
        return {"status": "ok", "config": config}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/config/test-model")
def test_model_config_api(payload: dict[str, object] = Body(default_factory=dict)) -> dict[str, object]:
    return test_model_connection(payload)


@app.get("/api/normalize-symbol")
def normalize_symbol_api(symbol: str = Query(..., description="股票代码或名称")) -> dict[str, object]:
    return normalize_symbol(symbol).to_dict()


@app.get("/api/upstream-status")
def upstream_status_api() -> dict[str, object]:
    return upstream_status()


@app.get("/api/data-check")
def data_check_api(
    symbol: str = Query(..., description="股票代码或名称"),
    data_source: str | None = Query(None, description="指定数据源"),
) -> dict[str, object]:
    normalized = normalize_symbol(symbol)
    return check_data_sources(normalized, data_source=data_source)


@app.get("/api/data-sources")
def data_sources_api(symbol: str = Query("PDD", description="股票代码或名称")) -> dict[str, object]:
    normalized = normalize_symbol(symbol)
    return source_payload_for_symbol(normalized)


@app.get("/api/market-snapshot")
def market_snapshot_api(
    symbol: str = Query(..., description="股票代码或名称"),
    data_source: str = Query("yfinance", description="主数据源"),
) -> dict[str, object]:
    normalized = normalize_symbol(symbol)
    ok, message = validate_source_for_symbol(normalized, data_source)
    if not ok:
        return audit_snapshot_for_block(normalized, data_source, message)
    return get_market_snapshot(normalized, data_source)


@app.get("/api/reports")
def reports_api(limit: int = 30) -> dict[str, object]:
    return list_report_records(limit=limit)


@app.get("/api/reports/{report_id}.md", response_class=PlainTextResponse)
def report_markdown_api(report_id: str) -> str:
    markdown = get_report_markdown(report_id)
    if markdown is None:
        raise HTTPException(status_code=404, detail="报告不存在。")
    return markdown


@app.get("/api/reports/{report_id}.docx")
def report_docx_api(report_id: str) -> Response:
    record = get_report_record(report_id)
    markdown = get_report_markdown(report_id)
    if not record or markdown is None:
        raise HTTPException(status_code=404, detail="报告不存在。")
    try:
        content = export_report_docx(markdown)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    filename = export_filename(record, "docx")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/reports/{report_id}.pdf")
def report_pdf_api(report_id: str) -> Response:
    record = get_report_record(report_id)
    markdown = get_report_markdown(report_id)
    if not record or markdown is None:
        raise HTTPException(status_code=404, detail="报告不存在。")
    try:
        content = export_report_pdf(markdown)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    filename = export_filename(record, "pdf")
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/api/reports/{report_id}")
def report_detail_api(report_id: str) -> dict[str, object]:
    record = get_report_record(report_id)
    if not record:
        raise HTTPException(status_code=404, detail="报告不存在。")
    markdown = get_report_markdown(report_id)
    return {"report": record, "markdown": markdown or ""}


@app.post("/api/analyze")
def analyze_api(
    symbol: str,
    date: str | None = None,
    data_source: str = "eodhd",
    report_template: str = "basic",
) -> dict[str, object]:
    normalized = normalize_symbol(symbol)
    source_ok, _ = validate_source_for_symbol(normalized, data_source)
    if not source_ok:
        return analyze_with_tradingagents(normalized, date=date, data_source=data_source, report_template=report_template)
    connection = resolve_connection_config()
    if connection.get("requires_key") and not connection.get("api_key"):
        raise HTTPException(
            status_code=400,
            detail="当前模型尚未配置，无法生成报告。请先进入模型配置并完成连接测试。",
        )
    return analyze_with_tradingagents(normalized, date=date, data_source=data_source, report_template=report_template)


@app.get("/api/mt5/signal")
def mt5_signal_api() -> dict[str, object]:
    return get_signal().to_dict()


@app.get("/api/mt5/signal.txt", response_class=PlainTextResponse)
def mt5_signal_text_api() -> str:
    return get_signal().to_text()


@app.post("/api/mt5/signal")
def mt5_save_signal_api(
    symbol: str = Form("CHART"),
    action: str = Form("WAIT"),
    volume: float = Form(0.0),
    sl: float = Form(0.0),
    tp: float = Form(0.0),
    comment: str = Form(""),
    ttl_minutes: int = Form(15),
    auto_trade_allowed: bool = Form(False),
    trade_mode: str = Form("DEMO"),
) -> dict[str, object]:
    if trade_mode.upper() == "LIVE":
        if os.getenv("MT5_LIVE_TRADING_ENABLED", "0") != "1":
            raise HTTPException(status_code=403, detail="实盘交易未启用。请设置 MT5_LIVE_TRADING_ENABLED=1")
        if not auto_trade_allowed:
            raise HTTPException(status_code=400, detail="实盘信号须设置 auto_trade_allowed=true")
        max_lv = float(os.getenv("MT5_MAX_LIVE_VOLUME", "0.01"))
        if volume <= 0 or volume > max_lv:
            raise HTTPException(status_code=400, detail=f"实盘量超限 {max_lv}")
        if sl <= 0 or tp <= 0:
            raise HTTPException(status_code=400, detail="实盘须设止损止盈")
    signal = save_signal(
        symbol=symbol, action=action, volume=volume,
        sl=sl, tp=tp, comment=comment, ttl_minutes=ttl_minutes,
        auto_trade_allowed=auto_trade_allowed,
        trade_mode=trade_mode.upper(),
    )
    return signal.to_dict()

@app.post("/api/mt5/clear-signal")
def mt5_clear_signal_api() -> dict[str, object]:
    return clear_signal().to_dict()