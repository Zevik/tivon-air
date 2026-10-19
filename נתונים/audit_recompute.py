"""Independent re-computation (audit) of the national comparison metrics, written separately from national_analysis.py (numpy, no pandas rolling).
Reads the raw hourly CSVs (national_2023/24/25), applies the documented QC (annual coverage >= 75%, each season >= 50% valid hours), recomputes
PM2.5 / PM10 annual means, share of days with daily PM2.5 > 15, O3 days with MDA8 >= 51 ppb (scaled to 365 days), JJA mean MDA8 and NO2 (ppb x 1.8804),
and compares them with national_summary_station_year.csv. Also reports data sanity checks (negative / extreme values).
Run: python -I audit_recompute.py > ../audit_recompute_output.txt"""
import sys, os, glob
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
SEAS = {12: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2, 7: 2, 8: 2, 9: 3, 10: 3, 11: 3}


def load(path, year):
    L = pd.read_csv(path)
    n = 8784 if year % 4 == 0 else 8760
    t0 = pd.Timestamp(f'{year}-01-01')
    out = {}
    L = L[L.channel.isin(['PM2.5', 'PM10', 'O3', 'NO2'])]
    ts = pd.to_datetime(L.datetime.str[:19])
    hr = ((ts - t0) / pd.Timedelta(hours=1)).astype(int).values
    ok = (hr >= 0) & (hr < n)
    for ch in ['PM2.5', 'PM10', 'O3', 'NO2']:
        m = (L.channel.values == ch) & ok & (L.valid.values == True)
        a = np.full(n, np.nan)
        a[hr[m]] = L.value.values[m]
        out[ch] = a
    return out, t0, n


def seasons_ok(a, t0, n):
    months = pd.date_range(t0, periods=n, freq='h').month.values
    sea = np.array([SEAS[m] for m in months])
    return all(np.isfinite(a[sea == k]).mean() >= 0.5 for k in range(4)), months


def mda8_days(a, t0, n):
    v = np.isfinite(a)
    x = np.where(v, a, 0.0)
    cs = np.concatenate([[0], np.cumsum(x)]); cc = np.concatenate([[0], np.cumsum(v.astype(int))])
    avg = np.full(n, np.nan)
    for t in range(n):
        lo = max(0, t - 7)
        c = cc[t + 1] - cc[lo]
        if c >= 6:
            avg[t] = (cs[t + 1] - cs[lo]) / c
    day = np.arange(n) // 24
    res = {}
    for d in np.unique(day):
        w = avg[day == d]
        if np.isfinite(w).sum() >= 18:
            res[d] = round(float(np.nanmax(w)), 6)
    return res


rows = []
neg = []
for y in (2023, 2024, 2025):
    for f in glob.glob(f'national_{y}/st*.csv'):
        sid = int(os.path.basename(f)[2:-4])
        L0 = pd.read_csv(f)
        if L0.empty:
            continue
        ch, t0, n = load(f, y)
        r = {'id': sid, 'year': y}
        for c in ['PM2.5', 'PM10', 'NO2', 'O3']:
            a = ch[c]
            cov = np.isfinite(a).mean() * 100
            sok, months = seasons_ok(a, t0, n)
            good = cov >= 75 and sok
            neg.append((sid, y, c, int((a < 0).sum()), int((a > 1000).sum())))
            if c == 'PM2.5':
                r['pm25_cov'] = cov
                r['pm25'] = np.nanmean(a) if good and np.isfinite(a).any() else np.nan
                if good:
                    d = np.arange(n) // 24
                    dm = pd.Series(a).groupby(d).agg(['mean', 'count'])
                    dm = dm[dm['count'] >= 18]['mean']
                    r['pm25_days15'] = 100 * (dm > 15).mean()
            if c == 'PM10':
                r['pm10'] = np.nanmean(a) if good and np.isfinite(a).any() else np.nan
            if c == 'NO2':
                r['no2'] = np.nanmean(a) * 1.8804 if good and np.isfinite(a).any() else np.nan
            if c == 'O3':
                r['o3_cov'] = cov
                if good:
                    m8 = mda8_days(a, t0, n)
                    if m8:
                        vals = np.array(list(m8.values()))
                        r['o3_days51'] = (vals >= 51).sum() * 365.0 / len(vals)
                        jja = [v for d_, v in m8.items() if pd.Timestamp(t0) + pd.Timedelta(days=int(d_)) >= pd.Timestamp(f'{y}-06-01') and pd.Timestamp(t0) + pd.Timedelta(days=int(d_)) <= pd.Timestamp(f'{y}-08-31')]
                        r['o3_jja'] = np.mean(jja) if jja else np.nan
        rows.append(r)
R = pd.DataFrame(rows).set_index(['id', 'year'])
# plausibility and stability rules (implemented here independently of national_analysis.py)
bad = (R.pm25 < 5) | (R.pm25 > 60)
R.loc[bad, ['pm25', 'pm25_days15']] = np.nan
R.loc[(R.pm10 < 15) | (R.pm10 > 150), 'pm10'] = np.nan
mm = R.o3_days51.dropna().groupby(level=0).agg(['min', 'max', 'count'])
unst = mm[(mm['count'] >= 2) & (mm['max'] / mm['min'] > 2.5)].index
R.loc[R.index.get_level_values(0).isin(unst), ['o3_days51', 'o3_jja']] = np.nan
print('audit: ozone-unstable stations excluded:', list(unst), '| implausible PM2.5 station-years set to NaN:', int(bad.sum()))
S = pd.read_csv('national_summary_station_year.csv').set_index(['id', 'year'])
print('station-years recomputed:', len(R), '| in pipeline file:', len(S))
for mine, theirs, tol in [('pm25', 'pm25', 0.01), ('pm10', 'pm10', 0.01), ('no2', 'no2', 0.01), ('o3_days51', 'o3_days51', 0.5), ('o3_jja', 'o3_jja', 0.05), ('pm25_days15', 'pm25_days_gt15_pct', 0.2)]:
    j = R[[mine]].join(S[[theirs]].rename(columns={theirs: 'p'}), how='outer')
    j = j.rename(columns={mine: 'a'})
    both = j.dropna()
    onlya = j[j.a.notna() & j.p.isna()]
    onlyp = j[j.a.isna() & j.p.notna()]
    d = (both.a - both.p).abs()
    print('%-12s compared %4d | max abs diff %.4f | diffs above tol %d | only audit has value %d | only pipeline has value %d' % (mine, len(both), d.max() if len(d) else np.nan, int((d > tol).sum()), len(onlya), len(onlyp)))
    if len(onlya) or len(onlyp) or (d > tol).any():
        print('   examples:', onlya.head(5).index.tolist(), onlyp.head(5).index.tolist(), both[d > tol].head(5).round(2).to_dict('index'))
N = pd.DataFrame(neg, columns=['id', 'year', 'ch', 'negatives', 'above1000'])
print('\nsanity: station-years with negative valid hourly values:', N[N.negatives > 0].groupby('ch').size().to_dict(), '| total negative hours by channel:', N.groupby('ch').negatives.sum().to_dict(), '| values above 1000:', int(N.above1000.sum()))
print(N[(N.negatives > 200)].sort_values('negatives', ascending=False).head(10).to_string(index=False))
t = R.loc[(137, slice(None)), :]
print('\nTivon recomputed by year:'); print(t.round(2).to_string())
