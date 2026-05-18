# Strategy Base (`strategy_base`)

Este programa existe para **definir o contrato que toda estratégia deve seguir**: receber `Bar` e retornar `Signal` ou `None`. A estratégia nunca interage com broker, feed, posição ou estado externo.

---

## Fluxo

```
Feed(bar)  →  strategy.on_bar(bar)  →  Signal | None
```

## Contrato

**Classe base:**

```python
class Strategy(ABC):
    def on_bar(self, bar: Bar) -> Signal | None
```

**Entrada (`on_bar(bar)`):**

- `bar: Bar` — candle OHLC padronizado

**Saída (`on_bar(bar)`):**

- `Signal | None` — sinal de trade (direção, entrada, stop, target) ou `None` se nenhuma ação

**Erros:**

- `on_bar` nunca deve lançar exceção. Se a lógica falhar, retorna `None` e loga internamente.

---

## Lógica

### Regras

1. A estratégia **não sabe se está em backtest, demo ou real.** Ela só vê `on_bar(bar)`.
2. A estratégia **não gerencia posição.** Ela não sabe se há posição aberta. O `execution_engine` gerencia.
3. A estratégia **não define horário de saída.** O `Signal` pode conter `stop`, `target` e `max_exit_time`, mas a lógica de saída é do engine.
4. A estratégia **pode ter estado interno** (último preço, flags, acumuladores), desde que seja resetado se necessário.
5. O `Signal.entry` deve ser o preço no qual a ordem deve ser executada (ex: `bar.open` do candle atual). Se `entry = 0`, o engine decide (usar `bar.close`).
6. A estratégia **pode receber o mesmo bar duas vezes** no mesmo step (fim de posição + reavaliação, se a posição fechou no bar atual). Estratégias que não devem reentrar imediatamente precisam de controle interno (ex: noop até próximo bar).

### Contrato do Signal

```
Signal(
  direction=Direction.LONG|SHORT,
  entry=float,        # preço de entrada
  stop=float,         # preço de stop loss
  target=float,       # preço de take profit
  timestamp=datetime, # momento do sinal
  strategy_id=str,    # identificador único da estratégia
  size=int=1,         # tamanho da posição (contratos)
  max_exit_time=datetime|None  # limite temporal
)
```

Se a estratégia não quiser definir stop/target (ex: estratégia de saída por tempo), pode usar `0` e o engine trata como "sem stop/target".

### Reset de estado

Toda estratégia com estado interno **deve** implementar `reset()` para reiniciar entre runs:

```python
def reset(self):
    """Reinicia estado interno. Chamado pelo engine entre BT → Demo."""
    self._condicao_ativa = False
```

---

## Edge cases

| Se | Então |
|----|-------|
| Estratégia retorna `None` N vezes seguidas | Normal — significa "sem sinal", engine continua |
| `on_bar(bar)` lança exceção | Engine captura, loga o erro, e trata como `None` |
| Strategy retorna `Signal` com `entry=0` | Engine usa `bar.close` do bar atual como entry |
| Signal com `stop` ou `target = 0` | Engine ignora stop/target (posição só fecha por tempo) |

---

## Critérios de aceitação

1. Toda estratégia concreta herda de `Strategy` e implementa `on_bar(bar) -> Signal | None`
2. Estratégia nunca chama broker, feed, mt5 ou qualquer dependência externa
3. `on_bar` é pura: mesmo bar → mesmo output (estado interno permitido, mas determinístico)
4. Estratégia não bloqueia nem dorme — engine controla o fluxo

---

## Dependências

- `core/types.py` — `Bar`, `Signal`, `Direction`
- `abc` — `ABC`, `abstractmethod`
