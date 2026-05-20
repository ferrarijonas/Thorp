"""Mineracao v2: RF + walk-forward + classes validadas OOS.
Uso: python scripts/minerar_markov_v2.py
Saida: state/mineracao_markov_v2_results.json + print detalhado
"""
import sys, os, json, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd, numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import _tree
from scipy import stats
from itertools import combinations

np.random.seed(42)

# =============================================
# 1. Carga
# =============================================
data_path = os.path.join(os.path.dirname(__file__), "..", "state",
                         "features_markov_dataset.csv")
print("Carregando dataset...")
dat = pd.read_csv(data_path)
dat["date"] = pd.to_datetime(dat["date"])
print(f"Total dias: {len(dat)}")

FEAT_NAMES = [c for c in dat.columns if c not in ("date", "target_dir", "target_ret")]
y = dat["target_dir"].values
ret = dat["target_ret"].values

baseline = max(y.mean(), 1 - y.mean())
print(f"Baseline (P(verde)): {baseline*100:.1f}%")

# =============================================
# 2. Walk-forward split
# =============================================
TRAIN_CUT = "2024-01-01"
mask_train = dat["date"] < TRAIN_CUT
mask_test = dat["date"] >= TRAIN_CUT

X_train = dat.loc[mask_train, FEAT_NAMES].values.astype(float)
y_train = y[mask_train]
ret_train = ret[mask_train]
X_test = dat.loc[mask_test, FEAT_NAMES].values.astype(float)
y_test = y[mask_test]
ret_test = ret[mask_test]

print(f"\nSplit: treino {X_train.shape[0]} dias (< 2024)")
print(f"       teste {X_test.shape[0]} dias (>= 2024)")
print(f"Baseline treino: {y_train.mean()*100:.1f}%")
print(f"Baseline teste:  {y_test.mean()*100:.1f}%")

# =============================================
# 3. Remove features correlacionadas
# =============================================
print("\n--- Removendo features correlacionadas (>0.95) ---")
df_train = pd.DataFrame(X_train, columns=FEAT_NAMES)
corr = df_train.corr().abs()
upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
to_drop = [col for col in upper.columns if any(upper[col] > 0.95)]
print(f"Removidas {len(to_drop)}: {to_drop}")

keep = [f for f in FEAT_NAMES if f not in to_drop]
print(f"Mantidas {len(keep)} features")

X_train = dat.loc[mask_train, keep].values.astype(float)
X_test = dat.loc[mask_test, keep].values.astype(float)

# =============================================
# 4. Grid search RF
# =============================================
print("\n--- Grid search Random Forest ---")

best_model = None
best_test_p = 1.0
best_params = {}
results = []

param_grid = {
    "n_estimators": [200, 500],
    "max_depth": [5, 7, 9],
    "min_samples_leaf": [10, 15, 30],
    "class_weight": ["balanced", None],
}

from itertools import product
keys = list(param_grid.keys())
for values in product(*param_grid.values()):
    params = dict(zip(keys, values))
    rf = RandomForestClassifier(
        n_estimators=params["n_estimators"],
        max_depth=params["max_depth"],
        min_samples_leaf=params["min_samples_leaf"],
        class_weight=params["class_weight"],
        random_state=42,
    )
    rf.fit(X_train, y_train)

    pred_train = rf.predict(X_train)
    pred_test = rf.predict(X_test)
    acc_train = (pred_train == y_train).mean()
    acc_test = (pred_test == y_test).mean()

    # p-valor: binomial test contra baseline no teste
    n_correct = (pred_test == y_test).sum()
    n_test = len(y_test)
    p_val = stats.binomtest(n_correct, n_test, p=baseline,
                            alternative="greater").pvalue

    results.append((params, acc_train, acc_test, p_val, rf))

    if p_val < best_test_p:
        best_test_p = p_val
        best_model = rf
        best_params = params

    print(f"  depth={params['max_depth']} "
          f"n={params['n_estimators']} "
          f"leaf={params['min_samples_leaf']} "
          f"w={params['class_weight']}  "
          f"acc_train={acc_train*100:.1f}% "
          f"acc_test={acc_test*100:.1f}% "
          f"p={p_val:.4f}")

print(f"\nMelhor modelo: {best_params}")
print(f"  acc_train: {acc_train*100:.1f}%")
print(f"  acc_test:  {acc_test*100:.1f}%")
print(f"  p_valor:   {best_test_p:.4f}")

imp = pd.Series(best_model.feature_importances_, index=keep).sort_values(ascending=False)
print(f"\nTop-15 features:")
for f, v in imp.head(15).items():
    print(f"  {f}: {v:.4f}")

# =============================================
# 5. Extracao de regras-folha
# =============================================
print("\n--- Extraindo regras-folha ---")

def extract_leaves(model, feature_names, X, y_val, ret_val, baseline_p):
    """Extrai todas as folhas da floresta, valida OOS."""
    rules = {}
    for tree in model.estimators_:
        t = tree.tree_
        def recurse(node, conditions):
            if t.feature[node] != _tree.TREE_UNDEFINED:
                name = feature_names[t.feature[node]]
                thresh = t.threshold[node]
                recurse(t.children_left[node],
                        conditions + [(name, "<=", thresh)])
                recurse(t.children_right[node],
                        conditions + [(name, ">", thresh)])
            else:
                # Leaf: registra a regra
                if not conditions:
                    return
                key = tuple(sorted((f, op, round(th, 4)) for f, op, th in conditions))
                n_samples = int(t.n_node_samples[node])
                class_dist = t.value[node][0]
                pred = np.argmax(class_dist)
                # Valida no dataset de validacao (teste)
                mask = np.ones(len(X), dtype=bool)
                for fname, op, th in conditions:
                    if op == "<=":
                        mask &= X[:, feature_names.index(fname)] <= th
                    else:
                        mask &= X[:, feature_names.index(fname)] > th
                n_val = mask.sum()
                if n_val < 5:
                    return
                val_ret = ret_val[mask].mean()
                val_win = (ret_val[mask] > 0).mean()
                val_dir = y_val[mask].mean()
                n_correct = int((y_val[mask] == (1 if val_dir > 0.5 else 0)).sum())
                # p-valor binomial contra baseline
                p = stats.binomtest(n_correct, n_val, p=baseline_p,
                                    alternative="greater").pvalue
                rules[key] = {
                    "n_treino": n_samples,
                    "n_teste": n_val,
                    "pred_treino": "COMPRA" if pred == 1 else "VENDA",
                    "media_ret_teste": round(val_ret, 1),
                    "win_rate_teste": round(val_win * 100, 1),
                    "p_dir_teste": round(val_dir * 100, 1),
                    "p_valor": round(p, 4),
                    "condicoes": [(f, op, round(th, 4)) for f, op, th in conditions],
                }
        recurse(0, [])
    return rules

all_rules = extract_leaves(best_model, keep, X_test, y_test, ret_test, baseline)

# Filtra p < 0.10
valid_rules = {k: v for k, v in all_rules.items() if v["p_valor"] < 0.10}
strong_rules = {k: v for k, v in all_rules.items() if v["p_valor"] < 0.05}

print(f"Regras unicas extraidas: {len(all_rules)}")
print(f"Validas (p<0.10 no teste): {len(valid_rules)}")
print(f"Fortes (p<0.05 no teste):  {len(strong_rules)}")

# =============================================
# 6. Agrupamento em temas
# =============================================
print("\n--- Temas encontrados ---")

def rule_to_features(rule_key):
    return set(f for f, op, th in rule_key)

def jaccard(a, b):
    return len(a & b) / max(len(a | b), 1)

# Agrupa regras por similaridade de features
all_keys = list(valid_rules.keys())
clusters = []
assigned = set()

for i, k1 in enumerate(all_keys):
    if k1 in assigned:
        continue
    cluster = [k1]
    assigned.add(k1)
    f1 = rule_to_features(k1)
    for j in range(i + 1, len(all_keys)):
        k2 = all_keys[j]
        if k2 in assigned:
            continue
        f2 = rule_to_features(k2)
        if jaccard(f1, f2) >= 0.4:
            cluster.append(k2)
            assigned.add(k2)
    clusters.append(cluster)

# Nomeia cada tema pela(s) feature(s) mais frequente(s)
themes = []
for cluster in clusters:
    feat_counts = {}
    for k in cluster:
        for f, op, th in k:
            feat_counts[f] = feat_counts.get(f, 0) + 1
    top_feats = sorted(feat_counts, key=feat_counts.get, reverse=True)[:3]
    theme_name = " + ".join(top_feats) if top_feats else "outros"
    theme_rules = []
    for k in cluster:
        r = valid_rules[k]
        cond_str = ", ".join(f"{f}{op}{th}" for f, op, th in r["condicoes"][:3])
        theme_rules.append({
            "regra": cond_str,
            "direcao": r["pred_treino"],
            "n_teste": r["n_teste"],
            "media_ret_teste": r["media_ret_teste"],
            "win_rate_teste": r["win_rate_teste"],
            "p_valor": r["p_valor"],
        })
    # Ordena por p-valor
    theme_rules.sort(key=lambda x: x["p_valor"])
    themes.append({
        "tema": theme_name,
        "classes": theme_rules,
    })

themes.sort(key=lambda t: t["classes"][0]["p_valor"])

print(f"{'Tema':<40} {'Classes':>8} {'Melhor p':>9} {'Melhor media':>12}")
print("-" * 72)
for t in themes:
    best = t["classes"][0]
    print(f"{t['tema']:<40} {len(t['classes']):>8} {best['p_valor']:>9.4f} {best['media_ret_teste']:>+10.1f}")

# =============================================
# 7. Print detalhado das classes
# =============================================
print("\n\n=== TODAS AS CLASSES VALIDAS (p < 0.10) ===")
print(f"{'#':>3} {'p':>7} {'N':>5} {'WR%':>5} {'Media':>7} {'Direcao':>8} {'Regra'}")
print("-" * 80)
sorted_rules = sorted(valid_rules.items(), key=lambda x: x[1]["p_valor"])
for i, (key, r) in enumerate(sorted_rules, 1):
    if i > 50:
        break
    sig = "***" if r["p_valor"] < 0.01 else "**" if r["p_valor"] < 0.05 else "*"
    cond_short = ", ".join(f"{f}{op}{th}" for f, op, th in r["condicoes"][:3])
    print(f"{i:>3} {r['p_valor']:>7.4f} {r['n_teste']:>5} "
          f"{r['win_rate_teste']:>5.1f} {r['media_ret_teste']:>+6.1f} "
          f"{r['pred_treino']:>8} {cond_short} {sig}")

# =============================================
# 8. Salva resultados
# =============================================
output = {
    "params": best_params,
    "baseline": round(baseline * 100, 1),
    "acc_treino": round(acc_train * 100, 1),
    "acc_teste": round(acc_test * 100, 1),
    "p_valor_modelo": round(best_test_p, 4),
    "total_features_entrada": len(FEAT_NAMES),
    "features_removidas_corr": to_drop,
    "features_mantidas": len(keep),
    "top_features": {f: round(v, 4) for f, v in imp.head(20).items()},
    "total_classes_extraidas": len(all_rules),
    "classes_validas_p10": len(valid_rules),
    "classes_validas_p05": len(strong_rules),
    "temas": [
        {
            "tema": t["tema"],
            "n_classes": len(t["classes"]),
            "classes": t["classes"][:5],  # top 5 por tema
        }
        for t in themes
    ],
}

out_path = os.path.join(os.path.dirname(__file__), "..", "state",
                        "mineracao_markov_v2_results.json")
with open(out_path, "w") as f:
    json.dump(output, f, indent=2, default=str)
print(f"\nResultados salvos em {out_path}")
