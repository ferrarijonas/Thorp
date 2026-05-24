# Contrato Broker

```
Arquivo:  broker/base.py
Propósito: Interface abstrata para execução de ordens e consulta de posições.
Implementações: SimulatedBroker (BT), Mt5Broker (Demo/Real)
```

## Interface

```python
from abc import ABC, abstractmethod
from core.types import Signal, Order, Position

class Broker(ABC):

    @abstractmethod
    def execute(self, signal: Signal, volume: float = 1.0) -> Order:
        """Envia uma ordem ao mercado. SEMPRE retorna Order (nunca None)."""
        ...

    @abstractmethod
    def fetch_positions(self) -> list[Position]:
        """Retorna lista de posições abertas no broker."""
        ...

    def close(self):
        """Libera recursos associados ao broker."""
        pass
```

## Regras

### execute()
- SEMPRE retorna `Order`, nunca `None`
- Sucesso: `Order(status=FILLED, filled_price=..., filled_at=...)`
- Falha: `Order(status=REJECTED, filled_price=0)`
- Se `signal` for None: retorna `Order(status=REJECTED)`
- Volume padrão é 1.0 (1 contrato)

### fetch_positions()
- Retorna lista de `Position` abertas
- Lista vazia se não há posições
- Em BT, sempre retorna lista vazia
- Cada Position tem `strategy_id` para vincular à engine correta

## Implementações

### SimulatedBroker
- execute() sempre FILLED, preço = signal.entry
- fetch_positions() sempre retorna []
- Cost é aplicado pela engine (não pelo broker)

### Mt5Broker
- execute() envia ordem real via MT5 API
- fetch_positions() consulta `mt5.positions_get(symbol=...)`
- Retorna Order(REJECTED) se conexão falhou ou ordem rejeitada
- get_exit_info(ticket) opcional: retorna {exit_price, closed_at} do histórico
