"""Multi-strategy live demo — N engines simultaneas com MT5.
Uso: python scripts/run_live_multi.py
Requer: MT5 aberto, conta demo, WINM26 no MarketWatch.

Exemplo com 3 copias da ExampleStrategy (sonda alternada).
Cada engine tem seu proprio position, ticket MT5 e PnL.
"""
import sys, os, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import ExecutionMode
from core.calibrator import Calibrator
from feed.mt5_feed import Mt5Feed
from broker.mt5_broker import Mt5Broker
from strategy.example_strategy import ExampleStrategy
from execution.manager import StrategyManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S")

CAPITAL = 1_000_000
feed = Mt5Feed(symbol="WINM26", mode="live")
broker = Mt5Broker(mode=ExecutionMode.DEMO, symbol="WINM26", volume=1.0)

rg = Calibrator.criar_risk_guardian(capital=CAPITAL, max_dd=1_000_000_000)
slip = Calibrator.criar_slippage()

mgr = StrategyManager(feed, broker, mode=ExecutionMode.DEMO, capital=CAPITAL)

# Adiciona N copias da ExampleStrategy com IDs unicos
mgr.add(lambda: ExampleStrategy("S01"), risk_guardian=rg, slippage=slip)
mgr.add(lambda: ExampleStrategy("S02"), risk_guardian=rg, slippage=slip)
mgr.add(lambda: ExampleStrategy("S03"), risk_guardian=rg, slippage=slip)

try:
    mgr.run(interval=30)
except KeyboardInterrupt:
    mgr.stop()
