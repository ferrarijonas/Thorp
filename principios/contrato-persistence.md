# Contrato Persistência

```
Arquivo:  core/persistence.py (novo, migrado de core/trade_store.py)
Propósito: Persistência externa de trades e capital.
           A engine NÃO chama persistência — quem usa decide.
```

## Interface

```python
class TradeStore:
    def __init__(self, path: str): ...
    def append(self, trade: Trade) -> None: ...
    def load(self) -> list[dict]: ...
    def clear(self) -> None: ...

class CapitalStore:
    def __init__(self, path: str): ...
    def save(self, capital: float, drawdown: float, initial_capital: float) -> None: ...
    def load(self) -> dict | None: ...
```

## Regras

- `TradeStore.append()` é atômico (escreve .tmp, depois rename)
- `CapitalStore.save()` também é atômico
- A engine **nunca** chama persistência — ela só gerencia trades em memória
- Quem quiser persistir: `run_bot.py`, scripts manuais, etc.

## Motivação

Antes: engine aceitava `trade_store_path` e persistia automaticamente.
Agora: engine não sabe de persistência. Menos responsabilidade, mais testável.

**Nenhum código de produção usava essa persistência** (run_bot.py nunca passou `trade_store_path`).
