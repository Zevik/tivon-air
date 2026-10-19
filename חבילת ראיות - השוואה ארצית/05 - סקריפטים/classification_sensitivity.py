"""Sensitivity of Tivon's national ranking to the station classification and to leaving out whole regions (jackknife)."""
import sys
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
A = pd.read_csv('national_summary_station.csv', encoding='utf-8').set_index('id').rename(columns={'class': 'cls'})
T = 137
cols = [('pm25', 'PM2.5'), ('pm25_nodust', 'PM2.5 בלי אבק'), ('o3_days51', 'אוזון ימים'), ('no2', 'NO2'), ('pm10', 'PM10')]


def pos(sub, c):
    x = sub[c].dropna()
    return 100 * (x < sub.loc[T, c]).mean(), x.median(), len(x)  # % of stations lower than Tivon


print('baseline (all stations):', {l: '%.0f%% lower, median %.1f, n=%d' % pos(A, c) for c, l in cols})
bgmask = A.cls == 'רקע עירוני/כללי'
alts = {
    'רקע בלבד (בסיס)': A[bgmask | (A.index == T)],
    'רקע בלי תחנות רשות שדות התעופה (371, 357)': A[(bgmask | (A.index == T)) & ~A.index.isin([371, 357])],
    'רקע בלי תחנות חברת חשמל': A[(bgmask | (A.index == T)) & ~A.owner.astype(str).str.contains('חברת חשמל')],
    'רקע בלי הנגב והערבה': A[(bgmask | (A.index == T)) & ~A.region.str.contains('נגב')],
    'כל התחנות, בלי תחנות תחבורה': A[(A.cls != 'תחבורה') | (A.index == T)],
}
for k, sub in alts.items():
    print('%-48s' % k, {l: '%.0f%%/%s' % (pos(sub, c)[0], '%.1f' % pos(sub, c)[1]) for c, l in cols})
print('\njackknife over regions (drop one region at a time; % of remaining stations lower than Tivon):')
rows = []
for r in A.region.unique():
    if r == 'טבעון':
        continue
    sub = A[A.region != r]
    rows.append((r, {l: pos(sub, c)[0] for c, l in cols}))
for c, l in cols:
    v = [x[1][l] for x in rows]
    print('  %-14s range %.0f%% - %.0f%% (full sample %.0f%%)' % (l, min(v), max(v), pos(A, c)[0]))
