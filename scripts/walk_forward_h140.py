"""Walk-forward mining: treino (ate 2025-06-30) -> teste (2025-07-01+).
Extrai regras Markovianas no treino, valida no teste futuro.
So sobrevivem regras significativas em AMBOS."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd, numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import _tree
from scipy import stats
from core.data import load_csv

np.random.seed(42)

SPLIT_DATE = pd.Timestamp("2025-07-01")
MIN_SAMPLES = 20

print(f"Split temporal: treino < {SPLIT_DATE.date()}, teste >= {SPLIT_DATE.date()}")

# =============================================
# 1. Monta dataset
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
    })

dat = pd.DataFrame(rows)
dat["date"] = pd.to_datetime(dat["date"])

# Features
dat["green_9"] = (dat["c9"] > dat["o9"]).astype(int)
dat["body_9"] = dat["c9"] - dat["o9"]
dat["range_9"] = dat["h9"] - dat["l9"]
dat["body_ratio"] = abs(dat["c9"] - dat["o9"]) / (dat["range_9"] + 0.001)
dat["pos_close"] = (dat["c9"] - dat["l9"]) / (dat["range_9"] + 0.001)
dat["shadow_up"] = (dat["h9"] - np.maximum(dat["o9"], dat["c9"])) / (dat["range_9"] + 0.001)
dat["shadow_dn"] = (np.minimum(dat["o9"], dat["c9"]) - dat["l9"]) / (dat["range_9"] + 0.001)
dat["fractal"] = dat["range_9"] / (abs(dat["body_9"]) + 1)
dat["wick_asym"] = dat["shadow_up"] / (dat["shadow_dn"] + 0.001)
dat["o_is_h"] = (dat["o9"] == dat["h9"]).astype(int)
dat["o_is_l"] = (dat["o9"] == dat["l9"]).astype(int)
dat["c_is_h"] = (dat["c9"] == dat["h9"]).astype(int)
dat["c_is_l"] = (dat["c9"] == dat["l9"]).astype(int)

dat["gap"] = dat["o9"] - dat["c9"].shift(1)
dat["green_9_d1"] = dat["green_9"].shift(1)
dat["range_9_d1"] = dat["range_9"].shift(1)
dat["green_01_d1"] = ((dat["c01"] > dat["o01"]).astype(int)).shift(1)
dat["ret_01_d1"] = (dat["c01"] - dat["o01"]).shift(1)
dat["acertou_ontem"] = (dat["green_9_d1"] == dat["green_01_d1"]).astype(int)
dat = dat.dropna()

# Target
dat["green_01"] = (dat["c01"] > dat["o01"]).astype(int)
dat["ret_01"] = dat["c01"] - dat["o01"]

# Variaveis binarias por quantil
feats_cont_list = ["range_9", "body_ratio", "pos_close", "shadow_up", "shadow_dn",
                   "fractal", "wick_asym", "gap", "v9"]

for col in feats_cont_list:
    q50 = dat[col].quantile(0.50)
    q75 = dat[col].quantile(0.75)
    dat[f"{col}_gt_q50"] = (dat[col] > q50).astype(int)
    dat[f"{col}_gt_q75"] = (dat[col] > q75).astype(int)

base_bin = ["green_9", "o_is_h", "o_is_l", "c_is_h", "c_is_l",
            "green_9_d1", "acertou_ontem", "green_01_d1",
            "gap_up" if "gap_up" in dat.columns else "green_9"]

dat["gap_up"] = (dat["gap"] > 0).astype(int)
base_bin.append("gap_up")

all_bin = base_bin + [f"{c}_gt_q50" for c in feats_cont_list] + [f"{c}_gt_q75" for c in feats_cont_list]
all_bin = [c for c in all_bin if c in dat.columns]

feat_names_cont = feats_cont_list
feat_names_bin = all_bin
feat_names = feat_names_cont + feat_names_bin

# =============================================
# 2. Split
# =============================================
train = dat[dat["date"] < SPLIT_DATE].copy()
test = dat[dat["date"] >= SPLIT_DATE].copy()
print(f"Treino: {len(train)} dias | Teste: {len(test)} dias")

def prepare(data):
    Xc = data[feat_names_cont].fillna(0).values.astype(float)
    Xb = data[feat_names_bin].fillna(0).values.astype(float)
    X = np.column_stack([Xc, Xb])
    return X, data["green_01"].values, data["ret_01"].values

X_tr, y_tr, r_tr = prepare(train)
X_te, y_te, r_te = prepare(test)

baseline_tr = max(np.mean(y_tr), 1 - np.mean(y_tr))
baseline_te = max(np.mean(y_te), 1 - np.mean(y_te))
print(f"Baseline treino: {baseline_tr*100:.1f}% | Baseline teste: {baseline_te*100:.1f}%")

# =============================================
# 3. Minerar no treino (RF + varredura de pares)
# =============================================
print(f"\n{'='*60}")
print("TREINO: Random Forest + varredura de pares")
print("="*60)

rf = RandomForestClassifier(n_estimators=200, max_depth=6, min_samples_leaf=15,
                             random_state=42, class_weight="balanced")
rf.fit(X_tr, y_tr)

# Extrair regras do RF
all_rules = []
for tree in rf.estimators_:
    t = tree.tree_
    def recurse(node, conditions):
        if t.feature[node] != _tree.TREE_UNDEFINED:
            name = feat_names[t.feature[node]]
            thresh = t.threshold[node]
            recurse(t.children_left[node], conditions + [(name, "<=", thresh)])
            recurse(t.children_right[node], conditions + [(name, ">", thresh)])
        else:
            total = sum(t.value[node][0])
            if total == 0: return
            pred = np.argmax(t.value[node][0])
            acc = max(t.value[node][0]) / total
            n_samples = int(t.n_node_samples[node])
            all_rules.append((n_samples, pred, acc, conditions))
    recurse(0, [])

# Unificar e filtrar
unique_train = {}
for ns, pred, acc, conds in all_rules:
    key = tuple(sorted(conds))
    if key not in unique_train or unique_train[key][2] < acc:
        unique_train[key] = (ns, pred, acc, conds)

# Filtrar: p < 0.05 vs baseline, N > MIN_SAMPLES
train_rules = []
for ns, pred, acc, conds in unique_train.values():
    if ns < MIN_SAMPLES: continue
    n_correct = int(acc * ns)
    p = stats.binomtest(n_correct, ns, p=baseline_tr, alternative="greater").pvalue
    if p < 0.05:
        train_rules.append((p, acc, ns, pred, conds))

train_rules.sort()
print(f"Regras significativas no treino: {len(train_rules)}")

# Varredura de pares binarios no treino
pair_results = []
for i in range(len(feat_names_bin)):
    for j in range(i + 1, len(feat_names_bin)):
        f1, f2 = feat_names_bin[i], feat_names_bin[j]
        for label, mask_fn in [("00", lambda a,b: (a==0)&(b==0)), ("11", lambda a,b: (a==1)&(b==1))]:
            mask = mask_fn(train[f1].values, train[f2].values)
            n_cond = mask.sum()
            if n_cond < MIN_SAMPLES or n_cond > len(train) - MIN_SAMPLES: continue
            v_cond = r_tr[mask]
            v_rest = r_tr[~mask]
            _, p = stats.ttest_ind(v_cond, v_rest, equal_var=False)
            if p < 0.05:
                pair_results.append((p, f1, f2, label, n_cond, v_cond.mean(), v_rest.mean()))

pair_results.sort()
print(f"Pares significativos no treino: {len(pair_results)}")

# =============================================
# 4. Validar no teste
# =============================================
print(f"\n{'='*60}")
print("TESTE: validacao out-of-sample (dados futuros)")
print("="*60)

# Validar regras do RF
surviving_rules = []
for p_tr, acc_tr, ns_tr, pred, conds in train_rules:
    # Aplica condicoes no teste
    mask = np.ones(len(test), dtype=bool)
    for fname, op, thresh in conds:
        idx = feat_names.index(fname)
        col = X_te[:, idx]
        if op == "<=":
            mask &= col <= thresh
        else:
            mask &= col > thresh
    n_te = mask.sum()
    if n_te < 8: continue
    y_te_sub = y_te[mask]
    acc_te = np.mean(y_te_sub == pred)
    n_correct = int(acc_te * n_te)
    p_te = stats.binomtest(n_correct, n_te, p=baseline_te, alternative="greater").pvalue
    if p_te < 0.10:
        pred_str = "COMPRA" if pred == 1 else "VENDA"
        rule_str = " E ".join(f"{f}{op}{th:.0f}" if th > 100 else f"{f}{op}{th:.3f}"
                              for f, op, th in conds[:5])
        surviving_rules.append((p_te, acc_te, n_te, pred_str, rule_str, acc_tr, ns_tr, p_tr))

# Validar pares
surviving_pairs = []
for p_tr, f1, f2, label, n_tr, ret_tr, ret_rest_tr in pair_results:
    if label == "00":
        mask = (test[f1].values == 0) & (test[f2].values == 0)
    else:
        mask = (test[f1].values == 1) & (test[f2].values == 1)
    n_te = mask.sum()
    if n_te < 8: continue
    v_cond = r_te[mask]
    v_rest = r_te[~mask]
    _, p_te = stats.ttest_ind(v_cond, v_rest, equal_var=False)
    if p_te < 0.10:
        pred_str = "COMPRA" if v_cond.mean() > 0 else "VENDA"
        surviving_pairs.append((p_te, f1, f2, label, n_te, v_cond.mean(), v_rest.mean(), p_tr, n_tr, ret_tr))

# =============================================
# 5. Resultados
# =============================================
print(f"\nRegras que sobreviveram ao walk-forward: {len(surviving_rules)}")
for p_te, acc_te, n_te, pred, rule, acc_tr, ns_tr, p_tr in sorted(surviving_rules)[:15]:
    sig = "***" if p_te < 0.05 else "*"
    print(f"  [{pred}] Teste: N={n_te} acc={acc_te*100:.0f}% p={p_te:.4f} | Treino: N={ns_tr} acc={acc_tr*100:.0f}% p={p_tr:.4f} | {rule} {sig}")

print(f"\nPares que sobreviveram ao walk-forward: {len(surviving_pairs)}")
for p_te, f1, f2, label, n_te, ret, ret_rest, p_tr, n_tr, ret_tr in sorted(surviving_pairs)[:15]:
    sig = "***" if p_te < 0.05 else "*"
    pred = "COMPRA" if ret > 0 else "VENDA"
    print(f"  [{pred}] {f1}={label[0]},{f2}={label[1]} Teste: N={n_te} ret={ret:+.1f} p={p_te:.4f} | Treino: N={n_tr} ret={ret_tr:+.1f} p={p_tr:.4f} {sig}")

# =============================================
# 6. Consolidar em regras simples
# =============================================
print(f"\n{'='*60}")
print("REGRAS CONSOLIDADAS (sobreviveram treino E teste)")
print("="*60)

consolidated = []

# Top RF rules
for p_te, acc_te, n_te, pred, rule, acc_tr, ns_tr, p_tr in sorted(surviving_rules):
    if p_te < 0.05:
        consolidated.append(("RF", pred, rule, n_te, acc_te, p_te))

# Top pairs
for p_te, f1, f2, label, n_te, ret, ret_rest, p_tr, n_tr, ret_tr in sorted(surviving_pairs):
    if p_te < 0.05:
        pred = "COMPRA" if ret > 0 else "VENDA"
        rule = f"{f1}={label[0]} AND {f2}={label[1]}"
        consolidated.append(("Par", pred, rule, n_te, 0, p_te))

print(f"Regras finais (p<0.05 no teste): {len(consolidated)}")
for src, pred, rule, n_te, acc, p in sorted(consolidated, key=lambda x: x[5]):
    acc_str = f"acc={acc*100:.0f}%" if acc > 0 else ""
    print(f"  [{src}] {pred}: {rule} (Teste N={n_te} {acc_str} p={p:.4f})")

# Marca regioes
if len(consolidated) > 0:
    # Aplica todas as regras consolidadas no teste para medir performance conjunta
    mask_compra = np.zeros(len(test), dtype=bool)
    mask_venda = np.zeros(len(test), dtype=bool)
    for src, pred, rule, n_te, acc, p in consolidated:
        # Tenta parsear a regra (simplificado: aplica cada feature manualmente)
        if pred == "COMPRA":
            # Aplica heuristica: se shadow_up ou gap aparecer na regra
            if "shadow_up_gt_q50" in rule and "=1" in rule:
                mask_compra |= test["shadow_up_gt_q50"].values == 1
            if "gap_gt_q50" in rule and "=1" in rule:
                mask_compra |= test["gap_gt_q50"].values == 1
    
    pnl_c = r_te[mask_compra]
    pnl_v = -r_te[mask_venda]
    if len(pnl_c) + len(pnl_v) > 10:
        pnl_all = np.concatenate([pnl_c, pnl_v])
        print(f"\n--- Performance consolidada no teste ---")
        print(f"COMPRA: N={len(pnl_c)} ret={pnl_c.mean():+.1f} pts")
        print(f"VENDA:  N={len(pnl_v)} ret={pnl_v.mean():+.1f} pts")
        print(f"TOTAL:  N={len(pnl_all)} ret={pnl_all.mean():+.1f} pts")
        _, p_all = stats.ttest_1samp(pnl_all, 0)
        print(f"p-valor: {p_all:.4f}")
