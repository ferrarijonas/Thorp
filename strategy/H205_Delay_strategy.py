from strategy.base import Strategy
from core.types import Bar, Signal, Direction

class H205_DelayStrategy(Strategy):
    def __init__(self):
        self._name = "H205_Delay"
        self._count = 0

    def on_bar(self, bar: Bar) -> Signal | None:
        self._count += 1
        if self._count < 3:
            return None
        return Signal(direction=Direction.COMPRA, entry=bar.close,
                      stop=0, target=0,
                      timestamp=bar.time, strategy_id=self._name)

    def reset(self):
        self._count = 0
