from __future__ import annotations

import importlib.util
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_host.app_meta import (
    APP_MODE,
    APP_NAME,
    APP_VERSION,
    BOUNDARIES,
    OPEN_SOURCE_NOTICE,
    SERVICE_POSITIONING,
)
from agent_host.config_manager import read_config_status
from agent_host.data_source_registry import all_sources
from agent_host.report_store import INDEX_PATH, list_report_records
from agent_host.runner import UPSTREAM


ROOT = Path(__file__).resolve().parents[1]
DEPENDENCIES = [
    ("fastapi", "FastAPI 服务"),
    ("uvicorn", "服务启动器"),
    ("yfinance", "yfinance 行情"),
    ("akshare", "Akshare 数据源"),
    ("tushare", "Tushare 数据源"),
    ("docx", "Word 导出"),
    ("reportlab", "PDF 导出"),
]


def build_diagnostics() -> dict[str, Any]:
    config = read_config_status()
    reports = list_report_records(limit=5)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "app": {"name": APP_NAME, "version": APP_VERSION},
        "system": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "service": {
            "status": "healthy",
            "mode": APP_MODE,
            "live_trading": "disabled",
            "positioning": SERVICE_POSITIONING,
            "info": config.get("service", {}),
        },
        "open_source_notice": OPEN_SOURCE_NOTICE,
        "config": config,
        "data_sources": [source.to_dict() for source in all_sources()],
        "upstream": {
            "available": UPSTREAM.exists(),
            "status": "available" if UPSTREAM.exists() else "missing",
        },
        "dependencies": [_dependency_status(module, label) for module, label in DEPENDENCIES],
        "reports": {
            "index_exists": INDEX_PATH.exists(),
            "count": reports.get("count", 0),
            "recent": reports.get("reports", []),
        },
        "runtime_assets": {
            "logs": "available",
            "runtime": "available",
            "wheelhouse": "available" if (ROOT / "wheelhouse").exists() else "missing",
            "upstream": "available" if UPSTREAM.exists() else "missing",
        },
        "boundaries": BOUNDARIES,
        "privacy_note": "诊断信息仅保留状态，不展示完整密钥、内部绝对路径或原始异常。",
    }


def diagnostics_text(payload: dict[str, Any] | None = None) -> str:
    data = payload or build_diagnostics()
    config = data.get("config", {})
    data_tokens = config.get("data_tokens", {})
    lines = [
        "TradingAgents 中文服务工作台诊断信息",
        f"生成时间：{data.get('generated_at')}",
        "",
        "应用",
        f"- 名称：{data['app'].get('name')}",
        f"- 版本：{data['app'].get('version')}",
        "",
        "模型配置",
        f"- 供应商：{config.get('provider') or '未配置'}",
        f"- 模型：{config.get('model') or '未配置'}",
        f"- 模型密钥：{'已配置' if config.get('api_key_configured') else '未配置'}",
        "",
        "数据源配置",
        f"- EODHD：{'已配置' if data_tokens.get('eodhd') else '未配置'}",
        f"- FMP：{'已配置' if data_tokens.get('fmp') else '未配置'}",
        f"- Alpha Vantage：{'已配置' if data_tokens.get('alpha_vantage') else '未配置'}",
        f"- Tushare：{'已配置' if data_tokens.get('tushare') else '未配置'}",
        "",
        "运行状态",
        f"- 服务：{data['service'].get('status')}",
        f"- 实盘交易：{data['service'].get('live_trading')}",
        f"- 上游 TradingAgents：{data['upstream'].get('status')}",
        "",
        "依赖",
    ]
    for item in data.get("dependencies", []):
        lines.append(f"- {item['label']} / {item['module']}：{item['status']}")
    lines.extend(
        [
            "",
            "报告",
            f"- 报告数量：{data['reports'].get('count')}",
            "",
            "边界",
        ]
    )
    lines.extend(f"- {item}" for item in data.get("boundaries", []))
    lines.extend(
        [
            "",
            "脱敏说明",
            "- 本诊断信息不展示完整密钥、内部绝对路径或原始异常详情。",
            "- 如需进一步排查，请将本页内容交给服务人员，不要另行粘贴密钥。",
        ]
    )
    return "\n".join(lines)


def _dependency_status(module: str, label: str) -> dict[str, Any]:
    spec = importlib.util.find_spec(module)
    return {
        "module": module,
        "label": label,
        "status": "ok" if spec else "missing",
    }
