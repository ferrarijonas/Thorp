# H141 — Continuação de 9:00 (herdado do H140)

## Tese central

> Quando o H140 sinaliza VENDA, 9:00 já caiu (-14.7pts) e 9:01 continua caindo (-34.7pts), com queda sustentada por 5-10min (+60pts). O edge é de **continuação**, não reversão. A entrada deve explorar isso via ordem limite no high do candle.

## Origem

Herdado do H140 (Markov Puro v3). O H140 tinha edge real (p=0.0143, N=166) mas o container SL=P75/TP=P50 criava RR desfavorável (120:80) que matava o EV. A análise do sinal bruto revelou:

- **Natureza: CONTINUAÇÃO** (correlação 9:00→9:01 = +0.145)
- **Direção: só VENDA** (0 de 166 sinais foram COMPRA)
- **Janela ótima: 5-10min** (+60-64pts)
- **Entrada limite no high** melhora drasticamente o resultado

## Método

1. Mesmas regras VENDA do H140 (shadow_up <= P50 + body_ratio <= P75, etc.)
2. Entrada via **ordem limite no open + 50% do range da 9:01**
3. Stop no **high da 9:01 + 10pts** (leve, só proteção)
4. **Time exit em 10min** (max_exit_time = 9:11)
5. Alvo opcional: P50 do minuto (se atingir antes do time exit)

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
```
ENTRADA: limite no open + 50% do range da 9:01 (so executa se high >= limite)
STOP:   high da 9:01 + 10pts (protecao)
EXIT:   time-based em 9:11 (10min hold)
ALVO:   P50 do minuto (opcional, se atingir antes do time exit)
SINAL:  shadow_up <= P50 AND body_ratio <= P75 (VENDA)
        + variante com acertou=False (reforco)
        Min 2 votos para entrar.
```
