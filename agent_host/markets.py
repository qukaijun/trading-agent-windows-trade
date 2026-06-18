from __future__ import annotations

import re
from dataclasses import asdict, dataclass


CN_NAME_ALIASES = {
    "贵州茅台": "600519.SH",
    "平安银行": "000001.SZ",
    "腾讯控股": "00700.HK",
    "阿里巴巴": "09988.HK",
    "英伟达": "NVDA",
    "苹果": "AAPL",
    "微软": "MSFT",
    "拼多多": "PDD",
    "BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD", "XRP": "XRP-USD", "DOGE": "DOGE-USD", "BNB": "BNB-USD", "ADA": "ADA-USD",
}

COMMODITY_ALIASES = {
    "XAUUSD": "GC=F", "XAU": "GC=F", "GOLD": "GC=F",
    "XAGUSD": "SI=F", "XAG": "SI=F", "SILVER": "SI=F",
}


@dataclass(frozen=True)
class NormalizedSymbol:
    raw: str
    market: str
    canonical: str
    yfinance: str
    display: str
    confidence: str
    notes: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def normalize_symbol(raw_symbol: str) -> NormalizedSymbol:
    raw = raw_symbol.strip()
    if not raw:
        raise ValueError("请输入要分析的股票代码")

    alias = CN_NAME_ALIASES.get(raw) or COMMODITY_ALIASES.get(raw.upper())
    symbol = (alias or raw).strip().upper().replace(" ", "")

    prefixed = _normalize_prefixed(symbol, raw)
    if prefixed:
        return prefixed

    if re.fullmatch(r"\d{6}\.(SH|SZ|SS)", symbol):
        code, suffix = symbol.split(".")
        canonical_suffix = "SH" if suffix in {"SH", "SS"} else "SZ"
        yf_suffix = "SS" if canonical_suffix == "SH" else "SZ"
        return NormalizedSymbol(raw, "A", f"{code}.{canonical_suffix}", f"{code}.{yf_suffix}", f"A股 {code}.{canonical_suffix}", "high")

    if re.fullmatch(r"\d{6}", symbol):
        suffix = _guess_a_share_suffix(symbol)
        yf_suffix = "SS" if suffix == "SH" else "SZ"
        return NormalizedSymbol(raw, "A", f"{symbol}.{suffix}", f"{symbol}.{yf_suffix}", f"A股 {symbol}.{suffix}", "medium", "已按代码前缀推断交易所，请在正式分析前确认。")

    if re.fullmatch(r"\d{1,5}\.HK", symbol):
        code = symbol.split(".")[0].zfill(5)
        return NormalizedSymbol(raw, "HK", f"{code}.HK", f"{code}.HK", f"港股 {code}.HK", "high")

    if re.fullmatch(r"\d{1,5}", symbol):
        code = symbol.zfill(5)
        return NormalizedSymbol(raw, "HK", f"{code}.HK", f"{code}.HK", f"港股 {code}.HK", "medium", "纯数字且不足 6 位，已按港股代码处理。")

    # ── Commodity (Gold/Silver) ──
    upper_sym = symbol.upper()
    if upper_sym in COMMODITY_ALIASES or re.fullmatch(r"^(XAUUSD|XAU|XAGUSD|XAG|GC=F|SI=F|GOLD|SILVER)$", upper_sym):
        yf_sym = COMMODITY_ALIASES.get(upper_sym, symbol)
        display_name = "黄金" if any(kw in upper_sym for kw in ("XAU", "GC", "GOLD")) else "白银"
        return NormalizedSymbol(raw, "COMMODITY", symbol, yf_sym, f"{display_name} {symbol}", "high")

    # ── Crypto ──
    if re.fullmatch(r"^[A-Z]{2,6}(-USD|-USDT)?$", symbol) and symbol not in {"NVDA", "AAPL", "MSFT", "PDD", "TSM"}:
        base = symbol.split("-")[0]
        return NormalizedSymbol(raw, "CRYPTO", base, f"{base}-USD", f"加密货币 {base}", "high")

    if re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", symbol):
        return NormalizedSymbol(raw, "US", symbol, symbol, f"美股 {symbol}", "medium" if alias else "high")

    return NormalizedSymbol(raw, "UNKNOWN", symbol, symbol, symbol, "low", "无法自动识别市场，请使用 A:600519.SH、HK:00700 或 US:NVDA 这类格式。")


def symbol_for_provider(symbol: NormalizedSymbol, provider_key: str) -> str:
    if symbol.market == "CRYPTO":
        return f"{symbol.canonical}-USD"
    if symbol.market == "COMMODITY":
        return symbol.yfinance
    if symbol.market == "US":
        if provider_key == "eodhd":
            return symbol.canonical if symbol.canonical.endswith(".US") else f"{symbol.canonical}.US"
        return symbol.canonical.replace(".US", "")
    return symbol.canonical


def market_name(market: str) -> str:
    return {"A": "A股", "HK": "港股", "US": "美股", "CRYPTO": "加密货币", "COMMODITY": "贵金属/商品"}.get(market, "未知市场")


def _normalize_prefixed(symbol: str, raw: str) -> NormalizedSymbol | None:
    if ":" not in symbol:
        return None
    prefix, value = symbol.split(":", 1)
    value = value.strip().upper()
    if prefix in {"A", "CN"}:
        if re.fullmatch(r"\d{6}", value):
            value = f"{value}.{_guess_a_share_suffix(value)}"
        if re.fullmatch(r"\d{6}\.(SH|SZ|SS)", value):
            normalized = normalize_symbol(value)
            return NormalizedSymbol(raw, normalized.market, normalized.canonical, normalized.yfinance, normalized.display, "high", normalized.notes)
    if prefix in {"HK", "H"}:
        value = value.replace(".HK", "")
        if re.fullmatch(r"\d{1,5}", value):
            normalized = normalize_symbol(f"{value}.HK")
            return NormalizedSymbol(raw, normalized.market, normalized.canonical, normalized.yfinance, normalized.display, "high", normalized.notes)
    if prefix in {"CRYPTO", "C", "COIN"}:
        value = value.replace("-USD", "").replace("-USDT", "").upper()
        return NormalizedSymbol(raw, "CRYPTO", value, f"{value}-USD", f"加密货币 {value}", "high")
    if prefix in {"COMMODITY", "CMD", "GOLD", "METAL"}:
        value = value.upper()
        yf_sym = COMMODITY_ALIASES.get(value, value)
        return NormalizedSymbol(raw, "COMMODITY", value, yf_sym, f"贵金属/商品 {value}", "high")
    if prefix in {"US", "USA"} and re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", value):
        return NormalizedSymbol(raw, "US", value, value, f"美股 {value}", "high")
    return None


def _guess_a_share_suffix(code: str) -> str:
    if code.startswith(("5", "6", "9")):
        return "SH"
    return "SZ"
