import sys, os, json
from datetime import datetime, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Signal, Direction, Bar
import pandas as pd

class RiskGuardian:
    def __init__(self, capital: float = 1000, max_dd: float = 200,
                 rr_ratio: float = 1.5, max_positions: int = 1,
                 trade_start: time = time(9, 0), trade_end: time = time(17, 0),
                 min_stop_pts: float = 250):
        self.capital = capital
        self.max_dd = max_dd
        self.rr_ratio = rr_ratio
        self.max_positions = max_positions
        self.trade_start = trade_start
        self.trade_end = trade_end
        self.min_stop_pts = min_stop_pts
        self._p75_por_hora: dict[int, float] = {}
        self._daily_pnl = 0.0
        self._capital_inicial = capital

    def calibrate(self, df: pd.DataFrame):
        df = df.copy()
        df["range"] = df["high"] - df["low"]
        self._p75_por_hora = df.groupby("h")["range"].quantile(0.75).to_dict()
        for h in range(24):
            if h not in self._p75_por_hora:
                self._p75_por_hora[h] = 125

    def process(self, signal: Signal | None, bar: Bar | None = None,
                mode: str = "bt", open_positions: int = 0) -> tuple[Signal | None, str]:
        if signal is None:
            return None, "sem sinal"

        if mode in ("demo", "real"):
            agora = datetime.now().time()
            if agora < self.trade_start or agora > self.trade_end:
                return None, f"fora do horario {self.trade_start}-{self.trade_end}"
            try:
                import MetaTrader5 as mt5
                if not mt5.initialize():
                    return None, "MT5 desconectado"
            except:
                return None, "MT5 nao disponivel"

        if open_positions >= self.max_positions:
            return None, f"maximo {self.max_positions} posicoes"

        dd = self._calc_dd()
        if dd > self.max_dd:
            return None, f"drawdown {dd:.0f} > maximo {self.max_dd}"

        if bar and signal.stop == 0:
            signal.stop = self._calc_stop(signal, bar)
            if self.min_stop_pts and mode in ("demo", "real"):
                if signal.direction == Direction.LONG:
                    min_allowed = bar.open - self.min_stop_pts
                    if signal.stop > min_allowed:
                        signal.stop = min_allowed
                else:
                    max_allowed = bar.open + self.min_stop_pts
                    if signal.stop < max_allowed:
                        signal.stop = max_allowed
        if bar and signal.target == 0:
            signal.target = self._calc_target(signal)
        if signal.max_exit_time is None and bar:
            signal.max_exit_time = bar.time.replace(hour=bar.time.hour + 1) if bar.time.hour < 17 else None
        signal.size = 1

        return signal, "ok"

    def post_process(self, pnl: float):
        self._daily_pnl += pnl
        self.capital += pnl

    def _calc_stop(self, signal: Signal, bar: Bar) -> float:
        stop_pts = self._p75_por_hora.get(bar.time.hour, 125)
        if signal.direction == Direction.LONG:
            return bar.open - stop_pts
        return bar.open + stop_pts

    def _calc_target(self, signal: Signal) -> float:
        stop_dist = abs(signal.entry - signal.stop)
        target_dist = stop_dist * self.rr_ratio
        if signal.direction == Direction.LONG:
            return signal.entry + target_dist
        return signal.entry - target_dist

    def _calc_dd(self) -> float:
        return max(0.0, self._capital_inicial - self.capital)
