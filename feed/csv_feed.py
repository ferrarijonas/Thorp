import sys, os, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Bar
from core.data import load_csv
import numpy as np

from feed.base import Feed

class CsvFeed(Feed):
    def __init__(self, csv_path: str = None, encoding: str = None, df=None):
        if df is None:
            df = load_csv(csv_path, encoding=encoding)
        self.df = df
        self._times = df.index.values
        self._opens = df["open"].values.astype(np.float64)
        self._highs = df["high"].values.astype(np.float64)
        self._lows = df["low"].values.astype(np.float64)
        self._closes = df["close"].values.astype(np.float64)
        self._volumes = df["volume"].values.astype(np.int32)
        self._idx = 0

    def poll(self) -> Bar | None:
        if self._idx >= len(self._times):
            return None
        i = self._idx
        self._idx += 1
        return Bar(
            time=pd.Timestamp(self._times[i]),
            open=float(self._opens[i]),
            high=float(self._highs[i]),
            low=float(self._lows[i]),
            close=float(self._closes[i]),
            volume=int(self._volumes[i]))

    def reset(self):
        self._idx = 0

    def close(self):
        pass
