"""Compara execucao de uma estrategia em:
  - BT sem slippage (ideal)
  - BT com slippage (realista)
  - Demo (real)
  
Uso: python scripts/comparar_execucao.py H103
"""

from datetime import datetime, timedelta
from feed.csv_feed import CsvFeed
from feed.mt5_feed import Mt5Feed
from broker.simulated import SimulatedBroker
from broker.mt5_broker import Mt5Broker
from execution.engine import ExecutionEngine
from execution.slippage import SlippageModel
from core.types import ExecutionMode
from core.risk_guardian import RiskGuardian
from core.data import load_csv
import importlib

def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/comparar_execucao.py H103")
        sys.exit(1)
    hid = sys.argv[1].upper()
    try:
        mod = importlib.import_module(f"strategy.{hid}_strategy")
        cls = getattr(mod, f"{hid}Strategy")
    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)

    df = load_csv()
    print(f"\n=== {hid} — Comparacao de Execucao ===\n")

    # 1. BT ideal (sem slippage)
    rg = RiskGuardian(1000, 99999, 1.5)
    rg.calibrate(df)
    e1 = ExecutionEngine(CsvFeed(), cls(), SimulatedBroker(10), ExecutionMode.BT, risk_guardian=rg)
    r1 = e1.run()
    print(f"BT ideal:       {r1.total:>4} trades | media {r1.media:>+6.0f} pts | WR {r1.win_rate:>3.0f}% | PF {r1.profit_factor:.2f} | p {r1.p_valor:.4f}")

    # 2. BT com slippage
    rg2 = RiskGuardian(1000, 99999, 1.5)
    rg2.calibrate(df)
    slip = SlippageModel(slip_pts=10, spread_pts=5, slip_stop_pts=15, slip_target_pts=10)
    e2 = ExecutionEngine(CsvFeed(), cls(), SimulatedBroker(10), ExecutionMode.BT, risk_guardian=rg2, slippage=slip)
    r2 = e2.run()
    print(f"BT + slippage:  {r2.total:>4} trades | media {r2.media:>+6.0f} pts | WR {r2.win_rate:>3.0f}% | PF {r2.profit_factor:.2f} | p {r2.p_valor:.4f}")

    # 3. Demo com MT5 (historico recente)
    try:
        from_date = datetime(2026, 5, 1)
        to_date = datetime(2026, 5, 16)
        rg3 = RiskGuardian(1000, 99999, 1.5)
        rg3.calibrate(df)
        feed_demo = Mt5Feed("WINM26", mode="historical", from_date=from_date, to_date=to_date)
        e3 = ExecutionEngine(feed_demo, cls(), Mt5Broker(ExecutionMode.DEMO, "WINM26", 1.0),
                              ExecutionMode.DEMO, risk_guardian=rg3)
        r3 = e3.run()
        print(f"Demo historico: {r3.total:>4} trades | media {r3.media:>+6.0f} pts | WR {r3.win_rate:>3.0f}% | PF {r3.profit_factor:.2f} | p {r3.p_valor:.4f}")
    except Exception as e:
        print(f"Demo: indisponivel ({e})")

    # Diferenca
    print(f"\nDiferenca BT ideal vs BT+slippage:")
    print(f"  Trades: {r1.total} → {r2.total}  (perdeu {r1.total - r2.total})")
    print(f"  Media: {r1.media:+.0f} → {r2.media:+.0f} pts (diferenca {r2.media - r1.media:+.0f})")

if __name__ == "__main__":
    main()
