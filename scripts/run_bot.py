"""Bot generico 24/7 — le config, instancia N estrategias, roda com watchdog interno.
Uso: python scripts/run_bot.py --terminal xp
     python scripts/run_bot.py --terminal exness

Lê state/bot_config.json para configuracao.
"""
import sys, os, json, time, logging, traceback
import logging.handlers
from datetime import datetime, time as dtime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.types import ExecutionMode
from core.mt5_connector import Mt5Connector
from core.calibrator import Calibrator
from feed.mt5_feed import Mt5Feed
from broker.mt5_broker import Mt5Broker
from execution.manager import StrategyManager

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "state", "logs")

def setup_logging(terminal_id: str):
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"bot_{terminal_id}_{datetime.now():%Y%m%d}.log")
    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10_000_000, backupCount=5, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(
        "%(asctime)s | %(message)s", datefmt="%H:%M:%S"))
    root.addHandler(console)


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "..", "state", "bot_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def estrategia_por_nome(nome: str):
    module = __import__(f"strategy.{nome}_strategy", fromlist=[f"{nome}Strategy"])
    cls = getattr(module, f"{nome}Strategy")
    return cls


def parse_time(t: str) -> dtime:
    parts = t.split(":")
    return dtime(int(parts[0]), int(parts[1]))


def should_sleep(cfg: dict) -> int:
    """Retorna segundos de sleep se estiver fora do horario.
    Retorna 0 se deve operar normalmente.
    """
    agora = datetime.now()
    if agora.weekday() >= 5:
        return 300  # fim de semana, 5 min
    trade_start = parse_time(cfg.get("trade_start", "09:00"))
    trade_end = parse_time(cfg.get("trade_end", "17:00"))
    hora = agora.time()
    if hora < trade_start or hora > trade_end:
        return 300  # fora do horario, 5 min
    return 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Thorp Bot 24/7")
    parser.add_argument("--terminal", required=True, help="ID do terminal em bot_config.json")
    args = parser.parse_args()

    config = load_config()
    terminais = [t for t in config["terminais"] if t["id"] == args.terminal]
    if not terminais:
        print(f"Terminal '{args.terminal}' nao encontrado no config")
        sys.exit(1)

    cfg = terminais[0]
    setup_logging(cfg["id"])

    log = logging.getLogger("bot")
    log.info(f"Thorp Bot iniciando | terminal={cfg['id']} | symbol={cfg['symbol']}")
    log.info(f"Estrategias: {cfg['strategies']}")

    state_dir = os.path.join(os.path.dirname(__file__), "..", "state")
    trade_store_path = os.path.join(state_dir, f"trades_{cfg['id']}.json")
    capital_store_path = os.path.join(state_dir, f"capital_{cfg['id']}.json")

    max_reconnect = cfg.get("max_reconnect", 5)
    reconectou = 0

    while reconectou < max_reconnect:
        try:
            # Iniciar terminal minimizado se nao estiver rodando
            exe_path = cfg.get("exe")
            if exe_path and not os.path.exists(exe_path.replace("terminal64.exe", "") + "\\lock"):
                import subprocess
                try:
                    subprocess.Popen([exe_path, "/minimized"], shell=True)
                    time.sleep(10)
                except:
                    pass
            connector = Mt5Connector(terminal_path=exe_path)
            connector.ensure_connected()

            feed = Mt5Feed(symbol=cfg["symbol"], mode="live", connector=connector)
            broker = Mt5Broker(
                mode=ExecutionMode[cfg["mode"].upper()],
                symbol=cfg["symbol"],
                volume=cfg.get("volume", 1.0),
                connector=connector,
            )

            rg = Calibrator.criar_risk_guardian(
                capital=cfg.get("capital", 1000000),
                max_dd=cfg.get("max_dd", 1000000000),
            )
            slip = Calibrator.criar_slippage()

            mgr = StrategyManager(
                feed, broker,
                mode=ExecutionMode[cfg["mode"].upper()],
                capital=cfg.get("capital", 1000000),
            )

            for nome in cfg["strategies"]:
                cls = estrategia_por_nome(nome)
                mgr.add(
                    cls,
                    risk_guardian=rg,
                    slippage=slip,
                    trade_store_path=trade_store_path,
                    capital_store_path=capital_store_path,
                )
                log.info(f"  Engine {nome} adicionada")

            log.info(f"Loop iniciado | intervalo={cfg.get('interval', 30)}s")
            intervalo = cfg.get("interval", 30)

            try:
                while True:
                    # Pausa inteligente fora do horario / fim de semana
                    s = should_sleep(cfg)
                    if s > 0:
                        time.sleep(s)
                        continue

                    try:
                        bar = feed.poll()
                    except Exception as e:
                        log.error(f"Feed poll error: {e}")
                        time.sleep(intervalo)
                        continue

                    if bar:
                        for engine in mgr.engines:
                            try:
                                engine.on_bar(bar)
                            except Exception as e:
                                log.error(f"Engine {getattr(engine, '_hid', '?')}: {e}")
                        mgr._save_state()
                    time.sleep(intervalo)

            except KeyboardInterrupt:
                log.info("Parando (Ctrl+C)...")
            finally:
                mgr.close()

        except ImportError as e:
            log.error(f"Pacote faltando: {e}")
            break
        except (ConnectionError, ValueError) as e:
            reconectou += 1
            log.warning(f"Conexao falhou ({reconectou}/{max_reconnect}): {e}")
            time.sleep(5)
            continue
        except Exception as e:
            reconectou += 1
            log.error(f"Erro inesperado ({reconectou}/{max_reconnect}): {e}")
            traceback.print_exc()
            if reconectou < max_reconnect:
                log.info("Reiniciando em 10s...")
                time.sleep(10)
            continue

    if reconectou >= max_reconnect:
        log.critical(f"Falhou apos {max_reconnect} tentativas. Encerrando.")


if __name__ == "__main__":
    main()
