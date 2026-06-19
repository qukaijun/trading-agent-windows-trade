import { useEffect, useRef } from "react";

interface Props { symbol?: string; height?: number; }

function genData(symbol: string) {
  const candles: { o: number; h: number; l: number; c: number }[] = [];
  let price = symbol === "BTC-USD" ? 64000 : symbol === "ETH-USD" ? 3400 : symbol === "XAGUSD" ? 30 : 4270;
  for (let i = 0; i < 100; i++) {
    const open = price;
    const close = open + (Math.random() - 0.45) * 80;
    const high = Math.max(open, close) + Math.random() * 30;
    const low = Math.min(open, close) - Math.random() * 30;
    candles.push({ o: open, h: high, l: low, c: close });
    price = close;
  }
  return candles;
}

export default function CanvasKline({ symbol = "GOLD", height = 420 }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const w = canvas.parentElement!.clientWidth;
    const h = height;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";
    ctx.scale(dpr, dpr);

    const candles = genData(symbol);

    // Calculate ranges
    let maxH = -Infinity, minL = Infinity;
    candles.forEach(c => { if (c.h > maxH) maxH = c.h; if (c.l < minL) minL = c.l; });
    const range = maxH - minL;
    const pad = range * 0.05;
    maxH += pad; minL -= pad;
    const chartH = h - 60;
    const candleW = Math.max(4, (w - 40) / candles.length * 0.6);
    const gap = (w - 40) / candles.length;
    const toY = (val: number) => chartH - ((val - minL) / (maxH - minL + 0.001)) * chartH + 10;

    // Background
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, w, h);

    // Grid
    ctx.strokeStyle = "#f1f5f9";
    ctx.lineWidth = 1;
    for (let i = 0; i < 5; i++) {
      const y = 10 + (chartH / 5) * i;
      ctx.beginPath(); ctx.moveTo(20, y); ctx.lineTo(w - 20, y); ctx.stroke();
    }

    // Candles
    candles.forEach((c, i) => {
      const x = 20 + i * gap + gap / 2;
      const isGreen = c.c >= c.o;
      ctx.strokeStyle = isGreen ? "#16a34a" : "#dc2626";
      ctx.fillStyle = isGreen ? "#16a34a" : "#dc2626";
      ctx.lineWidth = 1;

      // Wick
      ctx.beginPath();
      ctx.moveTo(x, toY(c.l));
      ctx.lineTo(x, toY(c.h));
      ctx.stroke();

      // Body
      const bodyH = Math.max(1, Math.abs(toY(c.o) - toY(c.c)));
      const bodyY = Math.min(toY(c.o), toY(c.c));
      if (isGreen)
        ctx.fillRect(x - candleW / 2, bodyY, candleW, bodyH);
      else {
        ctx.fillStyle = "#dc2626";
        ctx.fillRect(x - candleW / 2, bodyY, candleW, bodyH);
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(x - candleW / 2 + 1, bodyY + 1, candleW - 2, bodyH - 2);
      }
    });

    // Price labels
    ctx.fillStyle = "#94a3b8";
    ctx.font = "10px sans-serif";
    for (let i = 0; i < 5; i++) {
      const val = maxH - (range / 4) * i;
      const y = 10 + (chartH / 5) * i;
      ctx.fillText(val >= 1000 ? val.toFixed(0) : val.toFixed(2), 1, y + 3);
    }

    // Symbol label
    ctx.fillStyle = "#1e293b";
    ctx.font = "bold 12px sans-serif";
    ctx.fillText(symbol + " (模拟)", 22, h - 12);

    // Handle resize
    const onResize = () => {
      const pw = canvas.parentElement!.clientWidth;
      canvas.style.width = pw + "px";
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [symbol, height]);

  return (
    <div className="w-full rounded-md overflow-hidden border border-slate-200 bg-white">
      <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 text-xs font-medium text-slate-600">
        {symbol} · K线图
      </div>
      <canvas ref={ref} style={{ width: "100%", height }} />
    </div>
  );
}