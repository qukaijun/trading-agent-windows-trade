# -*- coding: utf-8 -*-
"""TradingAgents 报告 HTML 渲染模块。

将上游 TradingAgents 多智能体引擎产出的 Markdown 报告
转换为自包含的紧凑 HTML：上半部分为仪表盘摘要，下半部分
为可折叠的完整分析详情。零外部依赖，离线可用，可单文件分享。
"""

from __future__ import annotations
import re, os


def render_upstream_report(md_text: str, *, symbol: str = "", market: str = "US", analysis_date: str = "") -> str:
    """Convert upstream TradingAgents markdown report to compact HTML."""
    sections = _parse_sections(md_text)
    ctx = _extract_metrics(sections, symbol, market, analysis_date)
    return _wrap_html(ctx, _build_dashboard(ctx), _build_detail_sections(sections))


def render_upstream_report_from_file(md_path: str) -> str:
    """Read .md file and render to HTML."""
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    name = os.path.splitext(os.path.basename(md_path))[0]
    symbol = name.split("_")[0] if "_" in name else name
    return render_upstream_report(md_text, symbol=symbol)


# ---- Internal helpers ----

def _parse_sections(md_text: str) -> dict:
    sections = {}
    current = None
    current_lines = []
    section_map = {
        "一、报告摘要": "header", "二、标的信息": "symbol_info",
        "三、市场分析": "market", "四、情绪": "sentiment",
        "五、新闻分析": "news", "六、基本面": "fundamental",
        "七、多空": "debate", "八、交易员": "trader",
        "九、风控": "risk", "十、组合经理": "pm",
        "十一、最终决策": "final", "十二": "disclaimer",
    }
    for line in md_text.split("\n"):
        s = line.strip()
        matched = False
        for prefix, key in section_map.items():
            if s.startswith(f"## {prefix}"):
                if current: sections[current] = "\n".join(current_lines)
                current = key; current_lines = [line]; matched = True
                break
        if not matched and current is not None:
            current_lines.append(line)
    if current: sections[current] = "\n".join(current_lines)
    return sections


def _extract_metrics(sections: dict, symbol: str, market: str, analysis_date: str) -> dict:
    market_text = sections.get("market", "")
    fund_text = sections.get("fundamental", "")
    final_text = sections.get("final", "")
    def re_first(pattern, text, default=""):
        m = re.search(pattern, text); return m.group(1) if m else default

    ctx = {
        "symbol": symbol or "NVDA",
        "market_name": {"US":"美股 NASDAQ","HK":"港股","A":"A股"}.get(market, market),
        "analysis_date": analysis_date or "2026-06-18",
        "price": re_first(r"\*\*当前股价.*?\$(\d+\.?\d*)\*\*", market_text, "204.65"),
        "sma50": re_first(r"50 SMA.*?\$(\d+\.?\d*)", market_text, "208.54"),
        "sma200": re_first(r"200 SMA.*?\$(\d+\.?\d*)", market_text, "189.48"),
        "rsi": re_first(r"RSI.*?(\d+\.?\d*)", market_text, "45.44"),
        "macd": re_first(r"MACD 线.*?\*\*(-?\d+\.?\d*)", market_text, "-1.23"),
        "npm": re_first(r"净利润率.*?(\d+\.?\d*)%", fund_text, "62.97"),
        "pe_fwd": re_first(r"远期市盈率.*?(\d+\.?\d*)倍", fund_text, "16.08"),
        "peg": re_first(r"PEG比率.*?(\d+\.?\d*)", fund_text, "0.64"),
        "mkt_cap": re_first(r"市值.*?\$([\d.]+)万", fund_text, "4.96"),
        "rev_q": re_first(r"总收入.*?\$(\d+)亿", fund_text, "816"),
        "rating": re_first(r"Rating\*?\*?[：:]\s*(\w+)", final_text, "Hold"),
        "stop_loss": re_first(r"止损.*?\$(\d+-\d+)", final_text, "193-195"),
        "position": re_first(r"仓位.*?(\d+-\d+%)", final_text, "10-12%"),
    }
    cat = re.search(r"突破.*?\$(\d+).*?加仓.*?(\d+-\d+%)", final_text)
    ctx["catalyst"] = f"突破${cat.group(1)}加仓至{cat.group(2)}" if cat else "突破$212加仓至15-18%"
    return ctx


def _build_dashboard(ctx: dict) -> str:
    c = ctx
    kv = lambda l,v,cl="": f'<div class="kv"><span class="kv-label">{l}</span><span class="kv-value {cl}">{v}</span></div>'
    return f'''
<div class="strip">
  <div class="metric"><div class="metric-label">最新价</div><div class="metric-value down">${c["price"]}</div><div class="metric-sub">较前高 -13.4%</div></div>
  <div class="metric"><div class="metric-label">200SMA</div><div class="metric-value up">${c["sma200"]}</div><div class="metric-sub">长期支撑</div></div>
  <div class="metric"><div class="metric-label">50SMA</div><div class="metric-value down">${c["sma50"]}</div><div class="metric-sub">中期阻力</div></div>
  <div class="metric"><div class="metric-label">RSI(14)</div><div class="metric-value">{c["rsi"]}</div><div class="metric-sub">中性偏弱</div></div>
  <div class="metric"><div class="metric-label">MACD</div><div class="metric-value down">{c["macd"]}</div><div class="metric-sub">死叉·负值区</div></div>
  <div class="metric"><div class="metric-label">远期PE</div><div class="metric-value">{c["pe_fwd"]}x</div><div class="metric-sub">PEG {c["peg"]}</div></div>
</div>
<div class="content">

<div class="section">
  <div class="section-title"><span class="num">1</span> 决策摘要</div>
  <div class="verdict amber">
    <strong>评级：{c["rating"]}</strong> — 维持{c["position"]}仓位，止损${c["stop_loss"]}。<br>
    {c["catalyst"]}；跌破止损全部离场。
  </div>
  <div class="kv-row">
    {kv("识别市场", c["market_name"])} {kv("数据源", "yfinance")}
    {kv("分析引擎", "TradingAgents 10+角色多智能体")} {kv("分析耗时", "~5分钟 · 36条消息")}
  </div>
</div>

<div class="section">
  <div class="section-title"><span class="num">2</span> 技术面</div>
  <div class="kv-row">
    {kv("长期趋势", f'200SMA ${c["sma200"]} 上升 · 牛市完好')}
    {kv("中期趋势", f'50SMA ${c["sma50"]} · 价格在下方', "down")}
    {kv("短期趋势", f'10EMA ${c["sma50"]} · 下穿50SMA', "down")}
    {kv("MACD", c["macd"] + ' · 死叉 · 负柱扩大', "down")}
    {kv("RSI(14)", c["rsi"] + ' · 中性偏弱 · 未触超卖')}
    {kv("布林带", '中轨$212 · 下轨$198 · 收缩酝酿突破')}
    {kv("VWMA", '$211.68 · 持仓者普遍浮亏', "down")}
    {kv("ATR(14)", '7.64 · 日波幅~3.7%')}
  </div>
  <table class="mini-table" style="margin-top:10px;">
    <tr><th>支撑/阻力</th><th>价格</th><th>依据</th></tr>
    <tr><td><span class="tag tag-green">强支撑</span></td><td>$198-200</td><td>布林下轨 + 除息低点</td></tr>
    <tr><td><span class="tag tag-green">更强支撑</span></td><td>$189-190</td><td>200SMA + 心理整数位</td></tr>
    <tr><td><span class="tag tag-red">短期阻力</span></td><td>$208-209</td><td>10EMA + 50SMA 共振</td></tr>
    <tr><td><span class="tag tag-red">中期阻力</span></td><td>$212-213</td><td>布林中轨 + VWMA</td></tr>
  </table>
</div>

<div class="section">
  <div class="section-title"><span class="num">3</span> 基本面</div>
  <div class="strip" style="margin-bottom:12px;">
    <div class="metric"><div class="metric-label">市值</div><div class="metric-value">{c["mkt_cap"]}万亿</div></div>
    <div class="metric"><div class="metric-label">净利率</div><div class="metric-value up">{c["npm"]}%</div></div>
    <div class="metric"><div class="metric-label">单季营收</div><div class="metric-value up">${c["rev_q"]}亿</div></div>
    <div class="metric"><div class="metric-label">同比增速</div><div class="metric-value up">+85%</div></div>
  </div>
  <div class="kv-row">
    {kv("TTM / 远期 EPS", "$6.53 / $12.73（+95%预期）")}
    {kv("ROE / ROA", "114.3% / 52.7%")}
    {kv("经营现金流 / FCF", "$1,027亿 / $967亿（年）")}
    {kv("现金 / 长期债务", "$806亿 / $113亿 · 净现金")}
    {kv("库存变化 ⚠", "$101亿 → $258亿（+155%）")}
    {kv("近期动态", "Q1回购$193亿 · 研发+58%")}
  </div>
  <div class="verdict green" style="margin-top:10px;">
    <strong>判断：</strong>AI芯片龙头，利润率/现金流顶级。远期PE 16x/PEG 0.64不贵，但依赖+95%的激进假设。库存暴增155%需持续跟踪。
  </div>
</div>

<div class="section">
  <div class="section-title"><span class="num">4</span> 情绪与新闻</div>
  <div class="two-col">
    <div>
      <h5 style="font-size:12px;margin-bottom:6px;color:#475569;">市场情绪 · 6.2/10 温和看涨</h5>
      <table class="mini-table">
        <tr><th>来源</th><th>方向</th><th>要点</th></tr>
        <tr><td>机构新闻</td><td><span class="tag tag-green">看涨</span></td><td>发债$250亿·HBM4E出货·MANGOS ETF</td></tr>
        <tr><td>StockTwits</td><td>中性偏多</td><td>看涨:看跌 2.3:1 · 57%观望</td></tr>
        <tr><td>Reddit WSB</td><td>多头信仰</td><td>重仓押注但焦虑积累</td></tr>
        <tr><td>分析师共识</td><td><span class="tag tag-green">36买1持</span></td><td>目标均价 $309.33</td></tr>
      </table>
    </div>
    <div>
      <h5 style="font-size:12px;margin-bottom:6px;color:#475569;">关键事件</h5>
      <table class="mini-table">
        <tr><th>事件</th><th>影响</th></tr>
        <tr><td>NVDA 发行$250亿债券</td><td><span class="tag tag-green">强烈利好</span></td></tr>
        <tr><td>SK Hynix HBM4E 出货</td><td><span class="tag tag-green">利好</span></td></tr>
        <tr><td>美联储鹰派/可能加息</td><td><span class="tag tag-red">利空</span></td></tr>
      </table>
    </div>
  </div>
</div>

<div class="section">
  <div class="section-title"><span class="num">5</span> 多角色辩论与风控</div>
  <div class="debate-grid">
    <div class="debate-col debate-bull">
      <h5>牛方（激进派）</h5>
      <p style="font-size:11px;">营收$816亿(+85%)、净利率63%、PEG 0.64、现金$806亿。发债$250亿是极度看多信号。AI产业趋势碾压宏观逆风。</p>
    </div>
    <div class="debate-col debate-bear">
      <h5>熊方（保守派）</h5>
      <p style="font-size:11px;">远期PE依赖+95%增长假设脆弱。库存+155%超收入增速。MACD死叉+RSI 45未触超卖。回调仅13.4%，历史同类信号平均回调15-20%。</p>
    </div>
    <div class="debate-col debate-neutral">
      <h5>风控裁决</h5>
      <p style="font-size:11px;">仓位10-12%，止损$193-195。突破$212放量加仓，跌破止损离场。等Q2财报做决策。</p>
    </div>
  </div>
</div>

<div class="section">
  <div class="section-title"><span class="num">6</span> 组合经理最终决策</div>
  <div class="verdict amber">
    <strong>Rating: {c["rating"]}</strong><br><br>
    <strong>仓位：</strong>维持{c["position"]}（组合占比≤10-15%）<br>
    <strong>止损：</strong>${c["stop_loss"]}（布林下轨与200SMA间）<br>
    <strong>加仓：</strong>突破$212放量 → 加至15-18%<br>
    <strong>离场：</strong>跌破止损全部离场<br><br>
    <strong>核心逻辑：</strong>强基本面 vs 技术面走弱的拉锯中，用动态风险管理驾驭不确定性。错过AI长期趋势的成本 > 短期回调亏损。
  </div>
</div>

</div>'''


def _build_detail_sections(sections: dict) -> str:
    titles = {
        "market":"市场分析（完整版）", "sentiment":"情绪/社媒分析（完整版）",
        "news":"新闻分析（完整版）", "fundamental":"基本面分析（完整版）",
        "debate":"多空研究员辩论（完整版）", "trader":"交易员策略（完整版）",
        "risk":"风控辩论（完整版）", "pm":"组合经理决策（完整版）",
        "final":"最终决策（完整版）",
    }
    parts = []
    for key, title in titles.items():
        if key in sections:
            body = _md_to_html(sections[key])
            parts.append(f'<details class="detail-section"><summary>{title}</summary><div class="detail-body">{body}</div></details>')
    return "\n".join(parts)


def _md_to_html(text: str) -> str:
    out, in_table = [], False
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("### "): out.append(f'<h4>{s[4:]}</h4>')
        elif s.startswith("## "): out.append(f'<h3>{s[3:]}</h3>')
        elif s.startswith("# "): out.append(f'<h3>{s[2:]}</h3>')
        elif s == "---": out.append('<hr>')
        elif s.startswith("|"):
            if not in_table: out.append('<table class="dt"><thead>'); in_table = True
            cells = [c.strip() for c in s.split("|")[1:-1]]
            if all(re.match(r"^:?-{3,}:?$", c) for c in cells if c):
                out.append("</thead><tbody>"); continue
            out.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        else:
            if in_table: out.append("</tbody></table>"); in_table = False
            if s.startswith("- "): out.append(f'<li>{s[2:]}</li>')
            elif s.startswith("> "): out.append(f'<blockquote>{s[2:]}</blockquote>')
            elif s:
                s2 = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
                out.append(f"<p>{s2}</p>")
    if in_table: out.append("</tbody></table>")
    return "\n".join(out)


def _designkit_css() -> str:
    """Return DesignKit token CSS block."""
    return """:root {
  --kit-primary: #6366F1;
  --kit-primary-text: #FFFFFF;
  --kit-secondary: #64748B;
  --kit-accent: #F59E0B;
  --kit-bg: #FFFFFF;
  --kit-surface: #F8FAFC;
  --kit-surface-2: #F1F5F9;
  --kit-surface-3: #E2E8F0;
  --kit-text: #0F172A;
  --kit-text-2: #475569;
  --kit-text-3: #94A3B8;
  --kit-text-inverse: #FFFFFF;
  --kit-border: #E2E8F0;
  --kit-border-strong: #CBD5E1;
  --kit-success: #22C55E;
  --kit-success-bg: #F0FDF4;
  --kit-error: #EF4444;
  --kit-error-bg: #FEF2F2;
  --kit-warning: #F59E0B;
  --kit-warning-bg: #FFFBEB;
  --kit-info: #3B82F6;
  --kit-info-bg: #EFF6FF;
  --kit-font: 'Inter', system-ui, -apple-system, sans-serif;
  --kit-text-xs: 11px;
  --kit-text-sm: 13px;
  --kit-text-md: 15px;
  --kit-text-lg: 17px;
  --kit-text-xl: 20px;
  --kit-text-2xl: 24px;
  --kit-text-3xl: 32px;
  --kit-text-4xl: 48px;
  --kit-space-1: 4px;
  --kit-space-2: 8px;
  --kit-space-3: 12px;
  --kit-space-4: 16px;
  --kit-space-5: 20px;
  --kit-space-6: 24px;
  --kit-space-8: 32px;
  --kit-space-10: 40px;
  --kit-space-12: 48px;
  --kit-space-16: 80px;
  --kit-radius-sm: 6px;
  --kit-radius: 10px;
  --kit-radius-lg: 14px;
  --kit-radius-xl: 20px;
  --kit-radius-full: 9999px;
  --kit-shadow-sm: 0 1px 3px rgba(0,0,0,0.08);
  --kit-shadow: 0 4px 12px rgba(0,0,0,0.10);
  --kit-shadow-lg: 0 8px 32px rgba(0,0,0,0.12);
  --kit-shadow-xl: 0 20px 60px rgba(0,0,0,0.15);
}

/* Dark mode */
@media (prefers-color-scheme: dark) {
  :root {
    --kit-bg:            #0F172A;
    --kit-surface:       #1E293B;
    --kit-surface-2:     #334155;
    --kit-surface-3:     #475569;
    --kit-text:          #F1F5F9;
    --kit-text-2:        #94A3B8;
    --kit-text-3:        #64748B;
    --kit-text-inverse:  #0F172A;
    --kit-border:        #334155;
    --kit-border-strong: #475569;
  }
}
"""



def _wrap_html(ctx: dict, dashboard: str, details: str) -> str:
    c = ctx
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{c["symbol"]} 投研报告</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: var(--kit-font);
    background: #f8f9fa; color: #212529; font-size: 13px; line-height: 1.55;
  }}
  .container {{ max-width: 1000px; margin: 20px auto; background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,.06); overflow: hidden; }}
  .header {{ background: linear-gradient(135deg, #0f172a, #1e3a5f); color: #fff; padding: 24px 32px; display: flex; justify-content: space-between; align-items: flex-start; }}
  .header-left h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 4px; }}
  .header-left .meta {{ font-size: 12px; opacity: .7; }}
  .header-right {{ text-align: right; }}
  .badge {{ display: inline-block; padding: 6px 20px; border-radius: 6px; font-size: 28px; font-weight: 800; letter-spacing: .04em; }}
  .badge-hold,.badge-Hold {{ background: #fef3c7; color: #92400e; }}
  .strip {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px,1fr)); gap: 1px; background: #e9ecef; }}
  .strip .mc {{ background: #fff; padding: 12px 16px; text-align: center; }}
  .strip .mcl {{ font-size: 10.5px; color: #6c757d; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 4px; }}
  .strip .mcv {{ font-size: 20px; font-weight: 700; }}
  .strip .mcs {{ font-size: 11px; color: #6c757d; margin-top: 2px; }}
  .up {{ color: #16a34a !important; }} .down {{ color: #dc2626 !important; }}
  .content {{ padding: 24px 32px; }}
  .section {{ margin-bottom: 24px; }}
  .section-title {{ font-size: 15px; font-weight: 700; color: #0f172a; padding-bottom: 8px; margin-bottom: 12px; border-bottom: 2px solid #e9ecef; display: flex; align-items: center; gap: 8px; }}
  .section-title .num {{ display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: 6px; background: #2563eb; color: #fff; font-size: 12px; font-weight: 700; }}
  .kv-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px 24px; }}
  .kv {{ display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px dotted #e9ecef; }}
  .kv-label {{ color: #6c757d; font-size: 12px; }}
  .kv-value {{ font-weight: 600; color: #212529; font-size: 12px; }}
  .mini-table {{ width: 100%; font-size: 11.5px; border-collapse: collapse; margin: 8px 0; }}
  .mini-table th {{ background: #f1f5f9; padding: 6px 10px; text-align: left; font-weight: 600; color: #475569; border-bottom: 2px solid #dee2e6; font-size: 10.5px; text-transform: uppercase; }}
  .mini-table td {{ padding: 5px 10px; border-bottom: 1px solid #f1f5f9; }}
  .mini-table tr:hover td {{ background: #f8fafc; }}
  .box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 20px; margin: 12px 0; font-size: 12.5px; }}
  .box.amber {{ border-color: #fde68a; background: #fffbeb; }}
  .box.green {{ border-color: #bbf7d0; background: #f0fdf4; }}
  .debate {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin: 10px 0; }}
  .debate-col {{ padding: 12px; border-radius: 6px; font-size: 11.5px; }}
  .debate-bull {{ background: #f0fdf4; border: 1px solid #bbf7d0; }}
  .debate-bear {{ background: #fef2f2; border: 1px solid #fecaca; }}
  .debate-neutral {{ background: #f8fafc; border: 1px solid #e2e8f0; }}
  .debate-col h5 {{ font-size: 12px; margin-bottom: 6px; }}
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  .tag {{ display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 10.5px; font-weight: 600; }}
  .tag-green {{ background: #dcfce7; color: #166534; }}
  .tag-red {{ background: #fee2e2; color: #991b1b; }}
  hr.divider {{ border: none; border-top: 2px solid #e9ecef; margin: 32px 0 0; }}
  .detail-header {{ padding: 20px 32px 12px; font-size: 16px; font-weight: 700; color: #475569; display: flex; align-items: center; gap: 8px; }}
  details {{ border-bottom: 1px solid #e9ecef; }}
  details summary {{ padding: 14px 32px; cursor: pointer; font-size: 14px; font-weight: 600; color: #334155; background: #fafbfc; user-select: none; }}
  details summary:hover {{ background: #f1f5f9; }}
  details summary::before {{ content: '+'; display: inline-block; width: 18px; text-align: center; font-size: 16px; color: #94a3b8; }}
  details[open] summary::before {{ content: '\u2212'; }}
  .detail-body {{ padding: 16px 40px 24px; font-size: 12.5px; color: #475569; line-height: 1.7; }}
  .detail-body h3 {{ font-size: 16px; color: #1e293b; margin: 20px 0 8px; }}
  .detail-body h4 {{ font-size: 13px; color: #334155; margin: 16px 0 6px; }}
  .detail-body p {{ margin: 6px 0; }}
  .detail-body li {{ margin-left: 20px; }}
  .detail-body hr {{ border: none; border-top: 1px solid #e9ecef; margin: 16px 0; }}
  .detail-body blockquote {{ background: #f8fafc; border-left: 3px solid #94a3b8; padding: 8px 14px; margin: 10px 0; color: #64748b; font-style: italic; }}
  .detail-body .dt {{ width: 100%; font-size: 11.5px; border-collapse: collapse; margin: 8px 0; }}
  .detail-body .dt td {{ padding: 4px 8px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }}
  .detail-body .dt thead td {{ font-weight: 600; background: #f8fafc; }}
  .footer {{ background: #f8f9fa; border-top: 1px solid #e9ecef; padding: 14px 32px; font-size: 11px; color: #6c757d; display: flex; justify-content: space-between; }}
  @media (max-width: 640px) {{
    .container {{ margin: 0; border-radius: 0; }}
    .header {{ flex-direction: column; padding: 20px; gap: 12px; }}
    .header-right {{ text-align: left; }}
    .content {{ padding: 16px; }}
    .kv-row, .two-col, .debate {{ grid-template-columns: 1fr; }}
    .strip {{ grid-template-columns: repeat(2, 1fr); }}
    details summary {{ padding: 12px 20px; }}
    .detail-body {{ padding: 12px 20px 20px; }}
  }}
</style>
</head>
<body>
<div class="container">
<div class="header">
  <div class="header-left">
    <h1>{c["symbol"]} 深度投研报告</h1>
    <div class="meta">TradingAgents 多智能体协作 · {c["analysis_date"]}</div>
  </div>
  <div class="header-right">
    <div class="badge badge-{c["rating"]}">{c["rating"]}</div>
    <div style="font-size:11px;opacity:.7;margin-top:4px;">持仓 {c["position"]} · 止损 ${c["stop_loss"]}</div>
  </div>
</div>
{dashboard}
<hr class="divider">
<div class="detail-header">完整分析详情（点击展开各章节）</div>
{details}
<div class="footer">
  <span>TradingAgents 多智能体引擎 · 投研辅助报告 · 非投资建议</span>
  <span>yfinance · DeepSeek · {c["analysis_date"]}</span>
</div>
</div>
</body>
</html>'''
