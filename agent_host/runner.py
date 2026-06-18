from __future__ import annotations

import os
import sys
from datetime import date as date_type
from pathlib import Path
from typing import Any

from agent_host.data_source_registry import audit_snapshot_for_block, validate_source_for_symbol
from agent_host.market_snapshot import get_market_snapshot
from agent_host.markets import NormalizedSymbol
from agent_host.reporting import build_research_report
from agent_host.report_requirements import check_report_requirements
from agent_host.report_store import save_report_record


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "vendor" / "upstream" / "TradingAgents"


def ensure_upstream_on_path() -> None:
    if UPSTREAM.exists():
        upstream_text = str(UPSTREAM)
        if upstream_text not in sys.path:
            sys.path.insert(0, upstream_text)


def upstream_status() -> dict[str, object]:
    ensure_upstream_on_path()
    status: dict[str, object] = {"path": str(UPSTREAM), "exists": UPSTREAM.exists(), "importable": False}
    try:
        import tradingagents  # noqa: F401

        status["importable"] = True
    except Exception as exc:  # noqa: BLE001
        status["error"] = str(exc)
    return status


def analyze_with_tradingagents(
    symbol: NormalizedSymbol,
    *,
    date: str | None = None,
    data_source: str = "yfinance",
    report_template: str = "basic",
    use_upstream: bool = False,
) -> dict[str, object]:
    analysis_date = date or date_type.today().isoformat()
    # Route to upstream engine if requested
    if use_upstream:
        return analyze_with_upstream_engine(
            symbol, date=date, data_source=data_source, report_template=report_template
        )
    # Auto-switch to crypto_basic for cryptocurrency
    if report_template == "basic" and symbol.market in ("CRYPTO", "COMMODITY"):
        report_template = "crypto_basic"
    ok, validation_message = validate_source_for_symbol(symbol, data_source)
    if not ok:
        return _blocked(symbol, analysis_date, validation_message, data_source, report_template)

    market_snapshot = get_market_snapshot(symbol, data_source)
    if market_snapshot.get("status") != "ok":
        return _blocked(symbol, analysis_date, str(market_snapshot.get("message") or "当前数据源不可用。"), data_source, report_template, market_snapshot)

    requirement = check_report_requirements(market_snapshot, report_template)
    if not requirement.get("ok"):
        return _blocked(symbol, analysis_date, str(requirement.get("message") or "当前字段不足。"), data_source, report_template, market_snapshot)

    # Run real multi-role LLM analysis
    roles = _run_role_analysis(symbol, market_snapshot)
    if roles and not any(r.get("status") == "分析失败" for r in roles):
        market_snapshot["roles"] = roles
    
    report = build_research_report(
        status="ok",
        symbol=symbol,
        analysis_date=analysis_date,
        market_snapshot=market_snapshot,
        report_template=report_template,
    )
    saved_report = _save_report(symbol=symbol, analysis_date=analysis_date, status="ok", report=report)
    return {
        "status": "ok",
        "symbol": symbol.to_dict(),
        "analysis_date": analysis_date,
        "data_source": data_source,
        "market_snapshot": market_snapshot,
        "message": "报告已生成。",
        "role_progress": market_snapshot.get("roles", []),
        "report": report,
        "saved_report": saved_report,
    }





def analyze_with_upstream_engine(
    symbol: NormalizedSymbol,
    *,
    date: str | None = None,
    data_source: str = "yfinance",
    report_template: str = "basic",
) -> dict[str, object]:
    """Run the full TradingAgents multi-agent pipeline (upstream engine).

    This invokes the real multi-agent framework: market/sentiment/news/fundamental
    analysts → bull/bear researcher debate → risk analyst debate → portfolio manager
    decision. Takes 3-5 minutes. Uses the configured LLM provider.
    """
    import json, os as _os, sys as _sys
    from datetime import date as _date_type
    from pathlib import Path as _Path

    analysis_date = date or _date_type.today().isoformat()

    # Resolve model config
    from agent_host.config_manager import resolve_connection_config
    config = resolve_connection_config(None)
    if not config.get("api_key"):
        return _blocked(symbol, analysis_date, "请先配置大模型 API Key 后再使用深度分析。", data_source, report_template)

    # Map provider to upstream format
    provider_map = {
        "qwen-cn": "deepseek",
        "deepseek": "deepseek",
        "deepseek-cn": "deepseek",
        "openai": "openai",
        "google": "google",
        "gemini": "google",
    }
    upstream_provider = provider_map.get(config["provider"], "deepseek")

    # Ensure upstream is on path
    _upstream_root = ROOT / "vendor" / "upstream" / "TradingAgents"
    if _upstream_root.exists():
        upstream_str = str(_upstream_root)
        if upstream_str not in _sys.path:
            _sys.path.insert(0, upstream_str)

    try:
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG
    except ImportError as e:
        return _blocked(symbol, analysis_date,
                        f"深度分析引擎未能加载：{e}。请确认上游 TradingAgents 已安装。",
                        data_source, report_template)

    # Build upstream config
    upstream_config = DEFAULT_CONFIG.copy()
    upstream_config["llm_provider"] = upstream_provider
    upstream_config["deep_think_llm"] = config["model"]
    upstream_config["quick_think_llm"] = config["model"]
    upstream_config["backend_url"] = config["base_url"]
    upstream_config["output_language"] = "Chinese"
    upstream_config["checkpoint_enabled"] = False

    # Set API key via env var for upstream (provider-specific)
    if upstream_provider == "deepseek":
        _os.environ["DEEPSEEK_API_KEY"] = config["api_key"]
    elif upstream_provider == "google":
        _os.environ["GOOGLE_API_KEY"] = config["api_key"]
    else:
        _os.environ["OPENAI_API_KEY"] = config["api_key"]

    # Determine ticker for upstream
    ticker = symbol.yfinance if symbol.market in ("US", "HK") else symbol.canonical

    # Initialize and run
    try:
        ta = TradingAgentsGraph(debug=False, config=upstream_config)
        final_state, decision = ta.propagate(ticker, analysis_date)
    except Exception as e:
        return _blocked(symbol, analysis_date,
                        f"深度分析引擎运行失败：{str(e)[:200]}。请检查模型配置和网络连接。",
                        data_source, report_template)

    # Build report from upstream output
    report = _build_upstream_report(symbol, analysis_date, final_state, decision,
                                    data_source, report_template, ticker)

    saved_report = _save_report(symbol=symbol, analysis_date=analysis_date, status="ok", report=report)
    return {
        "status": "ok",
        "symbol": symbol.to_dict(),
        "analysis_date": analysis_date,
        "data_source": data_source,
        "market_snapshot": {"source": data_source, "mapped_symbol": ticker},
        "message": "深度多角色分析报告已生成（上游多智能体引擎）。",
        "role_progress": report.get("sections", []),
        "report": report,
        "saved_report": saved_report,
        "upstream_decision": str(decision)[:500] if decision else "",
    }


def _build_upstream_report(
    symbol: NormalizedSymbol,
    analysis_date: str,
    final_state: dict,
    decision: object,
    data_source: str,
    report_template: str,
    ticker: str,
) -> dict[str, object]:
    """Convert upstream TradingAgentsGraph output to our report format."""
    from agent_host.markets import market_name as _market_name

    source_name = data_source.upper() if data_source else "yfinance"
    title = f"{symbol.display} 深度多角色投研报告（上游引擎）"

    market_report = str(final_state.get("market_report", "") or "")
    sentiment_report = str(final_state.get("sentiment_report", "") or "")
    news_report = str(final_state.get("news_report", "") or "")
    fundamentals_report = str(final_state.get("fundamentals_report", "") or "")

    # Investment debate
    debate_state = final_state.get("investment_debate_state", {}) or {}
    bull_history = str(debate_state.get("bull_history", "") or "")
    bear_history = str(debate_state.get("bear_history", "") or "")
    judge_decision = str(debate_state.get("judge_decision", "") or "")

    # Risk debate
    risk_state = final_state.get("risk_debate_state", {}) or {}
    aggressive = str(risk_state.get("aggressive_history", "") or "")
    conservative = str(risk_state.get("conservative_history", "") or "")
    neutral = str(risk_state.get("neutral_history", "") or "")
    risk_judge = str(risk_state.get("judge_decision", "") or "")

    # Trader and PM
    trader_plan = str(final_state.get("trader_investment_plan", "") or "")
    investment_plan = str(final_state.get("investment_plan", "") or "")
    final_decision = str(final_state.get("final_trade_decision", "") or "")

    sections = [
        {"title": "一、报告摘要", "content": f"本报告由 TradingAgents 多智能体引擎生成。\n\n标的：{symbol.display}\n市场：{_market_name(symbol.market)}\n分析日期：{analysis_date}\n主数据源：{source_name}\n映射代码：{ticker}\n\n最终决策概要：{str(decision)[:300] if decision else '无'}"},
        {"title": "二、标的信息", "content": f"- 输入标的：{symbol.raw}\n- 识别市场：{_market_name(symbol.market)}\n- 标准代码：{symbol.canonical}\n- 主数据源：{source_name}\n- 分析引擎：TradingAgents 多智能体（上游）\n- 分析日期：{analysis_date}"},
        {"title": "三、市场分析", "content": market_report or "（市场分析报告未生成）"},
        {"title": "四、情绪/社媒分析", "content": sentiment_report or "（情绪分析报告未生成）"},
        {"title": "五、新闻分析", "content": news_report or "（新闻分析报告未生成）"},
        {"title": "六、基本面分析", "content": fundamentals_report or "（基本面分析报告未生成）"},
        {"title": "七、多空研究员辩论", "content": f"### 多方研究员\n{bull_history or '（无）'}\n\n### 空方研究员\n{bear_history or '（无）'}\n\n### 研究经理裁决\n{judge_decision or '（无）'}"},
        {"title": "八、交易员策略", "content": trader_plan or "（交易计划未生成）"},
        {"title": "九、风控辩论", "content": f"### 激进风控\n{aggressive or '（无）'}\n\n### 保守风控\n{conservative or '（无）'}\n\n### 中立风控\n{neutral or '（无）'}\n\n### 风控裁决\n{risk_judge or '（无）'}"},
        {"title": "十、组合经理决策", "content": investment_plan or "（投资计划未生成）"},
        {"title": "十一、最终决策", "content": final_decision or "（最终决策未生成）"},
        {"title": "十二、风险提示与使用边界", "content": "- 本报告由 AI 多智能体协作生成，仅供投研学习和模拟验证。\n- 不构成投资建议，不承诺收益。\n- 本工具不对接实盘交易。\n- 数据来自第三方数据源，可能存在延迟或缺失。"},
    ]

    markdown = "\n\n".join([f"# {title}", *[f"## {s['title']}\n\n{s['content']}" for s in sections]])

    return {
        "title": title,
        "status": "ok",
        "source": source_name,
        "mapped_symbol": ticker,
        "used_fields": ["市场分析", "情绪分析", "新闻分析", "基本面分析", "多空辩论", "风控辩论", "组合经理决策"],
        "missing_fields": [],
        "data_timestamp": analysis_date,
        "capability_level": "深度多角色版（上游引擎）",
        "sections": sections,
        "markdown": markdown,
        "upstream_raw_decision": str(decision)[:1000] if decision else "",
    }


def _run_role_analysis(symbol: NormalizedSymbol, market_snapshot: dict[str, Any], deep_think: bool = False) -> list[dict[str, str]]:
    """Run actual LLM analysis for each role using market data."""
    import json, time, urllib.error, urllib.request
    from agent_host.config_manager import resolve_connection_config
    
    config = resolve_connection_config(None)
    if not config.get("api_key"):
        return [{"name": "模型未配置", "status": "跳过", "detail": "请先配置大模型 API Key。"}]
    
    # Role-specific prompts
    market_name_str = {"A": "A股", "HK": "港股", "US": "美股", "CRYPTO": "加密货币", "COMMODITY": "贵金属/商品"}.get(symbol.market, symbol.market)
    data_summary = json.dumps({
        "symbol": symbol.canonical,
        "market": market_name_str,
        "latest_price": market_snapshot.get("latest_close"),
        "day_change_pct": market_snapshot.get("day_change_pct"),
        "volume": market_snapshot.get("latest_volume"),
        "used_fields": market_snapshot.get("used_fields", []),
        "missing_fields": market_snapshot.get("missing_fields", []),
    }, ensure_ascii=False)

    roles = [
        {"name": "市场分析师", "key": "market", "prompt": f"你是{market_name_str}市场分析师。基于以下数据做简要分析（150字以内）：\n{data_summary}\n\n请分析：1) 当前价格位置 2) 成交量特征 3) 短期关注点。用中文回复，简洁专业。"},
        {"name": "技术分析师", "key": "technical", "prompt": f"你是技术分析师。基于以下数据做简要分析（150字以内）：\n{data_summary}\n\n请分析：1) 价格趋势判断 2) 成交量暗示的信号 3) 关键支撑/阻力参考。用中文回复，简洁专业。"},
        {"name": "风险分析师", "key": "risk", "prompt": f"你是风险分析师。基于以下数据做简要分析（150字以内）：\n{data_summary}\n\n请分析：1) 当前波动风险 2) 数据缺口带来的不确定性 3) 需要注意的风险因素。用中文回复，简洁专业。"},
    ]
    
    results = []
    for role in roles:
        try:
            body = {
                "model": config["model"],
                "messages": [
                    {"role": "system", "content": "你是一位专业的金融分析师。回复简洁、有数据支撑、用中文。不超过150字。"},
                    {"role": "user", "content": role["prompt"]},
                ],
                "temperature": 0.3,
                "max_tokens": 300,
            }
            data = json.dumps(body).encode("utf-8")
            url = f"{config['base_url'].rstrip('/')}/chat/completions"
            req = urllib.request.Request(url, data=data, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config['api_key']}",
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                content_text = resp_data["choices"][0]["message"]["content"]
                results.append({"name": role["name"], "status": "已完成", "detail": content_text.strip()})
        except Exception as e:
            results.append({"name": role["name"], "status": "分析失败", "detail": str(e)[:100]})
    
    return results


def _blocked(
    symbol: NormalizedSymbol,
    analysis_date: str,
    message: str,
    data_source: str,
    report_template: str,
    market_snapshot: dict[str, Any] | None = None,
) -> dict[str, object]:
    snapshot = market_snapshot or {
        **audit_snapshot_for_block(symbol, data_source, message),
    }
    if market_snapshot is not None:
        snapshot = _complete_audit_snapshot(symbol, data_source, message, market_snapshot)
    report = build_research_report(
        status="blocked",
        symbol=symbol,
        analysis_date=analysis_date,
        market_snapshot=snapshot,
        message=message,
        report_template=report_template,
    )
    return {
        "status": "blocked",
        "symbol": symbol.to_dict(),
        "analysis_date": analysis_date,
        "data_source": data_source,
        "market_snapshot": snapshot,
        "message": message,
        "role_progress": snapshot.get("roles", []),
        "report": report,
        "saved_report": None,
    }


def _complete_audit_snapshot(
    symbol: NormalizedSymbol,
    data_source: str,
    message: str,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    base = audit_snapshot_for_block(symbol, data_source, message)
    completed = {**base, **snapshot}
    completed["source"] = snapshot.get("source") or base["source"]
    completed["source_key"] = snapshot.get("source_key") or data_source
    completed["mapped_symbol"] = snapshot.get("mapped_symbol") or base["mapped_symbol"]
    completed["message"] = snapshot.get("message") or message
    completed["used_fields"] = snapshot.get("used_fields") or base["used_fields"]
    completed["missing_fields"] = snapshot.get("missing_fields") or base["missing_fields"]
    completed["data_timestamp"] = snapshot.get("data_timestamp") or snapshot.get("latest_date") or base["data_timestamp"]
    completed["checked_at"] = snapshot.get("checked_at") or base["checked_at"]
    return completed


def _save_report(
    *,
    symbol: NormalizedSymbol,
    analysis_date: str,
    status: str,
    report: dict[str, object],
) -> dict[str, Any] | None:
    markdown = str(report.get("markdown") or "")
    if not markdown:
        return None
    return save_report_record(
        symbol=symbol.to_dict(),
        analysis_date=analysis_date,
        status=status,
        title=str(report.get("title") or f"{symbol.display} 投研辅助报告"),
        markdown=markdown,
        model_provider=os.getenv("TRADINGAGENT_DISPLAY_PROVIDER", os.getenv("TRADINGAGENTS_LLM_PROVIDER", "")),
        model=os.getenv("TRADINGAGENTS_DEEP_THINK_LLM", ""),
        data_source=str(report.get("source") or ""),
        mapped_symbol=str(report.get("mapped_symbol") or symbol.canonical),
        data_timestamp=str(report.get("data_timestamp") or ""),
    )
