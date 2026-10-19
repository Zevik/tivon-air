import sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
L = pd.read_csv('tivon_hourly_long_2021-2026.csv')
L['t'] = pd.to_datetime(L.datetime.str[:19])
L.loc[~L.valid, 'value'] = np.nan
W = L.pivot_table(index='t', columns='channel', values='value', aggfunc='first')
W = W.reindex(pd.date_range(W.index.min(), W.index.max(), freq='h'))
f = 46.0055 / (0.082057 * 298.15)
no2 = W['NO2'] * f
print('NO2 annual mean ug/m3 (nominal 25C):', no2.groupby(no2.index.year).mean().round(1).to_dict())
print('NO2 annual mean x0.965:', (no2 * 0.965).groupby(no2.index.year).mean().round(1).to_dict())
print('NO2 coverage:', no2.groupby(no2.index.year).apply(lambda s: round(s.notna().mean(), 3)).to_dict())
m = no2.groupby(no2.index.month).mean().round(1)
print('NO2 by month (all yrs):', m.to_dict())
print('PM2.5 winter (DJF) mean / summer (JJA) mean:', round(W.loc[W.index.month.isin([12, 1, 2]), 'PM2.5'].mean(), 2), round(W.loc[W.index.month.isin([6, 7, 8]), 'PM2.5'].mean(), 2))
print('channels:', list(W.columns))
