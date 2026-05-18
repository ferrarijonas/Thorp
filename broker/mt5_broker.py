import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
from core.types import *

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

class Mt5Broker:
    def __init__(self, mode: ExecutionMode, symbol: str = "WINM26", volume: float = 1.0):
        if mode not in (ExecutionMode.DEMO, ExecutionMode.REAL):
            raise ValueError(f"Mt5Broker mode must be DEMO or REAL, got {mode}")
        self.mode = mode
        self.symbol = symbol
        self.volume = volume
        self._connected = False
        self._connect()

    def _connect(self):
        if mt5 is None:
            raise ImportError("MetaTrader5 package not installed")
        if not mt5.initialize():
            raise ConnectionError(f"MT5 initialize failed: {mt5.last_error()}")
        if not mt5.symbol_select(self.symbol, True):
            raise ValueError(f"Symbol {self.symbol} not found in MarketWatch")
        self._connected = True
        self._log_connection()

    def _log_connection(self):
        try:
            info = mt5.account_info()
            if info:
                print(f"[Mt5Broker] Conectado modo {self.mode.value} | Conta {info.login} | Saldo {info.balance:.2f}")
        except:
            pass

    def execute(self, signal: Signal) -> Order:
        if not self._connected:
            try:
                self._connect()
            except:
                return Order(id="", signal=signal, type=OrderType.MARKET,
                             status=OrderStatus.REJECTED)

        order_type = mt5.ORDER_TYPE_BUY if signal.direction == Direction.LONG else mt5.ORDER_TYPE_SELL
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": self.volume,
            "type": order_type,
            "price": signal.entry,
            "sl": signal.stop if signal.stop else 0,
            "tp": signal.target if signal.target else 0,
            "deviation": 10,
            "magic": 1000,
            "comment": signal.strategy_id,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return Order(id=str(result.retcode), signal=signal,
                         type=OrderType.MARKET, status=OrderStatus.REJECTED,
                         filled_price=0, filled_at=datetime.now())
        return Order(id=str(result.order), signal=signal,
                     type=OrderType.MARKET, status=OrderStatus.FILLED,
                     filled_price=result.price, filled_at=datetime.now())

    def fetch_positions(self) -> list[Position]:
        if not self._connected:
            return []
        positions = mt5.positions_get(symbol=self.symbol)
        if positions is None:
            return []
        result = []
        for p in positions:
            result.append(Position(
                direction=Direction.LONG if p.type == mt5.ORDER_TYPE_BUY else Direction.SHORT,
                entry=p.price_open,
                size=round(p.volume),
                opened_at=datetime.fromtimestamp(p.time),
                strategy_id=str(p.comment),
                stop=p.sl,
                target=p.tp,
                max_exit_time=None,
                ticket=str(p.ticket)))
        return result

    def close(self):
        pass
