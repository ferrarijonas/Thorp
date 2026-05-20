"""Comparacao rapida: EA vs Python."""
import sys, os, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import numpy as np
from scipy import stats
from feed.csv_feed import CsvFeed
from broker.simulated import SimulatedBroker
from execution.engine import ExecutionEngine
from core.types import ExecutionMode, Direction
from core.risk_guardian import RiskGuardian
from core.data import load_csv
from core.types import Bar, Signal, Direction
from strategy.base import Strategy

class H141EA(Strategy):
    """Replica fiel do EA H141 v2.0"""
    def __init__(self, su=0.27, br=0.76, sl=120, tp=80):
        self._name = "H141_EA"
        self._su, self._br, self._sl, self._tp = su, br, sl, tp
        self._feat9 = None
        self._entrou = False

    def on_bar(self, bar):
        h, m = bar.time.hour, bar.time.minute
        if h == 9 and m == 0:
            O, H, L, C = bar.open, bar.high, bar.low, bar.close
            r = H - L
            self._feat9 = None
            if r > 0:
                self._feat9 = {"su": (H - max(O, C))/r, "br": abs(C - O)/r}
        if h == 9 and m == 1 and self._feat9 and not self._entrou:
            self._entrou = True
            f = self._feat9
            if f["su"] <= self._su and f["br"] <= self._br:
                return Signal(Direction.VENDA, bar.open, bar.open+self._sl,
                              bar.open-self._tp, bar.time, self._name)
        return None
    def reset(self):
        self._feat9 = None
        self._entrou = False

df = load_csv()

for label, su, br, sl, tp, cost in [
    ("Python rolling original", 0, 0, 0, 0, 10),
    ("EA v2.0 default (0.27/0.76 SL=120 TP=80)", 0.27, 0.76, 120, 80, 10),
    ("EA v2.0 com custo=0", 0.27, 0.76, 120, 80, 0),
    ("EA v2.0 SL=80 TP=80 (RR=1)", 0.27, 0.76, 80, 80, 10),
]:
    if label == "Python rolling original":
        # Roda H141 original
        from strategy.H141_strategy import H141Strategy
        feed = CsvFeed(); feed.reset()
        broker = SimulatedBroker(cost=10)
        strat = H141Strategy()
        rg = RiskGuardian(capital=99999, max_dd=99999)
        rg.calibrate(df)
        engine = ExecutionEngine(feed, strat, broker, ExecutionMode.BT, risk_guardian=rg, cost=10)
        engine.run()
    else:
        feed = CsvFeed(); feed.reset()
        broker = SimulatedBroker(cost=cost)
        strat = H141EA(su=su, br=br, sl=sl, tp=tp)
        rg = RiskGuardian(capital=99999, max_dd=99999)
        rg.calibrate(df)
        engine = ExecutionEngine(feed, strat, broker, ExecutionMode.BT, risk_guardian=rg, cost=cost)
        engine.run()

    ts = engine._trades
    pn = [t.pnl_points for t in ts]
    if not pn:
        print(f"{label}: 0 trades")
        continue
    a = np.array(pn)
    _, p = stats.ttest_1samp(a, 0)
    print(f"{label}: N={len(a):>3} media={a.mean():+6.1f} WR={(a>0).mean()*100:>4.1f}% p={p:.4f}")
