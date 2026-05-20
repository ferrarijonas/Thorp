"""H144 — green_9>0.5, shadow_dn>0.0651, gap<=32.5 → VENDA."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Direction
from strategy.markov_feature_set import MarkovFeatureSet

class H144Strategy(MarkovFeatureSet):
    def __init__(self):
        super().__init__("H144")

    def _check_conditions(self, f, bar):
        if (f["green_9"] > 0.5 and f["shadow_dn"] > 0.0651
                and (f["gap"] is not None and f["gap"] <= 32.5)):
            return Direction.VENDA
        return None
