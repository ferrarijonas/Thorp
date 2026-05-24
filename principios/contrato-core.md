# Contrato Core — Tipos e Regras

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
```

## Direction

```python
class Direction(Enum):
    COMPRA = 1
    VENDA = -1
    LONG = 1      # alias para COMPRA
    SHORT = -1    # alias para VENDA
```

COMPRA e VENDA são os nomes primários. LONG/SHORT são aliases.
No código interno (engine, broker, feeds), pode usar qualquer forma.
Na saída para o usuário (dashboard, logs, relatórios), usar COMPRA/VENDA.

## Signal

- Criado pela estratégia com `stop=0`, `target=0`, `max_exit_time=None`
- RiskGuardian e SlippageModel **retornam** Signal modificado (nunca mutam o original)
- Após processamento: stop, target, max_exit_time preenchidos
- O Signal original da estratégia nunca é alterado

```python
@dataclass
class Signal:
    direction: Direction
    entry: float
    stop: float
    target: float
    timestamp: datetime
    strategy_id: str
    size: int = 1
    max_exit_time: datetime | None = None
```

## Bar

- Sempre tem `time`, `open`, `high`, `low`, `close`, `volume`
- `high >= low` (validado pela fonte — feed respeita sempre)
- `time` é `datetime` com fuso horário local

```python
@dataclass
class Bar:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
```

## Order

- Ciclo de vida completo: `PENDING → FILLED | REJECTED | CANCELLED`
- Engine só cria `Position` se `Order.status == FILLED`
- Entry da Position = `Order.filled_price` (não `Signal.entry`)
- Uma ordem rejeitada tem status REJECTED, nunca None

```python
@dataclass
class Order:
    id: str
    signal: Signal
    type: OrderType
    status: OrderStatus
    filled_price: float = 0
    filled_at: datetime | None = None
```

## Position

- Representa uma posição em aberto
- Criada pela engine quando uma ordem é preenchida
- Fechada pela engine via SL, TP, time exit, ou reconcile externo
- `ticket` vincula à posição real no broker (vazio em BT)

```python
@dataclass
class Position:
    direction: Direction
    entry: float
    size: int
    opened_at: datetime
    strategy_id: str
    stop: float
    target: float
    closed: bool = False
    exit_price: float = 0
    closed_at: datetime | None = None
    pnl_points: float = 0
    max_exit_time: datetime | None = None
    ticket: str = ""
    _open_step: int = 0
```

## Trade

- Registro histórico de um trade completo (abertura + fechamento)
- Pode ter `rastro` com a sequência de OHLC entre entrada e saída

```python
@dataclass
class Trade:
    strategy_id: str
    direction: Direction
    entry: float
    exit: float
    pnl_points: float
    opened_at: datetime
    closed_at: datetime
    bars_held: int
    rastro: list | None = None
```

## ExecutionResult

- Gerado por `Analisador.resultado(trades) → ExecutionResult`
- Única fonte de verdade para métricas de backtest
- Todos os campos são computados, nunca setados manualmente

```python
@dataclass
class ExecutionResult:
    trades: list[Trade]
    total_pnl: float
    win_rate: float
    profit_factor: float
    total: int
    media: float
    p_valor: float
    metade1_media: float
    metade2_media: float
    metades_ok: bool
    sharpe: float = 0
    vantagem_pct: float = 0
    dd_max: float = 0
    mfe_medio: float = 0
    mae_medio: float = 0
```

## ExecutionMode

```python
class ExecutionMode(Enum):
    BT = "bt"
    DEMO = "demo"
    REAL = "real"
```

## OrderType

```python
class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
```

## OrderStatus

```python
class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
```
