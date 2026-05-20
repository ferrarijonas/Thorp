"""H146 — gap_rel_range<=5.7182, fragilidade>0.0714, delta_range>112.5 → VENDA."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Signal, Direction
from strategy.markov_feature_set import MarkovFeatureSet

class H146Strategy(MarkovFeatureSet):
    def __init__(self):
        super().__init__("H146")

    def _check_conditions(self, f):
        if (f["gap_rel_range"] <= 5.7182 and f["fragilidade"] > 0.0714
                and f["delta_range"] > 112.5):
            return Signal(direction=Direction.VENDA, entry=0, stop=0,
                          target=0, timestamp=0, strategy_id=self._name)
        return None
