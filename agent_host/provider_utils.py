from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def get_json(url: str, params: dict[str, Any], *, timeout: int = 15, attempts: int = 2) -> tuple[int, Any, str]:
    query = urllib.parse.urlencode({key: value for key, value in params.items() if value is not None})
    full_url = f"{url}?{query}" if query else url
    request = urllib.request.Request(full_url, headers={"User-Agent": "TradingAgentServiceWorkbench/1.0"})
    last_error = ""
    for index in range(max(1, attempts)):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                return int(response.status), json.loads(body) if body else {}, ""
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                data = {"message": body[:500]}
            return int(exc.code), data, ""
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            if index < attempts - 1:
                time.sleep(0.8)
    return 0, {}, last_error


def customer_error_message(source_name: str, status_code: int, technical_error: str = "") -> str:
    if status_code in {401, 403}:
        return f"{source_name} 当前 Token 权限不足，无法获取本次报告所需字段。请更换数据源或升级套餐后重试。"
    if status_code == 402:
        return f"{source_name} 当前订阅权限不足，无法获取该标的的报告字段。请更换数据源或升级套餐后重试。"
    if status_code == 429:
        return f"{source_name} 当前访问频率受限，请稍后重试，或联系服务人员检查数据源套餐。"
    if status_code == 0:
        return f"{source_name} 暂时无法访问，可能是网络或第三方服务限制。请稍后重试，或导出诊断包交给服务人员。"
    if technical_error:
        return f"{source_name} 数据获取失败，请稍后重试，或导出诊断包交给服务人员。"
    return f"{source_name} 暂时未返回可用数据，请确认标的代码和数据源状态。"
