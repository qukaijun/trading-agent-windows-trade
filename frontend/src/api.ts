async function request<T = unknown>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(detail || `HTTP ${res.status}`);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text() as T;
}

export interface SystemStatus {
  healthy: boolean;
  provider: string;
  model: string;
  mt5_connected: boolean;
  trade_mode: string;
}

export interface MarketPrice {
  symbol: string;
  name: string;
  price: number;
  change_pct: number;
}

export interface Mt5Signal {
  signal_id: string;
  symbol: string;
  action: string;
  volume: number;
  sl: number;
  tp: number;
  comment: string;
  source: string;
  created_at: string;
  expires_at: string;
  trade_mode: string;
  auto_trade_allowed: boolean;
}

// --- System ---
export async function fetchStatus(): Promise<SystemStatus> {
  const [health, cap, mt5cfg] = await Promise.all([
    request<{ status: string }>(`/health`),
    request<{ runtime: { provider: string; model: string; trade_mode: string } }>(`/api/capabilities`),
    request<{ live_enabled: boolean }>(`/api/mt5/config`).catch(() => ({ live_enabled: false })),
  ]);
  return {
    healthy: health.status === "healthy",
    provider: cap.runtime?.provider || "",
    model: cap.runtime?.model || "",
    mt5_connected: mt5cfg.live_enabled !== undefined,
    trade_mode: cap.runtime?.trade_mode || "模拟盘",
  };
}

// --- Market ---
export async function fetchPrice(symbol: string): Promise<MarketPrice | null> {
  try {
    const data = await request<{
      status: string;
      market_snapshot?: { current_price?: number; change_pct?: number; symbol_name?: string };
      latest_close?: number | null;
      day_change_pct?: number | null;
      symbol?: { display?: string };
    }>(`/api/market-snapshot?symbol=${encodeURIComponent(symbol)}&data_source=yfinance`);
    if (data.status !== "ok") return null;
    const price = data.market_snapshot?.current_price ?? data.latest_close;
    if (typeof price !== "number") return null;
    return {
      symbol,
      name: data.market_snapshot?.symbol_name || data.symbol?.display || symbol,
      price,
      change_pct: data.market_snapshot?.change_pct ?? data.day_change_pct ?? 0,
    };
  } catch {
    return null;
  }
}

// --- Analysis ---
export async function normalizeSymbol(symbol: string) {
  return request<{ canonical: string; market: string; name: string }>(
    `/api/normalize-symbol?symbol=${encodeURIComponent(symbol)}`
  );
}

export async function runAnalysis(symbol: string, template: string, dataSource: string = "yfinance", autoSignal: boolean = false) {
  const query = new URLSearchParams();
  query.set("symbol", symbol);
  query.set("report_template", template);
  query.set("data_source", dataSource);
  if (autoSignal) query.set("auto_signal", "true");
  const res = await fetch(`/api/analyze?${query.toString()}`, {
    method: "POST",
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// --- Reports ---
export async function fetchReports(limit = 10) {
  return request<{ reports: Array<{ id: string; title: string; symbol: unknown; analysis_date: string; status: string }> }>(
    `/api/reports?limit=${limit}`
  );
}

export async function fetchReportMarkdown(reportId: string) {
  return request<string>(`/api/reports/${encodeURIComponent(reportId)}.md`);
}

// --- MT5 Signal ---
export async function fetchCurrentSignal(): Promise<Mt5Signal> {
  return request<Mt5Signal>(`/api/mt5/signal`);
}

export async function sendSignal(params: {
  symbol: string;
  action: string;
  volume: number;
  sl: number;
  tp: number;
  comment?: string;
  trade_mode?: string;
  auto_trade_allowed?: boolean;
}) {
  const form = new URLSearchParams();
  form.set("symbol", params.symbol);
  form.set("action", params.action);
  form.set("volume", String(params.volume));
  form.set("sl", String(params.sl));
  form.set("tp", String(params.tp));
  form.set("comment", params.comment || "");
  form.set("trade_mode", params.trade_mode || "DEMO");
  form.set("auto_trade_allowed", params.auto_trade_allowed ? "true" : "false");
  form.set("ttl_minutes", "15");
  const res = await fetch(`/api/mt5/signal`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<Mt5Signal>;
}

export async function clearSignal() {
  return request<Mt5Signal>(`/api/mt5/clear-signal`, { method: "POST" });
}

// --- Strategy Compiler ---
export interface StrategyTemplate {
  id: string;
  name: string;
  category: string;
  description: string;
  default_symbol: string;
  default_type: string;
  default_timeframe: string;
  beginner_level: string;
  prompt: string;
  required_fields: string[];
  tags: string[];
}

export interface CompiledStrategy {
  id: string;
  name: string;
  source: string;
  prompt: string;
  template_id: string;
  status: string;
  symbol: { raw: string; market: string; canonical: string; yfinance: string; display: string; confidence: string; notes?: string };
  strategy_type: string;
  timeframe: string;
  mode: string;
  action: string;
  volume: number;
  entry: Record<string, unknown>;
  exit: Record<string, unknown>;
  risk: Record<string, unknown>;
  schedule: Record<string, unknown>;
  assumptions: string[];
  missing_fields: string[];
  warnings: string[];
  explain: string[];
  compiled_at: string;
}

export async function fetchStrategyTemplates() {
  return request<{ templates: StrategyTemplate[] }>(`/api/strategy/templates`);
}

export async function compileStrategy(payload: { prompt?: string; template_id?: string; symbol?: string }) {
  return request<{ status: string; strategy: CompiledStrategy }>(`/api/strategy/compile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// --- Demo Robots ---
export interface RobotEvent {
  time: string;
  type: string;
  message: string;
  price: number;
  action: string;
}

export interface StrategyRobot {
  id: string;
  name: string;
  status: string;
  mode: string;
  strategy: CompiledStrategy;
  created_at: string;
  updated_at: string;
  last_price: number;
  last_action: string;
  run_count: number;
  signal_count: number;
  events: RobotEvent[];
}

export async function fetchRobotsStatus() {
  return request<{ robots: StrategyRobot[]; running_count: number; updated_at: string }>(`/api/robots/status`);
}

export async function startRobot(strategy: CompiledStrategy) {
  return request<StrategyRobot>(`/api/robots/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ strategy }),
  });
}

export async function stopRobot(robotId: string) {
  return request<StrategyRobot>(`/api/robots/${encodeURIComponent(robotId)}/stop`, { method: "POST" });
}

export async function removeRobot(robotId: string) {
  return request<StrategyRobot>(`/api/robots/${encodeURIComponent(robotId)}/remove`, { method: "POST" });
}

export async function runRobotsOnce(robotId?: string) {
  return request<{ runs: RobotEvent[]; robots: StrategyRobot[] }>(`/api/robots/run-once`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(robotId ? { robot_id: robotId } : {}),
  });
}

// --- Scheduler ---
export interface SchedulerStatus {
  running: boolean;
  symbols: string[];
  interval_minutes: number;
  auto_signal: boolean;
  next_run_at: string | null;
  last_runs: Array<{ symbol: string; time: string; action: string; confidence: number; signal_sent: boolean; error?: string }>;
}

export async function fetchSchedulerStatus(): Promise<SchedulerStatus> {
  return request<SchedulerStatus>(`/api/scheduler/status`);
}

export async function startScheduler(): Promise<SchedulerStatus> {
  return request<SchedulerStatus>(`/api/scheduler/start`, { method: "POST" });
}

export async function stopScheduler(): Promise<SchedulerStatus> {
  return request<SchedulerStatus>(`/api/scheduler/stop`, { method: "POST" });
}

export async function runSchedulerOnce(): Promise<{ runs: unknown[] }> {
  return request(`/api/scheduler/run-once`, { method: "POST" });
}

export async function configureScheduler(config: Record<string, unknown>): Promise<SchedulerStatus> {
  return request<SchedulerStatus>(`/api/scheduler/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
}
