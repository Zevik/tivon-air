"""Within-day test: do ridge temperature / valley-ridge difference explain the night & evening PM2.5 excess vs noon, holding the day fixed?"""
import sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.stdout.reconfigure(encoding='utf-8')
IDX = pd.date_range('2021-01-01 00:00', '2026-10-17 09:00', freq='h')


def load(f):
    L = pd.read_csv(f)
    L['t'] = pd.to_datetime(L.datetime.str[:19])
    L.loc[~L.valid, 'value'] = np.nan
    return L.pivot_table(index='t', columns='channel', values='value', aggfunc='first').reindex(IDX)


tv = load('tivon_hourly_long_2021-2026.csv')
ca = load('carmelpark_st69_hourly_2021-2026.csv')
af = load('afula_st1_hourly_2021-2026.csv')
d = pd.DataFrame({'pm': tv['PM2.5'], 'pm10': tv['PM10'], 'ws': tv['WS'], 'Tc': ca['Temp'], 'RHc': ca['RH'], 'Ta': af['Temp']})
d['dT'] = d.Ta - d.Tc
d['hour'] = d.index.hour
d['date'] = d.index.normalize()
dm = d.groupby('date').agg(a=('pm10', 'mean'), b=('pm', 'mean'))
dust = (dm.a > 80) | (dm.b > 37.5) | ((dm.a > 50) & (dm.b / dm.a < 0.35))
dust = dust | dust.shift(1, fill_value=False)
w = d[d.index.month.isin([12, 1, 2]) & ~d.date.map(dust)].copy()
w['per'] = np.select([w.hour.between(0, 5), w.hour.between(12, 16), w.hour.between(18, 23)], ['night', 'noon', 'eve'], 'other')
w = w[w.per != 'other'].dropna(subset=['pm', 'ws', 'Tc', 'RHc', 'dT'])
w = w[(w.pm > 0.5) & (w.ws > 0.2)]
w['lp'] = np.log(w.pm)
w['lws'] = np.log(w.ws)
w['g'] = w.date.dt.strftime('%Y%m%d')
print('rows', len(w), 'days', w.g.nunique())
for f, lab in [('lp ~ C(per, Treatment("noon")) + C(g)', 'day FE only'),
               ('lp ~ C(per, Treatment("noon")) + lws + C(g)', 'day FE + ln WS'),
               ('lp ~ C(per, Treatment("noon")) + lws + Tc + RHc + C(g)', 'day FE + ln WS + T + RH'),
               ('lp ~ C(per, Treatment("noon")) + lws + Tc + RHc + dT + C(g)', 'day FE + ln WS + T + RH + dT')]:
    m = smf.ols(f, w).fit(cov_type='cluster', cov_kwds={'groups': w.g})
    out = []
    for k in m.params.index:
        if k.startswith('C(per'):
            out.append(f'{k.split("T.")[1].rstrip("]")}: x{np.exp(m.params[k]):.3f} [{np.exp(m.conf_int().loc[k][0]):.3f},{np.exp(m.conf_int().loc[k][1]):.3f}]')
    extra = [f'{c}: {m.params[c]:+.4f} p={m.pvalues[c]:.1e}' for c in ['lws', 'Tc', 'RHc', 'dT'] if c in m.params.index]
    print(f'[{lab}] vs noon -> ' + '; '.join(out) + ' | ' + '; '.join(extra))
