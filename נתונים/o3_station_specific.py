"""Days MDA8>100/>140 using each station's OFFICIAL-EQUIVALENT conversion (ratio official/feed measured against official tables, see validate_*.py)
versus the common 25C conversion. Tivon 1.886 (ratio 0.961), Ata 1.934 (0.986), Afula 1.950 (0.994)."""
import sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
IDX = pd.date_range('2021-01-01 00:00', '2026-10-17 09:00', freq='h')


def load(f):
    L = pd.read_csv(f)
    L['t'] = pd.to_datetime(L.datetime.str[:19])
    L.loc[~L.valid, 'value'] = np.nan
    return L.pivot_table(index='t', columns='channel', values='value', aggfunc='first').reindex(IDX)['O3']


FILES = {'Tivon': ('tivon_hourly_long_2021-2026.csv', 1.886), 'Ata': ('kataa_st88_hourly_2021-2026.csv', 1.934), 'Afula': ('afula_st1_hourly_2021-2026.csv', 1.950)}


def mda8(s):
    r = s.rolling(8, min_periods=6).mean()
    g = pd.DataFrame({'r': r}).groupby(r.index.normalize()).agg(m=('r', 'max'), n=('r', 'count'))
    return g[g.n >= 18]['m']


res = {}
for st, (f, fo) in FILES.items():
    o = load(f)
    for lab, fac in [('official-equiv', fo), ('25C', 1.9618), ('20C', 1.9954)]:
        m = mda8(o * fac)
        res[(st, lab)] = m
print('days MDA8>100 per year (valid days in brackets for official-equiv):')
for lab in ['official-equiv', '25C', '20C']:
    print('--', lab)
    for st in FILES:
        m = res[(st, lab)]
        print(f'{st:6s}', {y: int((m[m.index.year == y] > 100).sum()) for y in range(2021, 2027)}, '| mean 2021-25 per yr', round(sum((m[m.index.year == y] > 100).sum() for y in range(2021, 2026)) / 5, 1))
print('\ndays MDA8>140 per year:')
for lab in ['official-equiv', '25C', '20C']:
    print('--', lab)
    for st in FILES:
        m = res[(st, lab)]
        print(f'{st:6s}', {y: int((m[m.index.year == y] > 140).sum()) for y in range(2021, 2027)})
print('\nmean of daily MDA8 in JJA, 2021-2025, official-equiv / 25C:')
for st in FILES:
    a = res[(st, 'official-equiv')]
    b = res[(st, '25C')]
    sel = lambda m: m[(m.index.year <= 2025) & m.index.month.isin([6, 7, 8])].mean()
    print(st, round(sel(a), 1), round(sel(b), 1))
print('\nmax MDA8 per year official-equiv:')
for st in FILES:
    m = res[(st, 'official-equiv')]
    print(st, {y: round(m[m.index.year == y].max(), 1) for y in range(2021, 2027)})
# WHO peak-season metric (6 consecutive months), official-equiv vs 25C, Tivon
for lab in ['official-equiv', '25C']:
    m = res[('Tivon', lab)]
    mm = m.groupby([m.index.year, m.index.month]).mean()
    mm.index = pd.PeriodIndex([pd.Period(f'{a}-{b:02d}') for a, b in mm.index], freq='M')
    m6 = mm.rolling(6).mean()
    out = {}
    for y in range(2021, 2027):
        sub = m6[(m6.index >= pd.Period(f'{y}-06')) & (m6.index <= pd.Period(f'{y}-12'))]
        if len(sub):
            out[y] = round(sub.max(), 1)
    print('Tivon peak-season (max 6-month mean of monthly mean MDA8)', lab, out)
# p99 per year
for lab in ['official-equiv', '25C']:
    m = res[('Tivon', lab)]
    print('Tivon p99 MDA8', lab, {y: round(m[m.index.year == y].quantile(.99), 1) for y in range(2021, 2027)})
# Tivon annual hourly peak JJA official-equiv vs 25C
o = load(FILES['Tivon'][0])
for lab, fac in [('official-equiv', 1.886), ('25C', 1.9618)]:
    print('Tivon JJA peak hourly', lab, {y: round((o * fac)[(o.index.year == y) & o.index.month.isin([6, 7, 8])].max(), 1) for y in range(2021, 2027)},
          '| year peak', {y: round((o * fac)[o.index.year == y].max(), 1) for y in range(2021, 2027)})
