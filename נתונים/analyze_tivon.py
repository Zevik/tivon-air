"""Hourly analysis for Kiryat Tivon station (MANA / Envista station id 137).
Run:  python -I analyze_tivon.py   (from this folder; needs tivon_hourly_long_2021-2026.csv)
"""
import sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 220)
pd.set_option('display.max_columns', 40)

L = pd.read_csv('tivon_hourly_long_2021-2026.csv')
L['t'] = pd.to_datetime(L.datetime.str[:19])      # API serves fixed UTC+2 (Israel standard time, no DST)
L.loc[~L.valid, 'value'] = np.nan                 # drop values flagged invalid by the network
W = L.pivot_table(index='t', columns='channel', values='value', aggfunc='first')
W = W.reindex(pd.date_range(W.index.min(), W.index.max(), freq='h'))

MW = {'O3': 48.0, 'NO2': 46.0055, 'NO': 30.006, 'NOX': 46.0055}


def ug(ppb, mw, temp_c=25.0):
    return ppb * mw / (0.082057 * (273.15 + temp_c))


for c, m in MW.items():
    W[c + '_ug'] = ug(W[c], m)
W['hour'] = W.index.hour
W['month'] = W.index.month
W['year'] = W.index.year
W['date'] = W.index.normalize()
W['season'] = np.select([W.month.isin([12, 1, 2]), W.month.isin([6, 7, 8])], ['winter', 'summer'], 'other')
W['wyear'] = np.where(W.month == 12, W.year + 1, W.year)

print('rows', len(W), W.index.min(), W.index.max())
print('valid share by channel:')
print(W[['PM2.5', 'PM10', 'O3', 'NO2', 'WD', 'WS']].notna().mean().round(3).to_string())

# ================= 1. PM2.5 diurnal pattern =================
print('\n===== 1. PM2.5 evening (18-23) vs noon (12-16) =====')


def eve_noon(df, e=(18, 23), n=(12, 16)):
    ev = df[(df.hour >= e[0]) & (df.hour <= e[1])]['PM2.5']
    no = df[(df.hour >= n[0]) & (df.hour <= n[1])]['PM2.5']
    return ev.mean(), no.mean(), ev.median(), no.median()


res = {}
for s in ['winter', 'summer']:
    d = W[W.season == s]
    e, n, em, nm = eve_noon(d)
    e2, n2, _, _ = eve_noon(d, (18, 22))
    print(f'{s}: evening={e:.2f} noon={n:.2f} ratio={e / n:.3f} | medians {em:.1f}/{nm:.1f} ratio={em / nm:.3f} | 18-22 variant ratio={e2 / n2:.3f} | valid hours={d["PM2.5"].notna().sum()}')
    res[s] = (e, n)
print('ratio of ratios winter/summer: %.3f' % ((res['winter'][0] / res['winter'][1]) / (res['summer'][0] / res['summer'][1])))

print('\nBy year (winter = Dec of previous year + Jan + Feb; summer = JJA):')
rows = []
for s, yc in [('winter', 'wyear'), ('summer', 'year')]:
    for y, d in W[W.season == s].groupby(yc):
        e, n, _, _ = eve_noon(d)
        rows.append((s, y, len(d), round(d['PM2.5'].notna().mean(), 3), round(e, 2), round(n, 2), round(e / n, 3)))
print(pd.DataFrame(rows, columns=['season', 'yr', 'hrs', 'cov', 'eve', 'noon', 'ratio']).to_string(index=False))

for s in ['winter', 'summer']:
    d = W[W.season == s]
    ev = d[(d.hour >= 18) & (d.hour <= 23)].groupby('date')['PM2.5'].agg(['mean', 'count'])
    no = d[(d.hour >= 12) & (d.hour <= 16)].groupby('date')['PM2.5'].agg(['mean', 'count'])
    j = ev.join(no, lsuffix='_e', rsuffix='_n').query('count_e>=4 and count_n>=4')
    diff = j.mean_e - j.mean_n
    w = stats.wilcoxon(diff)
    rng = np.random.default_rng(0)
    bs = [rng.choice(diff.values, len(diff)).mean() for _ in range(2000)]
    print(f'{s}: paired days={len(j)} share(eve>noon)={(diff > 0).mean():.3f} mean diff={diff.mean():.2f} 95%CI[{np.percentile(bs, 2.5):.2f},{np.percentile(bs, 97.5):.2f}] wilcoxon p={w.pvalue:.2e}')

prof = W.groupby(['season', 'hour'])['PM2.5'].mean().unstack(0)[['winter', 'summer', 'other']]
print('\nPM2.5 mean by hour (standard time UTC+2):')
print(prof.round(1).T.to_string())
for s in ['winter', 'summer']:
    p = prof[s]
    print(s, 'peak hour', int(p.idxmax()), round(p.max(), 1), '| trough hour', int(p.idxmin()), round(p.min(), 1), '| peak/trough', round(p.max() / p.min(), 2))

for v in ['NO2_ug', 'WS']:
    out = []
    for s in ['winter', 'summer']:
        d = W[W.season == s]
        ev = d[(d.hour >= 18) & (d.hour <= 23)][v].mean()
        no = d[(d.hour >= 12) & (d.hour <= 16)][v].mean()
        out.append(f'{s} eve {ev:.2f} noon {no:.2f} ratio {ev / no:.2f}')
    print(v + ':', ' | '.join(out))

print('\nPM2.5 annual mean & coverage:')
ann = W.groupby('year')['PM2.5'].agg(['mean', 'count'])
ann['cov'] = ann['count'] / W.groupby('year').size()
print(ann.round(2).to_string())
dm = W.groupby('date')['PM2.5'].agg(['mean', 'count']).query('count>=18')
print('valid days per year:', dm.groupby(dm.index.year).size().to_dict())
print('days daily-mean>37.5:', dm[dm['mean'] > 37.5].groupby(dm[dm['mean'] > 37.5].index.year).size().to_dict())
print('days daily-mean>15 (WHO24h):', dm[dm['mean'] > 15].groupby(dm[dm['mean'] > 15].index.year).size().to_dict())
print('monthly means:')
print(W.groupby(['year', 'month'])['PM2.5'].mean().unstack().round(1).to_string())

# ================= 2. Wind sectors =================
print('\n===== 2. Wind sectors =====')
A = W.dropna(subset=['WD', 'WS']).copy()
A = A[A.WS >= 0.5]      # exclude calms (direction unreliable)
wd = A.WD.values
A['sec'] = np.select(
    [(wd >= 270) & (wd <= 315), (wd > 315) | (wd < 45), (wd >= 45) & (wd < 135), (wd >= 135) & (wd < 225), (wd >= 225) & (wd < 270)],
    ['Bay_NW_270-315', 'North_315-45', 'East_45-135', 'South_135-225', 'WSW_225-270'], 'x')
vars_ = ['NO2_ug', 'NOX_ug', 'PM2.5', 'PM10']
tab = A.groupby('sec')[vars_ + ['WS']].mean()
tab['n_hours'] = A.groupby('sec').size()
tab['share%'] = 100 * tab.n_hours / tab.n_hours.sum()
print('ALL hours (WS>=0.5):')
print(tab.round(2).to_string())
A['tod'] = np.where(A.hour.between(10, 17), 'day10-17', 'night18-09')
for s in ['winter', 'summer', 'other']:
    for t in ['day10-17', 'night18-09']:
        d = A[(A.season == s) & (A.tod == t)]
        g = d.groupby('sec')[['NO2_ug', 'PM2.5']].mean()
        g['n'] = d.groupby('sec').size()
        print(f'--- {s} {t}')
        print(g.round(2).T.to_string())

B = A.dropna(subset=['NO2_ug', 'PM2.5']).copy()
B = B[(B.NO2_ug > 0.5) & (B['PM2.5'] > 0.5)]
B['lNO2'] = np.log(B.NO2_ug)
B['lPM'] = np.log(B['PM2.5'])
B['bay'] = (B.sec == 'Bay_NW_270-315').astype(int)
B['grp'] = B.date.dt.strftime('%Y%m%d')
B['lWS'] = np.log(B.WS)
print('\nRegression (log conc; controls hour-of-day, month, year, ln WS; SE clustered by day):')
for y in ['lNO2', 'lPM']:
    m = smf.ols(f'{y} ~ bay + C(hour) + C(month) + C(year) + lWS', B).fit(cov_type='cluster', cov_kwds={'groups': B.grp})
    ci = np.exp(m.conf_int().loc['bay'])
    print(f'{y}: bay vs all other sectors: ratio={np.exp(m.params["bay"]):.3f} 95%CI[{ci[0]:.3f},{ci[1]:.3f}] p={m.pvalues["bay"]:.2e}')
    m2 = smf.ols(f'{y} ~ C(sec, Treatment("East_45-135")) + C(hour) + C(month) + C(year) + lWS', B).fit(cov_type='cluster', cov_kwds={'groups': B.grp})
    print('  ratios vs East sector:', np.exp(m2.params.filter(like='sec')).round(3).to_dict())
for v in ['NO2_ug', 'PM2.5']:
    b = A[A.sec == 'Bay_NW_270-315'][v].mean()
    print(f'{v}: RAW bay/east={b / A[A.sec == "East_45-135"][v].mean():.3f} bay/all-other={b / A[A.sec != "Bay_NW_270-315"][v].mean():.3f}')
A['wsb'] = pd.cut(A.WS, [0.5, 1, 2, 3, 10])
print('\nMeans by wind-speed bin, bay (True) vs other:')
print(A.assign(bay=A.sec == 'Bay_NW_270-315').groupby(['wsb', 'bay'], observed=True)[['NO2_ug', 'PM2.5']].mean().unstack().round(2).to_string())
print('\nShare of hours with 270-315 by season/time-of-day:')
print(A.assign(b=A.sec == 'Bay_NW_270-315').groupby(['season', 'tod']).b.mean().round(3).to_string())

# ================= 3. Ozone vs WHO 2021 =================
print('\n===== 3. Ozone =====')
for T in [25, 20]:
    print(f'ppb->ug/m3 factor for O3 at {T}C: {48.0 / (0.082057 * (273.15 + T)):.3f}')


def o3_table(col, label):
    o = W[col]
    r8 = o.rolling(8, min_periods=6).mean()     # trailing 8h mean, stamped at last hour, >=6 of 8 valid
    D = pd.DataFrame({'r8': r8, 'o': o})
    D['date'] = D.index.normalize()
    g = D.groupby('date').agg(mda8=('r8', 'max'), n8=('r8', 'count'), peak=('o', 'max'))
    g = g[g.n8 >= 18]                            # day needs >=18 of 24 running means
    g['year'] = g.index.year
    g['month'] = g.index.month
    out = []
    for y, d in g.groupby('year'):
        out.append(dict(year=y, valid_days=len(d), days_gt100=int((d.mda8 > 100).sum()), days_gt140=int((d.mda8 > 140).sum()),
                        max_mda8=d.mda8.max(), date_max=str(d.mda8.idxmax().date()), p99_mda8=d.mda8.quantile(.99),
                        peak_hourly=d.peak.max(), peak_hourly_date=str(d.peak.idxmax().date()), annual_mean=W.loc[W.year == y, col].mean()))
    print(label)
    print(pd.DataFrame(out).round(1).to_string(index=False))
    return g


g = o3_table('O3_ug', 'O3 in ug/m3 (25C, 1 atm), MDA8 from trailing 8h means:')
print('\nJJA peak hourly O3 (ug/m3):')
print(W[W.season == 'summer'].groupby('year')['O3_ug'].agg(['max', 'idxmax']).round(1).to_string())
print('\nMay-Oct peak hourly O3 (ug/m3):')
print(W[W.month.isin([5, 6, 7, 8, 9, 10])].groupby('year')['O3_ug'].agg(['max', 'idxmax']).round(1).to_string())

mm = g.groupby([g.index.year, g.index.month]).mda8.mean()
mm.index = pd.PeriodIndex([pd.Period(f'{a}-{b:02d}') for a, b in mm.index], freq='M')
m6 = mm.rolling(6).mean()
print('\nWHO peak-season metric (highest 6-month moving average of monthly mean MDA8):')
for y in range(2021, 2027):
    sub = m6[(m6.index >= pd.Period(f'{y}-06')) & (m6.index <= pd.Period(f'{y}-12'))]
    if len(sub):
        print(y, round(sub.max(), 1), 'window ending', sub.idxmax())
print('\nmonthly mean of daily MDA8:')
print(g.groupby(['year', 'month']).mda8.mean().unstack().round(0).to_string())
print('\nhour-of-day (stamp) at which 8h running mean >100 ends:')
r8 = W['O3_ug'].rolling(8, min_periods=6).mean()
print(r8[r8 > 100].index.hour.value_counts().sort_index().to_dict())

print('\nVALIDATION against published 2021 association report (annual mean 70.3; max 8h 147.7; 2 values >140):')
for T in [25, 20]:
    f = 48.0 / (0.082057 * (273.15 + T))
    r = (W['O3'] * f).rolling(8, min_periods=6).mean()
    r21 = r[r.index.year == 2021]
    print(f'@{T}C annual mean={(W.loc[W.year == 2021, "O3"] * f).mean():.1f}; max 8h={r21.max():.1f}; hours with 8h>140={(r21 > 140).sum()}; top3={r21.nlargest(3).round(1).to_dict()}')
