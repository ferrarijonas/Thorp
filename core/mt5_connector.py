"""Dono unico da conexao MT5. Feed, Broker e Guardian recebem por injecao."""
import sys, os, time, atexit, logging

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

_log = logging.getLogger("mt5_connector")


class Mt5Connector:
    """Gerencia o ciclo de vida da conexao com o terminal MetaTrader 5.

    Uso unico por processo Python. Feed e Broker recebem esta instancia
    em vez de chamar mt5.initialize() diretamente.

    Resiliencia: retry interno no _connect() se MT5 ainda estiver
    carregando (erro de codec ou initialize=False). Nao da shutdown
    cego — so fecha se ja conectado, evitando conflitos.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, terminal_path: str = None):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self._terminal_path = terminal_path
        self._connected = False
        atexit.register(self.close)

    def ensure_connected(self) -> bool:
        if mt5 is None:
            raise ImportError("MetaTrader5 package not installed")
        if self._connected:
            try:
                info = mt5.account_info()
                if info is not None:
                    return True
            except Exception:
                self._connected = False
        return self._connect()

    def _connect(self) -> bool:
        """Conecta ao terminal MT5 com retry interno.
        
        Nao chama shutdown() antes de initialize() para evitar conflitos
        com outros processos (watchdog check_mt5) e para nao resetar
        conexoes parciais durante loading do terminal.

        Retry: 8 tentativas com backoff 3→24s (total ~108s).
        """
        MAX_RETRIES = 8
        BASE_WAIT = 3
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if self._terminal_path:
                    ok = mt5.initialize(path=self._terminal_path)
                else:
                    ok = mt5.initialize()

                if ok:
                    info = mt5.terminal_info()
                    if info is not None:
                        acc = mt5.account_info()
                        if acc is not None:
                            self._connected = True
                            _log.info(
                                "MT5 conectado | server=%s build=%s login=%s",
                                acc.server, info.build, acc.login)
                            return True
                        else:
                            _log.warning("MT5 conectado mas account_info=None — nao logado?")
                    else:
                        _log.warning("MT5 initialize=True mas terminal_info=None — carregando...")
                else:
                    _log.warning("mt5.initialize() retornou False — terminal carregando?")

            except Exception as e:
                last_error = str(e)
                _log.warning(
                    "MT5 _connect tentativa %s/%s falhou: %s",
                    attempt, MAX_RETRIES, last_error)

                # Se foi erro de codec (utf-16 sem BOM), o terminal ainda
                # esta iniciando o IPC. Nao damos shutdown — deixamos o
                # terminal terminar de carregar.
                if "codec" in last_error.lower() or "bom" in last_error.lower():
                    _log.info("Erro de codec — terminal ainda carregando IPC. Aguardando...")

            if attempt < MAX_RETRIES:
                wait = min(BASE_WAIT * (2 ** (attempt - 1)), 30)
                _log.debug("Aguardando %ss antes da proxima tentativa...", wait)
                time.sleep(wait)

        self._connected = False
        _log.error("MT5 _connect falhou apos %s tentativas. Ultimo erro: %s",
                    MAX_RETRIES, last_error)
        return False

    def select_symbol(self, symbol: str) -> bool:
        if not self.ensure_connected():
            return False
        return mt5.symbol_select(symbol, True)

    def is_connected(self) -> bool:
        return self._connected

    def close(self):
        if mt5 is not None and self._connected:
            try:
                mt5.shutdown()
            except Exception:
                pass
        self._connected = False

    @property
    def mt5(self):
        return mt5
