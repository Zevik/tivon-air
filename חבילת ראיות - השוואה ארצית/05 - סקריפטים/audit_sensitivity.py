"""Sensitivity of the PM2.5 / NO2 / PM10 annual means and Tivon's national position to negative hourly values and to extreme values (> 1000 ug/m3).
Variants: base (all valid hours), negatives removed, negatives set to zero, values above 1000 removed. Run: python -I audit_sensitivity.py > ../audit_sensitivity_output.txt"""
import sys, os, glob
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
SEAS = {12: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2, 7: 2, 8: 2, 9: 3, 10: 3, 11: 3}
rows = []; hi = []
for y in (2023, 2024, 2025):
    n = 8784 if y % 4 == 0 else 8760; t0 = pd.Timestamp(f'{y}-01-01')
    months = pd.date_range(t0, periods=n, freq='h').month.values; sea = np.array([SEAS[m] for m in months])
    for f in glob.glob(f'national_{y}/st*.csv'):
        sid = int(os.path.basename(f)[2:-4]); L = pd.read_csv(f)
        if L.empty: continue
        L = L[L.channel.isin(['PM2.5', 'NO2', 'PM10']) & (L.valid == True)]
        ts = pd.to_datetime(L.datetime.str[:19]); hr = ((ts - t0) / pd.Timedelta(hours=1)).astype(int).values
        for ch in ['PM2.5', 'NO2', 'PM10']:
            m = (L.channel.values == ch) & (hr >= 0) & (hr < n)
            a = np.full(n, np.nan); a[hr[m]] = L.value.values[m]
            hi.append((sid, y, ch, int((a > 1000).sum()), float(np.nanmax(a)) if np.isfinite(a).any() else np.nan))
            cov = np.isfinite(a).mean() * 100
            if cov < 75 or not all(np.isfinite(a[sea == k]).mean() >= .5 for k in range(4)): continue
            conv = 1.8804 if ch == 'NO2' else 1
            b = a.copy(); b[b < 0] = np.nan
            c = a.copy(); c[c < 0] = 0
            d = a.copy(); d[d > 1000] = np.nan
            rows.append((sid, y, ch, np.nanmean(a) * conv, np.nanmean(b) * conv, np.nanmean(c) * conv, np.nanmean(d) * conv))
D = pd.DataFrame(rows, columns=['id', 'year', 'ch', 'base', 'noneg', 'zero', 'nohi'])
H = pd.DataFrame(hi, columns=['id', 'year', 'ch', 'n_gt1000', 'max'])
print('hours above 1000 by channel:', H.groupby('ch').n_gt1000.sum().to_dict(), '| channels with such values:', H[H.n_gt1000 > 0].groupby('ch').size().to_dict())
print('stations/years with max>1000 PM2.5 or NO2:'); print(H[(H.ch != 'PM10') & (H.n_gt1000 > 0)].to_string(index=False))
cnt = D.groupby(['id', 'ch']).size().rename('n')
G = D.groupby(['id', 'ch'])[['base', 'noneg', 'zero', 'nohi']].mean().reset_index().merge(cnt.reset_index(), on=['id', 'ch'])
G = G[G.n >= 2]  # same rule as the report: at least two valid years
print('(stations with at least two valid years, as in the report)')
for ch in ['PM2.5', 'NO2', 'PM10']:
    g = G[G.ch == ch]; t = g[g.id == 137].iloc[0]
    print(ch, '|', ' | '.join('%s: Tivon %.2f rank %d of %d median %.2f' % (k, t[k], int((g[k] > t[k]).sum()) + 1, len(g), g[k].median()) for k in ['base', 'noneg', 'zero', 'nohi']))
