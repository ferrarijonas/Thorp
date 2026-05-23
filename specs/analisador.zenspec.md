# Analisador (`core/analisador.py`)

Unifica todas as métricas de avaliação de hipóteses numa classe só.
O que hoje está espalhado em `engine._calc_stats()`, `avaliar_hipotese._calc_estatisticas()`,
`avaliar_hipotese.re_simular_um()`, e `testar_containers.mfe_mae()` vai pra cá.

---

## Contratos

### 1. `Analisador.calcular(trades: list[Trade]) -> dict`

**Entrada:** lista de `Trade` (com `pnl_points`, `rastro`, `entry`, `direction`).

**Saída:** dict com chaves em português:

| Chave | Tipo | Descrição |
|-------|------|-----------|
| `N` | int | número de trades |
| `media_pts` | float | média de pontos por trade |
| `wr_pct` | float | win rate em % |
| `vantagem_pct` | float | (WR − 50) × 2 — edge sobre aleatório |
| `p_valor` | float | p-valor do t-test |
| `pf` | float | profit factor |
| `sharpe` | float | razão média/desvio |
| `dd_max` | float | drawdown máximo em pontos |
| `mfe_medio` | float | MFE médio (positivo) |
| `mae_medio` | float | MAE médio (positivo) |
| `metade1` | float | média da 1ª metade |
| `metade2` | float | média da 2ª metade |
| `metades_ok` | bool | metades têm mesmo sinal |

**Edge cases:**
- 0 trades → `N=0, media_pts=0, wr_pct=0, vantagem_pct=0, p_valor=1, pf=0, sharpe=0, dd_max=0, mfe_medio=0, mae_medio=0, metade1=0, metade2=0, metades_ok=True`
- 1 trade → p_valor=1, metades usam o mesmo array, mfe/mae calculados se rastro existe
- trades sem rastro → mfe_medio=0, mae_medio=0
- todas wins → pf=inf
- todas losses → pf=0

### 2. `Analisador._mfe_mae(rastro, entry, direcao) -> (float, float)`

**Entrada:**
- `rastro: list[tuple(O,H,L,C,time)]` — barras do rastro
- `entry: float` — preço de entrada real
- `direcao: Direction` — COMPRA ou VENDA

**Saída:** `(MFE, MAE)` ambos >= 0.

**Lógica:**
- COMPRA: MFE = max(H − entry, 0), MAE = max(entry − L, 0)
- VENDA: MFE = max(entry − L, 0), MAE = max(H − entry, 0)

### 3. `Analisador.vantagem_por_entrada(trades, sl_fn, tp_fn, conv="worst") -> dict`

**Entrada:**
- `trades: list[Trade]`
- `sl_fn: callable(Trade) -> float` — P75 por minuto
- `tp_fn: callable(sp, minute) -> float` — P50 por minuto
- `conv: str` — "worst" ou "best"

**Saída:** `{"abertura": {media_pts, vantagem_pct, wr_pct, p_valor}, ...}`

**Geometrias:** abertura (=open), fechamento (=close), maxima (=high), minima (=low)
**Não inclui:** "meio" (mid), geometrias extras

**Edge cases:**
- trade sem rastro → pula
- offset do fechamento = 1 (ignora barra de entrada)
- rastro vazio após offset → None, trade ignorado
- < 5 trades válidos → retorna {} pra essa geometria

### 4. `Analisador.decaimento_temporal(trades, max_barras=20) -> dict`

**Entrada:**
- `trades: list[Trade]`
- `max_barras: int` — limite de barras a analisar

**Saída:** `{0: {media_pts, vantagem_pct, wr_pct, N}, 1: {...}, ...}`

**Lógica:** Para cada índice de barra i, calcula PnL no close da barra i para todos os trades que têm rastro com pelo menos i+1 barras.
- COMPRA: PnL = close_i − entry
- VENDA: PnL = entry − close_i
- Sem SL/TP aplicado (sinal puro)

**Edge cases:**
- < 5 trades no índice → pula
- N diminui ao longo do tempo (trades fecham)

### 5. `Analisador.re_simular(trades, sl_fn, tp_niveis, convencoes, geo) -> dict`

**Entrada:**
- `trades: list[Trade]`
- `sl_fn: callable(Trade) -> float` — P75 por minuto
- `tp_niveis: list[tuple(str, callable)]` — ex: `[("P50", lambda sp,m: P50_PTS.get(m,120)), ...]`
- `convencoes: list[str]` — ["worst", "best"]
- `geo: str` — geometria de entrada (padrão: "fechamento")

**Retorno:** `{"P50_worst": {media_pts, wr_pct, p_valor}, "P50_best": {...}, ...}`

**TIME row:** Quando `tp_fn` é `None` (nome="TIME"), pula checagem SL/TP e usa só time exit (last close).

**Edge cases:** iguais a `vantagem_por_entrada`.

### 6. `ExecutionResult` (expandido em `core/types.py`)

Campos novos (todos com default 0):
- `vantagem_pct: float`
- `dd_max: float`
- `mfe_medio: float`
- `mae_medio: float`

**Contrato:** `ExecutionEngine._calc_stats()` deve preencher os 4 campos novos usando `Analisador.calcular()`.

### 7. `avaliar_hipotese.py` (reescrito)

**Um modo. Sem flags. Sempre:**

```
1. engine.run()                              → trades + resultado bruto
2. Analisador.calcular(trades)               → ANOMALIA + métricas base
3. Analisador.vantagem_por_entrada(trades)   → ENTRADA
4. Analisador.decaimento_temporal(trades)    → TEMPO
5. Analisador.re_simular(trades, TIME+TPs)  → CONTÊINER + veredito
6. print formatado unificado
```

**Saída (4 seções fixas):**

```
H109 | N=42 | ROBUSTO

ANOMALIA (rastro puro)
  MFE +85  MAE -62  assimetria +23

ENTRADA          Média   Vantagem  Acerto   p
  fechamento     +28pts  +10.0%    55.0%    0.014  ←
  mínima         +25pts  +8.0%     54.0%    0.028
  abertura       +22pts  +6.0%     53.0%    0.042
  máxima         +12pts  -2.0%     49.0%    0.340
  N=42  1ª metade +22  2ª +28  ✓  DD 180  PF 1.42

TEMPO PÓS-ENTRADA
  Barra   Média    Vantagem  Acerto   N
  +0min   +3pts    +0.0%     50.0%    42
  +1min   +8pts    +4.0%     52.0%    42
  +2min   +14pts   +6.0%     53.0%    40
  +3min   +20pts   +10.0%    55.0%    35  ← pico
  ...

CONTÊINER (TP × convenção)
  TP     pior (SL→TP)           melhor (TP→SL)
  TIME   +18  53%  p=0.020      +18  53%  p=0.020
  P50    +25  55%  p=0.014      +32  60%  p=0.003
  P75    +15  52%  p=0.042      +28  58%  p=0.008
  2×P75  +10  48%  p=0.120      +22  55%  p=0.030
  3×P75   +5  45%  p=0.250      +18  52%  p=0.060

  H109 | ROBUSTO
```

---

## Veredito automático

Baseado em `re_simular` com P50 worst/best:

- `P50_worst.p < 0.05` E `P50_best.p < 0.05` E mesmo sinal de média → **ROBUSTO**
- `P50_worst.p < 0.05` OU `P50_best.p < 0.05` → **SINAL OK**
- Nenhum p < 0.05 → **MORTA**
- 0 trades → **MORTA**

---

## Dependências

- `numpy`, `scipy.stats`
- `core/types.py`: `Trade`, `Direction`, `ExecutionResult`
- `core/containers.py`: P50, P75 (para funções de SL/TP)
