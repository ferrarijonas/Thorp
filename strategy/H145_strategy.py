"""H145 — regime_vol<=0.5, delta_gap<=-2.5 → VENDA."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Signal, Direction
from strategy.markov_feature_set import MarkovFeatureSet

class H145Strategy(MarkovFeatureSet):
    def __init__(self):
        super().__init__("H145")

    def _check_conditions(self, f):
        if f["regime_vol"] <= 0.5 and f["delta_gap"] <= -2.5:
            return Signal(direction=Direction.VENDA, entry=0, stop=0,
                          target=0, timestamp=0, strategy_id=self._name)
        return None
