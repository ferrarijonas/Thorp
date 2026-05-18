# Thorp — Eng Spec (v2)

## Intenção

Esta arquitetura existe para que **o agente IA** consiga **orquestrar trading com a mesma lógica em backtest, demo e real** sem precisar de **reescrever estratégias entre modos e sem acoplamento com fonte de dados ou broker.**

---

## Glossário

| Termo | Definição |
|-------|-----------|
| `Agente IA` | O orquestrador central (opencode). Lê `state/`, decide, chama scripts, escreve decisões. |
| `Feed` | Componente que produz `Bar`. Única diferença entre BT, demo e real. |
| `Strategy` | Classe que recebe `Bar` e retorna `Signal`. Não sabe de onde o bar veio. |
| `Broker` | Componente que executa `Signal` como ordem. Simulado (BT) ou MT5 (demo/real). |
| `Engine` | Orquestra feed → strategy → broker. Gerencia posição e stop/target. |
| `Bar` | Dado padronizado: open, high, low, close, volume, timestamp. |
| `state/` | Diretório de observabilidade. O agente lê daqui pra saber o estado. |

---

## Arquitetura

```
                    ┌───────────┐
                    │   Feed    │  ← CSV ou MT5, sempre produz Bar
                    └─────┬─────┘
                          │ Bar
                          ▼
                    ┌───────────┐
                    │  Strategy │  ← on_bar(bar) -> Signal | None
                    └─────┬─────┘
                          │ Signal
                          ▼
                    ┌───────────┐
                    │   Broker  │  ← simulated (BT) ou MT5 (demo/real)
                    └─────┬─────┘
                          │ Order
                          ▼
                    ┌───────────┐
                    │   Engine  │  ← gerencia posições, stop/target/time
                    └───────────┘
```

### A diferença entre modos é UMA linha:

| Modo | Feed | Broker | Engine |
|------|------|--------|--------|
| **BT** | `csv_feed` | `simulated_broker` | `execution_engine` |
| **Demo** | `mt5_feed` | `mt5_broker(mode="demo")` | `execution_engine` |
| **Real** | `mt5_feed` | `mt5_broker(mode="real")` | `execution_engine` |

A `Strategy` **nunca muda**. Ela só vê `on_bar(bar)`.

---

## Componentes

### `specs/` — contratos

| Arquivo | O que define |
|---------|-------------|
| `feed-csv.zenspec.md` | Contrato do `csv_feed`: poll() → Bar do DataFrame |
| `feed-mt5.zenspec.md` | Contrato do `mt5_feed`: poll() → Bar do MT5 |
| `broker-simulated.zenspec.md` | Contrato do `simulated_broker`: executa Signal → Order preenchida |
| `broker-mt5.zenspec.md` | Contrato do `mt5_broker`: executa Signal → Order via MT5 |
| `strategy-base.zenspec.md` | Contrato do `Strategy`: on_bar(bar) → Signal |
| `execution-engine.zenspec.md` | Contrato do `execution_engine`: orquestra feed → strategy → broker |

### `feed/` — fontes de dados (produzem Bar)

| Arquivo | Classe | Método principal |
|---------|--------|-----------------|
| `feed/csv_feed.py` | `CsvFeed` | `poll() -> Bar | None` |
| `feed/mt5_feed.py` | `Mt5Feed` | `poll() -> Bar | None`, `fetch(from, to) -> list[Bar]` |

### `strategy/` — lógica de trading

| Arquivo | Classe | Método principal |
|---------|--------|-----------------|
| `strategy/base.py` | `Strategy(ABC)` | `on_bar(bar) -> Signal | None` |
| `strategy/H102_strategy.py` | `H102Strategy` | Implementa regra H102 |

### `broker/` — execução de ordens

| Arquivo | Classe | Método principal |
|---------|--------|-----------------|
| `broker/simulated.py` | `SimulatedBroker` | `execute(signal) -> Order` |
| `broker/mt5_broker.py` | `Mt5Broker` | `execute(signal) -> Order`, `fetch_positions() -> list[Position]` |

### `execution/` — orquestração

| Arquivo | Classe | Método principal |
|---------|--------|-----------------|
| `execution/engine.py` | `ExecutionEngine` | `run() -> ExecutionResult`, `step() -> Bar`, `run_live(interval)` |

### `core/executor.py` — **legado**

Contém `BacktestEngine` e `StrategyLogic` da versão anterior. Serão substituídos pelo `execution_engine` e `strategy/base.py` conforme o sensei.

| Componente antigo | Novo componente | Quando migrar |
|-------------------|----------------|--------------|
| `StrategyLogic.on_bar(bar, position)` | `Strategy.on_bar(bar)` | Fase 3 |
| `BacktestEngine.run()` | `ExecutionEngine.run()` | Fase 4 |

A diferença principal: `StrategyLogic` recebia `position` como parâmetro; `Strategy` (nova) **não recebe** — a engine gerencia posição.

### `core/` — tipos e utilidades

| Arquivo | O que contém |
|---------|-------------|
| `core/types.py` | `Bar`, `Signal`, `Order`, `Position`, `Trade`, `Direction`, `OrderType`, `OrderStatus`, `ExecutionMode`, `ExecutionResult` |
| `core/data.py` | `load_csv()` — carrega CSV como DataFrame (usado pelo csv_feed) |
| `core/executor.py` | `BacktestEngine` (legado, será substituído pelo `execution_engine`) |

---

## Fluxo

### Macro (ciclo de vida de uma estratégia)

```
CSV ──→ csv_feed ──┐
                    ├──→ execution_engine.run() ──→ ExecutionResult (BT)
MT5 ──→ mt5_feed ──┘            │
                          ┌──────┴──────┐
                          ▼             ▼
                   simulated_broker   mt5_broker(demo/real)
```

### Micro (loop da engine)

```
feed.poll() → Bar
     │
     ▼
strategy.on_bar(bar) → Signal | None
     │
     ▼
broker.execute(signal) → Order
     │
     ▼
engine gerencia posição (stop/target/time)
     │
     ▼
engine registra Trade se fechou
     │
     ▼
feed.poll() → (próximo)
```

### Loop do agente IA

```
1. Lê state/session.json → sabe a fase
2. Lê state/health.json → MT5 ok?
3. Decide ação → escreve em decisions.log
4. Chama script → test_hipotese / run_live / radiografia
5. Lê resultado → atualiza state/
6. Volta ao passo 1
```

---

## Ciclo de vida (do sistema)

```
[INIT] → [RADIOGRAFIA] → [HIPOTESE] → [BT_VALIDATION] → [DEMO] → [REAL] → [MONITOR]
   ↑         ↑              ↑               ↑              ↑         ↑         │
   └─────────┴──────────────┴───────────────┴──────────────┴─────────┴─────────┘
```

### Estados

| Estado | O que acontece | Se falhar |
|--------|---------------|-----------|
| `INIT` | Verifica MT5, carrega specs, lê session | Se MT5 off → log + aguarda |
| `RADIOGRAFIA` | Gera radiografia dos dados | Se dados corrompidos → avisa |
| `HIPOTESE` | Gera/testa hipóteses H10x | p > 0.05 → MORTA, próxima |
| `BT_VALIDATION` | Roda strategy no execution_engine com csv_feed | Se erro → debug |
| `DEMO` | Mesma strategy com mt5_feed + mt5_broker(demo) | Se MT5 demo off → bt-only |
| `REAL` | Mesma strategy com mt5_broker(real) | Guardian monitora DD |
| `MONITOR` | Estratégia ativa, agente monitora | DD > max → STOP, volta HIPOTESE |

---

## Modelo de erros

| Situação | Comportamento |
|----------|--------------|
| MT5 não conectado | `mt5_feed` retorna None; `mt5_broker` retorna Order(REJECTED) |
| Dados incompletos (gap) | `csv_feed` só pula linhas; `mt5_feed` retorna None no gap |
| Broker rejeita ordem | Engine não cria posição, continua no próximo bar |
| Strategy lança exceção | Engine captura, loga, trata como None |
| Engine sem bar por muito tempo (live) | Pausa até novo bar chegar (poll interval) |
| Drawdown > max | Guardian (a implementar) bloqueia novas entradas |

---

## Decisões e alternativas descartadas

| Decisão | Alternativa | Motivo |
|---------|-------------|--------|
| Feed + Broker separados | Engine tudo-em-um | Substituir feed troca o modo sem tocar em mais nada |
| `on_bar(bar)` sem position | `on_bar(bar, position)` | Estratégia mais pura; quem gerencia posição é a engine |
| `Bar` como dataclass | dict, namedtuple | Tipagem, IDE auto-complete, semântica clara |
| specs em markdown | YAML, JSON | Legível por humanos e IAs, sem parser extra |

---

## Escopo fora

- Não cobre deploy multi-máquina, cluster, alta disponibilidade
- Não cobre estratégias multi-ativo
- Não cobre frontend web ou dashboard
- Não cobre tick data ou orderbook (no futuro, mas não agora)
- Não cobre otimização genética automática
- Não cobre integração com brokers fora do MT5
