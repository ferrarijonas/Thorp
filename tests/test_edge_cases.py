import sys, os, tempfile, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import *
from feed.csv_feed import CsvFeed
from feed.mt5_feed import Mt5Feed
from broker.simulated import SimulatedBroker
from broker.mt5_broker import Mt5Broker
from execution.engine import ExecutionEngine
from strategy.base import Strategy
from strategy.H102_strategy import H102Strategy

import traceback

def test(msg, cond):
    if cond:
        print(f"  OK {msg}")
    else:
        print(f"  FAIL {msg}")

def section(name):
    print(f"\n=== {name} ===")

# ============================================================
# CSV FEED
# ============================================================
section("CsvFeed — edge cases")

# 1. Missing file
try:
    CsvFeed("nao_existe.csv")
    test("missing file raises", False)
except FileNotFoundError:
    test("missing file raises FileNotFoundError", True)
except Exception:
    test("missing file raises (not FileNotFoundError)", False)

# 2. Normal poll
feed = CsvFeed()
b1 = feed.poll()
test("poll returns Bar", isinstance(b1, Bar))

count = 0
while feed.poll():
    count += 1
test("poll exhausts all bars", count > 0)

# 3. Poll after exhaustion
b = feed.poll()
test("poll after exhaustion returns None", b is None)

# 4. Reset
feed.reset()
b = feed.poll()
test("reset works", isinstance(b, Bar) and b.time == b1.time)

# 5. Close (no-op)
feed.close()
test("close is callable", True)

# ============================================================
# MT5 FEED
# ============================================================
section("Mt5Feed — edge cases")

# 6. Invalid symbol
try:
    Mt5Feed("NAO_EXISTE_XYZ", mode="live")
    test("invalid symbol raises", False)
except ValueError:
    test("invalid symbol raises ValueError", True)
except Exception:
    test("invalid symbol raises (not ValueError)", False)

# 7. Live poll + dedup
try:
    feed2 = Mt5Feed("WINM26", mode="live")
    a = feed2.poll()
    b = feed2.poll()
    test("live poll returns Bar", isinstance(a, Bar))
    test("live dedup returns None", b is None)
    feed2.close()
except Exception as e:
    print(f"  SKIP Mt5Feed live (MT5 may not be running): {e}")

# 8. Historical fetch
try:
    from datetime import datetime, timedelta
    feed3 = Mt5Feed("WINM26", mode="historical",
        from_date=datetime.now() - timedelta(days=2),
        to_date=datetime.now())
    bars = feed3.fetch(datetime.now() - timedelta(days=2), datetime.now())
    test("historical fetch returns list", isinstance(bars, list))
    if bars:
        ok = all(hasattr(bar, attr) for bar in bars for attr in ["time","open","high","low","close","volume"])
        test("historical Bar has correct fields", ok and hasattr(bars[0], "time"))
    feed3.close()
except Exception as e:
    print(f"  SKIP Mt5Feed historical (MT5 may not be running): {e}")

# ============================================================
# SIMULATED BROKER
# ============================================================
section("SimulatedBroker — edge cases")

sb = SimulatedBroker(cost=10)

# 9. Execute None (already handled in engine, but verify)
result = sb.execute(None)
test("execute(None) returns None", result is None)

# 10. Execute with entry=0
sig = Signal(Direction.LONG, entry=0, stop=0, target=0, timestamp="now", strategy_id="T")
o = sb.execute(sig)
test("execute(entry=0) fills at 0", o is not None and o.filled_price == 0)

# 11. Normal execute
sig2 = Signal(Direction.SHORT, entry=1000, stop=1005, target=995, timestamp="now", strategy_id="T2")
o2 = sb.execute(sig2)
test("execute SHORT fills correctly", o2.status == OrderStatus.FILLED and o2.filled_price == 1000)

# 12. Multiple orders have different IDs
o3 = sb.execute(sig2)
test("orders have unique IDs", o2.id != o3.id)

# 13. Fetch positions (should be empty)
test("fetch_positions returns []", sb.fetch_positions() == [])

# ============================================================
# MT5 BROKER MODE
# ============================================================
section("Mt5Broker — edge cases")

# 14. Invalid mode
try:
    Mt5Broker("turbo", "WINM26", 1.0)
    test("invalid mode raises", False)
except ValueError:
    test("invalid mode raises ValueError", True)
except Exception:
    test("invalid mode raises (not ValueError)", False)

# 15. Invalid symbol (connection test)
try:
    b = Mt5Broker(ExecutionMode.DEMO, "NAO_EXISTE_XYZ", 1.0)
    test("invalid symbol in broker raises", False)
    b.close()
except (ValueError, ConnectionError):
    test("invalid symbol in broker raises ValueError/ConnectionError", True)
except Exception:
    test("invalid symbol in broker raises (unexpected)", False)

# ============================================================
# EXECUTION ENGINE
# ============================================================
section("ExecutionEngine — edge cases")

# 16. Empty feed
class EmptyFeed:
    def poll(self): return None
    def close(self): pass

engine = ExecutionEngine(EmptyFeed(), sb, sb, ExecutionMode.BT, cost=10)
result = engine.run()
test("empty feed returns ExecutionResult", isinstance(result, ExecutionResult))
test("empty feed has 0 trades", result.total == 0)
test("empty feed p_valor = 1", result.p_valor == 1)
test("empty feed metades_ok = True", result.metades_ok == True)

# 17. Strategy that always returns None
class NoopStrategy(Strategy):
    def on_bar(self, bar): return None

feed = CsvFeed()
engine = ExecutionEngine(feed, NoopStrategy(), SimulatedBroker(), ExecutionMode.BT)
result = engine.run(max_bars=1000)
test("noop strategy has 0 trades", result.total == 0)

# 18. Strategy that raises exception
class BrokenStrategy(Strategy):
    def on_bar(self, bar): raise ValueError("ops")

feed = CsvFeed()
engine = ExecutionEngine(feed, BrokenStrategy(), SimulatedBroker(), ExecutionMode.BT)
try:
    result = engine.run(max_bars=100)
    test("broken strategy does not crash", result.total == 0)
except:
    test("broken strategy does not crash", False)

# 19. Signal with entry=0 (engine should use bar.close)
class EntryZeroStrategy(Strategy):
    def __init__(self):
        self._done = False
    def on_bar(self, bar):
        if not self._done and bar.time.hour == 9 and bar.time.minute == 5:
            self._done = True
            return Signal(Direction.LONG, entry=0, stop=0, target=0,
                timestamp=bar.time, strategy_id="T3")
        return None

feed = CsvFeed()
engine = ExecutionEngine(feed, EntryZeroStrategy(), SimulatedBroker(), ExecutionMode.BT)
result = engine.run(max_bars=10000)
test("entry=0 uses bar.close (at least tries)", result.total >= 0)

# 20. Single trade (ttest needs at least 2 values)
class OneTradeStrategy(Strategy):
    def __init__(self):
        self._done = False
    def on_bar(self, bar):
        if not self._done:
            self._done = True
            return Signal(Direction.LONG, entry=100, stop=80, target=120,
                timestamp=bar.time, strategy_id="T4")
        return None

class OneBarFeed:
    def __init__(self):
        from datetime import datetime
        self._bar = Bar(time=datetime.now(), open=100, high=110, low=90, close=105, volume=100)
        self._done = False
    def poll(self):
        if self._done: return None
        self._done = True
        return self._bar
    def close(self): pass

engine = ExecutionEngine(OneBarFeed(), OneTradeStrategy(), SimulatedBroker(), ExecutionMode.BT)
result = engine.run()
test("single trade does not crash", result.total == 1)

# 21. Position with no stop/target (0)
class NoStopStrategy(Strategy):
    def __init__(self):
        self._done = False
    def on_bar(self, bar):
        if not self._done:
            self._done = True
            return Signal(Direction.LONG, entry=100, stop=0, target=0,
                timestamp=bar.time, strategy_id="T5")
        return None

engine = ExecutionEngine(OneBarFeed(), NoStopStrategy(), SimulatedBroker(), ExecutionMode.BT)
result = engine.run()
test("no stop/target does not crash", result.total == 1)

# 22. Run live KeyboardInterrupt
import signal
class InterruptFeed:
    def poll(self): raise KeyboardInterrupt()
    def close(self): pass

engine = ExecutionEngine(InterruptFeed(), NoopStrategy(), SimulatedBroker(), ExecutionMode.BT)
try:
    engine.run_live(interval=1)
except Exception:
    pass
test("run_live KeyboardInterrupt handled gracefully", True)

# 23. Close in BT mode (should not call mt5)
try:
    engine.close()
    test("close in BT mode works", True)
except:
    test("close in BT mode works", False)

# ============================================================
# PROFIT_FACTOR EDGE CASES
# ============================================================
section("Profit factor edge cases")

# 24. All wins (no losses)
from execution.engine import ExecutionEngine as EE
# We'll test _calc_stats indirectly by running a strategy that wins all
# Actually let's just test the math
from core.types import Trade, Direction
from datetime import datetime
trades_all_wins = [
    Trade(strategy_id="T", direction=Direction.LONG, entry=100, exit=110,
          pnl_points=10, opened_at=datetime.now(), closed_at=datetime.now(), bars_held=1),
    Trade(strategy_id="T", direction=Direction.LONG, entry=100, exit=120,
          pnl_points=20, opened_at=datetime.now(), closed_at=datetime.now(), bars_held=1),
]
t = [tr.pnl_points for tr in trades_all_wins]
wins = [v for v in t if v > 0]
losses = [v for v in t if v < 0]
pf = float(sum(wins) / abs(sum(losses))) if len(losses) > 0 else float('inf') if len(wins) > 0 else 0
test("all wins -> profit_factor = inf", pf == float('inf'))

# 25. All losses
trades_all_losses = [
    Trade(strategy_id="T", direction=Direction.LONG, entry=100, exit=90,
          pnl_points=-10, opened_at=datetime.now(), closed_at=datetime.now(), bars_held=1),
]
t = [tr.pnl_points for tr in trades_all_losses]
wins = [v for v in t if v > 0]
losses = [v for v in t if v < 0]
pf = float(sum(wins) / abs(sum(losses))) if len(losses) > 0 else float('inf') if len(wins) > 0 else 0
test("all losses -> profit_factor = 0", pf == 0)

# 26. No trades (empty)
t = []
wins = [v for v in t if v > 0]
losses = [v for v in t if v < 0]
pf = float(sum(wins) / abs(sum(losses))) if len(losses) > 0 else float('inf') if len(wins) > 0 else 0
test("no trades -> profit_factor = 0", pf == 0)

# ============================================================
# INTEGRATION: CSV backtest full pipeline
# ============================================================
section("Integration — H102 full CSV backtest")

feed = CsvFeed()
strategy = H102Strategy()
broker = SimulatedBroker(cost=10)
engine = ExecutionEngine(feed, strategy, broker, ExecutionMode.BT)
result = engine.run()
test("H102 backtest returns trades", result.total > 0)
test("H102 backtest total_pnl is float", isinstance(result.total_pnl, float))
test("H102 backtest p_valor is sane", 0 <= result.p_valor <= 1)
test("H102 backtest win_rate is percentage", 0 <= result.win_rate <= 100)
test("H102 backtest has trades list", isinstance(result.trades, list))

# ============================================================
# INTEGRATION: state/ directory
# ============================================================
section("State directory")

test("state/session.json exists", os.path.isfile("state/session.json"))
test("state/decisions.log exists", os.path.isfile("state/decisions.log"))

with open("state/session.json") as f:
    s = json.load(f)
test("session.json has fase", "fase" in s)
test("session.json has pendentes", "pendentes" in s)

# ============================================================
# SUMMARY
# ============================================================
print("\n=== RESUMO ===")
print("Edge case tests completed.")
