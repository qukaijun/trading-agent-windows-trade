import { useEffect, useRef } from "react";
import { createChart, ColorType, CandlestickSeries, HistogramSeries, type UTCTimestamp } from "lightweight-charts";

interface Props { symbol?: string; height?: number; }

function genData(symbol: string) {
  const data: { time: number; open: number; high: number; low: number; close: number }[] = [];
  const volumes: { time: number; value: number; color: string }[] = [];
  let price = symbol === "BTC-USD" ? 64000 : symbol === "ETH-USD" ? 3400 : symbol === "XAGUSD" ? 30 : 4270;
  const now = Math.floor(Date.now() / 1000);
  for (let i = 99; i >= 0; i--) {
    const t = now - i * 3600;
    const open = price + (Math.random() - 0.5) * 40;
    const close = open + (Math.random() - 0.5) * 50;
    const high = Math.max(open, close) + Math.random() * 20;
    const low = Math.min(open, close) - Math.random() * 20;
    data.push({ time: t as UTCTimestamp, open, high, low, close });
    volumes.push({ time: t as UTCTimestamp, value: Math.random() * 10000, color: close >= open ? "rgba(22,163,74,0.4)" : "rgba(220,38,38,0.4)" });
    price = close;
  }
  return { data, volumes };
}

export default function KlineChart({ symbol = "GOLD", height = 420 }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const { data, volumes } = genData(symbol);
    const chart = createChart(ref.current, {
      height,
      layout: { background: { type: ColorType.Solid, color: "#ffffff" }, textColor: "#64748b" },
      grid: { vertLines: { color: "#f1f5f9" }, horzLines: { color: "#f1f5f9" } },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: "#e2e8f0" },
      timeScale: { borderColor: "#e2e8f0", timeVisible: true },
    });

    const candle = chart.addSeries(CandlestickSeries, {
      upColor: "#16a34a", downColor: "#dc2626",
      borderUpColor: "#16a34a", borderDownColor: "#dc2626",
      wickUpColor: "#16a34a", wickDownColor: "#dc2626",
    });
    candle.setData(data as any);

    const vol = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" }, priceScaleId: "",
    });
    vol.setData(volumes as any);
    chart.priceScale("").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    chart.timeScale().fitContent();

    const handleResize = () => { chart.applyOptions({ width: ref.current!.clientWidth }); };
    window.addEventListener("resize", handleResize);
    return () => { window.removeEventListener("resize", handleResize); chart.remove(); };
  }, [symbol, height]);

  return (
    <div className="w-full rounded-md overflow-hidden border border-slate-200 bg-white">
      <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 text-xs font-medium text-slate-600">
        {symbol} · K线图 (模拟数据)
      </div>
      <div ref={ref} />
    </div>
  );
}