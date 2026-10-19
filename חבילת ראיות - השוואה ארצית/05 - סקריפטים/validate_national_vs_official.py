"""Validation of the public API (hourly, valid=True hours) against the OFFICIAL annual tables of the Haifa Bay Association (2023, 2024, 2025 annual reports):
PM2.5 annual means (Table 23/2023, 2024 report table, Table 22/2025) and PM10 annual means (2023, 2024 tables). Station-id mapping by station name (certain matches only).
Official values were transcribed from the extracted text of the PDFs saved in מקורות/pdf (see נספח). Run: python -I validate_national_vs_official.py > ../validate_national_vs_official_output.txt"""
import sys
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
ID = {'אחוזה': 136, 'נווה שאנן': 86, 'נשר': 87, 'עצמאות': 189, 'פארק הכרמל': 69, 'קרית אתא': 88, 'קרית בנימין': 97, 'קרית חיים': 499, 'קרית טבעון': 137, 'קרית ים': 92, 'קרית מוצקין': 382}
# official annual means, ug/m3
PM25 = {
    2023: {'אחוזה': 13.9, 'נווה שאנן': 13.0, 'נשר': 13.5, 'עצמאות': 18.0, 'פארק הכרמל': 15.0, 'קרית אתא': 17.0, 'קרית בנימין': 13.7, 'קרית חיים': 13.8, 'קרית טבעון': 15.4, 'קרית ים': 16.2, 'קרית מוצקין': 18.9},
    2024: {'אחוזה': 12.9, 'נווה שאנן': 14.3, 'נשר': 12.0, 'עצמאות': 13.5, 'פארק הכרמל': 16.2, 'קרית אתא': 14.5, 'קרית בנימין': 16.5, 'קרית חיים': 13.9, 'קרית טבעון': 15.4, 'קרית ים': 14.2, 'קרית מוצקין': 14.7},
    2025: {'אחוזה': 12.5, 'נווה שאנן': 11.8, 'נשר': 13.5, 'עצמאות': 16.0, 'פארק הכרמל': 13.0, 'קרית אתא': 17.2, 'קרית בנימין': 15.3, 'קרית חיים': 16.1, 'קרית טבעון': 14.5, 'קרית ים': 15.7, 'קרית מוצקין': 18.0},
}
PM10 = {
    2023: {'אחוזה': 29.0, 'נווה שאנן': 27.0, 'נשר': 25.7, 'קרית אתא': 36.1, 'קרית בנימין': 30.0, 'קרית חיים': 34.0, 'קרית טבעון': 27.8, 'קרית מוצקין': 38.8},
    2024: {'נשר': 28.6, 'קרית אתא': 33.5, 'קרית בנימין': 28.9, 'קרית חיים': 33.6, 'קרית טבעון': 28.7, 'קרית מוצקין': 32.8},
}


def api_mean(sid, year, ch):
    L = pd.read_csv(f'national_{year}/st{sid}.csv')
    v = L[(L.channel == ch) & (L.valid == True)].value
    n = 8784 if year % 4 == 0 else 8760
    return (v.mean() if len(v) else np.nan), 100 * len(v) / n


rows = []
for ch, T in (('PM2.5', PM25), ('PM10', PM10)):
    for y, d in T.items():
        for nm, off in d.items():
            a, cov = api_mean(ID[nm], y, ch)
            rows.append((ch, y, nm, ID[nm], off, a, a - off, cov))
R = pd.DataFrame(rows, columns=['pollutant', 'year', 'station', 'id', 'official', 'api', 'diff', 'api_coverage_pct'])
print(R.round(2).to_string(index=False))
for ch in ('PM2.5', 'PM10'):
    r = R[R.pollutant == ch]
    print('\n%s: n=%d | mean diff %+.2f | mean abs diff %.2f | max abs diff %.2f | within 0.5: %d of %d | within 1.0: %d of %d' % (
        ch, len(r), r['diff'].mean(), r['diff'].abs().mean(), r['diff'].abs().max(), (r['diff'].abs() <= 0.5).sum(), len(r), (r['diff'].abs() <= 1.0).sum(), len(r)))
t = R[R.id == 137]
print('\nTivon:'); print(t.round(2).to_string(index=False))
R.to_csv('validation_national_vs_official.csv', index=False, encoding='utf-8')

# ---------------- 2024 PM2.5: shifted-row test ----------------
print('\n===== 2024 PM2.5 table (Table 20 of the 2024 report): test for a one-row shift between labels and values =====')
ORDER = ['אחוזה', 'איגוד', 'הדר', 'נווה שאנן', 'נשר', 'עצמאות', 'פארק הכרמל', 'קרית אתא', 'קרית ביאליק', 'קרית בנימין', 'קרית חיים', 'קרית טבעון', 'קרית ים', 'קרית מוצקין']
PUB = [(12.9, 52), (12.9, 52), (16.4, 40.3), (14.3, 46.3), (12.0, 48), (13.5, 58.6), (16.2, 116), (14.5, 46), (16.1, 54.1), (16.5, 44.2), (13.9, 34), (15.4, 40.3), (14.2, 39.1), (14.7, 33.1)]
IDS = {'אחוזה': 136, 'נווה שאנן': 86, 'נשר': 87, 'עצמאות': 189, 'פארק הכרמל': 69, 'קרית אתא': 88, 'קרית בנימין': 97, 'קרית חיים': 499, 'קרית טבעון': 137, 'קרית ים': 92, 'קרית מוצקין': 382, 'קרית ביאליק (לפי יישוב, תחנה 380)': 380, 'הדר (תחבורתית; לפי שם, תחנה 391)': 391}
api = {}
for nm, sid in IDS.items():
    L = pd.read_csv(f'national_2024/st{sid}.csv'); L = L[(L.channel == 'PM2.5') & (L.valid == True)]
    L['t'] = pd.to_datetime(L.datetime.str[:19]); s = L.set_index('t').value
    dm = s.groupby(s.index.date).agg(['mean', 'count']); dm = dm[dm['count'] >= 18]['mean']
    api[nm] = (s.mean(), dm.max())
print('API 2024 per station (annual mean, max daily):', {k: (round(v[0], 2), round(v[1], 1)) for k, v in api.items()})
rows = []
for i, (lab, (m, mx)) in enumerate(zip(ORDER, PUB)):
    hit = [(k, round(v[0], 2), round(v[1], 1)) for k, v in api.items() if abs(v[0] - m) <= 0.2 and abs(v[1] - mx) <= 2.0]
    rows.append((i + 1, lab, m, mx, hit))
for r in rows:
    print('row %2d  label=%-12s published mean/max %.1f/%.1f -> API station(s) matching both: %s' % r)
# station-by-station: compare the API value of each station with the published value of the SAME label and of the PREVIOUS row (shift by one)
print('\nSame-label match vs previous-row match (annual mean, ug/m3):')
sh_same, sh_prev = [], []
for nm in ['נווה שאנן', 'נשר', 'עצמאות', 'פארק הכרמל', 'קרית אתא', 'קרית בנימין', 'קרית חיים', 'קרית טבעון', 'קרית ים', 'קרית מוצקין']:
    i = ORDER.index(nm)
    same = PUB[i][0]; nxt = PUB[i + 1][0] if i + 1 < len(PUB) else np.nan
    sh_same.append(abs(api[nm][0] - same)); sh_prev.append(abs(api[nm][0] - nxt) if not np.isnan(nxt) else np.nan)
    print('  %-12s API %.2f | published at its own row %.1f (diff %.2f) | published at the NEXT row %.1f (diff %.2f)' % (nm, api[nm][0], same, api[nm][0] - same, nxt, api[nm][0] - nxt if not np.isnan(nxt) else np.nan))
print('mean abs diff, own row: %.2f | next row: %.2f (stations where the next row exists)' % (np.nanmean(sh_same), np.nanmean(sh_prev)))
print('\n2025 report, Table 24 (comparison): labels list 12 stations, Table 22 lists 14 (Atzmaut and Carmel Park removed from labels but their values kept):')
T22 = {'אחוזה': 12.5, 'איגוד': 19.4, 'הדר': 14.6, 'נווה שאנן': 11.8, 'נשר': 13.5, 'עצמאות': 16.0, 'פארק הכרמל': 13.0, 'קרית אתא': 17.2, 'קרית ביאליק': 16.6, 'קרית בנימין': 15.3, 'קרית חיים': 16.1, 'קרית טבעון': 14.5, 'קרית ים': 15.7, 'קרית מוצקין': 18.0}
T24_labels = ['אחוזה', 'איגוד', 'הדר', 'נווה שאנן', 'נשר', 'קרית אתא', 'קרית ביאליק', 'קרית בנימין', 'קרית חיים', 'קרית טבעון', 'קרית מוצקין', 'קרית ים']
T24_vals = [12.5, 19.4, 14.6, 11.8, 13.5, 16.0, 13.0, 17.2, 16.6, 15.3, 16.1, 14.5]
t22_list = list(T22.items())
for k, (lab, v) in enumerate(zip(T24_labels, T24_vals)):
    own = T22.get(lab); src = t22_list[k] if k < len(t22_list) else None
    print('  Table 24 label %-12s value %.1f | Table 22 value of the SAME station %.1f | Table 22 value at the same ROW POSITION (%s) %.1f' % (lab, v, own, src[0], src[1]))

print('\n2023 report, Table 25 (comparison 2022 vs 2023, column 2023): labels list 12 stations, Table 23 lists 14 (Atzmaut and Carmel Park removed from the labels but their values kept):')
T23 = [('אחוזה', 13.9), ('איגוד', 17.3), ('הדר', 14.1), ('נווה שאנן', 13.0), ('נשר', 13.5), ('עצמאות', 18.0), ('פארק הכרמל', 15.0), ('קרית אתא', 17.0), ('קרית ביאליק', 16.7), ('קרית בנימין', 13.7), ('קרית חיים', 13.8), ('קרית טבעון', 15.4), ('קרית ים', 16.2), ('קרית מוצקין', 18.9)]
T25_labels = ['אחוזה', 'איגוד', 'הדר', 'נווה שאנן', 'נשר', 'קרית אתא', 'קרית ביאליק', 'קרית בנימין', 'קרית חיים', 'קרית טבעון', 'קרית מוצקין', 'קרית ים']
T25_vals = [14, 17, 14, 13, 14, 18, 15, 17, 17, 14, 14, 15]   # printed integers, column 2023
own = dict(T23)
for k, (lab, v) in enumerate(zip(T25_labels, T25_vals)):
    pos_name, pos_val = T23[k]
    print('  Table 25 label %-12s printed %2d | Table 23 value of the SAME station %.1f (rounds to %d) | Table 23 value at the same ROW POSITION (%s) %.1f (rounds to %d)' % (lab, v, own[lab], round(own[lab]), pos_name, pos_val, round(pos_val)))
