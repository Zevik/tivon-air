import json
import sys
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
base = r'C:\Users\Zevik\Documents\טבעון זיהום אויר'
A = pd.read_csv(base + r'\נתונים\national_summary_station.csv', encoding='utf-8')
A['city'] = A['city'].replace({'קיריית טבעון': 'קריית טבעון', 'כרם מהרל': 'כרם מהר"ל', 'כרם מהר"ל': 'כרם מהר"ל'})
A['city'] = A['city'].fillna(A['name'])
A['city'] = A['city'].replace({'מועצה אזורית חוף הכרמל': 'חוף הכרמל', 'מ.א. חבל יבנה': 'חבל יבנה', 'מועצה תעשייתית נאות חובב': 'נאות חובב', 'מועצה אזורית': 'חוף הכרמל', 'גליל עליון': 'תל חי (גליל עליון)', 'עמק המעיינות': 'בית שאן (עמק המעיינות)'})
cols = ['id', 'name', 'city', 'region', 'class', 'h', 'pm25', 'pm25_nodust', 'pm25_days15', 'o3_days51', 'o3_jja', 'no2', 'pm10']
D = A[cols].copy()
D = D.rename(columns={'class': 'cls'})
D = D[(D.pm25.notna()) | (D.o3_days51.notna()) | (D.no2.notna()) | (D.pm10.notna())]
for c in ['pm25', 'pm25_nodust', 'pm25_days15', 'o3_days51', 'o3_jja', 'no2', 'pm10', 'h']:
    D[c] = D[c].round(2)
data = json.loads(D.to_json(orient='records', force_ascii=False))
import os
here = os.path.dirname(os.path.abspath(__file__))
html = open(os.path.join(here, 'charts_template.html'), encoding='utf-8').read()
html = html.replace('/*DATA*/[]', json.dumps(data, ensure_ascii=False))
open(base + r'\השוואה ארצית - גרפים.html', 'w', encoding='utf-8').write(html)
print(len(data), 'stations;', 'size KB', len(html) // 1024)
