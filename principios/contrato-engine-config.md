# Contrato EngineConfig

```
Arquivo:  execution/config.py (novo)
Propósito: Objeto de configuração para ExecutionEngine.
           Separa parâmetros de engine da instanciação.
```

## Interface

```python
from dataclasses import dataclass
from core.types import ExecutionMode

@dataclass
class EngineConfig:
    convention: str = "worst"       # "worst" | "best"
    volume: float = 1.0             # contratos por trade
    cost: float = 10                # pontos por trade (comissão + spread)
    slippage_model: object = None   # SlippageModel | None
    risk_guardian: object = None    # RiskGuardian | None
```

## Engine.__init__

```python
class ExecutionEngine:
    def __init__(self, feed, strategy, broker, mode: ExecutionMode,
                 config: EngineConfig | None = None, **kwargs):
```

### Regras de compatibilidade
- Se `config` for passado, usa config (e ignora kwargs)
- Se `config` for None, monta EngineConfig a partir de kwargs compatíveis
- kwargs antigos continuam funcionando: `cost=10`, `risk_guardian=rg`, etc.
- `trade_store_path` e `capital_store_path` são removidos (persistência é externa)

### Parâmetros não-configuráveis via EngineConfig
- `feed`, `strategy`, `broker`, `mode` — obrigatórios, sempre posicionais
- Esses são dependências injetadas, não configuração
