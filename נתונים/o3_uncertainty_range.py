"""Day-count uncertainty range for ozone MDA8>100 and >140 (ug/m3) under explicit ppb->ug/m3 options. No fitted scale factor.
Options: 1.840 (lowest station-year implied by official reports, Carmel Park 2025), 1.886 (Tivon implied by official 2021 and 2025 means),
1.962 (25C, 1 atm), 1.995 (20C, 1 atm)."""
import sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
IDX = pd.date_range('2021-01-01 00:00', '2026-10-17 09:00', freq='h')


def load(f, keep_invalid=False):
    L = pd.read_csv(f)
    L['t'] = pd.to_datetime(L.datetime.str[:19])
    if not keep_invalid:
        L.loc[~L.valid, 'value'] = np.nan
    return L.pivot_table(index='t', columns='channel', values='value', aggfunc='first').reindex(IDX)['O3']


FILES = {'Tivon': 'tivon_hourly_long_2021-2026.csv', 'Ata': 'kataa_st88_hourly_2021-2026.csv', 'Afula': 'afula_st1_hourly_2021-2026.csv'}
FACT = [1.840, 1.886, 1.962, 1.995]


def mda8(s):
    r = s.rolling(8, min_periods=6).mean()
    g = pd.DataFrame({'r': r}).groupby(r.index.normalize()).agg(m=('r', 'max'), n=('r', 'count'))
    return g[g.n >= 18]['m']


rows = []
for st, f in FILES.items():
    o = load(f)
    for fac in FACT:
        m = mda8(o * fac)
        for y in range(2021, 2027):
            my = m[m.index.year == y]
            rows.append(dict(st=st, f=fac, year=y, days=len(my), gt100=int((my > 100).sum()), gt140=int((my > 140).sum()), max8=round(my.max(), 1)))
R = pd.DataFrame(rows)
for st in FILES:
    print('\n#####', st)
    print('days > 100:'); print(R[R.st == st].pivot(index='year', columns='f', values='gt100').to_string())
    print('days > 140:'); print(R[R.st == st].pivot(index='year', columns='f', values='gt140').to_string())
    print('valid days:', R[(R.st == st) & (R.f == 1.962)].set_index('year').days.to_dict())
    p = R[(R.st == st) & (R.year <= 2025)].groupby('f').gt100.sum() / 5
    print('mean days>100 per year 2021-2025 by factor:', p.round(1).to_dict())
# ranking robustness: Afula vs Tivon vs Ata, same factor
P = R[(R.year <= 2025)].groupby(['st', 'f']).gt100.sum().unstack('st') / 5
print('\nMean days>100/yr 2021-2025, by factor (rows) and station (cols):'); print(P.round(1).to_string())
# QA sensitivity: keep values flagged invalid by the network (Tivon)
o_all = load(FILES['Tivon'], keep_invalid=True)
for fac in [1.886, 1.962]:
    m = mda8(o_all * fac)
    print(f'Tivon incl. flagged-invalid hours, f={fac}:', {y: int((m[m.index.year == y] > 100).sum()) for y in range(2021, 2027)})
# window rule sensitivity: >=6 of 8 vs strict 8 of 8 hours
o = load(FILES['Tivon'])
for minp in [6, 8]:
    r = (o * 1.962).rolling(8, min_periods=minp).mean()
    g = pd.DataFrame({'r': r}).groupby(r.index.normalize()).agg(m=('r', 'max'), n=('r', 'count'))
    g = g[g.n >= 18]
    print(f'Tivon f=1.962 min_periods={minp}:', {y: int((g.m[g.index.year == y] > 100).sum()) for y in range(2021, 2027)}, 'valid days', len(g))
