"""Avalia uma hipótese: 1 BT + 5 seções de análise.
Se houver calibração de slippage, inclui CUSTO REAL (BT com custo real de execução).

Uso: python scripts/avaliar_hipotese.py H109
      python scripts/avaliar_hipotese.py H109 H110 H111
"""
import sys, os, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.CRITICAL)
for n in ["engine", "feed", "broker", "root"]:
    logging.getLogger(n).setLevel(logging.CRITICAL)

from feed.csv_feed import CsvFeed
from broker.simulated import SimulatedBroker
from execution.engine import ExecutionEngine
from core.types import ExecutionMode
from core.risk_guardian import RiskGuardian
from core.data import load_csv
from core.containers import P50 as P50_PTS, P75 as P75_PTS
from core.analisador import Analisador
from core.calibrator import Calibrator

TP_NIVEIS = [
    ("TIME",  None),
    ("P50",   lambda sp, m: P50_PTS.get(m, 120)),
    ("P75",   lambda sp, m: sp),
    ("2xP75", lambda sp, m: sp * 2),
    ("3xP75", lambda sp, m: sp * 3),
]


def _criar_engine(df, cls, rg, slippage=None, convention="worst"):
    feed = CsvFeed(df=df); feed.reset()
    strategy = cls()
    rg.usar_container_hora()
    if getattr(strategy, "USAR_CONTAINER_MINUTO", False):
        rg.usar_container_minuto()
    return ExecutionEngine(feed, strategy, SimulatedBroker(cost=10),
                           ExecutionMode.BT, risk_guardian=rg,
                           slippage=slippage, convention=convention)


def avaliar(hid, cls, df, rg, slippage=None):
    # BT ideal
    engine = _criar_engine(df, cls, rg)
    resultado = engine.run()
    trades = resultado.trades
    if not trades:
        print(f"\n{hid} | 0 trades | MORTA\n")
        return

    def sl_fn(t):
        return P75_PTS.get(t.opened_at.minute, 175)

    tp_fn = lambda sp, m: P50_PTS.get(m, 120)

    g = Analisador.calcular(trades)
    entrada = Analisador.vantagem_por_entrada(trades, sl_fn, tp_fn, "worst")
    tempo = Analisador.decaimento_temporal(trades)
    cont = Analisador.re_simular(trades, sl_fn, TP_NIVEIS)
    veredito = Analisador.veredito(trades, sl_fn, tp_fn)

    # CUSTO REAL: BT com slippage calibrado
    custo = None
    if slippage:
        engine2 = _criar_engine(df, cls, rg, slippage=slippage)
        custo = engine2.run()

    _print(hid, g, entrada, tempo, cont, veredito, custo, slippage)


def _print(hid, g, entrada, tempo, cont, veredito, custo, slippage):
    mfe = g["mfe_medio"]
    mae = g["mae_medio"]
    assimetria = mfe - mae
    print(f"\n{hid} | N={g['N']} | {veredito}")
    print()
    print("ANOMALIA (rastro puro)")
    print(f"  MFE +{mfe:.0f}  MAE -{mae:.0f}  assimetria {assimetria:+.0f}")
    print()

    # Ponto de entrada
    print(f"{'ENTRADA':<15} {'Média':>7} {'Vantagem':>9} {'Acerto':>7} {'p':>7}")
    melhores = sorted(entrada.items(), key=lambda x: x[1].get("vantagem_pct", 0), reverse=True)
    for geo, e in melhores:
        marcador = " <" if e["vantagem_pct"] >= max(v["vantagem_pct"] for v in entrada.values()) else ""
        print(f"  {geo:<13} {e['media_pts']:>+6.0f}pts {e['vantagem_pct']:>+7.1f}% {e['wr_pct']:>6.1f}% {e['p_valor']:>7.4f}{marcador}")
    print(f"  N={g['N']}  1a metade {g['metade1']:+.0f}  2a {g['metade2']:+.0f}  {'ok' if g['metades_ok'] else 'DIVERGE'}  DD {g['dd_max']:.0f}  PF {g['pf']:.2f}")
    print()

    # Tempo pós-entrada
    if tempo:
        print(f"{'TEMPO PÓS-ENTRADA':<12} {'Média':>7} {'Vantagem':>9} {'Acerto':>7} {'N':>5}")
        pico = max(tempo.values(), key=lambda x: x["vantagem_pct"])
        pico_i = [i for i, t in tempo.items() if t is pico][0]
        for i, t in sorted(tempo.items()):
            marcador = " <" if i == pico_i else ""
            print(f"  +{i}min{'':<7} {t['media_pts']:>+6.0f}pts {t['vantagem_pct']:>+7.1f}% {t['wr_pct']:>6.1f}% {t['N']:>5}{marcador}")
        print()

    # Container
    print(f"{'CONTÊINER (TP × convenção)':<12}")
    print(f"  {'TP':<6} {'pior (SL->TP)':<22} {'melhor (TP->SL)':<22}")
    for nome_tp, _ in TP_NIVEIS:
        w = cont.get(f"{nome_tp}_worst", {})
        b = cont.get(f"{nome_tp}_best", {})
        print(f"  {nome_tp:<6} {w.get('media_pts', 0):>+5.0f} {w.get('wr_pct', 0):>4.0f}%  p={w.get('p_valor',1):.4f}      "
              f"{b.get('media_pts', 0):>+5.0f} {b.get('wr_pct', 0):>4.0f}%  p={b.get('p_valor',1):.4f}")
    print()

    # Custo real (slippage)
    if custo:
        slip_label = f"slippage slip={slippage.slip_pts} spread={slippage.spread_pts}"
        custo_status = "PASSOU" if custo.p_valor < 0.05 and custo.metades_ok else "MORTA"
        metades_ok = "ok" if custo.metades_ok else "DIVERGE"
        print(f"CUSTO REAL ({slip_label})")
        print(f"  Média {custo.media:+.0f}pts  WR={custo.win_rate:.0f}%  p={custo.p_valor:.4f}")
        print(f"  N={custo.total}  1a metade {custo.metade1_media:+.0f}  2a {custo.metade2_media:+.0f}  {metades_ok}")
        print(f"  Veredito: {custo_status}")
        print()
    elif slippage is None:
        print(f"CUSTO REAL: calibração de slippage indisponível (state/slippage_calibration.json).")
        print(f"  Execute 'python -c \"from core.calibrator import Calibrator; c=Calibrator(); c.calibrar(); c.salvar()\"' com MT5 aberto.")
        print()

    print(f"  {hid} | {veredito}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("Uso: python scripts/avaliar_hipotese.py H109 [H110 ...]")
        sys.exit(1)

    import importlib
    df = load_csv()
    rg = RiskGuardian(capital=1000, max_dd=99999, rr_ratio=1.5)
    rg.calibrate(df)

    slippage = None
    try:
        slippage = Calibrator.criar_slippage()
    except Exception:
        pass

    for hid in args:
        try:
            mod = importlib.import_module(f"strategy.{hid}_strategy")
            cls = getattr(mod, f"{hid}Strategy")
            avaliar(hid, cls, df, rg, slippage)
        except Exception as e:
            print(f"{hid}: ERRO {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
