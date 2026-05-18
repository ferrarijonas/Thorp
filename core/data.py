import pandas as pd
import os

def load_csv(path=None, encoding=None):
    """Carrega dados OHLC de um arquivo CSV.
    
    Args:
        path: Caminho do CSV. Se None, procura automaticamente:
              - Historico_OHLC.csv (utf-16, sem cabecalho) — completo
              - Historico_AMOSTRA.csv (utf-8, com cabecalho) — exemplo
    """
    if path is None:
        base = os.path.join(os.path.dirname(__file__), "..")
        for candidate, enc in [("Historico_OHLC.csv", "utf-16"),
                                ("Historico_AMOSTRA.csv", "utf-8")]:
            p = os.path.join(base, candidate)
            if os.path.isfile(p):
                path, encoding = p, enc
                break
        if path is None:
            raise FileNotFoundError(
                "Nenhum CSV encontrado. Baixe o Historico_OHLC.csv ou "
                "use Historico_AMOSTRA.csv para testes.")

    has_header = encoding == "utf-8"
    df = pd.read_csv(path, header=0 if has_header else None,
        names=["datetime","open","high","low","close","volume"] if not has_header else None,
        encoding=encoding, parse_dates=["datetime"])
    df.set_index("datetime", inplace=True)
    for col in ["open","high","low","close"]:
        df[col] = df[col].astype(float)
    df["volume"] = df["volume"].astype(int)
    df["h"] = df.index.hour
    df["m"] = df.index.minute
    df["dow"] = df.index.dayofweek
    return df
