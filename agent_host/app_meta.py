from __future__ import annotations

from typing import Any


APP_NAME = "TradingAgents 中文服务工作台"
APP_VERSION = "0.2.0-p0-analysis"
APP_EDITION = "P0 演示版"
APP_MODE = "投研分析 / 非实盘"

SERVICE_POSITIONING = "本项目基于开源 TradingAgents 生态做中文化、本地部署和服务交付；服务内容包括安装配置、模型与数据源接入、培训、运维和售后支持，不销售开源软件本体。"

OPEN_SOURCE_NOTICE = [
    "核心研究框架参考并集成开源 TradingAgents 项目。",
    "本地封装、安装脚本、中文文档、配置页、报告整理、诊断和交付流程属于服务交付增强。",
    "客户应遵守相关开源许可证、第三方模型服务条款和数据源使用条款。",
]

FEATURES = [
    "PDD / US:PDD 美股识别",
    "单报告单主数据源",
    "EODHD 基础行情版报告",
    "FMP 较完整基础报告候选路径",
    "中文投研报告整理",
    "Markdown / Word / PDF 报告导出",
    "系统诊断和售后诊断包导出",
]

BOUNDARIES = [
    "当前版本仅用于投研分析、策略研究、学习和模拟验证。",
    "不开放实盘自动交易，不代客户下单。",
    "模型输出不构成证券投资咨询、买卖建议或收益承诺。",
    "第三方数据源可能延迟、缺失、错误或限流。",
]

SERVICE_ITEMS = [
    "本地安装部署",
    "模型 API Key / Base URL 配置",
    "EODHD / FMP 数据源配置",
    "PDD / NVDA 演示路径验收",
    "报告导出和历史报告排查",
    "系统诊断和日志导出排查",
]

DOCS = [
    "安装说明.md",
    "使用手册.md",
    "大模型配置指南.md",
    "数据源配置指南.md",
    "风险提示与免责声明.md",
    "客户交付验收单.md",
]


def about_payload(service_info: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "edition": APP_EDITION,
        "mode": APP_MODE,
        "service_positioning": SERVICE_POSITIONING,
        "open_source_notice": OPEN_SOURCE_NOTICE,
        "features": FEATURES,
        "boundaries": BOUNDARIES,
        "service_items": SERVICE_ITEMS,
        "support_items": SERVICE_ITEMS,
        "docs": DOCS,
        "service_info": service_info or {},
    }
