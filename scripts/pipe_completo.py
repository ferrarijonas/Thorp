"""Mostra o pipe completo de uma estrategia rodando em BT (CSV) vs Real (MT5).
Usa o mesmo codigo, mesmos componentes, muda so feed + broker.

Uso: python scripts/pipe_completo.py H103
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from feed.csv_feed import CsvFeed
from feed.mt5_feed import Mt5Feed
from broker.simulated import SimulatedBroker
from broker.mt5_broker import Mt5Broker
from execution.engine import ExecutionEngine
from execution.slippage import SlippageModel
from core.types import ExecutionMode
from core.risk_guardian import RiskGuardian
from core.data import load_csv
from datetime import datetime, timedelta
import importlib

def main():
    hid = sys.argv[1].upper() if len(sys.argv) > 1 else "H103"
    try:
        mod = importlib.import_module("strategy." + hid + "_strategy")
        strategy_cls = getattr(mod, hid + "Strategy")
    except Exception as e:
        print("Erro:", e)
        sys.exit(1)

    df = load_csv()
    sep = "=" * 60
    line = "-" * 60
    print()
    print(sep)
    print("  " + hid + " \u2014 Pipe Completo: CSV vs MT5")
    print(sep)

    # ======================
    # 1. BT com CSV
    # ======================
    print()
    print(line)
    print("  [1] BT (CSV historico)")
    print(line)
    print("  Feed:       CsvFeed.poll() -> Bar do Historico_OHLC.csv")
    print("  Strategy:   " + hid + "Strategy.on_bar(bar) -> Signal")
    print("  RiskGuard:  process() -> stop/target/size")
    print("  Slippage:   on_entry() -> +10pts entry, -15pts stop, +10pts target")
    print("  Broker:     SimulatedBroker.execute() -> Order(FILLED)")
    print("  Engine:     gerencia posicao, stop, target, time")

    rg_bt = RiskGuardian(1000, 99999, 1.5)
    rg_bt.calibrate(df)
    slip = SlippageModel(slip_pts=10, spread_pts=5, slip_stop_pts=15, slip_target_pts=10)
    eng_bt = ExecutionEngine(CsvFeed(), strategy_cls(), SimulatedBroker(10),
                              ExecutionMode.BT, risk_guardian=rg_bt, slippage=slip)
    r_bt = eng_bt.run()

    print()
    print("  Resultado BT:")
    print("    Trades: " + str(r_bt.total) + " | Media: " + f"{r_bt.media:+.0f}" + " pts | WR: " + f"{r_bt.win_rate:.0f}%")
    print("    PF: " + f"{r_bt.profit_factor:.2f}" + " | p: " + f"{r_bt.p_valor:.4f}")
    print("    Capital: 1000 -> " + f"{rg_bt.capital:.0f}")

    # ======================
    # 2. Demo com MT5
    # ======================
    print()
    print(line)
    print("  [2] Demo (MT5 historico recente)")
    print(line)
    print("  Feed:       Mt5Feed.poll() -> Bar do terminal MT5 (WINM26)")
    print("  Strategy:   " + hid + "Strategy.on_bar(bar) -> Signal (MESMA)")
    print("  RiskGuard:  process() -> stop/target/size (MESMA config)")
    print("  Slippage:   on_entry() -> pass (modo demo, sem degradacao)")
    print("  Broker:     Mt5Broker.execute() -> mt5.order_send() (ORDEM REAL)")
    print("  Engine:     gerencia posicao, stop, target, time (MESMA)")

    try:
        feed_demo = Mt5Feed("WINM26", mode="historical",
            from_date=datetime.now() - timedelta(days=2),
            to_date=datetime.now())
        rg_demo = RiskGuardian(1000, 99999, 1.5)
        rg_demo.calibrate(df)
        eng_demo = ExecutionEngine(feed_demo, strategy_cls(),
            Mt5Broker(ExecutionMode.DEMO, "WINM26", 1.0),
            ExecutionMode.DEMO, risk_guardian=rg_demo)
        r_demo = eng_demo.run()

        print()
        print("  Resultado Demo:")
        print("    Trades: " + str(r_demo.total) + " | Media: " + f"{r_demo.media:+.0f}" + " pts | WR: " + f"{r_demo.win_rate:.0f}%")
    except Exception as e:
        print()
        print("  Demo indisponivel:", e)

    # ======================
    # 3. Comparacao
    # ======================
    print()
    print(line)
    print("  [3] Diferenca BT vs Demo")
    print(line)
    print("  Feed difere:      CSV estatico (331k candles) vs MT5 historico (ao vivo)")
    print("  Broker difere:    Simulated (fill instantaneo) vs Mt5Broker (ordem real)")
    print("  Slippage difere:  10pts/slip BT vs 0pts/slip Demo (real)")
    print("  Strategy:         IDENTICA nos dois modos")
    print("  Engine:           IDENTICO nos dois modos")
    print("  RiskGuardian:     IDENTICO nos dois modos")

    print()
    print(sep)
    print("  RESUMO: Estrategia, Engine e RiskGuardian sao 1:1.")
    print("  A diferenca entre CSV e MT5 esta APENAS no Feed + Broker.")
    print(sep)
    print()

if __name__ == "__main__":
    main()
