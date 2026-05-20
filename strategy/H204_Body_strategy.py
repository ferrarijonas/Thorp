from strategy.base import Strategy
from core.types import Bar, Signal, Direction

class H204_BodyStrategy(Strategy):
    def __init__(self):
        self._name = "H204_Body"
        self._fired = False

    def on_bar(self, bar: Bar) -> Signal | None:
        if self._fired:
            return None
        body = abs(bar.close - bar.open)
        if body > 200:
            direcao = Direction.COMPRA
        elif body < 50:
            direcao = Direction.VENDA
        elif bar.close > bar.open:
            direcao = Direction.COMPRA
        else:
            return None
        self._fired = True
        return Signal(direction=direcao, entry=bar.close,
                      stop=0, target=0,
                      timestamp=bar.time, strategy_id=self._name)

    def reset(self):
        self._fired = False
