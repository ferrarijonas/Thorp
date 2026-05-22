# Thorp — AGENTS.md

Sou a interface entre o LLM e o Thorp. Quem abrir o opencode nesta pasta me lê primeiro.

## Papel

- Entendo a arquitetura do Thorp (lendo este arquivo + código)
- Ajudo o usuário a criar/testar/executar estratégias
- Opero via CLI: python scripts/, git add/commit/push
- Tudo o que faço fica registrado

## Setup

```bash
pip install -r requirements.txt
```

Colocar `Historico_OHLC.csv` na raiz para BT completo.
Ou usar `Historico_AMOSTRA.csv` (100 linhas, já incluso) para testes.

## Arquitetura (visão do LLM)

```
feed/       → CsvFeed (CSV), Mt5Feed (MT5 ao vivo)
strategy/   → base.py + Hxxx_strategy.py (só estratégias ativas/vivas)
              *.mq5 (EAs para MT5)
core/       → types, data, risk_guardian, calibrator, containers (percentis/min)
execution/  → engine (1 estratégia), manager (N estratégias), slippage
broker/     → simulated (BT), mt5_broker (demo/real)
scripts/    → pipeline (2 gates), avaliar_hipotese (1BT+re-sim), run_demo
state/      → session.json, decisions.log, positions.json
hipoteses/  → CATALOGO.json (índice), QUASE.json (prioridades)
              DADOS/ (percentis, templates)
              ATIVAS/ (hipóteses em teste, com código)
              EXPLORADAS/ (finalizadas, cada uma com RESUMO.md)
principios/ → sl-tp.md (SL/TP containers, pipeline de validação)
              ea-checklist.md (Python→MQL5 tradução)
```

### Pipeline de dados

```
CSV/MT5 → Feed → Engine.step() / on_bar(bar)
                    ├─ _reconcile() → sincroniza com MT5
                    ├─ check stop/target da posição atual
                    └─ strategy.on_bar(bar) → Signal
                         └─ RiskGuardian.process() → SL=P75, TP=P50
                         └─ broker.execute(signal) → Order → Position
```

## Fluxo do agente (do zero)

### Método Thorp: Dados → Radiografia → Hipóteses → Teste → Validação

```
1. [state/session.json] → ler fase atual, hipóteses vivas/mortas
2. [hipoteses/CATALOGO.json] → todas as hipóteses catalogadas
3. [hipoteses/QUASE.json] → hipóteses que quase passaram, priorizadas
4. [principios/sl-tp.md] → como SL e TP são tratados (containers, não edge)
5. [ANATOMIA DE HIPOTESE] → dissecar parametros contra dados antes de codificar
   → hipoteses/DADOS/ANATOMIA_TEMPLATE.md
6. [avaliar_hipotese.py] → 1 BT + re-simula 4TP × 2 conv (diagnóstico rápido)
7. [pipeline.py --compare] → valida robustez OHLC (worst + best)
8. [strategy/Hxxx_strategy.py] → implementar estratégia (colocar em ATIVAS/)
9. [state/] → registrar resultado em decisions.log + session.json
```

## Comandos

### Pipeline padrão (2 gates)

```bash
python scripts/pipeline.py Hxxx
python scripts/pipeline.py H102 H103 H104
python scripts/pipeline.py all
```

Gate 1: BT ideal (rápido). Se p < 0.05 e metades ok → Gate 2.
Gate 2: BT com slippage calibrado. p < 0.05 e metades ok → PASSOU.
~70% morrem no Gate 1. Silencioso (sem logs de trade).

### Avaliação rápida (recomendado — 1 BT + re-simulação)

```bash
python scripts/avaliar_hipotese.py Hxxx
```

Faz 1 BT (~30s) e re-simula 4TP × 2 convenções em <1s.
Usar como primeiro diagnóstico: mostra se a direção do sinal sobrevive a diferentes TPs e convenções.

`--entry` testa 5 geometrias de entrada (open/close/low/high/mid) re-simulando os trades existentes em <1s.
Útil para encontrar o ponto de entrada ideal sem rodar novo BT.

### Comparação de convenções OHLC (robustez — só se passou na avaliação rápida)

```bash
python scripts/pipeline.py --compare Hxxx
```

Roda worst-case (SL primeiro) e best-case (TP primeiro).
ROBUSTO = ambos com p<0.05 e mesmo sinal. Se divergem, edge é path-dependent → MORTA.
~60s por hipótese.

### BT avulso (sem pipeline)

```bash
python scripts/run_bateria.py Hxxx
python scripts/run_bateria.py --ideal Hxxx   # sem slippage
```

### Baseline (opcional — condição vs direção aleatória)

```bash
python scripts/testar_vs_baseline.py Hxxx
```

SL=P75, TP=P50. 500 rodadas baseline. Lento (~90s). Só se precisar diagnosticar KS.

### Batelada

```bash
python scripts/pipeline.py H102 H103 H104
python scripts/pipeline.py all          # todas H102-H120
```

### Demo ao vivo (1 estratégia)

```bash
python scripts/run_demo.py
```

### Comparar execução (BT ideal vs BT+slippage vs Demo)

```bash
python scripts/comparar_execucao.py Hxxx
```

### Calibrar slippage do MT5

```bash
python -c "from core.calibrator import Calibrator; c=Calibrator(); c.calibrar(); c.salvar()"
```

## Como criar uma estratégia

Criar `strategy/Hxxx_strategy.py`:

```python
from strategy.base import Strategy
from core.types import Bar, Signal, Direction

class HxxxStrategy(Strategy):
    def __init__(self):
        self._name = "Hxxx"   # identificador único para reconcile

    def on_bar(self, bar: Bar) -> Signal | None:
        # Regra de entrada. Exemplo:
        if bar.close > bar.open:
            return Signal(direction=Direction.LONG, entry=bar.close,
                          stop=0, target=0, timestamp=bar.time,
                          strategy_id=self._name)
        return None

    def reset(self):
        pass
```

- `stop=0 target=0` → RiskGuardian preenche:
  - SL = P75 do range da hora
  - TP = P50 do range da hora (se tese não define)
  - max_exit_time = 17h (fim da sessão)
- `strategy_id` único → necessário para reconciliação com MT5
- Para criar um EA (.mq5), consultar `principios/ea-checklist.md` obrigatoriamente antes de codificar

## Regras

- Convencao: usar **compra/venda** (nao LONG/SHORT). `Direction.COMPRA` e `Direction.VENDA` sao os nomes primarios; LONG/SHORT sao aliases.
- `state/decisions.log` registra cada decisao. Se nao esta la, nao aconteceu.
- Baseline: condicao vs aleatorio. Se KS p > 0.05, condicao e ruido (diagnostico, nao gate).
- BT: p < 0.05 e metades ok → PASSOU.
- RiskGuardian exige `min_stop_pts=250` em modo Demo/Real (mínimo do MT5).
- Em BT, slippage é aplicado pelo `SlippageModel` (calibrado do MT5).
- Em Demo/Real, `_reconcile()` sincroniza engine com posições reais do MT5 a cada step.
- `fetch_positions()` retorna posições do MT5 com ticket, direção, SL/TP.
- `principios/sl-tp.md` detalha a filosofia completa de SL e TP.
- `principios/ea-checklist.md` detalha as regras de tradução Python→MQL5 (consultar antes de criar um EA).
