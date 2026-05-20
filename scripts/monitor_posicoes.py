"""Monitor simples de posicoes abertas em tempo real."""
import sys, os, time, json, logging
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.mt5_connector import Mt5Connector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%H:%M:%S")
log = logging.getLogger("monitor")

TERMINAIS = {
    "xp": r"C:\Program Files\MetaTrader_1\terminal64.exe",
    "exness": r"C:\Program Files\MetaTrader 3\terminal64.exe",
}


def monitorar(terminal_id: str, interval: int = 10):
    cfg = TERMINAIS[terminal_id]
    connector = Mt5Connector(terminal_path=cfg)
    connector.ensure_connected()

    log.info(f"Monitor {terminal_id} iniciado | intervalo={interval}s")
    ultimo_estado = {}

    try:
        while True:
            mt5 = connector.mt5
            posicoes = mt5.positions_get()
            agora = datetime.now().strftime("%H:%M:%S")

            if posicoes and len(posicoes) > 0:
                for p in posicoes:
                    estado = f"{p.symbol} vol={p.volume} entry={p.price_open} profit={p.profit:.2f}"
                    tick = p.ticket
                    if ultimo_estado.get(tick) != estado:
                        log.info(f"[{terminal_id}] ABERTO: ticket={tick} | {estado}")
                        ultimo_estado[tick] = estado
            else:
                if ultimo_estado:
                    for ticket in list(ultimo_estado.keys()):
                        log.info(f"[{terminal_id}] FECHADO: ticket={ticket}")
                    ultimo_estado.clear()

            time.sleep(interval)

    except KeyboardInterrupt:
        log.info("Monitor parado")
    finally:
        connector.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--terminal", required=True, choices=["xp", "exness"])
    parser.add_argument("--interval", type=int, default=10)
    args = parser.parse_args()
    monitorar(args.terminal, args.interval)
