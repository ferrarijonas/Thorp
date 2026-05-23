from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

class Direction(Enum):
    COMPRA = 1
    VENDA = -1
    LONG = 1      # alias para COMPRA
    SHORT = -1    # alias para VENDA

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"

class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class ExecutionMode(Enum):
    BT = "bt"
    DEMO = "demo"
    REAL = "real"

@dataclass
class Bar:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

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

@dataclass
class Order:
    id: str
    signal: Signal
    type: OrderType
    status: OrderStatus
    filled_price: float = 0
    filled_at: datetime | None = None

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
