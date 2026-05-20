# H143 — Volume alto + range elevado + sombra inferior pesada

## Regra
`vol_9 > 4106, range_9_rank > 0.525, shadow_dn > 0.4535` → VENDA

## Tese
Volume acima da média + range no percentil 53+ dos últimos 21 dias + sombra inferior ocupa >45% do candle. Sinal de distribuição (venda no range alto com liquidez) → 9:01 cai.

## Batch screening (1097 dias)
N=104 | media=+56pts | media_apos_custo=+46pts | WR=65.4% | Sharpe=0.34 | p=0.003

## Origem
Mineração Markov v2 — 49 features, RF depth=5, walk-forward 2024.
