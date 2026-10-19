"""Official annual-report values (Haifa Bay Association) vs API-derived annual statistics, Tivon and Kiryat Ata: PM2.5, NO2, O3 (no fitted factors)."""
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


S = {'Tivon': load('tivon_hourly_long_2021-2026.csv'), 'Ata': load('kataa_st88_hourly_2021-2026.csv')}
F_NO2 = 46.0055 / (0.082057 * 298.15)
F_O3 = 48.0 / (0.082057 * 298.15)

# official PM2.5: (annual mean, max daily or None, days>37.5, availability or None, source)
PM_OFF = {('Tivon', 2021): (15.6, 74.9, 2, 98, 'annual 2021 Table'), ('Tivon', 2023): (14, None, 0, None, 'annual 2024 trend table (rounded)'),
          ('Tivon', 2024): (15.4, 40.3, 1, 96, 'annual 2024 Table 20'), ('Tivon', 2025): (14.5, 40.6, 3, 99, 'annual 2025 Table 22'),
          ('Ata', 2021): (19.4, 73.6, 4, 92, 'annual 2021 Table'), ('Ata', 2023): (18, None, 4, None, 'annual 2024 trend table (rounded)'),
          ('Ata', 2024): (14.5, 46, 1, 70, 'annual 2024 Table 20'), ('Ata', 2025): (17.2, 58.1, 4, 65, 'annual 2025 Table 22')}
rows = []
for (st, y), (om, ox, od, oa, src) in PM_OFF.items():
    p = S[st]['PM2.5']
    py = p[p.index.year == y]
    d = py.resample('D').agg(['mean', 'count'])
    d = d[d['count'] >= 18]
    rows.append(dict(st=st, year=y, off_mean=om, feed_mean=round(py.mean(), 2), diff=round(py.mean() - om, 2), off_maxd=ox, feed_maxd=round(d['mean'].max(), 1), off_days=od,
                     feed_days=int((d['mean'] > 37.5).sum()), off_avail=oa, feed_avail=round(100 * py.notna().mean()), src=src))
print('PM2.5 official vs feed:'); print(pd.DataFrame(rows).to_string(index=False))

# NO2 official (annual mean, availability): Tivon 2021 9.2/95, 2024 8.3/95, 2025 9.1/86 ; Ata 2021 11.6/91, 2025 11.9/85
NO2_OFF = {('Tivon', 2021): (9.2, 95), ('Tivon', 2024): (8.3, 95), ('Tivon', 2025): (9.1, 86), ('Ata', 2021): (11.6, 91), ('Ata', 2025): (11.9, 85)}
rows = []
for (st, y), (om, oa) in NO2_OFF.items():
    n = S[st]['NO2'] * F_NO2
    ny = n[n.index.year == y]
    rows.append(dict(st=st, year=y, off_mean=om, feed_mean_25C=round(ny.mean(), 2), ratio=round(om / ny.mean(), 3), off_avail=oa, feed_avail=round(100 * ny.notna().mean())))
print('\nNO2 official vs feed (25C):'); print(pd.DataFrame(rows).to_string(index=False))

# O3 Tivon official: 2018 66/133/0, 2019 66/130/0, 2020 66/159/2 (not in feed period); 2021 70.3/147.7/2/99 ; 2024 71.8/127.7/0/100 ; 2025 76.0/150/3/100
O3_OFF = {2021: (70.3, 147.7, 2, 99), 2024: (71.8, 127.7, 0, 100), 2025: (76.0, 150, 3, 100)}
o = S['Tivon']['O3'] * F_O3
r = o.rolling(8, min_periods=6).mean()
g = pd.DataFrame({'r': r}).groupby(r.index.normalize()).agg(m=('r', 'max'), n=('r', 'count'))
g = g[g.n >= 18]
rows = []
for y, (om, ox, oc, oa) in O3_OFF.items():
    oy = o[o.index.year == y]
    gy = g[g.index.year == y]
    rows.append(dict(year=y, off_mean=om, feed_mean_25C=round(oy.mean(), 1), mean_ratio=round(om / oy.mean(), 3), off_max8=ox, feed_max8_25C=round(gy.m.max(), 1), max_ratio=round(ox / gy.m.max(), 3),
                     off_days140=oc, feed_days140_25C=int((gy.m > 140).sum()), feed_days140_if_x0_96=int((gy.m * 0.96 > 140).sum())))
print('\nO3 Tivon official vs feed (25C):'); print(pd.DataFrame(rows).to_string(index=False))
