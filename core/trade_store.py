"""Persistencia atomica de trades e capital para continuidade 24/7.

Uso:
    store = TradeStore("state/trades.json")
    store.append(trade)       # append atomico
    trades = store.load()     # historico completo
    capital = CapitalStore("state/capital.json")
    capital.save(capital_float, dd_float)
    capital.load() -> (capital, dd)
"""
import sys, os, json, tempfile
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Trade


def _atomic_write(path: str, data):
    """Escreve data (dict ou lista) em path com atomicidade.
    Escreve em .tmp, depois rename. Garante que arquivo nunca fique truncado.
    """
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


class TradeStore:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def append(self, trade: Trade):
        trades = []
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    trades = json.load(f)
            except (json.JSONDecodeError, ValueError):
                trades = []
        d = {
            "strategy_id": trade.strategy_id,
            "direction": trade.direction.name,
            "entry": trade.entry,
            "exit": trade.exit,
            "pnl_points": trade.pnl_points,
            "opened_at": str(trade.opened_at),
            "closed_at": str(trade.closed_at),
            "bars_held": trade.bars_held,
        }
        trades.append(d)
        _atomic_write(self.path, trades)

    def load(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            return []

    def clear(self):
        if os.path.exists(self.path):
            os.remove(self.path)


class CapitalStore:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def save(self, capital: float, drawdown: float, initial_capital: float):
        data = {
            "capital": capital,
            "drawdown": drawdown,
            "initial_capital": initial_capital,
            "updated_at": str(datetime.now()),
        }
        _atomic_write(self.path, data)

    def load(self) -> dict | None:
        if not os.path.exists(self.path):
            return None
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            return None
