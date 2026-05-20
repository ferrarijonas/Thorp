# H145 — Regime baixo + gap caindo

## Regra
`regime_vol <= 0.5, delta_gap <= -2.5` → VENDA

## Tese
Range do 9:00 no terço inferior dos últimos 21 dias (regime baixo) + gap overnight caiu relativo a ontem. Microestrutura de baixa volatilidade com viés baixista → 9:01 continua caindo.

## Batch screening (1097 dias)
N=138 | media=+37pts | media_apos_custo=+27pts | WR=55.1% | Sharpe=0.21 | p=0.039

## Origem
Mineração Markov v2 — 49 features, RF depth=5, walk-forward 2024.
