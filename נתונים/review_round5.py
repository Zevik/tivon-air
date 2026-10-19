"""Round-5 checks from the updated peer review:
(A) bearings from Tivon (137) to the Haifa Bay industrial box and finer wind sub-sectors (270-305 / 305-335 / 335-45),
(B) structural break in Kiryat Ata (88) vs Tivon (137): monthly O3, NO, NO2, NOx in ppb,
(C) Ata vs Tivon ozone compared in mixing ratio (ppb), no density conversion,
(D) night-excess PM2.5 vs lnNOx: is the rise 1.40 -> 1.49 concentrated in the hours where NOx is lowest (conditioning artifact)?"""
import sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 220)
pd.set_option('display.max_columns', 40)
IDX = pd.date_range('2021-01-01 00:00', '2026-10-17 09:00', freq='h')


def load(f, idx=IDX):
    L = pd.read_csv(f)
    L['t'] = pd.to_datetime(L.datetime.str[:19])
    L.loc[~L.valid, 'value'] = np.nan
    return L.pivot_table(index='t', columns='channel', values='value', aggfunc='first').reindex(idx)


def bearing(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dl = np.radians(lon2 - lon1)
    y = np.sin(dl) * np.cos(p2)
    x = np.cos(p1) * np.sin(p2) - np.sin(p1) * np.cos(p2) * np.cos(dl)
    return (np.degrees(np.arctan2(y, x)) + 360) % 360


def dist_km(lat1, lon1, lat2, lon2):
    return np.hypot((lat2 - lat1) * 111.2, (lon2 - lon1) * 111.2 * np.cos(np.radians(lat1)))


# ================= A. bearings =================
print('===== A1. bearings from Tivon station 137 (32.72222, 35.13019) =====')
T = (32.72222324, 35.13018868)
pts = {'station 88 Kiryat Ata (API list)': (32.81190414, 35.11309366), 'station 69 Carmel Park (API list)': (32.73695541, 35.03551151),
       'station 344 mobile (API list)': (32.7072117, 35.1117242), 'station 1 Afula (API list)': (32.60372041, 35.29175519),
       'box SW corner of the reviewer box (32.792N,35.035E)': (32.792, 35.035), 'box SE corner (32.792N,35.065E)': (32.792, 35.065),
       'box NW corner (32.820N,35.035E)': (32.820, 35.035), 'box NE corner (32.820N,35.065E)': (32.820, 35.065)}
for k, (la, lo) in pts.items():
    print('%-55s bearing %5.1f deg  distance %5.1f km' % (k, bearing(*T, la, lo), dist_km(*T, la, lo)))
print('NOTE: industrial box coordinates are the reviewer\'s; they are NOT from a source in the folder. Only stations come from the MANA list.')

tv = load('tivon_hourly_long_2021-2026.csv')
tv['hour'] = tv.index.hour
tv['month'] = tv.index.month
tv['year'] = tv.index.year
tv['date'] = tv.index.normalize()
tv['NO2u'] = tv['NO2'] * 46.0055 / 24.4655
tv['NOx_ug'] = tv['NOX'] * 46.0055 / 24.4655
wd = tv.WD
tv['sub'] = np.select([(wd >= 270) & (wd < 305), (wd >= 305) & (wd < 335), (wd >= 335) | (wd < 45), (wd >= 45) & (wd < 270)], ['270-305', '305-335', '335-45', '45-270'], 'none')
d = tv[(tv.WS >= 0.5) & tv.WD.notna()].copy()
print('\nhours with WS>=0.5 and valid WD:', len(d), '; share by sub-sector:', (d['sub'].value_counts(normalize=True)).round(3).to_dict())

print('\n===== A2. mean, P99, share of overall-P99 hours, by sub-sector (WS>=0.5) =====')
rows = []
for ch, lab in [('NO2u', 'NO2'), ('NOx_ug', 'NOx'), ('PM2.5', 'PM2.5'), ('PM10', 'PM10')]:
    x = d.dropna(subset=[ch])
    p99 = x[ch].quantile(.99)
    hi = x[x[ch] > p99]
    for s in ['270-305', '305-335', '335-45', '45-270']:
        v = x[x['sub'] == s][ch]
        rows.append((lab, s, len(v), v.mean(), v.quantile(.99), (hi['sub'] == s).mean() * 100, (x['sub'] == s).mean() * 100, p99))
r = pd.DataFrame(rows, columns=['pollutant', 'sector', 'n', 'mean', 'P99', 'pct_of_P99_hours', 'pct_of_all_hours', 'overall_P99'])
print(r.round(2).to_string(index=False))
# ozone, summer daytime (12-17) so season/time are fixed
o = d[d.month.isin([6, 7, 8]) & d.hour.between(12, 17)].dropna(subset=['O3'])
print('\nO3 ppb, JJA 12-17h, by sub-sector:'); print(o.groupby('sub').O3.agg(['count', 'mean', lambda s: s.quantile(.99)]).round(1).to_string())

print('\n===== A3. adjusted ratio vs reference sector 45-270 (log OLS, hour+month+year+WS bins; day-clustered) =====')
d['wsb'] = pd.cut(d.WS, [0.5, 1, 3, 6, 50], right=False, labels=['0.5-1', '1-3', '3-6', '6+'])
d['g'] = d.date.dt.strftime('%Y%m%d')
for ch, lab in [('NO2u', 'NO2'), ('NOx_ug', 'NOx'), ('PM2.5', 'PM2.5'), ('PM10', 'PM10')]:
    x = d.dropna(subset=[ch, 'wsb']).copy()
    x = x[x[ch] > 0.5]
    x['ly'] = np.log(x[ch])
    m = smf.ols('ly ~ C(sub, Treatment("45-270")) + C(wsb) + C(hour) + C(month) + C(year)', x).fit(cov_type='cluster', cov_kwds={'groups': x.g})
    out = []
    for k in m.params.index:
        if k.startswith('C(sub'):
            out.append('%s x%.2f [%.2f,%.2f]' % (k.split('T.')[1].rstrip(']'), np.exp(m.params[k]), *np.exp(m.conf_int().loc[k])))
    print(lab, '|', '; '.join(out))

print('\n===== A4. stagnation (WS 0.5-1 vs 1-3) by sub-sector, ratio of means =====')
for ch, lab in [('NO2u', 'NO2'), ('PM2.5', 'PM2.5')]:
    out = []
    for s in ['270-305', '305-335', '335-45', '45-270']:
        a = d[(d['sub'] == s) & (d.WS < 1)][ch].mean()
        b = d[(d['sub'] == s) & (d.WS >= 1) & (d.WS < 3)][ch].mean()
        out.append('%s %.2f (n slow=%d)' % (s, a / b, int(((d['sub'] == s) & (d.WS < 1)).sum())))
    print(lab, '|', '; '.join(out))

# ================= B. Kiryat Ata break =================
print('\n===== B. Kiryat Ata (88) vs Tivon (137): monthly means (ppb for gases) =====')
ka = load('kataa_st88_hourly_2021-2026.csv')
cols = ['O3', 'NO', 'NO2', 'NOX']
mm = pd.DataFrame({f'{c}_{n}': df[c].resample('MS').mean() for n, df in [('ata', ka), ('tiv', tv)] for c in cols})
cnt = pd.DataFrame({f'{c}_{n}': df[c].resample('MS').count() for n, df in [('ata', ka), ('tiv', tv)] for c in ['O3']})
for c in cols:
    mm[c + '_diff'] = mm[c + '_ata'] - mm[c + '_tiv']
print(mm[['O3_ata', 'O3_tiv', 'O3_diff', 'NO_ata', 'NO_tiv', 'NO2_ata', 'NO2_tiv', 'NOX_ata', 'NOX_tiv']].round(1).join(cnt.add_suffix('_n')).to_string())
print('\nyearly means (ppb): ')
yy = pd.DataFrame({f'{c}_{n}': df[c].groupby(df.index.year).mean() for n, df in [('ata', ka), ('tiv', tv)] for c in cols}).round(2)
print(yy.to_string())
print('\nnight (00-05) O3 mean and noon NO mean by year, Ata vs Tivon (titration signature):')
for n, df in [('ata', ka), ('tiv', tv)]:
    h = df.index.hour
    print(n, 'night O3', df[h <= 5].groupby(df.index[h <= 5].year).O3.mean().round(1).to_dict(), '| NO 06-09h', df[(h >= 6) & (h <= 9)].groupby(df.index[(h >= 6) & (h <= 9)].year).NO.mean().round(2).to_dict())

print('\nbest single-step break in the monthly O3 difference (Ata minus Tivon), by least squares:')
for c in ['O3_diff', 'NO_diff', 'NO2_diff', 'NOX_diff']:
    s = mm[c].dropna()
    best = None
    for i in range(6, len(s) - 6):
        a, b = s.iloc[:i], s.iloc[i:]
        sse = ((a - a.mean()) ** 2).sum() + ((b - b.mean()) ** 2).sum()
        if best is None or sse < best[0]:
            best = (sse, s.index[i], a.mean(), b.mean())
    tot = ((s - s.mean()) ** 2).sum()
    print('%-9s break at %s: mean before %.2f, after %.2f; variance explained %.0f%%' % (c, best[1].strftime('%Y-%m'), best[2], best[3], 100 * (1 - best[0] / tot)))

# ================= C. ppb comparison =================
print('\n===== C. MDA8 in ppb, Ata vs Tivon (no conversion) =====')


def mda8(s):
    r = s.rolling(8, min_periods=6).mean()
    day = r.index.normalize()
    ok = r.groupby(day).count() >= 18
    return r.groupby(day).max().where(ok)


ma, mt = mda8(ka.O3), mda8(tv.O3)
c = pd.concat([ma.rename('ata'), mt.rename('tiv')], axis=1).dropna()
jja = c[c.index.month.isin([6, 7, 8])]
print('common days', len(c), '| JJA common days', len(jja))
print('JJA mean daily MDA8 ppb: Ata %.1f, Tivon %.1f, diff %.1f' % (jja.ata.mean(), jja.tiv.mean(), (jja.ata - jja.tiv).mean()))
for y in range(2021, 2026):
    j = jja[jja.index.year == y]
    print(y, 'JJA n=%d Ata %.1f Tivon %.1f' % (len(j), j.ata.mean(), j.tiv.mean()))
for th in (46, 51, 60, 65):
    print('days MDA8 >= %d ppb (common days): Ata %d, Tivon %d' % (th, (c.ata >= th).sum(), (c.tiv >= th).sum()))
for lab, sel in [('2021-2022', c.index.year <= 2022), ('2023-2025', (c.index.year >= 2023) & (c.index.year <= 2025))]:
    cc = c[sel]
    print('%s all-year mean MDA8 ppb: Ata %.1f Tivon %.1f ; days >=51 ppb: Ata %d Tivon %d (n=%d)' % (lab, cc.ata.mean(), cc.tiv.mean(), (cc.ata >= 51).sum(), (cc.tiv >= 51).sum(), len(cc)))

# ================= D. night excess vs lnNOx =================
print('\n===== D. winter night excess by hour group, with/without lnNOx (386-day sample) =====')
dm = tv.groupby('date').agg(a=('PM10', 'mean'), b=('PM2.5', 'mean'))
dust = (dm.a > 80) | (dm.b > 37.5) | ((dm.a > 50) & (dm.b / dm.a < 0.35))
dust = dust | dust.shift(1, fill_value=False)
tv['dust'] = tv.date.map(dust)
ca = load('carmelpark_st69_hourly_2021-2026.csv')
af = load('afula_st1_hourly_2021-2026.csv')
w = tv[tv.month.isin([12, 1, 2]) & ~tv.dust].copy()
w['lp'] = np.log(w['PM2.5'].where(w['PM2.5'] > 0.5))
w['lnox'] = np.log(w['NOx_ug'].where(w['NOx_ug'] > 0.5))
w['lws'] = np.log(w['WS'].where(w['WS'] > 0.2))
w['Tc'] = ca['Temp']
w['RHc'] = ca['RH']
w['dT'] = af['Temp'] - ca['Temp']
w['per'] = np.select([w.hour.between(0, 2), w.hour.between(3, 5), w.hour.between(12, 16), w.hour.between(18, 23)], ['night0-2', 'night3-5', 'noon', 'eve'], 'other')
w = w[w.per != 'other'].dropna(subset=['lp', 'lnox', 'lws', 'Tc', 'RHc', 'dT']).copy()
w['g'] = w.date.dt.strftime('%Y%m%d')
print('rows', len(w), 'days', w.g.nunique(), '| mean NOx ug/m3 by period:', w.groupby('per').NOx_ug.mean().round(1).to_dict())
for f, lab in [('lp ~ C(per, Treatment("noon")) + C(g)', 'day FE'), ('lp ~ C(per, Treatment("noon")) + lnox + C(g)', 'day FE + lnNOx'),
               ('lp ~ C(per, Treatment("noon")) + lws + Tc + RHc + dT + C(g)', 'full'), ('lp ~ C(per, Treatment("noon")) + lws + Tc + RHc + dT + lnox + C(g)', 'full + lnNOx')]:
    m = smf.ols(f, w).fit(cov_type='cluster', cov_kwds={'groups': w.g})
    out = ['%s x%.3f [%.3f,%.3f]' % (k.split('T.')[1].rstrip(']'), np.exp(m.params[k]), *np.exp(m.conf_int().loc[k])) for k in m.params.index if k.startswith('C(per')]
    print('[%s] vs noon: %s' % (lab, '; '.join(out)))
# within night: does the lnNOx slope differ between hours 0-2 and 3-5?
n = w[w.per.isin(['night0-2', 'night3-5'])].copy()
for per in ['night0-2', 'night3-5']:
    x = n[n.per == per]
    m = smf.ols('lp ~ lnox + C(g)', x).fit(cov_type='cluster', cov_kwds={'groups': x.g})
    print(per, 'within-night lnNOx slope %.3f [%.3f,%.3f]; mean lnNOx %.2f' % (m.params['lnox'], *m.conf_int().loc['lnox'], x.lnox.mean()))
print('noon mean lnNOx %.2f' % w[w.per == 'noon'].lnox.mean())
