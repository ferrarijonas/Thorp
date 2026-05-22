"""Bot Thorp — loop único. Task Scheduler reinicia se morrer.
Sem watchdog, sem manager, sem JSON persist (MT5 guarda historico)."""
import sys, os, time, json, logging, argparse, traceback
import logging.handlers
from datetime import datetime, time as dtime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import MetaTrader5 as mt5
from core.types import Bar, ExecutionMode

STATE_DIR = os.path.join(os.path.dirname(__file__), "..", "state")
LOG_DIR = os.path.join(STATE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S", force=True,
    handlers=[
        logging.handlers.RotatingFileHandler(
            os.path.join(LOG_DIR, f"bot_{datetime.now():%Y%m%d}.log"),
            maxBytes=10_000_000, backupCount=3, encoding="utf-8"),
        logging.StreamHandler()])
log = logging.getLogger("bot")

class FiltroTeste(logging.Filter):
    def __init__(self, aceitar_teste):
        super().__init__()
        self._aceitar = aceitar_teste
    def filter(self, record):
        msg = record.msg if isinstance(record.msg, str) else str(record.msg)
        eh_teste = "TESTE" in msg
        return eh_teste if self._aceitar else not eh_teste

# Handler separado para TESTE (validacao.log)
validacao_handler = logging.handlers.RotatingFileHandler(
    os.path.join(STATE_DIR, "validacao.log"),
    maxBytes=10_000_000, backupCount=3, encoding="utf-8")
validacao_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
validacao_handler.addFilter(FiltroTeste(True))
logging.getLogger().addHandler(validacao_handler)

# Remove TESTE do log principal e console
for h in logging.getLogger().handlers:
    if hasattr(h, 'baseFilename') and "validacao" in str(h.baseFilename):
        continue
    h.addFilter(FiltroTeste(False))


def load_config():
    cfg_path = os.path.join(STATE_DIR, "bot_config.json")
    if not os.path.exists(cfg_path):
        log.error("Config nao encontrado: %s", cfg_path)
        sys.exit(1)
    with open(cfg_path, encoding="utf-8") as f:
        return json.load(f)


def estrategia_por_nome(nome: str):
    module = __import__(f"strategy.{nome}_strategy", fromlist=[f"{nome}Strategy"])
    return getattr(module, f"{nome}Strategy")


# --- Data freshness (evita operar com feed congelado) ---
DATA_STALE_WARN = 300       # 5 min  — loga ALERTA
DATA_STALE_CRITICAL = 900   # 15 min — recusa processar barra
DATA_FRESH_OK = 120         # 2 min  — considerado ao vivo

def _tick_freshness(symbol: str):
    """Retorna (idade_segundos, tick_datetime). None em erro."""
    try:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None or tick.time_msc == 0:
            return 99999, None
        tick_dt = datetime.fromtimestamp(tick.time_msc / 1000)
        age = (datetime.now() - tick_dt).total_seconds()
        return age, tick_dt
    except Exception:
        return 99999, None


def _dentro_do_pregao(agora):
    """Seg a Sex, 9:00-18:00 (horario local)."""
    return agora.weekday() < 5 and dtime(9, 0) <= agora.time() <= dtime(18, 0)


def _pre_aquecer_cache(symbol: str):
    """Forca download de dados M1 do servidor para popular cache do terminal.
    copy_rates_from bate no history server (bypass cache local)."""
    from datetime import timedelta
    rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1,
                                datetime.now() - timedelta(hours=24), 1000)
    if rates is not None and len(rates) > 0:
        last = datetime.fromtimestamp(int(rates[-1]["time"]))
        log.info("Cache M1 pre-aquecido | %s barras | ultima=%s", len(rates), last)
        return True
    log.warning("Pre-aquecimento falhou | erro=%s", mt5.last_error())
    return False


def _reconectar_mt5(exe: str | None, symbol: str):
    """shutdown + reinitialize. Retorna True se reconectou com sucesso."""
    log.warning("Tentando reconectar MT5...")
    try:
        mt5.shutdown()
    except Exception:
        pass
    time.sleep(2)
    for attempt in range(1, 6):
        try:
            ok = mt5.initialize(path=exe) if exe else mt5.initialize()
            if ok:
                ti = mt5.terminal_info()
                ai = mt5.account_info()
                if ti is not None and ai is not None:
                    log.info("Reconectado | server=%s login=%s", ai.server, ai.login)
                    mt5.symbol_select(symbol, True)
                    _pre_aquecer_cache(symbol)
                    return True
            raise RuntimeError("initialize=False or info=None")
        except Exception as e:
            log.warning("Reconexao tentativa %s/5: %s", attempt, e)
            time.sleep(min(attempt * 2, 8))
    log.critical("Falha na reconexao apos 5 tentativas")
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--terminal", required=True)
    args = parser.parse_args()
    term_id = args.terminal

    config = load_config()
    term_cfg = next((t for t in config["terminais"] if t["id"] == term_id), None)
    if not term_cfg:
        log.error("Terminal '%s' nao encontrado no config", term_id)
        sys.exit(1)

    # Lock single instance
    lock_file = os.path.join(STATE_DIR, f"bot_{term_id}.lock")
    if os.path.exists(lock_file):
        try:
            with open(lock_file) as f:
                old_pid = json.load(f).get("pid", 0)
            if old_pid:
                import ctypes
                h = ctypes.windll.kernel32.OpenProcess(0x400000, False, old_pid)
                if h:
                    ctypes.windll.kernel32.CloseHandle(h)
                    log.error("Bot ja rodando (PID %s). Saindo.", old_pid)
                    sys.exit(0)
        except Exception:
            pass
        log.warning("Lock stale. Removendo...")
    with open(lock_file, "w") as f:
        json.dump({"pid": os.getpid(), "started": str(datetime.now())}, f)

    symbol = term_cfg["symbol"]
    mode = ExecutionMode[term_cfg["mode"].upper()]
    strategies_raw = term_cfg.get("strategies", [])
    if strategies_raw and isinstance(strategies_raw[0], str):
        strategies_raw = [{"name": s} for s in strategies_raw]

    trade_start = dtime(0, 0)
    trade_end = dtime(23, 59)
    intervalo = term_cfg.get("interval", 30)

    # --- Conecta MT5 (retry rapido, max ~65s) ---
    log.info("Conectando MT5 (%s)...", symbol)
    exe = term_cfg.get("exe")
    for attempt in range(1, 13):
        try:
            ok = mt5.initialize(path=exe) if exe else mt5.initialize()
            if ok:
                ti = mt5.terminal_info()
                ai = mt5.account_info()
                if ti is not None and ai is not None:
                    log.info("MT5 conectado | server=%s build=%s login=%s saldo=%.0f",
                             ai.server, ti.build, ai.login, ai.balance)
                    mt5.symbol_select(symbol, True)
                    _pre_aquecer_cache(symbol)
                    break
            raise RuntimeError(f"initialize={ok} terminal_info={ti} account_info={ai}")
        except Exception as e:
            log.warning("MT5 tentativa %s/12: %s", attempt, e)
            if attempt < 12:
                time.sleep(min(attempt * 2, 10))
    else:
        log.critical("MT5 nao conectou apos 12 tentativas")
        sys.exit(1)

    # --- Verifica dados ao vivo no startup ---
    agora = datetime.now()
    if _dentro_do_pregao(agora):
        log.info("Pregao detectado. Verificando dados ao vivo...")
        # Verifica 3x, se congelado tenta reconectar (ate 2x)
        for recon_try in range(3):
            age, tick_dt = _tick_freshness(symbol)
            if age < DATA_FRESH_OK:
                log.info("Dados OK | tick=%s idade=%.0fs", tick_dt, age)
                break
            log.error("Dados STALE | tick=%s idade=%.0fs | tentativa %s/3",
                     tick_dt, int(age), recon_try + 1)
            if recon_try < 2:
                if not _reconectar_mt5(exe, symbol):
                    log.critical("Reconexao falhou. ABORTANDO.")
                    sys.exit(1)
            else:
                log.critical("Dados CONGELADOS apos 3 tentativas. ABORTANDO.")
                sys.exit(1)
    else:
        age, tick_dt = _tick_freshness(symbol)
        log.info("Fora do pregao | tick=%s idade=%.0fs | iniciando mesmo assim", tick_dt, int(age))

    # --- Carrega RiskGuardian (calibracao do CSV cacheada) ---
    from core.risk_guardian import RiskGuardian
    from core.data import load_csv
    rg_cache = os.path.join(STATE_DIR, "risk_calibration.json")
    risk_guardians = {}
    for s in strategies_raw:
        nome = s["name"]
        cls = estrategia_por_nome(nome)
        ts = dtime(*(int(x) for x in s.get("trade_start", "09:00").split(":")))
        te = dtime(*(int(x) for x in s.get("trade_end", "18:00").split(":")))
        rg = RiskGuardian(capital=s.get("capital", 1_000_000),
                         max_dd=s.get("max_dd", 999_999_999),
                         min_stop_pts=250,
                         trade_start=ts, trade_end=te)
        if os.path.exists(rg_cache):
            with open(rg_cache) as f:
                cal = json.load(f)
            rg._p50_por_hora = {int(k): v for k, v in cal.get("p50_hora", {}).items()}
            rg._p75_por_hora = {int(k): v for k, v in cal.get("p75_hora", {}).items()}
            rg._p50_por_minuto = {int(k): v for k, v in cal.get("p50_minuto", {}).items()}
            rg._p75_por_minuto = {int(k): v for k, v in cal.get("p75_minuto", {}).items()}
        else:
            log.info("Calibrando RiskGuardian do CSV...")
            rg.calibrate(load_csv())
            with open(rg_cache, "w") as f:
                json.dump({
                    "p50_hora": rg._p50_por_hora, "p75_hora": rg._p75_por_hora,
                    "p50_minuto": rg._p50_por_minuto, "p75_minuto": rg._p75_por_minuto,
                }, f, indent=2)
        if getattr(cls, "USAR_CONTAINER_MINUTO", False):
            rg.usar_container_minuto()
        risk_guardians[nome] = rg

    # --- Instancia engines ---
    from execution.engine import ExecutionEngine
    from feed.mt5_feed import Mt5Feed
    from broker.mt5_broker import Mt5Broker

    engines = []
    for s in strategies_raw:
        nome = s["name"]
        cls = estrategia_por_nome(nome)
        vol = s.get("volume", 1.0)
        feed = Mt5Feed(symbol=symbol, mode="live")
        broker = Mt5Broker(mode=mode, symbol=symbol, volume=vol)
        engine = ExecutionEngine(feed, cls(), broker, mode=mode,
            risk_guardian=risk_guardians[nome], volume=vol)
        engines.append(engine)
        log.info("  %s | capital=%.0f volume=%.1f", nome,
                 s.get("capital", 1_000_000), vol)

    # --- Loop principal ---
    log.info("Loop | intervalo=%ss | janela=%s-%s", intervalo, trade_start, trade_end)
    _last_bar_ts = 0
    _last_pos_save = 0
    _last_fresh_check = 0
    _stale_count = 0

    while True:
        agora = datetime.now()
        if agora.weekday() >= 5:
            time.sleep(300); continue
        if agora.time() < trade_start or agora.time() > trade_end:
            time.sleep(60); continue

        try:
            # --- Pre-pregao (8:50-8:59): check agressivo a cada iteracao ---
            pre_pregao = (agora.weekday() < 5 and dtime(8, 50) <= agora.time() <= dtime(8, 59))

            # --- Health check: dados estao vivos? (a cada 60s, ou toda iteracao pre-pregao) ---
            if pre_pregao or time.time() - _last_fresh_check > 60:
                _last_fresh_check = time.time()
                age, tick_dt = _tick_freshness(symbol)
                if _dentro_do_pregao(agora) or pre_pregao:
                    if age > DATA_STALE_CRITICAL:
                        _stale_count += 1
                        if _stale_count == 1:
                            log.error("DADOS CONGELADOS | tick=%s idade=%.0fs | tentando reconectar...",
                                     tick_dt, int(age))
                            _reconectar_mt5(exe, symbol)
                    elif age > DATA_STALE_WARN:
                        log.warning("Dados atrasados | tick=%s idade=%.0fs", tick_dt, int(age))
                        _stale_count = max(0, _stale_count - 1)
                    else:
                        if _stale_count > 0:
                            log.info("Dados recuperados | tick=%s idade=%.0fs", tick_dt, int(age))
                        _stale_count = 0

            # Se dados estao criticamente stale, pula processamento
            if (_dentro_do_pregao(agora) or pre_pregao) and _stale_count >= 3:
                time.sleep(intervalo)
                continue

            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 1)
            if rates is None or len(rates) == 0:
                time.sleep(intervalo); continue

            r = rates[0]; ts = int(r["time"])
            if ts == _last_bar_ts:
                time.sleep(intervalo); continue
            _last_bar_ts = ts

            bar = Bar(time=datetime.fromtimestamp(ts),
                      open=float(r["open"]), high=float(r["high"]),
                      low=float(r["low"]), close=float(r["close"]),
                      volume=int(r["tick_volume"]))

            for engine in engines:
                try:
                    engine.on_bar(bar)
                except Exception as e:
                    log.error("Engine %s: %s",
                              getattr(engine.strategy, "_name", "?"), traceback.format_exc())

            # Reconcile (posicoes fechadas externamente)
            try:
                pos_list = mt5.positions_get(symbol=symbol) or []
                abertos = {str(p.ticket) for p in pos_list}
                for eng in engines:
                    if eng._position and eng._position.ticket:
                        if eng._position.ticket not in abertos:
                            log.info("Reconcile: %s ticket %s fechado externamente",
                                     getattr(eng.strategy, "_name", "?"), eng._position.ticket)
                            eng._position = None
            except Exception:
                pass

            # Positions.json snapshot
            if time.time() - _last_pos_save > 30:
                snapshot = [{"ticket": p.ticket, "type": "BUY" if p.type == 0 else "SELL",
                             "volume": p.volume, "entry": p.price_open, "sl": p.sl, "tp": p.tp,
                             "profit": p.profit, "comment": p.comment} for p in (mt5.positions_get(symbol=symbol) or [])]
                with open(os.path.join(STATE_DIR, "positions.json"), "w") as f:
                    json.dump(snapshot, f, indent=2)
                _last_pos_save = time.time()

        except Exception as e:
            log.error("Loop: %s", traceback.format_exc())

        time.sleep(intervalo)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.critical("Bot morreu: %s", traceback.format_exc())
        sys.exit(1)
