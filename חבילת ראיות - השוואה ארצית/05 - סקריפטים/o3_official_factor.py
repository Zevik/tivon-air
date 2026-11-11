"""Ozone/NO2 with the OFFICIAL ppb->ug/m3 factors (MoEP table 'ערכי סביבה לניטור רציף כולל מקדמים', Jan 2024,
sent by the Haifa Bay association in its reply of 11.2026): 25C and pressure by station elevation band.
O3: 0-50 m 1.96, 51-200 m 1.94, 201-400 m 1.90, 401-600 m 1.85. NO2: 1.88, 1.86, 1.82, 1.78.
Tivon station 137 is listed at 201 m -> band 201-400 (sensitivity: 1.94 if the 51-200 band is used).
Compares API x official factor with the published annual tables (values hard-coded from annual reports)."""
import sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
IDX = pd.date_range('2021-01-01 00:00', '2026-10-17 09:00', freq='h')
FILES = {'Tivon': 'tivon_hourly_long_2021-2026.csv', 'Ata': 'kataa_st88_hourly_2021-2026.csv', 'Afula': 'afula_st1_hourly_2021-2026.csv'}
ELEV = {'Tivon': 201, 'Ata': 44, 'Afula': 57}
O3F = {'Tivon': 1.90, 'Ata': 1.96, 'Afula': 1.94}
NO2F = {'Tivon': 1.82, 'Ata': 1.88, 'Afula': 1.86}
OFF_O3_MEAN = {'Tivon': {2021: 70.3, 2022: 70.3, 2023: 72.2, 2024: 71.8, 2025: 76.0},
               'Ata': {2021: 65.7, 2022: 69.4, 2023: 75.0, 2024: 81.5, 2025: 77.3}}
OFF_O3_GT140 = {'Tivon': {2021: 2, 2022: 0, 2023: 0, 2024: 0, 2025: 3}}
OFF_O3_MAX8 = {'Tivon': {2021: 147.7, 2022: 128.4, 2023: 128.3, 2024: 127.7, 2025: 150.0}}
OFF_NO2_MEAN = {'Tivon': {2021: 9.2, 2022: 7.4, 2023: 6.6, 2024: 8.3, 2025: 9.1}}


def load(f):
    L = pd.read_csv(f)
    L['t'] = pd.to_datetime(L.datetime.str[:19])
    L.loc[~L.valid, 'value'] = np.nan
    return L.pivot_table(index='t', columns='channel', values='value', aggfunc='first').reindex(IDX)


def mda8(s):
    r = s.rolling(8, min_periods=6).mean()
    g = pd.DataFrame({'r': r}).groupby(r.index.normalize()).agg(m=('r', 'max'), n=('r', 'count'))
    return g[g.n >= 18]['m']


D = {st: load(f) for st, f in FILES.items()}
print('Official factors used:', {s: (ELEV[s], O3F[s], NO2F[s]) for s in FILES})

print('\n=== Tivon: API x official factor vs published annual tables ===')
o = D['Tivon']['O3']
for fac in [1.90, 1.94]:
    m = mda8(o * fac)
    print(f'\n-- O3 factor {fac}')
    print('year | mean API | mean official | ratio | max8 API | max8 official | >140 API | >140 official | >100 API')
    for y in range(2021, 2026):
        oy = o[o.index.year == y] * fac
        my = m[m.index.year == y]
        print(y, '|', round(oy.mean(), 1), '|', OFF_O3_MEAN['Tivon'][y], '|', round(OFF_O3_MEAN['Tivon'][y] / oy.mean(), 3), '|',
              round(my.max(), 1), '|', OFF_O3_MAX8['Tivon'][y], '|', int((my > 140).sum()), '|', OFF_O3_GT140['Tivon'][y], '|', int((my > 100).sum()))
    print('2026 (to 17.10) >100:', int((m[m.index.year == 2026] > 100).sum()), ' >140:', int((m[m.index.year == 2026] > 140).sum()))
    print('mean days>100 2021-2025:', round(np.mean([(m[m.index.year == y] > 100).sum() for y in range(2021, 2026)]), 1))

print('\n-- NO2 factor 1.82 (Tivon)')
n = D['Tivon']['NO2'] * 1.82
for y in range(2021, 2026):
    ny = n[n.index.year == y]
    print(y, 'API', round(ny.mean(), 2), 'official', OFF_NO2_MEAN['Tivon'][y], 'diff', round(OFF_NO2_MEAN['Tivon'][y] - ny.mean(), 2))

print('\n=== Ata: O3 annual mean, factor 1.96 (0-50 m) and 1.94 (51-200 m) ===')
a = D['Ata']['O3']
for fac in [1.96, 1.94]:
    print('factor', fac, {y: (round((a[a.index.year == y] * fac).mean(), 1), OFF_O3_MEAN['Ata'][y]) for y in range(2021, 2026)})

print('\n=== Days MDA8>100 per year, each station with its official factor ===')
rows = {}
for st in FILES:
    m = mda8(D[st]['O3'] * O3F[st])
    rows[st] = {y: int((m[m.index.year == y] > 100).sum()) for y in range(2021, 2027)}
    rows[st]['mean21-25'] = round(np.mean([rows[st][y] for y in range(2021, 2026)]), 1)
print(pd.DataFrame(rows).to_string())

print('\n=== Sensitivity: Ata with 1.94 (51-200 m band) ===')
m = mda8(D['Ata']['O3'] * 1.94)
d = {y: int((m[m.index.year == y] > 100).sum()) for y in range(2021, 2027)}
print(d, 'mean21-25', round(np.mean([d[y] for y in range(2021, 2026)]), 1))
