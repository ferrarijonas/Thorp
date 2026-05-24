from core.types import Signal, Order, OrderType, OrderStatus, Position

from broker.base import Broker

class SimulatedBroker(Broker):
    def __init__(self, cost: float = 10):
        self.cost = cost

    def execute(self, signal: Signal, volume: float = 1.0) -> Order:
        import uuid
        if signal is None:
            return Order(
                id="", signal=None, type=OrderType.MARKET,
                status=OrderStatus.REJECTED)
        return Order(
            id=str(uuid.uuid4())[:8],
            signal=signal,
            type=OrderType.MARKET,
            status=OrderStatus.FILLED,
            filled_price=signal.entry,
            filled_at=signal.timestamp)

    def fetch_positions(self) -> list[Position]:
        return []
