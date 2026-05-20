"""Coordena multiplas estrategias ao vivo — 1 feed, 1 broker, N engines."""
import sys, os, time, logging, json
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import ExecutionMode
from execution.engine import ExecutionEngine

log = logging.getLogger("manager")

class PortfolioRiskManager:
    """Risco agregado do portfolio. Por hora: so soma PnL e DD."""
    def __init__(self, capital: float = 1000, max_dd: float = 99999):
        self.capital = capital
        self.max_dd = max_dd
        self._initial_capital = capital

    def update(self, pnl_change: float):
        self.capital += pnl_change

    @property
    def drawdown(self) -> float:
        return max(0.0, self._initial_capital - self.capital)


class StrategyManager:
    """Coordena N engines. Feed distribui mesma barra pra todas."""
    def __init__(self, feed, broker, mode: ExecutionMode = ExecutionMode.DEMO,
                 capital: float = 1000, max_dd: float = 99999):
        self.feed = feed
        self.broker = broker
        self.mode = mode
        self.portfolio_risk = PortfolioRiskManager(capital, max_dd)
        self.engines: list[ExecutionEngine] = []
        self.state_dir = os.path.join(os.path.dirname(__file__), "..", "state", "live")
        self._running = False
        os.makedirs(self.state_dir, exist_ok=True)

    def add(self, strategy_class, risk_guardian=None, slippage=None, capital=None,
            trade_store_path=None, capital_store_path=None):
        """Adiciona uma estrategia ao manager. capital=None usa o capital total."""
        engine = ExecutionEngine(
            feed=self.feed,
            strategy=strategy_class(),
            broker=self.broker,
            mode=self.mode,
            risk_guardian=risk_guardian,
            slippage=slippage,
            trade_store_path=trade_store_path,
            capital_store_path=capital_store_path,
        )
        hid = ""
        try:
            hid = strategy_class.__name__.replace("Strategy", "")
        except Exception:
            hid = f"ENG{len(self.engines)}"
        # Determina o strategy_id da engine (usado no dashboard)
        try:
            engine._hid = engine.strategy._name if hasattr(engine.strategy, '_name') else hid
        except Exception:
            engine._hid = hid
        engine._capital = capital or (self.portfolio_risk.capital / max(1, len(self.engines)))
        self.engines.append(engine)
        log.info(f"Adicionado {hid} ({len(self.engines)})")
        return engine

    @property
    def status(self) -> list[dict]:
        result = []
        for engine in self.engines:
            p = engine._position
            trades = engine._trades
            pnl = sum(t.pnl_points for t in trades)
            result.append({
                "hid": getattr(engine, "_hid", "?"),
                "posicao": p.direction.name if p else None,
                "entry": p.entry if p else None,
                "stop": p.stop if p else None,
                "target": p.target if p else None,
                "ticket": p.ticket if p else None,
                "trades": len(trades),
                "pnl": round(pnl, 1),
                "step": engine._step_count,
            })
        return result

    def render_dashboard(self):
        """Painel texto ao vivo."""
        os.system("cls" if os.name == "nt" else "clear")
        status = self.status
        total_pnl = sum(s["pnl"] for s in status)
        total_trades = sum(s["trades"] for s in status)
        total_pos = sum(1 for s in status if s["posicao"])
        print("=" * 74)
        print(f"  THORP LIVE  |  {datetime.now():%Y-%m-%d %H:%M:%S}  |  {len(self.engines)} engines")
        print("=" * 74)
        print(f"  {'ID':<6} {'Direcao':<8} {'Entry':>8} {'Stop':>8} {'Target':>8} {'Trades':>6} {'PnL':>8}")
        print("-" * 74)
        for s in status:
            direcao = s["posicao"] or "---"
            entry = f'{s["entry"]:.0f}' if s["entry"] else "---"
            stop = f'{s["stop"]:.0f}' if s["stop"] else "---"
            target = f'{s["target"]:.0f}' if s["target"] else "---"
            print(f"  {s['hid']:<6} {direcao:<8} {entry:>8} {stop:>8} {target:>8} {s['trades']:>6} {s['pnl']:>+8.0f}")
        print("-" * 74)
        print(f"  {'TOTAL':<6} {total_pos:>3} pos    {'':>10} {total_trades:>6} {total_pnl:>+8.0f}")
        print(f"  Capital: {self.portfolio_risk.capital:.0f}    DD: {self.portfolio_risk.drawdown:.0f}")
        print("=" * 74)

    def run(self, interval: int = 30, dashboard: bool = True):
        """Loop principal."""
        log.info(f"StrategyManager start | {len(self.engines)} engines | interval={interval}s")
        self._running = True
        try:
            while self._running:
                try:
                    bar = self.feed.poll()
                except Exception as e:
                    log.error(f"Feed poll error: {e}")
                    time.sleep(interval)
                    continue
                if bar:
                    for engine in self.engines:
                        try:
                            engine.on_bar(bar)
                        except Exception as e:
                            log.error(f"Engine {getattr(engine, '_hid', '?')}: {e}")
                    self._save_state()
                if dashboard:
                    self.render_dashboard()
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self._running = False
        log.info("StrategyManager stopped")
        self.close()

    def close(self):
        for engine in self.engines:
            try:
                engine.close()
            except Exception:
                pass
        try:
            self.feed.close()
        except Exception:
            pass

    def _save_state(self):
        path = os.path.join(self.state_dir, "manager_state.json")
        try:
            with open(path, "w") as f:
                json.dump({
                    "timestamp": str(datetime.now()),
                    "capital": self.portfolio_risk.capital,
                    "drawdown": self.portfolio_risk.drawdown,
                    "engines": self.status,
                }, f, indent=2, default=str)
        except Exception:
            pass
