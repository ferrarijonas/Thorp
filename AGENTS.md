# Thorp — AGENTS.md

Sou o **orquestrador do Thorp**. Leio `state/`, decido, executo scripts, registro.

## Estado atual

- Fase: `FASE_6_INTEGRATION_DEMO`
- Ativo: WIN M1 (331k candles CSV + MT5 ao vivo)
- H101: MORTA | H102: MORTA | H103: MORTA
- H104: MORTA (probe strategy para calibracao CSV vs Demo)
- H105 a H120: AGUARDANDO CRIACAO

## Como opero

```
1. Leio state/session.json → fase, pendentes, ultima acao
2. Leio state/decisions.log → linhas recentes (contexto)
3. Decido acao (pergunto se duvida)
4. Executo comando
5. Escrevo resultado em state/decisions.log
6. Atualizo state/session.json
```

## Comandos

### Calibrar slippage (atualiza state/slippage_calibration.json)
```
python -c "from core.calibrator import Calibrator; c=Calibrator(); c.calibrar(); c.salvar()"
```

### Testar bateria (BT com slippage calibrado)
```
python scripts/run_bateria.py H102 H103 H104
python scripts/run_bateria.py all          # todas H102-H120
python scripts/run_bateria.py --ideal H104 # sem slippage
```

### Rodar multi-strategy ao vivo (StrategyManager)
```
python scripts/run_live_multi.py
```

### Comparar execucao (BT ideal vs BT+slippage vs Demo)
```
python scripts/comparar_execucao.py H104
```

### Rodar demo single
```
python scripts/run_demo.py
```

### Criar estrategia nova
Criar `strategy/Hxxx_strategy.py` seguindo `specs/strategy-base.zenspec.md`:
```python
from strategy.base import Strategy

class HxxxStrategy(Strategy):
    def on_bar(self, bar) -> Signal | None:
        # regra de entrada. stop=0 target=0 → RiskGuardian preenche
        ...
    def reset(self):
        ...
```

### Conectar/aferir dados MT5
```
python -c "from broker.mt5_broker import Mt5Broker; from core.types import ExecutionMode; b=Mt5Broker(ExecutionMode.DEMO,'WINM26',1); print('OK'); b.close()"
```

## Arquitetura

```
feed/          → CsvFeed, Mt5Feed (fonte de dados OHLC)
strategy/      → HxxxStrategy (logica de entrada)
core/          → types, data, risk_guardian, calibrator
execution/     → engine, manager, slippage
broker/        → simulated, mt5_broker
scripts/       → bateria, demo, comparacao, multi-live
state/         → session, decisions, calibrations (runtime, nao versionado)
```

## Regras

- Toda decisao vai em `state/decisions.log`. Se nao esta la, nao aconteceu.
- Primeiro filtro: baseline test. Condicao vs aleatorio. Se p(KS) > 0.05 → MORTA (condicao e ruido).
- Segundo filtro: hipotese com SL + 17h. p > 0.05 ou metades divergem → MORTA.
- RiskGuardian bloqueia se DD > max, fora do horario, ou max posicoes.
- min_stop_pts=250 (empirico do MT5 demo).
- Specs em `specs/` definem contratos. Codigo segue spec.
- Principios SL/TP em `principios/sl-tp.md` — consultar antes de formular hipotese.
  - SL: P75 hora × alpha(regime ontem). Nunca otimizar.
  - TP: so usa RR fixo como fallback. Se TP faz parte da tese, a estrategia define.
