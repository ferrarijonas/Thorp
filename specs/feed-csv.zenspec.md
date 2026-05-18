# Feed CSV (`csv_feed`)

Este programa existe para **iterar dados históricos OHLC de um CSV e emitir `Bar` um por vez**, como se fossem candles chegando em tempo real.

---

## Fluxo

```
DataFrame  →  csv_feed  →  Bar
```

## Contrato

**Entrada:**

- `csv_path: str` — caminho do arquivo CSV (opcional; default `Historico_OHLC.csv`)
- `encoding: str` — encoding do CSV (default `utf-16`)

**Saída (`poll()`):**

- `Bar | None` — próximo candle, ou `None` quando acabar

**Outros métodos:**

- `reset()` — reinicia o índice para o início dos dados
- `close()` — no-op (compatível com interface esperada pelo engine; sem recursos externos)

**Erros:**

- Arquivo não encontrado → `FileNotFoundError` explícito
- CSV mal formatado (colunas erradas) → `ValueError` com detalhe
- Chamar `poll()` após acabarem os dados → retorna `None` (não falha)

---

## Lógica

```
load_csv(csv_path) → DataFrame com colunas:
  datetime, open, high, low, close, volume

csv_feed guarda o DataFrame internamente e um índice (posição atual).

poll():
  1. Se índice >= len(df): return None
  2. Pega a linha na posição índice
  3. Constrói Bar(
       time=datetime, open=open, high=high, low=low,
       close=close, volume=volume)
  4. Incrementa índice
  5. Return Bar

reset(): volta índice a 0
```

**Idempotência:** chamar `poll()` N vezes avança N posições. `reset()` torna a sequência replayável.

---

## Edge cases

| Se | Então |
|----|-------|
| DataFrame vazio (0 linhas) | `poll()` retorna `None` na primeira chamada |
| CSV tem gaps temporais (fim de semana) | Apenas pula para a próxima linha; gaps não são inferidos |
| Chamar `poll()` após o fim dos dados | Retorna `None` consistentemente |
| Reset seguido de poll | Recomeça do primeiro Bar |

---

## Critérios de aceitação

1. `poll()` retorna `Bar` com todos os campos preenchidos
2. Sequência de N `poll()` retorna N candles, na mesma ordem do CSV
3. Após o último candle, `poll()` retorna `None`
4. `reset()` + N `poll()` reproduz a mesma sequência idêntica

---

## Dependências

- `pandas` — leitura do CSV
- `core/data.py` — `load_csv()` carrega o DataFrame do CSV
- `core/types.py` — `Bar`
