# Thorp — Quem faz o quê

## Cadeia completa (BT = Demo = Real)

```
Feed → Strategy → RiskGuardian → SlippageModel → Broker → Engine
```

## Responsabilidades

### Strategy
| Decide | Exemplo | Como |
|--------|---------|------|
| **Direção** | LONG ou SHORT | `Signal(direction=LONG)` |
| **Condição de entrada** | gap > 0.3%, ret < -0.3% | lógica em `on_bar(bar)` |
| **Preço de entrada** | bar.open | `Signal(entry=bar.open)` |
| **Stop/Target** | delega | `stop=0, target=0` → RiskGuardian preenche |

A Strategy **não sabe** se é BT, Demo ou Real. Ela só emite `Signal`.

---

### RiskGuardian
| Decide | Exemplo | Como |
|--------|---------|------|
| **Stop size** | P75 range da hora | `_calc_stop()` |
| **Target size** | stop_dist × R:R ratio | `_calc_target()` |
| **Horário** | 9h-17h | `trade_start / trade_end` |
| **Drawdown máx** | 200 pts | `max_dd` |
| **Posições máx** | 1 | `max_positions` |
| **MT5 health** | terminal conectado? | `mt5.initialize()` |
| **Tamanho** | 1 contrato | `size=1` |

RiskGuardian enriquece o Signal (preenche stop/target) e **bloqueia** se risco violado.

---

### SlippageModel
| Emula | BT | Demo/Real |
|-------|-----|-----------|
| **Slippage na entrada** | entry ± spread/2 | zero (real) |
| **Slippage no stop** | stop pode escorregar N pts | zero (real) |
| **Slippage no target** | target pode escorregar N pts | zero (real) |
| **Spread** | custo adicional por trade | zero (real) |
| **Latência** | atraso de N ms no fill | zero (real) |

No BT, o SlippageModel **degrada** os fills pra parecerem reais. No Demo/Real, passa limpo (a realidade já entrega o efeito).

---

### Broker
| Faz | BT | Demo | Real |
|-----|-----|------|------|
| **Fill** | simulado (preenche na hora) | mt5.order_send() | mt5.order_send() |
| **Rejeição** | nunca | possível (saldo, símbolo) | possível |
| **Custo** | configurável (cost=10) | real (corretagem) | real (corretagem) |

---

### Engine
| Gerencia | Como |
|----------|------|
| **Posição** | cria quando broker preenche |
| **Stop** | verifica `bar.low <= stop` |
| **Target** | verifica `bar.high >= target` |
| **Time-limit** | verifica `bar.time >= max_exit_time` |
| **Trade** | registra quando posição fecha |
| **Sequência** | feed.poll() → on_bar() → process() → execute() |

---

## Resumo visual

```
Strategy           RiskGuardian         SlippageModel        Broker
───────            ────────────         ─────────────        ──────
direção     →      stop/size     →      slippage      →      fill
entry       →      target        →      spread        →      custo
condição    →      horário       →      latência      →      rejeição
                    DD check
                    MT5 check
```
