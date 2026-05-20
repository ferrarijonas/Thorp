"""H142 — delta_body<=-0.0365, fragilidade<=0.1504, body_ratio>0.4472 → VENDA."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Direction
from strategy.markov_feature_set import MarkovFeatureSet

class H142Strategy(MarkovFeatureSet):
    def __init__(self):
        super().__init__("H142")

    def _check_conditions(self, f, bar):
        if (f["delta_body"] <= -0.0365 and f["fragilidade"] <= 0.1504
                and f["body_ratio"] > 0.4472):
            return Direction.VENDA
        return None
