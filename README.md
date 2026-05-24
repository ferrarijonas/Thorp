# Thorp

Sistema modular de trading algorítmico para a **B3** (Bolsa de Valores do Brasil), com pipeline completo de dados → feature engineering → backtest → validação estatística → execução ao vivo.

Projetado para ser operado por **agentes LLM** via CLI: o `AGENTS.md` descreve a arquitetura, contratos e comandos para que qualquer agente entenda o sistema em segundos.

---

## Arquitetura

O Thorp segue o padrão **Feed → Engine → Broker** com injeção de dependência e contratos formais (ABCs):

```
OHLC CSV / MT5 → Feed.poll()
                    └─ ExecutionEngine.on_bar(bar)
                         ├─ Strategy.on_bar(bar) → Signal
                         ├─ RiskGuardian.process(signal) → stop/target
                         ├─ SlippageModel.on_entry(signal) → slippage
                         └─ Broker.execute(signal) → Order → Position
```

### Componentes

| Camada | Módulo | Responsabilidade |
|--------|--------|------------------|
| **Feed** | `feed/base.py` → ABC `Feed` | Fonte de dados OHLC. `CsvFeed` para CSV, `Mt5Feed` para MT5 ao vivo. |
| **Strategy** | `strategy/base.py` → ABC `Strategy` | Lógica de entrada. `on_bar(bar)` → `Signal` ou `None`. |
| **Engine** | `execution/engine.py` | Orquestra feed + estratégia + broker. Gerencia posição, SL/TP, rastro de trades. Configurável via `EngineConfig`. |
| **RiskGuardian** | `core/risk_guardian.py` | Define SL/TP como containers estatísticos (P75/P50 do range). Não muta o Signal original. |
| **SlippageModel** | `execution/slippage.py` | Simula custo de execução em BT (spread + slip). Retorna cópia, não muta. |
| **Broker** | `broker/base.py` → ABC `Broker` | Execução de ordens. `SimulatedBroker` para BT, `Mt5Broker` para Demo/Real. |
| **Analisador** | `core/analisador.py` | Métricas de performance: p-valor, MFE/MAE, decaimento temporal, re-simulação de containers. |

### Pipeline de dados

```
CSV/MT5
  → Feed.poll()                    # extração
  → Engine.on_bar()                # transformação (features + regras)
  → RiskGuardian.process()         # SL/TP estatísticos
  → Broker.execute()               # carga (ordem no mercado)
  → Analisador.resultado()         # análise (p-valor, metades, MFE/MAE)
```

### Contratos formais

Todo componente tem um **ABC** (Abstract Base Class) e um **spec em `principios/`**:

- `Feed`: `poll()`, `reset()`, `close()`
- `Broker`: `execute()`, `fetch_positions()`, `get_exit_info()`
- `Strategy`: `on_bar()`
- `EngineConfig`: dataclass com parâmetros de execução
- `RiskGuardian`: `process()` retorna cópia (não muta entrada)

Ver `principios/contrato-*.md` para a especificação completa de cada interface.

---

## Setup

```bash
pip install -e .
```

### Dados

- **Completo:** coloque `Historico_OHLC.csv` na raiz (`datetime,open,high,low,close,volume`, encoding utf-16, sem cabeçalho)
- **Amostra:** `Historico_AMOSTRA.csv` já incluso (100 linhas) para testes

### Conexão ao mercado

- MetaTrader 5 com conta Demo/Real na B3
- Ative "Allow Automated Trading" nas opções do terminal
- Ver scripts/CATALOGO.md para calibrar slippage

---

## Uso com agentes (opencode)

```bash
pip install opencode
opencode
```

O agente lê `AGENTS.md` automaticamente. Comandos disponíveis:

### Backtest + diagnóstico completo

```bash
python scripts/avaliar_hipotese.py H142
```

Entrega 5 seções por hipótese:

| Seção | Descrição |
|-------|-----------|
| ANOMALIA | MFE/MAE/assimetria — edge puro sem container |
| ENTRADA | Vantagem % por ponto de entrada (abertura/fechamento/máxima/mínima) |
| TEMPO PÓS-ENTRADA | Decaimento do edge barra a barra |
| CONTÊINER | 5 TPs × 2 convenções (pior/melhor caso) |
| CUSTO REAL | BT com slippage calibrado (se disponível) |

Veredito automático: `ROBUSTO` / `SINAL OK` / `MORTA`.

### Bot multi-estratégia

```bash
python scripts/run_bot.py --terminal xp
```

Lê `state/bot_config.json`. Suporta restart automático via Task Scheduler + `thorp_247.ps1`.

### Catálogo de scripts

```bash
# scripts/CATALOGO.md lista todos os scripts e seu propósito
```

---

## Estrutura de diretórios

```
thorp/
├── core/           → types, data, risk_guardian, analisador, calibrator, containers, persistence
├── execution/      → engine (orquestrador), config (EngineConfig), slippage, manager (dashboard)
├── broker/         → base.py (ABC), simulated (BT), mt5_broker (Demo/Real)
├── feed/           → base.py (ABC), csv_feed, mt5_feed
├── strategy/       → base.py (ABC), Hxxx_strategy.py (estratégias vivas), *.mq5 (EAs)
├── scripts/        → avaliar_hipotese, run_bot, CATALOGO.md
├── principios/     → sl-tp.md, ea-checklist.md, contrato-*.md (9 specs)
├── hipoteses/      → CATALOGO.json, ATIVAS/, EXPLORADAS/, DADOS/
├── state/          → session.json, decisions.log, containers_calibration.json, slippage_calibration.json
├── tests/          → test_edge_cases.py
├── AGENTS.md       → instruções para LLMs
├── pyproject.toml  → pacote pip instalável
```

---

## Criar uma estratégia

```python
from strategy.base import Strategy
from core.types import Bar, Signal, Direction

class MinhaEstrategia(Strategy):
    def __init__(self):
        self._name = "MINHA"   # identificador único
        self._count = 0

    def on_bar(self, bar: Bar) -> Signal | None:
        # stop=0 target=0 → RiskGuardian preenche com P75/P50
        if bar.close > bar.open:
            return Signal(direction=Direction.COMPRA, entry=bar.close,
                          stop=0, target=0, timestamp=bar.time,
                          strategy_id=self._name)
        return None

    def reset(self):
        self._count = 0
```

- `Signal` nunca é mutado por RiskGuardian ou SlippageModel — ambos retornam cópias
- stop/target podem ser definidos pela estratégia (substitui o container)
- max_exit_time opcional (padrão: 17h)

---

## Boas práticas

- ✅ **Interfaces formais** — ABCs para Feed, Broker, Strategy. Injeção de dependência.
- ✅ **Imutabilidade** — Signal nunca é mutado por processadores. Cópias via `dataclasses.replace()`.
- ✅ **Config objects** — `EngineConfig` separa configuração de instanciação.
- ✅ **Separação de responsabilidades** — Persistência externa à engine (`core/persistence.py`).
- ✅ **Pacote pip** — `pip install -e .`, sem `sys.path.insert`.
- ✅ **Especificações** — 9 contratos em `principios/` documentando cada interface.
- ✅ **Pipeline de dados** — Extração (Feed) → Transformação (Strategy + RiskGuardian) → Carga (Broker).
- ✅ **Métricas estatísticas** — p-valor (teste t), MFE/MAE, decaimento temporal, re-simulação Monte Carlo, validação walk-forward, correção de testes múltiplos (Bonferroni, FDR).
- ✅ **Rastreabilidade** — `state/decisions.log` registra toda decisão. Histórico de ordens disponível.

Dados de entrada: CSV OHLC com qualquer granularidade — o mesmo pipeline serve para outros mercados, ativos e intervalos.

---

## Licença

MIT
