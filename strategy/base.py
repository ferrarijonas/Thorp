from abc import ABC, abstractmethod
from core.types import Bar, Signal

class Strategy(ABC):
    @abstractmethod
    def on_bar(self, bar: Bar) -> Signal | None:
        ...

    def reset(self):
        pass
