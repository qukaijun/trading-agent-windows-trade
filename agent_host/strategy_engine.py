from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from agent_host.markets import normalize_symbol


@dataclass(frozen=True)
class StrategyTemplate:
    id: str
    name: str
    category: str
    description: str
    default_symbol: str
    default_type: str
    default_timeframe: str
    beginner_level: str
    prompt: str
    required_fields: tuple[str, ...]
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["required_fields"] = list(self.required_fields)
        data["tags"] = list(self.tags)
        return data


@dataclass
class CompiledStrategy:
    id: str
    name: str
    source: str
    prompt: str
    template_id: str
    status: str
    symbol: dict[str, str]
    strategy_type: str
    timeframe: str
    mode: str
    action: str
    volume: float
    entry: dict[str, Any]
    exit: dict[str, Any]
    risk: dict[str, Any]
    schedule: dict[str, Any]
    assumptions: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    explain: list[str] = field(default_factory=list)
    compiled_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


STRATEGY_TEMPLATES: tuple[StrategyTemplate, ...] = (
    StrategyTemplate(
        id="gold_breakout_demo",
        name="黄金突破观察",
        category="贵金属",
        description="观察黄金突破关键价位后的模拟盘顺势机会。",
        default_symbol="GOLD",
        default_type="breakout",
        default_timeframe="H1",
        beginner_level="easy",
        prompt="黄金 H1 收盘突破 4200 后模拟盘做多，止损 4170，止盈 4260，0.1 手。",
        required_fields=("symbol", "entry_price", "stop_loss", "take_profit"),
        tags=("黄金", "突破", "短线", "模拟盘"),
    ),
    StrategyTemplate(
        id="gold_pullback_demo",
        name="黄金回调做多",
        category="贵金属",
        description="等待黄金回调到支撑附近，再用模拟盘验证做多计划。",
        default_symbol="GOLD",
        default_type="pullback",
        default_timeframe="H1",
        beginner_level="easy",
        prompt="黄金回调到 4160 附近观察做多，止损 4135，止盈 4210，轻仓模拟盘。",
        required_fields=("symbol", "entry_price", "stop_loss", "take_profit"),
        tags=("黄金", "回调", "支撑", "模拟盘"),
    ),
    StrategyTemplate(
        id="silver_breakdown_demo",
        name="白银跌破支撑",
        category="贵金属",
        description="观察白银跌破支撑后的模拟盘做空机会。",
        default_symbol="XAGUSD",
        default_type="breakdown",
        default_timeframe="H1",
        beginner_level="medium",
        prompt="白银 H1 跌破 29.8 后模拟盘做空，止损 30.4，止盈 28.9。",
        required_fields=("symbol", "entry_price", "stop_loss", "take_profit"),
        tags=("白银", "做空", "突破", "模拟盘"),
    ),
    StrategyTemplate(
        id="btc_grid_demo",
        name="BTC 震荡网格",
        category="加密货币",
        description="在给定区间内模拟低买高卖的网格思路。",
        default_symbol="BTC-USD",
        default_type="grid",
        default_timeframe="H1",
        beginner_level="easy",
        prompt="BTC 在 60000 到 66000 之间做模拟网格，分 6 格，单格 0.01 BTC，不实盘。",
        required_fields=("symbol", "grid_low", "grid_high", "grid_count"),
        tags=("BTC", "网格", "震荡", "模拟盘"),
    ),
    StrategyTemplate(
        id="eth_trend_demo",
        name="ETH 趋势跟随",
        category="加密货币",
        description="用均线/趋势条件观察 ETH 顺势模拟盘机会。",
        default_symbol="ETH-USD",
        default_type="trend_following",
        default_timeframe="H1",
        beginner_level="medium",
        prompt="ETH 如果站上 20 均线并保持上行，模拟盘做多，跌破 20 均线退出。",
        required_fields=("symbol", "indicator", "exit_condition"),
        tags=("ETH", "趋势", "均线", "模拟盘"),
    ),
    StrategyTemplate(
        id="btc_dca_demo",
        name="BTC 分批买入",
        category="加密货币",
        description="按固定间隔或跌幅分批模拟买入。",
        default_symbol="BTC-USD",
        default_type="dca",
        default_timeframe="D1",
        beginner_level="easy",
        prompt="BTC 每下跌 3% 模拟分批买入一次，最多 5 次，总仓位不超过 0.05 BTC。",
        required_fields=("symbol", "step_pct", "max_entries", "max_position"),
        tags=("BTC", "DCA", "分批", "模拟盘"),
    ),
    StrategyTemplate(
        id="rsi_reversal_demo",
        name="RSI 反转观察",
        category="技术指标",
        description="观察 RSI 超买超卖后的模拟反转机会。",
        default_symbol="GOLD",
        default_type="rsi_reversal",
        default_timeframe="H1",
        beginner_level="medium",
        prompt="黄金 RSI 低于 30 后观察反弹做多，RSI 高于 70 不追多，先模拟盘。",
        required_fields=("symbol", "indicator", "threshold"),
        tags=("RSI", "反转", "黄金", "模拟盘"),
    ),
    StrategyTemplate(
        id="observe_only",
        name="只观察不下单",
        category="安全模式",
        description="只生成观察条件和风险提示，不写入 MT5 信号。",
        default_symbol="GOLD",
        default_type="observe",
        default_timeframe="H1",
        beginner_level="easy",
        prompt="帮我观察黄金短线方向，只提醒关键位置，不发送交易信号。",
        required_fields=("symbol",),
        tags=("观察", "安全", "新手"),
    ),
)


def list_strategy_templates() -> dict[str, Any]:
    return {"templates": [template.to_dict() for template in STRATEGY_TEMPLATES]}


def compile_strategy(payload: dict[str, Any]) -> dict[str, Any]:
    prompt = str(payload.get("prompt") or "").strip()
    template_id = str(payload.get("template_id") or "").strip()
    template = _find_template(template_id)
    if not prompt and template:
        prompt = template.prompt
    if not prompt:
        prompt = "帮我观察黄金短线机会，只做模拟盘。"

    merged_text = f"{template.prompt if template else ''}\n{prompt}".strip()
    symbol_text = str(payload.get("symbol") or _detect_symbol(merged_text, template) or "GOLD")
    symbol = normalize_symbol(symbol_text)
    strategy_type = str(payload.get("strategy_type") or _detect_strategy_type(merged_text, template))
    timeframe = str(payload.get("timeframe") or _detect_timeframe(merged_text, template))
    action = str(payload.get("action") or _detect_action(merged_text, strategy_type)).upper()
    mode = str(payload.get("mode") or _detect_mode(merged_text)).upper()
    volume = _detect_volume(merged_text, default=0.01 if "轻仓" in merged_text else 0.1)
    numbers = _numbers(merged_text)
    entry = _build_entry(strategy_type, action, merged_text, numbers)
    exit_rules = _build_exit(merged_text, numbers)
    risk = _build_risk(merged_text, volume)
    schedule = {
        "enabled": False,
        "interval_minutes": _detect_interval(merged_text),
        "max_runtime_minutes": 240,
    }

    missing = _missing_fields(strategy_type, entry, exit_rules)
    warnings = _warnings(mode, action, exit_rules, strategy_type)
    status = "ready" if not missing else "needs_confirmation"
    if strategy_type == "observe":
        status = "observe_only"
        action = "WAIT"

    compiled = CompiledStrategy(
        id=f"stg_{uuid.uuid4().hex[:12]}",
        name=_strategy_name(symbol.raw, strategy_type, template),
        source="template+rules" if template else "natural_language_rules",
        prompt=prompt,
        template_id=template.id if template else "",
        status=status,
        symbol=symbol.to_dict(),
        strategy_type=strategy_type,
        timeframe=timeframe,
        mode=mode,
        action=action,
        volume=volume,
        entry=entry,
        exit=exit_rules,
        risk=risk,
        schedule=schedule,
        assumptions=_assumptions(strategy_type, timeframe, action),
        missing_fields=missing,
        warnings=warnings,
        explain=_explain(symbol.raw, strategy_type, action, entry, exit_rules, mode),
    )
    return {"status": "ok", "strategy": compiled.to_dict()}


def _find_template(template_id: str) -> StrategyTemplate | None:
    for template in STRATEGY_TEMPLATES:
        if template.id == template_id:
            return template
    return None


def _detect_symbol(text: str, template: StrategyTemplate | None) -> str:
    lower = text.lower()
    if re.search(r"\bbtc\b|比特币|bitcoin", lower):
        return "BTC-USD"
    if re.search(r"\beth\b|以太|ethereum", lower):
        return "ETH-USD"
    if re.search(r"白银|xag|silver", lower):
        return "XAGUSD"
    if re.search(r"黄金|xau|gold", lower):
        return "GOLD"
    return template.default_symbol if template else "GOLD"


def _detect_strategy_type(text: str, template: StrategyTemplate | None) -> str:
    lower = text.lower()
    if "网格" in text or "grid" in lower:
        return "grid"
    if "dca" in lower or "分批" in text or "定投" in text:
        return "dca"
    if "rsi" in lower:
        return "rsi_reversal"
    if "均线" in text or "ma" in lower or "趋势" in text or "trend" in lower:
        return "trend_following"
    if "跌破" in text or "breakdown" in lower:
        return "breakdown"
    if "突破" in text or "breakout" in lower:
        return "breakout"
    if "回调" in text or "支撑" in text:
        return "pullback"
    if "观察" in text and ("不下单" in text or "不发送" in text):
        return "observe"
    return template.default_type if template else "discretionary"


def _detect_timeframe(text: str, template: StrategyTemplate | None) -> str:
    lower = text.lower()
    if "m15" in lower or "15分钟" in text:
        return "M15"
    if "m30" in lower or "30分钟" in text:
        return "M30"
    if "h4" in lower or "4小时" in text:
        return "H4"
    if "d1" in lower or "日线" in text:
        return "D1"
    if "h1" in lower or "1小时" in text or "小时" in text or "短线" in text or "日内" in text:
        return "H1"
    return template.default_timeframe if template else "H1"


def _detect_action(text: str, strategy_type: str) -> str:
    lower = text.lower()
    if "做空" in text or "看空" in text or "卖" in text or "short" in lower or "sell" in lower:
        return "SELL"
    if "做多" in text or "看多" in text or "买" in text or "long" in lower or "buy" in lower:
        return "BUY"
    if strategy_type == "breakdown":
        return "SELL"
    if strategy_type in {"breakout", "pullback", "trend_following", "rsi_reversal", "dca"}:
        return "BUY"
    return "WAIT"


def _detect_mode(text: str) -> str:
    if "实盘" in text or "live" in text.lower():
        return "LIVE"
    return "DEMO"


def _detect_volume(text: str, default: float) -> float:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:手|lot)", text, flags=re.IGNORECASE)
    if not match:
        return default
    return max(0.0, min(float(match.group(1)), 1.0))


def _numbers(text: str) -> list[float]:
    return [float(item) for item in re.findall(r"\d+(?:\.\d+)?", text)]


def _build_entry(strategy_type: str, action: str, text: str, numbers: list[float]) -> dict[str, Any]:
    if strategy_type == "grid":
        low = min(numbers[:2]) if len(numbers) >= 2 else 0
        high = max(numbers[:2]) if len(numbers) >= 2 else 0
        grid_count = int(numbers[2]) if len(numbers) >= 3 else 6
        return {"type": "grid_range", "low": low, "high": high, "grid_count": grid_count, "trigger": "range_active"}
    if strategy_type == "dca":
        step_pct = _after_keywords(text, ("下跌", "回撤"), default=3)
        max_entries = int(_after_keywords(text, ("最多",), default=5))
        return {"type": "dca", "step_pct": step_pct, "max_entries": max_entries, "trigger": "drawdown_step"}
    if strategy_type == "rsi_reversal":
        threshold = _after_keywords(text, ("低于", "<", "below"), default=30)
        return {"type": "indicator", "indicator": "RSI", "operator": "<=", "value": threshold, "trigger": "oversold_reversal"}
    if strategy_type == "trend_following":
        period = int(_after_keywords(text, ("均线", "ma"), default=20))
        return {"type": "indicator", "indicator": f"MA{period}", "operator": "above", "trigger": "trend_confirmed"}
    price = _entry_price(text, numbers)
    operator = "cross_above" if action == "BUY" else "cross_below"
    if strategy_type in {"pullback"}:
        operator = "touch_or_below" if action == "BUY" else "touch_or_above"
    return {"type": "price", "operator": operator, "price": price, "trigger": strategy_type}


def _build_exit(text: str, numbers: list[float]) -> dict[str, Any]:
    sl = _value_after_label(text, ("止损", "sl"))
    tp = _value_after_label(text, ("止盈", "目标", "tp"))
    if sl == 0 and len(numbers) >= 2:
        sl = numbers[-2]
    if tp == 0 and len(numbers) >= 2:
        tp = numbers[-1]
    return {
        "stop_loss": sl,
        "take_profit": tp,
        "trailing_stop": "移动止损" in text,
        "exit_on_opposite_signal": True,
    }


def _build_risk(text: str, volume: float) -> dict[str, Any]:
    level = "low" if any(word in text for word in ("保守", "轻仓", "小仓")) else "high" if any(word in text for word in ("激进", "重仓")) else "medium"
    return {
        "level": level,
        "max_volume": volume,
        "paper_first": "实盘" not in text,
        "requires_sl_tp_before_live": True,
    }


def _detect_interval(text: str) -> int:
    if "5分钟" in text:
        return 5
    if "15分钟" in text:
        return 15
    if "30分钟" in text:
        return 30
    return 30


def _missing_fields(strategy_type: str, entry: dict[str, Any], exit_rules: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if strategy_type in {"breakout", "breakdown", "pullback", "discretionary"} and not entry.get("price"):
        missing.append("entry.price")
    if strategy_type == "grid":
        if not entry.get("low"):
            missing.append("entry.low")
        if not entry.get("high"):
            missing.append("entry.high")
    if strategy_type != "observe":
        if not exit_rules.get("stop_loss"):
            missing.append("exit.stop_loss")
        if not exit_rules.get("take_profit") and strategy_type not in {"dca", "grid", "trend_following"}:
            missing.append("exit.take_profit")
    return missing


def _warnings(mode: str, action: str, exit_rules: dict[str, Any], strategy_type: str) -> list[str]:
    warnings: list[str] = []
    if mode == "LIVE":
        warnings.append("当前编译器默认建议先模拟盘验证；实盘需要额外确认。")
    if action in {"BUY", "SELL"} and not exit_rules.get("stop_loss"):
        warnings.append("没有止损，不能进入自动执行。")
    if strategy_type == "grid":
        warnings.append("网格策略当前只做模拟状态管理，不直接拆分多笔 MT5 订单。")
    if strategy_type == "dca":
        warnings.append("DCA 策略当前只生成模拟计划，不自动连续加仓。")
    return warnings


def _assumptions(strategy_type: str, timeframe: str, action: str) -> list[str]:
    assumptions = [f"周期按 {timeframe} 处理。", "未指定账户时默认模拟盘。"]
    if strategy_type in {"breakout", "breakdown"}:
        assumptions.append("突破默认按触价条件观察，正式版本可切换为收盘价确认。")
    if action == "WAIT":
        assumptions.append("方向不明确，先作为观察策略处理。")
    return assumptions


def _explain(symbol: str, strategy_type: str, action: str, entry: dict[str, Any], exit_rules: dict[str, Any], mode: str) -> list[str]:
    return [
        f"识别标的为 {symbol}。",
        f"策略类型为 {strategy_type}，方向为 {_action_text(action)}。",
        f"入场规则：{entry}",
        f"退出规则：SL {exit_rules.get('stop_loss') or '--'} / TP {exit_rules.get('take_profit') or '--'}。",
        f"执行模式：{mode}。",
    ]


def _action_text(action: str) -> str:
    if action == "BUY":
        return "做多"
    if action == "SELL":
        return "做空"
    return "等待"


def _strategy_name(symbol: str, strategy_type: str, template: StrategyTemplate | None) -> str:
    if template:
        return template.name
    names = {
        "breakout": "突破策略",
        "breakdown": "跌破策略",
        "pullback": "回调策略",
        "grid": "网格策略",
        "dca": "DCA 策略",
        "trend_following": "趋势跟随",
        "rsi_reversal": "RSI 反转",
        "observe": "观察策略",
    }
    return f"{symbol} {names.get(strategy_type, '自定义策略')}"


def _entry_price(text: str, numbers: list[float]) -> float:
    labeled = _value_after_label(text, ("突破", "跌破", "回调到", "到", "价格"))
    if labeled:
        return labeled
    return numbers[0] if numbers else 0


def _value_after_label(text: str, labels: tuple[str, ...]) -> float:
    for label in labels:
        match = re.search(rf"{re.escape(label)}\s*[:：]?\s*(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return 0


def _after_keywords(text: str, keywords: tuple[str, ...], default: float) -> float:
    for keyword in keywords:
        match = re.search(rf"{re.escape(keyword)}\s*[:：]?\s*(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return default
