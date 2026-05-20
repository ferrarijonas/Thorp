//+------------------------------------------------------------------+
//|                                            H140_Markov_Puro.mq5  |
//|                                            Thorp v2.0             |
//|                         Walk-forward validated  2026-05-19        |
//+------------------------------------------------------------------+
#property copyright "Thorp"
#property version   "2.00"
#property description "Markov Puro - 6 regras mean-reversion 9:00->9:01"
#property description "COMPRA: ontem 9:01 verde+range>P75 | wick_asym<P50+shadow_up<P75 | shadow_up>0.39+fractal>1.51"
#property description "VENDA: range>P50+pos_close>0.75 | acertou=0+shadow_up<P50 | shadow_up<P75+shadow_dn>0.25+range>182"

input double InpLotSize = 1.0;          // Volume (contratos)
input double InpSL = 275.0;             // Stop Loss (pontos)
input double InpTP = 180.0;             // Take Profit (pontos)
input int    InpMagic = 140001;         // Magic number

// Fixed thresholds from historical data (containers.py)
double P50 = 180.0;
double P75 = 275.0;
double SHADOW_P50 = 0.25;
double SHADOW_P75 = 0.50;

// Global state
datetime g_last_bar = 0;
ulong    g_ticket = 0;
int      g_dia_atual = 0;
int      g_ontem_9dir = -1;
int      g_ontem_01dir = -1;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit() {
   Print("=== H140 Markov Puro v2.0 ===");
   Print("Simbolo: ", _Symbol, " | Lote: ", InpLotSize);
   Print("SL: ", InpSL, " pts | TP: ", InpTP, " pts");

   g_ontem_9dir = (int)GlobalVariableGet("H140_ontem_9dir");
   g_ontem_01dir = (int)GlobalVariableGet("H140_ontem_01dir");
   if (g_ontem_9dir < 0 || g_ontem_9dir > 1) g_ontem_9dir = -1;
   if (g_ontem_01dir < 0 || g_ontem_01dir > 1) g_ontem_01dir = -1;
   Print("Contexto carregado: ontem_9dir=", g_ontem_9dir,
         " ontem_01dir=", g_ontem_01dir);

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
   GlobalVariableSet("H140_ontem_9dir", g_ontem_9dir);
   GlobalVariableSet("H140_ontem_01dir", g_ontem_01dir);
   Print("H140 finalizado. Contexto salvo. Razao: ", reason);
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

   // Verifica mudanca de dia
   int dia = dtm.day;
   if (g_dia_atual != 0 && dia != g_dia_atual) {
      Print("Novo dia: ", dtm.year, "-", dtm.mon, "-", dia);
   }
   g_dia_atual = dia;

   // =======================================================
   // 9:01 — avalia 9:00 e emite sinal
   // =======================================================
   if (h == 9 && m == 1) {
      // Le o bar 9:00 (indice 1 = bar anterior)
      MqlRates r9[1];
      if (!getBar(1, r9)) { Print("Erro: nao foi possivel ler 9:00"); return; }

      // Confere se e realmente 9:00
      MqlDateTime t9;
      TimeToStruct(r9[0].time, t9);
      if (t9.hour != 9 || t9.min != 0) { Print("Bar anterior nao e 9:00"); return; }

      double O = r9[0].open;
      double H = r9[0].high;
      double L = r9[0].low;
      double C = r9[0].close;
      double R = H - L;
      if (R <= 0) { g_ontem_9dir = (C > O) ? 1 : 0; return; }

      // Features
      double body_abs = fabs(C - O);
      double body_ratio = body_abs / R;
      double shadow_up = (H - fmax(O, C)) / R;
      double shadow_dn = (fmin(O, C) - L) / R;
      double pos_close = (C - L) / R;
      double fractal = R / (body_abs + 1);
      double wick_asym = shadow_up / (shadow_dn + 0.001);

      bool acertou = (g_ontem_9dir >= 0 && g_ontem_01dir >= 0) ?
                     (g_ontem_9dir == g_ontem_01dir) : false;
      bool ontem_01verde = (g_ontem_01dir == 1);
      bool ontem_9vermelho = (g_ontem_9dir == 0);

      // Debug
      Print("9:00 R=", R, " body=", C-O, " body_ratio=", StringFormat("%.3f", body_ratio),
            " shadow_up=", StringFormat("%.3f", shadow_up),
            " shadow_dn=", StringFormat("%.3f", shadow_dn));
      Print("       pos_close=", StringFormat("%.3f", pos_close),
            " fractal=", StringFormat("%.2f", fractal),
            " wick_asym=", StringFormat("%.3f", wick_asym));
      Print("       ctx: ontem_9dir=", g_ontem_9dir,
            " ontem_01dir=", g_ontem_01dir,
            " acertou=", acertou);

      // === Regras ===
      int compra = 0, venda = 0;

      if (ontem_01verde && R > P75) compra++;
      if (wick_asym <= SHADOW_P50 && shadow_up <= SHADOW_P75) compra++;
      if (shadow_up > 0.39 && fractal > 1.51 && ontem_9vermelho) compra += 2;

      if (R > P50 && pos_close > 0.75) venda++;
      if (!acertou && shadow_up <= SHADOW_P50) venda++;
      if (shadow_up <= SHADOW_P75 && shadow_dn > 0.25 && R > 182) venda++;

      // === Decisao ===
      int signal = 0;
      if (compra > venda && compra >= 1) signal = 1;
      else if (venda > compra && venda >= 1) signal = -1;

      if (signal != 0) {
         string lbl = (signal == 1) ? "COMPRA" : "VENDA";
         Print(">>> SINAL ", lbl, " (compra=", compra, " venda=", venda, ")");

         // So abre se nao tem posicao
         if (PositionSelect(_Symbol)) {
            Print("Posicao ja existe em ", _Symbol, ". Pulando.");
         } else {
            MqlTradeRequest req = {};
            MqlTradeResult res = {};
            req.action = TRADE_ACTION_DEAL;
            req.symbol = _Symbol;
            req.volume = InpLotSize;
            req.type = (signal == 1) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
            req.price = (signal == 1) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                                       : SymbolInfoDouble(_Symbol, SYMBOL_BID);
            req.deviation = 10;
            req.magic = InpMagic;

            double entry = req.price;
            if (signal == 1) {
               req.sl = NormalizeDouble(entry - InpSL, _Digits);
               req.tp = NormalizeDouble(entry + InpTP, _Digits);
            } else {
               req.sl = NormalizeDouble(entry + InpSL, _Digits);
               req.tp = NormalizeDouble(entry - InpTP, _Digits);
            }

            if (OrderSend(req, res)) {
               g_ticket = res.order;
               Print("Ordem OK: ticket=", res.order, " entry=", entry,
                     " sl=", req.sl, " tp=", req.tp);
            } else {
               Print("Ordem FALHOU: retcode=", res.retcode,
                     " ", res.comment);
            }
         }
      } else {
         Print("Sem sinal. compra=", compra, " venda=", venda);
      }

      // Atualiza contexto para amanha
      g_ontem_9dir = (C > O) ? 1 : 0;
      GlobalVariableSet("H140_ontem_9dir", g_ontem_9dir);
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
            GlobalVariableSet("H140_ontem_01dir", g_ontem_01dir);
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
