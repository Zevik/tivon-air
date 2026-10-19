"""Compare API-derived monthly ozone (mean, max 8h) and PM2.5 (mean, max daily) with the Ministry's monthly reports (6 months, 3 stations)."""
import sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 220)
IDX = pd.date_range('2021-01-01 00:00', '2026-10-17 09:00', freq='h')


def load(f):
    L = pd.read_csv(f)
    L['t'] = pd.to_datetime(L.datetime.str[:19])
    L.loc[~L.valid, 'value'] = np.nan
    return L.pivot_table(index='t', columns='channel', values='value', aggfunc='first').reindex(IDX)


S = {'Tivon': load('tivon_hourly_long_2021-2026.csv'), 'Ata': load('kataa_st88_hourly_2021-2026.csv'), 'Afula': load('afula_st1_hourly_2021-2026.csv')}
F = 48 / (0.082057 * 298.15)
# official monthly report values: (O3 max8h, O3 monthly mean, O3 avail%) ; (PM2.5 max daily, PM2.5 mean, avail%)
O3_OFF = {'2023-06': {'Afula': (124.4, 80.3, 100), 'Ata': (120.2, 85.0, 100), 'Tivon': (117.3, 80.2, 100)},
          '2023-10': {'Afula': (131.2, 73.4, 100), 'Ata': (123.8, 76.3, 98), 'Tivon': (115.5, 73.5, 99)},
          '2023-12': {'Afula': (83.0, 47.5, 100), 'Ata': (78.8, 56.8, 98), 'Tivon': (78.6, 53.3, 100)},
          '2024-07': {'Ata': (127.6, 96.5, 99), 'Tivon': (118.6, 86.6, 100)},          # Afula availability 32% in report
          '2024-08': {'Afula': (164.1, 94.9, 100), 'Ata': (130.3, 97.2, 100), 'Tivon': (127.7, 83.3, 100)},
          '2024-12': {'Afula': (95.4, 50.3, 100), 'Ata': (103.9, 70.8, 96), 'Tivon': (86.9, 59.5, 100)}}
PM_OFF = {'2023-06': {'Ata': (31.7, 15.6), 'Tivon': (26.0, 12.4)}, '2023-10': {'Ata': (35.6, 18.1), 'Tivon': (29.5, 16.2)},
          '2023-12': {'Ata': (32.10, 18.82), 'Tivon': (32.24, 19.34)}, '2024-08': {'Ata': (21.01, 15.10), 'Tivon': (16.51, 11.77)},
          '2024-12': {'Ata': (37.14, 20.61), 'Tivon': (40.29, 19.70)}, '2024-07': {'Tivon': (17.48, 12.65)}}


def m8max(o, mo):
    r = o.rolling(8, min_periods=6).mean()
    return r[mo].max()


rows = []
for mo, d in O3_OFF.items():
    for st, (mx, mean, av) in d.items():
        o = S[st]['O3'] * F
        rows.append(dict(month=mo, st=st, off_max8=mx, feed_max8=round(m8max(o, mo), 1), max_ratio=round(mx / m8max(o, mo), 3), off_mean=mean, feed_mean=round(o[mo].mean(), 1),
                         mean_ratio=round(mean / o[mo].mean(), 3), off_avail=av, feed_avail=round(100 * o[mo].notna().mean())))
R = pd.DataFrame(rows)
print('OZONE monthly (feed at 25C, no scale factor):'); print(R.to_string(index=False))
print(R.groupby('st')[['max_ratio', 'mean_ratio']].agg(['mean', 'min', 'max']).round(3))
print('\nPM2.5 monthly:')
rows = []
for mo, d in PM_OFF.items():
    for st, (mx, mean) in d.items():
        p = S[st]['PM2.5']
        dm = p[mo].resample('D').agg(['mean', 'count'])
        dm = dm[dm['count'] >= 18]
        rows.append(dict(month=mo, st=st, off_maxdaily=mx, feed_maxdaily=round(dm['mean'].max(), 1), off_mean=mean, feed_mean=round(p[mo].mean(), 2), mean_diff=round(p[mo].mean() - mean, 2)))
print(pd.DataFrame(rows).to_string(index=False))
# Afula exceedances Aug 2024
o = S['Afula']['O3'] * F
r = o.rolling(8, min_periods=6).mean()
d = r['2024-08'].resample('D').max()
print('\nAfula Aug 2024 days MDA8>140 (25C):', int((d > 140).sum()), '| official reports 2 exceedances, max 164.1')
