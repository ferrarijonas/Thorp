"""Payoff Table Builder — pre-computa rastros 9:01→17:00 por dia.
Uso: python scripts/payoff_table.py
Saida: state/payoff_table.json (~250KB, ~1100 dias)
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.data import load_csv
import numpy as np

def build(entry_minute=1, max_bars=480):
    df = load_csv()
    df = df.between_time("09:00", "17:00").copy()
    df["date"] = df.index.date
    df["h"] = df.index.hour
    df["m"] = df.index.minute

    rastros = {}
    dias = sorted(set(df["date"]))

    for dia in dias:
        day = df[df["date"] == dia]
        # Encontra barra de entrada
        entry_bars = day[(day["h"] == 9) & (day["m"] == entry_minute)]
        if len(entry_bars) == 0:
            continue
        entry_row = entry_bars.iloc[0]
        entry = float(entry_row["open"])

        # Pega barras a partir da entrada ate o fim do dia
        entry_idx = day.index.get_loc(entry_row.name)
        after = day.iloc[entry_idx:entry_idx + max_bars]

        if len(after) < 1:
            continue

        H = after["high"].values.astype(float)
        L = after["low"].values.astype(float)
        C = after["close"].values.astype(float)

        running_max_H = np.maximum.accumulate(H) - entry
        running_min_L = np.minimum.accumulate(L) - entry

        rastros[str(dia)] = {
            "d": str(dia),
            "e": round(entry, 1),
            "n": len(H),
            "h": [round(float(x), 1) for x in running_max_H],
            "l": [round(float(x), 1) for x in running_min_L],
            "c": [round(float(x), 1) for x in C],
        }

    table = {
        "meta": {
            "entry_minute": entry_minute,
            "max_bars": max_bars,
            "n_dias": len(rastros),
        },
        "rastros": rastros,
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "state", "payoff_table.json")
    with open(out_path, "w") as f:
        json.dump(table, f)

    print(f"Payoff table: {len(rastros)} dias salvos em {out_path}")
    print(f"Minuto entrada: 9:{entry_minute:02d}")
    print(f"Barras max: {max_bars}")
    return table

if __name__ == "__main__":
    build()
