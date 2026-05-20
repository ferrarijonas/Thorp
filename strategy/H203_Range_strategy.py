from strategy.base import Strategy
from core.types import Bar, Signal, Direction

class H203_RangeStrategy(Strategy):
    def __init__(self):
        self._name = "H203_Range"
        self._fired = False

    def on_bar(self, bar: Bar) -> Signal | None:
        if self._fired:
            return None
        rng = bar.high - bar.low
        if rng > 300:
            direcao = Direction.COMPRA
        elif rng < 100:
            direcao = Direction.VENDA
        else:
            return None
        self._fired = True
        return Signal(direction=direcao, entry=bar.close,
                      stop=0, target=0,
                      timestamp=bar.time, strategy_id=self._name)

    def reset(self):
        self._fired = False
