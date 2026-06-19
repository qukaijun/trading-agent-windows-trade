"""Lightweight trading scheduler - runs AI analysis on configured symbols at intervals."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

from agent_host.markets import normalize_symbol
from agent_host.runner import analyze_with_tradingagents, _extract_trading_signal
from agent_host.mt5_bridge import save_signal

logger = logging.getLogger("trading.scheduler")

# ─── Default config ──────────────────────────────────
DEFAULT_SYMBOLS = ["GOLD", "BTC-USD"]
DEFAULT_INTERVAL_MINUTES = 30
DEFAULT_TEMPLATE = "crypto_basic"
DEFAULT_DATA_SOURCE = "yfinance"


class TradingScheduler:
    """Runs analysis + signal on a configurable interval."""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self.symbols: list[str] = list(DEFAULT_SYMBOLS)
        self.interval_minutes: int = DEFAULT_INTERVAL_MINUTES
        self.template: str = DEFAULT_TEMPLATE
        self.data_source: str = DEFAULT_DATA_SOURCE
        self.auto_signal: bool = True
        self.last_runs: list[dict[str, Any]] = []  # last 20 entries
        self.next_run_at: str | None = None

    def status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "symbols": self.symbols,
            "interval_minutes": self.interval_minutes,
            "template": self.template,
            "data_source": self.data_source,
            "auto_signal": self.auto_signal,
            "next_run_at": self.next_run_at,
            "last_runs": self.last_runs[-5:],
        }

    def configure(self, config: dict[str, Any]) -> dict[str, Any]:
        if "symbols" in config and isinstance(config["symbols"], list):
            self.symbols = [str(s) for s in config["symbols"]]
        if "interval_minutes" in config:
            self.interval_minutes = max(1, min(240, int(config["interval_minutes"])))
        if "template" in config:
            self.template = str(config["template"])
        if "data_source" in config:
            self.data_source = str(config["data_source"])
        if "auto_signal" in config:
            self.auto_signal = bool(config["auto_signal"])
        return self.status()

    async def start(self) -> dict[str, Any]:
        if self._running:
            return {"message": "already running", **self.status()}
        self._running = True
        self._task = asyncio.create_task(self._loop())
        return {"message": "started", **self.status()}

    async def stop(self) -> dict[str, Any]:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self.next_run_at = None
        return {"message": "stopped", **self.status()}

    async def run_once(self) -> dict[str, Any]:
        """Run analysis for all symbols immediately."""
        results = []
        for sym in self.symbols:
            try:
                normalized = normalize_symbol(sym)
                result = analyze_with_tradingagents(
                    normalized,
                    data_source=self.data_source,
                    report_template=self.template,
                )
                ts = result.get("trading_signal")
                signal_sent = False
                if self.auto_signal and ts and ts.get("action") in ("BUY", "SELL"):
                    try:
                        save_signal(
                            symbol=normalized.canonical,
                            action=ts["action"],
                            volume=float(ts.get("volume", 0.1)),
                            sl=float(ts.get("sl", 0) or 0),
                            tp=float(ts.get("tp", 0) or 0),
                            comment=f"auto-{ts.get('action','?')} conf:{ts.get('confidence',0)}",
                            ttl_minutes=max(self.interval_minutes + 5, 10),
                            auto_trade_allowed=True,
                            trade_mode="DEMO",
                        )
                        signal_sent = True
                    except Exception:
                        pass
                entry = {
                    "symbol": sym,
                    "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "action": ts.get("action", "?") if ts else "?",
                    "confidence": ts.get("confidence", 0) if ts else 0,
                    "signal_sent": signal_sent,
                }
            except Exception as e:
                entry = {"symbol": sym, "time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "error": str(e)[:100]}
            results.append(entry)
        self.last_runs.extend(results)
        if len(self.last_runs) > 20:
            self.last_runs = self.last_runs[-20:]
        return {"runs": results}

    async def _loop(self) -> None:
        while self._running:
            now = datetime.now(timezone.utc)
            self.next_run_at = (now.replace(second=0, microsecond=0)).isoformat()
            try:
                await self.run_once()
            except Exception as e:
                logger.error("Scheduler run failed: %s", e)
            # Sleep for the interval
            for _ in range(self.interval_minutes * 60):
                if not self._running:
                    break
                await asyncio.sleep(1)


# ─── Singleton ────────────────────────────────────────
_scheduler: TradingScheduler | None = None


def get_scheduler() -> TradingScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = TradingScheduler()
    return _scheduler