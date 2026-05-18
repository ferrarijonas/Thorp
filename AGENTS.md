# Thorp — AGENTS.md

Sou a interface entre o LLM e o Thorp. Quem abrir o opencode nesta pasta me lê primeiro.

## Papel

- Entendo a arquitetura do Thorp (lendo este arquivo + código)
- Ajudo o usuário a criar/testar/executar estratégias
- Opero via CLI: python scripts/, git add/commit/push
- Tudo o que faço fica registrado

## Setup

```bash
pip install -r requirements.txt
```

Colocar `Historico_OHLC.csv` na raiz para BT completo.
Ou usar `Historico_AMOSTRA.csv` (100 linhas, já incluso) para testes.

## Arquitetura (visão do LLM)

```
feed/       → CsvFeed (CSV), Mt5Feed (MT5 ao vivo)
strategy/   → base.py + ExampleStrategy.py (template)
core/       → types, data, risk_guardian, calibrator
execution/  → engine (1 estratégia), manager (N estratégias), slippage
broker/     → simulated (BT), mt5_broker (demo/real)
scripts/    → run_bateria, run_demo, run_live_multi, comparar_execucao
state/      → runtime (calibration, session)
specs/      → contratos ZenSpec
```

### Pipeline de dados

```
CSV/MT5 → Feed → Engine.step() / on_bar(bar)
                    ├─ _reconcile() → sincroniza com MT5
                    ├─ check stop/target da posição atual
                    └─ strategy.on_bar(bar) → Signal
                         └─ RiskGuardian.process() → SL/TP
                         └─ broker.execute(signal) → Order → Position
```

### Fluxo multi-estratégia (StrategyManager)

```
Feed.poll() → mesma barra → Engine1.on_bar() → posição 1
                           → Engine2.on_bar() → posição 2
                           → Engine3.on_bar() → posição 3
                           → Dashboard + state/live/manager_state.json
```

## Comandos

### BT com slippage calibrado (default)
```bash
python scripts/run_bateria.py Example
python scripts/run_bateria.py --ideal Example   # sem slippage
```

### Demo ao vivo (1 estratégia)
```bash
python scripts/run_demo.py
```

### Multi-estratégia ao vivo (N engines, dashboard)
```bash
python scripts/run_live_multi.py
```

### Comparar execução (BT ideal vs BT+slippage vs Demo)
```bash
python scripts/comparar_execucao.py Example
```

### Calibrar slippage do MT5
```bash
python -c "from core.calibrator import Calibrator; c=Calibrator(); c.calibrar(); c.salvar()"
```

## Como criar uma estratégia

Criar `strategy/minha_strategy.py`:

```python
from strategy.base import Strategy
from core.types import Bar, Signal, Direction

class MinhaStrategy(Strategy):
    def __init__(self):
        self._name = "MINHA"   # identificador único para reconcile

    def on_bar(self, bar: Bar) -> Signal | None:
        if bar.close > bar.open:
            return Signal(direction=Direction.LONG, entry=bar.close,
                          stop=0, target=0, timestamp=bar.time,
                          strategy_id=self._name)
        return None

    def reset(self):
        pass
```

- `stop=0 target=0` → RiskGuardian preenche com P75 range + RR fixo
- `strategy_id` único → necessário para reconciliação com MT5

## Regras

- `state/decisions.log` registra cada decisão. Se não está lá, não aconteceu.
- RiskGuardian exige `min_stop_pts=250` em modo Demo/Real (mínimo do MT5).
- Em BT, slippage é aplicado pelo `SlippageModel` (calibrado do MT5).
- Em Demo/Real, `_reconcile()` sincroniza engine com posições reais do MT5 a cada step.
- `fetch_positions()` retorna posições do MT5 com ticket, direção, SL/TP.
