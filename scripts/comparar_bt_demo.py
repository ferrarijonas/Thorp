"""Compara o resultado de uma estrategia em BT (CSV) vs Demo (MT5).
Usa o mesmo periodo historico para ambos os modos e compara trades.

Uso: python scripts/comparar_bt_demo.py H102
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from datetime import datetime, timedelta
from feed.csv_feed import CsvFeed
from feed.mt5_feed import Mt5Feed
from broker.simulated import SimulatedBroker
from broker.mt5_broker import Mt5Broker
from execution.engine import ExecutionEngine
from core.types import ExecutionMode
from core.risk_guardian import RiskGuardian
import importlib

def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/comparar_bt_demo.py H103")
        sys.exit(1)
    hid = sys.argv[1].upper()

    mod_path = f"strategy.{hid}_strategy"
    try:
        mod = importlib.import_module(mod_path)
        cls = getattr(mod, f"{hid}Strategy")
    except Exception as e:
        print(f"Erro: strategy/{hid}_strategy.py nao encontrado: {e}")
        sys.exit(1)

    print(f"=== Comparacao BT vs Demo — {hid} ===")

    # --- BT com CSV ---
    feed_bt = CsvFeed()
    strat_bt = cls()
    result_bt = ExecutionEngine(feed_bt, strat_bt, SimulatedBroker(cost=10),
                                 ExecutionMode.BT).run()
    print(f"\nBT (CSV):")
    print(f"  Trades: {result_bt.total}  | Media: {result_bt.media:+.0f} pts  | WR: {result_bt.win_rate:.0f}%")
    print(f"  PF: {result_bt.profit_factor:.2f}  | p: {result_bt.p_valor:.4f}")

    # --- Demo com MT5 (mesmo periodo) ---
    try:
        from_date = datetime(2026, 5, 1)
        to_date = datetime(2026, 5, 16)
        feed_demo = Mt5Feed("WINM26", mode="historical",
                            from_date=from_date, to_date=to_date)
        strat_demo = cls()
        broker_demo = Mt5Broker(ExecutionMode.DEMO, "WINM26", 1.0)
        engine = ExecutionEngine(feed_demo, strat_demo, broker_demo,
                                  ExecutionMode.DEMO, risk_guardian=RiskGuardian())
        result_demo = engine.run()
        print(f"\nDemo (MT5 historico {from_date.date()} a {to_date.date()}):")
        print(f"  Trades: {result_demo.total}  | Media: {result_demo.media:+.0f} pts  | WR: {result_demo.win_rate:.0f}%")
        print(f"  PF: {result_demo.profit_factor:.2f}  | p: {result_demo.p_valor:.4f}")

        # Comparacao
        print(f"\n--- Diferenca ---")
        print(f"  Trades: BT={result_bt.total} vs Demo={result_demo.total} (diferenca={result_bt.total - result_demo.total})")
        print(f"  Media: BT={result_bt.media:+.0f} vs Demo={result_demo.media:+.0f}")
    except Exception as e:
        print(f"\nDemo nao disponivel: {e}")

    with open("state/decisions.log", "a") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M} | Comparacao {hid}: BT trades={result_bt.total} media={result_bt.media:+.0f} p={result_bt.p_valor:.4f}\n")

if __name__ == "__main__":
    main()
