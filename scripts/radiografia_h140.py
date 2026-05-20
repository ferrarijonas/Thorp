"""Radiografia H140 — testa cada preditor de 9:00 contra o retorno de 9:01.
Uso: python scripts/radiografia_h140.py
     python scripts/radiografia_h140.py --save  (salva CSV)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd
import numpy as np
from scipy import stats
from core.data import load_csv
from core.containers import P50 as P50_PTS, VOL_P50

# Silencia warnings
import warnings
warnings.filterwarnings("ignore")

pd.set_option('display.max_rows', 200)
pd.set_option('display.width', 180)

def build_dataset(df):
    """Monta dataset com 9:00 + 9:01 + D-1 + medias moveis e maximas/minimas."""
    # Filtra horario B3 (9:00-17:00)
    df_day = df.between_time("09:00", "17:00").copy()
    
    # Candle 9:00
    mask9 = (df_day['h']==9) & (df_day['m']==0)
    df9 = df_day[mask9][['open','high','low','close','volume']].copy()
    df9.columns = ['o9','h9','l9','c9','v9']
    df9['date'] = df9.index.date
    
    # Candle 9:01
    mask01 = (df_day['h']==9) & (df_day['m']==1)
    df01 = df_day[mask01][['open','close']].copy()
    df01.columns = ['o01','c01']
    df01['date'] = df01.index.date
    
    # Pregao anterior (D-1)
    df_day['date'] = df_day.index.date
    dates = sorted(df_day['date'].unique())
    date_map = {d: i for i, d in enumerate(dates)}
    df_day['date_idx'] = df_day['date'].map(date_map)
    
    # D-1 stats
    d1 = df_day.groupby('date').agg(
        o_d1=('open','first'), c_d1=('close','last'),
        h_d1=('high','max'), l_d1=('low','min'),
        v_d1=('volume','sum'),
        c9_d1=('close', lambda x: x.iloc[0] if len(x)>0 else np.nan),
        o9_d1=('open', lambda x: x.iloc[0] if len(x)>0 else np.nan),
        h9_d1=('high', lambda x: x.iloc[0] if len(x)>0 else np.nan),
        l9_d1=('low', lambda x: x.iloc[0] if len(x)>0 else np.nan),
        v9_d1=('volume', lambda x: x.iloc[0] if len(x)>0 else np.nan),
    )
    d1.index.name = 'date'
    d1 = d1.shift(1)  # D-1 relativo a hoje
    
    # Junta tudo
    m = df9.merge(df01, on='date', how='inner')
    m = m.merge(d1, on='date', how='left')
    
    # Remove linhas sem D-1 ou com problema
    m = m.dropna(subset=['c_d1','o9_d1'])
    
    return m

def compute_rolling_stats(df):
    """Calcula medias moveis e percentis rolantes."""
    # Precisamos ordenar por data
    df = df.sort_values('date')
    
    # Rolling 21 dias para stats de 9:00
    r9 = df['h9'] - df['l9']
    b9 = df['c9'] - df['o9']
    ret9 = b9 / df['o9']
    
    df['range9_21_avg'] = r9.rolling(21, min_periods=10).mean()
    df['range9_21_std'] = r9.rolling(21, min_periods=10).std()
    df['range9_21_p50'] = r9.rolling(21, min_periods=10).median()
    df['range9_21_p66'] = r9.rolling(21, min_periods=10).quantile(0.66)
    df['range9_21_p33'] = r9.rolling(21, min_periods=10).quantile(0.33)
    df['ret9_21_avg'] = ret9.rolling(21, min_periods=10).mean()
    df['ret9_21_std'] = ret9.rolling(21, min_periods=10).std()
    
    df['range9_21_max'] = r9.rolling(21, min_periods=10).max()
    df['range9_21_min'] = r9.rolling(21, min_periods=10).min()
    
    # Rolling para volume
    df['v9_21_avg'] = df['v9'].rolling(21, min_periods=10).mean()
    df['v9_21_std'] = df['v9'].rolling(21, min_periods=10).std()
    df['v9_21_p50'] = df['v9'].rolling(21, min_periods=10).median()
    df['v9_21_p66'] = df['v9'].rolling(21, min_periods=10).quantile(0.66)
    
    # Rolling para gap
    gap = df['o9'] - df['c_d1']
    df['gap_21_std'] = gap.rolling(21, min_periods=10).std()
    df['gap_21_avg'] = gap.rolling(21, min_periods=10).mean()
    
    # Rolling para max/min historico (dentro do dataset)
    df['max_hist'] = df['h9'].cummax()
    df['min_hist'] = df['l9'].cummin()
    
    # MM21 do close
    df['mm21'] = df['c9'].rolling(21, min_periods=10).mean()
    df['std21'] = df['c9'].rolling(21, min_periods=10).std()
    
    # VWAP D-1 (H+L+C)/3 * volume / volume
    df['vwap_d1'] = df['v_d1'].rolling(1).mean()  # placeholder
    # VWAP real = sum(HLC*V/3) / sum(V) por dia
    # Usaremos (close_D-1 + high_D-1 + low_D-1) / 3 como proxy
    df['vwap_d1'] = (df['h_d1'] + df['l_d1'] + df['c_d1']) / 3
    
    # Rolling 21 para close
    df['close_21_max'] = df['c9'].rolling(21, min_periods=10).max()
    df['close_21_min'] = df['c9'].rolling(21, min_periods=10).min()
    
    return df

def compute_predictors(df):
    """Calcula todos os 100 preditores."""
    P = df.copy()
    
    # Variaveis auxiliares
    r9 = P['h9'] - P['l9']          # range 9:00
    b9 = P['c9'] - P['o9']           # body orientado
    body = b9.abs()                   # corpo absoluto
    body_ratio = body / (r9 + 0.001)  # body ratio (evita div por zero)
    mid = (P['h9'] + P['l9']) / 2     # midpoint
    pos_close = (P['c9'] - P['l9']) / (r9 + 0.001)  # posicao do close no range
    
    sup_shadow = (P['h9'] - np.maximum(P['o9'], P['c9'])) / (r9 + 0.001)
    inf_shadow = (np.minimum(P['o9'], P['c9']) - P['l9']) / (r9 + 0.001)
    
    gap = P['o9'] - P['c_d1']  # gap overnight
    
    # Variavel alvo
    P['ret_01'] = P['c01'] - P['o01']      # retorno em pts
    P['dir_01'] = (P['ret_01'] > 0).astype(int)  # direcao binaria
    
    # Lista de resultados
    results = []
    
    def add(name, typ, values, nclasses=None):
        """Registra um preditor e testa contra ret_01."""
        nonlocal P, results
        valid = values.notna() & P['ret_01'].notna()
        vals = values[valid]
        rets = P.loc[valid, 'ret_01']
        dirs = P.loc[valid, 'dir_01']
        n = len(vals)
        if n < 10:
            results.append({'preditor': name, 'tipo': typ, 'n': n,
                           'acuracia': 0, 'media_pts': 0, 'p_valor': 1,
                           'classes': nclasses or 0, 'info': 'N < 10'})
            return
        
        if typ == 'binario':
            # Separa as duas classes
            mask1 = vals > 0.5 if vals.dtype.kind in 'bf' else vals == 1
            if isinstance(mask1, (pd.Series,)):
                v0 = rets[~mask1]; v1 = rets[mask1]
            else:
                v0 = rets[~vals]; v1 = rets[vals]
            n0, n1 = len(v0), len(v1)
            if n0 < 3 or n1 < 3:
                results.append({'preditor': name, 'tipo': typ, 'n': n,
                               'acuracia': 0, 'media_pts': 0, 'p_valor': 1,
                               'classes': 2, 'info': f'N0={n0} N1={n1} muito pequeno'})
                return
            m0, m1 = v0.mean(), v1.mean()
            dif = m1 - m0
            # T-test
            t, p = stats.ttest_ind(v1, v0, equal_var=False)
            # Acuracia preditiva: se m1 > m0, chutar 1; se <, chutar 0
            if dif > 0:
                acuracia = (v1 > 0).sum() / n1 * (n1/n) + (v0 <= 0).sum() / n0 * (n0/n) if n > 0 else 0.5
            else:
                acuracia = (v1 <= 0).sum() / n1 * (n1/n) + (v0 > 0).sum() / n0 * (n0/n) if n > 0 else 0.5
            results.append({'preditor': name, 'tipo': typ, 'n': n,
                           'acuracia': round(acuracia*100, 1),
                           'media_pts': round(dif, 1),
                           'p_valor': round(p, 4),
                           'classes': 2,
                           'info': f'classe0={n0} media={m0:.1f} | classe1={n1} media={m1:.1f}'})
        
        elif typ == 'continuo':
            # Correlacao de Pearson
            r_val, p = stats.pearsonr(vals, rets)
            # Split por mediana para acuracia
            med = vals.median()
            acima = rets[vals >= med]
            abaixo = rets[vals < med]
            if len(acima) > 3 and len(abaixo) > 3:
                dif = acima.mean() - abaixo.mean()
                if dif > 0:
                    acuracia = (acima > 0).sum()/len(acima)*(len(acima)/n) + (abaixo <= 0).sum()/len(abaixo)*(len(abaixo)/n)
                else:
                    acuracia = (acima <= 0).sum()/len(acima)*(len(acima)/n) + (abaixo > 0).sum()/len(abaixo)*(len(abaixo)/n)
            else:
                acuracia = 0.5
                dif = 0
            results.append({'preditor': name, 'tipo': typ, 'n': n,
                           'acuracia': round(acuracia*100, 1),
                           'media_pts': round(dif, 1),
                           'p_valor': round(p, 4),
                           'classes': 0,
                           'info': f'r={r_val:.4f}'})
        
        elif typ == 'discreto':
            # ANOVA
            valid_v = vals.dropna()
            grupos = [rets[vals == v] for v in sorted(valid_v.unique()) if (vals == v).sum() > 5]
            if len(grupos) < 2:
                results.append({'preditor': name, 'tipo': typ, 'n': n,
                               'acuracia': 0, 'media_pts': 0, 'p_valor': 1,
                               'classes': nclasses or 0, 'info': 'poucos grupos com N>5'})
                return
            f_val, p = stats.f_oneway(*grupos)
            results.append({'preditor': name, 'tipo': typ, 'n': n,
                           'acuracia': 0, 'media_pts': 0,
                           'p_valor': round(p, 4),
                           'classes': len(grupos),
                           'info': f'F={f_val:.4f}'})
    
    # ==============================
    # I. Geometria do candle (1-14)
    # ==============================
    
    # 1 Direcao do candle
    add('1. Direcao candle (9:00 verde?)', 'binario', (b9 > 0).astype(int))
    
    # 2 Posicao do close no range
    add('2. Posicao close no range', 'continuo', pos_close)
    
    # 3 Tamanho do corpo
    add('3. Tamanho do corpo (abs)', 'continuo', body)
    
    # 4 Body ratio
    add('4. Body ratio', 'continuo', body_ratio)
    
    # 5 Sombra superior relativa
    add('5. Sombra superior relativa', 'continuo', sup_shadow)
    
    # 6 Sombra inferior relativa
    add('6. Sombra inferior relativa', 'continuo', inf_shadow)
    
    # 7 Forma geometrica (discreta)
    forma = pd.Series('outro', index=P.index)
    forma[(body_ratio < 0.5) & (inf_shadow > 0.5) & (sup_shadow < 0.15)] = 'martelo'
    forma[(body_ratio < 0.5) & (sup_shadow > 0.5) & (inf_shadow < 0.15)] = 'estrela_cadente'
    forma[(body_ratio < 0.15) & (sup_shadow > 0.35) & (inf_shadow > 0.35)] = 'doji_longo'
    forma[(body_ratio > 0.8) & (sup_shadow < 0.1) & (inf_shadow < 0.1)] = 'marubozu'
    forma[(body_ratio >= 0.15) & (body_ratio <= 0.5) & (sup_shadow < 0.35) & (inf_shadow < 0.35)] = 'spinning_top'
    # Codifica como int para ANOVA
    forma_code = pd.Categorical(forma).codes
    add('7. Forma geometrica', 'discreto', pd.Series(forma_code, index=P.index), nclasses=6)
    
    # 8 Fractal dimension proxy
    fractal = r9 / (body + 1)
    add('8. Fractal dimension proxy', 'continuo', fractal)
    
    # 9 Amplitude (range)
    add('9. Range absoluto', 'continuo', r9)
    
    # 10 Open = High?
    add('10. Open = High?', 'binario', (P['o9'] == P['h9']).astype(int))
    
    # 11 Open = Low?
    add('11. Open = Low?', 'binario', (P['o9'] == P['l9']).astype(int))
    
    # 12 Close = High?
    add('12. Close = High?', 'binario', (P['c9'] == P['h9']).astype(int))
    
    # 13 Close = Low?
    add('13. Close = Low?', 'binario', (P['c9'] == P['l9']).astype(int))
    
    # 14 Wick asymmetry
    wick_asym = sup_shadow / (inf_shadow + 0.001)
    add('14. Wick asymmetry', 'continuo', wick_asym)
    
    # ==============================
    # II. Volume e liquidez (15-20)
    # ==============================
    
    # 15 Volume absoluto
    add('15. Volume absoluto', 'continuo', P['v9'])
    
    # 16 Volume relativo (vs P50 historico)
    add('16. Volume relativo (vs hist)', 'continuo', P['v9'] / VOL_P50[0])
    
    # 17 Volume percentil 21d
    # Rolling rank
    v9_rank = P['v9'].rolling(21, min_periods=10).apply(
        lambda x: (x.iloc[-1] > x[:-1]).sum() / len(x[:-1]) if len(x) > 1 else 0.5)
    add('17. Volume percentil 21d', 'continuo', v9_rank)
    
    # 18 Liquidez (Kyle's lambda)
    add('18. Kyle lambda (range/vol)', 'continuo', r9 / (P['v9'] + 1))
    
    # 19 Amihud illiquidity
    add('19. Amihud illiquidity', 'continuo', body / (P['v9'] + 1))
    
    # 20 Volume assinado
    add('20. Volume assinado', 'continuo', P['v9'] * np.sign(b9))
    
    # ==============================
    # III. Gap (21-23)
    # ==============================
    
    # 21 Gap overnight
    add('21. Gap overnight (pts)', 'continuo', gap)
    
    # 22 Gap tipo (up/down)
    add('22. Gap tipo (up/down)', 'binario', (gap > 0).astype(int))
    
    # 23 Gap magnitude classe
    gap_class = pd.cut(gap.abs(), bins=[0, 50, 150, 300, np.inf], labels=[0,1,2,3])
    gap_class_s = pd.Series(gap_class, index=P.index).fillna(0).astype(int)
    add('23. Gap magnitude classe', 'discreto', gap_class_s, nclasses=4)
    
    # ==============================
    # IV. Niveis de preco (24-35)
    # ==============================
    
    # 24 Round number proximity
    round_dist = (P['c9'] % 100).apply(lambda x: min(x, 100-x))
    add('24. Round number prox (pts)', 'continuo', round_dist)
    
    # 25 Round breach
    round_nearest = (P['c9'] / 100).round() * 100
    breach = ((P['l9'] < round_nearest) & (P['c9'] < round_nearest) & (P['o9'] > round_nearest)).astype(int)
    add('25. Round number rompeu?', 'binario', breach)
    
    # 26 Dist maxima historica
    add('26. Dist max historica', 'continuo', (P['max_hist'] - P['c9']) / P['max_hist'])
    
    # 27 Dist minima historica
    add('27. Dist min historica', 'continuo', (P['c9'] - P['min_hist']) / P['min_hist'])
    
    # 28 Range mensal
    P['month'] = pd.to_datetime(P['date']).dt.month
    P['year'] = pd.to_datetime(P['date']).dt.year
    monthly_max = P.groupby(['year','month'])['h9'].transform('max')
    monthly_min = P.groupby(['year','month'])['l9'].transform('min')
    add('28. Pos range mensal', 'continuo', (P['c9'] - monthly_min) / (monthly_max - monthly_min + 0.001))
    
    # 29 Dist maxima 21d
    add('29. Dist max 21d', 'continuo', (P['close_21_max'] - P['c9']) / P['close_21_max'])
    
    # 30 Dist minima 21d
    add('30. Dist min 21d', 'continuo', (P['c9'] - P['close_21_min']) / P['close_21_min'])
    
    # 31 Dist MM21
    add('31. Dist MM21', 'continuo', (P['c9'] - P['mm21']) / P['mm21'])
    
    # 32 Dist VWAP D-1
    add('32. Dist VWAP D-1', 'continuo', (P['o9'] - P['vwap_d1']) / P['vwap_d1'])
    
    # 33 VWAP candle
    vwap_candle = (P['h9'] + P['l9'] + P['c9']) / 3
    add('33. VWAP candle', 'continuo', vwap_candle)
    
    # 34 Close vs VWAP candle
    add('34. Close vs VWAP candle', 'continuo', P['c9'] - vwap_candle)
    
    # 35 Preco absoluto tier (por 5000)
    tier = (P['c9'] / 5000).astype(int)
    add('35. Preco tier (5000pts)', 'discreto', tier, nclasses=tier.nunique())
    
    # ==============================
    # V. Relacao D-1 (36-45)
    # ==============================
    
    # 36 Range D-1 total
    add('36. Range D-1 total', 'continuo', P['h_d1'] - P['l_d1'])
    
    # 37 Volume D-1
    add('37. Volume D-1', 'continuo', P['v_d1'])
    
    # 38 Direcao D-1
    add('38. Direcao D-1', 'binario', (P['c_d1'] > P['o_d1']).astype(int))
    
    # 39 Cor 9:00 D-1
    d1_9dir = (P['c9_d1'] > P['o9_d1']).astype(int)
    add('39. Cor 9:00 D-1', 'binario', d1_9dir)
    
    # 40 Cor 9:01 D-1
    # Precisamos do 9:01 de D-1, que nao temos diretamente
    # Vamos usar shift do proprio 9:01
    P['dir_01_d1'] = P['dir_01'].shift(1)
    add('40. Cor 9:01 D-1', 'binario', P['dir_01_d1'])
    
    # 41 Range 9:00 D-1
    add('41. Range 9:00 D-1', 'continuo', P['h9_d1'] - P['l9_d1'])
    
    # 42 Range ratio (9:00 hoje / 9:00 ontem)
    d1_r9 = P['h9_d1'] - P['l9_d1']
    add('42. Range ratio 9:00 h/ontem', 'continuo', r9 / (d1_r9 + 0.001))
    
    # 43 Range 9:00 / range total D-1
    add('43. Fragilidade abertura', 'continuo', r9 / ((P['h_d1'] - P['l_d1']) + 0.001))
    
    # 44 Volume D-1 relativo
    add('44. Volume D-1 relativo', 'continuo', P['v_d1'] / P['v_d1'].median() if not P['v_d1'].isna().all() else 0)
    
    # 45 Retorno D-1
    add('45. Retorno D-1', 'continuo', (P['c_d1'] - P['o_d1']) / P['o_d1'])
    
    # ==============================
    # VI. Calendario (46-53)
    # ==============================
    
    dates = pd.to_datetime(P['date'])
    
    # 46 Dia da semana
    add('46. Dia da semana', 'discreto', dates.dt.dayofweek, nclasses=5)
    
    # 47 Mes
    add('47. Mes', 'discreto', dates.dt.month, nclasses=12)
    
    # 48 Semana do contrato
    week_of_month = (dates.dt.day - 1) // 7 + 1
    add('48. Semana do mes', 'discreto', week_of_month, nclasses=5)
    
    # 49 Dia do mes
    add('49. Dia do mes', 'continuo', dates.dt.day)
    
    # 50 Dias ate vencimento (prox 3a segunda)
    def days_to_expiry(d):
        y, m = d.year, d.month
        first_day = pd.Timestamp(y, m, 1)
        days_to_first_monday = (7 - first_day.dayofweek) % 7
        third_monday = 1 + days_to_first_monday + 14
        if third_monday > pd.Timestamp(y, m, 1).days_in_month:
            if m == 12:
                next_exp = pd.Timestamp(y+1, 1, 1)
            else:
                next_exp = pd.Timestamp(y, m+1, 1)
            days_to_first = (7 - next_exp.dayofweek) % 7
            third_monday_next = 1 + days_to_first + 14
            expiry = pd.Timestamp(y if m < 12 else y+1,
                                  m+1 if m < 12 else 1,
                                  third_monday_next)
        else:
            expiry = pd.Timestamp(y, m, third_monday)
        return (expiry - d).days
    
    dte = dates.map(days_to_expiry)
    add('50. Dias ate vencimento', 'continuo', dte)
    
    # 51 Vespera de feriado BR
    feriados_br = [(1,1), (4,21), (5,1), (9,7), (10,12), (11,2), (11,15), (12,25)]
    is_vespera = dates.map(lambda d: (d.month, d.day+1) in feriados_br or
                          ((d.month, d.day) in [(4,20),(5,8),(10,11),(11,1),(11,14),(12,24)]))
    add('51. Vespera feriado BR', 'binario', is_vespera.astype(int))
    
    # 52 Pos-feriado
    is_pos = dates.map(lambda d: (d.month, d.day-1) in feriados_br)
    add('52. Pos-feriado BR', 'binario', is_pos.astype(int))
    
    # 53 Feriado EUA D-1
    add('53. Feriado EUA D-1', 'binario', pd.Series(0, index=P.index))
    
    # ==============================
    # VII. Cadeia de Markov (54-56)
    # ==============================
    
    # 55 Markov 2a ordem
    dir9 = (b9 > 0).astype(int)
    dir9_d1 = dir9.shift(1).fillna(0).astype(int)
    markov2 = dir9 * 2 + dir9_d1
    add('55. Markov 2a ordem (9:00 h+ontem)', 'discreto', markov2, nclasses=4)
    
    # 56 Transicao consistente
    dir01_d1 = P['dir_01'].shift(1)
    acertou_ontem = ((dir9_d1 == dir01_d1)).astype(int)
    add('56. Transicao consistente (acertou ontem?)', 'binario', acertou_ontem)
    
    # ==============================
    # VIII. Sequencias (57-61)
    # ==============================
    
    def calc_streak(series):
        g = (series != series.shift()).cumsum()
        return series.groupby(g).cumcount() + 1
    
    dir9_int = (b9 > 0).astype(int)
    high_streak = calc_streak((P['c9'] > P['o9']).astype(int))
    add('57. Streak dias alta geral', 'continuo', high_streak)
    
    low_streak = calc_streak((P['c9'] < P['o9']).astype(int))
    add('58. Streak dias baixa geral', 'continuo', low_streak)
    
    green9_streak = calc_streak(dir9_int)
    add('59. Streak 9:00 verde', 'continuo', green9_streak)
    
    r9_p50 = r9.rolling(21, min_periods=10).median()
    range_alto = (r9 > r9_p50).astype(int)
    add('60. Streak range alto', 'continuo', calc_streak(range_alto))
    
    v9_p50 = P['v9'].rolling(21, min_periods=10).median()
    vol_alto = (P['v9'] > v9_p50).astype(int)
    add('61. Streak volume alto', 'continuo', calc_streak(vol_alto))
    
    # ==============================
    # IX. Regime volatilidade (62-67)
    # ==============================
    
    # 62 Range percentil 21d
    # Usando rolling apply
    r9_pct = r9.rolling(21, min_periods=10).apply(
        lambda x: (x[:-1] < x.iloc[-1]).sum() / len(x[:-1]) if len(x) > 1 else 0.5)
    add('62. Range percentil 21d', 'continuo', r9_pct)
    
    # 63 Volume percentil 21d
    v9_pct = P['v9'].rolling(21, min_periods=10).apply(
        lambda x: (x[:-1] < x.iloc[-1]).sum() / len(x[:-1]) if len(x) > 1 else 0.5)
    add('63. Volume percentil 21d', 'continuo', v9_pct)
    
    # 64 Gap percentil 21d
    gap_abs = gap.abs()
    gap_pct = gap_abs.rolling(21, min_periods=10).apply(
        lambda x: (x[:-1] < x.iloc[-1]).sum() / len(x[:-1]) if len(x) > 1 else 0.5)
    add('64. Gap percentil 21d', 'continuo', gap_pct)
    
    # 65 Z-score retorno 9:00 21d
    add('65. Z-score ret 9:00 21d', 'continuo', (b9 - P['ret9_21_avg']*P['o9']) / (P['ret9_21_std']*P['o9'] + 0.001))
    
    # 66 Z-score range 9:00 21d
    add('66. Z-score range 9:00 21d', 'continuo', (r9 - P['range9_21_avg']) / (P['range9_21_std'] + 0.001))
    
    # 67 Regime volatilidade (alto/medio/baixo)
    regime = pd.Series(1, index=P.index)  # medio
    regime[r9 > P['range9_21_p66']] = 2  # alto
    regime[r9 < P['range9_21_p33']] = 0  # baixo
    add('67. Regime volatilidade (0=baixo,1=med,2=alto)', 'discreto', regime, nclasses=3)
    
    # ==============================
    # X. Analise temporal (68-72)
    # ==============================
    
    # 68 Retorno ajustado por vol
    add('68. Retorno ajustado por vol', 'continuo', gap / (P['gap_21_std'] + 0.001))
    
    # 69 Half-life (usando |gap| como proxy)
    add('69. Half-life persistencia (gap)', 'continuo', gap_abs)
    
    # 70 Donchian position
    add('70. Donchian position 21d', 'continuo', (P['c9'] - P['close_21_min']) / (P['close_21_max'] - P['close_21_min'] + 0.001))
    
    # 71 Bollinger position
    add('71. Bollinger position 21d (z-score)', 'continuo', (P['c9'] - P['mm21']) / (P['std21'] + 0.001))
    
    # 72 Keltner position (usando std como proxy ATR)
    add('72. Keltner position (close-MM21)/std21', 'continuo', (P['c9'] - P['mm21']) / (P['std21'] + 0.001))
    
    # ==============================
    # XI. Microestrutura (73-79)
    # ==============================
    
    # 73 Parkinson
    parkinson = (r9 ** 2) / (4 * np.log(2))
    add('73. Parkinson volatility', 'continuo', parkinson)
    
    # 74 Garman-Klass
    gk = 0.5 * (r9**2) - 0.386 * (b9**2)
    gk = gk.clip(lower=0)  # nao pode ser negativo
    add('74. Garman-Klass volatility', 'continuo', gk)
    
    # 75 Rogers-Satchell
    rs = (P['h9']-P['c9'])*(P['h9']-P['o9'])/(r9+0.001) + (P['l9']-P['o9'])*(P['l9']-P['c9'])/(r9+0.001)
    rs = rs.clip(lower=0)
    add('75. Rogers-Satchell volatility', 'continuo', rs)
    
    # 76 Vol gap (Parkinson - GK)
    add('76. Vol gap (Parkinson - GK)', 'continuo', parkinson - gk)
    
    # 77 Roll spread proxy
    # Covariancia serial do retorno (precisa de lag)
    ret9 = b9 / P['o9']
    roll = -ret9 * ret9.shift(1)
    roll_proxy = np.sqrt(roll.clip(lower=0) * 2)
    add('77. Roll spread proxy', 'continuo', roll_proxy)
    
    # 78 Order flow proxy (Lee-Ready)
    of_proxy = P['v9'] * np.sign(P['c9'] - mid)
    add('78. Order flow proxy', 'continuo', of_proxy)
    
    # 79 Pressao compradora %
    vol_buy = P['v9'] * (P['c9'] - mid) / (r9 + 0.001)
    vol_buy = vol_buy.clip(lower=0)
    pressao = vol_buy / (P['v9'] + 0.001)
    add('79. Pressao compradora %', 'continuo', pressao)
    
    # ==============================
    # XII. Combinacoes direcionais (80-84)
    # ==============================
    
    # 80 Direcao + range
    dir_range = dir9 * 2 + (r9 > P['range9_21_p50']).astype(int)
    add('80. Direcao + range codificado', 'discreto', dir_range, nclasses=4)
    
    # 81 Gap + corpo
    gap_sinal = (gap > 0).astype(int)
    corpo_grande = (body > body.median()).astype(int)
    gap_corpo = gap_sinal * 2 + corpo_grande
    add('81. Gap + corpo codificado', 'discreto', gap_corpo, nclasses=4)
    
    # 82 Delta intra-candle (range/body)
    add('82. Delta intra-candle (range/body)', 'continuo', r9 / (body + 0.001))
    
    # 83 Cor 9:00 + cor 9:01 D-1
    cor_9_01_d1_combo = dir9 * 2 + P['dir_01_d1'].fillna(0).astype(int)
    add('83. Cor 9:00 + cor 9:01 D-1', 'discreto', cor_9_01_d1_combo, nclasses=4)
    
    # 84 Forca direcional (body * vol rel)
    add('84. Forca direcional (body*vol)', 'continuo', b9 * (P['v9'] / VOL_P50[0]))
    
    # ==============================
    # XIII. Distribuicoes (85-89)
    # ==============================
    
    # 85 Mahalanobis distance (5D: O,H,L,C,V)
    # Standariza cada dimensao
    from scipy.spatial.distance import mahalanobis
    # Usaremos media e cov rolling 21d para cada dimensao
    cols_5d = ['o9','h9','l9','c9','v9']
    # Simplificacao: rolling z-score medio
    z_scores = pd.DataFrame(index=P.index)
    for col in cols_5d:
        mu = P[col].rolling(21, min_periods=10).mean()
        sigma = P[col].rolling(21, min_periods=10).std()
        z_scores[col] = (P[col] - mu) / (sigma + 0.001)
    mahal = z_scores.pow(2).sum(axis=1).pow(0.5)  # simplificado: sqrt(soma z^2)
    add('85. Mahalanobis distance (5D)', 'continuo', mahal)
    
    # 86 Prob condicional empirica
    # Usando posicao close como proxy
    add('86. Prob condicional (pos close)', 'continuo', pos_close)
    
    # 87 Entropia do candle
    p = pos_close.clip(0.001, 0.999)
    entropia = -p * np.log(p) - (1-p) * np.log(1-p)
    add('87. Entropia do candle', 'continuo', entropia)
    
    # 88 Spike detection
    spike = (b9.abs() / (P['range9_21_std'] * P['o9'] + 0.001) > 3).astype(int)
    add('88. Spike detection (ret>3std)', 'binario', spike)
    
    # 89 Amplitude vs custo
    add('89. Amplitude < 10pts? (filtro)', 'binario', (r9 < 10).astype(int))
    
    # ==============================
    # XIV. Derivados (90-97)
    # ==============================
    
    # 90 Log return
    add('90. Log return', 'continuo', np.log(P['c9'] / (P['o9'] + 0.001)))
    
    # 91 Midpoint asymmetry
    add('91. Midpoint asymmetry (O vs mid)', 'continuo', (P['o9'] - mid) / (r9 + 0.001))
    
    # 92 Range/body inverso
    add('92. Range/body inverso', 'continuo', r9 / (body + 0.001))
    
    # 93 Open drift (vs D-1 range)
    drift = pd.Series(1, index=P.index)  # dentro do range
    drift[P['o9'] > P['h_d1']] = 2  # acima
    drift[P['o9'] < P['l_d1']] = 0  # abaixo
    add('93. Open drift vs D-1 range', 'discreto', drift, nclasses=3)
    
    # 94 Ret x volume
    add('94. Ret x volume (log)', 'continuo', np.sign(b9) * np.log(P['v9'] + 1))
    
    # 95 Volume x gap
    vol_alto_bin = (P['v9'] > P['v9_21_p66']).astype(int)
    gap_alto_bin = (gap_abs > gap_abs.median()).astype(int)
    vol_gap = vol_alto_bin * 2 + gap_alto_bin
    add('95. Volume x gap interacao', 'discreto', vol_gap, nclasses=4)
    
    # 96 Range x body energia
    energia = r9 * (1 - abs(body_ratio - 0.5) * 2)
    add('96. Range x body energia', 'continuo', energia)
    
    # 97 Body score direcional
    add('97. Body score direcional', 'continuo', b9 * (P['v9'] / VOL_P50[0]))
    
    # ==============================
    # XV. Eventos BR (98-100)
    # ==============================
    
    # 98 Semana COPOM (reunioes 8x/ano: jan, mar, mai, jun, jul, set, nov, dez)
    # 3a ou 4a semana do mes aproximadamente
    copom_months = [1, 3, 5, 6, 7, 9, 11, 12]
    copom_week = (dates.dt.month.isin(copom_months) & (week_of_month >= 3)).astype(int)
    add('98. Semana COPOM', 'binario', copom_week)
    
    # 99 Payroll week (primeira sexta do mes)
    # Sexta = dayofweek 4
    first_friday = dates.map(lambda d: d.day <= 7 and d.dayofweek == 4).astype(int)
    add('99. Payroll week (1a sexta)', 'binario', first_friday)
    
    # 100 Pos-vencimento (terca + quarta da 3a semana)
    pos_exp = (dte <= 2).astype(int)
    add('100. Pos-vencimento (<=2d apos)', 'binario', pos_exp)
    
    return pd.DataFrame(results)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--save', action='store_true', help='Salva CSV')
    args = parser.parse_args()
    
    print("Carregando dados...")
    df = load_csv()
    print(f"Total de candles: {len(df):,}")
    
    print("Montando dataset 9:00 + 9:01 + D-1...")
    ds = build_dataset(df)
    print(f"Dias alinhados: {len(ds)}")
    
    print("Calculando stats rolantes...")
    ds = compute_rolling_stats(ds)
    
    print("Testando preditores...")
    results = compute_predictors(ds)
    
    # Ordena por p-valor
    results = results.sort_values('p_valor')
    
    print("\n" + "="*120)
    print(f"{'Resultados — Radiografia H140: 100 preditores de 9:00 vs 9:01':^120}")
    print(f"{'Dados: ' + str(len(ds)) + ' dias':^120}")
    print("="*120)
    print(f"{'#':>4} {'Preditor':<40} {'Tipo':<12} {'N':>5} {'Acuracia':>9} {'Media(pts)':>10} {'p-valor':>8} {'Info':<30}")
    print("-"*120)
    
    for i, row in results.iterrows():
        p_str = f"{row['p_valor']:.4f}" if row['p_valor'] < 1 else "1.0000"
        print(f"{results.index.get_loc(i)+1:>4} {row['preditor']:<40} {row['tipo']:<12} {row['n']:>5} {row['acuracia']:>8.1f}% {row['media_pts']:>+9.1f} {p_str:>8} {row['info']:<30}")
    
    print("-"*120)
    
    # Estatisticas
    sig05 = (results['p_valor'] < 0.05).sum()
    sig01 = (results['p_valor'] < 0.01).sum()
    sig001 = (results['p_valor'] < 0.001).sum()
    print(f"\nSignificantes a p<0.05: {sig05}/100")
    print(f"Significantes a p<0.01: {sig01}/100")
    print(f"Significantes a p<0.001: {sig001}/100")
    print(f"(Esperado por acaso a p<0.05: ~5/100)")
    
    if args.save:
        results.to_csv("radiografia_h140_resultados.csv", index=False)
        print("\nResultados salvos em radiografia_h140_resultados.csv")

if __name__ == "__main__":
    main()
