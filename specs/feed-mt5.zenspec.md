# Feed MT5 (`mt5_feed`)

Este programa existe para **conectar ao terminal MetaTrader 5 e emitir `Bar` a partir de candles reais**, suportando tanto consulta histórica quanto polling ao vivo.

---

## Fluxo

```
MetaTrader 5  →  mt5.initialize()  →  mt5_feed  →  Bar
```

## Contrato

**Entrada (construtor):**

- `symbol: str` — símbolo (ex: `"WIN"`, `"WINM1"`)
- `timeframe: int` — constante MT5 (ex: `mt5.TIMEFRAME_M1`)
- `mode: str` — `"historical"` ou `"live"`

**Entrada (`fetch(from_date, to_date)`):**

- `from_date: datetime`
- `to_date: datetime`

**Entrada (`poll()`):**

- nenhuma

**Saída (`fetch()`):**

- `list[Bar]`

**Saída (`poll()`):**

- `Bar | None` — novo candle desde a última chamada, ou `None`

**Erros:**

- MT5 não instalado ou não inicializado → `ConnectionError("MT5 not initialized")`
- Símbolo não encontrado no MarketWatch → `ValueError("Symbol SYMBOL not found")`
- Timeframe inválido → `ValueError("Invalid timeframe TF")`

---

## Lógica

### Inicialização

```
mt5_feed.__init__():
  1. if not mt5.initialize():
       raise ConnectionError
  2. mt5.symbol_select(symbol, True)
  3. Guarda symbol, timeframe, mode
```

### Fetch histórico

```
fetch(from_date, to_date):
  1. rates = mt5.copy_rates_range(symbol, timeframe, from_date, to_date)
  2. Se rates is None ou vazio: return []
  3. Converte cada rate para Bar:
       Bar(
         time=datetime.fromtimestamp(r['time']),
         open=r['open'], high=r['high'], low=r['low'], close=r['close'],
         volume=r['tick_volume'])  # tick_volume é int; compatível com Bar.volume:int
  4. return bars
```

### Poll ao vivo (modo `live`)

```
poll():
  1. rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 1)
  2. Se rates is None ou vazio: return None
  3. rate = rates[0]
  4. Se já vimos este candle (time == last_time): return None
  5. Constrói Bar igual ao fetch
  6. Atualiza last_time
  7. return Bar
```

### Encerramento

```
close():
  1. No-op. MT5 shutdown é gerenciado pelo engine (execution/engine.py) para evitar conflito entre feed e broker compartilharem a mesma instância.
```

---

## Edge cases

| Se | Então |
|----|-------|
| MT5 terminal fechado | `poll()` ou `fetch()` lança `ConnectionError` |
| Símbolo não selecionado | Tenta `symbol_select` automaticamente; se falhar, erro |
| `copy_rates_range` retorna `None` (MT5 erro interno) | Retorna lista vazia; `last_error()` pode ser consultado |
| Chamar `poll()` antes de qualquer dado disponível | Retorna `None` |
| Mesmo candle aparecer em 2 polls consecutivos (live) | Segundo poll retorna `None` (dedup por timestamp) |
| Símbolo parou de ser negociado (fim de pregão) | Poll retorna `None` continuamente (não falha) |

---

## Critérios de aceitação

1. `fetch()` retorna `list[Bar]` com candles ordenados por timestamp
2. Cada `Bar` tem `time`, `open`, `high`, `low`, `close`, `volume` preenchidos
3. Poll ao vivo não repete o mesmo candle
4. `close()` libera recursos sem exceção
5. CSV (`data.load_csv()`) e MT5 `fetch()` para o mesmo período retornam dados compatíveis (compara em testes)

---

## Dependências

- `MetaTrader5` — conexão com terminal
- `core/types.py` — `Bar`
