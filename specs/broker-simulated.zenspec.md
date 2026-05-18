# Broker Simulado (`simulated_broker`)

Este programa existe para **simular a execução de ordens durante backtest**, preenchendo ordens no candle seguinte sem latência, slippage ou rejeição.

---

## Fluxo

```
Signal  →  simulated_broker.execute()  →  Order(filled)
```

## Contrato

**Entrada (construtor):**

- `cost: float` — custo por trade em pontos (default `10`)
- Nenhuma dependência externa

**Entrada (`execute(signal)`):**

- `signal: Signal` — sinal gerado pela estratégia

**Saída (`execute(signal)`):**

- `Order` com `status = FILLED`, `filled_price = signal.entry`, `filled_at = signal.timestamp`

**Erros:**

- Nenhum — o simulated broker sempre preenche.

---

## Lógica

```
execute(signal):
  1. Cria Order(
       id = str(uuid4())[:8],
       signal = signal,
       type = OrderType.MARKET,
       status = OrderStatus.FILLED,
       filled_price = signal.entry,
       filled_at = signal.timestamp)
  2. return order
```

O broker simulado **não separa em modos BT/Demo/Real**. Ele só existe para backtest. Para modos Demo/Real, use `mt5_broker`.

### Consulta de posições

```
fetch_positions() -> list[Position]:
  1. return []  # simulated broker não tem posições reais
```

**Idempotência:** executar o mesmo signal duas vezes gera duas ordens distintas (sem dedup). O controle de idempotência é responsabilidade do `execution_engine`.

---

## Edge cases

| Se | Então |
|----|-------|
| `signal.entry` for `0` | Preenche a zero (trade possível, mas alerta no log) |
| `signal` for `None` | Retorna `None` (engine trata como "sem ação") |
| Custo maior que o ganho potencial | Trade ainda é preenchido; custo só afeta PnL final |

---

## Critérios de aceitação

1. `execute(signal)` retorna `Order(status=FILLED)` com o mesmo direction do signal
2. `Order.filled_price == signal.entry`
3. `Order.filled_at == signal.timestamp`
4. Chamadas consecutivas retornam ordens com IDs diferentes

---

## Dependências

- `core/types.py` — `Signal`, `Order`, `OrderType`, `OrderStatus`, `Position`
