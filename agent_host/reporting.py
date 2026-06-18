from __future__ import annotations

from typing import Any

from agent_host.market_snapshot import format_snapshot_markdown
from agent_host.markets import NormalizedSymbol, market_name


def build_research_report(
    *,
    status: str,
    symbol: NormalizedSymbol,
    analysis_date: str,
    market_snapshot: dict[str, Any] | None = None,
    message: str = "",
    report_template: str = "basic",
    decision: Any | None = None,
    error: str = "",
) -> dict[str, object]:
    snapshot = market_snapshot or {}
    source_name = str(snapshot.get("source") or "未选择")
    mapped_symbol = str(snapshot.get("mapped_symbol") or symbol.canonical)
    title = f"{symbol.display} 投研辅助报告"

    sections = [
        {"title": "一、报告摘要", "content": _summary(status, symbol, source_name, snapshot, message)},
        {"title": "二、标的信息", "content": _symbol_block(symbol, analysis_date, mapped_symbol, source_name, report_template)},
        {"title": "三、数据源与字段覆盖", "content": _source_audit(snapshot)},
        {"title": "四、行情观察", "content": format_snapshot_markdown(snapshot)},
        {"title": "五、多角色状态", "content": _roles_block(snapshot, symbol.market)},
        {"title": "六、风险提示", "content": _risk_block(snapshot)},
        {"title": "七、使用边界", "content": _boundary_block()},
    ]
    markdown = "\n\n".join([f"# {title}", *[f"## {item['title']}\n\n{item['content']}" for item in sections]])
    return {
        "title": title,
        "status": status,
        "source": source_name,
        "mapped_symbol": mapped_symbol,
        "used_fields": snapshot.get("used_fields", []),
        "missing_fields": snapshot.get("missing_fields", []),
        "data_timestamp": snapshot.get("data_timestamp") or snapshot.get("latest_date") or "",
        "capability_level": snapshot.get("capability_level") or "基础行情版",
        "sections": sections,
        "markdown": markdown,
    }


def _summary(status: str, symbol: NormalizedSymbol, source_name: str, snapshot: dict[str, Any], message: str) -> str:
    if status != "ok":
        return message or snapshot.get("message") or "本次报告未生成成功，请按页面提示检查配置或数据源。"
    close = _fmt_number(snapshot.get("latest_close"))
    change = _fmt_pct(snapshot.get("day_change_pct"))
    data_time = snapshot.get("data_timestamp") or snapshot.get("latest_date") or "未知"
    return "\n".join(
        [
            f"本报告仅使用 {source_name} 一个主数据源生成，标的为 {symbol.display}。",
            f"最新可用数据时间：{data_time}；最新价格：{close}；单日涨跌幅：{change}。",
            "本报告为投研辅助材料，不构成投资建议，也不承诺收益。",
        ]
    )


def _symbol_block(symbol: NormalizedSymbol, analysis_date: str, mapped_symbol: str, source_name: str, report_template: str) -> str:
    return "\n".join(
        [
            f"- 输入标的：{symbol.raw}",
            f"- 识别市场：{market_name(symbol.market)}",
            f"- 标准代码：{symbol.canonical}",
            f"- 数据源映射代码：{mapped_symbol}",
            f"- 主数据源：{source_name}",
            f"- 报告类型：{'基础行情版' if report_template == 'basic' else report_template}",
            f"- 分析日期：{analysis_date}",
        ]
    )


def _source_audit(snapshot: dict[str, Any]) -> str:
    used = snapshot.get("used_fields") or []
    missing = snapshot.get("missing_fields") or []
    return "\n".join(
        [
            f"- 主数据源：{snapshot.get('source') or '未选择'}",
            f"- 映射代码：{snapshot.get('mapped_symbol') or '未知'}",
            f"- 数据时间：{snapshot.get('data_timestamp') or snapshot.get('latest_date') or '未知'}",
            f"- 已使用字段：{', '.join(used) if used else '暂无'}",
            f"- 缺失字段：{', '.join(missing) if missing else '无'}",
            "- 说明：为避免不同数据公司口径混用，本报告不会后台使用其他数据源补齐缺失字段。",
        ]
    )


def _roles_block(snapshot: dict[str, Any], market: str = "") -> str:
    roles = snapshot.get("roles") or []
    if not roles:
        if market == "CRYPTO":
            roles = [
                {"name": "市场分析师", "status": "可用", "detail": "基于当前行情字段整理观察"},
                {"name": "趋势分析师", "status": "可用", "detail": "基于日线价格和成交量观察趋势"},
                {"name": "链上数据", "status": "字段不足", "detail": "当前主数据源未提供链上数据字段"},
                {"name": "市场情绪", "status": "字段不足", "detail": "当前主数据源未提供社交媒体/情绪字段"},
                {"name": "风险分析师", "status": "可用", "detail": "基于价格波动和数据缺口提示风险"},
                {"name": "研究经理", "status": "可用", "detail": "汇总本次报告"},
            ]
        else:
            roles = [
                {"name": "市场分析师", "status": "可用", "detail": "基于当前行情字段整理观察"},
                {"name": "基本面分析师", "status": "字段不足", "detail": "当前主数据源未提供完整基本面字段"},
                {"name": "新闻分析师", "status": "字段不足", "detail": "当前主数据源未提供新闻字段"},
                {"name": "风险分析师", "status": "可用", "detail": "基于价格波动和数据缺口提示风险"},
                {"name": "研究经理", "status": "可用", "detail": "汇总本次报告"},
            ]
    return "\n".join(f"- {item.get('name')}：{item.get('status')}。{item.get('detail')}" for item in roles)


def _risk_block(snapshot: dict[str, Any]) -> str:
    missing = snapshot.get("missing_fields") or []
    lines = [
        "本报告依赖第三方数据源，可能存在延迟、缺失、限流或套餐权限限制。",
        "模型和规则整理结果仅用于投研辅助，不构成证券投资咨询、买卖建议或收益承诺。",
    ]
    if missing:
        lines.append(f"本次缺失字段包括：{', '.join(missing)}。缺失部分不会被伪造，也不会由其他数据源自动补齐。")
    return "\n".join(f"- {line}" for line in lines)


def _boundary_block() -> str:
    return "\n".join(
        [
            "- 本工具用于投研分析、策略研究、学习和模拟验证。",
            "- 本版本不开放实盘自动交易，不代客户下单。",
            "- 本报告不构成投资建议，不承诺任何收益。",
            "- 第三方数据源可能延迟、缺失、错误或限流。",
        ]
    )


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
