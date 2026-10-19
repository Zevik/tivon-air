"""Validation against the 2022 and 2023 Association annual reports (found on envihaifa.org.il/דוחות-שנתיים)."""
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
# official: (mean, max daily, days>37.5, availability)
PM = {('Tivon', 2022): (16.9, 89.9, 8, 99), ('Ata', 2022): (19.1, 69.4, 18, 96), ('Tivon', 2023): (15.4, 37.4, 0, 98), ('Ata', 2023): (17.0, 42.8, 4, 94)}
rows = []
for (st, y), (om, ox, od, oa) in PM.items():
    p = S[st]['PM2.5']
    py = p[p.index.year == y]
    d = py.resample('D').agg(['mean', 'count'])
    d = d[d['count'] >= 18]
    rows.append(dict(st=st, year=y, off_mean=om, feed_mean=round(py.mean(), 2), diff=round(py.mean() - om, 2), off_maxd=ox, feed_maxd=round(d['mean'].max(), 1), off_days=od, feed_days=int((d['mean'] > 37.5).sum()), off_av=oa, feed_av=round(100 * py.notna().mean())))
print('PM2.5'); print(pd.DataFrame(rows).to_string(index=False))
# PM10 Tivon 2022 (35.3, 451.1, 8 ,99) and 2023 (27.8,110.1,0,98)
for y, om, ox in [(2022, 35.3, 451.1), (2023, 27.8, 110.1)]:
    p = S['Tivon']['PM10']
    py = p[p.index.year == y]
    d = py.resample('D').agg(['mean', 'count'])
    d = d[d['count'] >= 18]
    print('PM10 Tivon', y, 'off', om, ox, '| feed', round(py.mean(), 1), round(d['mean'].max(), 1))
# NO2 official: Tivon 2022 7.4 (95), 2023 6.6 (96.8); Ata 2022 10.0 (95), 2023 9.3 (96.6)
F = 46.0055 / 24.4655
rows = []
for (st, y), (om, oa) in {('Tivon', 2022): (7.4, 95), ('Tivon', 2023): (6.6, 96.8), ('Ata', 2022): (10.0, 95), ('Ata', 2023): (9.3, 96.6)}.items():
    n = S[st]['NO2'] * F
    ny = n[n.index.year == y]
    rows.append(dict(st=st, year=y, off=om, feed25=round(ny.mean(), 2), ratio=round(om / ny.mean(), 3), off_av=oa, feed_av=round(100 * ny.notna().mean())))
print('NO2'); print(pd.DataFrame(rows).to_string(index=False))
# O3: Tivon 2022 70.3/128.4/0/100 ; 2023 72.2/128.3/0/96.7 ; Ata 2022 69.4/127.9/0/97 ; 2023 75.0/129.2/0/97.0
O3 = {('Tivon', 2022): (70.3, 128.4, 0, 100), ('Tivon', 2023): (72.2, 128.3, 0, 96.7), ('Ata', 2022): (69.4, 127.9, 0, 97), ('Ata', 2023): (75.0, 129.2, 0, 97.0)}
rows = []
for (st, y), (om, ox, oc, oa) in O3.items():
    o = S[st]['O3'] * 48 / 24.4655
    r = o.rolling(8, min_periods=6).mean()
    g = pd.DataFrame({'r': r}).groupby(r.index.normalize()).agg(m=('r', 'max'), n=('r', 'count'))
    g = g[(g.n >= 18) & (g.index.year == y)]
    oy = o[o.index.year == y]
    rows.append(dict(st=st, year=y, off_mean=om, feed25_mean=round(oy.mean(), 1), mean_ratio=round(om / oy.mean(), 3), off_max8=ox, feed25_max8=round(g.m.max(), 1), max_ratio=round(ox / g.m.max(), 3), off_days140=oc,
                     feed25_days140=int((g.m > 140).sum()), off_av=oa, feed_av=round(100 * oy.notna().mean())))
print('O3'); print(pd.DataFrame(rows).to_string(index=False))
