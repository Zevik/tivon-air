"""Round-4 checks: (a) Simpson's-paradox test for PM2.5/NO2 stagnation effect with sector controls, (b) dust-filter sensitivity (PM2.5>37.5 OR-clause),
(c) PM2.5/PM10 and coarse fraction by hour/sector, (d) benzene resolution/LOD indicators and post-11.9 stats, 344-vs-137 in Jan-Aug,
(e) implied reference temperature from official/feed ratios (tests the 'ambient temperature conversion' hypothesis)."""
import sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 220)
IDX = pd.date_range('2021-01-01 00:00', '2026-10-17 09:00', freq='h')


def load(f, idx=IDX):
    L = pd.read_csv(f)
    L['t'] = pd.to_datetime(L.datetime.str[:19])
    L.loc[~L.valid, 'value'] = np.nan
    return L.pivot_table(index='t', columns='channel', values='value', aggfunc='first').reindex(idx)


tv = load('tivon_hourly_long_2021-2026.csv')
tv['hour'] = tv.index.hour
tv['month'] = tv.index.month
tv['year'] = tv.index.year
tv['date'] = tv.index.normalize()
tv['NO2u'] = tv['NO2'] * 46.0055 / 24.4655
tv['NOx_ug'] = tv['NOX'] * 46.0055 / 24.4655
tv['sec'] = np.select([(tv.WD >= 270) & (tv.WD <= 315), (tv.WD > 315) | (tv.WD < 45), (tv.WD >= 45) & (tv.WD < 135), (tv.WD >= 135) & (tv.WD < 225), (tv.WD >= 225) & (tv.WD < 270)],
                      ['Bay', 'N', 'E', 'S', 'WSW'], 'none')

dm = tv.groupby('date').agg(pm10=('PM10', 'mean'), pm25=('PM2.5', 'mean'))
dm['coarse'] = dm.pm10 - dm.pm25
dm['ratio'] = dm.pm25 / dm.pm10
old = (dm.pm10 > 80) | (dm.pm25 > 37.5) | ((dm.pm10 > 50) & (dm.ratio < 0.35))
new = (dm.pm10 > 80) | ((dm.pm10 > 50) & (dm.ratio < 0.35))        # PM2.5>37.5 OR-clause removed
none_ = pd.Series(False, index=dm.index)
nxt = lambda s: s | s.shift(1, fill_value=False)
FILT = {'old (with PM2.5>37.5 clause)': nxt(old), 'new (no PM2.5 clause)': nxt(new), 'coarse>60 only': nxt(dm.coarse > 60), 'no dust filter': none_}
winter_days = dm.index[dm.index.month.isin([12, 1, 2])]
for k, v in FILT.items():
    print('%-32s flagged winter days: %d of %d' % (k, int(v.loc[winter_days].sum()), len(winter_days)))
print('winter days flagged by old but not by new:', int((nxt(old) & ~nxt(new)).loc[winter_days].sum()), '| mean daily PM2.5 on those days: %.1f ; mean PM10: %.1f ; PM2.5/PM10 %.2f' % (
    dm.loc[(old & ~new) & dm.index.isin(winter_days), 'pm25'].mean(), dm.loc[(old & ~new) & dm.index.isin(winter_days), 'pm10'].mean(), dm.loc[(old & ~new) & dm.index.isin(winter_days), 'ratio'].mean()))

# ---------- (a) Simpson ----------
print('\n===== (a) stagnation effect with sector controls (winter DJF, WS>=0.5) =====')
for flab, flt in FILT.items():
    w = tv[tv.month.isin([12, 1, 2]) & ~tv.date.map(flt) & (tv.WS >= 0.5) & (tv.sec != 'none')].copy()
    w['slow'] = (w.WS < 1).astype(int)
    w['fast'] = (w.WS > 3).astype(int)
    w['g'] = w.date.dt.strftime('%Y%m%d')
    for y, col in [('PM2.5', 'PM2.5'), ('NO2', 'NO2u')]:
        d = w.dropna(subset=[col]).copy()
        d = d[d[col] > 0.5]
        d['ly'] = np.log(d[col])
        m0 = smf.ols('ly ~ slow + fast + C(hour) + C(month) + C(year)', d).fit(cov_type='cluster', cov_kwds={'groups': d.g})
        m1 = smf.ols('ly ~ slow + fast + C(sec) + C(hour) + C(month) + C(year)', d).fit(cov_type='cluster', cov_kwds={'groups': d.g})
        f = lambda m, k: 'x%.3f [%.3f,%.3f]' % (np.exp(m.params[k]), *np.exp(m.conf_int().loc[k]))
        print('[%s] %s: slow(0.5-1) vs 1-3: no sector ctrl %s | WITH sector %s ; fast(>3): no ctrl %s | sector %s' % (flab, y, f(m0, 'slow'), f(m1, 'slow'), f(m0, 'fast'), f(m1, 'fast')))
# per-sector effects (old filter and new filter)
print('\nper-sector slow(0.5-1) vs 1-3 effect, adjusted for hour/month/year (new filter):')
w = tv[tv.month.isin([12, 1, 2]) & ~tv.date.map(FILT['new (no PM2.5 clause)']) & (tv.WS >= 0.5) & (tv.sec != 'none') & (tv.WS <= 3)].copy()
w['slow'] = (w.WS < 1).astype(int)
w['g'] = w.date.dt.strftime('%Y%m%d')
for y, col in [('PM2.5', 'PM2.5'), ('NO2', 'NO2u')]:
    out = {}
    for s, d in w.groupby('sec'):
        d = d.dropna(subset=[col])
        d = d[d[col] > 0.5].copy()
        d['ly'] = np.log(d[col])
        m = smf.ols('ly ~ slow + C(hour) + C(month) + C(year)', d).fit(cov_type='cluster', cov_kwds={'groups': d.g})
        out[s] = 'x%.2f [%.2f,%.2f] n=%d' % (np.exp(m.params['slow']), *np.exp(m.conf_int().loc['slow']), len(d))
    print(y, out)
sh = tv[tv.month.isin([12, 1, 2]) & ~tv.date.map(FILT['new (no PM2.5 clause)']) & (tv.WS >= 0.5) & (tv.sec != 'none')].copy()
sh['bin'] = pd.cut(sh.WS, [0.5, 1, 3, 20], labels=['0.5-1', '1-3', '>3'], right=False)
print('\nsector shares by speed bin (winter, new filter):'); print(pd.crosstab(sh.bin, sh.sec, normalize='index').round(3).to_string())

# ---------- (b) dust filter sensitivity on day-FE evening/night ----------
print('\n===== (b) dust-filter sensitivity, day-FE evening/night vs noon (winter) =====')
ca = load('carmelpark_st69_hourly_2021-2026.csv')
af = load('afula_st1_hourly_2021-2026.csv')
tv['Tc'] = ca['Temp']
tv['RHc'] = ca['RH']
tv['dT'] = af['Temp'] - ca['Temp']
for flab, flt in FILT.items():
    w = tv[tv.month.isin([12, 1, 2]) & ~tv.date.map(flt)].copy()
    w['per'] = np.select([w.hour.between(0, 5), w.hour.between(12, 16), w.hour.between(18, 23)], ['night', 'noon', 'eve'], 'other')
    w = w[w.per != 'other']
    w['lp'] = np.log(w['PM2.5'].where(w['PM2.5'] > 0.5))
    w['lws'] = np.log(w.WS.where(w.WS > 0.2))
    w['lnox'] = np.log(w.NOx_ug.where(w.NOx_ug > 0.5))
    w = w.dropna(subset=['lp', 'lws', 'lnox', 'Tc', 'RHc', 'dT']).copy()
    w['g'] = w.date.dt.strftime('%Y%m%d')
    res = []
    for f, lab in [('lp ~ C(per, Treatment("noon")) + C(g)', 'base'), ('lp ~ C(per, Treatment("noon")) + lws + Tc + RHc + dT + C(g)', 'ctrl'), ('lp ~ C(per, Treatment("noon")) + lws + Tc + RHc + dT + lnox + C(g)', 'ctrl+NOx')]:
        m = smf.ols(f, w).fit(cov_type='cluster', cov_kwds={'groups': w.g})
        e = [k for k in m.params.index if 'eve' in k][0]
        n = [k for k in m.params.index if 'night' in k][0]
        res.append('%s eve %.2f night %.2f' % (lab, np.exp(m.params[e]), np.exp(m.params[n])))
    print('%-32s days %d | %s' % (flab, w.g.nunique(), ' | '.join(res)))

# ---------- (c) PM2.5/PM10 ----------
print('\n===== (c) PM2.5/PM10 =====')
w = tv[tv.month.isin([12, 1, 2]) & ~tv.date.map(FILT['new (no PM2.5 clause)'])].copy()
w['coarse'] = w.PM10 - w['PM2.5']
g = w.groupby('hour').agg(pm25=('PM2.5', 'mean'), pm10=('PM10', 'mean'), coarse=('coarse', 'mean'))
g['ratio'] = g.pm25 / g.pm10
print('winter hourly mean PM2.5, PM10, coarse, ratio of means:'); print(g.round(2).T.to_string())
for lab, hs in [('night 00-05', range(0, 6)), ('noon 12-16', range(12, 17)), ('eve 18-23', range(18, 24))]:
    d = w[w.hour.isin(hs)]
    print('%s: PM2.5 %.1f PM10 %.1f coarse %.1f ratio(mean) %.2f' % (lab, d['PM2.5'].mean(), d.PM10.mean(), d.coarse.mean(), d['PM2.5'].mean() / d.PM10.mean()))
d = w[(w.sec == 'E') & (w.WS >= 1) & (w.WS < 3)]
d2 = w[(w.sec == 'Bay') & (w.WS >= 1) & (w.WS < 3)]
d3 = w[(w.sec == 'S') & (w.WS >= 1) & (w.WS < 3)]
for lab, x in [('E 1-3', d), ('S 1-3', d3), ('Bay 1-3', d2)]:
    print('%s: PM2.5 %.1f PM10 %.1f coarse %.1f ratio %.2f n=%d' % (lab, x['PM2.5'].mean(), x.PM10.mean(), x.coarse.mean(), x['PM2.5'].mean() / x.PM10.mean(), len(x)))
# summer for reference
s = tv[tv.month.isin([6, 7, 8])]
print('summer overall ratio(mean) %.2f' % (s['PM2.5'].mean() / s.PM10.mean()))

# ---------- (d) benzene ----------
print('\n===== (d) benzene station 344 =====')
mb = load('mobile344_alroei_2026.csv', pd.date_range('2026-01-01', '2026-10-17 09:00', freq='h'))
bz = mb['Benzene'].dropna()
print('valid hours', len(bz), '| unique ppb values', bz.nunique(), '| smallest positive step', np.sort(bz.unique())[:8])
print('share of hours <=0.05 ppb: %.2f ; <=0.10 ppb (0.32 ug/m3): %.2f ; <=0.2 ppb: %.2f' % ((bz <= 0.05).mean(), (bz <= 0.10).mean(), (bz <= 0.2).mean()))
mon = (bz * 3.193).groupby(bz.index.to_period('M')).agg(['mean', lambda s: (s * 1).quantile(.5), lambda s: ((s / 3.193) <= 0.10).mean()])
print('monthly mean (ug), median, share<=0.10ppb:'); print(mon.round(2).to_string())
since = (mb['Benzene'] * 3.193)['2026-09-11 14:00':]
dd = since.resample('D').agg(['mean', 'count'])
dd = dd[dd['count'] >= 18]
print('\nsince 11.9.2026 14:00 (post-outage): hours %d, mean %.2f, max daily mean %.2f (%s), max hourly %.1f, days>3.9: %d' % (since.notna().sum(), since.mean(), dd['mean'].max(), dd['mean'].idxmax().date(), since.max(), int((dd['mean'] > 3.9).sum())))
print('hours > 3.9 ug/m3 since 11.9:', int((since > 3.9).sum()), '| hours > 5:', int((since > 5).sum()))
# 344 vs 137 Jan-Aug winter nights
c = mb.join(tv[['WS', 'WD', 'PM2.5', 'NO2u', 'NOx_ug']], how='left', lsuffix='_344', rsuffix='_137')
c['NO2_344u'] = c['NO2'] * 46.0055 / 24.4655
c['NOx_344u'] = c['NOX'] * 46.0055 / 24.4655
for lab, (a, b) in {'Jan-Feb': ('2026-01-01', '2026-02-28'), 'Jan-Aug': ('2026-01-01', '2026-08-31')}.items():
    x = c[a:b]
    n = x[x.index.hour <= 5]
    print('%s nights 00-05: WS 344 %.2f vs 137 %.2f (corr %.2f) | PM2.5 344 %.1f / 137 %.1f | NOx 344 %.1f / 137 %.1f | NO2 344 %.1f / 137 %.1f (location of 344 before Sept unknown)' % (
        lab, n.WS_344.mean(), n.WS_137.mean(), n.WS_344.corr(n.WS_137), n['PM2.5_344'].mean(), n['PM2.5_137'].mean(), n.NOx_344u.mean(), n.NOx_ug.mean(), n.NO2_344u.mean(), n.NO2u.mean()))

# ---------- (e) implied reference temperature ----------
print('\n===== (e) implied reference temperature, T = 298.15 * P_ratio / r =====')
H = {137: 201, 88: 44, 69: 527, 86: 235, 87: 96, 90: 391, 92: 21, 93: 122, 96: 5, 382: 32}
RATIO = {2021: {96: 0.989, 90: 0.966, 86: 0.966, 69: 0.995, 88: 0.983, 137: 0.962, 92: 0.991, 382: 0.997, 93: 0.987, 87: 0.988}, 2025: {96: 0.990, 90: 0.970, 86: 0.966, 69: 0.937, 88: 0.982, 137: 0.961, 92: 0.992, 382: 0.987, 93: 0.986}}
rows = []
for y, d in RATIO.items():
    for s, r in d.items():
        p = (1 - 2.25577e-5 * H[s]) ** 5.25588
        rows.append((y, s, H[s], round(p, 4), r, round(298.15 * p / r - 273.15, 1)))
R = pd.DataFrame(rows, columns=['year', 'st', 'h', 'P', 'ratio', 'impliedT_C'])
print(R.to_string(index=False))
print('implied T (C): mean %.1f sd %.1f min %.1f max %.1f; excluding Carmel Park (69): mean %.1f sd %.1f' % (R.impliedT_C.mean(), R.impliedT_C.std(), R.impliedT_C.min(), R.impliedT_C.max(), R[R.st != 69].impliedT_C.mean(), R[R.st != 69].impliedT_C.std()))
# monthly constancy for Tivon: the ambient-temperature hypothesis predicts ratio rising in cold months
mo = {'2023-06': 0.967, '2023-10': 0.964, '2023-12': 0.965, '2024-07': 0.966, '2024-08': 0.966, '2024-12': 0.964}
amb = {}
for m_ in mo:
    amb[m_] = ca['Temp'][m_].mean()   # Carmel Park monthly mean T (ridge proxy)
print('Tivon monthly official/feed ratio vs proxy ambient T (Carmel Park, C):', {k: (mo[k], round(amb[k], 1)) for k in mo})
pred = {k: round(0.9764 * (298.15) / (amb[k] + 273.15), 3) for k in mo}
print('ratio predicted if conversion used actual ambient T and station pressure:', pred)
