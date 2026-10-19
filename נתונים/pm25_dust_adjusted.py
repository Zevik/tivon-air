"""Winter evening-vs-noon PM2.5 after excluding dust days and controlling for wind speed."""
import sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.stdout.reconfigure(encoding='utf-8')
L = pd.read_csv('tivon_hourly_long_2021-2026.csv')
L['t'] = pd.to_datetime(L.datetime.str[:19])
L.loc[~L.valid, 'value'] = np.nan
W = L.pivot_table(index='t', columns='channel', values='value', aggfunc='first')
W = W.reindex(pd.date_range(W.index.min(), W.index.max(), freq='h'))
W['date'] = W.index.normalize()
W['hour'] = W.index.hour
W['month'] = W.index.month
W['year'] = W.index.year
day = W.groupby('date').agg(pm25=('PM2.5', 'mean'), pm10=('PM10', 'mean'))
day['ratio'] = day.pm25 / day.pm10
# dust day: daily PM10 > 80 or PM2.5 > 37.5 or (PM10>50 and PM2.5/PM10<0.35); also drop the following day
dust = (day.pm10 > 80) | (day.pm25 > 37.5) | ((day.pm10 > 50) & (day.ratio < 0.35))
dust = dust | dust.shift(1, fill_value=False)
print('dust-flagged days:', int(dust.sum()), 'of', len(day), ' winter:', int(dust[dust.index.month.isin([12, 1, 2])].sum()))
W['dust'] = W.date.map(dust)
for lab, d in [('all winter hours', W[W.month.isin([12, 1, 2])]), ('winter excl. dust days', W[W.month.isin([12, 1, 2]) & ~W.dust])]:
    ev = d[(d.hour >= 18) & (d.hour <= 23)]['PM2.5'].mean()
    no = d[(d.hour >= 12) & (d.hour <= 16)]['PM2.5'].mean()
    print(f'{lab}: evening {ev:.2f} noon {no:.2f} ratio {ev / no:.3f}')
for lab, d in [('summer excl. dust days', W[W.month.isin([6, 7, 8]) & ~W.dust])]:
    ev = d[(d.hour >= 18) & (d.hour <= 23)]['PM2.5'].mean()
    no = d[(d.hour >= 12) & (d.hour <= 16)]['PM2.5'].mean()
    print(f'{lab}: evening {ev:.2f} noon {no:.2f} ratio {ev / no:.3f}')
# regression: ln PM2.5 on evening dummy, winter non-dust, controlling month/year/ln WS, clustered by day
d = W[W.month.isin([12, 1, 2]) & ~W.dust & ((W.hour.between(18, 23)) | (W.hour.between(12, 16)))].dropna(subset=['PM2.5', 'WS']).copy()
d = d[(d['PM2.5'] > 0.5) & (d.WS > 0.2)]
d['eve'] = d.hour.between(18, 23).astype(int)
d['lp'] = np.log(d['PM2.5'])
d['lws'] = np.log(d.WS)
d['g'] = d.date.dt.strftime('%Y%m%d')
for f, lab in [('lp ~ eve + C(month) + C(year)', 'no wind control'), ('lp ~ eve + C(month) + C(year) + lws', 'with ln WS control')]:
    m = smf.ols(f, d).fit(cov_type='cluster', cov_kwds={'groups': d.g})
    ci = np.exp(m.conf_int().loc['eve'])
    print(f'{lab}: evening/noon ratio={np.exp(m.params["eve"]):.3f} CI[{ci[0]:.3f},{ci[1]:.3f}] p={m.pvalues["eve"]:.2e}')
# same restricted to hours with similar low wind (WS<=1.5)
dd = d[d.WS <= 1.5]
for lab, x in [('WS<=1.5 only', dd)]:
    ev = x[x.eve == 1]['PM2.5'].mean()
    no = x[x.eve == 0]['PM2.5'].mean()
    print(f'{lab}: evening {ev:.2f} (n={int((x.eve == 1).sum())}) noon {no:.2f} (n={int((x.eve == 0).sum())}) ratio {ev / no:.3f}')
