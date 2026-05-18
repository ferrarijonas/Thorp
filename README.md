# Thorp

Sistema de trading algorítmico para **WIN M1** (mini índice B3) com backtest, calibração de slippage via MT5 e execução multi-estratégia ao vivo.

## Estrutura

```
thorp/
├── broker/         → SimulatedBroker + Mt5Broker
├── core/           → types, data, risk_guardian, calibrator
├── execution/      → engine, manager (multi-strategy), slippage
├── feed/           → CsvFeed, Mt5Feed
├── strategy/       → base.py + ExampleStrategy
├── scripts/        → pipeline, demo, comparacao, multi-live
├── specs/          → contratos ZenSpec
└── state/          → runtime (sessao, calibracao)
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

## Uso

### Backtest com slippage calibrado

```bash
python scripts/run_bateria.py --ideal Example   # sem slippage
python scripts/run_bateria.py Example            # com slippage real do MT5
```

### Demo ao vivo (single engine)

```bash
python scripts/run_demo.py
```

### Multi-estratégia ao vivo (N engines)

```bash
python scripts/run_live_multi.py
```

Dashboard atualiza a cada 30s: posições, PnL, trades por engine.

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
