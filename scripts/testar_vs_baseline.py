import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd, numpy as np
from scipy import stats
from core.types import Bar, Direction
import logging, warnings
logging.disable(logging.CRITICAL)
warnings.filterwarnings("ignore")
os.environ["OPCODE_LOG"] = "0"

CSV = "C:\\Users\\Alice\\AppData\\Roaming\\MetaQuotes\\Terminal\\Common\\Files\\Historico_OHLC.csv"

def _load_csv(csv_path=None):
    path = csv_path or CSV
    df = pd.read_csv(path, header=None,
        names=["datetime","open","high","low","close","volume"],
        encoding="utf-16", parse_dates=["datetime"])
    df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)
    df["date"] = df["datetime"].dt.date
    return df

def _bar_from_row(row):
    return Bar(time=row["datetime"], open=row["open"], high=row["high"],
               low=row["low"], close=row["close"], volume=int(row["volume"]))

def _gerar_sinais(stgy_class, df):
    stgy = stgy_class()
    stgy.reset()
    sinais = []
    for i, (_, row) in enumerate(df.iterrows()):
        sinal = stgy.on_bar(_bar_from_row(row))
        if sinal is not None:
            sinais.append((i, sinal))
    return sinais

def _mfe_unico(i, direction, entry, df, forward_max=480):
    fim = min(i + 1 + forward_max, len(df))
    fatias = df.iloc[i+1:fim]
    if len(fatias) == 0:
        return None
    if direction == Direction.LONG:
        melhor = fatias["high"].max() - entry
    else:
        melhor = entry - fatias["low"].min()
    return melhor

def testar_vs_baseline(stgy_class, csv_path=None, forward_max=480, n_baseline=1000):
    df = _load_csv(csv_path)
    rng = np.random.default_rng(42)

    sinais = _gerar_sinais(stgy_class, df)
    if len(sinais) < 5:
        return {"erro": f"Apenas {len(sinais)} sinais. Amostra insuficiente."}

    # MFE da hipotese
    mfe_hyp = []
    for i, sinal in sinais:
        m = _mfe_unico(i, sinal.direction, sinal.entry, df, forward_max)
        if m is not None and m > 0:
            mfe_hyp.append(m)
    mfe_hyp = np.array(mfe_hyp)
    n_hyp = len(mfe_hyp)

    if n_hyp < 5:
        return {"erro": "MFE calculado insuficiente."}

    # Baseline: mesmos indices, direcao aleatoria
    baseline_all = []
    for _ in range(n_baseline):
        b = []
        for i, sinal in sinais:
            direcao_rand = Direction.LONG if rng.random() > 0.5 else Direction.SHORT
            m = _mfe_unico(i, direcao_rand, sinal.entry, df, forward_max)
            if m is not None and m > 0:
                b.append(m)
        baseline_all.append(np.array(b))

    # Distribuicao media do baseline
    mfe_base_medias = np.array([b.mean() for b in baseline_all])
    mfe_base_pooled = np.concatenate(baseline_all)

    # Teste t: hipotese vs baseline (media de cada rodada)
    t_stat, p_valor = stats.ttest_1samp(mfe_base_medias, mfe_hyp.mean())

    # KS test nas distribuicoes brutas
    ks_stat, ks_p = stats.ks_2samp(mfe_hyp, mfe_base_pooled)

    # Efeito: quantas rodadas baseline sao melhores que a hipotese?
    vezes_pior = (mfe_base_medias > mfe_hyp.mean()).sum()
    fracao_pior = vezes_pior / n_baseline

    resultado = {
        "sinais": n_hyp,
        "rodadas_baseline": n_baseline,
        "mfe_hipotese_medio": round(float(mfe_hyp.mean()), 1),
        "mfe_hipotese_p50": float(np.percentile(mfe_hyp, 50)),
        "mfe_hipotese_p75": float(np.percentile(mfe_hyp, 75)),
        "mfe_baseline_medio": round(float(mfe_base_pooled.mean()), 1),
        "mfe_baseline_p50": float(np.percentile(mfe_base_pooled, 50)),
        "mfe_baseline_p75": float(np.percentile(mfe_base_pooled, 75)),
        "teste_t_p": round(float(p_valor), 4),
        "ks_p": round(float(ks_p), 4),
        "baseline_melhor_que_hipotese": f"{fracao_pior:.1%}",
        "veredito": "CONDICAO TEM EDGE" if p_valor < 0.05 and ks_p < 0.05 else "CONDICAO E RUIDO"
    }
    return resultado

if __name__ == "__main__":
    hid = sys.argv[1].upper() if len(sys.argv) > 1 else "H102"
    mod = __import__(f"strategy.{hid}_strategy", fromlist=[f"{hid}Strategy"])
    stgy_class = getattr(mod, f"{hid}Strategy")
    res = testar_vs_baseline(stgy_class)
    for k, v in res.items():
        print(f"  {k}: {v}")
