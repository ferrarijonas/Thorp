# Thorp — Concept Spec

## Intenção

Este sistema existe para que **um agente de IA** consiga **descobrir, testar, validar e executar estratégias de trading na B3 (WIN)** sem precisar de **intervenção manual entre as fases de pesquisa e execução, mantendo rastreabilidade total de cada decisão.**

---

## O que é

Thorp é um **sistema agêntico de trading quantitativo** onde o agente IA é o orquestrador central. Ele parte de dados brutos do MetaTrader 5, gera radiografias do mercado, formula hipóteses, testa, valida, e executa — tudo com observabilidade total através do sistema de arquivos.

O nome vem de **Ed Thorp**, matemático que provou que mercados podem ser modelados. Aqui, o agente IA é o Thorp: observa, calcula e age.

Cadeia completa: **Dados → Radiografia → Hipóteses → ZenSpec → Código → Teste → Demo → Real**.

---

## Para quem é (e não é)

| É para | Não é para |
|--------|------------|
| Um agente IA que orquestra trading sistemático | Trading discricionário ("achismo") |
| Estratégias intraday em WIN (mini-índice B3) | Ações, opções, ou múltiplos ativos simultâneos |
| Pesquisador que quer rastreabilidade total | Quem quer executar sem entender o motivo |
| Fluxo backtest → demo → real sem atrito | Estratégia "liga e esquece" sem supervisão |

---

## Problema

1. **Pesquisa e execução são mundos separados.** O que funciona no backtest em Python morre na tradução pra MQL5. Resultados divergem sem explicação.
2. **Decisões não são rastreadas.** "Por que essa estratégia foi descontinuada?" — não há registro.
3. **Observabilidade zero.** O agente IA não consegue saber o estado atual do sistema sem ler dezenas de arquivos.
4. **Atrito entre modos.** O mesmo código não roda em backtest, demo e real — cada modo requer adaptação manual.

---

## Diferencial

| Característica | Thorp | Alternativas (Nautilus, backtrader, MT5 puro) |
|----------------|-------|-----------------------------------------------|
| Orquestrador IA | O agente IA é o cérebro, tudo passa por ele | Pipelines fixos, sem agente |
| Cadeia spec→código | ZenSpecKit: Concept → Eng → Stack → Sensei → ZenSpec → Código | Nenhuma especificação formal |
| Observabilidade | `state/` com JSON legíveis pelo agente a qualquer momento | Logs soltos, sem padrão |
 | Rastreabilidade | `decisions.log` com justificativa de cada ação | Nenhum registro de decisão |
| Um código, 3 modos | Backtest / Demo / Real com same interface | Cada modo com código diferente |
| B3 nativo | WIN M1, range por hora, P75 stop adaptativo | Foco crypto ou forex |

---

## Promessas

1. **Uma estratégia, três modos.** O mesmo código Python roda em backtest (dados históricos MT5), demo (mt5.order_send em conta demo) e real (mt5.order_send em conta real). A diferença é uma linha de config.
2. **Rastreabilidade forense.** Toda decisão do agente (criar hipótese, testar, validar, rejeitar, executar, parar) fica registrada em `state/decisions.log` com data, justificativa e resultado observado.
3. **Observabilidade em tempo real.** O agente (ou um humano) abre `state/session.json` e sabe: fase atual, estratégias ativas, P&L, drawdown, posições abertas, última decisão.
4. **Hipóteses vivas.** Cada hipótese (H101–H120) é um programa com ZenSpec, código e testes. Nenhuma estratégia morre no esquecimento — seu veredito final fica registrado.
5. **MT5 como data/exec layer.** O MetaTrader 5 é tratado como fonte de dados e gateway de execução. O agente IA não precisa de MQL5 — só Python chamando `MetaTrader5`.
6. **Auto-preservação.** O sistema não opera em dias de alta volatilidade anômala (eventos macro, feriados B3, abertura com gap > 2%). Drawdown máximo impede novas entradas.

---

## Princípios

- **Observabilidade primeiro.** O agente IA só decide bem se enxerga tudo. Todo estado do sistema é exposto em arquivos legíveis.
- **Agente orquestrador, não script.** O agente IA (opencode) é o cérebro. Scripts são ferramentas que ele chama. Nada acontece sem passar pelo agente.
- **Spec antes de código.** Toda estratégia, todo componente, toda pipeline começa com uma ZenSpec. Código sem spec não entra.
- **Rastro digital.** Se o agente tomou uma decisão, ela está registrada com motivo. Se não está registrada, não aconteceu.
- **Um código, três modos.** Backtest, demo e real compartilham a mesma lógica. A diferença é só o conector de execução.
- **Dados reais, não simulados.** Toda hipótese é testada contra dados históricos reais do MT5 (WIN M1). Sem dados sintéticos.
- **Falhe explícito.** Se MT5 desconecta, se o dado não carrega, se a ordem rejeita — o erro é registrado e o sistema para. Sem trades secretos.
- **Menos é mais.** Uma estratégia que funciona vale mais que 20 que não funcionam. O pipeline prioriza profundidade sobre quantidade.
- **Adaptativo por hora.** Stop e target não são fixos — usam P75 do range da hora corrente. O mercado muda durante o dia, o stop acompanha.

---

## Fronteiras (o que NÃO é)

- Não é um robô MQL5. Código MQL5 pode existir como bridge, mas o cérebro é Python.
- Não faz trading de ações, opções, futuros de commodity, crypto. Só WIN (mini-índice B3).
- Não substitui o MT5 Strategy Tester para backtests complexos de MQL5. O foco é backtest em Python com dados MT5.
- Não é um sistema de risk management institucional. Não faz hedge, não gerencia múltiplas contas.
- Não tem interface gráfica. Toda interação é via arquivos + CLI.
- Não executa sem supervisão do agente. O agente IA está sempre no loop.
- Não opera em múltiplos timeframes simultaneamente. Só M1.

---

## Decisões

| Decisão | Alternativa descartada | Motivo |
|---------|----------------------|--------|
| Agente IA como orquestrador central | Pipeline batch sem IA | IA pode adaptar, replanejar e justificar decisões em tempo real |
| MetaTrader5 como data/exec layer | NautilusTrader, backtrader, broker direto | MT5 já tem B3, já temos dados WIN M1, instalação zero |
| Filesystem como estado | Banco de dados, Redis | Observabilidade imediata: qualquer arquivo é legível pelo agente sem queries |
| ZenSpecKit como metodologia | Nenhuma especificação formal | Rastreabilidade, determinismo, auditabilidade |
| Python puro (sem MQL5) | Estratégias em MQL5 com chamadas Python | Mesmo código nos 3 modos; ecossistema Python para ML/análise |
| WIN M1 como ativo único | Múltiplos ativos | Foco, simplicidade, dados que já temos validados |
