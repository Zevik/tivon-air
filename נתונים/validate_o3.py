"""Cross-check of API-derived O3 vs published monthly reports + sensitivity of WHO day counts to the ppb->ug factor."""
import sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
L = pd.read_csv('tivon_hourly_long_2021-2026.csv')
L['t'] = pd.to_datetime(L.datetime.str[:19])
L.loc[~L.valid, 'value'] = np.nan
W = L.pivot_table(index='t', columns='channel', values='value', aggfunc='first')
W = W.reindex(pd.date_range(W.index.min(), W.index.max(), freq='h'))
F25 = 48.0 / (0.082057 * 298.15)

pub = {'2023-06': (80.2, 117.3), '2024-07': (86.6, 118.6), '2024-08': (83.3, 127.7), '2023-12': (53.3, 78.6), '2024-12': (59.5, 86.9)}
print('Monthly: published (mean, max 8h) vs API-derived @25C')
for k, (pm, px) in pub.items():
    o = W['O3'] * F25
    r = o.rolling(8, min_periods=6).mean()
    m = o[k].mean(), r[k].max()
    print(k, 'pub', pm, px, '| api %.1f %.1f' % m, '| ratio %.3f %.3f' % (m[0] / pm, m[1] / px))

# 2021 detail around the two published exceedances
r = (W['O3'] * F25).rolling(8, min_periods=6).mean()
print('\n2021-08-06 16:00 =', round(r['2021-08-06 16:00'], 1), '(pub 145.5);  2021-08-07 16:00 =', round(r['2021-08-07 16:00'], 1), '(pub 150.7)')

# sensitivity of days>100 to scale
print('\nDays with MDA8 > 100 under scale factors (1.00 = 25C factor 1.962; 0.96 = matches 2021 report at peak):')
for scale in [1.0, 0.98, 0.96, 0.93]:
    o = W['O3'] * F25 * scale
    r8 = o.rolling(8, min_periods=6).mean()
    D = pd.DataFrame({'r8': r8})
    D['date'] = D.index.normalize()
    g = D.groupby('date').agg(mda8=('r8', 'max'), n=('r8', 'count'))
    g = g[g.n >= 18]
    print(scale, g.groupby(g.index.year).apply(lambda d: int((d.mda8 > 100).sum())).to_dict(),
          '| >140:', g.groupby(g.index.year).apply(lambda d: int((d.mda8 > 140).sum())).to_dict())

# day counting with full-hour (all 24 windows incl. previous-day hours) and 'WHO strict' variants
o = W['O3'] * F25
for minp, lab in [(8, 'strict 8/8'), (6, '6/8')]:
    r8 = o.rolling(8, min_periods=minp).mean()
    D = pd.DataFrame({'r8': r8})
    D['date'] = D.index.normalize()
    g = D.groupby('date').agg(mda8=('r8', 'max'), n=('r8', 'count'))
    g = g[g.n >= 18]
    print(lab, g.groupby(g.index.year).apply(lambda d: int((d.mda8 > 100).sum())).to_dict())
# including values flagged invalid
L2 = pd.read_csv('tivon_hourly_long_2021-2026.csv')
L2['t'] = pd.to_datetime(L2.datetime.str[:19])
W2 = L2.pivot_table(index='t', columns='channel', values='value', aggfunc='first')
W2 = W2.reindex(pd.date_range(W2.index.min(), W2.index.max(), freq='h'))
r8 = (W2['O3'] * F25).rolling(8, min_periods=6).mean()
D = pd.DataFrame({'r8': r8})
D['date'] = D.index.normalize()
g = D.groupby('date').agg(mda8=('r8', 'max'), n=('r8', 'count'))
print('if flagged-invalid hours were kept:', g.groupby(g.index.year).apply(lambda d: int((d.mda8 > 100).sum())).to_dict())
