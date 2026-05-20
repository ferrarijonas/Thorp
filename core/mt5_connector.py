"""Dono unico da conexao MT5. Feed, Broker e Guardian recebem por injecao."""
import sys, os, atexit
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None


class Mt5Connector:
    """Gerencia o ciclo de vida da conexao com o terminal MetaTrader 5.

    Uso unico por processo Python. Feed e Broker recebem esta instancia
    em vez de chamar mt5.initialize() diretamente.
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
                pass
        return self._connect()

    def _connect(self) -> bool:
        mt5.shutdown()
        if self._terminal_path:
            ok = mt5.initialize(path=self._terminal_path)
        else:
            ok = mt5.initialize()
        if ok:
            self._connected = True
        else:
            self._connected = False
        return self._connected

    def select_symbol(self, symbol: str) -> bool:
        if not self.ensure_connected():
            return False
        return mt5.symbol_select(symbol, True)

    def is_connected(self) -> bool:
        return self._connected

    def close(self):
        if mt5 is not None:
            try:
                mt5.shutdown()
            except Exception:
                pass
        self._connected = False

    @property
    def mt5(self):
        return mt5
