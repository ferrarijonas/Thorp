# Checklist: Python → MQL5 EA

Checklist obrigatório para traduzir uma estratégia Python (Thorp) para Expert Advisor MT5.

---

## 1. Sinal — processar na barra CERTA

- [ ] Usar `getBar(1)` para a barra **completa** anterior
- [ ] NUNCA usar `getBar(0)` (barra atual, incompleta)
- [ ] Confirmar com `MqlDateTime` que é a barra esperada (hora/minuto)
- [ ] Se `R <= 0`, pular (candle sem range)

**Regra de ouro:** o sinal é processado na barra SEGUINTE à barra de análise.
Ex: H141 analisa a barra 9:00 → sinal é processado em 9:01 com `getBar(1)`.

---

## 2. Thresholds — SEMPRE adaptativos (rolling)

- [ ] NUNCA usar thresholds fixos nos Inputs para features derivadas
- [ ] Rolling percentiles: armazenar em **GlobalVariable string** (comma-separated)
- [ ] Seed de 21 dias no `OnInit()` se o buffer estiver vazio
- [ ] Atualizar o buffer APÓS computar o sinal (não usar o dia atual no próprio sinal)
- [ ] Trim para 21 dias no `BufSalvar()` (ou o valor de `InpBufDias`)

```cpp
// Padrão de buffer rolling via GV
void BufCarregar() { /* split da GV string */ }
void BufSalvar()   { /* join dos ultimos N dias */ }
void BufAdd(su, br) {
   // append, trim, save
}
double Percentil(arr, n, pct) {
   // sort, index = (n-1) * pct
}
```

**Exceção:** parâmetros de execução (SL em pts, volume, magic number) podem ser Inputs.

---

## 3. Preço de entrada — CONHECIDO no momento do sinal

- [ ] O preço de entrada deve ser CONHECIDO quando o sinal é processado
- [ ] NUNCA depender do range da barra ATUAL (circular)
- [ ] O preço deve ser ALCANÇÁVEL na barra de entrada
- [ ] Opções de preço conhecido E alcançável:
  - **Open da barra atual + % do range da barra anterior** (proxy)
  - Preço fixo validado (ex: open + 45pts)

```cpp
// CERTO: conhecido E alcançavel
double off = fmin(R_anterior * 0.30, 60);  // 30% range anterior, max 60pts
double limit = open_atual + off;
// ERRADO: conhecido mas NUNCA alcançado (continuacao nao retorna ao high anterior)
double limit = high_barra_anterior;
// ERRADO: circular
double limit = open_atual + 0.5 * (high_atual - low_atual);
```

---

## 4. Execução da entrada — SELL_LIMIT / BUY_LIMIT

- [ ] Usar **ordem pendente** (SELL_LIMIT / BUY_LIMIT) para entrar em nível específico
- [ ] SELL_LIMIT funciona em OHLC se o preço é de barra CONHECIDA
- [ ] Se ask (ou bid) já >= preço limite → MARKET direto (evita pending order desnecessária)
- [ ] Cancelar a pending order em 9:02 (próximo bar) se não executou

```cpp
if (ask >= limit_price) {
   // MARKET direto
   req.type = ORDER_TYPE_SELL;
   req.price = bid;
} else {
   // SELL_LIMIT
   req.action = TRADE_ACTION_PENDING;
   req.type = ORDER_TYPE_SELL_LIMIT;
   req.price = NormalizeDouble(limit_price, _Digits);
}
// Cancelar em 9:02
if (!hasPos()) DelPending();
```

---

## 5. Stop — baseado em preço CONHECIDO

- [ ] Stop em preço CONHECIDO, não no range da barra atual
- [ ] Validar contra dados históricos (P75 do range da hora)
- [ ] Pode ser Input (ex: `InpStopPts = 120` baseado no container P75)
- [ ] NUNCA: stop = high_01 + X (high_01 é desconhecido até o fim da barra)

```cpp
// CERTO
double stop = high_da_barra_conhecida + InpStopPts;
// CERTO (alternativa)
double stop = entry + InpStopPts;  // fixo, validado
// ERRADO
double stop = high_01 + 10;  // high_01 só conhecido no FIM de 9:01
```

---

## 6. Exit — tempo > preço

- [ ] Preferir **time-based exit** sobre TP fixo
- [ ] Time exit: verificar posição no horário alvo (ex: 9:11)
- [ ] Se tiver TP, usar como bônus, não como saída principal
- [ ] Em OHLC: verificar a cada barra nova após o horário alvo

```cpp
if (h == 9 && m == 11) {
   if (hasPos()) Fechar();  // fecha a mercado
}
```

---

## 7. Contexto D-1 — persistir entre sessões

- [ ] Usar GlobalVariables com prefixo único (`"H141_ontem_9dir"`)
- [ ] Salvar no `OnDeinit()`, carregar no `OnInit()`
- [ ] Prefixo único previne conflito entre estratégias no mesmo terminal

```cpp
int OnInit() {
   g_ontem_9dir = (int)GlobalVariableGet("H141_ontem_9dir");
}
void OnDeinit() {
   GlobalVariableSet("H141_ontem_9dir", g_ontem_9dir);
}
```

---

## 8. Teste no Strategy Tester

- [ ] "1 min OHLC" é SUFICIENTE (não precisa "Every tick")
- [ ] Tempo esperado: ~2-3 segundos para 5 anos de M1
- [ ] SELL_LIMIT testa corretamente em OHLC se preço é conhecido
- [ ] Verificar:
  - Número de trades esperado
  - Fill rate da pending order
  - Time exit funcionando
  - Rolling percentiles evoluindo (log)

**Modo "Every tick"** só necessário se houver lógica intra-barra (ENTRADAS POR ORDEM LIMITE DURANTE A BARRA funcionam via pending order, não precisam de Every tick).

---

## 9. Estrutura do código

- [ ] `if (!isNewBar()) return;` — UMA linha, zero lógica intra-barra
- [ ] Padrão H140: isNewBar + getBar + OnTradeTransaction
- [ ] < 250 linhas
- [ ] Inputs só para parâmetros de execução (volume, SL, magic)
- [ ] Logging: features do candle, sinal, entry/exit

---

## 10. Armadilhas comuns

| Armadilha | Solução |
|:----------|:--------|
| Thresholds fixos que não acompanham o mercado | Rolling percentiles em GV |
| Preço de entrada circular (depende da barra atual) | Usar preço CONHECIDO |
| Stop baseado em high desconhecido | Stop fixo validado ou preço conhecido |
| Múltiplas instâncias do EA corrompem GV | Prefixo único (`"H141_"`) |
| Tester lento | OHLC mode, não Every tick |
| Buffer vazio no primeiro teste | Seed de 21 dias no OnInit |

---

## Referências

- H140 EA: `strategy/H140_Markov_Puro.mq5` — padrão de estrutura simples
- H141 EA: `strategy/H141_Continuacao.mq5` — rolling percentiles + SELL_LIMIT + time exit
- H141 anatomy: `hipoteses/ATIVAS/H141/ANATOMIA.md` — lições específicas da estratégia
- Container SL/TP: `principios/sl-tp.md` — P75/P50 por hora
