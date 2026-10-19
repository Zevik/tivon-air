"""Round-2 analysis: Tivon (137) vs Afula (1) vs Kiryat Ata (88); temperature/humidity proxies (Carmel Park 69, Afula 1); stagnation bivariate analysis.
Run: python -I analyze_round2.py"""
import sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 220)
pd.set_option('display.max_columns', 40)

FILES = {'Tivon': 'tivon_hourly_long_2021-2026.csv', 'Afula': 'afula_st1_hourly_2021-2026.csv',
         'Ata': 'kataa_st88_hourly_2021-2026.csv', 'Carmel': 'carmelpark_st69_hourly_2021-2026.csv'}
IDX = pd.date_range('2021-01-01 00:00', '2026-10-17 09:00', freq='h')


def load(f):
    L = pd.read_csv(f)
    L['t'] = pd.to_datetime(L.datetime.str[:19])
    L.loc[~L.valid, 'value'] = np.nan
    W = L.pivot_table(index='t', columns='channel', values='value', aggfunc='first').reindex(IDX)
    return W


S = {k: load(v) for k, v in FILES.items()}
F = 1.9618 * 0.965          # ppb -> ug/m3 for O3 (25C factor x ministry calibration)
FN = 1.9618
F_NO2 = 46.0055 / (0.082057 * 298.15) * 0.965
for k, W in S.items():
    if 'O3' in W:
        W['O3c'] = W['O3'] * F
        W['O3n'] = W['O3'] * FN
    if 'NO2' in W:
        W['NO2u'] = W['NO2'] * F_NO2
    W['hour'] = W.index.hour
    W['month'] = W.index.month
    W['year'] = W.index.year
    W['date'] = W.index.normalize()


def mda8(series, minp=6):
    r = series.rolling(8, min_periods=minp).mean()
    g = pd.DataFrame({'r': r}).groupby(r.index.normalize()).agg(m=('r', 'max'), n=('r', 'count'))
    return g[g.n >= 18]['m']


print('===== 0. station facts =====')
for k in S:
    W = S[k]
    cols = [c for c in ['O3', 'NO2', 'PM2.5', 'PM10', 'WD', 'WS', 'Temp', 'RH'] if c in W]
    print(k, 'valid share:', {c: round(W[c].notna().mean(), 3) for c in cols})

# ---------------- 1+2 ozone three-station ----------------
print('\n===== 1+2. OZONE (calibrated ug/m3; nominal in brackets) =====')
M = {k: mda8(S[k]['O3c']) for k in ['Tivon', 'Afula', 'Ata', 'Carmel']}
Mn = {k: mda8(S[k]['O3n']) for k in ['Tivon', 'Afula', 'Ata', 'Carmel']}
rows = []
for k in M:
    for y in range(2021, 2027):
        m = M[k][M[k].index.year == y]
        mn = Mn[k][Mn[k].index.year == y]
        W = S[k]
        wy = W[W.year == y]
        jja = wy[wy.month.isin([6, 7, 8])]['O3c']
        rows.append(dict(st=k, year=y, days=len(m), gt100=int((m > 100).sum()), gt100_nom=int((mn > 100).sum()), gt140=int((m > 140).sum()),
                         max_mda8=round(m.max(), 1), p99=round(m.quantile(.99), 1), mean=round(wy['O3c'].mean(), 1), jja_peak_hr=round(jja.max(), 1)))
T = pd.DataFrame(rows)
print(T.to_string(index=False))
print('\nValidation vs 2025 annual report (Ata: mean 77.3, max8h 132, 0 exceedances of 140; Tivon: 76.0/150/3):')
print(T[(T.year == 2025)].to_string(index=False))
# pooled 2021-2025 per station
print('\nPooled 2021-2025 days MDA8>100 per year (calibrated), valid days:')
for k in M:
    m = M[k][M[k].index.year <= 2025]
    print(k, len(m), int((m > 100).sum()), 'per yr', round((m > 100).sum() / 5, 1), '| mean MDA8 JJA', round(m[m.index.month.isin([6, 7, 8])].mean(), 1), '| mean MDA8 all', round(m.mean(), 1))
# co-occurrence on summer-half-year days
J = pd.DataFrame({k: M[k] for k in ['Tivon', 'Afula', 'Ata']}).dropna()
J = J[J.index.year <= 2025]
print('\nDays with all three valid:', len(J))
for a, b in [('Tivon', 'Afula'), ('Tivon', 'Ata'), ('Ata', 'Afula')]:
    print(f'P({b}>100 | {a}>100) = {(J[b][J[a] > 100] > 100).mean():.3f};  corr MDA8 {a}-{b} = {J[a].corr(J[b]):.3f}')
print('Mean MDA8 on days Tivon>100:', J[J.Tivon > 100].mean().round(1).to_dict())
# 'gt100' joint
print('Joint >100: all three', int(((J > 100).all(axis=1)).sum()), '| Tivon only', int(((J.Tivon > 100) & (J.Afula <= 100) & (J.Ata <= 100)).sum()),
      '| Afula only', int(((J.Afula > 100) & (J.Tivon <= 100) & (J.Ata <= 100)).sum()), '| Ata only', int(((J.Ata > 100) & (J.Tivon <= 100) & (J.Afula <= 100)).sum()))

# timing of peaks (JJA and May-Sep high-ozone days)
print('\n--- timing of daily hourly-ozone peak (standard time UTC+2), JJA, days when station peak hourly >= 100 ug/m3 ---')
pk = {}
for k in ['Tivon', 'Afula', 'Ata']:
    o = S[k]['O3c']
    o = o[o.index.month.isin([6, 7, 8])]
    d = o.groupby(o.index.normalize())
    pk[k] = pd.DataFrame({'hr': d.apply(lambda s: s.idxmax().hour if s.notna().sum() >= 18 else np.nan), 'max': d.max()})
P = pd.concat({k: v for k, v in pk.items()}, axis=1).dropna()
P = P[(P[('Tivon', 'max')] >= 100) & (P[('Afula', 'max')] >= 100) & (P[('Ata', 'max')] >= 100)]
print('days', len(P))
for k in ['Tivon', 'Afula', 'Ata']:
    print(k, 'median peak hour', P[(k, 'hr')].median(), 'mean', round(P[(k, 'hr')].mean(), 2))
rng = np.random.default_rng(1)
for a, b in [('Afula', 'Tivon'), ('Tivon', 'Ata'), ('Afula', 'Ata')]:
    d = (P[(a, 'hr')] - P[(b, 'hr')]).values
    bs = [rng.choice(d, len(d)).mean() for _ in range(2000)]
    print(f'peak hour {a} minus {b}: mean {d.mean():.2f} h, 95%CI[{np.percentile(bs, 2.5):.2f},{np.percentile(bs, 97.5):.2f}], median {np.median(d):.1f}')
prof = pd.DataFrame({k: S[k][S[k].month.isin([6, 7, 8])].groupby('hour')['O3c'].mean() for k in ['Tivon', 'Afula', 'Ata']})
print('JJA mean diurnal O3 by hour:'); print(prof.round(0).T.to_string())
print('hour of mean-profile max:', prof.idxmax().to_dict())
# lagged cross-correlation of hourly anomalies
print('\nLagged corr (hourly O3, JJA, hours 8-20; positive lag = second station lags first):')
for a, b in [('Afula', 'Tivon'), ('Tivon', 'Ata'), ('Ata', 'Afula')]:
    out = {}
    for lag in range(-4, 5):
        x = S[a]['O3c']
        y = S[b]['O3c'].shift(-lag)       # b at t+lag
        df = pd.concat([x, y], axis=1, keys=['x', 'y'])
        df = df[df.index.month.isin([6, 7, 8]) & df.index.hour.isin(range(8, 21))].dropna()
        # remove each station's hour-of-day mean to focus on day-to-day covariance
        xm = df.x - df.groupby(df.index.hour).x.transform('mean')
        ym = df.y - df.groupby(df.index.hour).y.transform('mean')
        out[lag] = round(xm.corr(ym), 3)
    best = max(out, key=out.get)
    print(f'{b} at t+lag vs {a} at t:', out, '-> best lag', best)

# ---------------- 2. PM2.5 / NO2 / PM10 comparisons ----------------
print('\n===== 2b. PM2.5, NO2, PM10 comparison =====')
rows = []
for k in ['Tivon', 'Ata']:
    W = S[k]
    d = W['PM2.5'].groupby(W.date).agg(['mean', 'count'])
    d = d[d['count'] >= 18]
    for y in range(2021, 2027):
        wy = W[W.year == y]
        dy = d[d.index.year == y]
        rows.append(dict(st=k, year=y, pm25_mean=round(wy['PM2.5'].mean(), 1), cov=round(wy['PM2.5'].notna().mean(), 3), days_gt15=int((dy['mean'] > 15).sum()),
                         days_gt37_5=int((dy['mean'] > 37.5).sum()), valid_days=len(dy)))
print(pd.DataFrame(rows).to_string(index=False))
print('\nNO2 annual means (calibrated ug/m3) and coverage:')
print(pd.DataFrame({k: S[k].groupby('year')['NO2u'].mean().round(1) for k in ['Tivon', 'Afula', 'Ata']}).to_string())
print(pd.DataFrame({k: S[k].groupby('year')['NO2u'].apply(lambda s: round(s.notna().mean(), 2)) for k in ['Tivon', 'Afula', 'Ata']}).to_string())
print('\nPM10 annual means:')
print(pd.DataFrame({k: S[k].groupby('year')['PM10'].mean().round(1) for k in ['Tivon', 'Afula', 'Ata']}).to_string())
for k in ['Tivon', 'Ata']:
    W = S[k]
    for s, mset in [('winter', [12, 1, 2]), ('summer', [6, 7, 8])]:
        d = W[W.month.isin(mset)]
        ev = d[d.hour.between(18, 23)]
        no = d[d.hour.between(12, 16)]
        print(f'{k} {s}: PM2.5 eve/noon = {ev["PM2.5"].mean() / no["PM2.5"].mean():.3f} ({ev["PM2.5"].mean():.1f}/{no["PM2.5"].mean():.1f}); NO2 eve/noon = {ev["NO2u"].mean() / no["NO2u"].mean():.2f}')
d = S['Afula']
for s, mset in [('winter', [12, 1, 2]), ('summer', [6, 7, 8])]:
    x = d[d.month.isin(mset)]
    print(f'Afula {s}: NO2 eve/noon = {x[x.hour.between(18, 23)]["NO2u"].mean() / x[x.hour.between(12, 16)]["NO2u"].mean():.2f}; PM10 eve/noon = {x[x.hour.between(18, 23)]["PM10"].mean() / x[x.hour.between(12, 16)]["PM10"].mean():.2f}')
# winter hourly profile PM2.5 comparison
wp = pd.DataFrame({k: S[k][S[k].month.isin([12, 1, 2])].groupby('hour')['PM2.5'].mean() for k in ['Tivon', 'Ata']})
print('Winter PM2.5 by hour:'); print(wp.round(1).T.to_string())
# Tivon vs Ata hourly correlation in winter
cc = pd.concat([S['Tivon']['PM2.5'], S['Ata']['PM2.5']], axis=1, keys=['tv', 'at'])
cc = cc[cc.index.month.isin([12, 1, 2])].dropna()
print('winter hourly corr PM2.5 Tivon-Ata:', round(cc['tv'].corr(cc['at']), 3), ' mean ratio Tivon/Ata:', round(cc['tv'].mean() / cc['at'].mean(), 3))

# ---------------- 3. Temp/RH proxies ----------------
print('\n===== 3. Temp/RH proxies (Tivon station exposes no Temp/RH channel) =====')
tv = S['Tivon'].copy()
tv['T_c'] = S['Carmel']['Temp']
tv['RH_c'] = S['Carmel']['RH']
tv['T_a'] = S['Afula']['Temp']
tv['RH_a'] = S['Afula']['RH']
tv['dT'] = tv['T_a'] - tv['T_c']                  # valley minus ridge (normal lapse ~ +3C); small/negative = inversion
tv['cool3'] = tv['T_c'] - tv['T_c'].shift(3)
dd = tv.groupby('date').agg(pm10=('PM10', 'mean'), pm25=('PM2.5', 'mean'))
dust = (dd.pm10 > 80) | (dd.pm25 > 37.5) | ((dd.pm10 > 50) & (dd.pm25 / dd.pm10 < 0.35))
dust = dust | dust.shift(1, fill_value=False)
tv['dust'] = tv.date.map(dust)
tv['lp'] = np.log(tv['PM2.5'].where(tv['PM2.5'] > 0.5))
tv['lws'] = np.log(tv['WS'].where(tv['WS'] > 0.2))
tv['g'] = tv.date.dt.strftime('%Y%m%d')
w = tv[tv.month.isin([12, 1, 2]) & ~tv.dust].copy()
print('winter non-dust hours:', len(w), '| valid Carmel T/RH share', round(w['T_c'].notna().mean(), 3), '| Afula T share', round(w['T_a'].notna().mean(), 3))
print('winter mean T (Carmel Park 527m / Afula 57m) by hour:')
print(w.groupby('hour')[['T_c', 'T_a', 'RH_c', 'RH_a', 'dT']].mean().round(1).T.to_string())
night = w[w.hour.between(0, 5)].dropna(subset=['lp', 'lws', 'T_c', 'RH_c', 'T_a', 'dT', 'cool3'])
print('night 00-05 hours used:', len(night))
print('simple corr with ln PM2.5 (night):', night[['lp', 'T_c', 'RH_c', 'T_a', 'dT', 'lws', 'cool3']].corr()['lp'].round(3).to_dict())
for f, lab in [('lp ~ T_c + RH_c + lws + C(month) + C(year)', 'ridge T, RH, ln WS'),
               ('lp ~ T_a + RH_a + lws + C(month) + C(year)', 'valley (Afula) T, RH, ln WS'),
               ('lp ~ dT + lws + C(month) + C(year)', 'inversion proxy dT (Afula-Carmel) + ln WS'),
               ('lp ~ T_c + RH_c + dT + cool3 + lws + C(month) + C(year)', 'all')]:
    d = night.dropna(subset=['T_a', 'RH_a']) if 'T_a' in f else night
    m = smf.ols(f, d).fit(cov_type='cluster', cov_kwds={'groups': d.g})
    keep = [c for c in m.params.index if not c.startswith('C(') and c != 'Intercept']
    print(f'-- night model [{lab}] n={int(m.nobs)} R2={m.rsquared:.3f}')
    for c in keep:
        sd = d[c].std()
        print(f'   {c}: coef={m.params[c]:.4f} (per unit; x{np.exp(m.params[c]):.3f}), per 1 SD ({sd:.2f}) x{np.exp(m.params[c] * sd):.3f}, p={m.pvalues[c]:.2e}')
# does adding T/RH/dT/WS explain the evening-vs-noon contrast?
ev = w[w.hour.between(18, 23) | w.hour.between(12, 16)].dropna(subset=['lp', 'lws', 'T_c', 'RH_c', 'dT']).copy()
ev['eve'] = ev.hour.between(18, 23).astype(int)
for f, lab in [('lp ~ eve + C(month) + C(year)', 'base'), ('lp ~ eve + lws + C(month) + C(year)', '+WS'),
               ('lp ~ eve + lws + T_c + RH_c + C(month) + C(year)', '+WS+T+RH'), ('lp ~ eve + lws + T_c + RH_c + dT + C(month) + C(year)', '+WS+T+RH+dT')]:
    m = smf.ols(f, ev).fit(cov_type='cluster', cov_kwds={'groups': ev.g})
    ci = np.exp(m.conf_int().loc['eve'])
    print(f'evening/noon [{lab}]: x{np.exp(m.params["eve"]):.3f} CI[{ci[0]:.3f},{ci[1]:.3f}] p={m.pvalues["eve"]:.1e} n={int(m.nobs)}')
# daily radiative-cooling proxy: diurnal range at Carmel Park; clear/calm nights
day = tv.groupby('date').agg(Trange=('T_c', lambda s: s.max() - s.min()), pm_night=('PM2.5', lambda s: s[s.index.hour <= 5].mean()), pm_noon=('PM2.5', lambda s: s[(s.index.hour >= 12) & (s.index.hour <= 16)].mean()),
                             ws_night=('WS', lambda s: s[s.index.hour <= 5].mean()), RH_night=('RH_c', lambda s: s[s.index.hour <= 5].mean()), dust=('dust', 'max'))
day = day[day.index.month.isin([12, 1, 2]) & ~day.dust.astype(bool)].dropna()
day['q'] = pd.qcut(day.Trange, 4, labels=['Q1 smallest range', 'Q2', 'Q3', 'Q4 largest range'])
print('\nwinter non-dust days by Carmel Park daily temperature range (radiative-cooling proxy):')
print(day.groupby('q', observed=True).agg(n=('pm_night', 'size'), Trange=('Trange', 'mean'), pm_night=('pm_night', 'mean'), pm_noon=('pm_noon', 'mean'), ws_night=('ws_night', 'mean'), RH_night=('RH_night', 'mean')).round(2).to_string())
print('daily corr (night PM2.5, T range):', round(day.pm_night.corr(day.Trange), 3), ' (night PM2.5, night WS):', round(day.pm_night.corr(day.ws_night), 3), ' (night PM2.5, night RH):', round(day.pm_night.corr(day.RH_night), 3))

# ---------------- 4. Bivariate wind speed x direction ----------------
print('\n===== 4. Bivariate wind speed x sector (Tivon) =====')
b = S['Tivon'].copy()
b['dust'] = b.date.map(dust)
b['sec'] = np.select([(b.WD >= 270) & (b.WD <= 315), (b.WD > 315) | (b.WD < 45), (b.WD >= 45) & (b.WD < 135), (b.WD >= 135) & (b.WD < 225), (b.WD >= 225) & (b.WD < 270)],
                     ['Bay270-315', 'N315-45', 'E45-135', 'S135-225', 'WSW225-270'], 'none')
b.loc[b.WD.isna(), 'sec'] = 'none'
b['wsb'] = pd.cut(b.WS, [-0.01, 0.5, 1, 3, 20], labels=['<0.5 calm', '0.5-1', '1-3', '>3'])
print('hours by WS bin:', b.wsb.value_counts().sort_index().to_dict())
for lab, d in [('ALL SEASONS', b), ('WINTER DJF', b[b.month.isin([12, 1, 2])]), ('WINTER DJF excl. dust days (PM2.5 only)', b[b.month.isin([12, 1, 2]) & ~b.dust]), ('SUMMER JJA', b[b.month.isin([6, 7, 8])])]:
    print('\n---', lab)
    print('Mean by WS bin:'); print(d.groupby('wsb', observed=True)[['PM2.5', 'NO2u']].agg(['mean', 'count']).round(1).to_string())
    for v in ['PM2.5', 'NO2u']:
        t = d[d.sec != 'none'].pivot_table(index='sec', columns='wsb', values=v, aggfunc='mean', observed=True).round(1)
        n = d[d.sec != 'none'].pivot_table(index='sec', columns='wsb', values=v, aggfunc='count', observed=True)
        print(f'{v} by sector (rows) x WS bin (cols), mean; then n:'); print(t.to_string()); print(n.to_string())
# stagnation share of pollution
print('\n--- stagnation (WS<1) share of high-pollution hours ---')
for lab, d in [('winter', b[b.month.isin([12, 1, 2])]), ('all', b)]:
    d = d.dropna(subset=['WS'])
    st = d.WS < 1
    for v, thr in [('PM2.5', 25), ('PM2.5', 37.5), ('NO2u', 20)]:
        h = d[v] > thr
        print(f'{lab}: {v}>{thr}: hours={int(h.sum())}, share in WS<1 = {(st & h).sum() / h.sum():.3f}; WS<1 share of all hours = {st.mean():.3f}; P(>thr|WS<1)={(h[st]).mean():.3f}; P(>thr|WS>3)={(h[d.WS > 3]).mean():.3f}')
    x = d.dropna(subset=['PM2.5'])
    print(f'{lab}: PM2.5 mass share from WS<1 hours = {x[x.WS < 1]["PM2.5"].sum() / x["PM2.5"].sum():.3f} (hours share {(x.WS < 1).mean():.3f})')
# regression: stagnation effect
r = b[b.month.isin([12, 1, 2]) & ~b.dust].dropna(subset=['PM2.5', 'NO2u', 'WS']).copy()
r = r[(r['PM2.5'] > 0.5) & (r.NO2u > 0.5)]
r['stag'] = (r.WS < 1).astype(int)
r['high'] = (r.WS > 3).astype(int)
r['g'] = r.date.dt.strftime('%Y%m%d')
for y in ['PM2.5', 'NO2u']:
    r['ly'] = np.log(r[y])
    m = smf.ols('ly ~ stag + high + C(hour) + C(month) + C(year)', r).fit(cov_type='cluster', cov_kwds={'groups': r.g})
    print(f'{y} winter non-dust, adj hour/month/year: WS<1 vs 1-3: x{np.exp(m.params["stag"]):.3f} CI[{np.exp(m.conf_int().loc["stag"][0]):.3f},{np.exp(m.conf_int().loc["stag"][1]):.3f}]; WS>3 vs 1-3: x{np.exp(m.params["high"]):.3f} CI[{np.exp(m.conf_int().loc["high"][0]):.3f},{np.exp(m.conf_int().loc["high"][1]):.3f}]')
