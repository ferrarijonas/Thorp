"""Avalia uma hipotese com multiplos TP, convencoes OHLC e geometria de entrada.
Uso: python scripts/avaliar_hipotese.py H109
     python scripts/avaliar_hipotese.py --entry H111  (testa 5 geometrias)
     python scripts/avaliar_hipotese.py H109 H110 H111
"""
import sys, os, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.CRITICAL)
for n in ["engine","feed","broker","root"]:
    logging.getLogger(n).setLevel(logging.CRITICAL)

from feed.csv_feed import CsvFeed
from broker.simulated import SimulatedBroker
from execution.engine import ExecutionEngine
from core.types import ExecutionMode, Direction
from core.risk_guardian import RiskGuardian
from core.data import load_csv
from core.containers import P50 as P50_PTS, P75 as P75_PTS

TP_NIVEIS = [
    ("P50",   lambda sp,m: P50_PTS.get(m, 120)),
    ("P75",   lambda sp,m: sp),
    ("2xP75", lambda sp,m: sp*2),
    ("3xP75", lambda sp,m: sp*3),
]
ENTRY_GEO = ["open", "close", "low", "high", "mid"]

def _entry_price(rastro, entry_geo, trade_entry):
    """Calcula preco de entrada alternativo a partir do primeiro bar do rastro."""
    if entry_geo == "actual":
        return trade_entry
    O, H, L, C, _ = rastro[0]
    mapa = {"open": O, "close": C, "low": L, "high": H, "mid": (H+L)/2}
    return mapa.get(entry_geo, trade_entry)

def _rastro_offset(entry_geo):
    """Entrada no close: ignora barra de entrada (o trade abre no fim dela)."""
    return 1 if entry_geo == "close" else 0

def re_simular_um(trade, sl_pts, tp_pts, convention="worst", entry_geo="actual"):
    if not trade.rastro:
        return None
    direcao = trade.direction
    entry = _entry_price(trade.rastro, entry_geo, trade.entry)
    offset = _rastro_offset(entry_geo)
    rastro = trade.rastro[offset:]

    def check(bar, first_check_fn, second_check_fn):
        O, H, L, C, _ = bar
        if first_check_fn(H, L, C):
            return True, "first"
        if second_check_fn(H, L, C):
            return True, "second"
        return False, None

    if direcao == Direction.LONG:
        if convention == "worst":
            first = lambda H,L,C: L <= entry - sl_pts
            first_exit = -sl_pts
            second = lambda H,L,C: H >= entry + tp_pts
            second_exit = tp_pts
        else:
            first = lambda H,L,C: H >= entry + tp_pts
            first_exit = tp_pts
            second = lambda H,L,C: L <= entry - sl_pts
            second_exit = -sl_pts
    else:
        if convention == "worst":
            first = lambda H,L,C: H >= entry + sl_pts
            first_exit = -sl_pts
            second = lambda H,L,C: L <= entry - tp_pts
            second_exit = tp_pts
        else:
            first = lambda H,L,C: L <= entry - tp_pts
            first_exit = tp_pts
            second = lambda H,L,C: H >= entry + sl_pts
            second_exit = -sl_pts

    for bar in rastro:
        O, H, L, C, _ = bar
        if first(H, L, C):
            return first_exit
        if second(H, L, C):
            return second_exit

    last_close = rastro[-1][3] if rastro else entry
    return (last_close - entry) if direcao == Direction.LONG else (entry - last_close)

def _calc_estatisticas(pnls):
    arr = [p for p in pnls if p is not None]
    if len(arr) < 5:
        return {"n": 0, "media": 0, "wr": 0, "p": 1}
    import numpy as np
    from scipy import stats
    t = np.array(arr, dtype=float)
    _, p_val = stats.ttest_1samp(t, 0)
    wins = (t > 0).sum()
    return {
        "n": len(t),
        "media": round(float(t.mean()), 1),
        "wr": round(wins / len(t) * 100, 1),
        "p": round(float(p_val), 4),
    }

def avaliar(hid, cls, df, rg, testar_entrada=False):
    feed = CsvFeed(); feed.reset()
    engine = ExecutionEngine(feed, cls(), SimulatedBroker(cost=10),
                              ExecutionMode.BT, risk_guardian=rg,
                              convention="worst")
    resultado = engine.run()
    trades = resultado.trades
    if not trades:
        print(f"{hid}: 0 trades"); return

    def sl_pts(t):
        return P75_PTS.get(t.opened_at.minute, 175)

    geos = ENTRY_GEO if testar_entrada else ["actual"]

    for geo in geos:
        label_geo = f"entry={geo}" if testar_entrada else ""
        if testar_entrada:
            print(f"\n{hid} — {label_geo}")
            print(f"{'TP':>8} | {'worst':>20} {'':>20} | {'best':>20}")
        else:
            print(f"\n{hid} — SL=P75 por minuto de entrada")
            print(f"{'TP':>8} | {'worst':>20} {'':>20} | {'best':>20}")
        print(f"{'TP':>8} | {'media':>7} {'WR':>5} {'p':>7} | {'media':>7} {'WR':>5} {'p':>7}")
        print("-" * 65)

        for nome_tp, tp_fn in TP_NIVEIS:
            for conv in ["worst", "best"]:
                pnls = []
                for t in trades:
                    sp = sl_pts(t)
                    m = t.opened_at.minute
                    tp_pts = round(tp_fn(sp, m))
                    pnls.append(re_simular_um(t, sp, tp_pts, conv))
                est = _calc_estatisticas(pnls)
                if conv == "worst":
                    worst_est = est
                else:
                    best_est = est
            print(f"{nome_tp:>8} | {worst_est['media']:>+7.0f} {worst_est['wr']:>5.1f}% {worst_est['p']:>7.4f} | {best_est['media']:>+7.0f} {best_est['wr']:>5.1f}% {best_est['p']:>7.4f}")

    if not testar_entrada:
        print(f"\nOriginal (P50 worst): N={resultado.total} media={resultado.media:+.0f} WR={resultado.win_rate:.0f}% p={resultado.p_valor:.4f}")
    if testar_entrada:
        print(f"\nOriginal: N={resultado.total} | Rode sem --entry para tabela compacta")

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = set(a for a in sys.argv[1:] if a.startswith("--"))
    testar_entrada = "--entry" in flags

    if not args:
        print("Uso: python scripts/avaliar_hipotese.py [--entry] H109 [H110 ...]")
        sys.exit(1)

    import importlib
    df = load_csv()
    rg = RiskGuardian(capital=1000, max_dd=99999, rr_ratio=1.5)
    rg.calibrate(df)

    for hid in args:
        try:
            mod = importlib.import_module(f"strategy.{hid}_strategy")
            cls = getattr(mod, f"{hid}Strategy")
            avaliar(hid, cls, df, rg, testar_entrada)
        except Exception as e:
            print(f"{hid}: ERRO {e}")
            import traceback; traceback.print_exc()

if __name__ == "__main__":
    main()
