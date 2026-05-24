# Catálogo de Scripts

## Pipeline principal

| Script | Função | Uso |
|--------|--------|-----|
| `avaliar_hipotese.py` | BT único com 5 seções (diagnóstico + custo real) | `python scripts/avaliar_hipotese.py Hxxx` |
| `run_bot.py` | Bot 24/7 multi-estratégia (MT5 ao vivo) | `python scripts/run_bot.py --terminal xp` |
| `run_demo.py` | Atalho para `run_bot.py --terminal xp` | `python scripts/run_demo.py` |

## Validação e comparação

| Script | Função | Uso |
|--------|--------|-----|
| `comparar_execucao.py` | Compara BT ideal × BT+slippage × Demo (3 modos) | `python scripts/comparar_execucao.py Hxxx` |
| `testar_vs_baseline.py` | Condição vs direção aleatória (KS test) | `python scripts/testar_vs_baseline.py Hxxx` |
| `testar_containers.py` | Testa containers (SL/TP) via payoff table | `python scripts/testar_containers.py [H143]` |
| `monitor_posicoes.py` | Monitora posições abertas em tempo real | `python scripts/monitor_posicoes.py` |
| `check_mt5.py` | Health check para watchdog (conexão MT5) | `python scripts/check_mt5.py <caminho>` |

## Infraestrutura

| Script | Função | Uso |
|--------|--------|-----|
| `thorp_247.ps1` | Launcher PowerShell para Task Scheduler | Executado pelo Task Scheduler |
| `thorp_startup.bat` | Launcher alternativo (startup manual) | Executado na inicialização |

## Mineração de hipóteses (Markov chain)

| Script | Função | Uso |
|--------|--------|-----|
| `features_markov.py` | Gera dataset 9:00→9:01 com 49 features | `python scripts/features_markov.py` |
| `minerar_markov.py` | Mineração v1: RF + varredura de pares | `python scripts/minerar_markov.py` |
| `minerar_markov_v2.py` | Mineração v2: RF + walk-forward OOS | `python scripts/minerar_markov_v2.py` |
| `batch_screening_markov.py` | Testa 43 regras fortes contra histórico | `python scripts/batch_screening_markov.py` |
| `adversario_markov.py` | Valida regras contra noise, mult-test, estabilidade | `python scripts/adversario_markov.py` |
| `busca_combinatoria.py` | Busca exaustiva por combinações simples | `python scripts/busca_combinatoria.py` |
| `hmm_todos_minutos.py` | HMM vetorizado foco 9:00→9:01 | `python scripts/hmm_todos_minutos.py` |

## Estratégia H140 (análise específica)

| Script | Função |
|--------|--------|
| `walk_forward_h140.py` | Walk-forward mining (treino+teste) para H140 |
| `radiografia_h140.py` | Testa cada preditor vs retorno 9:01 |
| `payoff_table.py` | Pré-computa rastros 9:01→17:00 por dia (~250KB) |

---

## Ciclo de vida

Cada script tem sua própria fase:

- **Manutenção ativa**: `avaliar_hipotese.py`, `run_bot.py`, `run_demo.py`
- **Uso ocasional**: `comparar_execucao.py`, `testar_vs_baseline.py`, `testar_containers.py`, `monitor_posicoes.py`, `check_mt5.py`
- **Legado (mineração H140)**: scripts Markov — mantidos como referência mas não usados em novas hipóteses
- **Infraestrutura**: `thorp_247.ps1`, `thorp_startup.bat`

Novos scripts devem ser adicionados a este catálogo e mantidos junto da estratégia/hipótese que os criou.
