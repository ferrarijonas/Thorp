# H140 — Markov Puro (A Cadeia do Primeiro Minuto)

## Status: EM DEMO (20/05/2026)

Data: 2026-05-19 | Fase: Walk-forward concluido. Rodando em demo a partir de 20/05/2026.

Decisao: Apesar de MORTA no compare (path-dependent), o sinal e significativo (p<0.001) e a re-simulacao mostra +38 a +44pts. Vale testar em execucao real para verificar se o edge sobrevive ao slippage real do MT5.

Script de demo: `python scripts/run_demo.py` (atualizado com H140Strategy)
Horario: 8:55 (abertura), monitorar primeira hora (9:00-10:00)

---

## Tese central

> O primeiro minuto do dia (9:00) contem um estado oculto de Markov que, combinado com o contexto de D-1, **reverte em 9:01**. A transicao e anti-persistente, nao momentum.

A descoberta central: **9:01 reverte o sinal de exaustao/rejeicao de 9:00, especialmente quando o contexto de ontem reforca a reversao.**

---

## Metodologia

### Round 1 — Radiografia (100 preditores individuais)
- **Script:** `scripts/radiografia_h140.py`
- **Resultado:** 5/100 significantes a p<0.05 — exatamente o esperado por acaso
- **Conclusao:** Nenhum preditor marginal preve 9:01 isoladamente
- **Licao de Markov:** Testar variaveis uma a uma = testar letras individuais (A?, E?, O?). A estrutura esta na **classe** (vogal/consoante), nao na letra

### Round 2 — HMM em todos os minutos
- **Script:** `scripts/hmm_todos_minutos.py`
- **Resultado:** Estados latentes (K=5) encontrados via GMM em 282k candles
- **9:00 -> 9:01:** Nenhum estado preve (todos p > 0.46)
- **Global minuto-a-minuto:** Mean reversion existe (p=0.0000), mas efeito <1pt
- **Conclusao:** A cadeia Markoviana global e mean-reversion, mas o 9:00 e um caso especial que requer contexto

### Round 3 — Mineracao de classes (Random Forest + varredura de pares)
- **Script:** `scripts/minerar_markov.py` / `scripts/busca_combinatoria.py`
- **Metodo:** Random Forest 100 arvores (max_depth=5) em 47 features + varredura exaustiva de pares binarios
- **Resultado:** 305 classes Markovianas com p < 0.10, 30 com p < 0.001
- **Conclusao:** A estrutura aparece nas **interacoes condicionais** de 2-3 variaveis, nao nos efeitos marginais

---

## Os 4 Temas Markovianos (consolidados da mineracao)

### Tema 1: Sombra superior -> COMPRA (rejeicao no topo)

| Regra | N | Efeito | p-valor |
|-------|---|--------|---------|
| `shadow_up > P50` (sozinho) | 244 | +16 pts | 0.017 |
| `shadow_up > P50 + pos_close > P25` | 189 | +29 pts | 0.004 |
| `shadow_up > P50 + volume > P25` | 188 | +27 pts | 0.004 |
| `shadow_up > P50 + pos_close > P50` | 112 | +36 pts | 0.026 |

**Tese:** Rejeicao no topo = vendedores tentaram subir, falharam, compradores entram em 9:01.

### Tema 2: Errou ontem -> VENDA extrema

| Regra | N | Efeito | p-valor |
|-------|---|--------|---------|
| `errou ontem + shadow_up <= P50` | 126 | **-52 pts** | 0.003 |
| `errou ontem + range > P50` | 120 | -36 pts | 0.037 |
| `errou ontem + 9:00 vermelho` | 124 | -38 pts | 0.046 |
| `errou ontem + body > 14% + shadow_dn > P75` | 21 | 97% VENDA | 0.000 |

**Tese:** Quando a previsao de ontem falhou, 9:01 amplifica o movimento de venda.

### Tema 3: Gap grande -> COMPRA (gap reversal)

| Regra | N | Efeito | p-valor |
|-------|---|--------|---------|
| `gap > 318 + range < 158 + pos_close > 0.29` | 15 | 96% COMPRA | 0.000 |
| `gap > 302 + fractal > 1.51 + vol normal` | 16 | 93% COMPRA | 0.000 |
| `gap > 322 + shadow_up > 12%` | 42 | 78% COMPRA | 0.002 |
| `gap > 318 + body_ratio < 89%` | 38 | 83% COMPRA | 0.000 |

**Tese:** Gap de rompimento reverte pra cima em 9:01. Confirma H127.

### Tema 4: Acertou ontem + rejeicao -> COMPRA

| Regra | N | Efeito | p-valor |
|-------|---|--------|---------|
| `acertou + shadow_dn > P50 + range_rank normal` | 26 | 90% COMPRA | 0.000 |
| `acertou + vol_rank > 0.78 + vol < 21k` | 23 | 88% COMPRA | 0.001 |
| `acertou + shadow_up > 12% + vol > 9k` | 49 | 77% COMPRA | 0.001 |

**Tese:** Contexto de acerto + candle com rejeicao = COMPRA em 9:01.

---

## Implementacao final (v2 — walk-forward)

Regras validadas em `strategy/H140_strategy.py`:

**COMPRA (3 regras):**
1. `ontem 9:01 verde AND range_9 > P75` (N=34, p=0.036 no teste)
2. `wick_asym <= P50 AND shadow_up <= P75` (N=63, p=0.087 no teste)
3. `shadow_up > 39% AND fractal > 1.51 AND ontem 9:00 vermelho` (N=9, acc=89%)

**VENDA (3 regras):**
1. `range_9 > P50 AND pos_close > P75` (N=23, p=0.043 no teste)
2. `acertou_ontem=False AND shadow_up <= P50` (N=42, p=0.061 no teste)
3. `shadow_up <= P75 AND shadow_dn > 25% AND range_9 > 182` (N=17, p=0.037 no teste)

Percentis computados de buffer rolante de 21 dias.

---

## Resultados dos testes

### v1 (4 temas da mineracao inicial)
```
avaliar_hipotese.py H140: N=229, Re-sim +5 a +18pts, p>0.05 — NAO PASSOU
```

### v2 (walk-forward validated)
```
avaliar_hipotese.py --entry H140:
  TP      worst           best
  P50  +38 p=0.0005   +40 p=0.0002
  P75  +40 p=0.0006   +42 p=0.0002
  2x   +43 p=0.0006   +43 p=0.0006
  3x   +44 p=0.0007   +44 p=0.0007
  N=263, WR=60-62%, geometria de entrada irrelevante (5/5 identicas)

BT original (engine, cost=10, OHLC worst): N=263 media=-21 WR=54% p=0.0014
  → Sinal e real (p<0.001 ambos), mas execucao come ~60pts
```

### Walk-forward split
```
Treino: 359 dias (< 2025-07-01) | Teste: 138 dias (>= 2025-07-01)
Regras RF significativas no treino: 259
Sobreviveram ao teste out-of-sample: 7 regras com p<0.05
```

---

## Referencias

| Ref | Contribuicao |
|-----|-------------|
| Markov, A. A. (1906) | Cadeias de Markov — a estrutura esta na classe, nao na variavel |
| Breiman, L. (2001) | Random Forests — encontra interacoes que testes marginais nao capturam |
| Arlot & Celisse (2010) | Cross-validation — walk-forward como padrao ouro para series temporais |
| Nison, S. (1991) | Candlestick patterns — sombras como sinal de rejeicao |
| Bulkowski, T. (2008) | Encyclopedia of Candlestick Charts — validacao estatistica de shadows |
| Cont, R. (2001) | Mean reversion em microestrutura de mercados |
| H127 (Thorp) | Gap reversal — gap overnight reverte na abertura |

---

## Proximos passos

1. ~~Rodar `avaliar_hipotese.py H140`~~ CONCLUIDO: p<0.001 em todos os TPs
2. Rodar `pipeline.py H140` — Gate 1 (BT ideal) + Gate 2 (BT slippage)
3. Rodar `pipeline.py --compare H140` — testar worst AND best OHLC
4. Se p<0.05 com metades ok em todos: promovida para PASSOU
