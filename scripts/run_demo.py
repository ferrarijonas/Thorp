"""Demo single engine ao vivo com MT5.
Uso: python scripts/run_demo.py
Requer: MT5 aberto, conta demo, WINM26 no MarketWatch.
"""
import sys, os, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import ExecutionMode
from core.risk_guardian import RiskGuardian
from core.data import load_csv
from feed.mt5_feed import Mt5Feed
from strategy.example_strategy import ExampleStrategy
from broker.mt5_broker import Mt5Broker
from execution.engine import ExecutionEngine

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")

def main():
    print("=== Thorp Demo — ExampleStrategy com MT5 ao vivo ===")
    rg = RiskGuardian(capital=1_000_000, max_dd=999_999_999, min_stop_pts=250)
    try:
        rg.calibrate(load_csv())
    except FileNotFoundError:
        print("Aviso: CSV de calibracao nao encontrado, usando defaults")
    feed = Mt5Feed(symbol="WINM26", mode="live")
    strategy = ExampleStrategy()
    broker = Mt5Broker(mode=ExecutionMode.DEMO, symbol="WINM26", volume=1.0)
    engine = ExecutionEngine(feed, strategy, broker, mode=ExecutionMode.DEMO,
                              risk_guardian=rg)
    try:
        engine.run_live(interval=30)
    except KeyboardInterrupt:
        print("\nParando...")
    finally:
        engine.close()
        print("Engine fechado.")

if __name__ == "__main__":
    main()
