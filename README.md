# Thorp

Sistema de trading algorítmico para **WIN M1** (mini índice B3) com backtest, calibração de slippage via MT5 e execução multi-estratégia ao vivo.

Projetado para trabalhar com **LLMs via opencode**: instale, abra o opencode na pasta, e o agente AI já entende a arquitetura, comandos e pipeline — graças ao `AGENTS.md` que descreve tudo pro LLM.

## Arquitetura

```
┌──────────────────────────────────────────────────────────────────┐
│                        Task Scheduler                             │
│              (reinicia em ~30s se o processo morrer)               │
└──────────────────────────┬───────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────────┐
│                    thorp_247.ps1 (launcher)                       │
│              Start-Process python run_bot.py --terminal xp        │
└──────────────────────────┬───────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────────┐
│                       run_bot.py                                  │
│                                                                   │
│  1. mt5.initialize(path)  ← inicia/usa terminal existente         │
│  2. Carrega RiskGuardian (P50/P75 do CSV, cacheado em JSON)       │
│  3. Instancia N engines (H140, H141, H142...)                     │
│  4. Loop 30s: poll M1 → on_bar() → reconcile → positions.json    │
│  5. Se morre, Task Scheduler reinicia automaticamente             │
└──┬───────────────┬───────────────┬───────────────────────────────┘
   │               │               │
   ▼               ▼               ▼
┌─────────┐  ┌─────────┐  ┌─────────┐
│ Engine 1│  │ Engine 2│  │ Engine N│
│  H14x   │  │  H14y   │  │  H14z   │
└────┬────┘  └────┬────┘  └────┬────┘
     │            │            │
     ▼            ▼            ▼
┌──────────────────────────────────────────────────────────────────┐
│                       Mt5Broker                                   │
│               order_send(), positions_get()                       │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    MetaTrader 5 (DEMO/REAL)                       │
│                    WINM26 M1 · Conta XP                          │
└──────────────────────────────────────────────────────────────────┘
```

### Pipeline de dados (ao vivo)

```
MT5 M1 bar → run_bot.poll()
                └─ engine.on_bar(bar)
                     ├─ _reconcile() → sincroniza com MT5
                     ├─ check stop/target da posição atual
                     └─ strategy.on_bar(bar) → Signal
                          └─ RiskGuardian.process()
                               ├─ SL = P75 do range (hora ou minuto)
                               ├─ TP = P50 do range
                               └─ check horário, drawdown, min_stop
                          └─ Mt5Broker.execute(signal) → Order → Position
```

### Estrutura de diretórios

```
thorp/
├── broker/         → SimulatedBroker + Mt5Broker
├── core/           → types, data, risk_guardian, calibrator, containers
├── execution/      → engine (1 estratégia), slippage (só BT)
├── feed/           → CsvFeed, Mt5Feed
├── strategy/       → base.py + Hxxx_strategy.py (estratégias vivas)
├── scripts/        → avaliar_hipotese, run_bot
├── principios/     → sl-tp.md, ea-checklist.md (filosofia e regras)
├── hipoteses/      → CATALOGO.json, ATIVAS/, EXPLORADAS/, DADOS/
└── state/          → session.json, decisions.log, positions.json, logs/
```

## Setup

```bash
pip install -r requirements.txt
```

### Dados

- **Completo (331k candles):** coloque `Historico_OHLC.csv` na raiz do projeto (formato: `datetime,open,high,low,close,volume`, encoding utf-16, sem cabeçalho)
- **Amostra (100 linhas):** `Historico_AMOSTRA.csv` já incluso — funciona para testes

### MT5 ao vivo

1. Abra o MetaTrader 5 com conta demo
2. Certifique-se que `WINM26` está no MarketWatch
3. Ative em **Ferramentas → Opções → Expert Advisors**: "Allow Automated Trading"

## Uso com AI (opencode)

```bash
pip install opencode
opencode
```

O LLM lê `AGENTS.md` automaticamente e já sabe tudo sobre a arquitetura, comandos e pipeline. Basta pedir: "roda backtest", "cria estratégia nova", "abre demo ao vivo".

## Uso manual

### Backtest

```bash
python scripts/avaliar_hipotese.py Hxxx                 # BT + diagnóstico completo
python scripts/avaliar_hipotese.py H102 H103 H104         # múltiplas hipóteses
```

Se houver calibração de slippage (`state/slippage_calibration.json`), inclui automaticamente a seção CUSTO REAL (BT com custo de execução do MT5).

### Bot 24/7 (multi-estratégia ao vivo)

```bash
python scripts/run_bot.py --terminal xp
```

Lê `state/bot_config.json` para configurar terminais, estratégias, volumes e capital.
Task Scheduler + `thorp_247.ps1` garantem restart automático se o processo morrer.

As engines rodam em loop de 30s: poll M1 → on_bar() → reconciliação com MT5.

### Calibrar slippage

```bash
python -c "from core.calibrator import Calibrator; c=Calibrator(); c.calibrar(); c.salvar()"
```

## Criar uma estratégia

```python
from strategy.base import Strategy
from core.types import Bar, Signal, Direction

class MinhaEstrategia(Strategy):
    def __init__(self):
        self._count = 0

    def on_bar(self, bar: Bar) -> Signal | None:
        # stop=0 target=0 → RiskGuardian preenche com P75 range + RR
        if bar.close > bar.open:
            return Signal(direction=Direction.LONG, entry=bar.close,
                          stop=0, target=0, timestamp=bar.time,
                          strategy_id="MINHA")
        return None

    def reset(self):
        self._count = 0
```

## Requisitos

- Python 3.10+
- MetaTrader 5 (para dados ao vivo)
- Windows (MT5 depende de Win32)

## Licença

MIT
