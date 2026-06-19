from __future__ import annotations

import json
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal


Action = Literal["WAIT", "BUY", "SELL"]
TradeMode = Literal["DEMO", "LIVE"]
RUNTIME_DIR = Path(__file__).resolve().parents[1] / "runtime"
SIGNAL_PATH = RUNTIME_DIR / "mt5_signal.json"


@dataclass(frozen=True)
class Mt5Signal:
    signal_id: str
    symbol: str
    action: Action
    volume: float
    sl: float
    tp: float
    comment: str
    source: str
    created_at: str
    expires_at: str
    trade_mode: TradeMode = "DEMO"
    auto_trade_allowed: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_text(self) -> str:
        fields = {
            "id": self.signal_id,
            "symbol": self.symbol,
            "action": self.action,
            "volume": _format_number(self.volume),
            "sl": _format_number(self.sl),
            "tp": _format_number(self.tp),
            "auto": "1" if self.auto_trade_allowed else "0",
            "trade_mode": self.trade_mode,
            "demo_only": "1" if self.trade_mode == "DEMO" else "0",
            "expires_at": self.expires_at,
            "comment": _safe_text(self.comment),
        }
        return ";".join(f"{key}={value}" for key, value in fields.items())


def get_signal() -> Mt5Signal:
    if not SIGNAL_PATH.exists():
        return _default_signal()
    try:
        payload = json.loads(SIGNAL_PATH.read_text(encoding="utf-8"))
        signal = Mt5Signal(
            signal_id=str(payload.get("signal_id", "")) or _new_signal_id(),
            symbol=str(payload.get("symbol", "CHART")).strip().upper() or "CHART",
            action=_normalize_action(str(payload.get("action", "WAIT"))),
            volume=max(0.0, float(payload.get("volume", 0.0))),
            sl=max(0.0, float(payload.get("sl", 0.0))),
            tp=max(0.0, float(payload.get("tp", 0.0))),
            comment=str(payload.get("comment", ""))[:120],
            source=str(payload.get("source", "TradingAgentAssistant"))[:80],
            created_at=str(payload.get("created_at", "")) or _now_iso(),
            expires_at=str(payload.get("expires_at", "")) or _expiry_iso(15),
            trade_mode=_normalize_trade_mode(str(payload.get("trade_mode", "DEMO"))),
            auto_trade_allowed=bool(payload.get("auto_trade_allowed", False)),
        )
    except Exception:
        return _default_signal(comment="Invalid stored MT5 signal; reset to WAIT.")

    if _is_expired(signal.expires_at):
        return _default_signal(comment="Stored MT5 signal expired; reset to WAIT.")
    return signal


def save_signal(
    *,
    symbol: str,
    action: str,
    volume: float,
    sl: float = 0.0,
    tp: float = 0.0,
    comment: str = "",
    ttl_minutes: int = 15,
    auto_trade_allowed: bool = False,
    trade_mode: str = "DEMO",
) -> Mt5Signal:
    normalized_action = _normalize_action(action)
    normalized_mode = _normalize_trade_mode(trade_mode)
    ttl = min(max(int(ttl_minutes), 1), 240)
    signal = Mt5Signal(
        signal_id=_new_signal_id(),
        symbol=(symbol or "CHART").strip().upper() or "CHART",
        action=normalized_action,
        volume=max(0.0, float(volume)),
        sl=max(0.0, float(sl)),
        tp=max(0.0, float(tp)),
        comment=comment[:120],
        source="TradingAgentAssistant",
        created_at=_now_iso(),
        expires_at=_expiry_iso(ttl),
        trade_mode=normalized_mode,
        auto_trade_allowed=bool(auto_trade_allowed),
    )
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    SIGNAL_PATH.write_text(
        json.dumps(signal.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_mt5_file(signal)
    return signal


def clear_signal() -> Mt5Signal:
    signal = _default_signal(comment="Signal cleared.")
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    SIGNAL_PATH.write_text(
        json.dumps(signal.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return signal


def _default_signal(comment: str = "No active signal.") -> Mt5Signal:
    return Mt5Signal(
        signal_id="WAIT",
        symbol="CHART",
        action="WAIT",
        volume=0.0,
        sl=0.0,
        tp=0.0,
        comment=comment,
        source="TradingAgentAssistant",
        created_at=_now_iso(),
        expires_at=_expiry_iso(15),
        trade_mode="DEMO",
        auto_trade_allowed=False,
    )


def _normalize_action(action: str) -> Action:
    value = action.strip().upper()
    if value in {"BUY", "LONG"}:
        return "BUY"
    if value in {"SELL", "SHORT"}:
        return "SELL"
    return "WAIT"


def _normalize_trade_mode(value: str) -> TradeMode:
    mode = value.strip().upper()
    if mode in {"LIVE", "REAL"}:
        return "LIVE"
    return "DEMO"


def _write_mt5_file(signal: Mt5Signal) -> None:
    mt5_files = Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal"
    if not mt5_files.exists():
        return
    for instance in mt5_files.iterdir():
        files_dir = instance / "MQL5" / "Files"
        if files_dir.exists():
            demo = "1" if signal.trade_mode == "DEMO" else "0"
            text = (
                f"id={signal.signal_id}\n"
                f"symbol={signal.symbol}\n"
                f"action={signal.action}\n"
                f"volume={signal.volume}\n"
                f"sl={signal.sl}\n"
                f"tp={signal.tp}\n"
                f"comment={signal.comment}\n"
                f"demo={demo}\n"
                f"mode={signal.trade_mode}\n"
                f"auto={'1' if signal.auto_trade_allowed else '0'}\n"
            )
            (files_dir / "ta_signal.txt").write_text(text, encoding="ascii")
            break


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _expiry_iso(ttl_minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)).isoformat(
        timespec="seconds"
    )


def _is_expired(value: str) -> bool:
    try:
        expiry = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return True
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return expiry < datetime.now(timezone.utc)


def _new_signal_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"TA-{stamp}-{secrets.token_hex(3).upper()}"


def _format_number(value: float) -> str:
    if value <= 0:
        return "0"
    return f"{value:.8f}".rstrip("0").rstrip(".")


def _safe_text(value: str) -> str:
    return value.replace(";", ",").replace("\r", " ").replace("\n", " ")[:120]
