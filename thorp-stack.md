# Thorp — Stack Spec (v2)

## Intenção

Esta stack existe para que **o agente IA** consiga **orquestrar trading na B3 com o mínimo de dependências e máxima observabilidade** sem precisar de **compiladores, containers, banco de dados ou serviços externos.**

---

## Restrições

| Restrição | Imposta por | Consequência |
|-----------|-------------|-------------|
| Windows x86_64 | Ambiente do usuário | Scripts PowerShell compatíveis. Sem `fork()`, sem signals UNIX. |
| Python 3.13 | Ambiente já configurado | Pacotes compatíveis com 3.13. |
| MetaTrader 5 instalado | Fonte de dados + execução | `MetaTrader5` Python lib obrigatória. Terminal precisa estar aberto. |
| Sem Rust toolchain | Usuário não tem Rust | Sem NautilusTrader, sem compilação PyO3. Tudo em Python puro. |
| Sem Docker | Usuário não tem Docker | Tudo local, sem containers. |
| Sem acesso root/admin | Usuário padrão | `pip install --user`. Sem serviços system-wide. |
| Sem banco de dados | Decisão arquitetural | Estado em JSON filesystem. |
| WIN M1 como ativo único | Foco do projeto | Símbolo fixo, timeframe fixo. |

---

## Decisões

| Categoria | Decisão | Alternativa | Motivo |
|-----------|---------|-------------|--------|
| Linguagem | Python 3.13 | MQL5, Rust, C# | Já instalado, ecossistema de dados |
| Data feed | MetaTrader5 | Databento, B3 API | Já instalado, zero config |
| Data handling | pandas + numpy | Polars, cuDF | Já instalados |
| Estatística | scipy | statsmodels | Já instalado |
| Serialização | JSON | pickle, msgpack | Legível pelo agente IA |
| Estado | JSON em state/ | SQLite, Redis | Observabilidade imediata |
| Execução | MetaTrader5.order_send() | API de corretora | MT5 já conectado |
| Feed CSV | `feed/csv_feed.py` | Inline em cada script | Centraliza e padroniza |
| Feed MT5 | `feed/mt5_feed.py` | — | Único adapter pro MT5 |
| Broker simulado | `broker/simulated.py` | — | Backtest sem MT5 |
| Broker MT5 | `broker/mt5_broker.py` | — | Demo/Real |
| Engine | `execution/engine.py` | BacktestEngine antigo | Orquestra feed → strategy → broker |

---

## Dependências

### Core (já instaladas)

| Pacote | Versão | Papel |
|--------|--------|-------|
| `MetaTrader5` | 5.0.5735 | Conexão com terminal MT5 |
| `pandas` | ≥2.0 | DataFrames OHLC |
| `numpy` | ≥1.24 | Operações vetoriais |
| `scipy` | ≥1.11 | Testes estatísticos |

### Opcionais

| Pacote | Versão | Papel | Dev-only? |
|--------|--------|-------|-----------|
| `pytest` | ≥8.0 | Testes unitários | Sim |

---

## Scripts

| Comando | O que faz |
|---------|-----------|
| `python scripts/test_hipotese.py H102` | Testa hipótese H102 |
| `python scripts/radiografia.py` | Gera radiografia |
| `python scripts/status.py` | Atualiza state/ |
| `python -m pytest tests/` | Roda testes |

---

## Pastas

```
thorp/
├── AGENTS.md                        ← Constituição do agente
├── thorp-concept.md                 ← Concept Spec
├── thorp-engineering.md             ← Eng Spec (v2)
├── thorp-stack.md                   ← Stack Spec (v2)
├── thorp-sensei.md                  ← Sensei (plano de execução)
│
├── specs/
│   ├── feed-csv.zenspec.md
│   ├── feed-mt5.zenspec.md
│   ├── broker-simulated.zenspec.md
│   ├── broker-mt5.zenspec.md
│   ├── strategy-base.zenspec.md
│   └── execution-engine.zenspec.md
│
├── core/
│   ├── __init__.py
│   ├── types.py                    ← Bar, Signal, Order, Position, Trade, Direction, OrderType, OrderStatus, ExecutionMode, ExecutionResult
│   ├── data.py                     ← load_csv() (usado pelo csv_feed)
│   └── executor.py                 ← ExecutionResult, BacktestEngine (legado)
│
├── feed/
│   ├── __init__.py
│   ├── csv_feed.py                 ← poll() → Bar | None do CSV
│   └── mt5_feed.py                 ← poll() → Bar | None do MT5
│
├── strategy/
│   ├── __init__.py
│   ├── base.py                     ← Strategy(ABC): on_bar(bar) -> Signal
│   └── H102_strategy.py           ← Exemplo concreto
│
├── broker/
│   ├── __init__.py
│   ├── simulated.py                ← SimulatedBroker: preenche ordens no backtest
│   └── mt5_broker.py              ← Mt5Broker: envia ordens ao MT5
│
├── execution/
│   ├── __init__.py
│   └── engine.py                   ← ExecutionEngine: feed → strategy → broker
│
├── scripts/                        ← Scripts chamados pelo agente
│   ├── test_hipotese.py
│   ├── radiografia.py
│   └── status.py
│
├── state/                          ← Observabilidade
│   ├── session.json
│   ├── decisions.log
│   └── health.json
│
├── data/                           ← Dados OHLC
├── radiografia/                    ← Radiografias
├── hipoteses/                      ← Hipóteses H101–H120
├── strategies/                     ← Estratégias (legado)
├── reports/
├── tests/
└── cmds/                           ← Comandos do agente (opcional)
```

---

## Escopo fora

| Tecnologia | Por que não |
|------------|-------------|
| Rust/Cargo | Sem toolchain |
| Docker | Sem Docker |
| SQLite/Redis | Filesystem > observável |
| FastAPI/HTTP | Zero necessidade |
| TypeScript/Node | Sem frontend |
| MQL5 puro | Agente não escreve MQL5 |
| Matplotlib | Só gráficos, não essencial agora |
