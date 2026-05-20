# Anatomia de Hipótese — Template

## O que é

A Anatomia de Hipótese é o processo de **dissecar cada parâmetro de uma hipótese contra os dados empíricos** antes de testá-la. O objetivo é responder: *este parâmetro veio da estrutura do mercado ou de um chute?*

---

## Estrutura

### 1. Tese pura

O que a hipótese afirma sobre o mercado, **sem parâmetros**:

> Ex: "A abertura da WIN tem overshoot que reverte"

### 2. Decomposição paramétrica

Para cada parâmetro da implementação, responder:

| Parâmetro | Valor | Origem presumida | Origem real (dados) | Veredito |
|-----------|-------|-------------------|---------------------|----------|
| Janela temporal | 5 min | Fim da descoberta | Número redondo; fase de descoberta varia 5-10min | Arbitrário |
| Threshold | 0,3% | "Queda grande" | p10 da distribuição; cap de frequência | Arbitrário |
| Timing entrada | 9:06 | "Próximo candle" | r=+0,97 lag1; continua momentum | Arbitrário |

### 3. Teste condicional

O que os dados dizem sobre a premissa central:

> Ex: "Após drop >0,3% no m5, retorno médio m6-m30 = -0,028% (p=0,45) — não há reversão"

### 4. Estrutura de mercado (o que os dados revelam)

Propriedades observáveis do mercado relevantes para a pergunta:

- Perfil de volume por minuto
- Decaimento de range
- Correlação serial dos retornos
- Half-life de choques
- Distribuição condicional

### 5. Diagnóstico

- Premissa central é verdadeira ou falsa?
- Parâmetros são estruturais ou arbitrários?
- Vale a pena reformular ou a pergunta está morta?

---

## Checklist de integridade

- [ ] Cada parâmetro tem uma justificativa que vem do mercado, não de um número redondo
- [ ] A tese é testável e falseável
- [ ] Thresholds são adaptativos (quantil, volatilidade) ou, se fixos, justificados por borda natural do mercado
- [ ] Janelas temporais correspondem a fases observáveis (não minutos redondos)
- [ ] A correlação serial do ativo não contradiz a direção da aposta
- [ ] O baseline test é informativo (KS p < 0.05 ou diagnóstico claro de ruído)
