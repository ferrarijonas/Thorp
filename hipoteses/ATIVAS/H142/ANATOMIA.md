# H142 — Sombra inferior + corpo grosso + fragilidade baixa

## Regra
`delta_body <= -0.0365, fragilidade <= 0.1504, body_ratio > 0.4472` → VENDA

## Tese
Corpo do candle encolheu vs ontem (delta_body negativo) + abertura representa fração pequena do range total de ontem (fragilidade baixa) + corpo domina o candle (body_ratio > 0.45). Contexto de baixa volatilidade na abertura com corpo forte → 9:01 reverte pra baixo.

## Batch screening (1097 dias)
N=92 | media=+62pts | media_apos_custo=+52pts | WR=62.0% | Sharpe=0.29 | p=0.010

## Origem
Mineração Markov v2 — 49 features, RF depth=5, walk-forward 2024.
