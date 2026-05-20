"""Batch screening: testa todas as 43 regras fortes contra dados historicos.
Uso: python scripts/batch_screening_markov.py
Saida: state/batch_screening_ranking.csv + print ranking
"""
import sys, os, re, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd
import numpy as np
from scipy import stats

COST_PTS = 10  # custo de entrada+saida em pts

print("Carregando dataset...")
dat = pd.read_csv("state/features_markov_dataset.csv")
dat["date"] = pd.to_datetime(dat["date"])
print(f"Dias: {len(dat)} | {dat['date'].iloc[0].date()} a {dat['date'].iloc[-1].date()}")

print("Carregando regras...")
with open("state/mineracao_markov_v2_results.json") as f:
    data = json.load(f)

def parse_rule(rule_str):
    """Converte string 'gap_rel_range<=1.5733, fractal>1.7674' em (col, op, val) list."""
    parts = [p.strip() for p in rule_str.split(",")]
    conds = []
    for p in parts:
        m = re.match(r"([\w_]+)(<=|>)(-?\d+\.?\d*)", p)
        if m:
            conds.append((m.group(1), m.group(2), float(m.group(3))))
    return conds

def apply_rule(df, conditions, direction):
    """Aplica condicoes e retorna mask dos dias onde a regra vale."""
    mask = pd.Series(True, index=df.index)
    for col, op, val in conditions:
        if col not in df.columns:
            mask = pd.Series(False, index=df.index)
            break
        if op == "<=":
            mask &= df[col] <= val
        else:
            mask &= df[col] > val
    return mask

def test_rule(df, conditions, direction, cost=COST_PTS):
    """Testa regra: retorna stats."""
    mask = apply_rule(df, conditions, direction)
    n = mask.sum()
    if n < 5:
        return None

    sub = df[mask].copy()
    if direction == "VENDA":
        sub["pnl_trade"] = -sub["target_ret"]
    else:
        sub["pnl_trade"] = sub["target_ret"]
    sub["pnl_cost"] = sub["pnl_trade"] - cost
    sub["win"] = (sub["pnl_cost"] > 0).astype(int)

    n = len(sub)
    media = sub["pnl_trade"].mean()
    media_cost = sub["pnl_cost"].mean()
    wr = sub["win"].mean() * 100
    total_pnl = sub["pnl_trade"].sum()
    total_cost = sub["pnl_cost"].sum()

    # Sharpe (assumindo rf=0)
    std = sub["pnl_trade"].std()
    sharpe = media / std if std > 0 else 0

    # Profit factor
    gross_profit = sub.loc[sub["pnl_cost"] > 0, "pnl_cost"].sum()
    gross_loss = abs(sub.loc[sub["pnl_cost"] < 0, "pnl_cost"].sum())
    pf = gross_profit / gross_loss if gross_loss > 0 else 999

    # P-valor: binomial test WR vs 50%
    wins = sub["win"].sum()
    p_val = stats.binomtest(wins, n, p=0.5, alternative="greater").pvalue

    # P-valor do retorno: t-test contra 0
    t_stat, p_ret = stats.ttest_1samp(sub["pnl_cost"], 0)
    p_ret_one = p_ret / 2 if media_cost > 0 else 1 - p_ret / 2

    return {
        "n": n,
        "media_pts": round(media, 1),
        "media_cost_pts": round(media_cost, 1),
        "wr_pct": round(wr, 1),
        "total_pnl": round(total_pnl, 0),
        "total_cost": round(total_cost, 0),
        "sharpe": round(sharpe, 3),
        "profit_factor": round(pf, 2),
        "p_valor_binomial": round(p_val, 4),
        "p_valor_ttest": round(p_ret_one, 4),
        "std_pts": round(std, 1),
    }

# Coleta as 43 regras fortes
all_rules = []
for tema in data["temas"]:
    for cls in tema["classes"]:
        n = int(cls["n_teste"])
        media = cls["media_ret_teste"]
        p = cls["p_valor"]
        if n >= 30 and p < 0.05 and abs(media) > 30:
            all_rules.append(cls)

print(f"\nTotal de regras fortes: {len(all_rules)}")
print("Testando cada uma...")

results = []
done = 0
for r in all_rules:
    conds = parse_rule(r["regra"])
    # Direcao: usa o sinal do teste (media_ret_teste)
    direcao = "VENDA" if r["media_ret_teste"] < 0 else "COMPRA"
    stats_r = test_rule(dat, conds, direcao)
    if stats_r is None:
        continue
    stats_r["regra"] = r["regra"][:80]
    stats_r["direcao"] = direcao
    stats_r["p_original"] = r["p_valor"]
    stats_r["media_original"] = r["media_ret_teste"]
    stats_r["n_original"] = r["n_teste"]
    results.append(stats_r)
    done += 1
    if done % 10 == 0:
        print(f"  {done}/{len(all_rules)}")

# Ordena por score composto: media_cost * sqrt(n) * (1 - p_valor_ttest)
for r in results:
    r["score"] = round(r["media_cost_pts"] * (r["n"] ** 0.5) * (1 - r["p_valor_ttest"]), 1)

results.sort(key=lambda x: x["score"], reverse=True)

# Print ranking
print(f"\n{'='*110}")
print(f"{'RANKING BATCH SCREENING — 43 REGRAS (ordenado por score)':^110}")
print(f"{'Custo por trade: ' + str(COST_PTS) + 'pts':^110}")
print(f"{'='*110}")
print(f"{'#':>3} {'Regra':<55} {'Dir':>5} {'N':>4} {'Media':>7} {'Med_cst':>7} {'WR%':>5} {'Sharpe':>7} {'PF':>5} {'p_val':>6} {'Score':>7}")
print(f"{'-'*110}")

for i, r in enumerate(results[:43], 1):
    sig = "***" if r["p_valor_ttest"] < 0.01 else "**" if r["p_valor_ttest"] < 0.05 else "*"
    print(f"{i:>3} {r['regra']:<55} {r['direcao']:>5} {r['n']:>4} "
          f"{r['media_pts']:>+6.0f} {r['media_cost_pts']:>+6.0f} "
          f"{r['wr_pct']:>4.1f}% {r['sharpe']:>6.3f} {r['profit_factor']:>5.2f} "
          f"{r['p_valor_ttest']:>6.4f} {r['score']:>7.0f} {sig}")

# Salva CSV
out_cols = ["regra", "direcao", "n", "n_original", "media_pts", "media_cost_pts",
            "wr_pct", "sharpe", "profit_factor", "p_valor_binomial", "p_valor_ttest",
            "p_original", "media_original", "total_pnl", "std_pts", "score"]
out = pd.DataFrame(results)[out_cols]
out = out.sort_values("score", ascending=False)
out_path = "state/batch_screening_ranking.csv"
out.to_csv(out_path, index=False)
print(f"\nSalvo: {out_path}")

# Top-10 resumo
print(f"\n{'='*60}")
print(f"{'TOP-10':^60}")
print(f"{'='*60}")
for i, r in enumerate(results[:10], 1):
    print(f"{i:>2}. {r['regra'][:50]:<50} {r['direcao']:>5} "
          f"N={r['n']:>3} media={r['media_cost_pts']:>+5.0f}pts "
          f"WR={r['wr_pct']:>4.1f}% S={r['sharpe']:.2f} score={r['score']:.0f}")
