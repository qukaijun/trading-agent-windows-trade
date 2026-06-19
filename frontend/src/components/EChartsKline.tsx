import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface Props {
  symbol?: string;
  height?: number;
}

// Generate mock OHLC data (same as before but formatted for ECharts)
function genMockData(symbol: string) {
  const now = new Date();
  const data: number[][] = [];
  const volumes: number[][] = [];
  let price = symbol === "BTC-USD" ? 64000 : symbol === "ETH-USD" ? 3400 : symbol === "XAGUSD" ? 30 : 4270;

  for (let i = 99; i >= 0; i--) {
    void new Date(now.getTime() - i * 3600 * 1000);

    const open = price + (Math.random() - 0.5) * 40;
    const close = open + (Math.random() - 0.5) * 50;
    const high = Math.max(open, close) + Math.random() * 20;
    const low = Math.min(open, close) - Math.random() * 20;
    data.push([close, open, low, high]); // ECharts: [close, open, lowest, highest]
    volumes.push([i, Math.random() * 10000, close >= open ? 1 : -1]);
    price = close;
  }
  return { data: data.reverse(), volumes: volumes.reverse() };
}

export default function EChartsKline({ symbol = "GOLD", height = 420 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    if (!chartRef.current) {
      chartRef.current = echarts.init(containerRef.current);
    }

    const { data, volumes } = genMockData(symbol);
    const dates = data.map((_, i) => {
      const d = new Date(Date.now() - (99 - i) * 3600 * 1000);
      return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:00`;
    });

    chartRef.current.setOption({
      tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
      grid: { left: "8%", right: "2%", top: 16, bottom: "18%" },
      xAxis: { type: "category", data: dates, boundaryGap: false, axisLine: { lineStyle: { color: "#8392A5" } } },
      yAxis: { scale: true, splitLine: { lineStyle: { color: "#f1f5f9" } } },
      series: [
        {
          name: symbol,
          type: "candlestick",
          data: data,
          itemStyle: { color: "#16a34a", color0: "#dc2626", borderColor: "#16a34a", borderColor0: "#dc2626" },
        },
        {
          name: "Volume",
          type: "bar",
          data: volumes,
          yAxisIndex: 1,
          itemStyle: {
            color: (params: unknown) => {
              const item = params as { data: number[] };
              return item.data[2] > 0 ? "rgba(22,163,74,0.3)" : "rgba(220,38,38,0.3)";
            },
          },
        },
      ],
      dataZoom: [{ type: "inside" }, { type: "slider", height: 20, bottom: 4 }],
    }, true);

    const handleResize = () => chartRef.current?.resize();
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, [symbol, height]);

  useEffect(() => {
    return () => { chartRef.current?.dispose(); chartRef.current = null; };
  }, []);

  return (
    <div className="w-full rounded-md overflow-hidden border border-slate-200 bg-white">
      <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 text-xs font-medium text-slate-600">
        {symbol} · K线图 (模拟数据)
      </div>
      <div ref={containerRef} style={{ width: "100%", height }} />
    </div>
  );
}