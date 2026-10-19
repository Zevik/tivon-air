"""Validation of API annual means against OFFICIAL annual tables of other environmental associations (found via the user's search file):
Ashdod-Yavne Association (annual reports 2023, 2024, 2025: PM2.5 table; PM2.5 pages 55 / 40 / 36), and further tables added below as they are transcribed.
Official values transcribed by hand from the PDFs (listed in the evidence package); API value = mean of valid hourly values of the year.
Run: python -I validate_other_associations.py > ../validate_other_associations_output.txt"""
import os, sys
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.abspath(__file__))


def api(sid, y, ch='PM2.5'):
    L = pd.read_csv(os.path.join(BASE, f'national_{y}', f'st{sid}.csv'))
    v = L[(L.channel == ch) & (L.valid == True)].value
    return v.mean(), 100 * len(v) / (8784 if y % 4 == 0 else 8760)


rows = []
# ---- Ashdod-Yavne Association, PM2.5 annual mean (ug/m3), table order as printed ----
ash = {'שדרות ירושלים': 405, 'רובע ט"ו החדשה': 383, 'אזור תעשיה קלה': 115, 'פארק לכיש': 423, 'בני דרום': 365, 'גן יבנה': 116, 'אזור תעשייה צפוני': 535, 'יד בנימין': 122}
off = {2023: [16.4, 15.6, 15.7, 18, 16.5, 16.2, 19.9, 16.2], 2024: [15.5, 14.6, 15.5, 16.4, 16, 18.2, 23.9, 16.8], 2025: [16.8, 14.6, 15.5, 16.4, 15.3, 17.8, 21, 17.6]}
for y, vals in off.items():
    for (nm, sid), o in zip(ash.items(), vals):
        a, c = api(sid, y)
        rows.append(('איגוד אשדוד-חבל יבנה', y, 'PM2.5', nm, sid, o, a, a - o, c))
# ---- Ashkelon Association, PM2.5 annual mean 2024 (Table 7, PDF page 38 of the 2024 annual report) ----
ashk = [('ארז', 131, 15.13), ('אשקלון שמשון', 160, 14.65), ('אשקלון גן הוורדים', 123, 15.53), ('כפר מנחם הרחבה', 331, 14.6), ('כרמיה', 130, 17.29), ('מבקיעים', 306, 14.96), ('ניר ישראל', 129, 15.26),
        ('קריית גת', 124, 17.37), ('קריית מלאכי', 125, 16.22), ('שדה יואב', 128, 15.5), ('שדרות', 126, 15.13)]
for nm, sid, o in ashk:
    a_, c = api(sid, 2024)
    rows.append(('איגוד אשקלון', 2024, 'PM2.5', nm, sid, o, a_, a_ - o, c))
R = pd.DataFrame(rows, columns=['assoc', 'year', 'pollutant', 'station', 'id', 'official', 'api', 'diff', 'api_cov_pct'])
print(R.round(2).to_string(index=False))
for (a_, p_), g in R.groupby(['assoc', 'pollutant']):
    print('\n%s %s: n=%d | mean diff %+.2f | mean abs diff %.2f | max abs %.2f | within 0.5: %d | within 1.0: %d' % (a_, p_, len(g), g['diff'].mean(), g['diff'].abs().mean(), g['diff'].abs().max(), (g['diff'].abs() <= 0.5).sum(), (g['diff'].abs() <= 1.0).sum()))
R.to_csv(os.path.join(BASE, 'validation_other_associations.csv'), index=False, encoding='utf-8')
