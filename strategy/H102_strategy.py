import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Bar, Signal, Direction
from strategy.base import Strategy

class H102Strategy(Strategy):
    def __init__(self):
        self._abertura_9h: float = 0
        self._condicao_ativa: bool = False

    def on_bar(self, bar: Bar) -> Signal | None:
        h, m = bar.time.hour, bar.time.minute
        if h == 9 and m == 0:
            self._abertura_9h = bar.open
        if h == 9 and m == 5 and self._abertura_9h:
            if bar.close < self._abertura_9h * 0.997:
                self._condicao_ativa = True
        if h == 9 and m == 6 and self._condicao_ativa:
            self._condicao_ativa = False
            return Signal(
                direction=Direction.LONG,
                entry=bar.open,
                stop=0,
                target=0,
                timestamp=bar.time,
                strategy_id="H102")
        return None

    def reset(self):
        self._abertura_9h = 0
        self._condicao_ativa = False
