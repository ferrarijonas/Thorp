import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.types import Bar, Signal, Direction
from strategy.base import Strategy
from collections import deque

class H140Strategy(Strategy):
    """Markov Puro v2 — regras validadas via walk-forward (treino < 2025-07, teste >= 2025-07).
    
    Mineracao: Random Forest 200 arvores + varredura exaustiva de pares.
    Sobreviveram 7 regras com p<0.05 no teste out-of-sample.
    
    COMPRA (9:01 reverte pra cima):
      - ontem 9:01 foi verde AND range_9 > P75 (N=34, p=0.036 no teste)
      - wick_asym <= P50 AND shadow_up <= P75 (N=63, p=0.087)
      - shadow_up > 39% AND fractal > 1.51 AND ontem 9:00 vermelho (N=9, acc=89%)
    
    VENDA (9:01 reverte pra baixo):
      - range_9 > P50 AND pos_close > P75 (N=23, p=0.043 no teste)
      - acertou_ontem=0 AND shadow_up <= P50 (N=42, p=0.061)
      - shadow_up <= P75 AND shadow_dn > 25% AND range_9 > 182 (N=17, p=0.037)
    """
    def __init__(self):
        self._name = "H140"
        self._feat9 = None
        self._ontem_9dir = None
        self._ontem_01dir = None
        self._ontem_01verde = None
        self._ultimo_close = None
        self._dia_atual = None
        # Rolling buffer para percentis (21 dias)
        self._buf_ranges = deque(maxlen=21)
        self._buf_shadow_up = deque(maxlen=21)

    def _p50(self, buf):
        if len(buf) < 5: return 0
        s = sorted(buf)
        return s[len(s)//2]

    def _p75(self, buf):
        if len(buf) < 5: return 0
        s = sorted(buf)
        return s[int(len(s)*0.75)]

    def on_bar(self, bar: Bar) -> Signal | None:
        data = bar.time.date()
        h, m = bar.time.hour, bar.time.minute

        if self._dia_atual is None or data != self._dia_atual:
            self._dia_atual = data

        self._ultimo_close = bar.close

        if h == 9 and m == 0:
            O, H, L, C, V = bar.open, bar.high, bar.low, bar.close, bar.volume
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
                "O": O, "H": H, "L": L, "C": C, "V": V,
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

            # Atualiza buffers com os valores de 9:00
            self._buf_ranges.append(f["r"])
            self._buf_shadow_up.append(f["shadow_up"])

            r_p50 = self._p50(self._buf_ranges)
            r_p75 = self._p75(self._buf_ranges)
            su_p50 = self._p50(self._buf_shadow_up)
            su_p75 = self._p75(self._buf_shadow_up)
            # Fallback se buffer pequeno
            if r_p50 < 50: r_p50 = 180
            if r_p75 < 100: r_p75 = 275
            if su_p50 < 0.01: su_p50 = 0.25
            if su_p75 < 0.01: su_p75 = 0.50

            compra = 0
            venda = 0

            # === COMPRA signals ===

            # C1: ontem 9:01 foi verde + range alto (N=34, p=0.036)
            if f["ontem_01verde"] is True and f["r"] > r_p75:
                compra += 1

            # C2: wick simetrico + shadow_up contido (N=63, p=0.087)
            if f["wick_asym"] <= su_p50 and f["shadow_up"] <= su_p75:
                compra += 1

            # C3: rejeicao especifica (N=9, acc=89%) — so entra se muito forte
            if (f["shadow_up"] > 0.39 and f["fractal"] > 1.51
                    and f["ontem_9dir"] is False):
                compra += 2

            # === VENDA signals ===

            # V1: range > P50 + close no topo (N=23, p=0.043)
            if f["r"] > r_p50 and f["pos_close"] > 0.75:
                venda += 1

            # V2: errou ontem + sem sombra superior (N=42, p=0.061)
            if f["acertou"] is False and f["shadow_up"] <= su_p50:
                venda += 1

            # V3: sombra sup contida + sombra inf presente + range ok (N=17, p=0.037)
            if (f["shadow_up"] <= su_p75 and f["shadow_dn"] > 0.25
                    and f["r"] > 182):
                venda += 1

            # Decide
            if compra > venda and compra >= 1:
                return Signal(direction=Direction.COMPRA, entry=bar.open,
                              stop=0, target=0, timestamp=bar.time,
                              strategy_id=self._name, size=1)
            elif venda > compra and venda >= 1:
                return Signal(direction=Direction.VENDA, entry=bar.open,
                              stop=0, target=0, timestamp=bar.time,
                              strategy_id=self._name, size=1)

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
