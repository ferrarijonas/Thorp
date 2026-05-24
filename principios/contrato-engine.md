# Contrato ExecutionEngine

```
Arquivo:  execution/engine.py
Propósito: Orquestra uma estratégia contra um feed, gerenciando posições.
Dependências: Feed (obrigatório), Strategy (obrigatório), Broker (obrigatório),
              RiskGuardian (opcional), SlippageModel (opcional)
```

## Interface

```python
class ExecutionEngine:
    def __init__(self, feed, strategy, broker, mode: ExecutionMode,
                 cost: float = 10, risk_guardian=None, slippage=None,
                 convention: str = "worst", volume: float = 1.0):
        ...

    def on_bar(self, bar: Bar) -> Bar:
        """Processa uma barra: verifica saída, checa sinal, executa."""
        ...

    def run(self, max_bars: int | None = None) -> ExecutionResult:
        """Loop completo de backtest: poll + on_bar até exaustão."""
        ...

    def close(self):
        """Libera recursos."""
        ...
```

## Responsabilidades

### on_bar(bar)
1. Incrementa step_count
2. Chama _reconcile() para sincronizar com broker real (se Demo/Real)
3. Se há posição: adiciona barra ao rastro
4. Se há posição: verifica SL/TP/time exit via _check_exit()
5. Se não há posição: chama strategy.on_bar(bar) → Signal
6. Se há Signal: passa por RiskGuardian.process() (preenche stop/target)
7. Passa por SlippageModel.on_entry() (aplica slippage se BT)
8. Chama broker.execute(signal) → Order
9. Se Order.status == FILLED: cria Position
10. Se há posição: verifica saída na mesma barra (worst case)

### run(max_bars)
- Loop: step() → poll() + on_bar()
- Termina quando feed exausto ou max_bars atingido
- Se sobrou posição no final: fecha com pnl=0
- Retorna ExecutionResult

## O que a Engine NÃO faz
- ❌ Não faz loop de live (responsabilidade do bot)
- ❌ Não acessa broker.mt5 diretamente (usa métodos públicos do broker)
- ❌ Não escreve positions.json (responsabilidade do bot)
- ❌ Não renderiza dashboard
- ❌ Não faz health check de dados

## Nomenclatura
- Usar "compra" e "venda" em logs/relatórios (não LONG/SHORT)
- Direction.COMPRA e Direction.VENDA são os nomes primários
