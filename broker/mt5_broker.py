import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
from core.types import *
from core.mt5_connector import Mt5Connector
from broker.base import Broker

class Mt5Broker(Broker):
    def __init__(self, mode: ExecutionMode, symbol: str = "WINM26", volume: float = 1.0,
                 connector: Mt5Connector = None):
        if mode not in (ExecutionMode.DEMO, ExecutionMode.REAL):
            raise ValueError(f"Mt5Broker mode must be DEMO or REAL, got {mode}")
        self.mode = mode
        self.symbol = symbol
        self.volume = volume
        self.connector = connector or Mt5Connector()
        self.mt5 = self.connector.mt5
        self._connected = False
        self._connect()

    def _connect(self):
        if self.mt5 is None:
            raise ImportError("MetaTrader5 package not installed")
        if not self.connector.ensure_connected():
            raise ConnectionError(f"MT5 initialize failed: {self.mt5.last_error()}")
        if not self.connector.select_symbol(self.symbol):
            raise ValueError(f"Symbol {self.symbol} not found in MarketWatch")
        self._connected = True
        self._log_connection()

    def _log_connection(self):
        try:
            info = self.mt5.account_info()
            if info:
                print(f"[Mt5Broker] Conectado modo {self.mode.value} | Conta {info.login} | Saldo {info.balance:.2f}")
        except:
            pass

    def execute(self, signal: Signal, volume: float = 1.0) -> Order:
        if not self._connected:
            try:
                self._connect()
            except:
                return Order(id="", signal=signal, type=OrderType.MARKET,
                             status=OrderStatus.REJECTED)

        vol = volume if volume else self.volume
        order_type = self.mt5.ORDER_TYPE_BUY if signal.direction == Direction.LONG else self.mt5.ORDER_TYPE_SELL
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": vol,
            "type": order_type,
            "price": signal.entry,
            "sl": signal.stop if signal.stop else 0,
            "tp": signal.target if signal.target else 0,
            "deviation": 10,
            "magic": 1000,
            "comment": signal.strategy_id[:16],
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC
        }
        result = self.mt5.order_send(request)
        if result.retcode != self.mt5.TRADE_RETCODE_DONE:
            return Order(id=str(result.retcode), signal=signal,
                         type=OrderType.MARKET, status=OrderStatus.REJECTED,
                         filled_price=0, filled_at=datetime.now())
        return Order(id=str(result.order), signal=signal,
                     type=OrderType.MARKET, status=OrderStatus.FILLED,
                     filled_price=result.price, filled_at=datetime.now())

    def fetch_positions(self) -> list[Position]:
        if not self._connected:
            return []
        positions = self.mt5.positions_get(symbol=self.symbol)
        if positions is None:
            return []
        result = []
        for p in positions:
            result.append(Position(
                direction=Direction.LONG if p.type == self.mt5.ORDER_TYPE_BUY else Direction.SHORT,
                entry=p.price_open,
                size=round(p.volume),
                opened_at=datetime.fromtimestamp(p.time),
                strategy_id=str(p.comment),
                stop=p.sl,
                target=p.tp,
                max_exit_time=None,
                ticket=str(p.ticket)))
        return result

    def get_exit_info(self, ticket: str) -> dict | None:
        if not self._connected:
            return None
        try:
            tk = int(ticket)
            deals = self.mt5.history_deals_get(position=tk)
            if deals and len(deals) > 0:
                for d in deals:
                    if hasattr(d, 'entry') and d.entry == 1:
                        return {"exit_price": float(d.price),
                                "closed_at": datetime.fromtimestamp(d.time)}
                d = deals[-1]
                return {"exit_price": float(d.price),
                        "closed_at": datetime.fromtimestamp(d.time)}
        except Exception:
            pass
        return None

    def close(self):
        pass
