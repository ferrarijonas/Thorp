# Contrato RiskGuardian

```
Arquivo:  core/risk_guardian.py
Propósito: Gerencia risco de cada operação: SL, TP, horário, capital.
           SL e TP são containers (P75/P50 do range), não edge.
```

## Interface

```python
class RiskGuardian:
    def __init__(self, capital: float = 1000, max_dd: float = 200,
                 rr_ratio: float = 1.5, max_positions: int = 1,
                 trade_start: time = time(9, 0), trade_end: time = time(17, 0),
                 min_stop_pts: float = 250):
        ...

    def process(self, signal: Signal | None, bar: Bar | None = None,
                mode: str = "bt", open_positions: int = 0
                ) -> tuple[Signal | None, str]:
        """Filtra e preenche o Signal. Retorna (Signal modificado, motivo).
        
        - Se signal é None ou rejeitado: retorna (None, motivo)
        - Se stop==0: calcula stop = P75 do range (hora ou minuto)
        - Se target==0: calcula target = P50 do range
        - Se max_exit_time==None: define 17h
        - Em Demo/Real: enforce min_stop_pts (250pts)
        """
        ...

    def calibrate(self, df: pd.DataFrame):
        """Calcula P50/P75 por hora e por minuto do CSV.
        Resultados armazenados em state/containers_calibration.json.
        """
        ...

    def post_process(self, pnl: float):
        """Atualiza capital e daily_pnl após fechamento."""
        ...
```

## Regras

### process()
- **NUNCA muta o Signal original** — retorna uma nova instância
- Se o signal for rejeitado por qualquer motivo (DD, horário, max_positions), retorna `(None, "motivo")`
- Se passou, retorna `(signal_preenchido, "ok")`

### SL = P75 do range
- P75 do range histórico da hora (padrão) ou do minuto (se USAR_CONTAINER_MINUTO)
- Percentis calculados do CSV, não otimizados
- Container HORA: P75 do range da hora (ex: 9h ≈ 120pts)
- Container MINUTO: P75 do range do minuto (ex: 9:01 ≈ 315pts)

### TP = P50 do range
- Mediana histórica. Padrão = P50 da hora.
- Se a tese define preço-alvo ou tempo-alvo, o strategy pode setar target > 0.

### Capital e Drawdown
- capital inicial é definido na criação
- DD = max(0, capital_inicial - capital_atual)
- Se DD > max_dd, todas as entradas são bloqueadas até recuperar

### Horário
- trade_start e trade_end definem janela de operação
- Em Demo/Real, fora da janela → bloqueado
- max_exit_time padrão = 17h (fim da sessão)
