"""Analisador de performance — centraliza todas as métricas do Thorp."""

import numpy as np
from scipy import stats as scipy_stats
from core.types import Direction, Trade, ExecutionResult


GEO_PRECOS = {"abertura": 0, "fechamento": 3, "maxima": 1, "minima": 2}

def _entry_price(rastro, geo, trade_entry):
    """Preço de entrada a partir da barra anterior (rastro[0])."""
    if geo == "actual" or not rastro:
        return trade_entry
    return rastro[0][GEO_PRECOS.get(geo, 3)]


def re_simular_um(trade, sl_pts, tp_pts, convention="worst", geo="actual"):
    """Re-simula um trade contra seu rastro. Retorna PnL ou None.

    Rastro[0] = barra anterior (referência de entrada).
    Rastro[1:] = barra de entrada em diante (SL/TP verificados aqui).
    Se tp_pts é None: modo TIME (sem SL/TP, só time exit).
    """
    if not trade.rastro:
        return None
    direcao = trade.direction
    entry = _entry_price(trade.rastro, geo, trade.entry)

    has_prev = len(trade.rastro) >= 2
    offset = 1 if has_prev else 0
    rastro = trade.rastro[offset:]
    if not rastro:
        return None

    if tp_pts is None:
        last_close = rastro[-1][3]
        return (last_close - entry) if direcao == Direction.COMPRA else (entry - last_close)

    if direcao == Direction.COMPRA:
        if convention == "worst":
            first = lambda H, L, C: L <= entry - sl_pts
            first_exit = -sl_pts
            second = lambda H, L, C: H >= entry + tp_pts
            second_exit = tp_pts
        else:
            first = lambda H, L, C: H >= entry + tp_pts
            first_exit = tp_pts
            second = lambda H, L, C: L <= entry - sl_pts
            second_exit = -sl_pts
    else:
        if convention == "worst":
            first = lambda H, L, C: H >= entry + sl_pts
            first_exit = -sl_pts
            second = lambda H, L, C: L <= entry - tp_pts
            second_exit = tp_pts
        else:
            first = lambda H, L, C: L <= entry - tp_pts
            first_exit = tp_pts
            second = lambda H, L, C: H >= entry + sl_pts
            second_exit = -sl_pts

    for bar in rastro:
        O, H, L, C, _ = bar
        if first(H, L, C):
            return first_exit
        if second(H, L, C):
            return second_exit

    last_close = rastro[-1][3]
    return (last_close - entry) if direcao == Direction.COMPRA else (entry - last_close)


def _stats(arr, min_n=5):
    """Calcula estatísticas de um array de PnLs."""
    arr = np.array([x for x in arr if x is not None], dtype=float)
    n = len(arr)
    if n < min_n:
        return {"N": n, "media_pts": 0, "vantagem_pct": 0, "wr_pct": 0, "p_valor": 1}
    media = float(arr.mean())
    wr = float((arr > 0).mean() * 100)
    vantagem = (wr - 50) * 2
    _, p = scipy_stats.ttest_1samp(arr, 0)
    return {
        "N": n,
        "media_pts": round(media, 1),
        "vantagem_pct": round(vantagem, 1),
        "wr_pct": round(wr, 1),
        "p_valor": round(float(p), 4),
    }


class Analisador:

    @staticmethod
    def calcular(trades: list[Trade]) -> dict:
        """Métricas gerais do backtest."""
        arr = np.array([t.pnl_points for t in trades], dtype=float)
        N = len(arr)
        if N == 0:
            return {"N": 0, "media_pts": 0.0, "wr_pct": 0.0, "vantagem_pct": 0.0,
                    "p_valor": 1.0, "pf": 0.0, "sharpe": 0.0, "dd_max": 0.0,
                    "mfe_medio": 0.0, "mae_medio": 0.0,
                    "metade1": 0.0, "metade2": 0.0, "metades_ok": True}

        wins = arr[arr > 0]
        losses = arr[arr < 0]
        media = float(arr.mean())
        wr = float((arr > 0).mean() * 100)
        vantagem = (wr - 50) * 2
        if N >= 2:
            _, p = scipy_stats.ttest_1samp(arr, 0)
            p_val = float(p)
        else:
            p_val = 1.0
        pf = float(wins.sum() / abs(losses.sum())) if len(losses) > 0 else (float('inf') if len(wins) > 0 else 0)
        std = float(arr.std())
        sharpe = media / std if std > 0 else 0.0

        equity = np.cumsum(arr)
        peak = np.maximum.accumulate(equity)
        dd_max = float((peak - equity).max()) if N > 0 else 0.0

        mfes, maes = [], []
        for t in trades:
            if t.rastro:
                mfe, mae = Analisador._mfe_mae(t.rastro, t.entry, t.direction)
                mfes.append(mfe)
                maes.append(mae)
        mfe_medio = float(np.mean(mfes)) if mfes else 0.0
        mae_medio = float(np.mean(maes)) if maes else 0.0

        half = N // 2 if N >= 2 else N
        met1 = arr[:half]
        met2 = arr[half:] if N >= 2 else arr
        m1 = float(met1.mean()) if len(met1) > 0 else 0.0
        m2 = float(met2.mean()) if len(met2) > 0 else 0.0
        metades_ok = bool((m1 > 0) == (m2 > 0)) if N >= 2 else True

        return {
            "N": N, "media_pts": round(media, 1), "wr_pct": round(wr, 1),
            "vantagem_pct": round(vantagem, 1), "p_valor": round(p_val, 4),
            "pf": round(pf, 2), "sharpe": round(sharpe, 3),
            "dd_max": round(dd_max, 0),
            "mfe_medio": round(mfe_medio, 1), "mae_medio": round(mae_medio, 1),
            "metade1": round(m1, 1), "metade2": round(m2, 1),
            "metades_ok": metades_ok,
        }

    @staticmethod
    def resultado(trades: list[Trade]) -> ExecutionResult:
        """Retorna ExecutionResult completo a partir dos trades."""
        import numpy as np
        a = Analisador.calcular(trades)
        t = np.array([tr.pnl_points for tr in trades], dtype=float)
        return ExecutionResult(
            trades=trades,
            total_pnl=float(t.sum()) if len(t) > 0 else 0,
            win_rate=a["wr_pct"],
            profit_factor=a["pf"],
            total=a["N"],
            media=a["media_pts"],
            p_valor=a["p_valor"],
            metade1_media=a["metade1"],
            metade2_media=a["metade2"],
            metades_ok=a["metades_ok"],
            sharpe=a["sharpe"],
            vantagem_pct=a["vantagem_pct"],
            dd_max=a["dd_max"],
            mfe_medio=a["mfe_medio"],
            mae_medio=a["mae_medio"])

    @staticmethod
    def _mfe_mae(rastro: list, entry: float, direcao: Direction) -> tuple:
        """Calcula MFE e MAE a partir do rastro. Ambos positivos."""
        Hs = np.array([r[1] for r in rastro], dtype=float)
        Ls = np.array([r[2] for r in rastro], dtype=float)
        if direcao == Direction.COMPRA:
            mfe = max(float(np.max(Hs - entry)), 0.0)
            mae = max(float(np.max(entry - Ls)), 0.0)
        else:
            mfe = max(float(np.max(entry - Ls)), 0.0)
            mae = max(float(np.max(Hs - entry)), 0.0)
        return mfe, mae

    @staticmethod
    def vantagem_por_entrada(trades, sl_fn, tp_fn, conv="worst"):
        """Vantagem para cada ponto de entrada (abertura, fechamento, maxima, minima)."""
        pontos = {}
        geos = ["abertura", "fechamento", "maxima", "minima"]
        for geo in geos:
            pnls = []
            for t in trades:
                sp = sl_fn(t)
                m = t.opened_at.minute
                tp = round(tp_fn(sp, m))
                pnl = re_simular_um(t, sp, tp, conv, geo)
                if pnl is not None:
                    pnls.append(pnl)
            st = _stats(pnls)
            if st["N"] >= 5:
                pontos[geo] = st
        return pontos

    @staticmethod
    def decaimento_temporal(trades, max_barras=20):
        """Média e Vantagem barra a barra após entrada (sem container)."""
        if not trades:
            return {}
        lengths = [len(t.rastro) for t in trades if t.rastro]
        if not lengths:
            return {}
        max_len = min(max(lengths), max_barras)

        resultado = {}
        for i in range(max_len):
            pnls = []
            for t in trades:
                if t.rastro and len(t.rastro) > i:
                    close = t.rastro[i][3]
                    if t.direction == Direction.COMPRA:
                        pnls.append(close - t.entry)
                    else:
                        pnls.append(t.entry - close)
            st = _stats(pnls)
            if st["N"] >= 5:
                resultado[i] = st
        return resultado

    @staticmethod
    def re_simular(trades, sl_fn, tp_niveis, convencoes=("worst", "best"), geo="actual"):
        """Re-simula trades com múltiplos TPs e convenções.

        tp_niveis: list[tuple(str, callable)], ex: [("P50", fn), ("TIME", None)]
        """
        resultado = {}
        for nome_tp, tp_fn in tp_niveis:
            for conv in convencoes:
                chave = f"{nome_tp}_{conv}"
                pnls = []
                for t in trades:
                    sp = sl_fn(t)
                    m = t.opened_at.minute
                    tp = round(tp_fn(sp, m)) if tp_fn is not None else None
                    pnl = re_simular_um(t, sp, tp, conv, geo)
                    if pnl is not None:
                        pnls.append(pnl)
                resultado[chave] = _stats(pnls)
        return resultado

    @staticmethod
    def veredito(trades, sl_fn, tp_fn) -> str:
        """Veredito automático: ROBUSTO / SINAL OK / MORTA."""
        if not trades:
            return "MORTA"
        from core.containers import P50 as P50_PTS

        tp_niveis = [("P50", lambda sp, m: P50_PTS.get(m, 120))]
        res = Analisador.re_simular(trades, sl_fn, tp_niveis, ("worst", "best"))
        w = res.get("P50_worst", {})
        b = res.get("P50_best", {})
        pw = w.get("p_valor", 1)
        pb = b.get("p_valor", 1)
        mw = w.get("media_pts", 0)
        mb = b.get("media_pts", 0)
        mesmo_sinal = (mw > 0 and mb > 0) or (mw < 0 and mb < 0)

        if pw < 0.05 and pb < 0.05 and mesmo_sinal:
            return "ROBUSTO"
        elif pw < 0.05 or pb < 0.05:
            return "SINAL OK"
        return "MORTA"
