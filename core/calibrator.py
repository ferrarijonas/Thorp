"""Calibrador de execucao — mede dados reais do MT5 e alimenta SlippageModel."""
from datetime import datetime, timedelta
import numpy as np
import json

class Calibrator:
    def __init__(self, symbol: str = "WINM26"):
        self.symbol = symbol
        self.spread_por_hora: dict[int, float] = {}
        self.slippage_pts = 0
        self.slip_stop_pts = 0
        self.slip_target_pts = 0
        self.min_stop_pts = 250

    def calibrar(self, from_date: datetime = None, to_date: datetime = None) -> dict:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            raise ConnectionError("MT5 nao conectado")
        mt5.symbol_select(self.symbol, True)

        if to_date is None:
            to_date = datetime.now()
        if from_date is None:
            from_date = to_date - timedelta(days=7)

        rates = mt5.copy_rates_range(self.symbol, mt5.TIMEFRAME_M1, from_date, to_date)
        mt5.shutdown()

        if rates is None or len(rates) == 0:
            raise ValueError("Sem dados MT5 para calibrar")

        spreads: dict[int, list[float]] = {}
        for r in rates:
            h = int(datetime.fromtimestamp(r["time"]).hour)
            s = int(r["spread"])
            if s > 0:
                spreads.setdefault(h, []).append(float(s))

        for h in range(24):
            arr = np.array(spreads.get(h, [5]))
            self.spread_por_hora[h] = int(round(np.percentile(arr, 75)))

        self.slippage_pts = int(np.percentile(
            [s for sl in spreads.values() for s in sl], 75))
        self.slip_stop_pts = int(self.slippage_pts * 3)
        self.slip_target_pts = int(self.slippage_pts * 2)

        return self.dump()

    def dump(self) -> dict:
        return {
            "spread_por_hora": self.spread_por_hora,
            "slippage_pts": self.slippage_pts,
            "slip_stop_pts": self.slip_stop_pts,
            "slip_target_pts": self.slip_target_pts,
            "min_stop_pts": self.min_stop_pts,
        }

    def salvar(self, path: str = None):
        if path is None:
            path = os.path.join(os.path.dirname(__file__), "..", "state", "slippage_calibration.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.dump(), f, indent=2)
        return path

    @staticmethod
    def carregar(path: str = None) -> dict:
        if path is None:
            path = os.path.join(os.path.dirname(__file__), "..", "state", "slippage_calibration.json")
        with open(path) as f:
            return json.load(f)

    @staticmethod
    def criar_slippage(cal: dict = None) -> "SlippageModel":
        from execution.slippage import SlippageModel
        if cal is None:
            cal = Calibrator.carregar()
        return SlippageModel(
            slip_pts=cal["slippage_pts"],
            spread_pts=int(np.median(list(cal["spread_por_hora"].values()))),
            slip_stop_pts=cal["slip_stop_pts"],
            slip_target_pts=cal["slip_target_pts"],
        )

    @staticmethod
    def criar_risk_guardian(cal: dict = None, capital: float = 1000, max_dd: float = 99999) -> "RiskGuardian":
        from core.risk_guardian import RiskGuardian
        from core.data import load_csv
        if cal is None:
            cal = Calibrator.carregar()
        rg = RiskGuardian(capital=capital, max_dd=max_dd, rr_ratio=1.5,
                          min_stop_pts=cal.get("min_stop_pts", 250))
        rg.calibrate(load_csv())
        return rg

if __name__ == "__main__":
    c = Calibrator()
    cal = c.calibrar()
    path = c.salvar()
    print(f"Calibracao salva em {path}")
    print(json.dumps(cal, indent=2))
