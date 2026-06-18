# MT5 EA 模拟盘使用说明

本功能用于把 Trading Agent Assistant 的本地模拟信号发送给 MT5 EA。当前交付版本只用于模拟盘验证，不开放实盘自动交易。

## 当前边界

- 只建议连接 MT5 模拟盘账号。
- 服务端会拒绝 `trade_mode=LIVE` 的实盘信号。
- EA 自动交易默认关闭，需要客户在模拟盘中手动开启。
- 任何实盘交易能力都应作为后续单独版本处理。

## 安装 EA

1. 打开 MT5。
2. 进入 `File -> Open Data Folder`。
3. 打开 `MQL5\Experts`。
4. 把 `mt5_ea\TradingAgentBridgeEA.mq5` 复制进去。
5. 使用 MetaEditor 编译。
6. 回到 MT5，在导航器里刷新 Expert Advisors。

## 允许本地 WebRequest

MT5 默认不允许 EA 访问 HTTP 地址。需要添加本地服务地址：

1. MT5 菜单进入 `Tools -> Options -> Expert Advisors`。
2. 勾选 `Allow WebRequest for listed URL`。
3. 添加：

```text
http://127.0.0.1:8787
```

## 模拟盘测试

启动 Trading Agent Assistant 后，检查服务：

```powershell
Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8787/health
```

发送模拟盘信号：

```powershell
Invoke-WebRequest -UseBasicParsing -Method POST -Uri "http://127.0.0.1:8787/api/mt5/signal?symbol=XAUUSD&action=BUY&volume=0.01&trade_mode=DEMO&auto_trade_allowed=true&comment=demo-test"
```

查看信号：

```powershell
Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8787/api/mt5/signal.txt
```

清空信号：

```powershell
Invoke-WebRequest -UseBasicParsing -Method POST -Uri http://127.0.0.1:8787/api/mt5/clear-signal
```

## 实盘信号保护

当前版本如果发送：

```text
trade_mode=LIVE
```

服务端会返回错误：

```text
首版不开放实盘信号，请使用 DEMO 模式。
```

## 交付建议

MT5 功能在首版只作为模拟盘演示项，不作为标准投研版核心卖点。客户正式交付时，应优先验收 A股、港股、美股投研分析流程。
