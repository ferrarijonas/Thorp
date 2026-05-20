# H147 — Fluxo comprador não extremo + range pequeno + sem sombra superior

## Regra
`order_flow > -18792.5, range_9 <= 222.5, shadow_up <= 0.1111` → VENDA

## Tese
Fluxo comprador não está extremamente negativo (order_flow > -18792) + range pequeno (<= 222pts) + sem sombra superior relevante (shadow_up <= 11%). Candle sem rejeição em range pequeno, sem força compradora → 9:01 continua baixista.

## Batch screening (1097 dias)
N=192 | media=+30pts | media_apos_custo=+20pts | WR=55.2% | Sharpe=0.17 | p=0.053

## Origem
Mineração Markov v2 — 49 features, RF depth=5, walk-forward 2024.
