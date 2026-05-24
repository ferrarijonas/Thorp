# Contrato Order Lifecycle

```
Propósito: Rastrear o ciclo de vida completo de ordens na engine.
           Cada ordem emitida fica registrada, independente de ser preenchida ou não.
```

## Fluxo atual (já implementado)

```
strategy.on_bar() → Signal
broker.execute(signal) → Order

if Order.status == FILLED:
    Position(entry=Order.filled_price, ...)
```

## Adição: ordem histórica

A engine mantém um histórico de todas as ordens emitidas:

```python
self._orders: list[Order] = []   # em __init__
```

Após cada `broker.execute()`:

```python
self._orders.append(order)
```

Isso inclui ordens REJECTED — servem para diagnóstico.

## Responsabilidades

- O histórico de ordens é **apenas consultivo** (não usado pela engine)
- `ExecutionResult` não inclui ordens (por enquanto)
- Quem quiser usar, acessa `engine._orders`
- Uma ordem rejeitada tem `status=REJECTED`, não é retentada automaticamente

## Não-esopo

- ❌ Não há retry automático de ordens rejeitadas
- ❌ Não há suporte a ordens parciais
- ❌ Não há suporte a ordens LIMIT/STOP (apenas MARKET)
