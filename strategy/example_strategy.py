"""Example strategy — template para criar novas estrategias.

A cada barra, alterna LONG/SHORT. stop=0 target=0 delega ao
RiskGuardian: SL=P75 range, TP=P50 range.

Uso:
    from strategy.example_strategy import ExampleStrategy
    strategy = ExampleStrategy()
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Bar, Signal, Direction
from strategy.base import Strategy


class ExampleStrategy(Strategy):
    def __init__(self, name: str = "EXAMPLE"):
        self._name = name
        self._count = 0

    def on_bar(self, bar: Bar) -> Signal | None:
        self._count += 1
        direction = Direction.LONG if self._count % 2 == 0 else Direction.SHORT
        return Signal(
            direction=direction,
            entry=bar.close,
            stop=0,
            target=0,
            timestamp=bar.time,
            strategy_id=self._name)

    def reset(self):
        self._count = 0
