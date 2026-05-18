import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Signal, Direction, Bar

class SlippageModel:
    """Aplica slippage, spread e latencia nos fills do backtest.
    
    BT: degrada os preços pra simular condicoes reais.
    Demo/Real: passa limpo (a realidade ja entrega o efeito).
    """
    def __init__(self, slip_pts: float = 5, spread_pts: float = 2,
                 slip_stop_pts: float = 10, slip_target_pts: float = 5):
        self.slip_pts = slip_pts
        self.spread_pts = spread_pts
        self.slip_stop_pts = slip_stop_pts
        self.slip_target_pts = slip_target_pts

    def on_entry(self, signal: Signal, mode: str = "bt") -> Signal:
        if mode != "bt":
            return signal
        direcao = 1 if signal.direction == Direction.LONG else -1
        sinal = 1 if signal.direction == Direction.LONG else -1
        signal.entry += sinal * self.slip_pts + direcao * self.spread_pts / 2
        if signal.stop:
            signal.stop -= sinal * self.slip_stop_pts
        if signal.target:
            signal.target += sinal * self.slip_target_pts
        return signal

    def on_stop(self, stop_price: float, direction: Direction, mode: str = "bt") -> float:
        if mode != "bt":
            return stop_price
        if direction == Direction.LONG:
            return stop_price - self.slip_stop_pts
        return stop_price + self.slip_stop_pts

    def on_target(self, target_price: float, direction: Direction, mode: str = "bt") -> float:
        if mode != "bt":
            return target_price
        if direction == Direction.LONG:
            return target_price + self.slip_target_pts
        return target_price - self.slip_target_pts
