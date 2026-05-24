"""Interface abstrata para corretoras (execução de ordens e consulta de posições)."""
from abc import ABC, abstractmethod
from typing import Any
from core.types import Signal, Order, Position

class Broker(ABC):

    @abstractmethod
    def execute(self, signal: Signal, volume: float = 1.0) -> Order:
        """Envia uma ordem ao mercado. SEMPRE retorna Order (nunca None)."""

    @abstractmethod
    def fetch_positions(self) -> list[Position]:
        """Retorna lista de posições abertas no broker."""

    def get_exit_info(self, ticket: str) -> dict | None:
        """Retorna {exit_price, closed_at} do histórico do ticket, ou None."""
        return None

    def close(self):
        """Libera recursos associados ao broker."""
