"""Co-occurrence of days with MDA8>100 across Tivon, Ata, Afula under (a) common 25C and (b) station-specific official-equivalent conversions. 2021-2025, days valid in all three."""
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


def mda8(s):
    r = s.rolling(8, min_periods=6).mean()
    g = pd.DataFrame({'r': r}).groupby(r.index.normalize()).agg(m=('r', 'max'), n=('r', 'count'))
    return g[g.n >= 18]['m']


O = {'Tivon': load('tivon_hourly_long_2021-2026.csv'), 'Ata': load('kataa_st88_hourly_2021-2026.csv'), 'Afula': load('afula_st1_hourly_2021-2026.csv')}
for lab, fac in [('25C common', {'Tivon': 1.9618, 'Ata': 1.9618, 'Afula': 1.9618}), ('official-equivalent', {'Tivon': 1.886, 'Ata': 1.934, 'Afula': 1.950})]:
    J = pd.DataFrame({k: mda8(O[k] * fac[k]) for k in O}).dropna()
    J = J[J.index.year <= 2025]
    print('\n###', lab, 'days', len(J))
    for a, b in [('Tivon', 'Afula'), ('Tivon', 'Ata'), ('Ata', 'Afula')]:
        print(f'P({b}>100 | {a}>100) = {(J[b][J[a] > 100] > 100).mean():.3f}; corr = {J[a].corr(J[b]):.3f}')
    print('Tivon>100 days:', int((J.Tivon > 100).sum()), '| all three', int(((J > 100).all(axis=1)).sum()), '| Tivon only', int(((J.Tivon > 100) & (J.Afula <= 100) & (J.Ata <= 100)).sum()),
          '| Afula only', int(((J.Afula > 100) & (J.Tivon <= 100) & (J.Ata <= 100)).sum()), '| Ata only', int(((J.Ata > 100) & (J.Tivon <= 100) & (J.Afula <= 100)).sum()))
