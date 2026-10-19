"""National comparison for 2025 (guest API, unverified): annual PM2.5, days with daily PM2.5 > 15 (WHO 24h), days with MDA8 O3 above 100 ug/m3 at 25C/1 atm
(factor 1.962 = conversion B; ppb x 1.962) and above 51 ppb, annual NO2 (ppb x 1.881). Stations with >= 75% valid hours (PM2.5, O3) are ranked; Tivon (137) is marked.
Dust days are NOT removed. Run: python -I national_compare_2025.py > ../national_compare_2025_output.txt"""
import sys, os, glob
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200)
st = pd.read_csv('national_2025/_stations.csv').set_index('id')
IDX = pd.date_range('2025-01-01 00:00', '2025-12-31 23:00', freq='h')
res = []
for f in glob.glob('national_2025/st*.csv'):
    sid = int(os.path.basename(f)[2:-4])
    L = pd.read_csv(f)
    if L.empty: continue
    L['t'] = pd.to_datetime(L.datetime.str[:19])
    L.loc[~L.valid, 'value'] = np.nan
    p = L.pivot_table(index='t', columns='channel', values='value', aggfunc='first').reindex(IDX)
    r = {'id': sid, 'name': st.loc[sid, 'name'], 'city': st.loc[sid, 'city'], 'owner': st.loc[sid, 'owner'], 'h': st.loc[sid, 'height'], 'lat': st.loc[sid, 'lat'], 'lon': st.loc[sid, 'lon']}
    if 'PM2.5' in p:
        s = p['PM2.5']; r['pm25_cov'] = s.notna().mean() * 100; r['pm25'] = s.mean()
        dm = s.groupby(s.index.date).agg(['mean', 'count']); dm = dm[dm['count'] >= 18]
        r['pm25_days'] = (dm['mean'] > 15).sum(); r['pm25_valid_days'] = len(dm); r['pm25_days_pct'] = 100 * (dm['mean'] > 15).mean() if len(dm) else np.nan
    if 'O3' in p:
        s = p['O3']; r['o3_cov'] = s.notna().mean() * 100
        ro = s.rolling(8, min_periods=6).mean(); day = ro.index.normalize()
        ok = ro.groupby(day).count() >= 18; m8 = ro.groupby(day).max().where(ok).dropna()
        r['o3_days_ppb51'] = (m8 >= 51).sum(); r['o3_valid_days'] = len(m8); r['o3_days100_B'] = (m8 * 1.962 > 100).sum()
        r['o3_jja_m8_ppb'] = m8[m8.index.month.isin([6, 7, 8])].mean()
    if 'NO2' in p:
        r['no2_ugm3'] = p['NO2'].mean() * 1.881; r['no2_cov'] = p['NO2'].notna().mean() * 100
    res.append(r)
R = pd.DataFrame(res).set_index('id')
R.to_csv('national_2025/_summary.csv', encoding='utf-8')
mark = lambda df: df.assign(**{'*': np.where(df.index == 137, '<<< טבעון', '')})
c = R[(R.get('pm25_cov', 0) >= 75)].sort_values('pm25', ascending=False)
print('===== PM2.5 2025: annual mean (ug/m3), coverage >= 75%%; n=%d =====' % len(c))
print(mark(c)[['name', 'city', 'h', 'pm25', 'pm25_cov', 'pm25_days', 'pm25_valid_days', '*']].round(1).to_string())
if 137 in c.index:
    rk = list(c.index).index(137) + 1
    print('\nTivon PM2.5 rank (1 = highest): %d of %d | percentile of stations with lower value: %.0f%% | median %.1f, mean %.1f, min %.1f, max %.1f' % (rk, len(c), 100 * (c.pm25 < c.loc[137, 'pm25']).mean(), c.pm25.median(), c.pm25.mean(), c.pm25.min(), c.pm25.max()))
    print('Days with PM2.5 > 15 (valid days): Tivon %d of %d (%.0f%%); median station %.0f%%' % (c.loc[137, 'pm25_days'], c.loc[137, 'pm25_valid_days'], c.loc[137, 'pm25_days_pct'], c.pm25_days_pct.median()))
o = R[(R.get('o3_cov', 0) >= 75)].sort_values('o3_days_ppb51', ascending=False)
print('\n===== Ozone 2025: days with MDA8 >= 51 ppb (~100 ug/m3 at 25C, 1 atm); coverage >= 75%%; n=%d =====' % len(o))
print(mark(o)[['name', 'city', 'h', 'o3_days_ppb51', 'o3_days100_B', 'o3_valid_days', 'o3_jja_m8_ppb', '*']].round(1).to_string())
if 137 in o.index:
    rk = list(o.index).index(137) + 1
    print('\nTivon ozone rank (1 = most days): %d of %d | median stations %.0f days, Tivon %d' % (rk, len(o), o.o3_days_ppb51.median(), o.loc[137, 'o3_days_ppb51']))
n = R[(R.get('no2_cov', 0) >= 75)].sort_values('no2_ugm3', ascending=False)
print('\n===== NO2 2025: annual mean (ug/m3 at 25C); n=%d =====' % len(n))
if 137 in n.index:
    rk = list(n.index).index(137) + 1
    print('Tivon NO2 %.1f, rank %d of %d (1 = highest); median %.1f; max %.1f' % (n.loc[137, 'no2_ugm3'], rk, len(n), n.no2_ugm3.median(), n.no2_ugm3.max()))
    print(mark(n.head(8))[['name', 'city', 'no2_ugm3', '*']].round(1).to_string())
