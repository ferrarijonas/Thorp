import numpy as np
from scipy import stats

def run(df, params):
    trades = []
    for dia, g in df.groupby(df.index.date):
        g = g.sort_index()
        janela = g[(g["h"]==9) & (g["m"]>=6) & (g["m"]<=20)]
        if len(janela)==0: continue
        c906 = g[(g["h"]==9) & (g["m"]==6)]
        if len(c906)==0: continue
        idx=c906.index[0]; pos=df.index.get_loc(idx)
        try: c1=df.iloc[pos-1]["close"]; o6=df.iloc[pos-6]["open"]
        except: continue
        if not (c1 < o6 * 0.997): continue

        entrada = janela.iloc[0]["open"]
        stop = entrada - 125
        target = entrada + 125

        res = None
        for _, c in janela.iterrows():
            if c["low"] <= stop: res = stop - entrada; break
            if c["high"] >= target: res = target - entrada; break
            if c["m"] == 20: res = c["close"] - entrada; break
        if res is None: res = 0
        trades.append(res - 10)

    t = np.array(trades)
    if len(t)==0:
        return {"trades":0,"media_pts":0,"wr_pct":0,"pf":0,"p_valor":1,"metade1_media":0,"metade2_media":0,"metades_ok":False,"status":"SEM_TRADES"}

    media = t.mean()
    t_stat, p_val = stats.ttest_1samp(t, 0)
    met1=t[:len(t)//2]; met2=t[len(t)//2:]
    bruto = t[t>0].sum() if t[t>0].sum() else 0
    perda = abs(t[t<0].sum()) if t[t<0].sum() else 0
    pf = bruto/perda if perda > 0 else 0
    wr = np.mean(t>0)*100
    met1_media = met1.mean() if len(met1) else 0
    met2_media = met2.mean() if len(met2) else 0
    metades_ok = (met1_media>0) == (met2_media>0)

    if p_val < 0.05 and metades_ok:
        status = "PASSOU"
    else:
        status = "MORTA"

    return {
        "trades": int(len(t)),
        "media_pts": round(float(media), 1),
        "wr_pct": round(float(wr), 1),
        "pf": round(float(pf), 2),
        "p_valor": round(float(p_val), 4),
        "metade1_media": round(float(met1_media), 1),
        "metade2_media": round(float(met2_media), 1),
        "metades_ok": bool(metades_ok),
        "status": status
    }
