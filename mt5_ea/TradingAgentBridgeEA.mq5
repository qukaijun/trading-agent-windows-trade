//+------------------------------------------------------------------+
//| TradingAgentBridgeEA.mq5                                         |
//| MT5 bridge for Trading Agent Assistant.                          |
//+------------------------------------------------------------------+
#property strict
#property version   "0.1"
#property description "Reads local Trading Agent signals. Demo/live execution must be explicitly enabled."

#include <Trade/Trade.mqh>

input string SignalUrl = "http://127.0.0.1:8787/api/mt5/signal.txt";
input int PollSeconds = 5;
input bool EnableDemoAutoTrade = false;
input bool EnableLiveAutoTrade = false;
input bool ShowPopupAlert = true;
input bool UseChartSymbol = true;
input double MaxVolume = 0.10;
input double MaxLiveVolume = 0.01;
input int MaxSlippagePoints = 30;
input long MagicNumber = 8787001;

CTrade trade;
string lastSignalId = "";

struct TASignal
{
   string id;
   string symbol;
   string action;
   double volume;
   double sl;
   double tp;
   bool auto_allowed;
   bool demo_only;
   string trade_mode;
   string expires_at;
   string comment;
};

int OnInit()
{
   EventSetTimer(MathMax(PollSeconds, 1));
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(MaxSlippagePoints);
   Comment("Trading Agent Bridge EA\nWaiting for signal...\nDemo auto trade: ", EnableDemoAutoTrade ? "ON" : "OFF",
           "\nLive auto trade: ", EnableLiveAutoTrade ? "ON" : "OFF");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   Comment("");
}

void OnTimer()
{
   string body = FetchSignal();
   if(body == "")
      return;

   TASignal signal;
   if(!ParseSignal(body, signal))
   {
      Print("TradingAgentBridgeEA: invalid signal body: ", body);
      return;
   }

   RenderSignal(signal);

   if(signal.id == lastSignalId)
      return;

   lastSignalId = signal.id;
   if(signal.action == "WAIT")
      return;

   string message = StringFormat(
      "Trading Agent signal: %s %s volume %.2f SL %.5f TP %.5f\n%s",
      signal.action,
      ResolveSymbol(signal.symbol),
      signal.volume,
      signal.sl,
      signal.tp,
      signal.comment
   );
   Print(message);
   if(ShowPopupAlert)
      Alert(message);

   ExecuteSignalIfAllowed(signal);
}

string FetchSignal()
{
   char data[];
   char result[];
   string headers = "";
   string result_headers = "";
   int timeout = 3000;
   ResetLastError();
   int status = WebRequest("GET", SignalUrl, headers, timeout, data, result, result_headers);
   if(status == -1)
   {
      int err = GetLastError();
      Print("TradingAgentBridgeEA: WebRequest failed. Error=", err,
            ". Add http://127.0.0.1:8787 to Tools > Options > Expert Advisors > Allow WebRequest.");
      return "";
   }
   if(status != 200)
   {
      Print("TradingAgentBridgeEA: unexpected HTTP status: ", status);
      return "";
   }
   return CharArrayToString(result, 0, -1, CP_UTF8);
}

bool ParseSignal(string body, TASignal &signal)
{
   signal.id = GetField(body, "id", "");
   signal.symbol = GetField(body, "symbol", "CHART");
   signal.action = StringUpperSafe(GetField(body, "action", "WAIT"));
   signal.volume = StringToDouble(GetField(body, "volume", "0"));
   signal.sl = StringToDouble(GetField(body, "sl", "0"));
   signal.tp = StringToDouble(GetField(body, "tp", "0"));
   signal.auto_allowed = (GetField(body, "auto", "0") == "1");
   signal.demo_only = (GetField(body, "demo_only", "1") == "1");
   signal.trade_mode = StringUpperSafe(GetField(body, "trade_mode", signal.demo_only ? "DEMO" : "LIVE"));
   signal.expires_at = GetField(body, "expires_at", "");
   signal.comment = GetField(body, "comment", "");

   if(signal.id == "")
      return false;
   if(signal.action != "BUY" && signal.action != "SELL" && signal.action != "WAIT")
      signal.action = "WAIT";
   return true;
}

string GetField(string body, string key, string fallback)
{
   string parts[];
   int count = StringSplit(body, ';', parts);
   string prefix = key + "=";
   for(int i = 0; i < count; i++)
   {
      string item = parts[i];
      if(StringFind(item, prefix) == 0)
         return StringSubstr(item, StringLen(prefix));
   }
   return fallback;
}

string StringUpperSafe(string value)
{
   string copy = value;
   StringToUpper(copy);
   return copy;
}

string ResolveSymbol(string requested)
{
   if(UseChartSymbol || requested == "" || requested == "CHART")
      return _Symbol;
   return requested;
}

void ExecuteSignalIfAllowed(TASignal &signal)
{
   if(!signal.auto_allowed)
   {
      Print("TradingAgentBridgeEA: signal auto flag is off.");
      return;
   }

   long account_mode = AccountInfoInteger(ACCOUNT_TRADE_MODE);
   if(signal.trade_mode == "LIVE")
      ExecuteLiveSignal(signal, account_mode);
   else
      ExecuteDemoSignal(signal, account_mode);
}

void ExecuteDemoSignal(TASignal &signal, long account_mode)
{
   if(!EnableDemoAutoTrade)
      return;
   if(account_mode != ACCOUNT_TRADE_MODE_DEMO)
   {
      Print("TradingAgentBridgeEA: blocked. Account is not demo.");
      Alert("Trading Agent EA blocked: account is not demo.");
      return;
   }
   if(signal.volume <= 0 || signal.volume > MaxVolume)
   {
      Print("TradingAgentBridgeEA: blocked by volume limit. volume=", signal.volume, " max=", MaxVolume);
      return;
   }

   SendMarketOrder(signal, "demo");
}

void ExecuteLiveSignal(TASignal &signal, long account_mode)
{
   if(!EnableLiveAutoTrade)
   {
      Print("TradingAgentBridgeEA: live signal received but EnableLiveAutoTrade is OFF.");
      Alert("Trading Agent LIVE signal blocked: live auto trade is OFF.");
      return;
   }
   if(account_mode != ACCOUNT_TRADE_MODE_REAL)
   {
      Print("TradingAgentBridgeEA: live signal blocked. Account is not real.");
      Alert("Trading Agent LIVE signal blocked: account is not real.");
      return;
   }
   if(signal.volume <= 0 || signal.volume > MaxLiveVolume)
   {
      Print("TradingAgentBridgeEA: live signal blocked by volume limit. volume=", signal.volume, " max=", MaxLiveVolume);
      Alert("Trading Agent LIVE signal blocked by volume limit.");
      return;
   }

   SendMarketOrder(signal, "live");
}

void SendMarketOrder(TASignal &signal, string mode)
{
   if(signal.action != "BUY" && signal.action != "SELL")
      return;

   string symbol = ResolveSymbol(signal.symbol);
   if(!SymbolSelect(symbol, true))
   {
      Print("TradingAgentBridgeEA: cannot select symbol ", symbol);
      return;
   }

   bool ok = false;
   string comment = "TradingAgent " + mode + " " + signal.id;
   if(signal.action == "BUY")
      ok = trade.Buy(signal.volume, symbol, 0.0, signal.sl, signal.tp, comment);
   else if(signal.action == "SELL")
      ok = trade.Sell(signal.volume, symbol, 0.0, signal.sl, signal.tp, comment);

   if(!ok)
      Print("TradingAgentBridgeEA: trade failed. retcode=", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription());
   else
      Print("TradingAgentBridgeEA: ", mode, " trade sent. order=", trade.ResultOrder());
}

void RenderSignal(TASignal &signal)
{
   string text = "Trading Agent Bridge EA\n";
   text += "Signal: " + signal.id + "\n";
   text += "Action: " + signal.action + "\n";
   text += "Symbol: " + ResolveSymbol(signal.symbol) + "\n";
   text += "Volume: " + DoubleToString(signal.volume, 2) + "\n";
   text += "SL: " + DoubleToString(signal.sl, _Digits) + "\n";
   text += "TP: " + DoubleToString(signal.tp, _Digits) + "\n";
   text += "Signal trade mode: " + signal.trade_mode + "\n";
   text += "EA demo auto trade: " + (EnableDemoAutoTrade ? "ON" : "OFF") + "\n";
   text += "EA live auto trade: " + (EnableLiveAutoTrade ? "ON" : "OFF") + "\n";
   text += "Signal auto allowed: " + (signal.auto_allowed ? "YES" : "NO") + "\n";
   text += "Comment: " + signal.comment;
   Comment(text);
}
