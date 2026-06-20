from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_host.data_source_registry import validate_source_for_symbol
from agent_host.market_snapshot import get_market_snapshot
from agent_host.markets import normalize_symbol
from agent_host.mt5_bridge import save_signal


ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "runtime" / "strategy_robots.json"


@dataclass
class RobotEvent:
    time: str
    type: str
    message: str
    price: float = 0.0
    action: str = "WAIT"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyRobot:
    id: str
    name: str
    status: str
    mode: str
    strategy: dict[str, Any]
    created_at: str
    updated_at: str
    last_price: float = 0.0
    last_action: str = "WAIT"
    run_count: int = 0
    signal_count: int = 0
    events: list[RobotEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["events"] = [event.to_dict() for event in self.events][-20:]
        return data


class RobotManager:
    def __init__(self) -> None:
        self.robots: dict[str, StrategyRobot] = {}
        self._load()

    def status(self) -> dict[str, Any]:
        return {
            "robots": [robot.to_dict() for robot in self.robots.values()],
            "running_count": sum(1 for robot in self.robots.values() if robot.status == "running"),
            "updated_at": _now(),
        }

    def start(self, strategy: dict[str, Any]) -> dict[str, Any]:
        if strategy.get("status") == "needs_strategy_input" or strategy.get("strategy_type") == "assistant_help":
            raise ValueError("当前输入还不是可运行策略，请先补全交易标的、入场条件和风控。")
        strategy_id = str(strategy.get("id") or f"stg_{uuid.uuid4().hex[:12]}")
        robot_id = f"bot_{uuid.uuid4().hex[:10]}"
        now = _now()
        robot = StrategyRobot(
            id=robot_id,
            name=str(strategy.get("name") or strategy_id),
            status="running",
            mode="DEMO",
            strategy=strategy,
            created_at=now,
            updated_at=now,
            events=[
                RobotEvent(
                    time=now,
                    type="started",
                    message="模拟机器人已启动，强制使用 DEMO 模式，等待下一次观察。",
                )
            ],
        )
        self.robots[robot_id] = robot
        self._save()
        return robot.to_dict()

    def stop(self, robot_id: str) -> dict[str, Any]:
        robot = self._get(robot_id)
        robot.status = "stopped"
        robot.updated_at = _now()
        robot.events.append(RobotEvent(time=robot.updated_at, type="stopped", message="模拟机器人已停止。"))
        self._save()
        return robot.to_dict()

    def remove(self, robot_id: str) -> dict[str, Any]:
        robot = self._get(robot_id)
        del self.robots[robot_id]
        self._save()
        return robot.to_dict()

    def run_once(self, robot_id: str | None = None) -> dict[str, Any]:
        targets = [self._get(robot_id)] if robot_id else [robot for robot in self.robots.values() if robot.status == "running"]
        runs = [self._evaluate(robot) for robot in targets]
        self._save()
        return {"runs": runs, "robots": [robot.to_dict() for robot in self.robots.values()]}

    def _evaluate(self, robot: StrategyRobot) -> dict[str, Any]:
        now = _now()
        strategy = robot.strategy
        symbol_info = strategy.get("symbol") if isinstance(strategy.get("symbol"), dict) else {}
        raw_symbol = str(symbol_info.get("raw") or symbol_info.get("canonical") or "GOLD")
        normalized = normalize_symbol(raw_symbol)
        ok, message = validate_source_for_symbol(normalized, "yfinance")
        if not ok:
            event = RobotEvent(time=now, type="blocked", message=message)
            robot.events.append(event)
            robot.updated_at = now
            return {**event.to_dict(), "robot_id": robot.id, "symbol": normalized.raw}

        snapshot = get_market_snapshot(normalized, "yfinance")
        price = float(snapshot.get("latest_close") or snapshot.get("current_price") or 0)
        action, reason = _evaluate_strategy(strategy, price)
        robot.run_count += 1
        robot.last_price = price
        robot.last_action = action
        robot.updated_at = now

        if action in {"BUY", "SELL"}:
            exit_rules = strategy.get("exit") if isinstance(strategy.get("exit"), dict) else {}
            signal = save_signal(
                symbol=normalized.canonical,
                action=action,
                volume=float(strategy.get("volume") or 0.1),
                sl=float(exit_rules.get("stop_loss") or 0),
                tp=float(exit_rules.get("take_profit") or 0),
                comment=f"ROBOT-DEMO {robot.name}",
                ttl_minutes=30,
                auto_trade_allowed=False,
                trade_mode="DEMO",
            )
            robot.signal_count += 1
            robot.status = "triggered"
            event = RobotEvent(
                time=now,
                type="signal",
                message=f"{reason}，已生成模拟盘信号 {signal.action}。",
                price=price,
                action=action,
            )
        else:
            event = RobotEvent(time=now, type="watching", message=reason, price=price, action="WAIT")

        robot.events.append(event)
        return {**event.to_dict(), "robot_id": robot.id, "symbol": normalized.raw}

    def _get(self, robot_id: str | None) -> StrategyRobot:
        if not robot_id or robot_id not in self.robots:
            raise ValueError("机器人不存在。")
        return self.robots[robot_id]

    def _load(self) -> None:
        if not STATE_PATH.exists():
            return
        try:
            raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return
        for item in raw.get("robots", []):
            events = [RobotEvent(**event) for event in item.get("events", [])]
            item["events"] = events
            robot = StrategyRobot(**item)
            self.robots[robot.id] = robot

    def _save(self) -> None:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {"robots": [robot.to_dict() for robot in self.robots.values()]}
        STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_robot_manager() -> RobotManager:
    global _ROBOT_MANAGER
    try:
        return _ROBOT_MANAGER
    except NameError:
        _ROBOT_MANAGER = RobotManager()
        return _ROBOT_MANAGER


def _evaluate_strategy(strategy: dict[str, Any], price: float) -> tuple[str, str]:
    strategy_type = str(strategy.get("strategy_type") or "")
    action = str(strategy.get("action") or "WAIT").upper()
    entry = strategy.get("entry") if isinstance(strategy.get("entry"), dict) else {}

    if price <= 0:
        return "WAIT", "暂未取得有效价格，继续观察。"
    if strategy_type == "observe":
        return "WAIT", f"观察模式，当前价格 {price:.2f}。"
    if strategy_type == "grid":
        low = float(entry.get("low") or 0)
        high = float(entry.get("high") or 0)
        if low and high and low <= price <= high:
            return "WAIT", f"价格 {price:.2f} 在网格区间内，记录观察，不直接拆单。"
        return "WAIT", f"价格 {price:.2f} 不在网格区间，等待。"
    if strategy_type == "dca":
        return "WAIT", f"DCA 策略已就绪，当前价格 {price:.2f}；连续加仓仍需后续版本启用。"

    trigger_price = float(entry.get("price") or 0)
    if not trigger_price:
        return "WAIT", f"当前价格 {price:.2f}，入场价格未确认。"
    operator = str(entry.get("operator") or "")
    if action == "BUY" and operator in {"cross_above", "touch_or_above"} and price >= trigger_price:
        return "BUY", f"当前价格 {price:.2f} 已达到做多触发价 {trigger_price:.2f}"
    if action == "BUY" and operator == "touch_or_below" and price <= trigger_price:
        return "BUY", f"当前价格 {price:.2f} 已回调到 {trigger_price:.2f}"
    if action == "SELL" and operator in {"cross_below", "touch_or_below"} and price <= trigger_price:
        return "SELL", f"当前价格 {price:.2f} 已达到做空触发价 {trigger_price:.2f}"
    return "WAIT", f"当前价格 {price:.2f}，等待触发价 {trigger_price:.2f}。"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
