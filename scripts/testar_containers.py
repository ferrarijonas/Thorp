"""Testa containers via payoff table: MFE, MAE, SL/TP, time exit.
Uso: python scripts/testar_containers.py [H143] [H147]
Sem args: testa as 6 (H142-H147).
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
from scipy import stats
import pandas as pd

COST = 10  # custo round-trip

def load_payoff_table():
    with open("state/payoff_table.json") as f:
        return json.load(f)

def load_features():
    return pd.read_csv("state/features_markov_dataset.csv")

def load_rules():
    with open("state/mineracao_markov_v2_results.json") as f:
        return json.load(f)

def parse_rule(rule_str):
    import re
    parts = [p.strip() for p in rule_str.split(",")]
    conds = []
    for p in parts:
        m = re.match(r"([\w_]+)(<=|>)(-?\d+\.?\d*)", p)
        if m:
            conds.append((m.group(1), m.group(2), float(m.group(3))))
    return conds

def apply_rule(df, conditions, rule_direction):
    mask = pd.Series(True, index=df.index)
    for col, op, val in conditions:
        if col not in df.columns:
            return pd.Series(False, index=df.index)
        if op == "<=":
            mask &= df[col] <= val
        else:
            mask &= df[col] > val
    return mask


def query_pnl(rastro, direction, sl_pts, tp_pts, convention):
    """Retorna PnL sem custo."""
    entry = rastro["e"]
    H = np.array(rastro["h"])  # running max H - entry
    L = np.array(rastro["l"])  # running min L - entry
    n = rastro["n"]

    if direction == "VENDA":
        # SL = acima da entrada (H >= +sl), TP = abaixo da entrada (L <= -tp)
        sl_idx = np.argmax(H >= sl_pts) if (H >= sl_pts).any() else n
        tp_idx = np.argmax(L <= -tp_pts) if (L <= -tp_pts).any() else n
    else:
        # SL = abaixo da entrada (L <= -sl), TP = acima da entrada (H >= +tp)
        sl_idx = np.argmax(L <= -sl_pts) if (L <= -sl_pts).any() else n
        tp_idx = np.argmax(H >= tp_pts) if (H >= tp_pts).any() else n

    if sl_idx == n and tp_idx == n:
        # Time exit at last close
        close = rastro["c"][-1]
        return entry - close if direction == "VENDA" else close - entry

    # Se SL e TP na mesma barra, convenção decide
    if sl_idx == tp_idx and sl_idx < n:
        if convention == "worst":
            return -sl_pts
        else:
            return tp_pts

    if sl_idx < tp_idx:
        return -sl_pts
    else:
        return tp_pts


def mfe_mae(rastro, direction):
    """Retorna (MFE, MAE) em pts."""
    entry = rastro["e"]
    H = np.array(rastro["h"])
    L = np.array(rastro["l"])

    if direction == "COMPRA":
        mfe = H.max()
        mae = L.min()
    else:
        mfe = -L.min()  # L negativo = lucro pra VENDA
        mae = H.max()   # H positivo = perda pra VENDA
    return round(float(mfe), 1), round(float(mae), 1)


def test_rule_with_table(rule, dat, table, rule_direction):
    conds = parse_rule(rule["regra"])
    mask = apply_rule(dat, conds, rule_direction)
    days = dat.loc[mask, "date"].values

    if len(days) < 5:
        return None

    # Converte days pra string (formato da tabela)
    day_strs = [str(d)[:10] for d in days]
    rastros = [table["rastros"].get(d) for d in day_strs]
    valid = [(d, r) for d, r in zip(days, rastros) if r is not None]

    # Containers a testar
    containers = [
        ("time_9:02", None),  # time exit: nao usa SL/TP, fecha no close da 2a barra
        ("SL345_TP245", (345, 245)),
        ("SL275_TP180", (275, 180)),
        ("SL200_TP150", (200, 150)),
        ("SL400_TP300", (400, 300)),
    ]

    results = {}

    for cname, cparams in containers:
        if cparams is None:
            # Time exit: fecha no close da barra index 1 (9:02)
            pnls = []
            for day, r in valid:
                close = r["c"][1] if r["n"] > 1 else r["e"]
                entry = r["e"]
                pnl = entry - close if rule_direction == "VENDA" else close - entry
                pnls.append(pnl)
        else:
            sl_, tp_ = cparams
            pnls = []
            for day, r in valid:
                pnl = query_pnl(r, rule_direction, sl_, tp_, "worst")
                pnls.append(pnl)

        pnls_cost = [p - COST for p in pnls]
        arr = np.array(pnls_cost)
        n = len(arr)
        media = arr.mean()
        wr = (arr > 0).mean() * 100
        _, p_val = stats.ttest_1samp(arr, 0)
        p_val = p_val / 2 if media > 0 else 1 - p_val / 2
        sharpe = media / arr.std() if arr.std() > 0 else 0
        mfe, mae = 0, 0
        if valid:
            mfes, maes = zip(*[mfe_mae(r, rule_direction) for _, r in valid])
            mfe = np.mean(mfes)
            mae = np.mean(maes)

        results[cname] = {
            "n": n, "media": round(media, 1), "wr": round(wr, 1),
            "p": round(p_val, 4), "sharpe": round(sharpe, 3),
            "mfe": round(float(mfe), 1), "mae": round(float(mae), 1),
        }

    return results


def main():
    print("Carregando payoff table...")
    table = load_payoff_table()
    print(f"  {table['meta']['n_dias']} dias")

    print("Carregando features...")
    dat = load_features()
    print(f"  {len(dat)} dias")

    print("Carregando regras...")
    rules_data = load_rules()
    all_rules = []
    for tema in rules_data["temas"]:
        for cls in tema["classes"]:
            n = int(cls["n_teste"])
            media = cls["media_ret_teste"]
            p = cls["p_valor"]
            if n >= 30 and p < 0.05 and abs(media) > 30:
                all_rules.append(cls)

    # Filtra por IDs se passados
    targets = [a for a in sys.argv[1:] if a.startswith("H1")]
    if targets:
        # Mapeia: pega as regras do batch screening ranking
        ranking = pd.read_csv("state/batch_screening_ranking.csv")
        # Só pega as que estão no topo: H142, H143, H146, H147, etc
        target_regras = {}
        for t in targets:
            # Assumindo que a regra está no batch screening
            pass
        # Simplificacao: testa todas as 43
        pass

    print(f"\nTestando {len(all_rules)} regras com payoff table...\n")

    print(f"{'#':>3} {'Regra':<45} {'Dir':>5} | {'N':>4} | {'time 9:02':>22} | {'SL345 TP245':>22} | {'SL275 TP180':>22} | {'MFE':>7} {'MAE':>7}")
    print(f"{'':>3} {'':<45} {'':>5} | {'':>4} | {'media':>7} {'WR':>5} {'p':>6} | {'media':>7} {'WR':>5} {'p':>6} | {'media':>7} {'WR':>5} {'p':>6} | {'':>7} {'':>7}")
    print("-" * 150)

    results_all = []
    for i, r in enumerate(all_rules, 1):
        direcao = "VENDA" if r["media_ret_teste"] < 0 else "COMPRA"
        res = test_rule_with_table(r, dat, table, direcao)
        if res is None:
            continue
        r_short = r["regra"][:42]
        tc = res.get("time_9:02", {})
        s345 = res.get("SL345_TP245", {})
        s275 = res.get("SL275_TP180", {})

        # Score composto
        score = s345.get("media", 0) * s345.get("n", 1)**0.5 * (1 - s345.get("p", 1))
        results_all.append((score, r, res, direcao, r_short))

    results_all.sort(key=lambda x: x[0], reverse=True)

    for rank, (score, r, res, direcao, r_short) in enumerate(results_all[:20], 1):
        tc = res.get("time_9:02", {})
        s345 = res.get("SL345_TP245", {})
        s275 = res.get("SL275_TP180", {})
        mfe = res.get("SL345_TP245", {}).get("mfe", 0)
        mae = res.get("SL345_TP245", {}).get("mae", 0)
        n = s345.get("n", 0)
        print(f"{rank:>3} {r_short:<45} {direcao:>5} | {n:>4} | "
              f"{tc.get('media',0):>+6.0f} {tc.get('wr',0):>4.0f}% {tc.get('p',0):>5.3f} | "
              f"{s345.get('media',0):>+6.0f} {s345.get('wr',0):>4.0f}% {s345.get('p',0):>5.3f} | "
              f"{s275.get('media',0):>+6.0f} {s275.get('wr',0):>4.0f}% {s275.get('p',0):>5.3f} | "
              f"{mfe:>+6.0f} {mae:>+6.0f}")

    # Salvando
    out = []
    for score, r, res, direcao, _ in results_all:
        row = {"regra": r["regra"][:80], "direcao": direcao}
        for cname, cdata in res.items():
            for k, v in cdata.items():
                row[f"{cname}_{k}"] = v
        out.append(row)

    out_path = "state/containers_payoff_ranking.csv"
    pd.DataFrame(out).to_csv(out_path, index=False)
    print(f"\nSalvo: {out_path}")


if __name__ == "__main__":
    main()
