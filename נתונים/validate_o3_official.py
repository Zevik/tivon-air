"""Compare API-derived ozone with official Haifa Bay Association annual-report tables (2021: Table 15/16; 2025: Table 18),
station by station, WITHOUT any fitted scale factor. Reports the implied ppb->ug/m3 factor per station-year."""
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
    return L.pivot_table(index='t', columns='channel', values='value', aggfunc='first').reindex(IDX)['O3']


FILES = {137: 'tivon_hourly_long_2021-2026.csv', 88: 'kataa_st88_hourly_2021-2026.csv', 69: 'carmelpark_st69_hourly_2021-2026.csv'}
for sid in [86, 87, 90, 92, 93, 96, 98, 382]:
    FILES[sid] = f'val/st{sid}_2021_2025.csv'
O3 = {sid: load(f) for sid, f in FILES.items()}
NAME = {137: 'Tivon', 88: 'Ata', 69: 'CarmelPark', 86: 'NeveShanan', 87: 'Nesher', 90: 'Einstein', 92: 'Yam', 93: 'Shprintzak', 96: 'Igud(CheckPost)', 98: 'KfarHasidim', 382: 'Motzkin(NeveGanim)'}

# official: (annual mean, max 8h, number of days >140, availability %)
OFF = {2021: {96: (68, 160.4, 2, 98), 90: (84.6, 145.9, 1, 99), 86: (82.7, 152.7, 1, 99), 69: (88.6, 153.1, 3, 88), 88: (65.7, 139.1, 0, 97), 137: (70.3, 147.7, 2, 99),
              92: (77.3, 163.9, 3, 74), 382: (65.4, 133.6, 0, 99), 93: (85.6, 150.5, 1, 99), 87: (76.2, 138.1, None, None)},
       2025: {96: (73.7, 147, 1, 99), 90: (88.3, 154, 5, 96), 86: (85.2, 156, 5, 98), 69: (87.7, 145, 4, 93), 88: (77.3, 132, 0, 94), 137: (76.0, 150, 3, 100),
              92: (74.6, 142, 1, 95), 382: (71.2, 156, 3, 97), 93: (83.4, 161, 3, 100)}}


def mda8(s):
    r = s.rolling(8, min_periods=6).mean()
    g = pd.DataFrame({'r': r}).groupby(r.index.normalize()).agg(m=('r', 'max'), n=('r', 'count'))
    return g[g.n >= 18]['m']


rows = []
for y, tab in OFF.items():
    for sid, (om, ox, oc, oa) in tab.items():
        ppb = O3[sid][O3[sid].index.year == y]
        if ppb.notna().sum() < 1000:
            continue
        fm = ppb.mean()
        f_impl = om / fm
        for lab, fac in [('25C', 48 / (0.082057 * 298.15))]:
            m8 = mda8(ppb * fac)
            m8 = m8[m8.index.year == y]
            rows.append(dict(year=y, st=NAME[sid], off_mean=om, feed_mean_25C=round(fm * fac, 1), ratio_off_over_feed=round(om / (fm * fac), 3), implied_factor=round(f_impl, 3),
                             off_max8=ox, feed_max8_25C=round(m8.max(), 1), max_ratio=round(ox / m8.max(), 3), off_days140=oc, feed_days140_25C=int((m8 > 140).sum()),
                             off_avail=oa, feed_avail=round(100 * ppb.notna().mean())))
R = pd.DataFrame(rows)
print(R.to_string(index=False))
print('\nSummary of off/feed MEAN ratio by year:'); print(R.groupby('year').ratio_off_over_feed.agg(['count', 'mean', 'std', 'min', 'max']).round(3))
print('Summary of off/feed MAX-8h ratio by year:'); print(R.groupby('year').max_ratio.agg(['count', 'mean', 'std', 'min', 'max']).round(3))
print('Implied factor (ug/m3 per ppb) range by year:'); print(R.groupby('year').implied_factor.agg(['mean', 'std', 'min', 'max']).round(3))
print('Reference factors: 25C =', round(48 / (0.082057 * 298.15), 4), '| 20C =', round(48 / (0.082057 * 293.15), 4), '| 30C =', round(48 / (0.082057 * 303.15), 4))
print('\nCorrelation of 8h-max official vs feed (25C) across station-years:', round(R.off_max8.corr(R.feed_max8_25C), 3))

# count sensitivity: days>100 and >140 for Tivon under alternative factors
print('\nTivon days MDA8>100 / >140 under conversion options (no fitted scale):')
t = O3[137]
opts = {'25C (1.962)': 48 / (0.082057 * 298.15), '20C (1.995)': 48 / (0.082057 * 293.15), 'implied-from-official-mean (Tivon 2021 1.887; 2025 per-year)': None}
for y in range(2021, 2027):
    ppb = t[t.index.year == y]
    out = []
    for lab, f in opts.items():
        if f is None:
            if y in OFF:
                f = OFF[y][137][0] / ppb.mean()
            else:
                f = np.nan
        if np.isnan(f):
            out.append(f'{lab}: n/a')
            continue
        m8 = mda8(ppb * f)
        m8 = m8[m8.index.year == y]
        out.append(f'{lab} f={f:.3f}: >100={int((m8 > 100).sum())}, >140={int((m8 > 140).sum())}')
    print(y, ' | '.join(out))
