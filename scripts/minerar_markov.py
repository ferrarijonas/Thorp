"""Mineracao completa de classes Markovianas: 9:00 -> 9:01.
Random Forest + varredura exaustiva de pares + todas as regras."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd, numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import _tree
from sklearn.model_selection import cross_val_score
from scipy import stats
from core.data import load_csv

np.random.seed(42)

# =============================================
# 1. Monta dataset rico de features
# =============================================
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
        "date": dia, "o9": o9, "h9": h9, "l9": l9, "c9": c9, "v9": v9,
        "o01": o01, "c01": c01,
        "dow": d9.index[0].dayofweek,
        "day": d9.index[0].day,
        "month": d9.index[0].month,
    })

dat = pd.DataFrame(rows)

# Features basicas de 9:00
dat["green_9"] = (dat["c9"] > dat["o9"]).astype(int)
dat["body_9"] = dat["c9"] - dat["o9"]
dat["range_9"] = dat["h9"] - dat["l9"]
dat["body_ratio"] = abs(dat["c9"] - dat["o9"]) / (dat["range_9"] + 0.001)
dat["pos_close"] = (dat["c9"] - dat["l9"]) / (dat["range_9"] + 0.001)
dat["shadow_up"] = (dat["h9"] - np.maximum(dat["o9"], dat["c9"])) / (dat["range_9"] + 0.001)
dat["shadow_dn"] = (np.minimum(dat["o9"], dat["c9"]) - dat["l9"]) / (dat["range_9"] + 0.001)
dat["mid"] = (dat["h9"] + dat["l9"]) / 2
dat["vol_9"] = dat["v9"]
dat["fractal"] = dat["range_9"] / (abs(dat["body_9"]) + 1)
dat["wick_asym"] = dat["shadow_up"] / (dat["shadow_dn"] + 0.001)
dat["o_is_h"] = (dat["o9"] == dat["h9"]).astype(int)
dat["o_is_l"] = (dat["o9"] == dat["l9"]).astype(int)
dat["c_is_h"] = (dat["c9"] == dat["h9"]).astype(int)
dat["c_is_l"] = (dat["c9"] == dat["l9"]).astype(int)

# Gap overnight
dat["gap"] = dat["o9"] - dat["c9"].shift(1)

# D-1 features
dat["green_9_d1"] = dat["green_9"].shift(1)
dat["range_9_d1"] = dat["range_9"].shift(1)
dat["body_ratio_d1"] = dat["body_ratio"].shift(1)
dat["pos_close_d1"] = dat["pos_close"].shift(1)
dat["green_01_d1"] = ((dat["c01"] > dat["o01"]).astype(int)).shift(1)
dat["ret_01_d1"] = (dat["c01"] - dat["o01"]).shift(1)
dat["acertou_ontem"] = (dat["green_9_d1"] == dat["green_01_d1"]).astype(int)
dat["range_d1_total"] = (dat["h9"].shift(1) - dat["l9"].shift(1)).where(
    (dat["o9"].shift(1) - dat["o9"].shift(1) == 0), 150)  # fallback

# Drop NaNs
dat = dat.dropna()
n = len(dat)
print(f"Dias validos: {n}")

# Target
dat["green_01"] = (dat["c01"] > dat["o01"]).astype(int)
dat["ret_01"] = dat["c01"] - dat["o01"]

# Rolling stats para features normalizadas
for col in ["range_9", "body_ratio", "vol_9", "gap"]:
    dat[f"{col}_p50"] = dat[col].rolling(21, min_periods=10).median()
    dat[f"{col}_rank"] = dat[col].rolling(21, min_periods=10).apply(
        lambda x: (x.iloc[-1] > x[:-1]).sum() / len(x[:-1]) if len(x) > 1 else 0.5)
dat = dat.dropna()
print(f"Dias com rolling stats: {len(dat)}")
n = len(dat)

baseline = max(dat["green_01"].mean(), 1 - dat["green_01"].mean())
print(f"Baseline (melhor classe): {baseline*100:.1f}%")

# =============================================
# 2. Features para o modelo (continuas + binarias)
# =============================================
feats_cont = [
    "range_9", "body_ratio", "pos_close", "shadow_up", "shadow_dn",
    "vol_9", "gap", "fractal", "wick_asym",
    "range_9_rank", "body_ratio_rank", "vol_9_rank", "gap_rank",
]
feats_bin = [
    "green_9", "o_is_h", "o_is_l", "c_is_h", "c_is_l",
    "green_9_d1", "acertou_ontem", "green_01_d1",
]

# Versoes binarias por threshold
for col in ["range_9", "body_ratio", "pos_close", "shadow_up", "shadow_dn", "vol_9", "gap", "fractal"]:
    q25 = dat[col].quantile(0.25)
    q50 = dat[col].quantile(0.50)
    q75 = dat[col].quantile(0.75)
    dat[f"{col}_gt_q25"] = (dat[col] > q25).astype(int)
    dat[f"{col}_gt_q50"] = (dat[col] > q50).astype(int)
    dat[f"{col}_gt_q75"] = (dat[col] > q75).astype(int)
    feats_bin.extend([f"{col}_gt_q25", f"{col}_gt_q50", f"{col}_gt_q75"])

# Gap binario
dat["gap_up"] = (dat["gap"] > 0).astype(int)
dat["gap_big"] = (abs(dat["gap"]) > np.percentile(abs(dat["gap"]), 90)).astype(int)
feats_bin.extend(["gap_up", "gap_big"])

# Features continuas
X_cont = dat[feats_cont].fillna(0).values.astype(float)

# Features binarias
X_bin = dat[feats_bin].fillna(0).values.astype(float)

# Full feature set
X_all = np.column_stack([X_cont, X_bin])
feat_names = feats_cont + feats_bin
y = dat["green_01"].values

print(f"Features: {len(feat_names)} ({len(feats_cont)} continuas + {len(feats_bin)} binarias)")

# =============================================
# 3. Random Forest
# =============================================
print(f"\n{'='*70}")
print("RANDOM FOREST (100 arvores, max_depth=5)")
print("="*70)

rf = RandomForestClassifier(n_estimators=100, max_depth=5, min_samples_leaf=15, 
                             random_state=42, class_weight="balanced")
rf.fit(X_all, y)
cv = cross_val_score(rf, X_all, y, cv=5)
print(f"Cross-val accuracy: {cv.mean()*100:.1f}% +- {cv.std()*100:.1f}%")

# Feature importance
imp = pd.Series(rf.feature_importances_, index=feat_names).sort_values(ascending=False)
print(f"\nTop-20 features:")
for f, v in imp.head(20).items():
    if v > 0.01:
        print(f"  {f}: {v:.4f}")

# =============================================
# 4. Extrai TODAS as regras-folha de todas as arvores
# =============================================
print(f"\n{'='*70}")
print("REGRAS-FOLHA (todas as 100 arvores, folhas com acc > baseline)")
print("="*70)

all_rules = []

def extract_leaves(tree, feature_names, X, y):
    t = tree.tree_
    def recurse(node, depth, conditions):
        if t.feature[node] != _tree.TREE_UNDEFINED:
            name = feature_names[t.feature[node]]
            thresh = t.threshold[node]
            recurse(t.children_left[node], depth + 1,
                    conditions + [(name, "<=", thresh)])
            recurse(t.children_right[node], depth + 1,
                    conditions + [(name, ">", thresh)])
        else:
            # Leaf: calcula acuracia
            n_leaves_global = t.value[node][0]
            # Estima N real: usa a proporção do nó na árvore
            n_samples = int(t.n_node_samples[node])
            class_dist = t.value[node][0]
            total = sum(class_dist)
            if total == 0: return
            pred = np.argmax(class_dist)
            acc = max(class_dist) / total
            all_rules.append((n_samples, pred, acc, conditions))

    recurse(0, 1, [])

for tree in rf.estimators_:
    extract_leaves(tree, feat_names, X_all, y)

# Remove duplicatas (mesmas condicoes)
unique_rules = {}
for n_samples, pred, acc, conditions in all_rules:
    key = tuple(sorted(conditions))
    if key not in unique_rules or unique_rules[key][2] < acc:
        unique_rules[key] = (n_samples, pred, acc, conditions)

# Ordena por acuracia
sorted_rules = sorted(unique_rules.values(), key=lambda x: x[2], reverse=True)

print(f"\nTotal de regras unicas: {len(sorted_rules)}")
print(f"\nTop-30 regras por acuracia (p < 0.10):")
print(f"{'#':>3} {'Acur':>6} {'N':>5} {'Sinal':>7} {'Condicoes'}")
print("-"*80)

count = 0
for ns, pred, acc, conds in sorted_rules:
    if count >= 30: break
    n_eff = min(ns, n)
    # Teste binomial aproximado
    n_correct = int(acc * ns)
    if n_correct > ns: n_correct = ns
    # p-valor binomial contra baseline
    p = stats.binomtest(n_correct, ns, p=max(0.5, 1 - baseline),
                       alternative='greater').pvalue if ns > 0 else 1
    if p < 0.10:
        count += 1
        pred_str = "COMPRA" if pred == 1 else "VENDA"
        rule_str = " E ".join(f"{f}{op}{th:.0f}" if th > 100 else f"{f}{op}{th:.3f}"
                              for f, op, th in conds[:5])
        sig = " ***" if p < 0.05 else " *" if p < 0.10 else ""
        print(f"{count:>3} {acc*100:>5.1f}% {ns:>5} {pred_str:>7}  {rule_str}{sig}")

# =============================================
# 5. Varredura exaustiva de pares binarios
# =============================================
print(f"\n{'='*70}")
print("VARREDURA EXAUSTIVA DE PARES")
print("="*70)

# Top binary features from importance
top_bin = [f for f in imp.head(30).index if f in feats_bin]
if len(top_bin) > 20: top_bin = top_bin[:20]

pair_results = []
for i in range(len(top_bin)):
    for j in range(i + 1, len(top_bin)):
        f1, f2 = top_bin[i], top_bin[j]
        # 4 combinacoes: 00, 01, 10, 11
        mask_00 = (dat[f1] == 0) & (dat[f2] == 0)
        mask_01 = (dat[f1] == 0) & (dat[f2] == 1)
        mask_10 = (dat[f1] == 1) & (dat[f2] == 1)
        mask_11 = (dat[f1] == 1) & (dat[f2] == 1)
        
        # Testa cada par contra o complemento
        for label, mask in [("00", mask_00), ("11", mask_11)]:
            n_cond = mask.sum()
            if n_cond < 20 or n_cond > n - 20: continue
            v_cond = dat.loc[mask, "ret_01"]
            v_rest = dat.loc[~mask, "ret_01"]
            _, p = stats.ttest_ind(v_cond, v_rest, equal_var=False)
            if p < 0.10:
                pair_results.append((f1, f2, label, n_cond, v_cond.mean(), p))

pair_results.sort(key=lambda x: x[5])

print(f"\nTop pares (p < 0.10): {len(pair_results)} encontrados")
print(f"{'F1':<22} {'F2':<22} {'Clas':>4} {'N':>5} {'Ret':>7} {'p':>7}")
for f1, f2, label, n_cond, ret, p in pair_results[:30]:
    sig = " ***" if p < 0.05 else " *"
    print(f"{f1:<22} {f2:<22} {label:>4} {n_cond:>5} {ret:>+6.1f} {p:.4f}{sig}")

# =============================================
# 6. Consolidado: melhores classes para H140
# =============================================
print(f"\n\n{'='*70}")
print("CLASSES MARKOVIANAS CANDIDATAS PARA H140")
print("="*70)
print(f"Baseline: {baseline*100:.0f}% | Dias: {n}")
print()

all_candidates = []

# Rules from RF
for ns, pred, acc, conds in sorted_rules:
    n_correct = int(acc * ns)
    p = stats.binomtest(n_correct, ns, p=baseline, 
                       alternative='greater').pvalue if ns >= 20 else 1
    if p < 0.10:
        pred_str = "COMPRA" if pred == 1 else "VENDA"
        rule_str = " E ".join(f"{f}{op}{th:.0f}" if th > 100 else f"{f}{op}{th:.3f}"
                              for f, op, th in conds[:4])
        all_candidates.append((p, acc*100, ns, pred_str, f"[RF] {rule_str}"))

# Pairs from exhaustive search
for f1, f2, label, n_cond, ret, p in pair_results:
    if p < 0.05:
        pred_str = "COMPRA" if ret > 0 else "VENDA"
        all_candidates.append((p, 0, n_cond, pred_str, 
            f"[Par] {f1}={label[0]},{f2}={label[1]} ret={ret:+.1f}"))

all_candidates.sort(key=lambda x: x[0])

print(f"{'#':>3} {'p-valor':>8} {'Acc':>6} {'N':>5} {'Sinal':>7} {'Regra'}")
for i, (p, acc, ns, sinal, rule) in enumerate(all_candidates[:30], 1):
    sig = "***" if p < 0.01 else "**" if p < 0.05 else "*"
    print(f"{i:>3} {p:>8.4f} {acc:>5.1f}% {ns:>5} {sinal:>7} {rule} {sig}")

print(f"\nTotal de candidatos: {len(all_candidates)}")
