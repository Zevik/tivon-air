"""O3 WHO-2021 metrics at the textbook 25C factor and at a factor calibrated to the ministry's published monthly means (x0.965)."""
import sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 220)
L = pd.read_csv('tivon_hourly_long_2021-2026.csv')
L['t'] = pd.to_datetime(L.datetime.str[:19])
L.loc[~L.valid, 'value'] = np.nan
W = L.pivot_table(index='t', columns='channel', values='value', aggfunc='first')
W = W.reindex(pd.date_range(W.index.min(), W.index.max(), freq='h'))
F25 = 48.0 / (0.082057 * 298.15)

for scale, lab in [(1.0, 'NOMINAL (25C, 1.962 ug/m3 per ppb)'), (0.965, 'CALIBRATED to ministry monthly means (x0.965 = 1.893)')]:
    o = W['O3'] * F25 * scale
    r8 = o.rolling(8, min_periods=6).mean()
    D = pd.DataFrame({'r8': r8, 'o': o})
    D['date'] = D.index.normalize()
    g = D.groupby('date').agg(mda8=('r8', 'max'), n=('r8', 'count'), peak=('o', 'max'))
    g = g[g.n >= 18]
    print('\n####', lab)
    rows = []
    for y, d in g.groupby(g.index.year):
        jja = o[(o.index.year == y) & (o.index.month.isin([6, 7, 8]))]
        rows.append(dict(year=y, valid_days=len(d), gt100=int((d.mda8 > 100).sum()), pct_days=round(100 * (d.mda8 > 100).mean(), 1),
                         gt140=int((d.mda8 > 140).sum()), max_mda8=round(d.mda8.max(), 1), p99=round(d.mda8.quantile(.99), 1),
                         peak_hour_year=round(d.peak.max(), 1), peak_hour_JJA=round(jja.max(), 1), JJA_when=str(jja.idxmax()),
                         annual_mean=round(o[o.index.year == y].mean(), 1)))
    print(pd.DataFrame(rows).to_string(index=False))
    mm = g.groupby([g.index.year, g.index.month]).mda8.mean()
    mm.index = pd.PeriodIndex([pd.Period(f'{a}-{b:02d}') for a, b in mm.index], freq='M')
    m6 = mm.rolling(6).mean()
    ps = {}
    for y in range(2021, 2027):
        sub = m6[(m6.index >= pd.Period(f'{y}-06')) & (m6.index <= pd.Period(f'{y}-12'))]
        if len(sub):
            ps[y] = (round(sub.max(), 1), str(sub.idxmax()))
    print('peak-season (6-mo max mean MDA8):', ps)
    tot = g[g.index.year <= 2025]
    print('2021-2025 pooled: days', len(tot), '>100:', int((tot.mda8 > 100).sum()), 'avg/yr', round((tot.mda8 > 100).sum() / 5, 1))
