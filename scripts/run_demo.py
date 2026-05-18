import sys, os, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import ExecutionMode
from feed.mt5_feed import Mt5Feed
from strategy.H102_strategy import H102Strategy
from broker.mt5_broker import Mt5Broker
from execution.engine import ExecutionEngine

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")

def main():
    print("=== Thorp Demo — H102 com MT5 ao vivo ===")
    feed = Mt5Feed(symbol="WINM26", mode="live")
    strategy = H102Strategy()
    broker = Mt5Broker(mode=ExecutionMode.DEMO, symbol="WINM26", volume=1.0)
    engine = ExecutionEngine(feed, strategy, broker, mode=ExecutionMode.DEMO)
    try:
        engine.run_live(interval=30)
    except KeyboardInterrupt:
        print("\nParando...")
    finally:
        engine.close()
        print("Engine fechado.")

if __name__ == "__main__":
    main()
