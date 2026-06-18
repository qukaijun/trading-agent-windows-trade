from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "runtime" / "reports"
INDEX_PATH = REPORT_DIR / "index.json"
MAX_INDEX_ITEMS = 200


def save_report_record(
    *,
    symbol: dict[str, str],
    analysis_date: str,
    status: str,
    title: str,
    markdown: str,
    model_provider: str = "",
    model: str = "",
    data_source: str = "",
    mapped_symbol: str = "",
    data_timestamp: str = "",
) -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report_id = _build_report_id(symbol=symbol, analysis_date=analysis_date, created_at=created_at)
    filename = f"{report_id}.md"
    report_path = REPORT_DIR / filename
    report_path.write_text(markdown or "", encoding="utf-8")

    record = {
        "id": report_id,
        "title": title,
        "status": status,
        "symbol": symbol,
        "analysis_date": analysis_date,
        "created_at": created_at,
        "model_provider": model_provider,
        "model": model,
        "data_source": data_source,
        "mapped_symbol": mapped_symbol,
        "data_timestamp": data_timestamp,
        "markdown_file": filename,
    }

    records = _read_index()
    records = [item for item in records if item.get("id") != report_id]
    records.insert(0, record)
    _write_index(records[:MAX_INDEX_ITEMS])
    return record


def list_report_records(limit: int = 30) -> dict[str, Any]:
    safe_limit = max(1, min(int(limit or 30), MAX_INDEX_ITEMS))
    records = _read_index()
    return {"reports": records[:safe_limit], "count": len(records)}


def get_report_record(report_id: str) -> dict[str, Any] | None:
    for record in _read_index():
        if record.get("id") == report_id:
            return record
    return None


def get_report_markdown(report_id: str) -> str | None:
    record = get_report_record(report_id)
    if not record:
        return None
    filename = str(record.get("markdown_file", ""))
    path = (REPORT_DIR / filename).resolve()
    if REPORT_DIR.resolve() not in path.parents and path != REPORT_DIR.resolve():
        return None
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _read_index() -> list[dict[str, Any]]:
    if not INDEX_PATH.exists():
        return []
    try:
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _write_index(records: list[dict[str, Any]]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_report_id(*, symbol: dict[str, str], analysis_date: str, created_at: str) -> str:
    canonical = symbol.get("canonical") or symbol.get("yfinance") or symbol.get("raw") or "symbol"
    base = f"{analysis_date}-{canonical}-{created_at}"
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", base).strip("-")
    return slug[:120]
