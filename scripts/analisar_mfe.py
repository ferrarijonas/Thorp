import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd, numpy as np
from core.types import Bar, Signal, Direction
import logging
logging.disable(logging.CRITICAL)
os.environ["OPCODE_LOG"] = "0"

CSV = "C:\\Users\\Alice\\AppData\\Roaming\\MetaQuotes\\Terminal\\Common\\Files\\Historico_OHLC.csv"

def _load_csv(csv_path=None):
    path = csv_path or CSV
    df = pd.read_csv(path, header=None,
        names=["datetime","open","high","low","close","volume"],
        encoding="utf-16", parse_dates=["datetime"])
    df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)
    df["h"] = df["datetime"].dt.hour
    df["m"] = df["datetime"].dt.minute
    df["date"] = df["datetime"].dt.date
    return df

def _bar_from_row(row):
    return Bar(time=row["datetime"], open=row["open"], high=row["high"],
               low=row["low"], close=row["close"], volume=int(row["volume"]))

def gerar_todos_sinais(stgy_class, df):
    stgy = stgy_class()
    stgy.reset()
    sinais = []
    for i, (_, row) in enumerate(df.iterrows()):
        sinal = stgy.on_bar(_bar_from_row(row))
        if sinal is not None:
            sinais.append((i, sinal))
    return sinais

def calcular_mfe(sinais, df, forward_max=480):
    mfes, picos = [], []
    for i, sinal in sinais:
        fim = min(i + 1 + forward_max, len(df))
        fatias = df.iloc[i+1:fim]
        if len(fatias) == 0:
            continue
        if sinal.direction == Direction.LONG:
            melhor = fatias["high"].max() - sinal.entry
            idx_max = fatias["high"].idxmax()
        else:
            melhor = sinal.entry - fatias["low"].min()
            idx_max = fatias["low"].idxmin()
        candles_ate_pico = int(fatias.index.get_loc(idx_max)) if melhor > 0 else 0
        mfes.append(melhor)
        picos.append(candles_ate_pico)
    return np.array(mfes), np.array(picos)

def bootstrap_pct(vals, pct, n_boot=5000):
    rng = np.random.default_rng(42)
    boots = np.percentile(rng.choice(vals, size=(n_boot, len(vals)), replace=True), pct, axis=1)
    return {
        "pct": pct,
        "valor": float(np.percentile(vals, pct)),
        "ic_inf": float(np.percentile(boots, 2.5)),
        "ic_sup": float(np.percentile(boots, 97.5)),
        "cv": float(boots.std() / boots.mean()) if boots.mean() > 0 else 0
    }

def testar_target_oos(df, stgy_class, target_pts):
    from execution.engine import ExecutionEngine
    from feed.csv_feed import CsvFeed
    from broker.simulated import SimulatedBroker
    from core.types import ExecutionMode
    from core.risk_guardian import RiskGuardian
    from io import StringIO

    class SilentFeed(CsvFeed):
        def __init__(self, df):
            self._df = df.copy()
            self._idx = 0
        def poll(self):
            if self._idx >= len(self._df):
                return None
            row = self._df.iloc[self._idx]
            self._idx += 1
            return Bar(time=row["datetime"], open=row["open"], high=row["high"],
                       low=row["low"], close=row["close"], volume=int(row["volume"]))
        def close(self):
            pass

    class StgyWrap(stgy_class):
        def on_bar(self, bar):
            s = super().on_bar(bar)
            if s is not None:
                s.target = s.entry + target_pts if s.direction == Direction.LONG else s.entry - target_pts
                s.stop = 0
            return s

    cal_df = _load_csv()
    rg = RiskGuardian(1000, 99999, 1.5)
    rg.calibrate(cal_df)

    old_stdout = sys.stdout
    sys.stdout = StringIO()
    e = ExecutionEngine(SilentFeed(df), StgyWrap(), SimulatedBroker(10), ExecutionMode.BT, risk_guardian=rg)
    r = e.run()
    sys.stdout = old_stdout

    return {
        "target": target_pts,
        "trades": r.total,
        "media": round(r.media, 1),
        "wr": round(r.win_rate, 1),
        "p": round(r.p_valor, 4),
        "metades_ok": r.metades_ok,
        "status": "PASSOU" if r.p_valor < 0.05 and r.metades_ok else "MORTA"
    }

def analisar_mfe(strategy_class, csv_path=None, forward_max=480, train_pct=0.7):
    df = _load_csv(csv_path)
    datas = sorted(df["date"].unique())
    n_total = len(datas)
    corte = int(n_total * train_pct)
    datas_train = set(datas[:corte])
    datas_test = set(datas[corte:])

    df_train = df[df["date"].isin(datas_train)].copy()
    df_test = df[df["date"].isin(datas_test)].copy()

    sinais = gerar_todos_sinais(strategy_class, df_train)
    mfes, picos = calcular_mfe(sinais, df_train, forward_max)

    if len(mfes) < 10:
        return {"erro": f"Apenas {len(mfes)} sinais no treino. Amostra insuficiente."}

    resultado = {
        "dias_train": len(datas_train),
        "dias_test": len(datas_test),
        "sinais_train": len(sinais),
        "mfe_amostras": len(mfes),
        "mfe_medio": float(round(mfes.mean(), 1)),
        "mfe_por_pct": {},
        "validacao_oos": []
    }

    for pct in [50, 75, 90]:
        res = bootstrap_pct(mfes, pct)
        tp_pico = float(np.percentile(picos, pct))
        resultado["mfe_por_pct"][f"P{pct}"] = {**res, "tempo_ate_pico_min": tp_pico}

    targets = sorted(set(int(round(np.percentile(mfes, p))) for p in [50, 75, 90] if np.percentile(mfes, p) > 0))
    for t in targets:
        resultado["validacao_oos"].append(testar_target_oos(df_test, strategy_class, t))

    return resultado


if __name__ == "__main__":
    hid = sys.argv[1].upper() if len(sys.argv) > 1 else "H102"
    mod = __import__(f"strategy.{hid}_strategy", fromlist=[f"{hid}Strategy"])
    stgy_class = getattr(mod, f"{hid}Strategy")
    res = analisar_mfe(stgy_class)
    print(res)
