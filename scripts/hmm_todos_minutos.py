"""HMM puro — vetorizado. Foco: transicao 9:00 -> 9:01."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from scipy import stats
from core.data import load_csv

np.random.seed(42)

print("Carregando...")
df = load_csv()
df_b3 = df.between_time("09:00", "17:00")
n = len(df_b3)
print(f"Candles B3: {n:,}")

# Features vetorizadas
r = (df_b3["high"] - df_b3["low"]).values
ba = (df_b3["close"] - df_b3["open"]).abs().values
b = (df_b3["close"] - df_b3["open"]).values
v = df_b3["volume"].values
c = df_b3["close"].values
o = df_b3["open"].values

X = np.column_stack([
    np.log1p(r),
    np.log1p(ba),
    ba / (r + 1),
    np.sign(b),
    np.log1p(v),
]).astype(np.float32)

X_s = StandardScaler().fit_transform(X)
print("GMM K=5...")
gmm = GaussianMixture(n_components=5, covariance_type="full",
                      random_state=42, max_iter=200, reg_covar=1e-4)
states = gmm.fit_predict(X_s)

# Perfil dos estados
print(f"\n--- Perfil dos 5 estados ---")
print(f"{'Est':>4} {'N':>8} {'%':>5} {'Range':>7} {'Body':>7} {'Body%':>6} {'Dir+%':>5}")
for k in range(5):
    mk = states == k
    nk = mk.sum()
    m = np.median
    print(f"{k:>4} {nk:>8} {nk/n*100:>4.1f}% {m(r[mk]):>7.0f} {m(ba[mk]):>7.0f} {m(ba[mk])/(m(r[mk])+1)*100:>5.1f}% {np.mean(b[mk]>0)*100:>4.1f}%")

# ==============================
# 9:00 -> 9:01  (vetorizado)
# ==============================
print(f"\n{'='*55}")
print("TRANSICAO 9:00 -> 9:01")
print("="*55)

h = df_b3.index.hour.values
m = df_b3.index.minute.values
dia = df_b3.index.date

mask9 = (h == 9) & (m == 0)
mask01 = (h == 9) & (m == 1)

# Encontra pares: 9:00 seguido de 9:01 no mesmo dia
idx_ok = []
for i in range(n-1):
    if mask9[i] and mask01[i+1] and dia[i] == dia[i+1]:
        idx_ok.append(i)

idx_ok = np.array(idx_ok)
print(f"Pares: {len(idx_ok)} dias")

s9 = states[idx_ok]
s01 = states[idx_ok + 1]
rets = c[idx_ok + 1] - o[idx_ok + 1]

# Matriz de transicao
print(f"\nMatriz de transicao 9:00 -> 9:01:")
print("S9\\S01", end="")
for j in range(5):
    print(f"   S{j}", end="")
print(f"  {'N':>5}  {'Ret':>7}  {'pval':>7}")
for i in range(5):
    mi = s9 == i
    ni = mi.sum()
    if ni == 0: continue
    print(f"  S{i}   ", end="")
    for j in range(5):
        print(f"{(mi & (s01 == j)).sum():>5}", end="")
    rk = rets[mi]
    _, p = stats.ttest_1samp(rk, 0) if len(rk)>=3 else (0,1)
    print(f"  {ni:>5}  {rk.mean():+6.1f}  {p:.4f}")

# Retorno por estado de 9:00
print(f"\nCondicional ao estado de 9:00:")
any_p = False
for k in range(5):
    mk = s9 == k
    nk = mk.sum()
    if nk < 10: continue
    rk = rets[mk]
    _, p = stats.ttest_1samp(rk, 0)
    d = np.mean(rk > 0) * 100
    fl = " <-- p<0.05" if p < 0.05 else ""
    if p < 0.05: any_p = True
    print(f"  S{k}: N={nk:>3} ret={rk.mean():+6.1f}pts dir+={d:.0f}% p={p:.4f}{fl}")

# ==============================
# Matriz global (vetorizada)
# ==============================
print(f"\n{'='*55}")
print("MATRIZ GLOBAL (todos os minutos, intraday)")
print("="*55)

# Pares consecutivos mesmo dia
same_day = dia[:-1] == dia[1:]
s_from = states[:-1][same_day]
s_to = states[1:][same_day]
n_trans = len(s_from)

trans_norm = np.zeros((5, 5))
for i in range(5):
    mask_i = s_from == i
    total_i = mask_i.sum()
    if total_i > 0:
        for j in range(5):
            trans_norm[i, j] = (mask_i & (s_to == j)).sum() / total_i

print(f"Transicoes: {n_trans:,}")
print(f"\nDe\\Para", end="")
for j in range(5): print(f"   S{j}", end="")
print(f"  {'Permanece':>10}")
for i in range(5):
    print(f"  S{i}   ", end="")
    for j in range(5):
        print(f"{trans_norm[i,j]:>6.4f}", end="")
    print(f"  {trans_norm[i,i]*100:>9.1f}%")

# Retorno do minuto seguinte por estado
print(f"\nRetorno t+1 condicionado ao estado:")
for k in range(5):
    mk = s_from == k
    nk = mk.sum()
    if nk < 100: continue
    rk = c[1:][same_day][mk] - c[:-1][same_day][mk]
    _, p = stats.ttest_1samp(rk, 0)
    d = np.mean(rk > 0) * 100
    fl = " ***" if p < 0.01 else " *" if p < 0.05 else ""
    print(f"  S{k}: N={nk:>8,} ret={rk.mean():+7.2f}pts dir+={d:.0f}% p={p:.4f}{fl}")

print(f"\n--- CONCLUSAO ---")
if any_p:
    print("Ha estado(s) latente(s) com poder preditivo em 9:00 -> 9:01!")
else:
    print("Nenhum estado de 9:00 preve 9:01 com p<0.05.")
    print("A transicao 9:00 -> 9:01 e essencialmente ruido branco.")
    print("O primeiro minuto do dia nao carrega informacao suficiente.")
