import pandas as pd

def load_csv(path="Historico_OHLC.csv", encoding="utf-16"):
    df = pd.read_csv(path, header=None,
        names=["datetime","open","high","low","close","volume"],
        encoding=encoding, parse_dates=["datetime"])
    df.set_index("datetime", inplace=True)
    df[["open","high","low","close"]] = df[["open","high","low","close"]].astype(float)
    df["volume"] = df["volume"].astype(int)
    df["h"] = df.index.hour
    df["m"] = df.index.minute
    df["dow"] = df.index.dayofweek
    return df
