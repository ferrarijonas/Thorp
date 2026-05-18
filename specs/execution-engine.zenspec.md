# Execution Engine (`execution_engine`)

Este programa existe para **orquestrar o ciclo completo de trading**: puxar `Bar` do feed, passar para a estratégia, executar o sinal no broker, gerenciar posição (stop, target, time-limit) e registrar resultados.

**É o único componente que conhece feed, strategy e broker.** A estratégia nunca vê o broker; o broker nunca vê a estratégia.

---

## Fluxo

```
Feed  →  execution_engine.run()
            │
            ├─ on_bar(bar) → strategy → Signal → broker.execute() → Order
            │
            └─ gerencia posição (stop/target/time)
                    │
                    └─ Trade
```

### Backtest

```
csv_feed  →  execution_engine  →  simulated_broker  →  ExecutionResult
```

### Demo

```
mt5_feed (live)  →  execution_engine  →  mt5_broker (demo)  →  state/positions.json
```

### Real

```
mt5_feed (live)  →  execution_engine  →  mt5_broker (real)  →  state/positions.json
```

---

## Contrato

**Entrada (construtor):**

- `feed: object` — instância de `csv_feed` ou `mt5_feed` (método `poll() -> Bar | None`)
- `strategy: Strategy` — classe que herda de `Strategy`
- `broker: object` — instância de `simulated_broker` ou `mt5_broker` (métodos `execute(signal) -> Order` e `fetch_positions() -> list[Position]`)
- `mode: ExecutionMode` — `ExecutionMode.BT`, `.DEMO` ou `.REAL` (não aceitar string)
- `cost: float` — custo por trade em pontos (default `10`)

**Entrada (`run()`):**

- `max_bars: int | None` — limita candles processados (útil para debug)

**Saída (`run()`):**

- `ExecutionResult` — trades, estatísticas, PnL

**Saída (`step()`):**

- `Bar | None` — processa um bar, retorna o bar ou `None` se acabou

**Métodos de cleanup:**

- `close()` — chama `feed.close()` e `mt5.shutdown()` se existirem

---

## Lógica

```
execution_engine.__init__(feed, strategy, broker, mode, cost=10):
  1. Guarda feed, strategy, broker, mode, cost
  2. position = None
  3. trades = []
  4. step_count = 0
```

```
step() -> Bar | None:
  1. bar = feed.poll()
  2. Se bar is None: return None

  3. step_count += 1

  4. Se position exists:
       a. max_exit_time: se bar.time >= position.max_exit_time
            → fecha em bar.close
       b. stop LONG: se bar.low <= position.stop
            → fecha em position.stop
       c. target LONG: se bar.high >= position.target
            → fecha em position.target
       d. stop SHORT: se bar.high >= position.stop
            → fecha em position.stop
       e. target SHORT: se bar.low <= position.target
            → fecha em position.target
       f. Se fechou:
            pnl = (exit - entry) * direction.value - cost
            trades.append(Trade(
                strategy_id=position.strategy_id,
                direction=position.direction,
                entry=position.entry,
                exit=exit,
                pnl_points=pnl,
                opened_at=position.opened_at,
                closed_at=bar.time,
                bars_held=step_count - position._open_step))
            position = None

  5. Se NOT position:
       signal = strategy.on_bar(bar)
       Se signal:
            order = broker.execute(signal)
            Se order.status == FILLED:
                position = Position(
                    direction=signal.direction,
                    entry=order.filled_price,
                    size=signal.size,
                    opened_at=bar.time,
                    strategy_id=signal.strategy_id,
                    stop=signal.stop,
                    target=signal.target,
                    max_exit_time=signal.max_exit_time)
                position._open_step = step_count

  6. return bar
```

**Nota:** No passo 4, se a posição fecha por stop/target, o mesmo bar ainda é passado para `strategy.on_bar()` no passo 5 (se `position = None`). Isso permite reentrada no mesmo candle. Estratégias que não devem reentrar imediatamente devem controlar isso internamente (ex: flag de cooldown).

```
run(max_bars=None) -> ExecutionResult:
  1. Enquanto True:
       bar = step()
       Se bar is None: break
       Se max_bars e step_count >= max_bars: break
  2. Se position aberta no fim:
       pnl = 0  # fecha a zero, sem custo
       trades.append(Trade(bars_held=step_count - position._open_step))
       position = None
  3. Calcula estatísticas em trades usando scipy.ttest_1samp
  4. return ExecutionResult(
       trades=trades,
       total_pnl=float(t.sum()),
       media=float(t.mean()),
       win_rate=float((t>0).mean()*100),
       profit_factor=...,
       total=len(t),
       p_valor=float(p_val),
       metade1_media=float(m1),
       metade2_media=float(m2),
       metades_ok=bool((m1>0)==(m2>0)))
```

```
run_live(interval=60):
  1. Enquanto True:
       try:
           bar = step()
           Se bar:
               # atualiza state/positions.json com broker.fetch_positions()
               pass
           sleep(interval)
       except Exception as e:
           log(f"run_live error: {e}")
           sleep(interval)  # tenta de novo após intervalo
           continue
```

```
close():
  1. Se feed tem método close(): feed.close()
  2. Se mode != BT (não inicializou MT5): tenta mt5.shutdown() se initialize() já foi chamado
```

---

## Edge cases

| Se | Então |
|----|-------|
| Feed acabou (None) com posição aberta | Fecha posição no último preço (PnL = 0) |
| Broker rejeita ordem | Position não criada, engine continua |
| Strategy retorna Signal com posição aberta | Signal ignorado |
| Estratégia lança exceção | Engine captura, loga, trata como `None`, continua |
| Posição fecha por stop/target e strategy reentra no mesmo bar | Permitido. Estratégia deve controlar se quer ou não |
| `run_live` lança exceção | Capturada, logada, loop continua |
| `max_exit_time` no passado ao criar posição | Posição fecha no mesmo bar (entrada + saída no mesmo candle) |
| Chamar `step()` com feed exaurido | Retorna `None` consistentemente |

---

## Critérios de aceitação

1. Backtest roda do início ao fim, retorna `ExecutionResult` com trades
2. Mesma `Strategy` em BT e demo produz `Signal` idênticos para os mesmos `Bar`
3. Stop e target: posição fecha exatamente nos preços definidos
4. Time-limit: posição fecha em `bar.close` no bar do limite
5. `bars_held` em cada `Trade` reflete o número de steps que a posição ficou aberta
6. Modo live (`run_live`) não morre em erro — loga e continua
7. `close()` libera recursos sem exceção
8. Se broker rejeita, nenhuma posição é criada (estado consistente)

---

## Dependências

- `core/types.py` — `Bar`, `Signal`, `Order`, `Position`, `Trade`, `ExecutionResult`, `ExecutionMode`, `Direction`
- `feed` — objeto com `poll() -> Bar | None` e opcionalmente `close()`
- `strategy` — objeto com `on_bar(bar) -> Signal | None`
- `broker` — objeto com `execute(signal) -> Order` e `fetch_positions() -> list[Position]`
- `scipy` — teste t nas estatísticas
