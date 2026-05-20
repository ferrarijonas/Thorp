from strategy.base import Strategy
from core.types import Bar, Signal, Direction

class H202_ShortStrategy(Strategy):
    def __init__(self):
        self._name = "H202_Short"
        self._fired = False

    def on_bar(self, bar: Bar) -> Signal | None:
        if self._fired:
            return None
        self._fired = True
        return Signal(direction=Direction.VENDA, entry=bar.close,
                      stop=0, target=0,
                      timestamp=bar.time, strategy_id=self._name)

    def reset(self):
        self._fired = False
