from __future__ import annotations

import os
from typing import Any

from agent_host.config_manager import providers_payload, read_config_status
from agent_host.data_source_registry import all_sources


SUPPORTED_MARKETS = [
    {"market": "A", "name": "A股", "examples": ["A:600519.SH", "600519", "000001.SZ"]},
    {"market": "HK", "name": "港股", "examples": ["HK:00700", "00700.HK", "9988"]},
    {"market": "US", "name": "美股", "examples": ["PDD", "US:PDD", "NVDA"]},
    {"market": "CRYPTO", "name": "加密货币", "examples": ["BTC", "ETH", "CRYPTO:BTC", "BTC-USD"]},
    {"market": "COMMODITY", "name": "贵金属/商品", "examples": ["XAUUSD", "GOLD:XAUUSD", "GC=F", "XAGUSD"]},
]


def current_runtime() -> dict[str, str]:
    config = read_config_status()
    provider = str(config.get("provider") or os.getenv("TRADINGAGENTS_LLM_PROVIDER", ""))
    model = str(config.get("model") or os.getenv("TRADINGAGENTS_DEEP_THINK_LLM", ""))
    return {
        "provider": provider or "未配置",
        "display_provider": provider or "未配置",
        "model": model or "未配置",
        "markets": str(config.get("markets") or "A,HK,US"),
        "trade_mode": "投研分析 / 非实盘",
    }


def capabilities_payload() -> dict[str, Any]:
    return {
        "runtime": current_runtime(),
        "model_providers": providers_payload(),
        "data_sources": [source.to_dict() for source in all_sources()],
        "supported_markets": SUPPORTED_MARKETS,
        "boundaries": [
            "本工具用于投研辅助、学习和模拟验证，不构成投资建议。",
            "本轮不开放实盘自动交易，不承诺收益。",
            "每份报告只使用一个主数据源，缺失字段会在报告中说明。",
            "第三方数据源可能延迟、缺失、限流或受套餐权限影响。",
        ],
    }
