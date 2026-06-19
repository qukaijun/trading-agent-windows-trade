//+------------------------------------------------------------------+
//| TradingAgentFileBridgeEA.mq5                                     |
//| Reads signals from local file - no HTTP needed                   |
//+------------------------------------------------------------------+
#property strict
#property version "0.2"
#property description "Reads TA signals from MQL5/Files/ta_signal.txt"

#include <Trade/Trade.mqh>

input int PollSeconds = 3;
input bool EnableDemoAutoTrade = true;
input bool EnableLiveAutoTrade = false;
input double MaxVolume = 0.10;
input double MaxLiveVolume = 0.01;
input int MaxSlippagePoints = 30;
input long MagicNumber = 8787002;

CTrade trade;
string lastSignalId = "";

int OnInit()
{
   EventSetTimer(MathMax(PollSeconds, 1));
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(MaxSlippagePoints);
   Comment("TA File Bridge\nDemo: ", EnableDemoAutoTrade ? "ON" : "OFF",
           "\nLive: ", EnableLiveAutoTrade ? "ON" : "OFF",
           "\nWaiting...");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { EventKillTimer(); Comment(""); }

void OnTimer()
{
   string body = ReadSignalFile();
   if(body == "") { Comment("TA File Bridge\nNo signal"); return; }

   string id = GetValue(body, "id");
   if(id == lastSignalId) return;

   string action = GetValue(body, "action");
   if(action == "WAIT" || action == "") return;

   string symbol = GetValue(body, "symbol");
   double volume = StringToDouble(GetValue(body, "volume"));
   double sl = StringToDouble(GetValue(body, "sl"));
   double tp = StringToDouble(GetValue(body, "tp"));
   string comment = GetValue(body, "comment");
   string demo = GetValue(body, "demo");
   string mode = GetValue(body, "mode");
   string auto = GetValue(body, "auto");

   string display = StringFormat("TA Signal: %s %s V=%.2f SL=%.5f TP=%.5f [%s]",
                                  action, symbol, volume, sl, tp, 
                                  demo == "1" ? "DEMO" : "LIVE");
   Comment(display);
   Print(display);

   lastSignalId = id;

   if(auto != "1") { Print("TA: auto=0, skip"); return; }

   if(demo == "1") {
      if(!EnableDemoAutoTrade) { Print("TA: demo trade disabled"); return; }
      if(volume <= 0 || volume > MaxVolume) { Print("TA: volume out of range"); return; }
      SendOrder(symbol, action, volume, sl, tp, comment);
   } else {
      if(!EnableLiveAutoTrade) { Print("TA: live trade disabled"); return; }
      if(volume <= 0 || volume > MaxLiveVolume) { Print("TA: live volume out of range"); return; }
      SendOrder(symbol, action, volume, sl, tp, comment);
   }
}

string ReadSignalFile()
{
   int handle = FileOpen("ta_signal.txt", FILE_TXT|FILE_READ|FILE_SHARE_READ);
   if(handle == INVALID_HANDLE) return "";
   string content = FileReadString(handle, 4096);
   FileClose(handle);
   return content;
}

string GetValue(string data, string key)
{
   string prefix = key + "=";
   int start = StringFind(data, "\n" + prefix);
   if(start < 0) {
      start = StringFind(data, prefix);
      if(start != 0) return "";
      start = 0;
   } else {
      start++;
   }
   start += StringLen(prefix);
   int end = StringFind(data, "\n", start);
   if(end < 0) end = StringLen(data);
   return StringSubstr(data, start, end - start);
}

void SendOrder(string symbol, string action, double volume, double sl, double tp, string comment)
{
   if(!SymbolSelect(symbol, true)) {
      Print("TA: cannot select ", symbol);
      return;
   }
   bool ok = false;
   string cmt = "TA " + comment;
   if(action == "BUY")
      ok = trade.Buy(volume, symbol, 0.0, sl, tp, cmt);
   else if(action == "SELL")
      ok = trade.Sell(volume, symbol, 0.0, sl, tp, cmt);
   if(!ok)
      Print("TA: trade failed. retcode=", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription());
   else
      Print("TA: trade sent. order=", trade.ResultOrder());
}
