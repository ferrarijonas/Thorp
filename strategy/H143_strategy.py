"""H143 — vol_9>4106, range_9_rank>0.525, shadow_dn>0.4535 → VENDA."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Signal, Direction
from strategy.markov_feature_set import MarkovFeatureSet

class H143Strategy(MarkovFeatureSet):
    def __init__(self):
        super().__init__("H143")

    def _check_conditions(self, f):
        if (f["vol_9"] > 4106.0 and f["range_9_rank"] > 0.525
                and f["shadow_dn"] > 0.4535):
            return Signal(direction=Direction.VENDA, entry=0, stop=0,
                          target=0, timestamp=0, strategy_id=self._name)
        return None
