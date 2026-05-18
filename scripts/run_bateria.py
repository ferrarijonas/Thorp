"""Roda multiplas estrategias em backtest com slippage calibrado.
Uso: python scripts/run_bateria.py H102 H103 H104
     python scripts/run_bateria.py all          # todas as H10x
     python scripts/run_bateria.py --ideal H102 # sem slippage
"""

import sys, os, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from feed.csv_feed import CsvFeed
from broker.simulated import SimulatedBroker
from execution.engine import ExecutionEngine
from core.types import ExecutionMode
from core.risk_guardian import RiskGuardian
from core.calibrator import Calibrator
from core.data import load_csv

logging.basicConfig(level=logging.WARNING)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = set(a for a in sys.argv[1:] if a.startswith("--"))
    usar_slippage = "--ideal" not in flags

    if not args:
        print("Uso: python scripts/run_bateria.py [--ideal] H102 H103 ...")
        sys.exit(1)

    if args[0] == "all":
        args = [f"H{i}" for i in range(102, 121)]

    import importlib
    estrategias = {}
    for hid in args:
        try:
            mod = importlib.import_module(f"strategy.{hid}_strategy")
            cls = getattr(mod, f"{hid}Strategy")
            estrategias[hid] = cls
        except Exception as e:
            print(f"  ERRO {hid}: {e}")

    if not estrategias:
        print("Nenhuma estrategia valida encontrada")
        sys.exit(1)

    df = load_csv()
    rg = RiskGuardian(capital=1000, max_dd=99999, rr_ratio=1.5)
    rg.calibrate(df)

    slippage = None
    modo_label = "ideal"
    if usar_slippage:
        try:
            slippage = Calibrator.criar_slippage()
            modo_label = f"slippage(slip={slippage.slip_pts} spread={slippage.spread_pts})"
        except Exception:
            pass

    print(f"Modo: {modo_label}")
    print(f"{'ID':<6} {'Trades':>6} {'Media':>6} {'WR':>4} {'PF':>5} {'p':>7} {'Met1':>6} {'Met2':>6} {'Status':<8}")
    print("-" * 60)

    for hid, cls in estrategias.items():
        feed_base = CsvFeed(); feed_base.reset()
        strategy = cls()
        engine = ExecutionEngine(feed_base, strategy, SimulatedBroker(cost=10),
                                  ExecutionMode.BT, risk_guardian=rg, slippage=slippage)
        try:
            r = engine.run()
            status = "PASSOU" if r.p_valor < 0.05 and r.metades_ok else "MORTA"
            print(f"{hid:<6} {r.total:>6} {r.media:>+6.0f} {r.win_rate:>3.0f}% {r.profit_factor:>5.2f} {r.p_valor:>7.4f} {r.metade1_media:>+6.0f} {r.metade2_media:>+6.0f} {status:<8}")
            with open("state/decisions.log", "a") as f:
                f.write(f"2026-05-18 | {hid} testado ({modo_label}) | p={r.p_valor:.4f} WR={r.win_rate:.0f}% media={r.media:+.0f}pts metades={r.metade1_media:+.0f}/{r.metade2_media:+.0f} -> {status}\n")
        except Exception as e:
            print(f"{hid:<6} {'ERRO':>6} {str(e)[:30]:<30}")

    print(f"\nCapital final: {rg.capital:.0f} (inicial 1000)")

if __name__ == "__main__":
    main()
