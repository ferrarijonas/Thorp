import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Bar, Signal, Direction
from strategy.base import Strategy

class H104Strategy(Strategy):
    def __init__(self):
        self._bar_count = 0

    def on_bar(self, bar: Bar) -> Signal | None:
        self._bar_count += 1
        direction = Direction.LONG if self._bar_count % 2 == 0 else Direction.SHORT
        return Signal(
            direction=direction,
            entry=bar.close,
            stop=0,
            target=0,
            timestamp=bar.time,
            strategy_id="H104")

    def reset(self):
        self._bar_count = 0
