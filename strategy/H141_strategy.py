from core.types import Bar, Signal, Direction
from strategy.base import Strategy
from collections import deque
from datetime import datetime, time as dtime

class H141Strategy(Strategy):
    """Continuacao de 9:00 — VENDA com entrada limite no high + time exit.
    
    Sinal: mesmas regras VENDA do H140 (shadow_up<=P50, body_ratio<=P75, etc).
    Entrada: ordem limite no open + 50% do range da 9:01.
    Stop: high da 9:01 + 10pts.
    Exit: time-based em 9:11 (10min hold).
    """
    def __init__(self):
        self._name = "H141"
        self._feat9 = None
        self._ontem_9dir = None
        self._ontem_01dir = None
        self._ontem_01verde = None
        self._ultimo_close = None
        self._dia_atual = None
        self._buf_ranges = deque(maxlen=21)
        self._buf_shadow_up = deque(maxlen=21)
        self._buf_shadow_dn = deque(maxlen=21)
        self._buf_body_ratio = deque(maxlen=21)
        self._buf_wick_asym = deque(maxlen=21)
        self._buf_gap = deque(maxlen=21)

    def _p(self, buf, pct):
        if len(buf) < 5: return 0
        s = sorted(buf)
        return s[int(len(s)*pct)]

    def _p25(self, buf): return self._p(buf, 0.25)
    def _p50(self, buf): return self._p(buf, 0.50)
    def _p75(self, buf): return self._p(buf, 0.75)
    def _p90(self, buf): return self._p(buf, 0.90)

    def on_bar(self, bar: Bar) -> Signal | None:
        data = bar.time.date()
        h, m = bar.time.hour, bar.time.minute

        if self._dia_atual is None or data != self._dia_atual:
            self._dia_atual = data

        self._ultimo_close = bar.close

        if h == 9 and m == 0:
            O, H, L, C = bar.open, bar.high, bar.low, bar.close
            r = H - L
            if r <= 0:
                self._feat9 = None
                self._ontem_9dir = C > O
                return None

            body_ratio = abs(C - O) / r
            shadow_up = (H - max(O, C)) / r
            shadow_dn = (min(O, C) - L) / r
            pos_close = (C - L) / r
            fractal = r / (abs(C - O) + 1)
            wick_asym = shadow_up / (shadow_dn + 0.001)

            acertou = None
            if self._ontem_9dir is not None and self._ontem_01dir is not None:
                acertou = (self._ontem_9dir == self._ontem_01dir)

            gap = None
            if self._ultimo_close is not None and self._ultimo_close != bar.close:
                gap = O - self._ultimo_close

            self._feat9 = {
                "O": O, "H": H, "L": L, "C": C, "V": bar.volume,
                "r": r, "body_ratio": body_ratio,
                "shadow_up": shadow_up, "shadow_dn": shadow_dn,
                "pos_close": pos_close, "fractal": fractal,
                "wick_asym": wick_asym, "gap": gap, "acertou": acertou,
                "ontem_01verde": self._ontem_01verde,
                "ontem_9dir": self._ontem_9dir,
            }
            self._ontem_9dir = C > O

        if h == 9 and m == 1 and self._feat9 is not None:
            f = self._feat9
            self._feat9 = None
            self._ontem_01dir = bar.close > bar.open
            self._ontem_01verde = bar.close > bar.open

            # Atualiza buffers
            self._buf_ranges.append(f["r"])
            self._buf_shadow_up.append(f["shadow_up"])
            self._buf_shadow_dn.append(f["shadow_dn"])
            self._buf_body_ratio.append(f["body_ratio"])
            self._buf_wick_asym.append(f["wick_asym"])
            if f["gap"] is not None:
                self._buf_gap.append(abs(f["gap"]))

            br_p25 = self._p25(self._buf_body_ratio)
            br_p50 = self._p50(self._buf_body_ratio)
            br_p75 = self._p75(self._buf_body_ratio)
            su_p50 = self._p50(self._buf_shadow_up)
            su_p75 = self._p75(self._buf_shadow_up)
            sd_p75 = self._p75(self._buf_shadow_dn)
            wa_p50 = self._p50(self._buf_wick_asym)
            wa_p75 = self._p75(self._buf_wick_asym)
            gap_p90 = self._p90(self._buf_gap)

            # Fallbacks
            if br_p25 < 0.01: br_p25 = 0.20
            if br_p50 < 0.01: br_p50 = 0.45
            if br_p75 < 0.01: br_p75 = 0.65
            if su_p50 < 0.01: su_p50 = 0.20
            if su_p75 < 0.01: su_p75 = 0.40
            if sd_p75 < 0.01: sd_p75 = 0.40
            if wa_p50 < 0.01: wa_p50 = 0.90
            if wa_p75 < 0.01: wa_p75 = 2.90
            if gap_p90 < 1: gap_p90 = 400

            # Regras VENDA (mesmas do H140)
            venda = 0
            if f["shadow_up"] <= su_p50 and f["body_ratio"] <= br_p75:
                venda += 1
            if (f["shadow_up"] <= su_p50 and f["body_ratio"] <= br_p75
                    and f["acertou"] is False):
                venda += 1

            if venda < 2:
                return None

            # Entrada limite: open + 50% do range da 9:00 (conhecido)
            o_01, h_01 = bar.open, bar.high

            limit_price = o_01 + 0.5 * f["r"]

            # Verifica se a ordem limite teria sido executada
            if h_01 < limit_price:
                return None

            # Stop no high + 10pts (protecao)
            stop_price = h_01 + 10

            # Time exit em 9:11 (10min de hold)
            max_exit = bar.time.replace(hour=9, minute=11)

            return Signal(
                direction=Direction.VENDA,
                entry=limit_price,
                stop=stop_price,
                target=0,
                timestamp=bar.time,
                strategy_id=self._name,
                size=1,
                max_exit_time=max_exit)

        return None

    def reset(self):
        self._feat9 = None
        self._ontem_9dir = None
        self._ontem_01dir = None
        self._ontem_01verde = None
        self._ultimo_close = None
        self._dia_atual = None
        self._buf_ranges.clear()
        self._buf_shadow_up.clear()
        self._buf_shadow_dn.clear()
        self._buf_body_ratio.clear()
        self._buf_wick_asym.clear()
        self._buf_gap.clear()
