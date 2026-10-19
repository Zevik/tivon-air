"""Validation of API NO2 and ozone against the OFFICIAL tables of the Ashdod-Yavne Association (annual reports 2023, 2024, 2025: NO2 pages 53/38/34, ozone pages 54/39/35)
and the Ashkelon Association (annual report 2024: ozone Table 4 p.35, NO2 Table 6 p.37). Values transcribed by hand from the PDFs (in the evidence package).
NO2: API annual mean of valid hours (ppb) x 1.8804 compared with the official annual mean (ug/m3).
Ozone: the unit conversion is not published, so the ratio official/API (ug per ppb) is computed per station; a stable ratio near the physical 1.96 (and near the 1.89 'official-equivalent' factor found in Haifa) means agreement.
Ozone MDA8 maximum: API (trailing 8 h mean, >= 6 valid of 8, day with >= 18 windows) versus the official maximum.
Run: python -I validate_no2_o3_other_associations.py > ../validate_no2_o3_other_associations_output.txt"""
import os, sys
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.abspath(__file__))
NO2F = 46.0055 / 24.4655


def series(sid, y, ch):
    L = pd.read_csv(os.path.join(BASE, f'national_{y}', f'st{sid}.csv'))
    L = L[(L.channel == ch)]
    L['t'] = pd.to_datetime(L.datetime.str[:19])
    L = L[L.valid == True].set_index('t').value
    idx = pd.date_range(f'{y}-01-01', f'{y}-12-31 23:00', freq='h')
    return L[~L.index.duplicated()].reindex(idx)


def mdamax(s):
    ro = s.rolling(8, min_periods=6).mean()
    d = ro.groupby(ro.index.date)
    ok = d.count() >= 18
    mx = d.max()[ok]
    return round(float(mx.max()), 6), int((mx >= 51).sum()), int(ok.sum())


rows = []
# ---- NO2 (ug/m3): (assoc, year, station, id, official)
no2 = []
A = {405: 'שדרות ירושלים', 383: 'רובע ט"ו החדשה', 115: 'אזור תעשיה קלה', 423: 'פארק לכיש', 365: 'בני דרום', 116: 'גן יבנה', 511: 'קבוצת יבנה מערב', 122: 'יד בנימין', 535: 'אזור תעשייה צפוני'}
for y, ids, vals in [(2023, [405, 383, 115, 423, 365, 116, 511, 122], [22.6, 12.6, 17.5, 17.2, 14.7, 17.3, 13.5, 12.9]),
                     (2024, [405, 383, 115, 423, 365, 116, 511, 122], [19.6, 13.1, 16.9, 15.7, 13, 14.5, 12, 12.6]),
                     (2025, [405, 383, 535, 115, 423, 116, 511, 122], [19.3, 14, 14.9, 19.5, 16.1, 15.8, 14.3, 14.7])]:
    for i, v in zip(ids, vals):
        no2.append(('איגוד אשדוד-חבל יבנה', y, A[i], i, v))
K = {131: 'ארז', 160: 'אשקלון שמשון', 123: 'אשקלון גן הוורדים', 127: 'גברעם', 331: 'כפר מנחם הרחבה', 130: 'כרמיה', 306: 'מבקיעים', 129: 'ניר ישראל', 124: 'קריית גת', 125: 'קריית מלאכי', 128: 'שדה יואב', 126: 'שדרות'}
for i, v in zip([131, 160, 123, 127, 331, 130, 306, 129, 124, 125, 128, 126], [7.9, 8.2, 11.9, 5.9, 6.3, 13.2, 8.3, 6.9, 11.2, 12.1, 7.1, 9.1]):
    no2.append(('איגוד אשקלון', 2024, K[i], i, v))
R = []
for assoc, y, nm, sid, o in no2:
    s = series(sid, y, 'NO2')
    cov = 100 * s.notna().mean()
    a = s.mean() * NO2F
    R.append((assoc, y, 'NO2', nm, sid, o, a, a - o, cov))
N = pd.DataFrame(R, columns=['assoc', 'year', 'pollutant', 'station', 'id', 'official', 'api', 'diff', 'api_cov_pct'])
print(N.round(2).to_string(index=False))
Nv = N[N.api_cov_pct >= 50]
print('\nNO2 (stations with API coverage >= 50%%): n=%d | mean diff %+.2f | mean abs diff %.2f | max abs %.2f | mean ratio api/official %.3f' % (len(Nv), Nv['diff'].mean(), Nv['diff'].abs().mean(), Nv['diff'].abs().max(), (Nv.api / Nv.official).mean()))
for a_, g in Nv.groupby('assoc'):
    print('  %s: n=%d, mean abs diff %.2f, max abs %.2f, mean diff %+.2f' % (a_, len(g), g['diff'].abs().mean(), g['diff'].abs().max(), g['diff'].mean()))

# ---- Ozone: (assoc, year, station, id, official annual mean ug, official max 8h ug, official exceedances)
oz = []
for y, rows_ in [(2023, [(383, 65.4, 128.7, 0), (115, 58.1, 137.9, 0), (365, 57, 127.5, 0), (122, 52.9, 132.3, 0)]),
                 (2024, [(383, 68.4, 129.1, 0), (115, 63.1, 125.6, 0), (365, 54.6, 118.8, 0), (122, 63.2, 153.1, 1)]),
                 (2025, [(383, 74.4, 164, 4), (115, 61.9, 166, 2), (511, 31.2, 74.2, 3), (122, 69.5, 182.4, 4)])]:
    for i, m, mx, ex in rows_:
        oz.append(('איגוד אשדוד-חבל יבנה', y, A[i], i, m, mx, ex))
for i, m, mx in [(131, 65.1, 142.4), (160, 79.7, 153.2), (123, 73, 159.4), (127, 77.5, 160.8), (130, 59.4, 132.8), (306, 69.3, 134.2), (124, 74, 152.6), (125, 68.1, 132), (126, 81.6, 157.6)]:
    oz.append(('איגוד אשקלון', 2024, K[i], i, m, mx, None))
R2 = []
for assoc, y, nm, sid, om, omx, ex in oz:
    s = series(sid, y, 'O3')
    cov = 100 * s.notna().mean()
    am = s.mean()
    amx, d51, nd = mdamax(s)
    R2.append((assoc, y, nm, sid, om, am, om / am, omx, amx, omx / amx, ex, d51, cov))
O = pd.DataFrame(R2, columns=['assoc', 'year', 'station', 'id', 'off_mean', 'api_mean_ppb', 'ratio_mean', 'off_max8', 'api_max8_ppb', 'ratio_max8', 'off_exceed_days', 'api_days_ge51ppb', 'api_cov_pct'])
print('\n' + O.round(3).to_string(index=False))
Ov = O[O.api_cov_pct >= 50]
print('\nozone annual mean, ratio official(ug)/API(ppb): n=%d | mean %.3f | min %.3f | max %.3f | SD %.3f' % (len(Ov), Ov.ratio_mean.mean(), Ov.ratio_mean.min(), Ov.ratio_mean.max(), Ov.ratio_mean.std()))
print('ozone max 8h, ratio official(ug)/API(ppb):  n=%d | mean %.3f | min %.3f | max %.3f | SD %.3f' % (len(Ov), Ov.ratio_max8.mean(), Ov.ratio_max8.min(), Ov.ratio_max8.max(), Ov.ratio_max8.std()))
for a_, g in Ov.groupby('assoc'):
    print('  %s: ratio of annual mean %.3f (SD %.3f), ratio of max 8h %.3f (SD %.3f)' % (a_, g.ratio_mean.mean(), g.ratio_mean.std(), g.ratio_max8.mean(), g.ratio_max8.std()))
N.to_csv(os.path.join(BASE, 'validation_no2_other_associations.csv'), index=False, encoding='utf-8')
O.to_csv(os.path.join(BASE, 'validation_o3_other_associations.csv'), index=False, encoding='utf-8')
