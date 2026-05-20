//+------------------------------------------------------------------+
//|                                            H141_Continuacao.mq5  |
//|                                            Thorp v2.0             |
//|                    Continuacao 9:00 — padrao H140 (simples)      |
//+------------------------------------------------------------------+
#property copyright "Thorp"
#property version   "2.00"
#property description "Continuacao de 9:00 — VENDA quando"
#property description "shadow_up<=P50 e body_ratio<=P75 na abertura"
#property description "Entrada MARKET as 9:01 | SL/TP fixos"

input double InpLotSize = 1.0;          // Volume (contratos)
input int    InpMagic = 141001;         // Magic number
input double InpSL = 120.0;             // Stop Loss (pontos)
input double InpTP = 80.0;              // Take Profit (pontos)
input double InpShadowP50 = 0.27;       // shadow_up P50
input double InpBodyP75 = 0.76;         // body_ratio P75

// Contexto
datetime g_last_bar = 0;
ulong    g_ticket = 0;
int      g_dia_atual = 0;
int      g_ontem_9dir = -1;
int      g_ontem_01dir = -1;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit() {
   Print("=== H141 Continuacao v2.0 ===");
   Print("Simbolo: ", _Symbol, " | Lote: ", InpLotSize);
   Print("SL: ", InpSL, " pts | TP: ", InpTP, " pts");
   Print("shadow_up <= ", InpShadowP50, " | body_ratio <= ", InpBodyP75);

   g_ontem_9dir = (int)GlobalVariableGet("H141_ontem_9dir");
   g_ontem_01dir = (int)GlobalVariableGet("H141_ontem_01dir");
   if (g_ontem_9dir < 0 || g_ontem_9dir > 1) g_ontem_9dir = -1;
   if (g_ontem_01dir < 0 || g_ontem_01dir > 1) g_ontem_01dir = -1;
   Print("Contexto: ontem_9dir=", g_ontem_9dir,
         " ontem_01dir=", g_ontem_01dir);

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
   GlobalVariableSet("H141_ontem_9dir", g_ontem_9dir);
   GlobalVariableSet("H141_ontem_01dir", g_ontem_01dir);
   Print("H141 finalizado. Contexto salvo. Razao: ", reason);
}

//+------------------------------------------------------------------+
//| Check new bar                                                    |
//+------------------------------------------------------------------+
bool isNewBar() {
   datetime bar_time = iTime(_Symbol, PERIOD_M1, 0);
   if (bar_time == g_last_bar) return false;
   g_last_bar = bar_time;
   return true;
}

//+------------------------------------------------------------------+
//| Get bar by index (0=current, 1=previous...)                      |
//+------------------------------------------------------------------+
bool getBar(int idx, MqlRates &r[]) {
   return CopyRates(_Symbol, PERIOD_M1, idx, 1, r) > 0;
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick() {
   if (!isNewBar()) return;

   MqlDateTime dtm;
   TimeToStruct(g_last_bar, dtm);
   int h = dtm.hour, m = dtm.min;

   // Reset diario as 8:59
   if (h == 8 && m == 59) {
      g_dia_atual = 0;
   }

   int dia = dtm.day;
   if (g_dia_atual != 0 && dia != g_dia_atual) {
      Print("Novo dia: ", dtm.year, "-", dtm.mon, "-", dia);
   }
   g_dia_atual = dia;

   // =======================================================
   // 9:01 — avalia 9:00 e emite sinal
   // =======================================================
   if (h == 9 && m == 1) {
      MqlRates r9[1];
      if (!getBar(1, r9)) { Print("Erro: nao foi possivel ler 9:00"); return; }

      MqlDateTime t9;
      TimeToStruct(r9[0].time, t9);
      if (t9.hour != 9 || t9.min != 0) { Print("Bar anterior nao e 9:00"); return; }

      double O = r9[0].open;
      double H = r9[0].high;
      double L = r9[0].low;
      double C = r9[0].close;
      double R = H - L;
      if (R <= 0) { g_ontem_9dir = (C > O) ? 1 : 0; return; }

      double body_ratio = fabs(C - O) / R;
      double shadow_up  = (H - fmax(O, C)) / R;

      Print("9:00 R=", R, " shadow_up=", StringFormat("%.3f", shadow_up),
            " body_ratio=", StringFormat("%.3f", body_ratio));

      // Sinal VENDA
      if (shadow_up <= InpShadowP50 && body_ratio <= InpBodyP75) {
         Print(">>> SINAL VENDA");

         if (PositionSelect(_Symbol)) {
            Print("Posicao ja existe em ", _Symbol, ". Pulando.");
         } else {
            MqlTradeRequest req = {};
            MqlTradeResult res = {};
            req.action = TRADE_ACTION_DEAL;
            req.symbol = _Symbol;
            req.volume = InpLotSize;
            req.type = ORDER_TYPE_SELL;
            req.price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
            req.deviation = 10;
            req.magic = InpMagic;
            req.sl = NormalizeDouble(req.price + InpSL, _Digits);
            req.tp = NormalizeDouble(req.price - InpTP, _Digits);

            if (OrderSend(req, res)) {
               g_ticket = res.order;
               Print("Ordem OK: ticket=", res.order, " entry=", req.price,
                     " sl=", req.sl, " tp=", req.tp);
            } else {
               Print("Ordem FALHOU: retcode=", res.retcode,
                     " ", res.comment);
            }
         }
      } else {
         Print("Sem sinal. shadow_up=", StringFormat("%.3f", shadow_up),
               " (>", InpShadowP50, ") ou body_ratio=", StringFormat("%.3f", body_ratio),
               " (>", InpBodyP75, ")");
      }

      g_ontem_9dir = (C > O) ? 1 : 0;
      GlobalVariableSet("H141_ontem_9dir", g_ontem_9dir);
   }

   // =======================================================
   // 9:02 — guarda direcao do 9:01
   // =======================================================
   if (h == 9 && m == 2) {
      MqlRates r01[1];
      if (getBar(1, r01)) {
         MqlDateTime t01;
         TimeToStruct(r01[0].time, t01);
         if (t01.hour == 9 && t01.min == 1) {
            g_ontem_01dir = (r01[0].close > r01[0].open) ? 1 : 0;
            GlobalVariableSet("H141_ontem_01dir", g_ontem_01dir);
            Print("9:01 ", (g_ontem_01dir == 1) ? "VERDE" : "VERMELHO",
                  " (salvo)");
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Monitora fechamentos                                             |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest& request,
                        const MqlTradeResult& result) {
   if (trans.type == TRADE_TRANSACTION_DEAL_ADD) {
      HistorySelect(0, TimeCurrent());
      int total = HistoryDealsTotal();
      if (total > 0) {
         ulong ticket = HistoryDealGetTicket(total - 1);
         if (ticket > 0) {
            double profit = HistoryDealGetDouble(ticket, DEAL_PROFIT);
            if (profit != 0) {
               string symbol = HistoryDealGetString(ticket, DEAL_SYMBOL);
               if (symbol == _Symbol) {
                  Print(">>> FECHADO ticket=", ticket,
                        " profit=", profit);
               }
            }
         }
      }
   }
}
//+------------------------------------------------------------------+
