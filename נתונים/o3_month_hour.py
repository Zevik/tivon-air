"""Tivon ozone distribution by month and hour (official-equivalent factor 1.886 and standard 25C 1.962), 2021-2025."""
import sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 200)
IDX = pd.date_range('2021-01-01 00:00', '2026-10-17 09:00', freq='h')
L = pd.read_csv('tivon_hourly_long_2021-2026.csv')
L['t'] = pd.to_datetime(L.datetime.str[:19])
L.loc[~L.valid, 'value'] = np.nan
o = L.pivot_table(index='t', columns='channel', values='value', aggfunc='first').reindex(IDX)['O3']
for lab, f in [('official-equivalent 1.886', 1.886), ('standard 25C 1.962', 1.962)]:
    x = o * f
    r = x.rolling(8, min_periods=6).mean()
    D = pd.DataFrame({'r': r}).groupby(r.index.normalize()).agg(m=('r', 'max'), n=('r', 'count'))
    D = D[(D.n >= 18) & (D.index.year <= 2025)]
    print('\n####', lab)
    tab = pd.DataFrame({'mean_MDA8': D.m.groupby(D.index.month).mean().round(0), 'days_gt100_per_yr': (D.m > 100).groupby(D.index.month).sum() / 5, 'valid_days': D.m.groupby(D.index.month).size()})
    print(tab.round(1).T.to_string())
    xs = x[x.index.year <= 2025]
    prof = xs.groupby([xs.index.month.isin([6, 7, 8]), xs.index.hour]).mean().unstack(0)
    prof.columns = ['non-JJA', 'JJA']
    print('mean hourly O3 by hour (UTC+2), JJA and rest:'); print(prof.round(0).T.to_string())
    r2 = r[r.index.year <= 2025]
    ex = r2[r2 > 100]
    print('end-hour distribution of 8h windows >100 (UTC+2):', ex.index.hour.value_counts().sort_index().to_dict())
