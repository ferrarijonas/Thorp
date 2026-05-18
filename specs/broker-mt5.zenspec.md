# Broker MT5 (`mt5_broker`)

Este programa existe para **enviar ordens reais ao MetaTrader 5** em modo Demo ou Real, e consultar o estado de posições abertas.

---

## Fluxo

```
Signal  →  mt5_broker.execute()  →  mt5.order_send()  →  Order(filled|rejected)
```

## Contrato

**Entrada (construtor):**

- `mode: ExecutionMode` — `ExecutionMode.DEMO` ou `ExecutionMode.REAL`
- `symbol: str` — símbolo MT5 (ex: `"WIN"`)
- `volume: float` — lote fixo (ex: `1.0`)

**Entrada (`execute(signal)`):**

- `signal: Signal` — sinal da estratégia (direction, entry, stop, target)

**Saída (`execute(signal)`):**

- `Order` com `status = FILLED` ou `REJECTED`

**Entrada (`fetch_positions()`):**

- nenhuma

**Saída (`fetch_positions()`):**

- `list[Position]` — posições abertas no terminal

**Erros:**

- MT5 não inicializado → tenta reconectar uma vez; se falhar, `Order(status=REJECTED)`
- Saldo insuficiente → `Order(status=REJECTED)`
- Símbolo desabilitado para trading → `Order(status=REJECTED)`
- Erro de timeout → `Order(status=REJECTED)`

---

## Lógica

### Inicialização

```
mt5_broker.__init__():
  1. Guarda mode, symbol, volume
  2. Conecta ao MT5 via initialize() se não estiver conectado
```

### Execução de ordem

```
execute(signal):
  1. Mapeia Direction para mt5.ORDER_TYPE:
       LONG  → mt5.ORDER_TYPE_BUY
       SHORT → mt5.ORDER_TYPE_SELL

  2. request = mt5.TradeRequest(
       action=mt5.TRADE_ACTION_DEAL,
       symbol=self.symbol,
       volume=self.volume,
       type=order_type,
       price=signal.entry,
       sl=signal.stop,
       tp=signal.target,
       deviation=10,
       magic=1000,
       comment=signal.strategy_id,  # identificador completo sem truncamento
       type_time=mt5.ORDER_TIME_GTC,
       type_filling=mt5.ORDER_FILLING_IOC)

  3. result = mt5.order_send(request)
  4. Se result.retcode != mt5.TRADE_RETCODE_DONE:
       return Order(status=REJECTED, ...)
  5. return Order(
       id=str(result.order),
       signal=signal,
       type=OrderType.MARKET,
       status=OrderStatus.FILLED,
       filled_price=result.price,
       filled_at=datetime.now())
```

### Consulta de posições

```
fetch_positions():
  1. positions = mt5.positions_get(symbol=self.symbol)
  2. Se None: return []
  3. Converte cada position MT5 para Position:
       Position(
         direction=LONG|SHORT,
         entry=position.price_open,
         size=round(position.volume),  # MT5 volume pode ser float
         opened_at=datetime.fromtimestamp(position.time),
         strategy_id=str(position.comment),
         stop=position.sl,
         target=position.tp,
         max_exit_time=None)  # MT5 não persiste time-limit; engine gerencia separadamente
  4. return positions
```

---

## Edge cases

| Se | Então |
|----|-------|
| MT5 terminal desconectou entre calls | `initialize()` tentar reconectar automaticamente |
| Ordem rejeitada (motivo qualquer) | `Order(status=REJECTED)`, sem exceção |
| `signal.entry` distante do mercado (ex: stop não atingido) | Ordem pode ser rejeitada pelo MT5; broker retorna REJECTED |
| Símbolo com nome diferente no MT5 (ex: `"WINM1"` vs `"WIN"`) | Usar exatamente o nome do símbolo no terminal; se não encontrar, lança `ValueError` |
| Volume mínimo abaixo do exigido pela corretora | MT5 rejeita; broker retorna REJECTED |

---

## Critérios de aceitação

1. `execute(signal)` retorna `Order` com status FILLED ou REJECTED — nunca lança exceção inesperada
2. `fetch_positions()` retorna posições abertas consistentes com o terminal
3. Ordem rejeitada é reportada como `Order.status == REJECTED`, não como exceção
4. Reconexão automática se MT5 cair e voltar

---

## Dependências

- `MetaTrader5` — envio de ordens e consulta
- `core/types.py` — `Signal`, `Order`, `OrderStatus`, `OrderType`, `Direction`, `Position`
