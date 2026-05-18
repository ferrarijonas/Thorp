# Stop Loss e Take Profit — Princípios Thorp

---

## SL

Stop loss **não é edge**. É container. Serve pra dar um limite pro trade errado sem cortar os bons.

- **SL = P75 do range da hora × alpha(regime ontem)**
- P75 do range histórico total por hora. ~35k candles/hora. Confiança >99%.
- alpha: Consolidado=1.2, Moderado=1.5, Forte=2.0. Fixos, redondos, não otimizados.
- Se regime não disponível: usa alpha=1.5.
- **Nunca otimizar SL.** Trocar P75 pra P80 não é otimizar (ainda é descritivo). Grid search de stop em pontos é overfit.

Preferir SL mais largo com alta confiança a SL apertado com baixa confiança. Edge que você corta não volta.

---

## TP

Diferente do SL, TP **pode** ser edge. Mas só se a hipótese disser onde o movimento termina.

### Fontes de target

| Fonte | Exemplo | Edge? |
|---|---|---|
| Tese (preço) | "Volta pra média 200", "fecha o gap" | ✅ Sim |
| Tese (tempo) | "Reversão leva 15 min", "momentum dura 5 candles" | ✅ Sim |
| Nenhum | Não tem tese de saída → 17h (fim da sessão) | ❌ Não |

**RR fixo (stop×1.5, stop×2) não é edge.** É convenção. Só usado como último fallback.

### Baseline test (gate obrigatório)

Antes de qualquer análise de target, a hipótese precisa provar que a **condição é melhor que aleatório no mesmo instante:**

```
python scripts/testar_vs_baseline.py Hxxx
```

O baseline gera N trades no mesmo horário de cada sinal com direção aleatória (cara/coroa). Compara distribuições via KS test.

- **Se p(KS) > 0.05** → condição é ruído. Hipótese MORTA.
- **Se p(KS) < 0.05** → condição tem edge. Continua pro teste padrão.

### Diagnóstico MFE (pós-baseline, pós-teste padrão)

Se a hipótese passou baseline + teste padrão, roda **MFE** como diagnóstico de target:

```
python scripts/analisar_mfe.py Hxxx
```

1. Divide dados 70/30 por data
2. Gera **todos os sinais** sem bloquear posição
3. Calcula MFE com bootstrap de P50, P75, P90
4. Valida cada percentil como target na amostra OOS

**Se MFE passar OOS** → usa como target descritivo.
**Se MFE falhar OOS** → mantém só saída temporal (17h). O edge é só de entrada.

---

## Como o RiskGuardian decide

1. strategy retorna stop > 0 → usa da estratégia
2. stop == 0 → P75 hora × alpha(regime ontem)
3. strategy retorna target > 0 → usa da estratégia (pode vir de MFE)
4. target == 0 → max_exit_time = 17h (fallback temporal da sessão)
5. target == 0 E sem max_exit_time → rr_ratio (último caso)
