import sys, os, time, logging, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import *
import numpy as np

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("engine")

class ExecutionEngine:
    def __init__(self, feed, strategy, broker, mode: ExecutionMode,
                 cost: float = 10, risk_guardian=None, slippage=None):
        self.feed = feed
        self.strategy = strategy
        self.broker = broker
        self.mode = mode
        self.cost = cost
        self.risk_guardian = risk_guardian
        self.slippage = slippage
        self._position: Position | None = None
        self._trades: list[Trade] = []
        self._step_count = 0

    def step(self) -> Bar | None:
        bar = self.feed.poll()
        if bar is None:
            return None
        return self.on_bar(bar)

    def on_bar(self, bar: Bar) -> Bar:
        self._step_count += 1
        self._reconcile()

        if self._position:
            mode_str = self.mode.value if hasattr(self.mode, 'value') else str(self.mode)
            exit_price = None
            if self._position.max_exit_time and bar.time >= self._position.max_exit_time:
                exit_price = bar.close
            elif self._position.direction == Direction.LONG:
                if bar.low <= self._position.stop:
                    exit_price = self._position.stop
                    if self.slippage:
                        exit_price = self.slippage.on_stop(exit_price, self._position.direction, mode_str)
                elif bar.high >= self._position.target:
                    exit_price = self._position.target
                    if self.slippage:
                        exit_price = self.slippage.on_target(exit_price, self._position.direction, mode_str)
            else:
                if bar.high >= self._position.stop:
                    exit_price = self._position.stop
                    if self.slippage:
                        exit_price = self.slippage.on_stop(exit_price, self._position.direction, mode_str)
                elif bar.low <= self._position.target:
                    exit_price = self._position.target
                    if self.slippage:
                        exit_price = self.slippage.on_target(exit_price, self._position.direction, mode_str)

            if exit_price is not None:
                pnl = (exit_price - self._position.entry) * self._position.direction.value - self.cost
                closed_at = bar.time
                bars_held = self._step_count - self._position._open_step
                self._trades.append(Trade(
                    strategy_id=self._position.strategy_id,
                    direction=self._position.direction,
                    entry=self._position.entry,
                    exit=exit_price,
                    pnl_points=round(pnl, 1),
                    opened_at=self._position.opened_at,
                    closed_at=closed_at,
                    bars_held=bars_held))
                log.info(f"{self._position.strategy_id} FECHOU dir={'LONG' if self._position.direction==Direction.LONG else 'SHORT'} entry={self._position.entry:.0f} exit={exit_price:.0f} pnl={pnl:+.0f}")
                if self.risk_guardian:
                    self.risk_guardian.post_process(pnl)
                self._position = None

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
                order = self.broker.execute(signal)
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
                bars_held=0))
            self._position = None
        return self._calc_stats()

    def _calc_stats(self) -> ExecutionResult:
        t = np.array([tr.pnl_points for tr in self._trades], dtype=float)
        if len(t) == 0:
            return ExecutionResult(trades=[], total_pnl=0, win_rate=0,
                profit_factor=0, total=0, media=0, p_valor=1,
                metade1_media=0, metade2_media=0, metades_ok=True)

        from scipy import stats as scipy_stats
        _, p_val = scipy_stats.ttest_1samp(t, 0)
        met1 = t[:len(t)//2] if len(t)//2 > 0 else t
        met2 = t[len(t)//2:] if len(t)//2 > 0 else t
        wins = t[t > 0]; losses = t[t < 0]
        m1 = float(met1.mean()); m2 = float(met2.mean())
        total_pnl = float(t.sum())
        win_rate = float((t > 0).mean() * 100)
        pf = float(wins.sum() / abs(losses.sum())) if len(losses) > 0 else float('inf') if len(wins) > 0 else 0
        media = float(t.mean())
        std = float(t.std())
        sharpe = media / std if std > 0 else 0
        metades_ok = bool((m1 > 0) == (m2 > 0))

        return ExecutionResult(
            trades=self._trades,
            total_pnl=total_pnl,
            win_rate=win_rate,
            profit_factor=pf,
            total=len(t),
            media=media,
            p_valor=float(p_val),
            metade1_media=m1,
            metade2_media=m2,
            metades_ok=metades_ok,
            sharpe=sharpe)

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
                import MetaTrader5 as mt5
                ticket = int(self._position.ticket) if self._position.ticket else 0
                if ticket:
                    deals = mt5.history_deals_get(position=ticket)
                    if deals is not None and len(deals) > 0:
                        for d in deals:
                            if hasattr(d, 'entry') and d.entry == 1:
                                exit_price = float(d.price)
                                closed_at = datetime.fromtimestamp(d.time)
                                break
                        else:
                            d = deals[-1]
                            exit_price = float(d.price)
                            closed_at = datetime.fromtimestamp(d.time)
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
            self._position = None
        except Exception as e:
            log.warning(f"Reconcile error: {e}")

    def run_live(self, interval: int = 60):
        log.info(f"Engine live start | mode={self.mode.value} | interval={interval}s")
        state_dir = os.path.join(os.path.dirname(__file__), "..", "state")
        try:
            while True:
                try:
                    self._reconcile()
                    bar = self.step()
                    if bar:
                        log.info(f"Bar: {bar.time} O={bar.open:.0f} H={bar.high:.0f} L={bar.low:.0f} C={bar.close:.0f}")
                    self._reconcile()
                    positions = self.broker.fetch_positions()
                    with open(os.path.join(state_dir, "positions.json"), "w") as f:
                        json.dump([{
                            "strategy_id": p.strategy_id,
                            "direction": p.direction.name,
                            "entry": p.entry,
                            "size": p.size,
                            "opened_at": str(p.opened_at),
                            "stop": p.stop,
                            "target": p.target,
                            "ticket": p.ticket,
                        } for p in positions], f, indent=2)
                except Exception as e:
                    log.error(f"step error: {e}")
                time.sleep(interval)
        except KeyboardInterrupt:
            log.info("Engine live stopped (Ctrl+C)")

    def close(self):
        if hasattr(self.feed, "close"):
            self.feed.close()
        if self.mode != ExecutionMode.BT:
            try:
                import MetaTrader5 as mt5
                mt5.shutdown()
            except:
                pass
