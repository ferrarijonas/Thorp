import sys, os, time, logging, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import *

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("engine")

class ExecutionEngine:
    def __init__(self, feed, strategy, broker, mode: ExecutionMode,
                 cost: float = 10, risk_guardian=None, slippage=None,
                 convention: str = "worst",
                 trade_store_path: str = None,
                 capital_store_path: str = None,
                 volume: float = 1.0):
        self.feed = feed
        self.strategy = strategy
        self.broker = broker
        self.mode = mode
        self.cost = cost
        self.risk_guardian = risk_guardian
        self.slippage = slippage
        self.convention = convention
        self._volume = volume
        self._position: Position | None = None
        self._trades: list[Trade] = []
        self._step_count = 0
        self._rastro_temp: list = []
        self._prev_bar: Bar | None = None

        self._trade_store = None
        self._capital_store = None
        if trade_store_path:
            from core.trade_store import TradeStore, CapitalStore
            self._trade_store = TradeStore(trade_store_path)
            self._capital_store = CapitalStore(capital_store_path or
                trade_store_path.replace("trades", "capital"))
            self._restore_state()

    def step(self) -> Bar | None:
        bar = self.feed.poll()
        if bar is None:
            return None
        return self.on_bar(bar)

    def _check_exit(self, bar: Bar) -> float | None:
        """Verifica SL/TP/horário no bar atual.
           convention='worst': SL testado primeiro (conservador).
           convention='best': TP testado primeiro (otimista).
           Retorna exit_price ou None."""
        if not self._position:
            return None
        mode_str = self.mode.value if hasattr(self.mode, 'value') else str(self.mode)
        p = self._position
        if p.max_exit_time and bar.time >= p.max_exit_time:
            return bar.close
        if p.direction == Direction.LONG:
            if self.convention == "worst":
                if bar.low <= p.stop:
                    price = p.stop
                    return self.slippage.on_stop(price, p.direction, mode_str) if self.slippage else price
                if bar.high >= p.target:
                    price = p.target
                    return self.slippage.on_target(price, p.direction, mode_str) if self.slippage else price
            else:
                if bar.high >= p.target:
                    price = p.target
                    return self.slippage.on_target(price, p.direction, mode_str) if self.slippage else price
                if bar.low <= p.stop:
                    price = p.stop
                    return self.slippage.on_stop(price, p.direction, mode_str) if self.slippage else price
        else:
            if self.convention == "worst":
                if bar.high >= p.stop:
                    price = p.stop
                    return self.slippage.on_stop(price, p.direction, mode_str) if self.slippage else price
                if bar.low <= p.target:
                    price = p.target
                    return self.slippage.on_target(price, p.direction, mode_str) if self.slippage else price
            else:
                if bar.low <= p.target:
                    price = p.target
                    return self.slippage.on_target(price, p.direction, mode_str) if self.slippage else price
                if bar.high >= p.stop:
                    price = p.stop
                    return self.slippage.on_stop(price, p.direction, mode_str) if self.slippage else price
        return None

    def _fechar_posicao(self, exit_price: float, bar: Bar):
        pnl = (exit_price - self._position.entry) * self._position.direction.value - self.cost
        bars_held = self._step_count - self._position._open_step
        t = Trade(
            strategy_id=self._position.strategy_id,
            direction=self._position.direction,
            entry=self._position.entry,
            exit=exit_price,
            pnl_points=round(pnl, 1),
            opened_at=self._position.opened_at,
            closed_at=bar.time,
            bars_held=bars_held,
            rastro=self._rastro_temp.copy() if self._rastro_temp else None)
        self._trades.append(t)
        log.info(f"{self._position.strategy_id} FECHOU dir={'LONG' if self._position.direction==Direction.LONG else 'SHORT'} entry={self._position.entry:.0f} exit={exit_price:.0f} pnl={pnl:+.0f}")
        if self.risk_guardian:
            self.risk_guardian.post_process(pnl)
        self._persist_trade(t)
        self._position = None

    def on_bar(self, bar: Bar) -> Bar:
        self._step_count += 1
        self._reconcile()

        # Gravar rastro da posição existente (barras entre entrada e saída)
        if self._position:
            self._rastro_temp.append((bar.open, bar.high, bar.low, bar.close, bar.time))

        # 1. Verificar saída da posição existente (barra anterior ou atual)
        if self._position:
            exit_price = self._check_exit(bar)
            if exit_price is not None:
                self._fechar_posicao(exit_price, bar)

        if not self._position:
            try:
                signal = self.strategy.on_bar(bar)
            except Exception as e:
                log.warning(f"Strategy error: {e}")
                signal = None

            if signal:
                if signal.entry == 0:
                    signal.entry = bar.close
                if self.risk_guardian:
                    signal, motivo = self.risk_guardian.process(
                        signal, bar=bar,
                        mode=self.mode.value if hasattr(self.mode, 'value') else str(self.mode),
                        open_positions=1 if self._position else 0)
                    if signal is None:
                        log.warning(f"BLOQUEADO: {motivo}")
                        return bar
                if self.slippage:
                    signal = self.slippage.on_entry(signal, mode=self.mode.value if hasattr(self.mode, 'value') else str(self.mode))
                order = self.broker.execute(signal, volume=self._volume)
                if order and order.status != OrderStatus.FILLED:
                    log.warning(f"{signal.strategy_id} ORDEM REJEITADA: id={order.id}")
                if order and order.status == OrderStatus.FILLED:
                    self._position = Position(
                        direction=signal.direction,
                        entry=order.filled_price,
                        size=signal.size,
                        opened_at=bar.time,
                        strategy_id=signal.strategy_id,
                        stop=signal.stop,
                        target=signal.target,
                        max_exit_time=signal.max_exit_time,
                        _open_step=self._step_count)
                    if self._prev_bar:
                        self._rastro_temp = [
                            (self._prev_bar.open, self._prev_bar.high, self._prev_bar.low, self._prev_bar.close, self._prev_bar.time),
                            (bar.open, bar.high, bar.low, bar.close, bar.time)]
                    else:
                        self._rastro_temp = [(bar.open, bar.high, bar.low, bar.close, bar.time)]
                    if self.mode != ExecutionMode.BT and hasattr(self.broker, 'fetch_positions'):
                        try:
                            ps = self.broker.fetch_positions()
                            for p in ps:
                                if p.strategy_id == signal.strategy_id:
                                    self._position.ticket = p.ticket
                                    break
                        except:
                            pass
                    log.info(f"{signal.strategy_id} ABRIU dir={'LONG' if signal.direction==Direction.LONG else 'SHORT'} entry={order.filled_price:.0f} stop={signal.stop:.0f} target={signal.target:.0f}")

                    # 2. Verificar saída na MESMA barra de entrada (worst-case)
                    exit_price = self._check_exit(bar)
                    if exit_price is not None:
                        self._fechar_posicao(exit_price, bar)

        self._prev_bar = bar
        return bar

    def run(self, max_bars: int | None = None) -> ExecutionResult:
        while True:
            bar = self.step()
            if bar is None:
                break
            if max_bars and self._step_count >= max_bars:
                break
        if self._position:
            self._trades.append(Trade(
                strategy_id=self._position.strategy_id,
                direction=self._position.direction,
                entry=self._position.entry,
                exit=self._position.entry,
                pnl_points=0,
                opened_at=self._position.opened_at,
                closed_at=self._position.opened_at,
                bars_held=0,
                rastro=self._rastro_temp.copy() if self._rastro_temp else None))
            self._position = None
        return self._calc_stats()

    def _calc_stats(self) -> ExecutionResult:
        from core.analisador import Analisador
        return Analisador.resultado(self._trades)

    def _restore_state(self):
        if self._capital_store:
            cap = self._capital_store.load()
            if cap and self.risk_guardian:
                self.risk_guardian.capital = cap.get("capital", self.risk_guardian.capital)
                self.risk_guardian._capital_inicial = cap.get("initial_capital",
                    self.risk_guardian._capital_inicial)
        if self._trade_store:
            for d in self._trade_store.load():
                trade = Trade(
                    strategy_id=d["strategy_id"],
                    direction=Direction[d["direction"]],
                    entry=d["entry"],
                    exit=d["exit"],
                    pnl_points=d["pnl_points"],
                    opened_at=datetime.fromisoformat(d["opened_at"]),
                    closed_at=datetime.fromisoformat(d["closed_at"]),
                    bars_held=d.get("bars_held", 0))
                self._trades.append(trade)
                if self.risk_guardian:
                    self.risk_guardian.post_process(trade.pnl_points)

    def _persist_trade(self, trade: Trade):
        if self._trade_store:
            self._trade_store.append(trade)
        if self._capital_store and self.risk_guardian:
            self._capital_store.save(
                self.risk_guardian.capital,
                max(0, self.risk_guardian._capital_inicial - self.risk_guardian.capital),
                self.risk_guardian._capital_inicial)

    def _reconcile(self):
        """Sincroniza self._position com as posicoes reais do broker (Demo/Real)."""
        if self.mode == ExecutionMode.BT or self._position is None:
            return
        if not self._position.strategy_id:
            return
        try:
            abertas = self.broker.fetch_positions()
            tem = any(p.strategy_id == self._position.strategy_id for p in abertas)
            if tem:
                return
            log.info(f"Reconcile: {self._position.strategy_id} nao esta mais no MT5 — fechado pelo broker")
            exit_price = self._position.entry
            closed_at = datetime.now()
            try:
                info = self.broker.get_exit_info(self._position.ticket)
                if info:
                    exit_price = info["exit_price"]
                    closed_at = info["closed_at"]
            except Exception:
                pass
            pnl = (exit_price - self._position.entry) * self._position.direction.value - self.cost
            self._trades.append(Trade(
                strategy_id=self._position.strategy_id,
                direction=self._position.direction,
                entry=self._position.entry,
                exit=exit_price,
                pnl_points=round(pnl, 1),
                opened_at=self._position.opened_at,
                closed_at=closed_at,
                bars_held=0))
            log.info(f"{self._position.strategy_id} FECHOU via MT5 entry={self._position.entry:.0f} exit={exit_price:.0f} pnl={pnl:+.0f}")
            if self.risk_guardian:
                self.risk_guardian.post_process(pnl)
            self._persist_trade(self._trades[-1])
            self._position = None
        except Exception as e:
            log.warning(f"Reconcile error: {e}")

    def close(self):
        if hasattr(self.feed, "close"):
            self.feed.close()
        from core.mt5_connector import Mt5Connector
        Mt5Connector().close()
