"""Interface abstrata para fontes de dados OHLC."""
from abc import ABC, abstractmethod
from core.types import Bar

class Feed(ABC):

    @abstractmethod
    def poll(self) -> Bar | None:
        """Retorna a próxima barra disponível, ou None se esgotou."""

    def reset(self):
        """Reinicia o feed para a primeira barra (usado em BT)."""

    def close(self):
        """Libera recursos associados ao feed."""
