"""Round-5b: is the heavier NO2/NOx upper tail in the 305-335 and 335-45 sectors still there after adjusting for hour, month, year, wind-speed bin?
Linear probability model (indicator of exceeding the overall P99 / P95), day-clustered SEs; plus per-sector tail share by season and hour group."""
import sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
sys.stdout.reconfigure(encoding='utf-8')
IDX = pd.date_range('2021-01-01 00:00', '2026-10-17 09:00', freq='h')
L = pd.read_csv('tivon_hourly_long_2021-2026.csv'); L['t'] = pd.to_datetime(L.datetime.str[:19]); L.loc[~L.valid, 'value'] = np.nan
tv = L.pivot_table(index='t', columns='channel', values='value', aggfunc='first').reindex(IDX)
tv['hour'] = tv.index.hour; tv['month'] = tv.index.month; tv['year'] = tv.index.year; tv['g'] = tv.index.strftime('%Y%m%d')
tv['NO2u'] = tv.NO2 * 46.0055 / 24.4655; tv['NOx_ug'] = tv.NOX * 46.0055 / 24.4655
wd = tv.WD
tv['sub'] = np.select([(wd >= 270) & (wd < 305), (wd >= 305) & (wd < 335), (wd >= 335) | (wd < 45), (wd >= 45) & (wd < 270)], ['s270_305', 's305_335', 's335_45', 'rest'], 'none')
d = tv[(tv.WS >= 0.5) & tv.WD.notna()].copy()
d['wsb'] = pd.cut(d.WS, [0.5, 1, 3, 6, 50], right=False, labels=['a', 'b', 'c', 'd'])
for ch, lab in [('NO2u', 'NO2'), ('NOx_ug', 'NOx')]:
    x = d.dropna(subset=[ch, 'wsb']).copy()
    for q in (.95, .99):
        th = x[ch].quantile(q)
        x['hi'] = (x[ch] > th).astype(float)
        m = smf.ols('hi ~ C(sub, Treatment("rest")) + C(wsb) + C(hour) + C(month) + C(year)', x).fit(cov_type='cluster', cov_kwds={'groups': x.g})
        base = x[x['sub'] == 'rest'].hi.mean()
        out = ['%s %+.2f pp [%.2f,%.2f]' % (k.split('T.')[1].rstrip(']'), 100 * m.params[k], *(100 * m.conf_int().loc[k])) for k in m.params.index if k.startswith('C(sub')]
        print('%s > P%d (%.1f): reference-sector rate %.2f%%; adjusted difference: %s' % (lab, int(q * 100), th, 100 * base, '; '.join(out)))
x = d.dropna(subset=['NO2u']).copy(); th = x.NO2u.quantile(.99); x['hi'] = x.NO2u > th
x['grp'] = np.where(x.month.isin([12, 1, 2]), 'DJF', np.where(x.month.isin([6, 7, 8]), 'JJA', 'MAM+SON')) + np.where(x.hour.between(10, 17), ' day', ' night')
print('\nNO2 > P99 share of hours by sector and season/time group (percent of hours in that cell):')
print((x.groupby(['grp', 'sub']).hi.mean().unstack() * 100).round(2).to_string())
print('\nn hours per cell:'); print(x.groupby(['grp', 'sub']).size().unstack().to_string())
