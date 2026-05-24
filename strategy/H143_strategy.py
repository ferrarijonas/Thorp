"""H143 — vol_9>4106, range_9_rank>0.525, shadow_dn>0.4535 → VENDA."""
from core.types import Direction
from strategy.markov_feature_set import MarkovFeatureSet

class H143Strategy(MarkovFeatureSet):
    def __init__(self):
        super().__init__("H143")

    def _check_conditions(self, f, bar):
        if (f["vol_9"] > 4106.0 and f["range_9_rank"] > 0.525
                and f["shadow_dn"] > 0.4535):
            return Direction.VENDA
        return None
