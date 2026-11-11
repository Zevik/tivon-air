"""PM2.5 2024: corrected Table 20 (Haifa Bay association reply, 11.2026) vs API annual means
(api column of validation_national_vs_official.csv, produced by validate_national_vs_official.py)."""
import sys
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
CORR = {136: ('אחוזה', 12.8, 96), 86: ('נווה שאנן', 12.0, 93), 87: ('נשר', 13.5, 98), 189: ('עצמאות', 16.0, 97),
        69: ('פארק הכרמל', 14.0, 69), 88: ('קריית אתא', 16.1, 89), 97: ('קריית בנימין', 13.9, 98), 499: ('קריית חיים', 15.3, 96),
        137: ('קריית טבעון', 14.1, 98), 92: ('קריית ים', 14.7, 79), 382: ('קריית מוצקין', 15.6, 93)}
v = pd.read_csv('validation_national_vs_official.csv')
v = v[(v.year == 2024) & (v.pollutant == 'PM2.5')].set_index('id')
rows = []
for i, (name, off, cov) in CORR.items():
    rows.append(dict(id=i, station=name, official_corrected=off, official_cov=cov, published=v.loc[i, 'official'], api=round(v.loc[i, 'api'], 2),
                     api_cov=round(v.loc[i, 'api_coverage_pct']), diff=round(v.loc[i, 'api'] - off, 2)))
R = pd.DataFrame(rows)
print(R.to_string(index=False))
print('\ncorrected table: mean |diff| %.2f, max %.2f (n=%d)' % (R['diff'].abs().mean(), R['diff'].abs().max(), len(R)))
s = R[(R.official_cov - R.api_cov).abs() <= 10]
print('stations with official/API coverage within 10 points: mean |diff| %.2f, max %.2f (n=%d)' % (s['diff'].abs().mean(), s['diff'].abs().max(), len(s)))
print('published table: mean |diff| %.2f' % (R.api - R.published).abs().mean())
