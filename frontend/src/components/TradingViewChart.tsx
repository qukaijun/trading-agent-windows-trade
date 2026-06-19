import { useState } from "react";

const SYMBOL_MAP: Record<string, string> = {
  GOLD: "OANDA:XAUUSD",
  "XAGUSD": "OANDA:XAGUSD",
  "BTC-USD": "COINBASE:BTCUSD",
  "ETH-USD": "COINBASE:ETHUSD",
};

const INTERVALS = [
  { value: "5", label: "5分" },
  { value: "15", label: "15分" },
  { value: "60", label: "1时" },
  { value: "240", label: "4时" },
  { value: "D", label: "日线" },
];

interface Props {
  symbol?: string;
  height?: number;
}

export default function TradingViewChart({ symbol = "GOLD", height = 420 }: Props) {
  const [interval, setInterval_] = useState("60");
  const tvSymbol = SYMBOL_MAP[symbol] || "OANDA:XAUUSD";

  return (
    <div className="w-full rounded-md overflow-hidden border border-slate-200">
      <div className="flex items-center justify-between px-3 py-2 bg-slate-50 border-b border-slate-200">
        <span className="text-xs font-medium text-slate-600">{symbol} · {tvSymbol}</span>
        <div className="flex gap-1">
          {INTERVALS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setInterval_(value)}
              className={`px-2 py-0.5 text-[11px] rounded ${
                interval === value
                  ? "bg-blue-600 text-white"
                  : "bg-white text-slate-500 hover:bg-slate-100 border border-slate-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <iframe
        src={`https://s.tradingview.com/widgetembed/?frameElementId=tradingview_chart&symbol=${encodeURIComponent(tvSymbol)}&interval=${interval}&hidesidetoolbar=1&hidelegend=0&saveimage=0&studies=[]&theme=light&style=1&timezone=Asia/Shanghai&locale=zh_CN&toolbarbg=f1f3f6&studies_overrides={}&overrides={}&enabled_features=[]&disabled_features=[]&showpopupbutton=0&utm_source=localhost&utm_medium=widget&utm_campaign=chart`}
        width="100%"
        height={height}
        style={{ border: "none" }}
        title="TradingView Chart"
        loading="eager"
      />
    </div>
  );
}