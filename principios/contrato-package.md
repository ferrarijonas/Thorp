# Contrato Package

```
Propósito: Thorp como pacote pip instalável.
           Eliminar sys.path.insert(0, ...) de todos os arquivos.
```

## Estrutura

```
pyproject.toml       # definição do pacote
core/
execution/
broker/
feed/
strategy/
scripts/
principios/
state/
tests/
```

## Instalação

```bash
pip install -e .     # modo desenvolvimento (editable)
pip install .        # instalado no ambiente
```

## Imports

Depois de instalado:

```python
from core.types import Bar, Signal, Direction
from feed.csv_feed import CsvFeed
from broker.simulated import SimulatedBroker
from execution.engine import ExecutionEngine
from strategy.H142_strategy import H142Strategy
```

Sem `sys.path.insert(0, ...)` em lugar nenhum.

## pyproject.toml mínimo

```toml
[build-system]
requires = ["setuptools>=64"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "thorp"
version = "0.2.0"
requires-python = ">=3.10"
dependencies = ["pandas", "numpy", "scipy"]

[tool.setuptools.packages.find]
include = ["core*", "execution*", "broker*", "feed*", "strategy*", "scripts*"]
```
