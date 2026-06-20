import { useCallback, useEffect, useRef, useState, type ComponentType, type ReactNode } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bot,
  Brain,
  CandlestickChart,
  CheckCircle2,
  Clock3,
  Cpu,
  FileText,
  LayoutDashboard,
  Pause,
  Play,
  Power,
  Radio,
  RefreshCw,
  Send,
  Server,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Trash2,
  TrendingDown,
  TrendingUp,
  Wifi,
  Zap,
} from "lucide-react";
import KlineChart from "./components/KlineChart";
import {
  clearSignal,
  compileStrategy,
  configureScheduler,
  fetchCurrentSignal,
  fetchPrice,
  fetchReportMarkdown,
  fetchReports,
  fetchRobotsStatus,
  fetchSchedulerStatus,
  fetchStatus,
  fetchStrategyTemplates,
  removeRobot,
  runAnalysis,
  runRobotsOnce,
  runSchedulerOnce,
  sendSignal,
  startRobot,
  startScheduler,
  stopRobot,
  stopScheduler,
  type CompiledStrategy,
  type MarketPrice,
  type Mt5Signal,
  type SchedulerStatus,
  type StrategyRobot,
  type StrategyTemplate,
  type SystemStatus,
} from "./api";

type PageId = "workspace" | "analysis" | "signals" | "reports" | "automation";
type Icon = ComponentType<{ size?: number; className?: string }>;

type WatchItem = {
  symbol: string;
  label: string;
  name: string;
  venue: string;
};

type ReportItem = {
  id: string;
  title: string;
  analysis_date: string;
  status?: string;
};

type TradingSignalDraft = {
  action?: string;
  confidence?: number;
  volume?: number;
  sl?: number;
  tp?: number;
  reason?: string;
};

type AnalysisResult = Record<string, unknown> & {
  report?: string;
  signal_sent?: boolean;
  trading_signal?: TradingSignalDraft;
  market_snapshot?: Record<string, unknown>;
  symbol?: Record<string, unknown>;
};

type StrategyDraft = {
  symbol: string;
  template: string;
  action: string;
  volume: string;
  sl: string;
  tp: string;
  horizon: string;
  risk: string;
  intent: string;
  summary: string;
  checklist: string[];
};

const WATCHLIST: WatchItem[] = [
  { symbol: "GOLD", label: "GOLD", name: "黄金", venue: "GC=F" },
  { symbol: "BTC-USD", label: "BTC", name: "比特币", venue: "Crypto" },
  { symbol: "ETH-USD", label: "ETH", name: "以太坊", venue: "Crypto" },
  { symbol: "XAGUSD", label: "XAG", name: "白银", venue: "SI=F" },
];

const TEMPLATES = [
  { value: "basic", label: "综合分析" },
  { value: "crypto_basic", label: "加密货币" },
  { value: "technical", label: "技术分析" },
];

const NAV_ITEMS: Array<{ id: PageId; label: string; icon: Icon }> = [
  { id: "workspace", label: "交易工作台", icon: LayoutDashboard },
  { id: "analysis", label: "AI 分析", icon: Brain },
  { id: "signals", label: "交易信号", icon: Radio },
  { id: "reports", label: "报告中心", icon: FileText },
  { id: "automation", label: "自动调度", icon: SlidersHorizontal },
];

function cx(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(" ");
}

function fmtPrice(value?: number | null) {
  if (typeof value !== "number" || Number.isNaN(value)) return "--";
  if (Math.abs(value) >= 1000) return value.toLocaleString("en-US", { maximumFractionDigits: 2 });
  return value.toFixed(Math.abs(value) >= 1 ? 2 : 4);
}

function fmtPct(value?: number | null) {
  if (typeof value !== "number" || Number.isNaN(value)) return "--";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function fmtShortTime(iso?: string | null) {
  if (!iso) return "--";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "--";
  return date.toLocaleTimeString("zh-CN", { hour12: false, hour: "2-digit", minute: "2-digit" });
}

function actionText(action?: string) {
  if (action === "BUY") return "做多";
  if (action === "SELL") return "做空";
  return "等待";
}

function actionClass(action?: string) {
  if (action === "BUY") return "text-emerald-700 bg-emerald-50 border-emerald-200";
  if (action === "SELL") return "text-red-700 bg-red-50 border-red-200";
  return "text-neutral-600 bg-neutral-100 border-neutral-200";
}

function strategyTypeText(type?: string) {
  const names: Record<string, string> = {
    breakout: "突破",
    breakdown: "跌破",
    pullback: "回调",
    grid: "网格",
    dca: "分批",
    trend_following: "趋势跟随",
    rsi_reversal: "RSI 反转",
    observe: "只观察",
    discretionary: "自定义",
  };
  return names[type || ""] || type || "--";
}

function strategyStatusText(status?: string) {
  if (status === "ready") return "可模拟";
  if (status === "needs_confirmation") return "待补参数";
  if (status === "observe_only") return "只观察";
  return status || "--";
}

function riskText(level?: unknown) {
  if (level === "low") return "低";
  if (level === "high") return "高";
  if (level === "medium") return "中";
  return String(level || "--");
}

function robotStatusText(status?: string) {
  if (status === "running") return "运行中";
  if (status === "triggered") return "已触发";
  if (status === "stopped") return "已停止";
  return status || "--";
}

function robotStatusClass(status?: string) {
  if (status === "running") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (status === "triggered") return "border-amber-200 bg-amber-50 text-amber-700";
  if (status === "stopped") return "border-neutral-200 bg-neutral-100 text-neutral-600";
  return "border-neutral-200 bg-neutral-50 text-neutral-600";
}

function clampReport(text: string) {
  return text.length > 9000 ? `${text.slice(0, 9000)}\n\n...` : text;
}

function parseNaturalStrategy(input: string): StrategyDraft {
  const text = input.trim();
  const normalized = text.toLowerCase();
  const symbol = /btc|比特币|bitcoin/.test(normalized)
    ? "BTC-USD"
    : /eth|以太|ethereum/.test(normalized)
      ? "ETH-USD"
      : /白银|xag|silver/.test(normalized)
        ? "XAGUSD"
        : "GOLD";
  const template = /btc|eth|加密|比特币|以太|crypto/.test(normalized) ? "crypto_basic" : /技术|均线|突破|回调|支撑|压力|趋势/.test(text) ? "technical" : "basic";
  const action = /做空|看空|卖|sell|short/.test(normalized) ? "SELL" : /做多|看多|买|buy|long/.test(normalized) ? "BUY" : "WAIT";
  const horizon = /日内|短线|小时|h1|m30|30分钟|1小时/.test(normalized) ? "短线" : /波段|几天|周线|4小时|h4/.test(normalized) ? "波段" : "待确认";
  const risk = /保守|轻仓|小仓/.test(text) ? "保守" : /激进|重仓/.test(text) ? "激进" : "中性";
  const numbers = Array.from(text.matchAll(/\d+(?:\.\d+)?/g)).map((match) => match[0]);
  const sl = text.match(/(?:止损|sl)\s*[:：]?\s*(\d+(?:\.\d+)?)/i)?.[1] || "";
  const tp = text.match(/(?:止盈|目标|tp)\s*[:：]?\s*(\d+(?:\.\d+)?)/i)?.[1] || "";
  const volume = text.match(/(\d+(?:\.\d+)?)\s*(?:手|lot)/i)?.[1] || (risk === "保守" ? "0.01" : "0.10");
  const intent = text || "请分析黄金短线机会，优先用模拟盘验证。";
  const checklist = [
    `标的：${symbol}`,
    `方向：${actionText(action)}`,
    `周期：${horizon}`,
    `风险：${risk}`,
    sl || tp ? `风控：SL ${sl || "--"} / TP ${tp || "--"}` : "风控：等待 AI 给出 SL/TP",
  ];

  return {
    symbol,
    template,
    action,
    volume,
    sl: sl || (numbers.length >= 2 ? numbers[0] : ""),
    tp: tp || (numbers.length >= 2 ? numbers[1] : ""),
    horizon,
    risk,
    intent,
    summary: `我会把这句话整理成 ${symbol} 的${horizon}交易研究任务，先做 AI 分析，再用模拟盘信号验证。`,
    checklist,
  };
}

export default function App() {
  const [page, setPage] = useState<PageId>("workspace");
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [prices, setPrices] = useState<Record<string, MarketPrice | null>>({});
  const [signal, setSignal] = useState<Mt5Signal | null>(null);
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [scheduler, setScheduler] = useState<SchedulerStatus | null>(null);
  const [chartSymbol, setChartSymbol] = useState("GOLD");
  const [symbol, setSymbol] = useState("GOLD");
  const [template, setTemplate] = useState("basic");
  const [autoSignal, setAutoSignal] = useState(true);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [analysisText, setAnalysisText] = useState("");
  const [analysisError, setAnalysisError] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [strategyPrompt, setStrategyPrompt] = useState("帮我看黄金，偏短线，优先模拟盘，看看能不能做多");
  const [strategyDraft, setStrategyDraft] = useState<StrategyDraft | null>(null);
  const [strategyTemplates, setStrategyTemplates] = useState<StrategyTemplate[]>([]);
  const [compiledStrategy, setCompiledStrategy] = useState<CompiledStrategy | null>(null);
  const [robots, setRobots] = useState<StrategyRobot[]>([]);
  const [robotBusy, setRobotBusy] = useState(false);
  const [robotMessage, setRobotMessage] = useState("");
  const [sigSymbol, setSigSymbol] = useState("GOLD");
  const [sigAction, setSigAction] = useState("BUY");
  const [sigVolume, setSigVolume] = useState("0.10");
  const [sigSl, setSigSl] = useState("");
  const [sigTp, setSigTp] = useState("");
  const [sigMode, setSigMode] = useState("DEMO");
  const [sigAuto, setSigAuto] = useState(false);
  const [sigBusy, setSigBusy] = useState(false);
  const [sigMessage, setSigMessage] = useState("");
  const [sigError, setSigError] = useState("");
  const [viewingReportId, setViewingReportId] = useState("");
  const [viewingReport, setViewingReport] = useState("");
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const refreshTimer = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  const loadAll = useCallback(async () => {
    const [statusResult, signalResult, reportsResult, schedulerResult, templatesResult, robotsResult] = await Promise.allSettled([
      fetchStatus(),
      fetchCurrentSignal(),
      fetchReports(12),
      fetchSchedulerStatus(),
      fetchStrategyTemplates(),
      fetchRobotsStatus(),
    ]);

    if (statusResult.status === "fulfilled") setStatus(statusResult.value);
    if (signalResult.status === "fulfilled") setSignal(signalResult.value);
    if (reportsResult.status === "fulfilled") setReports((reportsResult.value.reports || []) as ReportItem[]);
    if (schedulerResult.status === "fulfilled") setScheduler(schedulerResult.value);
    if (templatesResult.status === "fulfilled") setStrategyTemplates(templatesResult.value.templates || []);
    if (robotsResult.status === "fulfilled") setRobots(robotsResult.value.robots || []);

    const quoteEntries = await Promise.all(
      WATCHLIST.map(async (item) => [item.symbol, await fetchPrice(item.symbol)] as const),
    );
    setPrices(Object.fromEntries(quoteEntries));
    setLastRefresh(new Date());
  }, []);

  useEffect(() => {
    void loadAll();
    refreshTimer.current = setInterval(() => void loadAll(), 30000);
    return () => {
      if (refreshTimer.current) clearInterval(refreshTimer.current);
    };
  }, [loadAll]);

  const activeSignal = signal && signal.action !== "WAIT" ? signal : null;
  const quoteList = WATCHLIST.map((item) => ({ ...item, price: prices[item.symbol] || null }));
  const availableQuotes = quoteList.filter((item) => item.price);
  const avgChange =
    availableQuotes.length > 0
      ? availableQuotes.reduce((sum, item) => sum + (item.price?.change_pct || 0), 0) / availableQuotes.length
      : 0;

  const handleAnalyze = async (targetSymbol = symbol, targetTemplate = template) => {
    const cleanSymbol = targetSymbol.trim();
    if (!cleanSymbol) return;
    setSymbol(cleanSymbol);
    setTemplate(targetTemplate);
    setAnalyzing(true);
    setAnalysisError("");
    setAnalysisText("");
    setAnalysisResult(null);
    try {
      const result = (await runAnalysis(cleanSymbol, targetTemplate, "yfinance", autoSignal)) as AnalysisResult;
      setAnalysisResult(result);
      setAnalysisText(typeof result.report === "string" ? result.report : JSON.stringify(result, null, 2));
      const normalized = result.symbol;
      setSigSymbol(String(normalized?.raw || normalized?.canonical || cleanSymbol));
      if (result.trading_signal?.action) setSigAction(String(result.trading_signal.action));
      if (typeof result.trading_signal?.volume === "number") setSigVolume(String(result.trading_signal.volume));
      if (typeof result.trading_signal?.sl === "number") setSigSl(String(result.trading_signal.sl));
      if (typeof result.trading_signal?.tp === "number") setSigTp(String(result.trading_signal.tp));
      void loadAll();
    } catch (error) {
      setAnalysisError(error instanceof Error ? error.message : String(error));
    } finally {
      setAnalyzing(false);
    }
  };

  const handleAnalyzeSymbol = (nextSymbol: string) => {
    setSymbol(nextSymbol);
    setChartSymbol(nextSymbol);
    setPage("analysis");
  };

  const applyCompiledStrategy = (strategy: CompiledStrategy) => {
    const targetTemplate = strategy.symbol.market === "CRYPTO" ? "crypto_basic" : strategy.strategy_type === "trend_following" ? "technical" : "basic";
    const stopLoss = strategy.exit.stop_loss;
    const takeProfit = strategy.exit.take_profit;
    const riskLevel = typeof strategy.risk.level === "string" ? strategy.risk.level : "medium";
    setCompiledStrategy(strategy);
    setStrategyDraft({
      symbol: strategy.symbol.raw,
      template: targetTemplate,
      action: strategy.action,
      volume: String(strategy.volume || 0.1),
      sl: String(stopLoss || ""),
      tp: String(takeProfit || ""),
      horizon: strategy.timeframe,
      risk: riskText(riskLevel),
      intent: strategy.prompt,
      summary: strategy.explain.join(" "),
      checklist: [
        `标的：${strategy.symbol.raw}`,
        `方向：${actionText(strategy.action)}`,
        `类型：${strategyTypeText(strategy.strategy_type)}`,
        `状态：${strategyStatusText(strategy.status)}`,
      ],
    });
    setSymbol(strategy.symbol.raw);
    setChartSymbol(strategy.symbol.raw);
    setTemplate(targetTemplate);
    setSigSymbol(strategy.symbol.raw);
    setSigAction(strategy.action);
    setSigVolume(String(strategy.volume || 0.1));
    setSigSl(String(stopLoss || ""));
    setSigTp(String(takeProfit || ""));
    setSigMode("DEMO");
    setSigAuto(false);
    setAutoSignal(false);
  };

  const handleStrategyPrompt = async () => {
    setAnalysisError("");
    setRobotMessage("");
    const fallbackDraft = parseNaturalStrategy(strategyPrompt);
    setStrategyDraft(fallbackDraft);
    try {
      const compiled = await compileStrategy({ prompt: strategyPrompt });
      applyCompiledStrategy(compiled.strategy);
    } catch (error) {
      setAnalysisError(error instanceof Error ? error.message : String(error));
      setCompiledStrategy(null);
      setSymbol(fallbackDraft.symbol);
      setChartSymbol(fallbackDraft.symbol);
      setTemplate(fallbackDraft.template);
      setSigSymbol(fallbackDraft.symbol);
      setSigAction(fallbackDraft.action);
      setSigVolume(fallbackDraft.volume);
      setSigSl(fallbackDraft.sl);
      setSigTp(fallbackDraft.tp);
    }
  };

  const handleTemplateCompile = async (templateId: string) => {
    const templateItem = strategyTemplates.find((item) => item.id === templateId);
    if (templateItem) setStrategyPrompt(templateItem.prompt);
    setAnalysisError("");
    setRobotMessage("");
    try {
      const compiled = await compileStrategy({ template_id: templateId });
      applyCompiledStrategy(compiled.strategy);
    } catch (error) {
      setAnalysisError(error instanceof Error ? error.message : String(error));
    }
  };

  const handleStartRobot = async () => {
    if (!compiledStrategy) {
      setRobotMessage("请先生成策略 JSON。");
      return;
    }
    setRobotBusy(true);
    setRobotMessage("");
    try {
      const robot = await startRobot(compiledStrategy);
      setRobots((current) => [robot, ...current.filter((item) => item.id !== robot.id)]);
      setRobotMessage(`${robot.name} 已启动模拟观察。`);
      void loadAll();
    } catch (error) {
      setRobotMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setRobotBusy(false);
    }
  };

  const handleRunRobotsOnce = async (robotId?: string) => {
    setRobotBusy(true);
    setRobotMessage("");
    try {
      const result = await runRobotsOnce(robotId);
      setRobots(result.robots || []);
      setRobotMessage(result.runs?.[0]?.message || "已执行一次模拟观察。");
      void loadAll();
    } catch (error) {
      setRobotMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setRobotBusy(false);
    }
  };

  const handleStopRobot = async (robotId: string) => {
    setRobotBusy(true);
    try {
      const robot = await stopRobot(robotId);
      setRobots((current) => current.map((item) => (item.id === robot.id ? robot : item)));
    } finally {
      setRobotBusy(false);
    }
  };

  const handleRemoveRobot = async (robotId: string) => {
    setRobotBusy(true);
    try {
      await removeRobot(robotId);
      setRobots((current) => current.filter((item) => item.id !== robotId));
    } finally {
      setRobotBusy(false);
    }
  };

  const handleUseAnalysisSignal = () => {
    if (analysisResult?.trading_signal?.action) setSigAction(String(analysisResult.trading_signal.action));
    if (typeof analysisResult?.trading_signal?.volume === "number") setSigVolume(String(analysisResult.trading_signal.volume));
    if (typeof analysisResult?.trading_signal?.sl === "number") setSigSl(String(analysisResult.trading_signal.sl));
    if (typeof analysisResult?.trading_signal?.tp === "number") setSigTp(String(analysisResult.trading_signal.tp));
    setPage("signals");
  };

  const handleSendSignal = async () => {
    setSigBusy(true);
    setSigMessage("");
    setSigError("");
    try {
      const nextSignal = await sendSignal({
        symbol: sigSymbol.trim() || "GOLD",
        action: sigAction,
        volume: Number.parseFloat(sigVolume) || 0.1,
        sl: Number.parseFloat(sigSl) || 0,
        tp: Number.parseFloat(sigTp) || 0,
        trade_mode: sigMode,
        auto_trade_allowed: sigAuto,
      });
      setSignal(nextSignal);
      setSigMessage(`${actionText(nextSignal.action)} ${nextSignal.symbol} 已发送`);
      void loadAll();
    } catch (error) {
      setSigError(error instanceof Error ? error.message : String(error));
    } finally {
      setSigBusy(false);
    }
  };

  const handleClearSignal = async () => {
    setSigBusy(true);
    setSigMessage("");
    setSigError("");
    try {
      await clearSignal();
      setSignal(null);
      setSigMessage("当前信号已清除");
      void loadAll();
    } catch (error) {
      setSigError(error instanceof Error ? error.message : String(error));
    } finally {
      setSigBusy(false);
    }
  };

  const handleOpenReport = async (reportId: string) => {
    setViewingReportId(reportId);
    setViewingReport("");
    setPage("reports");
    try {
      setViewingReport(await fetchReportMarkdown(reportId));
    } catch (error) {
      setViewingReport(error instanceof Error ? error.message : String(error));
    }
  };

  return (
    <div className="min-h-screen bg-[#f4f2ee] text-neutral-900">
      <div className="flex min-h-screen">
        <Sidebar page={page} onPageChange={setPage} status={status} scheduler={scheduler} />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar
            page={page}
            status={status}
            scheduler={scheduler}
            activeSignal={activeSignal}
            lastRefresh={lastRefresh}
            onRefresh={loadAll}
          />
          <main className="min-w-0 flex-1 overflow-auto px-5 py-4">
            {page === "workspace" && (
              <WorkspacePage
                quotes={quoteList}
                chartSymbol={chartSymbol}
                activeSignal={activeSignal}
                status={status}
                reports={reports}
                scheduler={scheduler}
                avgChange={avgChange}
                analysisResult={analysisResult}
                analyzing={analyzing}
                analysisError={analysisError}
                strategyPrompt={strategyPrompt}
                strategyDraft={strategyDraft}
                strategyTemplates={strategyTemplates}
                compiledStrategy={compiledStrategy}
                robots={robots}
                robotBusy={robotBusy}
                robotMessage={robotMessage}
                setStrategyPrompt={setStrategyPrompt}
                onChartSymbolChange={setChartSymbol}
                onAnalyzeSymbol={handleAnalyzeSymbol}
                onQuickAnalyze={(nextSymbol) => void handleAnalyze(nextSymbol)}
                onStrategyPrompt={() => void handleStrategyPrompt()}
                onTemplateCompile={(templateId) => void handleTemplateCompile(templateId)}
                onStartRobot={() => void handleStartRobot()}
                onRunRobotsOnce={(robotId) => void handleRunRobotsOnce(robotId)}
                onStopRobot={(robotId) => void handleStopRobot(robotId)}
                onRemoveRobot={(robotId) => void handleRemoveRobot(robotId)}
                onUseAnalysisSignal={handleUseAnalysisSignal}
                onOpenAnalysis={() => setPage("analysis")}
                onOpenSignals={() => setPage("signals")}
                onOpenAutomation={() => setPage("automation")}
                onOpenReport={handleOpenReport}
                orderTicket={
                  <OrderTicket
                    sigSymbol={sigSymbol}
                    setSigSymbol={setSigSymbol}
                    sigAction={sigAction}
                    setSigAction={setSigAction}
                    sigVolume={sigVolume}
                    setSigVolume={setSigVolume}
                    sigSl={sigSl}
                    setSigSl={setSigSl}
                    sigTp={sigTp}
                    setSigTp={setSigTp}
                    sigMode={sigMode}
                    setSigMode={setSigMode}
                    sigAuto={sigAuto}
                    setSigAuto={setSigAuto}
                    sigBusy={sigBusy}
                    sigMessage={sigMessage}
                    sigError={sigError}
                    onSend={handleSendSignal}
                    onClear={handleClearSignal}
                  />
                }
              />
            )}
            {page === "analysis" && (
              <AnalysisPage
                symbol={symbol}
                setSymbol={setSymbol}
                template={template}
                setTemplate={setTemplate}
                autoSignal={autoSignal}
                setAutoSignal={setAutoSignal}
                analyzing={analyzing}
                result={analysisResult}
                reportText={analysisText}
                error={analysisError}
                onAnalyze={handleAnalyze}
                onUseSignal={handleUseAnalysisSignal}
              />
            )}
            {page === "signals" && (
              <SignalsPage
                activeSignal={activeSignal}
                orderTicket={
                  <OrderTicket
                    sigSymbol={sigSymbol}
                    setSigSymbol={setSigSymbol}
                    sigAction={sigAction}
                    setSigAction={setSigAction}
                    sigVolume={sigVolume}
                    setSigVolume={setSigVolume}
                    sigSl={sigSl}
                    setSigSl={setSigSl}
                    sigTp={sigTp}
                    setSigTp={setSigTp}
                    sigMode={sigMode}
                    setSigMode={setSigMode}
                    sigAuto={sigAuto}
                    setSigAuto={setSigAuto}
                    sigBusy={sigBusy}
                    sigMessage={sigMessage}
                    sigError={sigError}
                    onSend={handleSendSignal}
                    onClear={handleClearSignal}
                  />
                }
              />
            )}
            {page === "reports" && (
              <ReportsPage
                reports={reports}
                viewingReportId={viewingReportId}
                viewingReport={viewingReport}
                onOpenReport={handleOpenReport}
                onCloseReport={() => setViewingReportId("")}
              />
            )}
            {page === "automation" && <AutomationPage scheduler={scheduler} status={status} onRefresh={loadAll} />}
          </main>
        </div>
      </div>
    </div>
  );
}

function Sidebar({
  page,
  onPageChange,
  status,
  scheduler,
}: {
  page: PageId;
  onPageChange: (page: PageId) => void;
  status: SystemStatus | null;
  scheduler: SchedulerStatus | null;
}) {
  return (
    <aside className="flex w-64 shrink-0 flex-col bg-[#111111] text-neutral-300">
      <div className="border-b border-white/10 px-5 py-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-emerald-500 text-black">
            <CandlestickChart size={22} />
          </div>
          <div>
            <div className="text-sm font-semibold tracking-wide text-white">TradingAgents</div>
            <div className="text-xs text-neutral-500">AI Trade Desk</div>
          </div>
        </div>
      </div>
      <nav className="flex-1 px-3 py-4">
        {NAV_ITEMS.map((item) => {
          const IconComponent = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => onPageChange(item.id)}
              className={cx(
                "mb-1 flex h-10 w-full items-center gap-3 rounded-md px-3 text-left text-sm transition-colors",
                page === item.id ? "bg-white text-neutral-950" : "text-neutral-400 hover:bg-white/10 hover:text-white",
              )}
            >
              <IconComponent size={17} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
      <div className="border-t border-white/10 p-4 text-xs">
        <StatusLine icon={Server} label="后端" ok={!!status?.healthy} value={status?.healthy ? "在线" : "异常"} />
        <StatusLine icon={Cpu} label="模型" ok={!!status?.model} value={status?.model || "未配置"} />
        <StatusLine icon={Clock3} label="调度" ok={!!scheduler?.running} value={scheduler?.running ? "运行中" : "已停止"} />
      </div>
    </aside>
  );
}

function StatusLine({ icon: IconComponent, label, value, ok }: { icon: Icon; label: string; value: string; ok: boolean }) {
  return (
    <div className="mb-2 flex items-center gap-2 text-neutral-400">
      <IconComponent size={14} className={ok ? "text-emerald-400" : "text-neutral-600"} />
      <span className="w-9">{label}</span>
      <span className="min-w-0 flex-1 truncate text-right text-neutral-500">{value}</span>
    </div>
  );
}

function TopBar({
  page,
  status,
  scheduler,
  activeSignal,
  lastRefresh,
  onRefresh,
}: {
  page: PageId;
  status: SystemStatus | null;
  scheduler: SchedulerStatus | null;
  activeSignal: Mt5Signal | null;
  lastRefresh: Date | null;
  onRefresh: () => void;
}) {
  const activePage = NAV_ITEMS.find((item) => item.id === page);
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-neutral-200 bg-white px-5">
      <div>
        <div className="text-base font-semibold text-neutral-950">{activePage?.label || "交易工作台"}</div>
        <div className="text-xs text-neutral-500">黄金、加密货币、MT5 信号与自动调度</div>
      </div>
      <div className="flex items-center gap-2">
        <Pill icon={Wifi} label={status?.healthy ? "后端在线" : "后端异常"} tone={status?.healthy ? "green" : "red"} />
        <Pill icon={Bot} label={status?.model || "模型未配置"} tone={status?.model ? "neutral" : "amber"} />
        <Pill icon={Activity} label={scheduler?.running ? "自动运行" : "手动模式"} tone={scheduler?.running ? "green" : "neutral"} />
        <Pill icon={Zap} label={activeSignal ? `${actionText(activeSignal.action)} ${activeSignal.symbol}` : "无活跃信号"} tone={activeSignal ? "amber" : "neutral"} />
        <button
          onClick={onRefresh}
          title="刷新"
          className="ml-1 flex h-9 w-9 items-center justify-center rounded-md border border-neutral-200 bg-white text-neutral-600 hover:bg-neutral-50"
        >
          <RefreshCw size={16} />
        </button>
        <div className="w-14 text-right text-[11px] text-neutral-400">{lastRefresh ? fmtShortTime(lastRefresh.toISOString()) : "--"}</div>
      </div>
    </header>
  );
}

function Pill({ icon: IconComponent, label, tone }: { icon: Icon; label: string; tone: "green" | "red" | "amber" | "neutral" }) {
  const toneClass = {
    green: "border-emerald-200 bg-emerald-50 text-emerald-700",
    red: "border-red-200 bg-red-50 text-red-700",
    amber: "border-amber-200 bg-amber-50 text-amber-700",
    neutral: "border-neutral-200 bg-neutral-50 text-neutral-600",
  }[tone];
  return (
    <div className={cx("flex h-8 items-center gap-1.5 rounded-md border px-2.5 text-xs", toneClass)}>
      <IconComponent size={14} />
      <span className="max-w-36 truncate">{label}</span>
    </div>
  );
}

function WorkspacePage({
  quotes,
  chartSymbol,
  activeSignal,
  status,
  reports,
  scheduler,
  avgChange,
  analysisResult,
  analyzing,
  analysisError,
  strategyPrompt,
  strategyDraft,
  strategyTemplates,
  compiledStrategy,
  robots,
  robotBusy,
  robotMessage,
  orderTicket,
  setStrategyPrompt,
  onChartSymbolChange,
  onAnalyzeSymbol,
  onQuickAnalyze,
  onStrategyPrompt,
  onTemplateCompile,
  onStartRobot,
  onRunRobotsOnce,
  onStopRobot,
  onRemoveRobot,
  onUseAnalysisSignal,
  onOpenAnalysis,
  onOpenSignals,
  onOpenAutomation,
  onOpenReport,
}: {
  quotes: Array<WatchItem & { price: MarketPrice | null }>;
  chartSymbol: string;
  activeSignal: Mt5Signal | null;
  status: SystemStatus | null;
  reports: ReportItem[];
  scheduler: SchedulerStatus | null;
  avgChange: number;
  analysisResult: AnalysisResult | null;
  analyzing: boolean;
  analysisError: string;
  strategyPrompt: string;
  strategyDraft: StrategyDraft | null;
  strategyTemplates: StrategyTemplate[];
  compiledStrategy: CompiledStrategy | null;
  robots: StrategyRobot[];
  robotBusy: boolean;
  robotMessage: string;
  orderTicket: ReactNode;
  setStrategyPrompt: (value: string) => void;
  onChartSymbolChange: (symbol: string) => void;
  onAnalyzeSymbol: (symbol: string) => void;
  onQuickAnalyze: (symbol: string) => void;
  onStrategyPrompt: () => void;
  onTemplateCompile: (templateId: string) => void;
  onStartRobot: () => void;
  onRunRobotsOnce: (robotId?: string) => void;
  onStopRobot: (robotId: string) => void;
  onRemoveRobot: (robotId: string) => void;
  onUseAnalysisSignal: () => void;
  onOpenAnalysis: () => void;
  onOpenSignals: () => void;
  onOpenAutomation: () => void;
  onOpenReport: (reportId: string) => void;
}) {
  return (
    <div className="space-y-4">
      <SmartPilot
        status={status}
        scheduler={scheduler}
        activeSignal={activeSignal}
        analysisResult={analysisResult}
        analyzing={analyzing}
        analysisError={analysisError}
        strategyPrompt={strategyPrompt}
        strategyDraft={strategyDraft}
        strategyTemplates={strategyTemplates}
        compiledStrategy={compiledStrategy}
        robotBusy={robotBusy}
        setStrategyPrompt={setStrategyPrompt}
        onQuickAnalyze={onQuickAnalyze}
        onStrategyPrompt={onStrategyPrompt}
        onTemplateCompile={onTemplateCompile}
        onStartRobot={onStartRobot}
        onUseAnalysisSignal={onUseAnalysisSignal}
        onOpenAnalysis={onOpenAnalysis}
        onOpenSignals={onOpenSignals}
        onOpenAutomation={onOpenAutomation}
      />

      <DemoRobotPanel
        robots={robots}
        busy={robotBusy}
        message={robotMessage}
        onRunOnce={onRunRobotsOnce}
        onStop={onStopRobot}
        onRemove={onRemoveRobot}
      />

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-4">
        <MetricCard label="市场均值" value={fmtPct(avgChange)} meta="关注列表涨跌" tone={avgChange >= 0 ? "green" : "red"} icon={avgChange >= 0 ? TrendingUp : TrendingDown} />
        <MetricCard label="当前信号" value={activeSignal ? actionText(activeSignal.action) : "等待"} meta={activeSignal ? `${activeSignal.symbol} · ${activeSignal.volume} 手` : "暂无执行信号"} tone={activeSignal ? "amber" : "neutral"} icon={Radio} />
        <MetricCard label="自动调度" value={scheduler?.running ? "运行中" : "已停止"} meta={scheduler?.running ? `${scheduler.interval_minutes} 分钟间隔` : "手动触发"} tone={scheduler?.running ? "green" : "neutral"} icon={Clock3} />
        <MetricCard label="历史报告" value={String(reports.length)} meta="最近分析记录" tone="neutral" icon={FileText} />
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-4">
        {quotes.map((item) => (
          <QuoteTile
            key={item.symbol}
            item={item}
            selected={item.symbol === chartSymbol}
            onSelect={() => onChartSymbolChange(item.symbol)}
            onAnalyze={() => onAnalyzeSymbol(item.symbol)}
          />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 2xl:grid-cols-[minmax(0,1fr)_390px]">
        <div className="min-w-0">
          <KlineChart symbol={chartSymbol} height={470} />
        </div>
        {orderTicket}
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_390px]">
        <RecentReports reports={reports} onOpenReport={onOpenReport} />
        <CurrentSignalPanel signal={activeSignal} />
      </div>
    </div>
  );
}

function SmartPilot({
  status,
  scheduler,
  activeSignal,
  analysisResult,
  analyzing,
  analysisError,
  strategyPrompt,
  strategyDraft,
  strategyTemplates,
  compiledStrategy,
  robotBusy,
  setStrategyPrompt,
  onQuickAnalyze,
  onStrategyPrompt,
  onTemplateCompile,
  onStartRobot,
  onUseAnalysisSignal,
  onOpenAnalysis,
  onOpenSignals,
  onOpenAutomation,
}: {
  status: SystemStatus | null;
  scheduler: SchedulerStatus | null;
  activeSignal: Mt5Signal | null;
  analysisResult: AnalysisResult | null;
  analyzing: boolean;
  analysisError: string;
  strategyPrompt: string;
  strategyDraft: StrategyDraft | null;
  strategyTemplates: StrategyTemplate[];
  compiledStrategy: CompiledStrategy | null;
  robotBusy: boolean;
  setStrategyPrompt: (value: string) => void;
  onQuickAnalyze: (symbol: string) => void;
  onStrategyPrompt: () => void;
  onTemplateCompile: (templateId: string) => void;
  onStartRobot: () => void;
  onUseAnalysisSignal: () => void;
  onOpenAnalysis: () => void;
  onOpenSignals: () => void;
  onOpenAutomation: () => void;
}) {
  const draft = analysisResult?.trading_signal;
  const backendReady = !!status?.healthy;
  const modelReady = !!status?.model && status.model !== "未配置";

  const title = !backendReady
    ? "后端未连接，先恢复本地服务"
    : compiledStrategy
      ? `已生成策略 JSON：${compiledStrategy.name}`
      : "从一句话生成可运行策略 JSON";
  const detail = compiledStrategy
    ? `${compiledStrategy.symbol.raw} · ${strategyTypeText(compiledStrategy.strategy_type)} · ${strategyStatusText(compiledStrategy.status)}。下一步可以调用 AI 分析，或直接启动模拟机器人观察触发条件。`
    : "直接像聊天一样描述策略，助手会先用人话回复，再把它整理成可复核、可运行的策略 JSON。";

  const strategyDisabled = !backendReady || !strategyPrompt.trim();
  const aiAnalyzeDisabled = analyzing || !backendReady || !modelReady || !compiledStrategy;
  const robotDisabled = robotBusy || !backendReady || !compiledStrategy;
  const visibleTemplates = strategyTemplates.slice(0, 8);

  return (
    <section className="rounded-md border border-neutral-200 bg-white p-4">
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_430px]">
        <div className="flex items-start gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-neutral-950 text-white">
            <Bot size={21} />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-base font-semibold text-neutral-950">AI 自动交易三步入口</h2>
              <span className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700">小白入口</span>
              <span className="rounded-md border border-neutral-200 bg-neutral-50 px-2 py-1 text-xs text-neutral-600">模板库</span>
              <span className="rounded-md border border-neutral-200 bg-neutral-50 px-2 py-1 text-xs text-neutral-600">策略 JSON</span>
              <span className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-700">机器人只跑 DEMO</span>
            </div>
            <div className="mt-3 text-xl font-semibold text-neutral-950">{title}</div>
            <div className="mt-1 max-w-3xl text-sm leading-6 text-neutral-600">{detail}</div>
            <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-3">
              <PilotCheckpoint icon={backendReady ? CheckCircle2 : AlertTriangle} label="后端" value={backendReady ? "正常" : "异常"} ok={backendReady} />
              <PilotCheckpoint icon={compiledStrategy ? CheckCircle2 : FileText} label="策略 JSON" value={compiledStrategy ? strategyStatusText(compiledStrategy.status) : "待生成"} ok={!!compiledStrategy} />
              <PilotCheckpoint icon={modelReady ? Brain : Settings} label="AI 分析" value={modelReady ? "可用" : "未配置"} ok={modelReady} />
            </div>
            <div className="mt-4 rounded-md border border-neutral-200 bg-[#f7f7f4] p-3">
              <div className="mb-2 flex items-center justify-between gap-2 text-xs text-neutral-500">
                <span>把你的想法发给策略助手</span>
                <span>当前：规则编译，不会自动实盘</span>
              </div>
              <textarea
                value={strategyPrompt}
                onChange={(event) => setStrategyPrompt(event.target.value)}
                onKeyDown={(event) => {
                  if ((event.ctrlKey || event.metaKey) && event.key === "Enter" && !strategyDisabled) onStrategyPrompt();
                }}
                rows={3}
                className="w-full resize-none bg-transparent text-sm leading-6 text-neutral-900 outline-none placeholder:text-neutral-400"
                placeholder="例如：黄金 H1 突破 4200 后模拟盘做多，止损 4170，止盈 4260，0.1 手。按 Ctrl+Enter 发送。"
              />
              {strategyDraft && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {strategyDraft.checklist.map((item) => (
                    <span key={item} className="rounded-md border border-neutral-200 bg-white px-2 py-1 text-xs text-neutral-600">{item}</span>
                  ))}
                </div>
              )}
            </div>
            <AssistantReplyCard strategy={compiledStrategy} modelReady={modelReady} backendReady={backendReady} />
            <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4">
              {visibleTemplates.length === 0 && (
                <div className="col-span-full rounded-md border border-dashed border-neutral-200 bg-neutral-50 p-3 text-sm text-neutral-500">
                  模板库等待后端返回。你仍可先用上面的自然语言编译。
                </div>
              )}
              {visibleTemplates.map((item) => (
                <button
                  key={item.id}
                  onClick={() => onTemplateCompile(item.id)}
                  disabled={!backendReady}
                  className="rounded-md border border-neutral-200 bg-white px-3 py-2 text-left hover:border-neutral-400 hover:bg-neutral-50"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="truncate text-xs font-semibold text-neutral-900">{item.name}</div>
                    <span className="shrink-0 rounded bg-neutral-100 px-1.5 py-0.5 text-[10px] text-neutral-500">{item.category}</span>
                  </div>
                  <div className="mt-1 line-clamp-2 text-[11px] leading-4 text-neutral-500">{item.description}</div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {[strategyTypeText(item.default_type), item.default_timeframe, ...item.tags.slice(0, 2)].map((tag, index) => (
                      <span key={`${item.id}-${tag}-${index}`} className="rounded bg-neutral-50 px-1.5 py-0.5 text-[10px] text-neutral-500">{tag}</span>
                    ))}
                  </div>
                </button>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                onClick={onStrategyPrompt}
                disabled={strategyDisabled}
                className="flex h-10 items-center gap-2 rounded-md bg-emerald-600 px-4 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Bot size={16} />
                发送给策略助手
              </button>
              <button
                onClick={() => compiledStrategy && onQuickAnalyze(compiledStrategy.symbol.raw)}
                disabled={aiAnalyzeDisabled}
                className="flex h-10 items-center gap-2 rounded-md border border-neutral-200 px-3 text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Brain size={16} className={analyzing ? "animate-spin" : ""} />
                {analyzing ? "AI 分析中" : modelReady ? "AI 分析行情" : "模型未配置"}
              </button>
              <button
                onClick={onStartRobot}
                disabled={robotDisabled}
                className="flex h-10 items-center gap-2 rounded-md bg-neutral-950 px-4 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Play size={15} />
                启动模拟机器人
              </button>
              {draft && !activeSignal && (
                <button onClick={onUseAnalysisSignal} className="flex h-10 items-center gap-2 rounded-md border border-neutral-200 px-3 text-sm font-medium text-neutral-700 hover:bg-neutral-50">
                  <Send size={15} />
                  套用 AI 信号
                </button>
              )}
              <button onClick={onOpenAnalysis} className="flex h-10 items-center gap-2 rounded-md border border-neutral-200 px-3 text-sm font-medium text-neutral-700 hover:bg-neutral-50">
                <BarChart3 size={15} />
                进入 AI 分析
              </button>
              <button onClick={onOpenAutomation} className="flex h-10 items-center gap-2 rounded-md border border-neutral-200 px-3 text-sm font-medium text-neutral-700 hover:bg-neutral-50">
                <Clock3 size={15} />
                自动巡检
              </button>
              {activeSignal && (
                <button onClick={onOpenSignals} className="flex h-10 items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 text-sm font-medium text-amber-700 hover:bg-amber-100">
                  <Radio size={15} />
                  查看当前信号
                </button>
              )}
            </div>
            {analysisError && <AlertBox message={analysisError} />}
          </div>
        </div>
        <StrategyJsonCard strategy={compiledStrategy} scheduler={scheduler} activeSignal={activeSignal} onStartRobot={onStartRobot} busy={robotBusy} />
      </div>
    </section>
  );
}

function StrategyJsonCard({
  strategy,
  scheduler,
  activeSignal,
  onStartRobot,
  busy,
}: {
  strategy: CompiledStrategy | null;
  scheduler: SchedulerStatus | null;
  activeSignal: Mt5Signal | null;
  onStartRobot: () => void;
  busy: boolean;
}) {
  if (!strategy) {
    return (
      <div className="rounded-md border border-neutral-200 bg-[#f7f7f4] p-4">
        <SectionTitle icon={FileText} title="策略 JSON 编译结果" />
        <EmptyState title="等待编译" detail="选择模板或输入一句话后，这里会显示机器可读的策略 JSON。" />
        <div className="mt-4 grid grid-cols-1 gap-2">
          <PilotCheckpoint icon={ShieldCheck} label="安全边界" value="默认模拟盘" ok />
          <PilotCheckpoint icon={Clock3} label="调度" value={scheduler?.running ? "自动巡检中" : "手动触发"} ok={!!scheduler?.running} />
          <PilotCheckpoint icon={Radio} label="当前信号" value={activeSignal ? `${actionText(activeSignal.action)} ${activeSignal.symbol}` : "暂无"} ok={!!activeSignal} />
        </div>
      </div>
    );
  }

  const warnings = [...strategy.missing_fields.map((item) => `缺少 ${item}`), ...strategy.warnings];
  return (
    <div className="rounded-md border border-neutral-200 bg-[#f7f7f4] p-4">
      <div className="flex items-start justify-between gap-3">
        <SectionTitle icon={FileText} title="策略 JSON 编译结果" />
        <span className={cx("rounded-md border px-2 py-1 text-xs font-medium", strategy.status === "ready" ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-amber-200 bg-amber-50 text-amber-700")}>
          {strategyStatusText(strategy.status)}
        </span>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <StrategyMeta label="标的" value={strategy.symbol.raw} />
        <StrategyMeta label="方向" value={actionText(strategy.action)} />
        <StrategyMeta label="类型" value={strategyTypeText(strategy.strategy_type)} />
        <StrategyMeta label="周期" value={strategy.timeframe} />
        <StrategyMeta label="手数" value={String(strategy.volume)} />
        <StrategyMeta label="风险" value={riskText(strategy.risk.level)} />
      </div>
      <div className="mt-3 rounded-md border border-neutral-200 bg-white p-3 text-xs leading-5 text-neutral-600">
        <div className="font-semibold text-neutral-900">入场规则</div>
        <div className="mt-1 font-mono">{JSON.stringify(strategy.entry)}</div>
        <div className="mt-3 font-semibold text-neutral-900">退出规则</div>
        <div className="mt-1">SL {String(strategy.exit.stop_loss || "--")} / TP {String(strategy.exit.take_profit || "--")}</div>
      </div>
      {warnings.length > 0 && (
        <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-800">
          {warnings.slice(0, 3).map((item) => <div key={item}>• {item}</div>)}
        </div>
      )}
      <pre className="mt-3 max-h-52 overflow-auto whitespace-pre-wrap rounded-md bg-neutral-950 p-3 text-[11px] leading-5 text-neutral-100">
        {JSON.stringify(strategy, null, 2)}
      </pre>
      <button
        onClick={onStartRobot}
        disabled={busy}
        className="mt-3 flex h-10 w-full items-center justify-center gap-2 rounded-md bg-neutral-950 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <Play size={15} />
        {busy ? "处理中" : "用此策略启动模拟机器人"}
      </button>
    </div>
  );
}

function StrategyMeta({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-md border border-neutral-200 bg-white p-2">
      <div className="text-[11px] text-neutral-500">{label}</div>
      <div className="mt-1 truncate text-xs font-semibold text-neutral-900">{value}</div>
    </div>
  );
}

function AssistantReplyCard({
  strategy,
  modelReady,
  backendReady,
}: {
  strategy: CompiledStrategy | null;
  modelReady: boolean;
  backendReady: boolean;
}) {
  if (!backendReady) {
    return (
      <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-800">
        <div className="font-semibold">助手回复</div>
        <div className="mt-1">我现在连不上本地后端，所以还不能读取你的策略。先启动后端服务，再回到这里发送一句话。</div>
      </div>
    );
  }

  if (!strategy) {
    return (
      <div className="mt-3 rounded-md border border-dashed border-neutral-300 bg-white p-3 text-sm leading-6 text-neutral-600">
        <div className="flex items-center gap-2 font-semibold text-neutral-900">
          <Bot size={15} />
          助手会这样回复你
        </div>
        <div className="mt-2">
          你发送后，我会先告诉你：“我理解你要交易什么、方向是什么、什么时候入场、止损止盈在哪里、下一步该点哪个按钮。”
        </div>
        <div className="mt-2 text-xs text-neutral-500">看不懂 JSON 没关系，小白只看这里和下方机器人面板就够了。</div>
      </div>
    );
  }

  const missing = strategy.missing_fields;
  const warnings = strategy.warnings;
  const ready = strategy.status === "ready";
  const entryPrice = typeof strategy.entry.price === "number" && strategy.entry.price > 0 ? fmtPrice(strategy.entry.price) : "";
  const strategyManagedExit = ["grid", "dca", "trend_following"].includes(strategy.strategy_type);
  const exitText = strategyManagedExit
    ? "按策略规则退出，当前版本不拆分真实订单"
    : `SL ${String(strategy.exit.stop_loss || "--")} / TP ${String(strategy.exit.take_profit || "--")}`;
  const entryText = entryPrice
    ? `价格到 ${entryPrice} 附近触发`
    : strategy.entry.type === "grid_range"
      ? `${fmtPrice(Number(strategy.entry.low))} - ${fmtPrice(Number(strategy.entry.high))} 区间网格观察`
      : strategy.entry.type === "indicator"
        ? `${String(strategy.entry.indicator || "指标")} 条件触发`
        : "入场条件还需要你补充确认";

  const steps = [
    ready ? "第一步：先检查我识别的标的、方向、入场、止损止盈是否符合你的意思。" : "第一步：先补齐黄色提示里的缺失参数，尤其是入场价和止损。",
    "第二步：确认无误后，点“启动模拟机器人”，它只会跑 DEMO，不会实盘。",
    "第三步：到“模拟盘机器人运行面板”点“执行一次”，看它是否生成 MT5 模拟信号。",
    modelReady ? "第四步：如果想让大模型再解释行情背景，再点“AI 分析行情”。" : "第四步：模型还没配置，所以现在先做规则编译和模拟观察；配置模型后才能做 AI 行情解释。",
  ];

  return (
    <div className="mt-3 overflow-hidden rounded-md border border-emerald-200 bg-emerald-50">
      <div className="border-b border-emerald-100 bg-white/70 px-3 py-2">
        <div className="flex items-center gap-2 text-sm font-semibold text-emerald-900">
          <Bot size={16} />
          助手回复：我已经读懂你的策略
        </div>
      </div>
      <div className="space-y-3 p-3 text-sm leading-6 text-neutral-700">
        <div>
          我理解你想用 <span className="font-semibold text-neutral-950">{strategy.symbol.raw}</span> 做
          <span className="font-semibold text-neutral-950"> {strategyTypeText(strategy.strategy_type)}</span>，
          方向是 <span className="font-semibold text-neutral-950">{actionText(strategy.action)}</span>，
          周期按 <span className="font-semibold text-neutral-950">{strategy.timeframe}</span> 处理，
          当前只建议走 <span className="font-semibold text-neutral-950">模拟盘</span>。
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          <StrategyMeta label="什么时候进" value={entryText} />
          <StrategyMeta label="怎么退出" value={exitText} />
          <StrategyMeta label="仓位" value={`${strategy.volume || 0.1} 手 · 风险 ${riskText(strategy.risk.level)}`} />
        </div>
        {(missing.length > 0 || warnings.length > 0) && (
          <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-800">
            {[...missing.map((item) => `还缺少：${item}`), ...warnings].slice(0, 4).map((item) => (
              <div key={item}>• {item}</div>
            ))}
          </div>
        )}
        <div className="rounded-md border border-emerald-100 bg-white p-3">
          <div className="text-xs font-semibold text-neutral-900">下一步照着做</div>
          <div className="mt-2 space-y-1 text-xs leading-5 text-neutral-600">
            {steps.map((step) => <div key={step}>• {step}</div>)}
          </div>
        </div>
      </div>
    </div>
  );
}

function PilotCheckpoint({ icon: IconComponent, label, value, ok }: { icon: Icon; label: string; value: string; ok: boolean }) {
  return (
    <div className="rounded-md border border-neutral-200 bg-[#f7f7f4] p-3">
      <div className="flex items-center gap-2 text-xs text-neutral-500">
        <IconComponent size={14} className={ok ? "text-emerald-600" : "text-amber-600"} />
        {label}
      </div>
      <div className="mt-1 truncate text-sm font-semibold text-neutral-900">{value}</div>
    </div>
  );
}

function DemoRobotPanel({
  robots,
  busy,
  message,
  onRunOnce,
  onStop,
  onRemove,
}: {
  robots: StrategyRobot[];
  busy: boolean;
  message: string;
  onRunOnce: (robotId?: string) => void;
  onStop: (robotId: string) => void;
  onRemove: (robotId: string) => void;
}) {
  const runningCount = robots.filter((robot) => robot.status === "running").length;
  const signalCount = robots.reduce((sum, robot) => sum + robot.signal_count, 0);

  return (
    <section className="rounded-md border border-neutral-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <SectionTitle icon={Bot} title="模拟盘机器人运行面板" />
          <div className="mt-2 text-sm leading-6 text-neutral-600">
            机器人只做 DEMO 观察：读取行情、判断触发条件、写入模拟盘 MT5 信号，不会自动实盘下单。
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700">运行 {runningCount}</span>
          <span className="rounded-md border border-neutral-200 bg-neutral-50 px-2 py-1 text-xs text-neutral-600">信号 {signalCount}</span>
          <button
            onClick={() => onRunOnce()}
            disabled={busy || runningCount === 0}
            className="flex h-8 items-center gap-1.5 rounded-md bg-neutral-950 px-3 text-xs font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Zap size={14} />
            全部执行一次
          </button>
        </div>
      </div>

      {message && <div className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{message}</div>}
      {robots.length === 0 && <EmptyState title="暂无模拟机器人" detail="先从上方模板或自然语言生成策略 JSON，然后点击“启动模拟机器人”。" />}

      {robots.length > 0 && (
        <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
          {robots.map((robot) => {
            const strategy = robot.strategy;
            const latestEvent = robot.events?.[robot.events.length - 1];
            const symbol = strategy.symbol?.raw || strategy.symbol?.canonical || "--";
            return (
              <div key={robot.id} className="rounded-md border border-neutral-200 bg-[#f7f7f4] p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="truncate text-sm font-semibold text-neutral-950">{robot.name}</div>
                      <span className={cx("rounded-md border px-2 py-0.5 text-[11px] font-medium", robotStatusClass(robot.status))}>{robotStatusText(robot.status)}</span>
                      <span className="rounded-md border border-neutral-200 bg-white px-2 py-0.5 text-[11px] text-neutral-500">{robot.mode}</span>
                    </div>
                    <div className="mt-1 text-xs text-neutral-500">
                      {symbol} · {strategyTypeText(strategy.strategy_type)} · {strategy.timeframe} · {actionText(strategy.action)}
                    </div>
                  </div>
                  <div className="text-right text-xs text-neutral-500">
                    <div>运行 {robot.run_count}</div>
                    <div>信号 {robot.signal_count}</div>
                  </div>
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2">
                  <StatusBox label="最新价" value={robot.last_price ? fmtPrice(robot.last_price) : "--"} ok={robot.last_price > 0} />
                  <StatusBox label="动作" value={actionText(robot.last_action)} ok={robot.last_action !== "WAIT"} />
                  <StatusBox label="更新" value={fmtShortTime(robot.updated_at)} ok />
                </div>
                {latestEvent && (
                  <div className="mt-3 rounded-md border border-neutral-200 bg-white p-3 text-xs leading-5 text-neutral-600">
                    <div className="font-semibold text-neutral-900">{fmtShortTime(latestEvent.time)} · {latestEvent.type}</div>
                    <div className="mt-1">{latestEvent.message}</div>
                  </div>
                )}
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    onClick={() => onRunOnce(robot.id)}
                    disabled={busy || robot.status !== "running"}
                    className="flex h-8 items-center gap-1.5 rounded-md border border-neutral-200 bg-white px-3 text-xs font-medium text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Zap size={14} />
                    执行一次
                  </button>
                  <button
                    onClick={() => onStop(robot.id)}
                    disabled={busy || robot.status !== "running"}
                    className="flex h-8 items-center gap-1.5 rounded-md border border-neutral-200 bg-white px-3 text-xs font-medium text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Pause size={14} />
                    停止
                  </button>
                  <button
                    onClick={() => onRemove(robot.id)}
                    disabled={busy}
                    className="flex h-8 items-center gap-1.5 rounded-md border border-red-200 bg-white px-3 text-xs font-medium text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Trash2 size={14} />
                    删除
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

function MetricCard({
  label,
  value,
  meta,
  tone,
  icon: IconComponent,
}: {
  label: string;
  value: string;
  meta: string;
  tone: "green" | "red" | "amber" | "neutral";
  icon: Icon;
}) {
  const toneClass = {
    green: "text-emerald-700 bg-emerald-50 border-emerald-100",
    red: "text-red-700 bg-red-50 border-red-100",
    amber: "text-amber-700 bg-amber-50 border-amber-100",
    neutral: "text-neutral-700 bg-white border-neutral-200",
  }[tone];
  return (
    <section className="rounded-md border border-neutral-200 bg-white p-4">
      <div className="flex items-center justify-between">
        <div className="text-xs font-medium text-neutral-500">{label}</div>
        <div className={cx("flex h-8 w-8 items-center justify-center rounded-md border", toneClass)}>
          <IconComponent size={16} />
        </div>
      </div>
      <div className="mt-2 text-2xl font-semibold tracking-normal text-neutral-950">{value}</div>
      <div className="mt-1 text-xs text-neutral-500">{meta}</div>
    </section>
  );
}

function QuoteTile({
  item,
  selected,
  onSelect,
  onAnalyze,
}: {
  item: WatchItem & { price: MarketPrice | null };
  selected: boolean;
  onSelect: () => void;
  onAnalyze: () => void;
}) {
  const change = item.price?.change_pct ?? 0;
  return (
    <section className={cx("rounded-md border bg-white p-3", selected ? "border-neutral-950" : "border-neutral-200")}>
      <button onClick={onSelect} className="block w-full text-left">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-sm font-semibold text-neutral-950">{item.label}</div>
            <div className="mt-0.5 text-xs text-neutral-500">{item.name} · {item.venue}</div>
          </div>
          <div className={cx("flex h-7 w-7 items-center justify-center rounded-md", change >= 0 ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700")}>
            {change >= 0 ? <TrendingUp size={15} /> : <TrendingDown size={15} />}
          </div>
        </div>
        <div className="mt-4 flex items-end justify-between">
          <div className="text-xl font-semibold text-neutral-950">{fmtPrice(item.price?.price)}</div>
          <div className={cx("text-sm font-medium", change >= 0 ? "text-emerald-700" : "text-red-700")}>{fmtPct(item.price?.change_pct)}</div>
        </div>
      </button>
      <button onClick={onAnalyze} className="mt-3 flex h-8 w-full items-center justify-center gap-2 rounded-md border border-neutral-200 text-xs font-medium text-neutral-700 hover:bg-neutral-50">
        <Brain size={14} />
        分析
      </button>
    </section>
  );
}

function RecentReports({ reports, onOpenReport }: { reports: ReportItem[]; onOpenReport: (reportId: string) => void }) {
  return (
    <section className="rounded-md border border-neutral-200 bg-white p-4">
      <SectionTitle icon={FileText} title="最近报告" />
      <div className="mt-3 divide-y divide-neutral-100">
        {reports.length === 0 && <EmptyState title="暂无报告" detail="完成一次 AI 分析后会生成记录" />}
        {reports.slice(0, 6).map((report) => (
          <button key={report.id} onClick={() => onOpenReport(report.id)} className="flex w-full items-center justify-between gap-4 py-3 text-left hover:bg-neutral-50">
            <div className="min-w-0">
              <div className="truncate text-sm font-medium text-neutral-900">{report.title}</div>
              <div className="mt-1 text-xs text-neutral-500">{report.analysis_date}</div>
            </div>
            <span className="shrink-0 rounded-md bg-neutral-100 px-2 py-1 text-xs text-neutral-600">{report.status || "完成"}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

function CurrentSignalPanel({ signal }: { signal: Mt5Signal | null }) {
  return (
    <section className="rounded-md border border-neutral-200 bg-white p-4">
      <SectionTitle icon={Radio} title="当前信号" />
      {!signal && <EmptyState title="暂无活跃信号" detail="AI 或手动信号会显示在这里" />}
      {signal && (
        <div className="mt-4 space-y-3">
          <div className={cx("rounded-md border p-3", actionClass(signal.action))}>
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold">{actionText(signal.action)} {signal.symbol}</div>
              <div className="text-xs">{signal.volume} 手</div>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
              <span>止损 {signal.sl || "--"}</span>
              <span>止盈 {signal.tp || "--"}</span>
              <span>模式 {signal.trade_mode}</span>
              <span>过期 {fmtShortTime(signal.expires_at)}</span>
            </div>
          </div>
          <div className="break-all rounded-md bg-neutral-50 p-3 font-mono text-xs text-neutral-500">{signal.signal_id}</div>
        </div>
      )}
    </section>
  );
}

function AnalysisPage({
  symbol,
  setSymbol,
  template,
  setTemplate,
  autoSignal,
  setAutoSignal,
  analyzing,
  result,
  reportText,
  error,
  onAnalyze,
  onUseSignal,
}: {
  symbol: string;
  setSymbol: (value: string) => void;
  template: string;
  setTemplate: (value: string) => void;
  autoSignal: boolean;
  setAutoSignal: (value: boolean) => void;
  analyzing: boolean;
  result: AnalysisResult | null;
  reportText: string;
  error: string;
  onAnalyze: () => void;
  onUseSignal: () => void;
}) {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[390px_minmax(0,1fr)]">
      <section className="rounded-md border border-neutral-200 bg-white p-4">
        <SectionTitle icon={Brain} title="AI 分析任务" />
        <div className="mt-4 space-y-4">
          <Field label="标的">
            <input
              value={symbol}
              onChange={(event) => setSymbol(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && onAnalyze()}
              className="h-10 w-full rounded-md border border-neutral-300 px-3 text-sm outline-none focus:border-neutral-950"
              placeholder="GOLD / BTC-USD"
            />
          </Field>
          <Field label="策略模板">
            <select
              value={template}
              onChange={(event) => setTemplate(event.target.value)}
              className="h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm outline-none focus:border-neutral-950"
            >
              {TEMPLATES.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </Field>
          <label className="flex items-center justify-between rounded-md border border-neutral-200 bg-neutral-50 px-3 py-3 text-sm text-neutral-700">
            <span>分析完成后生成 MT5 信号</span>
            <input type="checkbox" checked={autoSignal} onChange={(event) => setAutoSignal(event.target.checked)} className="h-4 w-4 accent-neutral-950" />
          </label>
          <button
            onClick={onAnalyze}
            disabled={analyzing || !symbol.trim()}
            className="flex h-10 w-full items-center justify-center gap-2 rounded-md bg-neutral-950 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {analyzing ? <RefreshCw size={16} className="animate-spin" /> : <Bot size={16} />}
            {analyzing ? "分析中" : "开始分析"}
          </button>
          {error && <AlertBox message={error} />}
        </div>
      </section>

      <section className="min-w-0 rounded-md border border-neutral-200 bg-white p-4">
        <div className="flex items-center justify-between gap-3">
          <SectionTitle icon={BarChart3} title="分析结果" />
          {result?.trading_signal && (
            <button onClick={onUseSignal} className="flex h-9 items-center gap-2 rounded-md bg-emerald-600 px-3 text-sm font-semibold text-white hover:bg-emerald-700">
              <Send size={15} />
              使用信号
            </button>
          )}
        </div>
        {analyzing && <LoadingPanel />}
        {!analyzing && !result && !error && <EmptyState title="等待分析" detail="选择标的后启动 AI 多智能体分析" />}
        {result?.trading_signal && (
          <div className={cx("mt-4 rounded-md border p-3", actionClass(result.trading_signal.action))}>
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <span className="font-semibold">AI 决策：{actionText(result.trading_signal.action)}</span>
              <span>信心 {result.trading_signal.confidence ?? "--"}%</span>
              <span>手数 {result.trading_signal.volume ?? "--"}</span>
              <span>SL {result.trading_signal.sl ?? "--"}</span>
              <span>TP {result.trading_signal.tp ?? "--"}</span>
              <span>{result.signal_sent ? "已写入信号" : "未写入信号"}</span>
            </div>
          </div>
        )}
        {reportText && (
          <pre className="mt-4 max-h-[640px] overflow-auto whitespace-pre-wrap rounded-md bg-[#f7f7f4] p-4 text-xs leading-6 text-neutral-800">
            {clampReport(reportText)}
          </pre>
        )}
      </section>
    </div>
  );
}

function SignalsPage({ activeSignal, orderTicket }: { activeSignal: Mt5Signal | null; orderTicket: ReactNode }) {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[390px_minmax(0,1fr)]">
      {orderTicket}
      <CurrentSignalPanel signal={activeSignal} />
    </div>
  );
}

function OrderTicket({
  sigSymbol,
  setSigSymbol,
  sigAction,
  setSigAction,
  sigVolume,
  setSigVolume,
  sigSl,
  setSigSl,
  sigTp,
  setSigTp,
  sigMode,
  setSigMode,
  sigAuto,
  setSigAuto,
  sigBusy,
  sigMessage,
  sigError,
  onSend,
  onClear,
}: {
  sigSymbol: string;
  setSigSymbol: (value: string) => void;
  sigAction: string;
  setSigAction: (value: string) => void;
  sigVolume: string;
  setSigVolume: (value: string) => void;
  sigSl: string;
  setSigSl: (value: string) => void;
  sigTp: string;
  setSigTp: (value: string) => void;
  sigMode: string;
  setSigMode: (value: string) => void;
  sigAuto: boolean;
  setSigAuto: (value: boolean) => void;
  sigBusy: boolean;
  sigMessage: string;
  sigError: string;
  onSend: () => void;
  onClear: () => void;
}) {
  return (
    <section className="rounded-md border border-neutral-200 bg-white p-4">
      <SectionTitle icon={ShieldCheck} title="执行面板" />
      <div className="mt-4 grid grid-cols-3 gap-2">
        <ExecutionGuard label="账户" value={sigMode === "LIVE" ? "实盘" : "模拟盘"} ok={sigMode !== "LIVE"} />
        <ExecutionGuard label="自动交易" value={sigAuto ? "已开启" : "已关闭"} ok={!sigAuto} />
        <ExecutionGuard label="风控" value={sigSl || sigTp ? "已填写" : "待确认"} ok={!!sigSl || !!sigTp} />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3">
        <Field label="标的">
          <input value={sigSymbol} onChange={(event) => setSigSymbol(event.target.value)} className="h-10 w-full rounded-md border border-neutral-300 px-3 font-mono text-sm outline-none focus:border-neutral-950" />
        </Field>
        <Field label="账户">
          <select value={sigMode} onChange={(event) => setSigMode(event.target.value)} className="h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm outline-none focus:border-neutral-950">
            <option value="DEMO">模拟盘</option>
            <option value="LIVE">实盘</option>
          </select>
        </Field>
        <div className="col-span-2">
          <div className="mb-2 text-xs font-medium text-neutral-500">方向</div>
          <div className="grid grid-cols-3 gap-2">
            {["BUY", "SELL", "WAIT"].map((action) => (
              <button
                key={action}
                onClick={() => setSigAction(action)}
                className={cx(
                  "h-10 rounded-md border text-sm font-semibold",
                  sigAction === action ? actionClass(action) : "border-neutral-200 bg-white text-neutral-600 hover:bg-neutral-50",
                )}
              >
                {actionText(action)}
              </button>
            ))}
          </div>
        </div>
        <Field label="手数">
          <input type="number" step="0.01" value={sigVolume} onChange={(event) => setSigVolume(event.target.value)} className="h-10 w-full rounded-md border border-neutral-300 px-3 text-sm outline-none focus:border-neutral-950" />
        </Field>
        <Field label="允许自动交易">
          <button
            onClick={() => setSigAuto(!sigAuto)}
            className={cx("flex h-10 w-full items-center justify-center gap-2 rounded-md border text-sm font-semibold", sigAuto ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-neutral-200 bg-neutral-50 text-neutral-600")}
          >
            <Power size={15} />
            {sigAuto ? "已开启" : "已关闭"}
          </button>
        </Field>
        <Field label="止损">
          <input type="number" step="0.01" value={sigSl} onChange={(event) => setSigSl(event.target.value)} placeholder="0=不设" className="h-10 w-full rounded-md border border-neutral-300 px-3 text-sm outline-none focus:border-neutral-950" />
        </Field>
        <Field label="止盈">
          <input type="number" step="0.01" value={sigTp} onChange={(event) => setSigTp(event.target.value)} placeholder="0=不设" className="h-10 w-full rounded-md border border-neutral-300 px-3 text-sm outline-none focus:border-neutral-950" />
        </Field>
      </div>
      <div className="mt-4 grid grid-cols-[1fr_auto] gap-2">
        <button onClick={onSend} disabled={sigBusy} className="flex h-10 items-center justify-center gap-2 rounded-md bg-neutral-950 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50">
          <Send size={16} />
          {sigBusy ? "处理中" : "发送信号"}
        </button>
        <button onClick={onClear} disabled={sigBusy} className="h-10 rounded-md border border-neutral-200 px-3 text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-50">
          清除
        </button>
      </div>
      {sigMessage && <div className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{sigMessage}</div>}
      {sigError && <AlertBox message={sigError} />}
    </section>
  );
}

function ReportsPage({
  reports,
  viewingReportId,
  viewingReport,
  onOpenReport,
  onCloseReport,
}: {
  reports: ReportItem[];
  viewingReportId: string;
  viewingReport: string;
  onOpenReport: (reportId: string) => void;
  onCloseReport: () => void;
}) {
  if (viewingReportId) {
    return (
      <section className="rounded-md border border-neutral-200 bg-white p-4">
        <button onClick={onCloseReport} className="mb-4 flex h-9 items-center gap-2 rounded-md border border-neutral-200 px-3 text-sm font-medium text-neutral-700 hover:bg-neutral-50">
          返回列表
        </button>
        <pre className="max-h-[720px] overflow-auto whitespace-pre-wrap rounded-md bg-[#f7f7f4] p-4 text-xs leading-6 text-neutral-800">{viewingReport || "加载中..."}</pre>
      </section>
    );
  }

  return <RecentReports reports={reports} onOpenReport={onOpenReport} />;
}

function ExecutionGuard({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div className={cx("rounded-md border p-2", ok ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50")}>
      <div className={cx("text-[11px]", ok ? "text-emerald-700" : "text-amber-700")}>{label}</div>
      <div className="mt-0.5 truncate text-xs font-semibold text-neutral-900">{value}</div>
    </div>
  );
}

function AutomationPage({ scheduler, status, onRefresh }: { scheduler: SchedulerStatus | null; status: SystemStatus | null; onRefresh: () => void }) {
  const [symbols, setSymbols] = useState("GOLD,BTC-USD");
  const [intervalMinutes, setIntervalMinutes] = useState("30");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const runAction = async (action: () => Promise<unknown>, done: string) => {
    setBusy(true);
    setMessage("");
    try {
      await action();
      setMessage(done);
      onRefresh();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[390px_minmax(0,1fr)]">
      <section className="rounded-md border border-neutral-200 bg-white p-4">
        <SectionTitle icon={Settings} title="调度配置" />
        <div className="mt-4 space-y-4">
          <Field label="监控品种">
            <input value={symbols} onChange={(event) => setSymbols(event.target.value)} className="h-10 w-full rounded-md border border-neutral-300 px-3 font-mono text-sm outline-none focus:border-neutral-950" />
          </Field>
          <Field label="执行间隔">
            <select value={intervalMinutes} onChange={(event) => setIntervalMinutes(event.target.value)} className="h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm outline-none focus:border-neutral-950">
              <option value="5">5 分钟</option>
              <option value="15">15 分钟</option>
              <option value="30">30 分钟</option>
              <option value="60">1 小时</option>
              <option value="120">2 小时</option>
              <option value="240">4 小时</option>
            </select>
          </Field>
          <button
            disabled={busy}
            onClick={() => runAction(() => configureScheduler({ symbols: symbols.split(",").map((item) => item.trim()).filter(Boolean), interval_minutes: Number.parseInt(intervalMinutes, 10) || 30 }), "配置已保存")}
            className="flex h-10 w-full items-center justify-center gap-2 rounded-md border border-neutral-200 text-sm font-semibold text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
          >
            <SlidersHorizontal size={16} />
            保存配置
          </button>
          <div className="grid grid-cols-2 gap-2">
            {scheduler?.running ? (
              <button disabled={busy} onClick={() => runAction(stopScheduler, "调度已停止")} className="flex h-10 items-center justify-center gap-2 rounded-md bg-red-600 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50">
                <Pause size={16} />
                停止
              </button>
            ) : (
              <button disabled={busy} onClick={() => runAction(startScheduler, "调度已启动")} className="flex h-10 items-center justify-center gap-2 rounded-md bg-emerald-600 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50">
                <Play size={16} />
                启动
              </button>
            )}
            <button disabled={busy} onClick={() => runAction(runSchedulerOnce, "已执行一次")} className="flex h-10 items-center justify-center gap-2 rounded-md bg-neutral-950 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">
              <Zap size={16} />
              执行一次
            </button>
          </div>
          {message && <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{message}</div>}
        </div>
      </section>

      <section className="rounded-md border border-neutral-200 bg-white p-4">
        <SectionTitle icon={Activity} title="运行状态" />
        <div className="mt-4 grid grid-cols-2 gap-3">
          <StatusBox label="后端" value={status?.healthy ? "正常" : "异常"} ok={!!status?.healthy} />
          <StatusBox label="模型" value={status?.model || "未配置"} ok={!!status?.model} />
          <StatusBox label="提供商" value={status?.provider || "未配置"} ok={!!status?.provider} />
          <StatusBox label="MT5" value={status?.mt5_connected ? "可用" : "未连接"} ok={!!status?.mt5_connected} />
        </div>
        <div className="mt-5">
          <div className="text-xs font-medium text-neutral-500">最近执行</div>
          <div className="mt-2 divide-y divide-neutral-100">
            {!scheduler?.last_runs?.length && <EmptyState title="暂无执行记录" detail="启动调度或执行一次后会出现记录" />}
            {scheduler?.last_runs?.slice(0, 10).map((run, index) => (
              <div key={`${run.symbol}-${run.time}-${index}`} className="grid grid-cols-[80px_80px_80px_1fr] items-center gap-3 py-3 text-sm">
                <span className="text-xs text-neutral-500">{fmtShortTime(run.time)}</span>
                <span className="font-mono font-semibold">{run.symbol}</span>
                <span className={cx("rounded-md border px-2 py-1 text-center text-xs", actionClass(run.action))}>{actionText(run.action)}</span>
                <span className="truncate text-xs text-neutral-500">{run.error || (run.signal_sent ? "信号已发送" : `${run.confidence}%`)}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function SectionTitle({ icon: IconComponent, title }: { icon: Icon; title: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex h-8 w-8 items-center justify-center rounded-md bg-neutral-100 text-neutral-700">
        <IconComponent size={16} />
      </div>
      <h2 className="text-sm font-semibold text-neutral-950">{title}</h2>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-medium text-neutral-500">{label}</span>
      {children}
    </label>
  );
}

function StatusBox({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div className="rounded-md border border-neutral-200 bg-neutral-50 p-3">
      <div className="flex items-center gap-2 text-xs text-neutral-500">
        {ok ? <CheckCircle2 size={14} className="text-emerald-600" /> : <AlertTriangle size={14} className="text-amber-600" />}
        {label}
      </div>
      <div className="mt-2 truncate text-sm font-semibold text-neutral-900">{value}</div>
    </div>
  );
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="mt-4 rounded-md border border-dashed border-neutral-200 bg-neutral-50 p-6 text-center">
      <div className="text-sm font-medium text-neutral-700">{title}</div>
      <div className="mt-1 text-xs text-neutral-500">{detail}</div>
    </div>
  );
}

function AlertBox({ message }: { message: string }) {
  return (
    <div className="mt-3 flex gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
      <AlertTriangle size={16} className="mt-0.5 shrink-0" />
      <span className="break-words">{message}</span>
    </div>
  );
}

function LoadingPanel() {
  return (
    <div className="mt-4 rounded-md border border-neutral-200 bg-neutral-50 p-8 text-center">
      <RefreshCw size={22} className="mx-auto animate-spin text-neutral-500" />
      <div className="mt-3 text-sm font-medium text-neutral-700">AI 正在分析</div>
      <div className="mt-1 text-xs text-neutral-500">行情、技术、风险与交易信号正在汇总</div>
    </div>
  );
}
