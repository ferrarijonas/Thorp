import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Bar, Signal, Direction
from strategy.base import Strategy

class H103Strategy(Strategy):
    def __init__(self):
        self._ultimo_close = None
        self._entrou_hoje = False
        self._dia_atual = None

    def on_bar(self, bar: Bar) -> Signal | None:
        data = bar.time.date()
        if self._dia_atual is None or data != self._dia_atual:
            self._dia_atual = data
            self._entrou_hoje = False
        h, m = bar.time.hour, bar.time.minute
        if h == 9 and m == 0 and self._ultimo_close and not self._entrou_hoje:
            gap = (bar.open - self._ultimo_close) / self._ultimo_close
            if abs(gap) > 0.003:
                self._entrou_hoje = True
                direcao = Direction.LONG if gap > 0 else Direction.SHORT
                # stop=0 target=0 → RiskManager preenche
                return Signal(direction=direcao, entry=bar.open,
                    stop=0, target=0, timestamp=bar.time,
                    strategy_id="H103")
        self._ultimo_close = bar.close
        return None

    def reset(self):
        self._ultimo_close = None
        self._entrou_hoje = False
        self._dia_atual = None
