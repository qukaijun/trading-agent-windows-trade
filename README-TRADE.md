# Trading Agent Windows - 交易版 (Trade Edition)

独立交易版本。基于 trading-agent-windows-mvp 扩展，新增贵金属/商品 + 实盘 MT5 交易能力。

## 与原版区别

| 能力 | 原版 (mvp) | 交易版 (trade) |
|------|-----------|---------------|
| A股/港股/美股 | ✅ | ✅ |
| 加密货币 | ✅ | ✅ |
| 贵金属/商品 (XAUUSD/XAGUSD) | ❌ | ✅ |
| MT5 模拟盘 | ✅ | ✅ |
| MT5 实盘 | ❌ 硬编码禁止 | ✅ 环境变量开关 |
| 实盘风控 (量/止损) | ❌ | ✅ |

## 启动

```powershell
cd trading-agent-windows-trade
..\trading-agent-windows-mvp\.venv\Scripts\python.exe -m agent_host
```

## MT5 实盘配置

```powershell
# 开启实盘
$env:MT5_LIVE_TRADING_ENABLED = "1"
$env:MT5_MAX_LIVE_VOLUME = "0.01"   # 最大下单量

# 关闭实盘（默认）
$env:MT5_LIVE_TRADING_ENABLED = "0"
```

## API

- `GET /api/mt5/signal.txt` — MT5 EA 轮询信号
- `POST /api/mt5/signal` — 发送交易信号 (Form 参数)
- `GET /api/mt5/config` — 查看 MT5 配置状态
- `POST /api/mt5/clear-signal` — 清除信号

## 实盘安全规则

实盘信号必须满足全部条件才会被接受：
1. `MT5_LIVE_TRADING_ENABLED=1`
2. `auto_trade_allowed=true`
3. `sl > 0` 且 `tp > 0`（止损止盈必填）
4. `volume` ≤ `MT5_MAX_LIVE_VOLUME`

## 版本管理

- 原版 (mvp)：投研分析，不做实盘
- 交易版 (trade)：投研 + 实盘/模拟盘交易

上游 TradingAgents 开源，Apache-2.0。本项目是中文服务化包装，不销售开源软件本体。
