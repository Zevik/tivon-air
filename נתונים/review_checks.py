"""Checks prompted by the external peer review: (1) barometric-pressure explanation of the official/feed ratio, (2) O3 and upper percentiles by wind sector,
(3) 2026 right-censoring (Jan1-Oct17 comparison), (4) rain effect on PM2.5 (rain from Kiryat Ata, station 88)."""
import sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 220)
IDX = pd.date_range('2021-01-01 00:00', '2026-10-17 09:00', freq='h')


def load(f):
    L = pd.read_csv(f)
    L['t'] = pd.to_datetime(L.datetime.str[:19])
    L.loc[~L.valid, 'value'] = np.nan
    return L.pivot_table(index='t', columns='channel', values='value', aggfunc='first').reindex(IDX)


# ---------- (1) pressure ----------
H = {137: 201, 88: 44, 69: 527, 86: 235, 87: 96, 90: 391, 92: 21, 93: 122, 96: 5, 382: 32}
RATIO = {  # official mean / feed mean (25C, 1 atm) from validate_o3_official_output.txt
    2021: {96: 0.989, 90: 0.966, 86: 0.966, 69: 0.995, 88: 0.983, 137: 0.962, 92: 0.991, 382: 0.997, 93: 0.987, 87: 0.988},
    2025: {96: 0.990, 90: 0.970, 86: 0.966, 69: 0.937, 88: 0.982, 137: 0.961, 92: 0.992, 382: 0.987, 93: 0.986}}


def p_ratio(h):
    return (1 - 2.25577e-5 * h) ** 5.25588


rows = []
for y, d in RATIO.items():
    for sid, r in d.items():
        rows.append(dict(year=y, st=sid, h=H[sid], p=p_ratio(H[sid]), r=r))
D = pd.DataFrame(rows)
D['r_over_p'] = D.r / D.p
print('(1) PRESSURE TEST: observed official/feed ratio vs standard-atmosphere pressure ratio at station elevation')
print(D.round(4).to_string(index=False))
print('corr(r, p) =', round(D.r.corr(D.p), 3), '| r/p mean', round(D.r_over_p.mean(), 4), 'sd', round(D.r_over_p.std(), 4), '| r sd', round(D.r.std(), 4))
m = smf.ols('r ~ p', D).fit()
print('OLS r = a + b p: a=%.3f b=%.3f R2=%.3f' % (m.params['Intercept'], m.params['p'], m.rsquared))
print('Without Carmel Park (69):'); D2 = D[D.st != 69]
m2 = smf.ols('r ~ p', D2).fit()
print('corr', round(D2.r.corr(D2.p), 3), 'r/p mean', round(D2.r_over_p.mean(), 4), 'sd', round(D2.r_over_p.std(), 4), 'R2', round(m2.rsquared, 3))
print('Tivon: p ratio at 201 m =', round(p_ratio(201), 4), '; at 223 m =', round(p_ratio(223), 4))

# ---------- (2) ozone and upper percentiles by sector ----------
tv = load('tivon_hourly_long_2021-2026.csv')
tv['sec'] = np.select([(tv.WD >= 270) & (tv.WD <= 315), (tv.WD > 315) | (tv.WD < 45), (tv.WD >= 45) & (tv.WD < 135), (tv.WD >= 135) & (tv.WD < 225), (tv.WD >= 225) & (tv.WD < 270)],
                      ['Bay270-315', 'N315-45', 'E45-135', 'S135-225', 'WSW225-270'], 'none')
tv = tv[(tv.WS >= 0.5) & (tv.sec != 'none')].copy()
tv['O3u'] = tv['O3'] * 1.886
tv['NO2u'] = tv['NO2'] * 46.0055 / (0.082057 * 298.15)
tv['month'] = tv.index.month
tv['hour'] = tv.index.hour
tv['summer'] = tv.month.isin([6, 7, 8])
tv['dayh'] = tv.hour.between(10, 17)
print('\n(2) BY WIND SECTOR (WS>=0.5), O3 in ug/m3 with factor A=1.886:')
g = tv.groupby('sec').agg(n=('O3u', 'size'), O3_mean=('O3u', 'mean'), O3_p99=('O3u', lambda s: s.quantile(.99)), O3_gt100h=('O3u', lambda s: (s > 100).mean()),
                          NO2_mean=('NO2u', 'mean'), NO2_p99=('NO2u', lambda s: s.quantile(.99)), PM25_mean=('PM2.5', 'mean'), PM25_p99=('PM2.5', lambda s: s.quantile(.99)),
                          PM10_p99=('PM10', lambda s: s.quantile(.99)))
print(g.round(2).to_string())
for lab, d in [('JJA daytime 10-17', tv[tv.summer & tv.dayh]), ('winter all hours', tv[tv.month.isin([12, 1, 2])])]:
    gg = d.groupby('sec').agg(n=('O3u', 'size'), O3_mean=('O3u', 'mean'), O3_p99=('O3u', lambda s: s.quantile(.99)), O3_gt100h=('O3u', lambda s: (s > 100).mean()), NO2_p99=('NO2u', lambda s: s.quantile(.99)), PM25_p99=('PM2.5', lambda s: s.quantile(.99)))
    print('\n--', lab); print(gg.round(2).to_string())
# share of top-1% hours falling in each sector vs sector share
print('\nshare of the top 1% hours (all sectors pooled) by sector vs sector share of hours:')
for v, col in [('O3', 'O3u'), ('NO2', 'NO2u'), ('PM2.5', 'PM2.5'), ('PM10', 'PM10')]:
    thr = tv[col].quantile(.99)
    top = tv[tv[col] >= thr]
    print(v, 'thr', round(thr, 1), (top.sec.value_counts(normalize=True)).round(3).to_dict(), '| sector shares', tv.sec.value_counts(normalize=True).round(3).to_dict())
# regression: O3 in sector adjusting hour/month/year/ln WS (JJA daytime)
d = tv[tv.summer & tv.dayh].dropna(subset=['O3u', 'WS']).copy()
d['bay'] = (d.sec == 'Bay270-315').astype(int)
d['lO3'] = np.log(d.O3u.clip(lower=1))
d['lws'] = np.log(d.WS)
d['g'] = d.index.strftime('%Y%m%d')
d['year'] = d.index.year
mm = smf.ols('lO3 ~ bay + C(hour) + C(month) + C(year) + lws', d).fit(cov_type='cluster', cov_kwds={'groups': d.g})
print('\nJJA daytime: O3 bay sector vs other sectors, adj: ratio=%.3f CI[%.3f,%.3f]' % (np.exp(mm.params['bay']), *np.exp(mm.conf_int().loc['bay'])))
# all-hours O3 regression (with NO2 not controlled)
d = tv.dropna(subset=['O3u', 'WS']).copy()
d['bay'] = (d.sec == 'Bay270-315').astype(int)
d['lO3'] = np.log(d.O3u.clip(lower=1))
d['lws'] = np.log(d.WS)
d['g'] = d.index.strftime('%Y%m%d')
d['year'] = d.index.year
mm = smf.ols('lO3 ~ bay + C(hour) + C(month) + C(year) + lws', d).fit(cov_type='cluster', cov_kwds={'groups': d.g})
print('all hours: O3 bay vs other, adj: ratio=%.3f CI[%.3f,%.3f]' % (np.exp(mm.params['bay']), *np.exp(mm.conf_int().loc['bay'])))

# ---------- (3) 2026 right-censoring ----------
tv0 = load('tivon_hourly_long_2021-2026.csv')
p = tv0['PM2.5']
dm = p.resample('D').agg(['mean', 'count'])
dm = dm[dm['count'] >= 18]
print('\n(3) PM2.5 days>15 and >37.5 and mean, Jan 1 - Oct 17 only, each year:')
for y in range(2021, 2027):
    s = dm[(dm.index >= f'{y}-01-01') & (dm.index <= f'{y}-10-17')]
    pm = p[f'{y}-01-01':f'{y}-10-17']
    print(y, 'valid days', len(s), '>15:', int((s['mean'] > 15).sum()), '(%.1f%%)' % (100 * (s['mean'] > 15).mean()), '>37.5:', int((s['mean'] > 37.5).sum()), 'mean', round(pm.mean(), 2))
print('Nov1-Dec31 share of annual days>15 (2021-2025):', round(sum(int((dm[(dm.index >= f'{y}-11-01') & (dm.index <= f'{y}-12-31')]['mean'] > 15).sum()) for y in range(2021, 2026)) / sum(int((dm[dm.index.year == y]['mean'] > 15).sum()) for y in range(2021, 2026)), 3))
# ozone Jan1-Oct17
o = tv0['O3'] * 1.886
r = o.rolling(8, min_periods=6).mean()
g8 = pd.DataFrame({'r': r}).groupby(r.index.normalize()).agg(m=('r', 'max'), n=('r', 'count'))
g8 = g8[g8.n >= 18]
print('O3 days MDA8>100 (A), Jan1-Oct17:', {y: int((g8[(g8.index >= f'{y}-01-01') & (g8.index <= f'{y}-10-17')].m > 100).sum()) for y in range(2021, 2027)})
print('O3 days MDA8>100 (A), Nov1-Dec31:', {y: int((g8[(g8.index >= f'{y}-11-01') & (g8.index <= f'{y}-12-31')].m > 100).sum()) for y in range(2021, 2026)})

# ---------- (4) rain ----------
ata = load('kataa_st88_hourly_2021-2026.csv')
rain = ata['Rain']
print('\n(4) RAIN (Kiryat Ata, ~10 km): channel units/total:', round(rain.sum(), 1), 'hours with rain>0:', int((rain > 0).sum()))
dd = pd.DataFrame({'pm': tv0['PM2.5'], 'pm10': tv0['PM10'], 'rain': rain})
dd['date'] = dd.index.normalize()
day = dd.groupby('date').agg(pm=('pm', 'mean'), pm10=('pm10', 'mean'), rain=('rain', 'sum'), n=('pm', 'count'))
day = day[day.n >= 18]
day['prev_rain'] = day.rain.shift(1)
w = day[day.index.month.isin([11, 12, 1, 2, 3])].copy()
w['wet'] = w.rain > 0.2
w['wet_prev'] = w.prev_rain > 0.2
print('Nov-Mar daily PM2.5 mean on rain days vs dry:', w.groupby('wet').pm.agg(['mean', 'median', 'count']).round(1).to_dict('index'))
print('Next-day after rain vs dry-after-dry:', w.groupby(['wet', 'wet_prev']).pm.agg(['mean', 'count']).round(1).to_dict('index'))
w['dust'] = (w.pm10 > 80) | (w.pm > 37.5)
ww = w[~w.dust].copy()
ww['lp'] = np.log(ww.pm)
ww['month'] = ww.index.month
ww['year'] = ww.index.year
mr = smf.ols('lp ~ wet + wet_prev + C(month) + C(year)', ww).fit(cov_type='HC1')
print('non-dust days Nov-Mar log PM2.5 ~ rain today + rain yesterday: rain today x%.3f (p=%.1e), rain yesterday x%.3f (p=%.1e), n=%d' % (np.exp(mr.params['wet[T.True]']), mr.pvalues['wet[T.True]'], np.exp(mr.params['wet_prev[T.True]']), mr.pvalues['wet_prev[T.True]'], mr.nobs))
# is night excess different on dry days?
dd2 = dd.copy()
dd2['hour'] = dd2.index.hour
dd2['wetday'] = dd2.date.map(day.rain > 0.2)
dd2 = dd2[dd2.index.month.isin([12, 1, 2]) & dd2.wetday.notna()]
for wd, x in dd2.groupby('wetday'):
    n = x[x.hour.between(0, 5)].pm.mean()
    nn = x[x.hour.between(12, 16)].pm.mean()
    print('winter wet-day =', wd, ': night %.1f noon %.1f ratio %.2f' % (n, nn, n / nn), 'hours', len(x))
