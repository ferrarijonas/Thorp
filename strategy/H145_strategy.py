"""H145 — regime_vol<=0.5, delta_gap<=-2.5 → VENDA."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Direction
from strategy.markov_feature_set import MarkovFeatureSet

class H145Strategy(MarkovFeatureSet):
    def __init__(self):
        super().__init__("H145")

    def _check_conditions(self, f, bar):
        if f["regime_vol"] <= 0.5 and f["delta_gap"] <= -2.5:
            return Direction.VENDA
        return None
