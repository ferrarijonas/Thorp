"""H144 — green_9>0.5, shadow_dn>0.0651, gap<=32.5 → VENDA."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Signal, Direction
from strategy.markov_feature_set import MarkovFeatureSet

class H144Strategy(MarkovFeatureSet):
    def __init__(self):
        super().__init__("H144")

    def _check_conditions(self, f):
        if (f["green_9"] > 0.5 and f["shadow_dn"] > 0.0651
                and (f["gap"] is not None and f["gap"] <= 32.5)):
            return Signal(direction=Direction.VENDA, entry=0, stop=0,
                          target=0, timestamp=0, strategy_id=self._name)
        return None
