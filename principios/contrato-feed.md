# Contrato Feed

```
Arquivo:  feed/base.py
Propósito: Interface abstrata para fontes de dados OHLC.
Implementações: CsvFeed (CSV), Mt5Feed (MT5 ao vivo/histórico)
```

## Interface

```python
from abc import ABC, abstractmethod
from core.types import Bar

class Feed(ABC):

    @abstractmethod
    def poll(self) -> Bar | None:
        """Retorna a próxima barra disponível, ou None se esgotou."""
        ...

    def reset(self):
        """Reinicia o feed para a primeira barra (usado em BT)."""
        pass

    def close(self):
        """Libera recursos associados ao feed."""
        pass
```

## Regras

### poll()
- Chamada repetidamente pela engine (on_bar → step → poll)
- Retorna `Bar` se há próxima barra
- Retorna `None` se o feed terminou
- Em modo live, retorna `None` se não há barra nova ainda (dedup)

### reset()
- Coloca o índice de volta ao início
- Usado em BT para re-executar o mesmo feed
- Em live, é no-op (não dá pra resetar o futuro)

### close()
- Libera recursos (arquivos, conexões de rede)
- Idempotente: chamar 2x não quebra

## Implementações

### CsvFeed
- Lê de DataFrame pandas pré-carregado
- poll() avança índice interno
- reset() zera índice
- Suporta filtro prévio (ex: `CsvFeed(df=df.between_time("09:00","17:00"))`)

### Mt5Feed
- Lê do terminal MetaTrader 5 ao vivo
- poll() copia rates do MT5 e deduplica por timestamp
- Modo "historical": pré-carrega range de datas e poll() avança índice
- Modo "live": poll() a cada chamada, sem cache interno
- reset() no-op em live, zera índice em historical
