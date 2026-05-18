import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Signal, Order, OrderType, OrderStatus, Position

class SimulatedBroker:
    def __init__(self, cost: float = 10):
        self.cost = cost

    def execute(self, signal: Signal) -> Order | None:
        if signal is None:
            return None
        import uuid
        return Order(
            id=str(uuid.uuid4())[:8],
            signal=signal,
            type=OrderType.MARKET,
            status=OrderStatus.FILLED,
            filled_price=signal.entry,
            filled_at=signal.timestamp)

    def fetch_positions(self) -> list[Position]:
        return []
