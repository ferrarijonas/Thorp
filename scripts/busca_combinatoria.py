"""Busca exaustiva por combinacoes simples que preveem 9:01."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd, numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import cross_val_score
from scipy import stats
from core.data import load_csv

df = load_csv()
dfD = df.between_time("09:00", "17:00")

dias = sorted(set(dfD.index.date))
rows = []
for dia in dias:
    d9 = dfD.loc[str(dia)]
    if len(d9) < 2: continue
    r9 = d9[(d9.index.hour == 9) & (d9.index.minute == 0)]
    r01 = d9[(d9.index.hour == 9) & (d9.index.minute == 1)]
    if len(r9) == 0 or len(r01) == 0: continue
    o9, h9, l9, c9, v9 = r9.iloc[0][["open", "high", "low", "close", "volume"]]
    o01, c01 = r01.iloc[0][["open", "close"]]
    rows.append({
        "date": dia,
        "green_9": c9 > o9,
        "body_9": c9 - o9,
        "body_ratio": abs(c9 - o9) / (h9 - l9 + 0.001),
        "range_9": h9 - l9,
        "pos_close": (c9 - l9) / (h9 - l9 + 0.001),
        "shadow_up": (h9 - max(o9, c9)) / (h9 - l9 + 0.001),
        "shadow_dn": (min(o9, c9) - l9) / (h9 - l9 + 0.001),
        "vol_9": v9,
        "o9": o9, "h9": h9, "l9": l9, "c9": c9,
        "ret_01": c01 - o01,
        "green_01": int(c01 > o01),
    })

dat = pd.DataFrame(rows)
dat["green_9_d1"] = dat["green_9"].shift(1)
dat["range_9_d1"] = dat["range_9"].shift(1)
dat["ret_01_d1"] = dat["ret_01"].shift(1)
dat["green_01_d1"] = dat["green_01"].shift(1)
dat["acertou_ontem"] = (dat["green_9_d1"] == dat["green_01_d1"]).astype(int)

dat["gap"] = dat["o9"] - dat["c9"].shift(1)
dat = dat.dropna()

n = len(dat)
print(f"Dias: {n}")
print(f"Baseline (melhor entre sempre 0 ou sempre 1): {max((dat.green_01 == 0).sum(), (dat.green_01 == 1).sum()) / n * 100:.1f}%")

# Decision tree
feats = ["green_9", "body_ratio", "range_9", "pos_close", "shadow_up", "shadow_dn",
         "vol_9", "gap", "green_9_d1", "range_9_d1", "acertou_ontem"]
X = dat[feats].values.astype(float)
y = dat["green_01"].values

print(f"\n--- Decision Tree (max_depth=3) ---")
tree = DecisionTreeClassifier(max_depth=3, min_samples_leaf=20, random_state=42)
tree.fit(X, y)
cv = cross_val_score(tree, X, y, cv=5)
print(f"Cross-val accuracy: {cv.mean() * 100:.1f}% +- {cv.std() * 100:.1f}%")

imp = pd.Series(tree.feature_importances_, index=feats).sort_values(ascending=False)
print(f"\nFeature importance:")
for f, v in imp.items():
    if v > 0:
        print(f"  {f}: {v:.4f}")

# Regras da arvore
from sklearn.tree import _tree
def get_rules(tree, feature_names):
    t = tree.tree_
    rules = []
    def recurse(node, depth, conditions):
        if t.feature[node] != _tree.TREE_UNDEFINED:
            name = feature_names[t.feature[node]]
            threshold = t.threshold[node]
            recurse(t.children_left[node], depth + 1,
                    conditions + [f"{name} <= {threshold:.3f}"])
            recurse(t.children_right[node], depth + 1,
                    conditions + [f"{name} > {threshold:.3f}"])
        else:
            class_dist = t.value[node][0]
            pred = np.argmax(class_dist)
            n_samples = int(t.n_node_samples[node])
            rules.append((n_samples, pred, class_dist, conditions))
    recurse(0, 1, [])
    return rules

rules = get_rules(tree, feats)
rules.sort(key=lambda x: x[0], reverse=True)

print(f"\nRegras da arvore:")
for n_samples, pred, dist, conditions in rules:
    pct = n_samples / n * 100
    acc = max(dist) / sum(dist) * 100 if sum(dist) > 0 else 0
    rule_str = " AND ".join(conditions) if conditions else "ALWAYS"
    pred_str = "COMPRA" if pred == 1 else "VENDA"
    print(f"  IF {rule_str:>60} => {pred_str} (N={n_samples}, acc={acc:.0f}%)")

# Busca exaustiva de combinacoes simples
print(f"\n\n--- Teste de combinacoes binarias (top-20 por p-valor) ---")
print(f"{'Combinacao':<50} {'N0':>5} {'N1':>5} {'Ret0':>7} {'Ret1':>7} {'p':>7}")

combos = {
    "gap_up + green_9": (dat["gap"] > 0) & (dat["green_9"]),
    "gap_up + red_9": (dat["gap"] > 0) & (~dat["green_9"]),
    "gap_dn + green_9": (dat["gap"] < 0) & (dat["green_9"]),
    "gap_dn + red_9": (dat["gap"] < 0) & (~dat["green_9"]),
    "acertou_ontem + green_9": (dat["acertou_ontem"] == 1) & (dat["green_9"]),
    "acertou_ontem + red_9": (dat["acertou_ontem"] == 1) & (~dat["green_9"]),
    "errou_ontem + green_9": (dat["acertou_ontem"] == 0) & (dat["green_9"]),
    "errou_ontem + red_9": (dat["acertou_ontem"] == 0) & (~dat["green_9"]),
    "range > P75": dat["range_9"] > dat["range_9"].quantile(0.75),
    "range > P75 + gap_up": (dat["range_9"] > dat["range_9"].quantile(0.75)) & (dat["gap"] > 0),
    "range > P75 + gap_dn": (dat["range_9"] > dat["range_9"].quantile(0.75)) & (dat["gap"] < 0),
    "body > P75 + green_9": (dat["body_ratio"] > dat["body_ratio"].quantile(0.75)) & (dat["green_9"]),
    "body > P75 + red_9": (dat["body_ratio"] > dat["body_ratio"].quantile(0.75)) & (~dat["green_9"]),
    "pos>0.66 (terco sup)": dat["pos_close"] > 0.66,
    "pos<0.33 (terco inf)": dat["pos_close"] < 0.33,
    "pos>0.66 + gap_up": (dat["pos_close"] > 0.66) & (dat["gap"] > 0),
    "pos<0.33 + gap_dn": (dat["pos_close"] < 0.33) & (dat["gap"] < 0),
    "pos>0.66 + acertou": (dat["pos_close"] > 0.66) & (dat["acertou_ontem"] == 1),
    "pos<0.33 + acertou": (dat["pos_close"] < 0.33) & (dat["acertou_ontem"] == 1),
    "range_9 > P75 + green_9": (dat["range_9"] > dat["range_9"].quantile(0.75)) & (dat["green_9"]),
    "range_9 < P25 + green_9": (dat["range_9"] < dat["range_9"].quantile(0.25)) & (dat["green_9"]),
    "gap grande (>P90) + green_9": (abs(dat["gap"]) > np.percentile(abs(dat["gap"]), 90)) & (dat["green_9"]),
    "gap grande (>P90) + red_9": (abs(dat["gap"]) > np.percentile(abs(dat["gap"]), 90)) & (~dat["green_9"]),
    "vol > P75 + green_9": (dat["vol_9"] > dat["vol_9"].quantile(0.75)) & (dat["green_9"]),
    "vol > P75 + red_9": (dat["vol_9"] > dat["vol_9"].quantile(0.75)) & (~dat["green_9"]),
    "green_9_d1 + green_9": (dat["green_9_d1"]) & (dat["green_9"]),
    "red_9_d1 + red_9": (~dat["green_9_d1"]) & (~dat["green_9"]),
    "acertou + range_9 > P75": (dat["acertou_ontem"] == 1) & (dat["range_9"] > dat["range_9"].quantile(0.75)),
    "acertou + pos>0.66": (dat["acertou_ontem"] == 1) & (dat["pos_close"] > 0.66),
    "acertou + pos<0.33": (dat["acertou_ontem"] == 1) & (dat["pos_close"] < 0.33),
}

results = []
for name, mask in combos.items():
    v0 = dat.loc[~mask, "ret_01"]
    v1 = dat.loc[mask, "ret_01"]
    n0, n1 = len(v0), len(v1)
    if n1 < 8 or n0 < 8: continue
    _, p = stats.ttest_ind(v1, v0, equal_var=False)
    results.append((name, n0, n1, v0.mean(), v1.mean(), p))

results.sort(key=lambda x: x[5])
for name, n0, n1, r0, r1, p in results[:20]:
    fl = " <--" if p < 0.05 else ""
    print(f"{name:<50} {n0:>5} {n1:>5} {r0:>+6.1f} {r1:>+6.1f} {p:.4f}{fl}")

# Estrategia final: repete se acertou, inverte se errou
print(f"\n\n--- ESTRATEGIA: repete se acertou ontem, inverte se errou ---")
mask_c = (dat["acertou_ontem"] == 1) & (dat["green_9"]) | (dat["acertou_ontem"] == 0) & (~dat["green_9"])
mask_v = (dat["acertou_ontem"] == 1) & (~dat["green_9"]) | (dat["acertou_ontem"] == 0) & (dat["green_9"])

pnl_c = dat.loc[mask_c, "ret_01"]
pnl_v = -dat.loc[mask_v, "ret_01"]
pnl = np.concatenate([pnl_c.values, pnl_v.values])
print(f"COMPRA: N={len(pnl_c)} ret={pnl_c.mean():+.1f} pts")
print(f"VENDA:  N={len(pnl_v)} ret={pnl_v.mean():+.1f} pts")
print(f"TOTAL:  N={len(pnl)} ret={pnl.mean():+.1f} pts (sem custo)")
_, p = stats.ttest_1samp(pnl, 0)
d = np.mean(pnl > 0) * 100
print(f"Win rate: {d:.1f}% p-valor: {p:.4f}")

# Versao com filtro adicional (range_9 + body)
print(f"\n\n--- COM FILTRO: acertou ontem + range_9 > P75 + green_9 ---")
mask_c2 = mask_c & (dat["range_9"] > dat["range_9"].quantile(0.75))
mask_v2 = mask_v & (dat["range_9"] > dat["range_9"].quantile(0.75))
pnl2 = np.concatenate([dat.loc[mask_c2, "ret_01"].values, -dat.loc[mask_v2, "ret_01"].values])
if len(pnl2) > 10:
    print(f"Filtro range>P75: N={len(pnl2)} ret={pnl2.mean():+.1f} pts")
    _, p2 = stats.ttest_1samp(pnl2, 0)
    print(f"p-valor: {p2:.4f}")

# Com filtro de body ratio
mask_c3 = mask_c & (dat["body_ratio"] > dat["body_ratio"].quantile(0.75))
mask_v3 = mask_v & (dat["body_ratio"] > dat["body_ratio"].quantile(0.75))
pnl3 = np.concatenate([dat.loc[mask_c3, "ret_01"].values, -dat.loc[mask_v3, "ret_01"].values])
if len(pnl3) > 10:
    print(f"Filtro body>P75: N={len(pnl3)} ret={pnl3.mean():+.1f} pts")
    _, p3 = stats.ttest_1samp(pnl3, 0)
    print(f"p-valor: {p3:.4f}")
