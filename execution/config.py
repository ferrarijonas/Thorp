"""EngineConfig — objeto de configuracao para ExecutionEngine."""
from dataclasses import dataclass

@dataclass
class EngineConfig:
    convention: str = "worst"        # "worst" | "best"
    volume: float = 1.0              # contratos por trade
    cost: float = 10                 # pontos por trade
    slippage_model: object = None    # SlippageModel | None
    risk_guardian: object = None     # RiskGuardian | None
