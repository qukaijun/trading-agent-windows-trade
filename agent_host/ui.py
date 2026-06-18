from __future__ import annotations

from html import escape
from typing import Mapping


def render_home(runtime: Mapping[str, str]) -> str:
    html = HOME_TEMPLATE
    replacements = {
        "__PROVIDER__": escape(runtime.get("display_provider", "未配置")),
        "__MODEL__": escape(runtime.get("model", "未配置")),
        "__MODE__": escape(runtime.get("trade_mode", "投研分析 / 非实盘")),
    }
    for key, value in replacements.items():
        html = html.replace(key, value)
    return html


HOME_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TradingAgents 中文服务工作台</title>
  <style>
    :root {
      --page: #f6f7f9;
      --surface: #ffffff;
      --soft: #f8fafc;
      --text: #1f2937;
      --muted: #64748b;
      --line: #d7dde6;
      --blue: #2563eb;
      --green: #047857;
      --amber: #a16207;
      --red: #b42318;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--page);
      color: var(--text);
      font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
      line-height: 1.55;
    }
    button, input, select { font: inherit; }
    button {
      min-height: 38px;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      background: #fff;
      color: var(--text);
      cursor: pointer;
      padding: 0 12px;
    }
    button.primary { background: var(--blue); border-color: var(--blue); color: #fff; font-weight: 700; }
    button.secondary { color: var(--muted); background: var(--soft); }
    button:disabled { opacity: .55; cursor: not-allowed; }
    input, select {
      width: 100%;
      height: 38px;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      padding: 0 10px;
      background: #fff;
      color: var(--text);
    }
    header {
      border-bottom: 1px solid var(--line);
      background: #fff;
    }
    .topbar {
      max-width: 1280px;
      margin: 0 auto;
      padding: 14px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    h1 { margin: 0; font-size: 20px; }
    .sub { margin-top: 4px; color: var(--muted); font-size: 13px; }
    .badge {
      display: inline-flex;
      align-items: center;
      min-height: 26px;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 0 10px;
      color: var(--muted);
      font-size: 12px;
      background: #fff;
    }
    main {
      max-width: 1280px;
      margin: 0 auto;
      padding: 18px 20px 28px;
      display: grid;
      grid-template-columns: minmax(0, 1.05fr) minmax(360px, .95fr);
      gap: 14px;
      align-items: start;
    }
    .panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .panel-head {
      padding: 13px 15px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .panel-title { font-weight: 800; }
    .panel-desc { color: var(--muted); font-size: 12px; margin-top: 2px; }
    .panel-body { padding: 15px; }
    .analysis-card {
      background: linear-gradient(180deg, #fff 0%, #f8fbff 100%);
      border-top: 3px solid var(--blue);
    }
    .grid { display: grid; gap: 12px; }
    .grid.two { grid-template-columns: 1fr 1fr; }
    .field label { display: block; color: var(--muted); font-size: 12px; margin-bottom: 5px; }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; }
    .actions button { flex: 1; }
    .status-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 12px; }
    .status-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: var(--soft);
      min-height: 78px;
    }
    .kicker { color: var(--muted); font-size: 12px; }
    .value { margin-top: 4px; font-weight: 800; overflow-wrap: anywhere; }
    .note { color: var(--muted); font-size: 12px; }
    .source-list, .role-list, .history-list { display: grid; gap: 8px; }
    .source-item, .role-item, .history-item {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: var(--soft);
    }
    .source-item.selectable { cursor: pointer; background: #fff; }
    .source-item.active { border-color: var(--blue); outline: 2px solid rgba(37, 99, 235, .12); }
    .source-title, .role-title { font-weight: 800; }
    .source-meta, .role-meta, .history-meta { color: var(--muted); font-size: 12px; margin-top: 3px; }
    .ok { color: var(--green); }
    .warn { color: var(--amber); }
    .bad { color: var(--red); }
    .progress {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 8px;
      margin-top: 12px;
    }
    .step {
      border: 1px solid var(--line);
      background: var(--soft);
      border-radius: 8px;
      padding: 8px;
      min-height: 58px;
      font-size: 12px;
      color: var(--muted);
    }
    .step.active { color: var(--blue); border-color: var(--blue); background: #eff6ff; }
    .report-view {
      min-height: 620px;
      padding: 24px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      overflow-wrap: anywhere;
    }
    .report-view.empty { color: var(--muted); display: flex; align-items: center; justify-content: center; text-align: center; }
    .report-view h1 { font-size: 23px; border-bottom: 1px solid var(--line); padding-bottom: 10px; margin-top: 0; }
    .report-view h2 { margin-top: 24px; font-size: 18px; }
    .report-view ul { padding-left: 20px; }
    .download-row { display: flex; gap: 8px; justify-content: flex-end; flex-wrap: wrap; }
    .download-row button { min-height: 32px; font-size: 12px; }
    details {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      overflow: hidden;
    }
    summary { padding: 12px 14px; cursor: pointer; font-weight: 800; }
    details[open] summary { border-bottom: 1px solid var(--line); }
    .details-body { padding: 14px; }
    pre { margin: 0; white-space: pre-wrap; font-family: Consolas, "Microsoft YaHei", monospace; font-size: 13px; }
    @media (max-width: 980px) {
      main { grid-template-columns: 1fr; }
      .status-cards, .progress, .grid.two { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div class="topbar">
      <div>
        <h1>TradingAgents 中文服务工作台</h1>
        <div class="sub">输入标的，选择一个主数据源，生成投研辅助报告</div>
      </div>
      <div class="actions">
        <span class="badge">__MODE__</span>
        <span class="badge">不含实盘交易</span>
      </div>
    </div>
  </header>

  <main>
    <section class="grid">
      <section class="panel analysis-card">
        <div class="panel-head">
          <div>
            <div class="panel-title">开始分析</div>
            <div class="panel-desc">第一步只需要输入股票代码；配置项会在缺失时提示补齐</div>
          </div>
        </div>
        <div class="panel-body grid">
          <div class="grid two">
            <div class="field">
              <label for="symbol">标的代码</label>
              <input id="symbol" value="PDD" autocomplete="off">
            </div>
            <div class="field">
              <label for="date">分析日期</label>
              <input id="date" type="date">
            </div>
          </div>
          <div class="status-cards">
            <div class="status-card">
              <div class="kicker">模型状态</div>
              <div id="modelState" class="value">__PROVIDER__ / __MODEL__</div>
              <div class="note">未配置时会阻断生成</div>
            </div>
            <div class="status-card">
              <div class="kicker">数据源状态</div>
              <div id="sourceState" class="value">等待识别标的</div>
              <div class="note">每份报告只使用一个主数据源</div>
            </div>
            <div class="status-card">
              <div class="kicker">下一步</div>
              <div id="nextAction" class="value">识别市场</div>
              <div class="note">PDD / US:PDD 将识别为美股</div>
            </div>
          </div>
          <div class="actions">
            <button id="normalizeBtn">识别市场</button>
            <button id="checkBtn">检查数据源</button>
            <button id="analyzeBtn" class="primary">生成报告</button>
          </div>
          <div id="symbolBox" class="source-item">等待识别市场。</div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">主数据源</div>
            <div class="panel-desc">报告生成时按标的市场过滤；不混用多个数据源补字段</div>
          </div>
        </div>
        <div class="panel-body">
          <div id="sourceList" class="source-list">等待识别标的。</div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">角色状态与生成进度</div>
            <div class="panel-desc">展示客户能理解的分析角色状态，不显示底层调用细节</div>
          </div>
        </div>
        <div class="panel-body grid">
          <div class="progress">
            <div id="step-symbol" class="step">识别标的</div>
            <div id="step-source" class="step">读取数据</div>
            <div id="step-field" class="step">检查字段</div>
            <div id="step-report" class="step">整理报告</div>
            <div id="step-done" class="step">完成</div>
          </div>
          <div id="roleList" class="role-list"></div>
        </div>
      </section>

      <details>
        <summary>配置与售后</summary>
        <div class="details-body grid">
          <div class="grid two">
            <select id="providerSelect"></select>
            <input id="modelInput" placeholder="模型名称">
            <input id="apiKeyInput" type="password" placeholder="模型 API Key，留空则保留原配置">
            <input id="baseUrlInput" placeholder="模型服务地址，高级配置">
            <input id="eodhdInput" type="password" placeholder="EODHD Token，留空则保留原配置">
            <input id="fmpInput" type="password" placeholder="FMP Token，留空则保留原配置">
          </div>
          <div class="actions">
            <button id="loadConfigBtn">读取配置</button>
            <button id="saveConfigBtn">保存配置</button>
            <button id="testModelBtn">测试模型</button>
            <button id="diagBtn" class="secondary">导出诊断</button>
          </div>
          <div id="configStatus" class="source-item">配置入口已后置。正常分析路径无需查看技术细节。</div>
        </div>
      </details>
    </section>

    <section class="grid">
      <section class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">当前报告</div>
            <div class="panel-desc">报告内容优先展示；下载只是次级动作</div>
          </div>
          <div class="download-row">
            <button id="downloadMdBtn" class="secondary" disabled>Markdown</button>
            <button id="downloadDocxBtn" class="secondary" disabled>Word</button>
            <button id="downloadPdfBtn" class="secondary" disabled>PDF</button>
          </div>
        </div>
        <div class="panel-body">
          <div id="reportView" class="report-view empty">输入 PDD 或 US:PDD，选择主数据源后生成报告。</div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">历史报告</div>
            <div class="panel-desc">历史记录只作为回看入口，不抢当前报告主位置</div>
          </div>
        </div>
        <div class="panel-body">
          <div id="historyList" class="history-list">正在加载历史报告。</div>
        </div>
      </section>
    </section>
  </main>

  <script>
    const $ = (id) => document.getElementById(id);
    let currentSymbol = null;
    let selectedSource = "eodhd";
    let selectedSourceAllowed = false;
    let selectedSourceReason = "";
    let providers = {};
    let lastMarkdown = "";
    let lastReportId = "";

    const sourceNames = { eodhd: "EODHD", fmp: "FMP", yfinance: "yfinance", alpha_vantage: "Alpha Vantage" };

    function today() { return new Date().toISOString().slice(0, 10); }
    function setStep(activeId) {
      ["step-symbol", "step-source", "step-field", "step-report", "step-done"].forEach((id) => $(id).classList.toggle("active", id === activeId));
    }
    function customerError(text) {
      return `${text}。请稍后重试，或导出诊断包交给服务人员。`;
    }
    async function requestJson(url, options) {
      const response = await fetch(url, options);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || response.statusText);
      return payload;
    }
    function escapeHtml(value) {
      return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
    }
    function markdownToHtml(markdown) {
      if (!markdown) return "";
      const blocks = [];
      let list = [];
      const flush = () => {
        if (list.length) {
          blocks.push(`<ul>${list.map((item) => `<li>${item}</li>`).join("")}</ul>`);
          list = [];
        }
      };
      markdown.split(/\\r?\\n/).forEach((line) => {
        const text = line.trim();
        if (!text) { flush(); return; }
        if (text.startsWith("# ")) { flush(); blocks.push(`<h1>${escapeHtml(text.slice(2))}</h1>`); }
        else if (text.startsWith("## ")) { flush(); blocks.push(`<h2>${escapeHtml(text.slice(3))}</h2>`); }
        else if (text.startsWith("- ")) { list.push(escapeHtml(text.slice(2))); }
        else { flush(); blocks.push(`<p>${escapeHtml(text)}</p>`); }
      });
      flush();
      return blocks.join("");
    }
    function renderRoles(roles) {
      const fallback = [
        { name: "市场分析师", status: "等待", detail: "等待读取行情数据" },
        { name: "基本面分析师", status: "等待", detail: "等待字段检查" },
        { name: "新闻分析师", status: "等待", detail: "等待字段检查" },
        { name: "风险分析师", status: "等待", detail: "等待生成报告" },
        { name: "研究经理", status: "等待", detail: "等待汇总报告" }
      ];
      $("roleList").innerHTML = (roles && roles.length ? roles : fallback).map((role) => {
        const cls = role.status === "可用" ? "ok" : role.status === "字段不足" ? "warn" : "";
        return `<div class="role-item"><div class="role-title">${escapeHtml(role.name)} <span class="${cls}">${escapeHtml(role.status)}</span></div><div class="role-meta">${escapeHtml(role.detail || "")}</div></div>`;
      }).join("");
    }
    function renderSources(payload) {
      const market = payload.symbol.market;
      const all = (payload.grouped && payload.grouped[market]) || [];
      const visible = all.filter((item) => ["eodhd", "fmp", "yfinance", "alpha_vantage"].includes(item.key) || market !== "US");
      const selectable = visible.filter((item) => item.selectable_for_current_symbol);
      if (!visible.find((item) => item.key === selectedSource)) selectedSource = (selectable[0] || visible[0] || {}).key || selectedSource;
      const current = visible.find((item) => item.key === selectedSource);
      selectedSourceAllowed = !!(current && current.selectable_for_current_symbol);
      selectedSourceReason = current ? (current.selectable_reason || "当前数据源不可用于本次报告。") : "请选择一个可用数据源。";
      $("sourceList").innerHTML = visible.map((item) => {
        const canSelect = item.selectable_for_current_symbol;
        const active = item.key === selectedSource;
        const statusClass = canSelect ? "ok" : (item.current_symbol_status || "").includes("权限") || (item.current_symbol_status || "").includes("失败") ? "bad" : "warn";
        return `<div class="source-item ${canSelect ? "selectable" : ""} ${active ? "active" : ""}" data-source="${item.key}">
          <div class="source-title">${escapeHtml(item.name)} <span class="${statusClass}">${escapeHtml(item.current_symbol_status || item.runtime_status || item.status)}</span></div>
          <div class="source-meta">能力：${escapeHtml((item.abilities || []).join(" / "))}</div>
          <div class="source-meta">映射代码：${escapeHtml(item.mapped_symbol || "不适用")}</div>
          <div class="source-meta">本次状态：${escapeHtml(item.selectable_reason || "")}</div>
          <div class="source-meta">${escapeHtml(item.recommended_for || "")}</div>
        </div>`;
      }).join("") || "当前市场暂无可选数据源。";
      document.querySelectorAll(".source-item[data-source]").forEach((node) => {
        node.addEventListener("click", () => {
          selectedSource = node.getAttribute("data-source") || selectedSource;
          renderSources(payload);
        });
      });
      $("sourceState").textContent = selectable.length ? `可选 ${selectable.length} 个 ${payload.market_name} 数据源` : "当前市场没有可用报告数据源";
    }
    async function normalizeSymbol() {
      setStep("step-symbol");
      const symbol = $("symbol").value.trim() || "PDD";
      currentSymbol = await requestJson(`/api/normalize-symbol?symbol=${encodeURIComponent(symbol)}`);
      $("symbolBox").innerHTML = `<strong>${escapeHtml(currentSymbol.display)}</strong><div class="source-meta">市场：${escapeHtml(currentSymbol.market)}；标准代码：${escapeHtml(currentSymbol.canonical)}；识别置信度：${escapeHtml(currentSymbol.confidence)}</div>`;
      $("nextAction").textContent = "选择主数据源";
      const sources = await requestJson(`/api/data-sources?symbol=${encodeURIComponent(symbol)}`);
      renderSources(sources);
      return currentSymbol;
    }
    async function checkData() {
      if (!currentSymbol) await normalizeSymbol();
      setStep("step-source");
      const payload = await requestJson(`/api/market-snapshot?symbol=${encodeURIComponent($("symbol").value)}&data_source=${encodeURIComponent(selectedSource)}`);
      if (payload.status === "ok") {
        $("nextAction").textContent = "生成报告";
        $("sourceState").textContent = `${sourceNames[selectedSource] || selectedSource} 可用于本次报告`;
      } else {
        $("nextAction").textContent = "处理数据源提示";
        $("sourceState").textContent = payload.message || "数据源暂时不可用";
      }
      const sources = await requestJson(`/api/data-sources?symbol=${encodeURIComponent($("symbol").value)}`);
      renderSources(sources);
      renderRoles(payload.roles || []);
      return payload;
    }
    async function analyze() {
      setStep("step-field");
      $("reportView").className = "report-view empty";
      $("reportView").textContent = "正在检查字段并生成报告。";
      try {
        if (!currentSymbol) await normalizeSymbol();
        if (!selectedSourceAllowed) {
          $("nextAction").textContent = "生成数据源阻断说明";
        }
        setStep("step-source");
        const params = new URLSearchParams();
        params.set("symbol", $("symbol").value.trim() || "PDD");
        params.set("data_source", selectedSource);
        params.set("report_template", "basic");
        if ($("date").value) params.set("date", $("date").value);
        setStep("step-report");
        const payload = await requestJson(`/api/analyze?${params.toString()}`, { method: "POST" });
        renderRoles(payload.role_progress || (payload.market_snapshot && payload.market_snapshot.roles) || []);
        lastMarkdown = payload.report && payload.report.markdown ? payload.report.markdown : "";
        lastReportId = payload.saved_report && payload.saved_report.id ? payload.saved_report.id : "";
        $("downloadMdBtn").disabled = !lastMarkdown;
        $("downloadDocxBtn").disabled = !lastReportId;
        $("downloadPdfBtn").disabled = !lastReportId;
        $("reportView").className = "report-view";
        $("reportView").innerHTML = lastMarkdown ? markdownToHtml(lastMarkdown) : `<p>${escapeHtml(payload.message || "报告未生成。")}</p>`;
        $("nextAction").textContent = payload.status === "ok" ? "查看当前报告" : "按提示处理后重试";
        setStep(payload.status === "ok" ? "step-done" : "step-field");
        loadReports();
      } catch (error) {
        $("reportView").className = "report-view empty";
        $("reportView").textContent = error.message || customerError("报告生成失败");
        $("nextAction").textContent = "按提示处理后重试";
        setStep("step-field");
      }
    }
    async function loadConfig() {
      const payload = await requestJson("/api/config");
      const config = payload.config || {};
      providers = {};
      $("providerSelect").innerHTML = (payload.providers || []).map((item) => {
        providers[item.key] = item;
        return `<option value="${item.key}">${escapeHtml(item.label)}</option>`;
      }).join("");
      $("providerSelect").value = config.provider || "qwen-cn";
      const defaults = providers[$("providerSelect").value] || {};
      $("modelInput").value = config.model || defaults.default_model || "";
      $("baseUrlInput").value = config.base_url || defaults.default_base_url || "";
      $("apiKeyInput").value = "";
      $("eodhdInput").value = "";
      $("fmpInput").value = "";
      const dataTokens = config.data_tokens || {};
      $("modelState").textContent = config.api_key_configured ? `${config.provider || "模型"} 已配置` : "模型未配置";
      $("configStatus").textContent = `模型：${config.api_key_configured ? "已配置" : "未配置"}；EODHD：${dataTokens.eodhd ? "已配置" : "未配置"}；FMP：${dataTokens.fmp ? "已配置" : "未配置"}`;
    }
    async function saveConfig() {
      $("configStatus").textContent = "正在保存配置。";
      const payload = await requestJson("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: $("providerSelect").value,
          model: $("modelInput").value,
          base_url: $("baseUrlInput").value,
          api_key: $("apiKeyInput").value,
          eodhd_api_key: $("eodhdInput").value,
          fmp_api_key: $("fmpInput").value,
          keep_existing_key: true
        })
      });
      $("apiKeyInput").value = "";
      $("eodhdInput").value = "";
      $("fmpInput").value = "";
      $("configStatus").textContent = "配置已保存。";
      loadConfig();
    }
    async function testModel() {
      $("configStatus").textContent = "正在测试模型连接。";
      const payload = await requestJson("/api/config/test-model", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: $("providerSelect").value,
          model: $("modelInput").value,
          base_url: $("baseUrlInput").value,
          api_key: $("apiKeyInput").value
        })
      });
      $("configStatus").textContent = payload.message || "模型测试完成。";
      $("modelState").textContent = payload.status === "ok" ? "模型连接成功" : "模型连接失败";
    }
    async function loadReports() {
      try {
        const payload = await requestJson("/api/reports?limit=6");
        const reports = payload.reports || [];
        $("historyList").innerHTML = reports.length ? reports.map((report) => {
          const symbol = report.symbol && (report.symbol.canonical || report.symbol.raw) || "";
          return `<button class="history-item" data-id="${escapeHtml(report.id)}"><div><strong>${escapeHtml(report.title || symbol)}</strong></div><div class="history-meta">${escapeHtml(report.analysis_date || "")} / ${escapeHtml(report.data_source || "")} / ${escapeHtml(report.status || "")}</div></button>`;
        }).join("") : "暂无历史报告。";
        document.querySelectorAll(".history-item[data-id]").forEach((node) => node.addEventListener("click", async () => {
          const id = node.getAttribute("data-id");
          const payload = await requestJson(`/api/reports/${encodeURIComponent(id)}`);
          lastMarkdown = payload.markdown || "";
          lastReportId = id;
          $("downloadMdBtn").disabled = !lastMarkdown;
          $("downloadDocxBtn").disabled = !lastReportId;
          $("downloadPdfBtn").disabled = !lastReportId;
          $("reportView").className = "report-view";
          $("reportView").innerHTML = markdownToHtml(lastMarkdown);
        }));
      } catch (error) {
        $("historyList").textContent = customerError("历史报告加载失败");
      }
    }
    $("providerSelect").addEventListener("change", () => {
      const defaults = providers[$("providerSelect").value] || {};
      $("modelInput").value = defaults.default_model || $("modelInput").value;
      $("baseUrlInput").value = defaults.default_base_url || $("baseUrlInput").value;
    });
    $("normalizeBtn").addEventListener("click", () => normalizeSymbol().catch((error) => $("symbolBox").textContent = error.message || customerError("标的识别失败")));
    $("checkBtn").addEventListener("click", () => checkData().catch((error) => $("sourceState").textContent = error.message || customerError("数据源检查失败")));
    $("analyzeBtn").addEventListener("click", analyze);
    $("loadConfigBtn").addEventListener("click", () => loadConfig().catch((error) => $("configStatus").textContent = error.message || customerError("配置读取失败")));
    $("saveConfigBtn").addEventListener("click", () => saveConfig().catch((error) => $("configStatus").textContent = error.message || customerError("配置保存失败")));
    $("testModelBtn").addEventListener("click", () => testModel().catch((error) => $("configStatus").textContent = error.message || customerError("模型测试失败")));
    $("diagBtn").addEventListener("click", () => window.open("/api/diagnostics.txt", "_blank"));
    $("downloadMdBtn").addEventListener("click", () => {
      if (!lastMarkdown) return;
      const blob = new Blob([lastMarkdown], { type: "text/markdown;charset=utf-8" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `tradingagents-report-${$("symbol").value || "symbol"}.md`;
      link.click();
      URL.revokeObjectURL(link.href);
    });
    $("downloadDocxBtn").addEventListener("click", () => { if (lastReportId) window.open(`/api/reports/${encodeURIComponent(lastReportId)}.docx`, "_blank"); });
    $("downloadPdfBtn").addEventListener("click", () => { if (lastReportId) window.open(`/api/reports/${encodeURIComponent(lastReportId)}.pdf`, "_blank"); });
    $("date").value = today();
    renderRoles();
    loadConfig().catch(() => {});
    normalizeSymbol().catch(() => {});
    loadReports();
  </script>
</body>
</html>
"""
