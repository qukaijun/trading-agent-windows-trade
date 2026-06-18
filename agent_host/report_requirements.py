from __future__ import annotations

from typing import Any


REQUIRED_FIELDS = {
    "basic": ["最新价格", "日线", "最新交易日"],
    "fundamental_basic": ["最新价格", "日线", "公司资料"],
    "crypto_basic": ["最新价格", "日线", "最新交易日"],
}


def check_report_requirements(snapshot: dict[str, Any], report_template: str = "basic") -> dict[str, Any]:
    template = report_template or "basic"
    required = REQUIRED_FIELDS.get(template, REQUIRED_FIELDS["basic"])
    used = set(str(item) for item in snapshot.get("used_fields", []))
    missing = [field for field in required if field not in used]
    if snapshot.get("status") != "ok":
        return {
            "ok": False,
            "message": snapshot.get("message") or "当前数据源暂时不可用，请切换数据源或稍后重试。",
            "required_fields": required,
            "missing_required_fields": missing or list(snapshot.get("missing_fields", [])),
        }
    if missing:
        return {
            "ok": False,
            "message": f"当前主数据源缺少{', '.join(missing)}字段，无法生成所选报告。请切换数据源或选择基础行情版。",
            "required_fields": required,
            "missing_required_fields": missing,
        }
    return {"ok": True, "message": "字段检查通过。", "required_fields": required, "missing_required_fields": []}
