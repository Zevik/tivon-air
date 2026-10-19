"""Round-3 checks: (A1) station 344 vs 137 and the 25.9.2026 benzene peak, (A2) PM2.5/NOx profile and NOx control in the winter night regression,
(B4) effect of Afula's July-2024 gap on the 3-station intersection."""
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
mb = load('mobile344_alroei_2026.csv', pd.date_range('2026-01-01', '2026-10-17 09:00', freq='h'))

print('===== A1. station 344 vs 137 =====')
c = mb.join(tv, how='left', lsuffix='_344', rsuffix='_137')
ppb = {'NO2': 46.0055, 'NOX': 46.0055, 'O3': 48.0}
for k in ['NO2', 'NOX', 'O3']:
    for s in ['_344', '_137']:
        c[k + s + 'u'] = c[k + s] * ppb[k] / 24.4655
periods = {'Jan-Mar': ('2026-01-01', '2026-03-31'), 'Apr-Jun': ('2026-04-01', '2026-06-30'), 'Jul-Aug': ('2026-07-01', '2026-08-31'), 'Sep1-24': ('2026-09-01', '2026-09-24'),
           'Sep25-26': ('2026-09-25', '2026-09-26'), 'Sep27-Oct17': ('2026-09-27', '2026-10-17')}


def circ_diff(a, b):
    d = (a - b + 180) % 360 - 180
    return d


rows = []
for lab, (a, b) in periods.items():
    x = c[a:b]
    r = {'period': lab, 'hours': len(x)}
    for v, (v1, v2) in {'WS': ('WS_344', 'WS_137'), 'O3': ('O3_344u', 'O3_137u'), 'NO2': ('NO2_344u', 'NO2_137u'), 'NOX': ('NOX_344u', 'NOX_137u'), 'PM2.5': ('PM2.5_344', 'PM2.5_137')}.items():
        z = x[[v1, v2]].dropna()
        r[v + '_corr'] = round(z[v1].corr(z[v2]), 2) if len(z) > 10 else np.nan
        r[v + '_mean344/137'] = '%.1f/%.1f' % (z[v1].mean(), z[v2].mean())
    wd = x[['WD_344', 'WD_137']].dropna()
    r['WD_absdiff_median'] = round(circ_diff(wd.WD_344, wd.WD_137).abs().median(), 0)
    rows.append(r)
print(pd.DataFrame(rows).T.to_string())

# night vs day decoupling (Jan-Oct 17 and Sep27-Oct17)
for lab, (a, b) in {'all 2026': ('2026-01-01', '2026-10-17'), 'Sep27-Oct17': ('2026-09-27', '2026-10-17')}.items():
    x = c[a:b]
    night = x[x.index.hour.isin([0, 1, 2, 3, 4, 5])]
    day = x[(x.index.hour >= 11) & (x.index.hour <= 16)]
    print('\n', lab)
    for nm, d in [('night 00-05', night), ('day 11-16', day)]:
        z = d[['WS_344', 'WS_137', 'WD_344', 'WD_137']].dropna()
        print('  %-12s WS 344 %.2f vs 137 %.2f | corr WS %.2f | median |dWD| %.0f deg | share |dWD|>90: %.2f' % (nm, z.WS_344.mean(), z.WS_137.mean(), z.WS_344.corr(z.WS_137), circ_diff(z.WD_344, z.WD_137).abs().median(), (circ_diff(z.WD_344, z.WD_137).abs() > 90).mean()))
        for v in ['PM2.5', 'NO2', 'NOX', 'O3']:
            a1 = d[v + '_344' if v == 'PM2.5' else v + '_344u'].mean()
            a2 = d[v + '_137' if v == 'PM2.5' else v + '_137u'].mean()
            print('     %s mean 344 %.1f / 137 %.1f  ratio %.2f' % (v, a1, a2, a1 / a2))
# SO2 / H2S
for v in ['SO2', 'H2S']:
    s = mb[v]['2026-09-27':]
    print('\n%s since 27.9 (ppb): mean %.2f p99 %.2f max %.2f valid %d; all-2026 mean %.2f max %.2f' % (v, s.mean(), s.quantile(.99), s.max(), s.notna().sum(), mb[v].mean(), mb[v].max()))
# trapping: night NOx 344 minus 137 in winter-like calm nights
x = c['2026-09-27':]
n = x[x.index.hour.isin(range(0, 6))]
print('\nNight (00-05) hours since 27.9 with 137 WS<1:', int((n.WS_137 < 1).sum()), '| NOx ug 344/137 in those hours: %.1f / %.1f' % (n[n.WS_137 < 1].NOX_344u.mean(), n[n.WS_137 < 1].NOX_137u.mean()))

# Sept data availability and gaps for 344
print('\n--- station 344 data continuity, Sept 2026 (valid benzene hours per day) ---')
b = mb['Benzene']['2026-09-15':'2026-10-02']
cnt = b.groupby(b.index.normalize()).apply(lambda s: int(s.notna().sum()))
print(cnt.to_dict())
allv = mb['2026-09-01':'2026-10-17'][['Benzene', 'NO2', 'O3', 'PM2.5', 'WS']].notna().all(axis=1)
miss = (~allv)
runs = []
start = None
for t, m_ in miss.items():
    if m_ and start is None:
        start = t
    if (not m_) and start is not None:
        runs.append((start, t - pd.Timedelta(hours=1)))
        start = None
print('gaps (any key channel missing) Sep1-Oct17, runs >=3h:', [(str(a), str(b2), int((b2 - a) / pd.Timedelta(hours=1)) + 1) for a, b2 in runs if (b2 - a) >= pd.Timedelta(hours=2)])
# the hours of the benzene peak
print('\nbenzene hourly around 25.9 (ug/m3 at 25C) with WS, WD, PM2.5, NOx:')
z = mb['2026-09-24 22:00':'2026-09-25 10:00'][['Benzene', 'WS', 'WD', 'NOX', 'PM2.5', 'O3', 'SO2', 'H2S']].copy()
z['Benzene'] = (z['Benzene'] * 3.193).round(1)
print(z.round(1).to_string())
# weekly stability of (344-137) NOx ratio and corr to detect relocation
w = c['2026-08-01':].copy()
w['wk'] = w.index.to_period('W')
g = w.groupby('wk').apply(lambda d: pd.Series({'NO2corr': d.NO2_344u.corr(d.NO2_137u), 'O3corr': d.O3_344u.corr(d.O3_137u), 'WScorr': d.WS_344.corr(d.WS_137), 'PMcorr': d['PM2.5_344'].corr(d['PM2.5_137']),
                                                'NO2ratio': d.NO2_344u.mean() / d.NO2_137u.mean(), 'O3diff': d.O3_344u.mean() - d.O3_137u.mean(), 'n': len(d)}))
print('\nweekly 344-vs-137 relation (weeks starting):'); print(g.round(2).to_string())

# ================= A2. PM2.5/NOx =================
print('\n===== A2. winter PM2.5/NOx profile and NOx control =====')
tv['NOx_ug'] = tv['NOX'] * 46.0055 / 24.4655
tv['hour'] = tv.index.hour
tv['month'] = tv.index.month
tv['date'] = tv.index.normalize()
dm = tv.groupby('date').agg(a=('PM10', 'mean'), b=('PM2.5', 'mean'))
dust = (dm.a > 80) | (dm.b > 37.5) | ((dm.a > 50) & (dm.b / dm.a < 0.35))
dust = dust | dust.shift(1, fill_value=False)
tv['dust'] = tv.date.map(dust)
w = tv[tv.month.isin([12, 1, 2]) & ~tv.dust].copy()
prof = w.groupby('hour').agg(pm=('PM2.5', 'mean'), nox=('NOx_ug', 'mean'), no2=('NO2', 'mean'))
prof['pm_over_nox'] = prof.pm / prof.nox
print('winter non-dust hourly mean PM2.5, NOx (ug/m3, 25C), PM2.5/NOx:'); print(prof[['pm', 'nox', 'pm_over_nox']].round(2).T.to_string())
w['lp'] = np.log(w['PM2.5'].where(w['PM2.5'] > 0.5))
w['lnox'] = np.log(w['NOx_ug'].where(w['NOx_ug'] > 0.5))
w['lws'] = np.log(w['WS'].where(w['WS'] > 0.2))
ca = load('carmelpark_st69_hourly_2021-2026.csv')
af = load('afula_st1_hourly_2021-2026.csv')
w['Tc'] = ca['Temp']
w['RHc'] = ca['RH']
w['dT'] = af['Temp'] - ca['Temp']
w['per'] = np.select([w.hour.between(0, 5), w.hour.between(12, 16), w.hour.between(18, 23)], ['night', 'noon', 'eve'], 'other')
w = w[w.per != 'other'].dropna(subset=['lp', 'lnox', 'lws', 'Tc', 'RHc', 'dT']).copy()
w['g'] = w.date.dt.strftime('%Y%m%d')
print('rows', len(w), 'days', w.g.nunique())
for f, lab in [('lp ~ C(per, Treatment("noon")) + C(g)', 'day FE'),
               ('lp ~ C(per, Treatment("noon")) + lws + Tc + RHc + dT + C(g)', 'day FE + WS + T + RH + dT (previous full model)'),
               ('lp ~ C(per, Treatment("noon")) + lnox + C(g)', 'day FE + lnNOx'),
               ('lp ~ C(per, Treatment("noon")) + lws + Tc + RHc + dT + lnox + C(g)', 'day FE + full + lnNOx')]:
    m = smf.ols(f, w).fit(cov_type='cluster', cov_kwds={'groups': w.g})
    out = []
    for k in m.params.index:
        if k.startswith('C(per'):
            out.append('%s x%.3f [%.3f,%.3f]' % (k.split('T.')[1].rstrip(']'), np.exp(m.params[k]), *np.exp(m.conf_int().loc[k])))
    ex = ' | lnNOx coef %.3f (p=%.1e)' % (m.params['lnox'], m.pvalues['lnox']) if 'lnox' in m.params.index else ''
    print('[%s] vs noon: %s%s' % (lab, '; '.join(out), ex))
# NOx by period (supports the traffic-decline premise)
print('NOx mean by period (winter non-dust):', w.groupby('per').NOx_ug.mean().round(1).to_dict(), '| PM/NOx ratio by period:', (w.groupby('per')['PM2.5'].mean() / w.groupby('per').NOx_ug.mean()).round(2).to_dict())

# ================= B4. intersection loss =================
print('\n===== B4. 3-station intersection loss =====')
at = load('kataa_st88_hourly_2021-2026.csv')


def mda8(s):
    r = s.rolling(8, min_periods=6).mean()
    g = pd.DataFrame({'r': r}).groupby(r.index.normalize()).agg(m=('r', 'max'), n=('r', 'count'))
    return g[g.n >= 18]['m']


T = mda8(tv['O3'] * 1.886)
A = mda8(at['O3'] * 1.934)
F = mda8(af['O3'] * 1.950)
T = T[T.index.year <= 2025]
both = T.index.intersection(A.index).intersection(F.index)
lost = T.index.difference(both)
print('Tivon valid days 2021-25', len(T), '| in 3-station intersection', len(both), '| lost', len(lost))
print('Tivon days>100 (A): total', int((T > 100).sum()), 'in intersection', int((T.loc[both] > 100).sum()), 'lost', int((T.loc[lost] > 100).sum()))
lm = pd.Series(1, index=lost).groupby([lost.year, lost.month]).sum()
print('lost days by year-month (top):', lm.sort_values(ascending=False).head(8).to_dict())
lost_af = T.index.difference(F.index)
lost_at = T.index.difference(A.index)
print('days missing only because of Afula:', len(lost_af), '| because of Ata:', len(lost_at))
fj = af['O3']['2024-07']
print('Afula Jul 2024 valid O3 hours share:', round(fj.notna().mean(), 3), '| valid MDA8 days in Jul 2024:', int(((F.index.year == 2024) & (F.index.month == 7)).sum()))
print('Tivon days>100 (A) in Jul 2024:', int((T[(T.index.year == 2024) & (T.index.month == 7)] > 100).sum()), 'of', int(((T.index.year == 2024) & (T.index.month == 7)).sum()))
print('lost-days>100 by month:', pd.Series((T.loc[lost] > 100).values, index=lost).groupby([lost.year, lost.month]).sum().sort_values(ascending=False).head(6).to_dict())
