# H144 — Verde com sombra inferior e gap pequeno

## Regra
`green_9 > 0.5, shadow_dn > 0.0651, gap <= 32.5` → VENDA

## Tese
9:00 verde (compradores no controle) + sombra inferior presente (rejeitaram baixa) + gap pequeno/neutro (sem viés noturno forte). Sinal de exaustão compradora → 9:01 reverte pra baixo.

## Batch screening (1097 dias)
N=180 | media=+35pts | media_apos_custo=+25pts | WR=58.9% | Sharpe=0.20 | p=0.026

## Origem
Mineração Markov v2 — 49 features, RF depth=5, walk-forward 2024.
