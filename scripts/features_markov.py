"""Gera dataset 9:00 -> 9:01 com 49 features atomicas (rolling, sem vazamento).
Uso: python scripts/features_markov.py
Saida: state/features_markov_dataset.csv
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd
import numpy as np
from core.data import load_csv

np.random.seed(42)

def build_dataset(df):
    """Monta tabela dia-a-dia com candle 9:00, 9:01, e D-1."""
    df = df.between_time("09:00", "17:00").copy()
    df["date"] = df.index.date

    # Candle 9:00
    m9 = (df["h"] == 9) & (df["m"] == 0)
    d9 = df[m9][["open","high","low","close","volume","date"]].copy()
    d9.columns = ["o9","h9","l9","c9","v9","date"]

    # Candle 9:01
    m01 = (df["h"] == 9) & (df["m"] == 1)
    d01 = df[m01][["open","close","date"]].copy()
    d01.columns = ["o01","c01","date"]

    # D-1 stats (range diario total, etc)
    d1 = df.groupby("date").agg(
        o_d1=("open","first"),
        c_d1=("close","last"),
        h_d1=("high","max"),
        l_d1=("low","min"),
        v_d1=("volume","sum"),
        h9_d1=("high", lambda x: x.iloc[0] if len(x) > 0 else 0),
        l9_d1=("low", lambda x: x.iloc[0] if len(x) > 0 else 0),
        o9_d1=("open", lambda x: x.iloc[0] if len(x) > 0 else 0),
        c9_d1=("close", lambda x: x.iloc[0] if len(x) > 0 else 0),
        v9_d1=("volume", lambda x: x.iloc[0] if len(x) > 0 else 0),
    )
    d1.index.name = "date"

    # Merge
    m = d9.merge(d01, on="date", how="inner")
    m = m.merge(d1.shift(1), on="date", how="left")  # D-1 real
    m = m.dropna(subset=["c_d1"]).reset_index(drop=True)
    m = m.sort_values("date").reset_index(drop=True)
    return m

def compute_rolling(dat):
    """Rolling 21d stats para features que precisam de normalizacao."""
    cols = {
        "range_9": dat["h9"] - dat["l9"],
        "body_ratio": (dat["c9"] - dat["o9"]).abs() / (dat["h9"] - dat["l9"] + 0.001),
        "vol_9": dat["v9"].astype(float),
        "gap": dat["o9"] - dat["c_d1"],
    }
    p = {}
    for name, series in cols.items():
        r = series.rolling(21, min_periods=10)
        p[f"{name}_avg"] = r.mean().values
        p[f"{name}_std"] = r.std().values
        p[f"{name}_p50"] = r.median().values
        p[f"{name}_p25"] = r.quantile(0.25).values
        p[f"{name}_p75"] = r.quantile(0.75).values
    # Rank: fracao de dias nos ultimos 21 que foram MENORES que hoje
    for name, series in cols.items():
        rank = series.rolling(21, min_periods=10).apply(
            lambda x: (x[:-1] < x.iloc[-1]).sum() / max(len(x[:-1]), 1) if len(x) > 1 else 0.5)
        p[f"{name}_rank"] = rank.values
    for k, v in p.items():
        dat[k] = v
    return dat

def compute_features(dat):
    """Computa as 49 features."""
    P = dat.copy()
    n = len(P)

    # Variaveis auxiliares
    r9 = P["h9"] - P["l9"]
    b9 = P["c9"] - P["o9"]
    body = b9.abs()
    body_ratio = body / (r9 + 0.001)
    mid = (P["h9"] + P["l9"]) / 2
    pos_close = (P["c9"] - P["l9"]) / (r9 + 0.001)
    sup_shadow = (P["h9"] - np.maximum(P["o9"], P["c9"])) / (r9 + 0.001)
    inf_shadow = (np.minimum(P["o9"], P["c9"]) - P["l9"]) / (r9 + 0.001)
    gap = P["o9"] - P["c_d1"]
    green_9 = (b9 > 0).astype(int)
    fractal = r9 / (body + 1)
    wick_asym = sup_shadow / (inf_shadow + 0.001)

    # D-1 features (pre-computadas)
    d1_r9 = P["h9_d1"] - P["l9_d1"]
    d1_b9 = P["c9_d1"] - P["o9_d1"]
    d1_green_9 = (d1_b9 > 0).astype(int)
    d1_body_ratio = d1_b9.abs() / (d1_r9 + 0.001)
    d1_pos_close = (P["c9_d1"] - P["l9_d1"]) / (d1_r9 + 0.001)
    d1_sup_shadow = (P["h9_d1"] - np.maximum(P["o9_d1"], P["c9_d1"])) / (d1_r9 + 0.001)
    d1_inf_shadow = (np.minimum(P["o9_d1"], P["c9_d1"]) - P["l9_d1"]) / (d1_r9 + 0.001)

    # Target
    P["target_ret"] = P["c01"] - P["o01"]
    P["target_dir"] = (P["target_ret"] > 0).astype(int)

    # =====================================
    # GEOMETRIA 9:00 (10)
    # =====================================
    P["range_9"] = r9
    P["body_ratio"] = body_ratio
    P["pos_close"] = pos_close
    P["shadow_up"] = sup_shadow
    P["shadow_dn"] = inf_shadow
    P["fractal"] = fractal
    P["wick_asym"] = wick_asym
    P["vol_9"] = P["v9"].astype(float)
    P["gap"] = gap
    P["green_9"] = green_9

    # =====================================
    # FORMA PURA (6)
    # =====================================
    P["o_is_h"] = (P["o9"] == P["h9"]).astype(int)
    P["o_is_l"] = (P["o9"] == P["l9"]).astype(int)
    P["c_is_h"] = (P["c9"] == P["h9"]).astype(int)
    P["c_is_l"] = (P["c9"] == P["l9"]).astype(int)
    P["body_abs"] = body
    P["log_return"] = np.log(P["c9"] / (P["o9"] + 0.001))

    # =====================================
    # VOLUME (3)
    # =====================================
    P["vol_9_rank"] = P["vol_9_rank"]
    # pressao compradora
    vol_buy = P["v9"] * (P["c9"] - mid) / (r9 + 0.001)
    vol_buy = vol_buy.clip(lower=0)
    P["pressao_compradora"] = vol_buy / (P["v9"].astype(float) + 0.001)
    P["order_flow"] = P["v9"].astype(float) * np.sign(b9)

    # =====================================
    # GAP (4)
    # =====================================
    P["gap_rank"] = P["gap_rank"]
    P["gap_up"] = (gap > 0).astype(int)
    P["gap_pct"] = gap / (P["c_d1"] + 0.001)
    P["gap_rel_range"] = gap / (r9 + 0.001)

    # =====================================
    # REGIME (5)
    # =====================================
    P["range_9_rank"] = P["range_9_rank"]
    P["body_ratio_rank"] = P["body_ratio_rank"]
    P["zscore_range"] = (r9 - P["range_9_avg"]) / (P["range_9_std"] + 0.001)
    P["zscore_vol"] = (P["v9"].astype(float) - P["vol_9_avg"]) / (P["vol_9_std"] + 0.001)
    regime = pd.Series(1, index=P.index)
    regime[r9 > P["range_9_p75"]] = 2
    regime[r9 < P["range_9_p25"]] = 0
    P["regime_vol"] = regime.astype(int)

    # =====================================
    # D-1 (6)
    # =====================================
    P["green_9_d1"] = d1_green_9
    # green_01_d1 — direcao do 9:01 de ontem (shift do target_dir)
    P["green_01_d1"] = P["target_dir"].shift(1).fillna(0).astype(int)
    P["acertou_ontem"] = (d1_green_9 == P["green_01_d1"]).astype(int)
    P["range_d1_total"] = P["h_d1"] - P["l_d1"]
    P["range_9_d1"] = d1_r9
    P["retorno_d1"] = (P["c_d1"] - P["o_d1"]) / (P["o_d1"] + 0.001)

    # =====================================
    # CRUZAMENTO (2)
    # =====================================
    P["range_ratio"] = r9 / (d1_r9 + 0.001)
    P["fragilidade"] = r9 / ((P["h_d1"] - P["l_d1"]) + 0.001)

    # =====================================
    # TEMPORAL (9)
    # =====================================
    def calc_streak(series):
        g = (series != series.shift()).cumsum()
        s = series.groupby(g).cumcount() + 1
        return s.shift(1).fillna(0).astype(int)  # streak ANTES de hoje

    P["streak_green_9"] = calc_streak(green_9)
    P["streak_red_9"] = calc_streak((b9 < 0).astype(int))
    P["streak_range_high"] = calc_streak((r9 > P["range_9_p50"]).astype(int))
    P["streak_gap_up"] = calc_streak((gap > 0).astype(int))
    P["streak_vol_high"] = calc_streak((P["v9"].astype(float) > P["vol_9_p50"]).astype(int))

    P["delta_range"] = r9 - d1_r9
    P["delta_body"] = body_ratio - d1_body_ratio
    P["delta_vol"] = P["v9"].astype(float) - P["v9_d1"].astype(float)
    P["delta_gap"] = gap - P["gap"].shift(1)

    # =====================================
    # POSICAO (3)
    # =====================================
    P["round_dist"] = (P["c9"] % 100).apply(lambda x: min(x, 100 - x))
    round_nearest = (P["c9"] / 100).round() * 100
    P["round_breach"] = (
        (P["l9"] < round_nearest) & (P["c9"] < round_nearest) & (P["o9"] > round_nearest)
    ).astype(int)
    drift = pd.Series(1, index=P.index)
    drift[P["o9"] > P["h_d1"]] = 2
    drift[P["o9"] < P["l_d1"]] = 0
    P["open_drift"] = drift.astype(int)

    # =====================================
    # GAP_DINAMICO (1) — baseado em rank rolling, nao em quantil estatico
    # =====================================
    P["gap_big"] = (P["gap_rank"] > 0.90).astype(int)

    return P

def main():
    print("Carregando dados...")
    df = load_csv()
    print(f"Total candles: {len(df):,}")

    print("Montando dataset dia-a-dia...")
    dat = build_dataset(df)
    print(f"Dias alinhados: {len(dat)}")

    print("Computando rolling stats (21d)...")
    dat = compute_rolling(dat)

    print("Computando 49 features...")
    dat = compute_features(dat)

    # Remove linhas com NaN (primeiros dias sem rolling window)
    before = len(dat)
    dat = dat.dropna()
    print(f"Linhas validas: {len(dat)} (removidas {before - len(dat)})")

    # Colunas finais
    feat_cols = [
        # GEOMETRIA (10)
        "range_9", "body_ratio", "pos_close", "shadow_up", "shadow_dn",
        "fractal", "wick_asym", "vol_9", "gap", "green_9",
        # FORMA PURA (6)
        "o_is_h", "o_is_l", "c_is_h", "c_is_l", "body_abs", "log_return",
        # VOLUME (3)
        "vol_9_rank", "pressao_compradora", "order_flow",
        # GAP (4)
        "gap_rank", "gap_up", "gap_pct", "gap_rel_range",
        # REGIME (5)
        "range_9_rank", "body_ratio_rank", "zscore_range", "zscore_vol", "regime_vol",
        # D-1 (6)
        "green_9_d1", "green_01_d1", "acertou_ontem",
        "range_d1_total", "range_9_d1", "retorno_d1",
        # CRUZAMENTO (2)
        "range_ratio", "fragilidade",
        # TEMPORAL (9)
        "streak_green_9", "streak_red_9", "streak_range_high",
        "streak_gap_up", "streak_vol_high",
        "delta_range", "delta_body", "delta_vol", "delta_gap",
        # POSICAO (3)
        "round_dist", "round_breach", "open_drift",
        # GAP DINAMICO (1)
        "gap_big",
    ]
    assert len(feat_cols) == 49, f"Esperado 49 features, tem {len(feat_cols)}"

    out = dat[["date", "target_dir", "target_ret"] + feat_cols].copy()
    out["date"] = out["date"].astype(str)

    out_path = os.path.join(os.path.dirname(__file__), "..", "state",
                            "features_markov_dataset.csv")
    out.to_csv(out_path, index=False)
    print(f"\nSalvo: {out_path}")
    print(f"Shape: {out.shape}")
    print(f"Dias: {out['date'].iloc[0]} a {out['date'].iloc[-1]}")
    print(f"Baseline (P(verde)): {out['target_dir'].mean()*100:.1f}%")
    print(f"Features: {len(feat_cols)}")

if __name__ == "__main__":
    main()
