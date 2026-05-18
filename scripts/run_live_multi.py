"""Multi-strategy live demo — N estrategias simultaneas."""
import sys, os, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import ExecutionMode, Bar, Signal, Direction
from strategy.base import Strategy
from core.calibrator import Calibrator
from feed.mt5_feed import Mt5Feed
from broker.mt5_broker import Mt5Broker
from execution.manager import StrategyManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S")

CAPITAL_TOTAL = 1_000_000

# Fabrica de estrategias com ID unico
class ProbeStrategy(Strategy):
    def __init__(self, name: str = "PROBE"):
        self._name = name
        self._count = 0

    def on_bar(self, bar: Bar) -> Signal | None:
        self._count += 1
        direcao = Direction.LONG if self._count % 2 == 0 else Direction.SHORT
        return Signal(direction=direcao, entry=bar.close, stop=0, target=0,
                      timestamp=bar.time, strategy_id=self._name)

    def reset(self):
        self._count = 0

feed = Mt5Feed(symbol="WINM26", mode="live")
broker = Mt5Broker(mode=ExecutionMode.DEMO, symbol="WINM26", volume=1.0)
rg = Calibrator.criar_risk_guardian(capital=CAPITAL_TOTAL, max_dd=1_000_000_000)
slip = Calibrator.criar_slippage()

mgr = StrategyManager(feed, broker, mode=ExecutionMode.DEMO, capital=CAPITAL_TOTAL)

# 3 estrategias independentes — cada uma com strategy_id unico
mgr.add(lambda: ProbeStrategy("S01"), risk_guardian=rg, slippage=slip)
mgr.add(lambda: ProbeStrategy("S02"), risk_guardian=rg, slippage=slip)
mgr.add(lambda: ProbeStrategy("S03"), risk_guardian=rg, slippage=slip)

try:
    mgr.run(interval=30)
except KeyboardInterrupt:
    mgr.stop()
