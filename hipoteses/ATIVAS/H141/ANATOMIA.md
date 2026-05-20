# H141 — Continuação de 9:00 (herdado do H140)

## Tese central

> Quando o H140 sinaliza VENDA, 9:00 já caiu (-14.7pts) e 9:01 continua caindo (-34.7pts), com queda sustentada por 5-10min (+60pts). O edge é de **continuação**, não reversão. A entrada deve explorar isso via ordem limite no high do candle.

## Origem

Herdado do H140 (Markov Puro v3). O H140 tinha edge real (p=0.0143, N=166) mas o container SL=P75/TP=P50 criava RR desfavorável (120:80) que matava o EV. A análise do sinal bruto revelou:

- **Natureza: CONTINUAÇÃO** (correlação 9:00→9:01 = +0.145)
- **Direção: só VENDA** (0 de 166 sinais foram COMPRA)
- **Janela ótima: 5-10min** (+60-64pts)
- **Entrada limite no high** melhora drasticamente o resultado

## Método (Python — pipeline de validacao)

1. Regra VENDA: `shadow_up <= P50_rolling AND body_ratio <= P75_rolling` (percentis 21 dias)
2. Entrada via **ordem limite no open + 50% do range da 9:01**
3. Stop no **high da 9:01 + 10pts** (leve, só proteção)
4. **Time exit em 10min** (max_exit_time = 9:11)
5. Min 2 votos (V1 + V2 com acertou)

## EA MT5 (simplificado — padrao H140)

```cpp
// Diferencas do Python:
// - Nao usa percentis rolling (use buffers 21 dias nao funciona em OHLC)
// - Nao usa entrada limite (nao ha ticks intra-barra em OHLC)
// - Nao usa time exit (usa SL/TP fixos via OrderSend)
// - Usa thresholds FIXOS via Inputs (ajustaveis no MT5)
//
// Regra: shadow_up <= InpShadowP50 && body_ratio <= InpBodyP75
// Entrada: MARKET SELL as 9:01 (nao limite)
// SL: entry + InpSL | TP: entry - InpTP
```

## Licoes sobre criar EAs para MT5

1. **NUNCA** usar logica intra-barra (`!isNewBar()` com condicoes) — MT5 tester OHLC nao gera ticks
2. **NUNCA** usar entrada limite (SELL_LIMIT) em estrategias OHLC — sem ticks, ordem nunca executa
3. **NUNCA** usar buffers rolling com GlobalVariables em EA — multiplas instancias corrompem dados
4. **SEMPRE** seguir o padrao H140: `if (!isNewBar()) return;` — 1 linha, zero complexidade
5. **SEMPRE** usar MARKET ORDER com SL/TP fixos nos Inputs
6. **SEMPRE** usar `getBar(1)` para ler barra COMPLETA (nunca `getBar(0)` que e barra atual)
7. **SEMPRE** testar no MT5 em "1 min OHLC" (nao "Every tick") — 2s vs 30min para 5 anos
8. **SEMPRE** manter EA < 250 linhas e estrutura identica ao H140 (comprovado)

## Setup

```bash
python scripts/avaliar_hipotese.py H141   # 1 BT + re-sim
python scripts/pipeline.py H141           # gates
python scripts/pipeline.py --compare H141 # robustez OHLC
```

## Resultados

### Pipeline
```
Gate 1 (BT ideal): N=74  media=+65  WR=96%  p=0.0000  → PASSOU
Gate 2 (slippage): N=74  media=+73  WR=95%  p=0.0000  → PASSOU
Compare: worst=+65(p=0.0000) best=+65(p=0.0000) → ROBUSTO
```

### Re-simulação (avaliar_hipotese.py)
```
TP      worst
P50  +56 p=0.0002  WR=54.1%
P75  +14 p=0.2268
2x   +14 p=0.2268
3x   +14 p=0.2268
```

### Status: PASSOU → EM DEMO (20/05/2026)

### Regras finais

**Python (pipeline — referencia de resultados):**
```
SINAL:  shadow_up <= P50_rolling AND body_ratio <= P75_rolling + !acertou
ENTRADA: limite no open + 50% range (so se high >= limite)
STOP:   high da 9:01 + 10pts
EXIT:   time-based 9:11 (10min hold)
N: 74 | media: +65 | WR: 96% | p: 0.0000 | ROBUSTO
```

**EA MT5 (simplificado — mesmo padrao H140):**
```
SINAL:  shadow_up <= InpShadowP50 && body_ratio <= InpBodyP75 (fixo)
ENTRADA: MARKET SELL as 9:01
SL:     entry + InpSL (default 120pts)
TP:     entry - InpTP (default 80pts)
Inputs: InpShadowP50=0.27, InpBodyP75=0.76
```
