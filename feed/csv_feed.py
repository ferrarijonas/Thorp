import sys, os, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Bar
from core.data import load_csv

class CsvFeed:
    def __init__(self, csv_path: str = None, encoding: str = None):
        self.df = load_csv(csv_path, encoding=encoding)
        self._idx = 0

    def poll(self) -> Bar | None:
        if self._idx >= len(self.df):
            return None
        row = self.df.iloc[self._idx]
        self._idx += 1
        return Bar(
            time=row.name,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row["volume"]))

    def reset(self):
        self._idx = 0

    def close(self):
        pass
