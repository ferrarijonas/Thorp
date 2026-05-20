import pandas as pd
import os

def _detect_encoding(path: str) -> str:
    """Detecta encoding do CSV lendo os primeiros bytes."""
    with open(path, "rb") as f:
        raw = f.read(32)
    if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
        return "utf-16"
    if raw.startswith(b'\xef\xbb\xbf'):
        return "utf-8-sig"
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "utf-16"


def load_csv(path=None, encoding=None):
    """Carrega dados OHLC de um arquivo CSV.

    Args:
        path: Caminho do CSV. Se None, procura automaticamente:
              - Historico_OHLC.csv — completo (encoding auto-detectado)
              - Historico_AMOSTRA.csv — exemplo (utf-8, com cabecalho)
    """
    if path is None:
        base = os.path.join(os.path.dirname(__file__), "..")
        candidates = ["Historico_OHLC.csv", "Historico_AMOSTRA.csv"]
        for candidate in candidates:
            p = os.path.join(base, candidate)
            if os.path.isfile(p):
                path, encoding = p, _detect_encoding(p)
                break
        if path is None:
            raise FileNotFoundError(
                "Nenhum CSV encontrado. Baixe o Historico_OHLC.csv ou "
                "use Historico_AMOSTRA.csv para testes.")

    has_header = path.endswith("AMOSTRA.csv")
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
