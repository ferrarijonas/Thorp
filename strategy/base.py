from abc import ABC, abstractmethod
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Bar, Signal

class Strategy(ABC):
    @abstractmethod
    def on_bar(self, bar: Bar) -> Signal | None:
        ...

    def reset(self):
        pass
