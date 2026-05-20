from strategy.base import Strategy
from core.types import Bar, Signal, Direction

class H201_LongStrategy(Strategy):
    def __init__(self):
        self._name = "H201_Long"
        self._fired = False

    def on_bar(self, bar: Bar) -> Signal | None:
        if self._fired:
            return None
        self._fired = True
        return Signal(direction=Direction.COMPRA, entry=bar.close,
                      stop=0, target=0,
                      timestamp=bar.time, strategy_id=self._name)

    def reset(self):
        self._fired = False
