import sys, os
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Bar
from core.mt5_connector import Mt5Connector

from feed.base import Feed

class Mt5Feed(Feed):
    def __init__(self, symbol: str = "WINM26", timeframe=None,
                 mode: str = "live",
                 from_date: datetime = None, to_date: datetime = None,
                 connector: Mt5Connector = None):
        self.connector = connector or Mt5Connector()
        self.mt5 = self.connector.mt5
        if self.mt5 is None:
            raise ImportError("MetaTrader5 package not installed")
        self.symbol = symbol
        self.timeframe = timeframe or self.mt5.TIMEFRAME_M1
        self.mode = mode
        self._last_time = None
        self._bars: list[Bar] = []
        self._idx = 0

        self.connector.ensure_connected()
        if not self.connector.select_symbol(symbol):
            raise ValueError(f"Symbol {symbol} not found in MarketWatch")
        valid_tfs = [self.mt5.TIMEFRAME_M1, self.mt5.TIMEFRAME_M5, self.mt5.TIMEFRAME_M15,
                     self.mt5.TIMEFRAME_M30, self.mt5.TIMEFRAME_H1, self.mt5.TIMEFRAME_D1]
        if self.timeframe not in valid_tfs:
            raise ValueError(f"Invalid timeframe {self.timeframe}. Use mt5.TIMEFRAME_*")

        if mode == "historical" and from_date and to_date:
            self._bars = self.fetch(from_date, to_date)

    def fetch(self, from_date: datetime, to_date: datetime) -> list[Bar]:
        rates = self.mt5.copy_rates_range(self.symbol, self.timeframe, from_date, to_date)
        if rates is None or len(rates) == 0:
            return []
        result = []
        for r in rates:
            result.append(Bar(
                time=datetime.fromtimestamp(r["time"]),
                open=float(r["open"]),
                high=float(r["high"]),
                low=float(r["low"]),
                close=float(r["close"]),
                volume=int(r["tick_volume"])))
        return result

    def poll(self) -> Bar | None:
        if self.mode == "historical" and self._bars:
            if self._idx >= len(self._bars):
                return None
            bar = self._bars[self._idx]
            self._idx += 1
            return bar

        rates = self.mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, 1)
        if rates is None or len(rates) == 0:
            return None
        r = rates[0]
        ts = int(r["time"])
        if ts == self._last_time:
            return None
        self._last_time = ts
        return Bar(
            time=datetime.fromtimestamp(ts),
            open=float(r["open"]),
            high=float(r["high"]),
            low=float(r["low"]),
            close=float(r["close"]),
            volume=int(r["tick_volume"]))

    def reset(self):
        self._idx = 0

    def close(self):
        pass
