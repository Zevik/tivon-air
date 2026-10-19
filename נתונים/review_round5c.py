"""Round-5c: (A) NO2/NOx upper tail by sub-sector with a true-night definition (00-05) separated from morning rush (06-09), midday (10-17), evening (18-23);
(B) 2024 PM2.5: is the API-official gap a uniform scale factor? compare API monthly means with the three official monthly reports (Jul, Aug, Dec 2024)."""
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
d['tod'] = np.select([d.hour.between(0, 5), d.hour.between(6, 9), d.hour.between(10, 17), d.hour.between(18, 23)], ['night00-05', 'morning06-09', 'midday10-17', 'evening18-23'], 'x')
d['season'] = np.where(d.month.isin([12, 1, 2]), 'DJF', np.where(d.month.isin([6, 7, 8]), 'JJA', 'MAM+SON'))
for ch, lab in [('NO2u', 'NO2'), ('NOx_ug', 'NOx')]:
    x = d.dropna(subset=[ch, 'wsb']).copy(); th = x[ch].quantile(.99); x['hi'] = (x[ch] > th).astype(float)
    print('=====', lab, '> overall P99 (%.1f); percent of hours above, by sector, season x time-of-day =====' % th)
    print((x.groupby(['season', 'tod', 'sub']).hi.mean().unstack() * 100).round(2).to_string())
    print('hours per cell (min over sectors):', int(x.groupby(['season', 'tod', 'sub']).size().min()))
    # adjusted by time-of-day group
    for tod in ['night00-05', 'morning06-09', 'midday10-17', 'evening18-23']:
        y = x[x.tod == tod]
        m = smf.ols('hi ~ C(sub, Treatment("rest")) + C(wsb) + C(month) + C(year) + C(hour)', y).fit(cov_type='cluster', cov_kwds={'groups': y.g})
        out = ['%s %+.2f pp [%.2f,%.2f]' % (k.split('T.')[1].rstrip(']'), 100 * m.params[k], *(100 * m.conf_int().loc[k])) for k in m.params.index if k.startswith('C(sub')]
        print('  adjusted %-13s rest-rate %.2f%% | %s' % (tod, 100 * y[y['sub'] == 'rest'].hi.mean(), '; '.join(out)))
    w = x[x.month.isin([12, 1, 2, 3, 4, 5, 9, 10, 11])]
    y = w[w.tod == 'night00-05']
    print('  non-summer true-night 00-05 share in sectors:', (y.groupby('sub').hi.mean() * 100).round(2).to_dict(), 'n:', y.groupby('sub').size().to_dict())

print('\n===== B. 2024 PM2.5, Tivon: API monthly means vs official monthly reports =====')
p = tv['PM2.5']
p24 = p[p.index.year == 2024]
mm = p24.resample('MS').agg(['mean', 'count'])
mm['pct_valid'] = (100 * mm['count'] / p24.resample('MS').size()).round(1)
print(mm.round(2).to_string())
print('API 2024 annual mean (valid hours): %.2f ; hours valid %d of %d (%.1f%%)' % (p24.mean(), p24.count(), len(p24), 100 * p24.count() / len(p24)))
off = {7: 12.7, 8: 11.8, 12: 19.7}
for m_, v in off.items():
    a = mm['mean'].iloc[m_ - 1]
    print('month %d: API %.2f vs official %.1f -> diff %+.2f (ratio %.3f)' % (m_, a, v, a - v, a / v))
other = [i for i in range(1, 13) if i not in off]
need = (15.4 * 12 - sum(off.values()) - 0) / len(other)
print('If the official annual is 15.4 and the three official months are as reported, the other 9 months would need to average %.2f; API average of those months %.2f' % (need, mm['mean'].iloc[[i - 1 for i in other]].mean()))
