# Trading Agent Windows MVP

目标：新建一个独立的 Trading Agent 中文版 Windows 一键安装项目，用于投研、个股分析、策略研究和回测报告。首版不开放实盘自动交易。

定位说明：本项目基于开源 TradingAgents 生态做中文化、本地部署和服务交付。我们提供的是安装配置、模型/数据源接入、培训、运维和售后支持服务，不销售开源软件本体。

本项目不是 `vibetrading` 的延续，也不直接改第三方 `site-packages`。建议采用“上游 TradingAgents + 中文产品外壳 + 市场数据适配层 + Windows 安装器”的结构。

## 参考上游

- 原版：TauricResearch/TradingAgents
  - 多智能体金融交易研究框架
  - Apache-2.0
  - 支持多 LLM provider、Docker、CLI、持久化决策日志
- 中文增强版：hsliuping/TradingAgents-CN
  - 中文本地化
  - 支持 A 股、港股、美股分析与教学
  - FastAPI + Vue + MongoDB + Redis 架构

## 首版定位

- Windows 10/11 一键安装
- 中文配置向导
- 中文启动入口
- A 股、港股、美股行情/财务/新闻数据接入
- 多模型供应商配置：通义千问、DeepSeek、Kimi、智谱、MiniMax、硅基流动、OpenAI、OpenRouter、Ollama、自定义 OpenAI 兼容接口
- 网页配置和模型连接测试
- 行情快照和确定性行情数据摘要
- 中文投研报告整理
- 历史报告本地保存
- Markdown / Word / PDF 报告导出
- 系统诊断和诊断文本导出
- 本地报告导出与日志诊断
- 研究、学习、回测用途
- 首版运行模式：投研分析 / 模拟验证

## 首版不做

- 不开放实盘自动下单
- 不托管资金或券商账户
- 不承诺收益
- 不提供证券投资咨询
- 不把免费行情源包装成实盘级行情

## 建议目录

```text
trading-agent-windows-mvp/
  docs/                 产品、技术、合规和安装方案
  scripts/              Windows 安装、配置、启动、诊断脚本
  installer/            Inno Setup 安装器脚本
  agent_host/           我们自己的轻量包装层，后续对接上游 TradingAgents
  vendor/upstream/      上游源码快照或 Git 子模块，不手工散改
  wheelhouse/           后续生成离线 wheel 包
  runtime/              后续放 Python 安装器或运行时
  logs/                 本地运行日志
```

## 推荐路线

1. 固定上游底座：优先评估 TauricResearch/TradingAgents，吸收 TradingAgents-CN 的中文化和 A/HK/US 市场经验。
2. 做中文产品壳：配置、启动、错误提示、日志导出、风险确认全部中文化。
3. 做数据适配层：统一 symbol 规范和数据源优先级，避免 A 股、港股、美股代码混淆。
4. 做 Windows 一键安装：固定 Python 版本，生成 wheelhouse，Inno Setup 打包。
5. 实盘另开版本：需要券商 API、权限隔离、下单确认、审计日志、紧急停止和合规审查。

## 当前状态

项目骨架阶段。下一步建议先拉取上游源码做兼容性验证：

```powershell
.\scripts\fetch-upstream.ps1
.\scripts\bootstrap-dev.ps1
```

开发验证通过后，生成离线依赖包：

```powershell
.\scripts\build-wheelhouse.ps1
.\scripts\install-offline.ps1
```
