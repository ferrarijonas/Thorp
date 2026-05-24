"""Aplica slippage, spread e latencia nos fills do backtest.
BT: degrada os precos pra simular condicoes reais.
Demo/Real: passa limpo (a realidade ja entrega o efeito).
"""
import sys, os
from dataclasses import replace
from core.types import Signal, Direction, Bar

class SlippageModel:
    def __init__(self, slip_pts: float = 5, spread_pts: float = 2,
                 slip_stop_pts: float = 10, slip_target_pts: float = 5):
        self.slip_pts = slip_pts
        self.spread_pts = spread_pts
        self.slip_stop_pts = slip_stop_pts
        self.slip_target_pts = slip_target_pts

    def on_entry(self, signal: Signal, mode: str = "bt") -> Signal:
        if mode != "bt":
            return signal
        sinal = 1 if signal.direction == Direction.LONG else -1
        new_entry = signal.entry + sinal * self.slip_pts + sinal * self.spread_pts / 2
        new_stop = signal.stop - sinal * self.slip_stop_pts if signal.stop else 0
        new_target = signal.target + sinal * self.slip_target_pts if signal.target else 0
        return replace(signal, entry=new_entry, stop=new_stop, target=new_target)

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
