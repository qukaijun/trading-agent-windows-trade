interface Props {
  symbol?: string;
  height?: number;
}

const TRADING_VIEW_SYMBOLS: Record<string, string> = {
  GOLD: "OANDA:XAUUSD",
  XAUUSD: "OANDA:XAUUSD",
  XAGUSD: "OANDA:XAGUSD",
  "BTC-USD": "COINBASE:BTCUSD",
  BTCUSD: "COINBASE:BTCUSD",
  "ETH-USD": "COINBASE:ETHUSD",
  ETHUSD: "COINBASE:ETHUSD",
};

function tradingViewUrl(symbol: string) {
  const tvSymbol = TRADING_VIEW_SYMBOLS[symbol] || symbol;
  const params = new URLSearchParams({
    symbol: tvSymbol,
    interval: "60",
    hidesidetoolbar: "1",
    symboledit: "1",
    saveimage: "0",
    toolbarbg: "F7F7F4",
    studies: "[]",
    theme: "light",
    style: "1",
    timezone: "Asia/Shanghai",
    locale: "zh_CN",
    withdateranges: "1",
  });
  return `https://s.tradingview.com/widgetembed/?${params.toString()}`;
}

export default function KlineChart({ symbol = "GOLD", height = 420 }: Props) {
  return (
    <div className="w-full overflow-hidden rounded-md border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-600">
        <span>{symbol} · TradingView K线图</span>
        <span className="text-slate-400">外部图表组件</span>
      </div>
      <iframe
        title={`${symbol} TradingView chart`}
        src={tradingViewUrl(symbol)}
        className="block w-full border-0"
        style={{ height }}
        loading="lazy"
        referrerPolicy="origin"
      />
    </div>
  );
}
