# Thorp — Sensei Spec (v2)

- `Modo de execução: Core-first`

## Entradas

| Tipo | Arquivo | Papel |
|------|---------|-------|
| Conceito | `thorp-concept.md` | Porquê, o que é, fronteiras |
| Engenharia | `thorp-engineering.md` (v2) | Arquitetura feed/strategy/broker/engine |
| Stack | `thorp-stack.md` (v2) | Pastas, dependências, comandos |

---

## Saídas

| Nome | Arquivo | Escala |
|------|---------|--------|
| Sensei (macro) | `thorp-sensei.md` (este) | Macro: fases, componentes, blocos |
| ZenTarefas | `thorp-tarefas.md` (a gerar) | Micro: tarefas acionáveis do dia |

---

## Componentes-alvo

| Nome | Tipo | Depende de |
|------|------|------------|
| `feed/csv_feed.py` | Componente | `core/types.py` |
| `feed/mt5_feed.py` | Componente | `core/types.py`, MetaTrader5 |
| `strategy/base.py` | Componente | `core/types.py` |
| `broker/simulated.py` | Componente | `core/types.py` |
| `broker/mt5_broker.py` | Componente | `core/types.py`, MetaTrader5 |
| `execution/engine.py` | Orquestrador | feed + strategy + broker + `core/types.py` |
| `strategy/H102_strategy.py` | Componente | `strategy/base.py` |

---

## Fases

| Fase | Objetivo | Critério de "pronto" |
|------|----------|----------------------|
| **1** | **MT5 Broker** — conectar, enviar ordem de teste, ler posições | `broker/mt5_broker.py` conecta ao MT5, `mt5.initialize()` retorna True. Script de teste verifica símbolo WIN, consulta saldo, envia ordem demo. Conexão funcional. |
| **2** | **Feed CSV** — `feed/csv_feed.py` | `csv_feed.poll()` retorna `Bar` um por um. Teste: N chamadas retornam N candles na ordem correta. `step()` com exec_engine processa CSV igual ao BacktestEngine antigo. |
| **3** | **Strategy base + Simulated broker** | `strategy/base.py` com `Strategy(ABC)`. `broker/simulated.py` preenche ordens. H102 migrada pra strategy pura. |
| **4** | **Execution Engine** | `execution/engine.py` orquestra feed → strategy → broker. Mesmo resultado do BacktestEngine antigo pro H102. `run()` e `step()` funcionando. |
| **5** | **Demo/Real** | `feed/mt5_feed.py` (live) + `broker/mt5_broker.py`. Engine roda ao vivo. Exemplo: H102 emite signals, broker envia ordens demo, positions.json atualiza. |
| **6** | **Comparação 1:1** | Rodar H102 em BT (csv_feed) e Demo (mt5_feed) com a MESMA strategy. Comparar signals emitidos. Divergências = bugs no feed ou broker. |
| **7** | **Refino** | Testes unitários de cada componente. Validação cruzada BT vs MT5 < 5% divergência. AGENTS.md atualizado. |

---

## Tarefas por fase

### Fase 1 — MT5 Broker

| ID | Tipo | Tarefa | Origem | Saída |
|----|------|--------|--------|-------|
| T1 | Código | Implementar `broker/mt5_broker.py` | `specs/broker-mt5.zenspec.md` | `broker/mt5_broker.py` |
| T2 | Teste | Conectar MT5, verificar símbolo WIN, consultar saldo da conta | T1 | Terminal conectado |
| T3 | Teste | Enviar ordem de teste (demo), verificar retorno | T1 | Ordem enviada ou rejeitada com retorno válido |

### Fase 2 — Feed CSV

| ID | Tipo | Tarefa | Origem | Saída |
|----|------|--------|--------|-------|
| T4 | Código | Implementar `feed/csv_feed.py` | `specs/feed-csv.zenspec.md` | `feed/csv_feed.py` |
| T5 | Teste | Poll N bars, ver ordem e conteúdo | T4 | Teste automatizado |

### Fase 3 — Strategy + Simulated

| ID | Tipo | Tarefa | Origem | Saída |
|----|------|--------|--------|-------|
| T6 | Código | Implementar `strategy/base.py` | `specs/strategy-base.zenspec.md` | `strategy/base.py` |
| T7 | Código | Implementar `broker/simulated.py` | `specs/broker-simulated.zenspec.md` | `broker/simulated.py` |
| T8 | Código | Migrar H102 para `strategy/H102_strategy.py` (pura) | T6, spec strategy | `strategy/H102_strategy.py` |

### Fase 4 — Execution Engine

| ID | Tipo | Tarefa | Origem | Saída |
|----|------|--------|--------|-------|
| T9 | Código | Implementar `execution/engine.py` | `specs/execution-engine.zenspec.md` | `execution/engine.py` |
| T10 | Teste | Rodar H102 no engine com csv_feed + simulated_broker | T9, T4, T7 | Resultado igual ao BacktestEngine antigo |

### Fase 5 — Demo/Real

| ID | Tipo | Tarefa | Origem | Saída |
|----|------|--------|--------|-------|
| T11 | Código | Implementar `feed/mt5_feed.py` (live) | `specs/feed-mt5.zenspec.md` | `feed/mt5_feed.py` |
| T12 | Teste | Rodar engine ao vivo: mt5_feed + mt5_broker + H102 | T9, T11, T1 | Positions no MT5 demo |

### Fase 6 — Comparação 1:1

| ID | Tipo | Tarefa | Origem | Saída |
|----|------|--------|--------|-------|
| T13 | Código | Script de comparação BT vs Demo | T10, T12 | `scripts/comparar_bt_demo.py` |
| T14 | Doc | Relatório de divergências | T13 | Log em decisions.log |

### Fase 7 — Refino

| ID | Tipo | Tarefa | Origem | Saída |
|----|------|--------|--------|-------|
| T15 | Teste | Testes unitários: csv_feed, mt5_feed, simulated, engine | T4, T11, T7, T9 | `tests/` |
| T16 | Doc | AGENTS.md atualizado | todos | `AGENTS.md` |

---

## Regras de passagem de fase

| Fase | Pode encerrar quando |
|------|---------------------|
| 1 | MT5 conecta, `initialize()` retorna True, símbolo WIN selecionado, ordem demo enviada com retorno válido |
| 2 | `csv_feed.poll()` retorna Bar em sequência, sem pular ou repetir |
| 3 | Strategy pura implementada, broker simulado preenche ordens |
| 4 | Engine roda backtest completo com resultado idêntico ao BacktestEngine |
| 5 | Engine roda ao vivo, positions.json recebe dados do MT5 demo |
| 6 | Divergências BT vs Demo documentadas e < 5% |
| 7 | Testes verdes, AGENTS.md atualizado |

---

## Registro de mudanças

| ID | Origem | O que mudou | Tarefas afetadas |
|----|--------|-------------|-----------------|
| v2 | Revisão arquitetural | Feed/Strategy/Broker/Engine separados. Specs em `specs/`. Fases reordenadas. | Todas |
