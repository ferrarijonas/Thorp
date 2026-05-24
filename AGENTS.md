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
scripts/    → avaliar_hipotese (BT completo, 5 seções), run_bot
              CATALOGO.md (índice completo de scripts)
state/      → session.json, decisions.log, positions.json
              containers_calibration.json (P50/P75 range)
              slippage_calibration.json (spread/slip MT5)
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

Rastro de cada trade inclui a **barra anterior** (rastro[0]) como referência de entrada.
rastro[1:] é a barra de entrada em diante, onde SL/TP são verificados.
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
6. [avaliar_hipotese.py] → 1 BT + 5 seções (diagnóstico + custo real unificados). Script único de backtest.
7. [strategy/Hxxx_strategy.py] → implementar estratégia (colocar em ATIVAS/)
8. [state/] → registrar resultado em decisions.log + session.json
```

## Comandos

Todos os scripts do Thorp estão catalogados em `scripts/CATALOGO.md`, com descrição e uso de cada um.

### Avaliação de hipótese — 1 BT + 5 seções (script único de backtest)

```bash
python scripts/avaliar_hipotese.py Hxxx
```

Faz 1 BT (~30s) e entrega 5 seções sempre:

| Seção | O que mostra |
|-------|-------------|
| ANOMALIA | MFE/MAE/assimetria — edge puro sem container |
| ENTRADA | Vantagem % para 4 pontos (abertura/fechamento/máxima/mínima) |
| TEMPO PÓS-ENTRADA | Vantagem barra a barra, mostra onde o edge pica e morre |
| CONTÊINER | 5 TPs (TIME/P50/P75/2xP75/3xP75) × 2 convenções (pior/melhor caso) |
| CUSTO REAL | BT com slippage calibrado do MT5 (se disponível) |

**Sem flags. Um comando. Sempre mesma saída.**

Veredito automático: ROBUSTO (ambos p<0.05 e mesmo sinal) / SINAL OK (um p<0.05) / MORTA.

Saída com encoding UTF-8: `$env:PYTHONIOENCODING='utf-8'; python scripts/avaliar_hipotese.py Hxxx`

### Batelada

```bash
python scripts/avaliar_hipotese.py H102 H103 H104
```

### Baseline (opcional — condição vs direção aleatória)

```bash
python scripts/testar_vs_baseline.py Hxxx
```

SL=P75, TP=P50. 500 rodadas baseline. Lento (~90s). Só se precisar diagnosticar KS.

### Demo ao vivo (1 estratégia)

```bash
python scripts/run_bot.py --terminal xp
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
- `core/analisador.py` centraliza todas as métricas (`calcular`, `vantagem_por_entrada`, `decaimento_temporal`, `re_simular`, `veredito`). O `avaliar_hipotese` é uma fachada que chama esses 5 métodos.
- `CsvFeed` usa numpy arrays para acesso rápido. Para otimizar BT, passe o DataFrame pré-filtrado: `CsvFeed(df=df.between_time("09:00","17:00"))`.
- Rastro de cada trade inclui a barra anterior [0] como referência de entrada. rastro[1:] para SL/TP.
