"""Pipeline de teste em 2 gates:
Gate 1: BT ideal (rápido, sem slippage)
  Se p >= 0.05 → MORTA (70% morrem aqui)
Gate 2: BT com slippage calibrado
  Se p < 0.05 E metades ok → PASSOU

Se especificar --compare, roda worst-case + best-case das convenções OHLC.
Se ambos concordam (same direction), edge é robusto.
Se divergem, edge é path-dependent → MORTA.

Uso: python scripts/pipeline.py H102
     python scripts/pipeline.py --compare H102
     python scripts/pipeline.py H102 H103 H104
     python scripts/pipeline.py all
"""
import sys, os, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.CRITICAL)
for nome in ["engine", "feed", "broker", "root"]:
    logging.getLogger(nome).setLevel(logging.CRITICAL)

from feed.csv_feed import CsvFeed
from broker.simulated import SimulatedBroker
from execution.engine import ExecutionEngine
from core.types import ExecutionMode
from core.risk_guardian import RiskGuardian
from core.calibrator import Calibrator
from core.data import load_csv

def testar_uma(hid, cls, df, rg, slippage, convention="worst"):
    feed = CsvFeed(); feed.reset()
    strategy = cls()
    if getattr(strategy, "USAR_CONTAINER_MINUTO", False):
        rg.usar_container_minuto()
    engine = ExecutionEngine(feed, strategy, SimulatedBroker(cost=10),
                              ExecutionMode.BT, risk_guardian=rg,
                              slippage=slippage, convention=convention)
    r = engine.run()
    return r

def _rodar_comparacao(hid, cls, df, rg, slippage):
    """Roda worst-case e best-case. Retorna (worst_r, best_r, robusto)."""
    w = testar_uma(hid, cls, df, rg, slippage, convention="worst")
    b = testar_uma(hid, cls, df, rg, slippage, convention="best")
    mesmo_sinal = (w.media > 0) == (b.media > 0)
    robusto = mesmo_sinal and w.p_valor < 0.05 and b.p_valor < 0.05
    return w, b, robusto

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = set(a for a in sys.argv[1:] if a.startswith("--"))
    comparar = "--compare" in flags

    if not args:
        print("Uso: python scripts/pipeline.py [--compare] H102 [H103 ...]")
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

    if comparar:
        cabecalho = f"{'ID':<6} {'N':>5} {'Worst':>7} {'p_w':>7} {'Best':>7} {'p_b':>7} {'Robusto':<8}"
        print(cabecalho)
        print("-" * 55)
    else:
        print(f"{'ID':<6} {'Gate1':<8} {'N':>5} {'Media':>6} {'WR':>4} {'p':>7} | {'Gate2':<8} {'N':>5} {'Media':>6} {'WR':>4} {'p':>7} {'Status':<8}")
        print("-" * 85)

    for hid, cls in estrategias.items():
        if comparar:
            w, b, robusto = _rodar_comparacao(hid, cls, df, rg, slippage=None)
            sinal_w = f"{w.media:+.0f}" if w.p_valor < 0.05 else f"{w.media:+.0f}ns"
            sinal_b = f"{b.media:+.0f}" if b.p_valor < 0.05 else f"{b.media:+.0f}ns"
            status = "ROBUSTO" if robusto else "MORTA"
            print(f"{hid:<6} {w.total:>5} {sinal_w:>7} {w.p_valor:>7.4f} {sinal_b:>7} {b.p_valor:>7.4f} {status:<8}")
            with open("state/decisions.log", "a") as f:
                f.write(f"2026-05-18 | {hid} worst={w.media:+.0f}(p={w.p_valor:.4f}) best={b.media:+.0f}(p={b.p_valor:.4f}) {status}\n")
        else:
            # Gate 1: BT ideal (rápido)
            r1 = testar_uma(hid, cls, df, rg, slippage=None, convention="worst")
            g1_status = "PASSOU" if r1.p_valor < 0.05 and r1.metades_ok else "MORTA"

            if g1_status == "MORTA":
                print(f"{hid:<6} {g1_status:<8} {r1.total:>5} {r1.media:>+6.0f} {r1.win_rate:>3.0f}% {r1.p_valor:>7.4f} | {'—':<8} {'—':>5} {'—':>6} {'—':>4} {'—':>7} MORTA")
                with open("state/decisions.log", "a") as f:
                    f.write(f"2026-05-18 | {hid} Gate1=morto | p={r1.p_valor:.4f} WR={r1.win_rate:.0f}% media={r1.media:+.0f}pts\n")
                continue

            # Gate 2: BT com slippage (se passou gate 1)
            try:
                slippage = Calibrator.criar_slippage()
            except Exception:
                slippage = None

            r2 = testar_uma(hid, cls, df, rg, slippage=slippage, convention="worst")
            g2_status = "PASSOU" if r2.p_valor < 0.05 and r2.metades_ok else "MORTA"
            status_final = g2_status

            modo = f"slippage(slip={slippage.slip_pts} spread={slippage.spread_pts})" if slippage else "ideal"
            print(f"{hid:<6} {g1_status:<8} {r1.total:>5} {r1.media:>+6.0f} {r1.win_rate:>3.0f}% {r1.p_valor:>7.4f} | {g2_status:<8} {r2.total:>5} {r2.media:>+6.0f} {r2.win_rate:>3.0f}% {r2.p_valor:>7.4f} {status_final:<8}")
            with open("state/decisions.log", "a") as f:
                f.write(f"2026-05-18 | {hid} Gate1=p{r1.p_valor:.4f} Gate2({modo})=p{r2.p_valor:.4f} media={r2.media:+.0f}pts -> {status_final}\n")

if __name__ == "__main__":
    main()
