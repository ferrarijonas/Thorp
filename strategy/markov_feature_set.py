"""Feature set compartilhado para estrategias Markov v2 (H142-H147).
Cada estrategia herda desta classe e define _check_conditions().
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Bar, Signal
from strategy.base import Strategy
from collections import deque

class MarkovFeatureSet(Strategy):
    BUFFER_DAYS = 21

    def __init__(self, name: str):
        self._name = name
        self.reset()

    def _p(self, buf, pct):
        if len(buf) < 5:
            return 0
        s = sorted(buf)
        return s[int(len(s) * pct)]

    def _p25(self, buf): return self._p(buf, 0.25)
    def _p50(self, buf): return self._p(buf, 0.50)
    def _p75(self, buf): return self._p(buf, 0.75)
    def _rank(self, buf, val):
        if len(buf) < 5:
            return 0.5
        return sum(1 for v in buf if v < val) / max(len(buf), 1)

    def _check_conditions(self, f, bar) -> Signal | None:
        raise NotImplementedError

    def reset(self):
        self._feat9 = None
        self._prev_close = None
        self._ontem_9close = None
        self._dia_atual = None
        self._buf_range9 = deque(maxlen=self.BUFFER_DAYS)
        self._buf_body_ratio = deque(maxlen=self.BUFFER_DAYS)
        self._buf_vol9 = deque(maxlen=self.BUFFER_DAYS)
        self._buf_gap = deque(maxlen=self.BUFFER_DAYS)
        self._body_ratio_d1 = None
        self._range_9_d1 = None
        self._gap_d1 = None
        self._range_d1_total = None
        self._vol_9_d1 = None

    def on_bar(self, bar: Bar) -> Signal | None:
        data = bar.time.date()
        h, m = bar.time.hour, bar.time.minute

        if self._dia_atual is None or data != self._dia_atual:
            self._dia_atual = data

        if h == 9 and m == 0:
            O, H, L, C, V = bar.open, bar.high, bar.low, bar.close, bar.volume
            r9 = H - L
            if r9 <= 0:
                return None

            body = abs(C - O)
            body_ratio = body / r9
            shadow_up = (H - max(O, C)) / r9 if r9 > 0 else 0
            shadow_dn = (min(O, C) - L) / r9 if r9 > 0 else 0
            pos_close = (C - L) / r9 if r9 > 0 else 0
            fractal = r9 / (body + 1)
            mid = (H + L) / 2
            wick_asym = shadow_up / (shadow_dn + 0.001)
            green_9 = 1 if C > O else 0

            gap = None
            if self._prev_close is not None:
                gap = O - self._prev_close
            else:
                gap = 0

            body_abs = body
            log_return = C / (O + 0.001)
            v9 = float(V)
            o_is_h = 1 if O == H else 0
            c_is_h = 1 if C == H else 0
            order_flow = v9 * (1 if C > mid else -1 if C < mid else 0)
            pressao = (v9 * max(C - mid, 0) / (r9 + 0.001)) / (v9 + 0.001)

            gap_up = 1 if gap > 0 else 0
            gap_rel_range = gap / (r9 + 0.001)

            # D-1 context
            body_ratio_d1 = self._body_ratio_d1 or body_ratio
            range_9_d1 = self._range_9_d1 or r9
            gap_d1 = self._gap_d1 or gap
            range_d1_total = self._range_d1_total or r9
            vol_9_d1 = self._vol_9_d1 or v9

            fragilidade = r9 / (range_d1_total + 0.001)
            range_ratio = r9 / (range_9_d1 + 0.001)

            delta_body = body_ratio - body_ratio_d1
            delta_range = r9 - range_9_d1
            delta_gap = (gap or 0) - (gap_d1 or 0)
            delta_vol = v9 - vol_9_d1

            # Rolling ranks
            range_9_rank = self._rank(self._buf_range9, r9)
            body_ratio_rank = self._rank(self._buf_body_ratio, body_ratio)

            # Regime vol
            range_p25 = self._p25(self._buf_range9)
            range_p75 = self._p75(self._buf_range9)
            regime_vol = 1
            if range_p25 > 0 and r9 < range_p25:
                regime_vol = 0
            if range_p75 > 0 and r9 > range_p75:
                regime_vol = 2

            zscore_range = 0
            if len(self._buf_range9) >= 10:
                avg = sum(self._buf_range9) / len(self._buf_range9)
                std = (sum((x - avg)**2 for x in self._buf_range9) / len(self._buf_range9))**0.5
                zscore_range = (r9 - avg) / (std + 0.001)

            # Store features
            self._feat9 = {
                "body_ratio": body_ratio, "shadow_up": shadow_up,
                "shadow_dn": shadow_dn, "range_9": r9,
                "green_9": green_9, "vol_9": v9,
                "gap": gap, "fractal": fractal,
                "wick_asym": wick_asym, "pos_close": pos_close,
                "body_abs": body_abs, "log_return": log_return,
                "o_is_h": o_is_h, "c_is_h": c_is_h,
                "order_flow": order_flow,
                "pressao_compradora": pressao,
                "gap_up": gap_up, "gap_rel_range": gap_rel_range,
                "range_9_rank": range_9_rank,
                "body_ratio_rank": body_ratio_rank,
                "regime_vol": regime_vol,
                "zscore_range": zscore_range,
                "delta_body": delta_body, "delta_range": delta_range,
                "delta_gap": delta_gap, "delta_vol": delta_vol,
                "fragilidade": fragilidade, "range_ratio": range_ratio,
                "range_d1_total": range_d1_total,
                "range_9_d1": range_9_d1,
                "body_ratio_d1": body_ratio_d1,
            }

            # Update buffers (depois de computar, pra nao usar o proprio dia)
            self._buf_range9.append(r9)
            self._buf_body_ratio.append(body_ratio)
            self._buf_vol9.append(v9)
            self._buf_gap.append(gap if gap is not None else 0)

            self._body_ratio_d1 = body_ratio
            self._range_9_d1 = r9
            self._gap_d1 = gap
            self._range_d1_total = range_d1_total
            self._vol_9_d1 = v9

            self._prev_close = C

        if h == 9 and m == 1 and self._feat9 is not None:
            f = self._feat9
            self._feat9 = None
            direcao = self._check_conditions(f, bar)
            if direcao is not None:
                return Signal(
                    direction=direcao,
                    entry=bar.open,
                    stop=0, target=0,
                    timestamp=bar.time,
                    strategy_id=self._name)
        return None

        return None
