"""H147 — order_flow>-18792.5, range_9<=222.5, shadow_up<=0.1111 → VENDA."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Signal, Direction
from strategy.markov_feature_set import MarkovFeatureSet

class H147Strategy(MarkovFeatureSet):
    def __init__(self):
        super().__init__("H147")

    def _check_conditions(self, f):
        if (f["order_flow"] > -18792.5 and f["range_9"] <= 222.5
                and f["shadow_up"] <= 0.1111):
            return Signal(direction=Direction.VENDA, entry=0, stop=0,
                          target=0, timestamp=0, strategy_id=self._name)
        return None
