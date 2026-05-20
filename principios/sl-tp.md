# Stop Loss e Take Profit — Princípios Thorp

---

## SL (container)

Stop loss **não é edge**. É container.

- **SL = P75 do range da hora** (sem multiplicadores, sem regime)
- P75 do range histórico total por hora. ~35k candles/hora. Confiança >99%.
- **Nunca otimizar SL.** Trocar P75 pra P80 não é otimizar. Grid search de stop em pontos é overfit.

---

## TP (container)

TP só é edge se a **tese** define (preço-alvo ou tempo-alvo). Caso contrário é container:

- **TP = P50 do range da hora** (mediana histórica por hora)
- ~35k candles/hora. Confiança >99%.
- Aplicado IGUAL na hipótese e no baseline.

**RR fixo (stop×1.5, stop×2) não é edge.** P50 é menos arbitrário que RR fixo.

---

## Pipeline

```
1. (Opcional) Baseline test — diagnóstico rápido:
   python scripts/testar_vs_baseline.py Hxxx
   Compara condição vs direção aleatória. Mostra se o filtro adiciona algo.

2. BT real (gate definitivo):
   python scripts/run_bateria.py Hxxx
   SL=P75, TP=P50, slippage calibrado. p<0.05 e metades ok → PASSOU.

3. Target final:
   ├─ Tese define preço ou tempo → usa
   └─ Tese não define → 17h (fim da sessão)
```

O BT real já é o padrão ouro. O baseline test é um atalho pra matar hipóteses fracas em segundos.

---

## RiskGuardian (implementado)

1. strategy retorna stop > 0 → usa
2. stop == 0 → calcula P75 hora
3. strategy retorna target > 0 → usa
4. target == 0 → calcula P50 hora
5. max_exit_time == None → 17h

## Containers por minuto (opcional)

Para microestrutura (abertura, minutos específicos), `core/containers.py` tem
P50/P75 e VOL_P50/VOL_P75 por minuto (9:00-9:30), calculados de 585 pregões.

Uso: a estratégia importa os valores e seta stop/target no Signal diretamente,
bypassando o RiskGuardian. Per-minute é mais preciso que per-hour quando o
comportamento do mercado muda drasticamente minuto a minuto (como na abertura).
