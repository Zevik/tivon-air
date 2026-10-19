import sys, os, shutil, hashlib, zipfile, urllib.request, urllib.parse, json, re, glob
import numpy as np
import pandas as pd
import pymupdf
sys.stdout.reconfigure(encoding='utf-8')
base = r'C:\Users\Zevik\Documents\טבעון זיהום אויר'
pk = base + r'\חבילת ראיות - השוואה ארצית'
os.makedirs(pk, exist_ok=True)
D = {k: pk + '\\' + v for k, v in {'rep': '01 - דוחות רשמיים ומסמכי ייחוס', 'st': '02 - רשימת תחנות', 'raw': '03 - נתונים גולמיים (zip)', 'res': '04 - תוצאות מעובדות ופלטי בדיקה', 'scr': '05 - סקריפטים', 'pub': '06 - מסמכי הפרסום'}.items()}
for d in D.values():
    os.makedirs(d, exist_ok=True)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
mb = lambda p: os.path.getsize(p) / 1e6
UNST = [int(x) for x in re.search(r'excluded from the ozone ranking[^\[]*\[([^\]]*)\]', open(base + chr(92) + 'national_analysis_output.txt', encoding='utf-8').read()).group(1).split(',')]

# ---------- 1. official reports: copy + verify against the official server + relevant pages ----------
UA = {'User-Agent': 'Mozilla/5.0'}
Q = lambda s: urllib.parse.quote(s)
reports = {
    2023: ('איגוד_דוח_שנתי_2023.pdf', 'https://www.envihaifa.org.il/' + Q('דוח שנתי 2023-compressed.pdf'), [(100, 'טבלה 23: PM2.5 לפי תחנה, 2023'), (95, 'PM10 לפי תחנה, 2023'), (104, 'טבלה 25: השוואת PM2.5 2022–2023 (ערכים מוסטים בשורה)')]),
    2024: ('איגוד_דוח_שנתי_2024.pdf', 'https://www.envihaifa.org.il/prdFiles/' + Q('דוח שנתי 2024 - איגוד ערים מפרץ חיפה להגנת הסביבה_compressed.pdf'), [(107, 'טבלה 20: PM2.5 לפי תחנה, 2024 (מוסטת בשורה)'), (103, 'PM10 לפי תחנה, 2024; ערכי סביבה לפי סוג (PM10)'), (111, 'טבלת השוואה PM2.5 2023–2024')]),
    2025: ('איגוד_דוח_שנתי_2025.pdf', 'https://www.envihaifa.org.il/prdFiles/' + Q('דוח שנתי 2025- איגוד ערים מפרץ חיפה להגנת הסביבה_compressed.pdf'), [(106, 'טבלה 22: PM2.5 לפי תחנה, 2025; ערכי סביבה ויעד'), (110, 'טבלה 24: השוואת PM2.5 2024–2025 (ערכים מוסטים בשורה)')]),
}
rep_info = []
for y, (fn, url, pages) in reports.items():
    src = base + r'\מקורות\pdf' + '\\' + fn
    dst = D['rep'] + f'\\דוח_שנתי_איגוד_ערים_מפרץ_חיפה_{y}.pdf'
    shutil.copy2(src, dst)
    try:
        data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=240).read()
        same = hashlib.sha256(data).hexdigest() == sha(src)
        status = 'זהה לקובץ באתר האיגוד (SHA-256 זהה, נבדק 18.10.2026)' if same else 'שונה מהקובץ באתר (יש לבדוק)'
    except Exception as e:
        status = 'לא נבדק מול האתר: %s' % e
    doc = pymupdf.open(src); out = pymupdf.open()
    for pg, _ in pages:
        out.insert_pdf(doc, from_page=pg - 1, to_page=pg - 1)
    ex = D['rep'] + f'\\קטעים_רלוונטיים_דוח_{y}.pdf'
    out.save(ex)
    rep_info.append(dict(y=y, url=url, status=status, sha=sha(src), pages=pages, total=len(doc), mb=mb(src), file=os.path.basename(dst), extract=os.path.basename(ex)))
    print(y, status)
# ---------- 1b. reports of other associations (found through the user's search file); downloaded copies in %TEMP%\ext_reports ----------
ext_dir = os.path.join(os.environ['TEMP'], 'ext_reports')
ext_urls = re.findall(r'\[PDF ישיר\]\(([^)]+)\)', open(base + r'\היכן חיפשנו ומה לא נמצא.md', encoding='utf-8').read())
ext_urls = list(dict.fromkeys(ext_urls))
EXT = [  # (local temp file, url index, package name, title, pages used, note)
    ('r1.pdf', 0, 'איגוד_אשדוד_חבל_יבנה_דוח_שנתי_2023.pdf', 'איגוד ערים אשדוד-חבל יבנה: דוח שנתי 2023', [(53, 'NO2'), (54, 'אוזון'), (55, 'PM2.5 לפי תחנה (בשימוש לאימות)'), (56, 'בנזן (בקובץ החיפוש מסומן כ-PM10; בפועל בנזן)')], 'אומת: PM2.5, 8 תחנות'),
    ('r2.pdf', 1, 'איגוד_אשדוד_חבל_יבנה_דוח_פעילות_2024.pdf', 'איגוד ערים אשדוד-חבל יבנה: דוח פעילות 2024', [(38, 'NO2'), (39, 'אוזון'), (40, 'PM2.5 לפי תחנה (בשימוש לאימות)'), (41, 'בנזן')], 'אומת: PM2.5, 8 תחנות'),
    ('r3.pdf', 2, 'איגוד_אשדוד_חבל_יבנה_דוח_2025.pdf', 'איגוד ערים אשדוד-חבל יבנה: דוח 2025', [(34, 'NO2'), (35, 'אוזון'), (36, 'PM2.5 לפי תחנה (בשימוש לאימות)'), (37, 'בנזן')], 'אומת: PM2.5, 8 תחנות'),
    ('r4.pdf', 3, 'איגוד_אשקלון_דוח_שנתי_2024.pdf', 'איגוד ערים אשקלון: דוח שנתי 2024', [(35, 'אוזון'), (37, 'NO2'), (38, 'טבלה 7: PM2.5 לפי תחנה (בשימוש לאימות)')], 'אומת: PM2.5, 10 תחנות'),
    ('r6.pdf', 5, 'איגוד_שרון_כרמל_דוח_שנתי_2024.pdf', 'איגוד ערים לסביבה שרון כרמל: דוח שנתי 2024', [(13, 'PM2.5 ו-PM10: טקסט'), (14, 'PM2.5: תרשים מגמה'), (15, 'PM10: סיכום')], 'נפתח (בקובץ החיפוש מסומן כחסום 403); טבלת ממוצעים לפי תחנה לא אותרה בטקסט, ולכן לא אומת'),
]
ext_info = []
for fn, ui, name, title, pages, note in EXT:
    srcf = os.path.join(ext_dir, fn)
    if not os.path.exists(srcf):
        continue
    shutil.copy2(srcf, D['rep'] + '\\' + name)
    doc = pymupdf.open(srcf); out = pymupdf.open()
    for pg, _ in pages:
        out.insert_pdf(doc, from_page=pg - 1, to_page=pg - 1)
    exn = 'קטעים_' + name
    out.save(D['rep'] + '\\' + exn)
    ext_info.append(dict(title=title, url=ext_urls[ui], pages=pages, note=note, sha=sha(srcf), mb=mb(srcf), name=name, total=len(doc)))
    print('ext', name, '%.1f MB' % mb(srcf))
# WHO
who_url = 'https://www.winchester.gov.uk/assets/attach/31475/9789240034228-eng.pdf'
whop = D['rep'] + '\\WHO_global_air_quality_guidelines_2021.pdf'
if not os.path.exists(whop):
    open(whop, 'wb').write(urllib.request.urlopen(urllib.request.Request(who_url, headers=UA), timeout=240).read())
wd = pymupdf.open(whop); wo = pymupdf.open(); wo.insert_pdf(wd, from_page=18, to_page=18); wo.save(D['rep'] + '\\WHO_2021_Table_0.1_עמוד_19.pdf')
shutil.copy2(base + r'\מקורות\דפי-אינטרנט\gov_il_ערכי_איכות_אוויר_2026-10-17.txt', D['rep'] + '\\gov_il_ערכי_איכות_אוויר_תוקף_תקנות.txt')

# ---------- 2. station list ----------
shutil.copy2(base + r'\מקורות\mana_stations_list_2026-10-17.json', D['st'] + '\\mana_stations_list_2026-10-17.json')
shutil.copy2(base + r'\נתונים\national_2025\_stations.csv', D['st'] + '\\stations_used_161.csv')

# ---------- 3. raw data zips ----------
for y in (2023, 2024, 2025):
    zp = D['raw'] + f'\\national_{y}.zip'
    if not os.path.exists(zp):
        with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for f in sorted(glob.glob(base + rf'\נתונים\national_{y}\*')):
                z.write(f, os.path.basename(f))
    print('zip', y, '%.1f MB' % mb(zp))

# ---------- 4. results ----------
res_files = [r'נתונים\national_summary_station.csv', r'נתונים\national_summary_station_year.csv', r'נתונים\validation_national_vs_official.csv', r'נתונים\validation_other_associations.csv', r'validate_other_associations_output.txt', r'נתונים\validation_no2_other_associations.csv', r'נתונים\validation_o3_other_associations.csv', r'validate_no2_o3_other_associations_output.txt', r'national_analysis_output.txt', r'audit_recompute_output.txt', r'audit_sensitivity_output.txt',
             r'classification_sensitivity_output.txt', r'validate_national_vs_official_output.txt', r'national_compare_2025_output.txt']
for f in res_files:
    if os.path.exists(base + '\\' + f):
        shutil.copy2(base + '\\' + f, D['res'] + '\\' + os.path.basename(f))
# ---------- 5. scripts ----------
scr = ['fetch_national_year.py', 'national_analysis.py', 'audit_recompute.py', 'validate_national_vs_official.py', 'validate_other_associations.py', 'validate_no2_o3_other_associations.py', 'classification_sensitivity.py']
for f in scr:
    shutil.copy2(base + r'\נתונים' + '\\' + f, D['scr'] + '\\' + f)
sp = r'C:\Users\Zevik\AppData\Local\Temp\claude\C--Users-Zevik-Documents-----------------\173011dd-2bac-4be9-a8fb-cab9574b6e7a\scratchpad'
for f in ['build_national_report2.py', 'build_charts.py', 'charts_template.html']:
    shutil.copy2(sp + '\\' + f, D['scr'] + '\\' + f)
shutil.copy2(base + chr(92) + 'נתונים' + chr(92) + 'audit_sensitivity.py', D['scr'] + chr(92) + 'audit_sensitivity.py')

# ---------- worked example (Tivon 2025) ----------
raw = pd.read_csv(base + r'\נתונים\national_2025\st137.csv')
raw = raw[raw.valid == True]
raw['t'] = pd.to_datetime(raw.datetime.str[:19])
pm = raw[raw.channel == 'PM2.5'].set_index('t').value
dmn = pm.groupby(pm.index.date).agg(['mean', 'count', 'sum'])
dv = dmn[dmn['count'] >= 18]
no2 = raw[raw.channel == 'NO2'].value
o3 = raw[raw.channel == 'O3'].set_index('t').value.reindex(pd.date_range('2025-01-01', '2025-12-31 23:00', freq='h'))
ro = o3.rolling(8, min_periods=6).mean()
dayro = ro['2025-07-10']
ex_day = dayro.round(2)
ex = dict(pm_n=len(pm), pm_sum=pm.sum(), pm_mean=pm.mean(), pm_days=len(dv), pm_gt15=int((dv['mean'] > 15).sum()), no2_n=len(no2), no2_mean=no2.mean(), no2_ug=no2.mean() * 1.8804,
          o3_day_max=float(round(dayro.max(), 6)), o3_day_vals=[None if pd.isna(v) else round(v, 1) for v in o3['2025-07-10']], o3_day_roll=[None if pd.isna(v) else round(v, 2) for v in dayro])
print(ex['pm_n'], ex['pm_mean'], ex['o3_day_max'])

A = pd.read_csv(base + r'\נתונים\national_summary_station.csv', encoding='utf-8').set_index('id')
SY = pd.read_csv(base + r'\נתונים\national_summary_station_year.csv', encoding='utf-8')
VAL = pd.read_csv(base + r'\נתונים\validation_national_vs_official.csv', encoding='utf-8')
f1 = lambda v: '' if pd.isna(v) else '%.1f' % v
f2 = lambda v: '' if pd.isna(v) else '%.2f' % v
f0 = lambda v: '' if pd.isna(v) else '%.0f' % v
rel = lambda p: p.replace('\\', '/')


def md(df, cols, heads):
    out = ['| ' + ' | '.join(heads) + ' |', '| ' + ' | '.join(['---'] * len(heads)) + ' |']
    for _, r in df.iterrows():
        out.append('| ' + ' | '.join(str(r[c]) for c in cols) + ' |')
    return '\n'.join(out)


PK = 'חבילת ראיות - השוואה ארצית'
lnk = lambda sub, fn: '[%s](%s)' % (fn, urllib.parse.quote(PK + '/' + sub + '/' + fn))
# sources table
src_rows = [
    ('מנ"א: אתר ממשלתי לנתוני איכות אוויר', 'https://air.sviva.gov.il/', 'מקור אסימון האורח לקריאת ה-API; תיעוד ציבורי', 'נבדק 18.10.2026 (HTTP 200)'),
    ('מנ"א: ממשק הנתונים (API)', 'https://air-papi.sviva.gov.il/v1/envista/stations/{id}/data?timebase=60&from=YYYY/MM/DD&to=YYYY/MM/DD', 'כל הנתונים השעתיים (PM2.5, PM10, O3, NO2) ל-161 תחנות, 2023–2025; כותרת Authorization: ApiToken (אסימון אורח מהאתר, מתחלף)', 'נקרא 17–18.10.2026; נתונים גולמיים בחבילה (03)'),
    ('מנ"א: רשימת התחנות', 'https://air-papi.sviva.gov.il/v1/envista/stations', 'מטא-דאטה: שם, יישוב, בעלים, סוג, גובה, קואורדינטות, ערוצים (278 תחנות)', 'עותק בחבילה (02)'),
]
for r in rep_info:
    src_rows.append(('איגוד ערים אזור מפרץ חיפה: דוח שנתי %d' % r['y'], r['url'], 'אימות ה-API: ' + '; '.join('עמ\' %d: %s' % (p, t) for p, t in r['pages']), r['status'] + '; SHA-256: ' + r['sha'][:16]))
src_rows += [
    ('WHO: Global air quality guidelines 2021 (דף הפרסום)', 'https://www.who.int/publications/i/item/9789240034228', 'הנחיות WHO: PM2.5 5/15, PM10 15/45, אוזון 100 (8 שעות, אחוזון 99: 3–4 ימים) ו-60 (עונה), NO2 10/25 (מק"ג/מ"ק)', 'דף נפתח (HTTP 200)'),
    ('WHO: המסמך המלא (עותק משוכפל)', who_url, 'טבלה 0.1 (עמ\' xvii, עמוד 19 ב-PDF): הערכים לעיל; עותק בחבילה', 'נקרא 18.10.2026; מקור רשמי: https://iris.who.int/handle/10665/345329'),
    ('המשרד להגנת הסביבה: ערכי איכות אוויר', 'https://www.gov.il/he/pages/air_quality_values', 'תוקף תקנות 2022 (1.3.2022) ועדכון אבק (1.1.2023)', 'נקרא בדפדפן 18.10.2026 (בקשות אוטומטיות מקבלות 403)'),
    ('איגוד ערים, דוחות 2023–2025: ערכי הסביבה בישראל', 'ראו שורות הדוחות לעיל', 'PM2.5: ערך סביבה שנתי 25 (טבלה 22, עמ\' 106 בדוח 2025); PM10: ערך סביבה שנתי 50 אחרי הורדת ימי סופת אבק (עמ\' 103 בדוח 2024)', 'נבדק בתמונת העמוד'),
]
for e in ext_info:
    src_rows.append((e['title'], e['url'], 'אימות ה-API: ' + '; '.join('עמ\' %d: %s' % (pg, tx) for pg, tx in e['pages']), e['note'] + '; נקרא 18.10.2026; SHA-256: ' + e['sha'][:16] + '; ' + '%.1f MB, %d עמ\'' % (e['mb'], e['total'])))
src_rows.append(('קישורים בקובץ החיפוש ש**אינם פעילים** (HTTP 404, נבדקו 18.10.2026)', 'איגוד אשקלון 2025 (e-a.org.il, "דוח שנת 2025 - ניטור.pdf"); חברת החשמל 2023 ו-2024 (ieccontent.iec.co.il, iecmedia.iec.co.il)', 'לא שימשו', 'שלושה קישורים לחברת החשמל ואחד לאשקלון 2025 מחזירים 404; צריך למצוא כתובות נכונות'))
tab_src = md(pd.DataFrame(src_rows, columns=['a', 'b', 'c', 'd']), ['a', 'b', 'c', 'd'], ['מקור', 'כתובת', 'שימוש בדוח ההשוואה', 'סטטוס בדיקה'])

stn = pd.read_csv(base + r'\נתונים\national_2025\_stations.csv').set_index('id')
A2 = A.copy()
A2['city'] = A2['city'].replace({'קיריית טבעון': 'קריית טבעון'}).fillna('—')
tab_meta = md(A2.reset_index().assign(h=lambda d: d.h.map(f0), coast_km=lambda d: d.coast_km.map(f0), lat=lambda d: d.lat.map(lambda v: '%.4f' % v), lon=lambda d: d.lon.map(lambda v: '%.4f' % v)),
              ['id', 'name', 'city', 'owner', 'class', 'region', 'h', 'coast_km', 'lat', 'lon'], ['מזהה', 'תחנה', 'יישוב', 'בעלים', 'סוג', 'אזור', 'גובה (מ\')', 'מרחק מחוף (ק"מ)', 'קו רוחב', 'קו אורך'])
SYn = SY.merge(A2[['name', 'city']], left_on='id', right_index=True, how='left')
SYn = SYn.sort_values(['id', 'year'])
tab_sy = md(SYn.assign(pm25=lambda d: d.pm25.map(f2), pm10=lambda d: d.pm10.map(f2), no2=lambda d: d.no2.map(f2), o3_days51=lambda d: d.o3_days51.map(f1), o3_jja=lambda d: d.o3_jja.map(f2), pm25_days_gt15_pct=lambda d: d.pm25_days_gt15_pct.map(f1),
                 pm25_cov=lambda d: d.pm25_cov.map(f0), o3_cov=lambda d: d.o3_cov.map(f0)),
            ['id', 'name', 'year', 'pm25', 'pm25_cov', 'pm25_days_gt15_pct', 'pm10', 'no2', 'o3_days51', 'o3_jja', 'o3_cov'], ['מזהה', 'תחנה', 'שנה', 'PM2.5', 'כיסוי PM2.5 %', '% ימים >15', 'PM10', 'NO2', 'ימי אוזון >51 ppb', 'MDA8 קיץ ppb', 'כיסוי אוזון %'])
VAL2 = pd.read_csv(base + r'\נתונים\validation_other_associations.csv', encoding='utf-8')
N2 = pd.read_csv(base + r'\נתונים\validation_no2_other_associations.csv', encoding='utf-8'); O2 = pd.read_csv(base + r'\נתונים\validation_o3_other_associations.csv', encoding='utf-8')
N2g = N2[N2.api_cov_pct >= 85]; O2g = O2[O2.api_cov_pct >= 85]
n2_ash, n2_ask = N2g[N2g.assoc.str.contains('אשדוד')], N2g[N2g.assoc.str.contains('אשקלון')]
n2_exc = '; '.join('%s %d, מזהה %d, כיסוי API %.0f%%, רשמי %.1f מול API %.1f' % (r.station, r.year, r.id, r.api_cov_pct, r.official, r.api) for r in N2[(N2.api_cov_pct < 85) & N2.api.notna()].itertuples())
o3_lo = O2g[O2g.ratio_mean > 1.5]
f2_ = lambda v: '' if pd.isna(v) else '%.2f' % v
f3_ = lambda v: '' if pd.isna(v) else '%.3f' % v
tab_n2 = md(N2.assign(official=N2.official.map(f1), api=N2.api.map(f2_), diff=N2['diff'].map(lambda v: '' if pd.isna(v) else '%+.2f' % v), api_cov_pct=N2.api_cov_pct.map(f0)), ['assoc', 'year', 'station', 'id', 'official', 'api', 'diff', 'api_cov_pct'], ['איגוד', 'שנה', 'תחנה', 'מזהה', 'דוח האיגוד', 'API', 'הפרש', 'כיסוי API %'])
tab_o3 = md(O2.assign(off_mean=O2.off_mean.map(f1), api_mean_ppb=O2.api_mean_ppb.map(f2_), ratio_mean=O2.ratio_mean.map(f3_), off_max8=O2.off_max8.map(f1), api_max8_ppb=O2.api_max8_ppb.map(f2_), ratio_max8=O2.ratio_max8.map(f3_), api_cov_pct=O2.api_cov_pct.map(f0)), ['assoc', 'year', 'station', 'id', 'off_mean', 'api_mean_ppb', 'ratio_mean', 'off_max8', 'api_max8_ppb', 'ratio_max8', 'api_cov_pct'], ['איגוד', 'שנה', 'תחנה', 'מזהה', 'ממוצע רשמי (מק"ג/מ"ק)', 'ממוצע API (ppb)', 'יחס', 'מרבי 8 שעות רשמי', 'מרבי 8 שעות API (ppb)', 'יחס', 'כיסוי API %'])
v2 = VAL2[VAL2.api_cov_pct >= 50]
v2tab = lambda d: md(d.assign(official=d.official.map(f1), api=d.api.map(f2), diff=d['diff'].map(lambda v: '%+.2f' % v), api_cov_pct=d.api_cov_pct.map(f0)), ['year', 'station', 'id', 'official', 'api', 'diff', 'api_cov_pct'], ['שנה', 'תחנה', 'מזהה', 'דוח האיגוד', 'API', 'הפרש', 'כיסוי API %'])
tab_ash = v2tab(v2[v2.assoc.str.contains('אשדוד')]); tab_ask = v2tab(v2[v2.assoc.str.contains('אשקלון')])
stat2 = lambda d: 'n=%d, הפער הממוצע המוחלט %.2f, המרבי %.2f' % (len(d), d['diff'].abs().mean(), d['diff'].abs().max())
exc2 = '; '.join('%s (מזהה %d, כיסוי API %.0f%%)' % (r.station, r.id, r.api_cov_pct) for r in VAL2[VAL2.api_cov_pct < 50].itertuples())
vt = VAL.copy()
tab_val = md(vt.assign(official=vt.official.map(f1), api=vt.api.map(f2), diff=vt['diff'].map(lambda v: '%+.2f' % v), api_coverage_pct=vt.api_coverage_pct.map(f0)), ['pollutant', 'year', 'station', 'id', 'official', 'api', 'diff', 'api_coverage_pct'], ['מזהם', 'שנה', 'תחנה', 'מזהה', 'דוח האיגוד', 'API', 'הפרש', 'כיסוי API %'])
read = lambda f: open(base + '\\' + f, encoding='utf-8').read()
aud = read('audit_recompute_output.txt')
sens = read('audit_sensitivity_output.txt')
clsens = read('classification_sensitivity_output.txt')
valout = read('validate_national_vs_official_output.txt')
valout_shift = valout[valout.find('===== 2024 PM2.5'):]
valout_shift = re.sub(r"np\.float64\(([0-9.\-]+)\)", r"\1", valout_shift)

appendix = f'''# נספח: מקורות, נתונים וחישובים (השוואה ארצית, קריית טבעון מול שאר הארץ)

תאריך: 18.10.2026. נספח ל[דוח ההשוואה הארצית](השוואה%20ארצית%20-%20קריית%20טבעון%20מול%20שאר%20הארץ.md) ול[גרפים](השוואה%20ארצית%20-%20גרפים.html). המטרה: שכל מספר, טענה וחישוב בהשוואה יהיו ניתנים לבדיקה עצמאית. הקבצים עצמם בתיקייה **`{PK}/`** (מצורפת), והם רשומים בסעיף 10 עם SHA-256.

## 1. תוכן החבילה

| תיקייה | תוכן |
| --- | --- |
| `01 - דוחות רשמיים ומסמכי ייחוס` | שלושת הדוחות השנתיים של איגוד ערים חיפה (2023–2025; עותקים זהים לקובצי האתר), חמישה דוחות של איגודי ערים אחרים (אשדוד-חבל יבנה 2023–2025, אשקלון 2024, שרון-כרמל 2024), קטעי העמודים הרלוונטיים מכל דוח, מסמך WHO 2021 ועמוד הטבלה 0.1, וטקסט הדף של gov.il |
| `02 - רשימת תחנות` | רשימת התחנות המלאה של מנ"א (JSON, 278 תחנות) ו-161 התחנות שנשלפו (CSV) |
| `03 - נתונים גולמיים (zip)` | נתונים שעתיים גולמיים של 161 תחנות (PM2.5, PM10, O3, NO2), קובץ לכל תחנה, זיפ לכל שנה |
| `04 - תוצאות מעובדות ופלטי בדיקה` | טבלאות התוצאות (CSV) ופלטי הסקריפטים והביקורות |
| `05 - סקריפטים` | כל הקוד שיצר את המספרים, ההשוואות והמסמכים |
| `06 - מסמכי הפרסום` | דוח ההשוואה, הגרפים, הסיכום בשפה פשוטה, דוח הביקורת הפנימית והנספח הזה |

## 2. מקורות וקישורים

{tab_src}

**הערה על קישורים:** בקשות אוטומטיות לחלק מהאתרים הממשלתיים (gov.il, data.gov.il, האתר של עיריית קריית ים) נחסמות (403 או הפניה); בדפדפן הם נפתחים. לכן העותקים בחבילה הם העוגן: דוח 2024 באתר האיגוד זהה (SHA-256) לקובץ השמור, ולא נעשה שימוש בעותק של עיריית קריית ים.

## 3. הגדרות ונוסחאות

1. **ממוצע שנתי:** ממוצע כל השעות עם `valid=True` בשנה. **כיסוי:** שעות תקפות חלקי שעות השנה (8,760; 8,784 ב-2024).
2. **תחנה-שנה נכללת** אם הכיסוי השנתי לפחות 75% **ובכל עונה** (חורף דצמבר–פברואר, אביב מרץ–מאי, קיץ יוני–אוגוסט, סתיו ספטמבר–נובמבר) לפחות 50% שעות תקפות במזהם (למניעת הטיה עונתית). נדרש לפחות שנתיים תקפות לממוצע תלת-שנתי. תחנה-שנה עם PM2.5 מתחת ל-5 או מעל 60 (ערך שלילי באורות רבין, חדרה, 2024) הוצאה. PM10 מתחת ל-15 או מעל 150 הוצא (ערך מתחת ל-15 אינו סביר בישראל; נמצא אחד: אורות רבין 2024, 13.6). **יציבות האוזון:** תחנה שמספר ימי האוזון השנתי שלה (אחרי הכיסוי) משתנה פי יותר מ-2.5 בין שנותיה הוצאה מדירוג האוזון (שונות גבוהה; אינה בהכרח טעות, ותחנה 122 למשל תואמת לדוח האיגוד): תחנות {', '.join(str(i) for i in UNST)}.
3. **יום תקף ל-PM2.5:** לפחות 18 שעות תקפות. **% ימים מעל 15:** ימי ממוצע יממתי מעל 15 מק"ג/מ"ק חלקי הימים התקפים (15 = הנחיית WHO היממתית).
4. **MDA8:** לכל שעה, ממוצע ה-8 שעות המסתיימות בה (6 שעות תקפות לפחות מתוך 8); ה-MDA8 של יום הוא המרבי של ממוצעים אלה בשעות היום, ליום תקף נדרשים 18 ממוצעים לפחות. **ימי אוזון:** ימים עם MDA8 של 51 ppb לפחות, מנורמל ל-365 ימים (`ימים × 365 / ימים תקפים`). **51 ppb:** 1 ppb אוזון = 48.00/24.4655 = 1.962 מק"ג/מ"ק ב-25°C ו-1 atm, ולכן 100/1.962 = 50.97, כלומר 100 מק"ג/מ"ק (הנחיית WHO ל-8 שעות) הם כ-51 ppb. ההשוואה ב-ppb מבטלת את תלות הדירוג בגורם ההמרה.
5. **NO2:** ממוצע ב-ppb × 46.0055/24.4655 = 1.8804 (25°C, 1 atm).
6. **ימי אבק אזוריים:** בכל שנה, חציון ה-PM10 היומי (יממה תקפה: 18 שעות) על פני כל תחנות ה-PM10 גבוה מ-60 מק"ג/מ"ק; נוסף היום שאחריו (53–61 ימים בשנה). **PM2.5 בלי אבק:** ממוצע הימים התקפים שאינם ימי אבק (נדרשים 150 ימים לפחות).
7. **ממוצע תלת-שנתי לתחנה:** ממוצע הערכים של השנים התקפות. **חציון, רבעונים ודירוג:** על פני תחנות. **"X% מהתחנות נמוכות מטבעון":** שיעור התחנות עם ערך נמוך ממש מערך טבעון. **דירוג:** מספר התחנות עם ערך גבוה ממש, ועוד אחת (1 = הגבוה ביותר).
8. **סוג תחנה:** *תחבורה* (סוג "תחבורתית" או "תחנות פנים מבניות", או בעלות נתיבי ישראל, נתיבי איילון, רכבת ישראל או התחנה המרכזית); *תעשייה/מחצבה/תחנת כוח* (סוג "על הגדר", "תעשייתית" או "נמלי ים", או בעלות/שם עם מחצבה, אבן וסיד, תחנת כוח, ת"כ, MRC, או.פי, נאות חובב, שברון, ים המלח, או שם התחנה כולל "תעשייה", או בעלות "נשר" או "שפיר"); *רקע עירוני/כללי*: השאר. **מגבלה:** הסיווג יוריסטי; אינו מבחין בין תחנות של חברת החשמל לתחנות כוח פרטיות, ותחנה אחת הסומנה כלא פעילה במטא-דאטה נשארת במדגם. נבדקה רגישות לסיווג ולהשמטת אזורים (סעיף 7).
9. **אזור:** לפי יישוב ובעלות וקואורדינטות (תל אביב וגוש דן, חיפה והקריות, ירושלים, נגב וערבה, דרום החוף והשפלה הדרומית, שרון וכרמל, עמקים וגליל, שפלה ומודיעין); טבעון בנפרד. קוד הסיווג ב-`national_analysis.py` (פונקציות `klass` ו-`region`).
10. **מרחק מהחוף:** `(קו אורך התחנה − קו אורך החוף באותו קו רוחב) × 95 ק"מ`, כשקו החוף הוא אינטרפולציה לינארית בין נקודות (קו רוחב 31.50→34.47, 31.66→34.55, 31.80→34.64, 32.08→34.76, 32.33→34.85, 32.45→34.88, 32.70→34.95, 32.82→35.00, 32.90→35.07, 33.09→35.10); הערכה גסה. **גובה:** מרשימת התחנות; לתחנות 384, 385 ו-454 שדה הגובה ב-API מכיל ערך שאינו גובה (קו אורך), ולתחנות 563 (0 מ') ו-586 (+232 מ' בבקעת הירדן) ערך לא סביר; כולן הוצאו. ארבע תחנות דרומית ל-31.1°N (דרום הנגב והערבה) נשארות בלי מרחק מחוף, כי קו החוף שבשימוש מכסה 31.5–33.1°N.
11. **התאמה (סעיף 4.6 בדוח):** `ערך ~ תחבורה + תעשייה + גובה/100 + מרחק מחוף/10` (OLS, שגיאות תקן HC1), על ממוצעי תחנות, בלי תחנות מתחת ל-100 מ\' מתחת לפני הים או רחוקות מ-80 ק"מ מהחוף; לאוזון בלי משתנה התחבורה (אין תחנות תחבורה עם אוזון).
12. **ערכי ייחוס בגרפים:** PM2.5: WHO 5 (שנתי), ישראל 25 (טבלה 22 בדוח 2025); NO2 ישראל 40 ואוזון ישראל 140 מק"ג/מ"ק ל-8 שעות (טבלאות האוזון והחנקן הדו-חמצני בדוח אשקלון 2024, עמ' 35 ו-37); PM10: WHO 15, ישראל 50 (ערך סביבה שנתי אחרי הורדת ימי סופת אבק, עמ\' 103 בדוח 2024); NO2: WHO 10; אוזון: WHO 100 מק"ג/מ"ק ל-8 שעות, 3–4 ימים בשנה (טבלה 0.1 של WHO, הערה a).

## 4. תהליך (צעד אחר צעד)

1. `fetch_national_year.py <שנה>`: קורא את אסימון האורח מ-`air.sviva.gov.il`, ולכל תחנה פעילה ונייחת עם PM2.5 או אוזון (161) שולף חודש אחר חודש את הנתונים השעתיים מה-API ושומר ערוצי PM2.5, PM10, O3 ו-NO2.
2. `national_analysis.py`: מחשב מדדי תחנה-שנה, בקרת איכות, ימי אבק, סיווג, ממוצעי תחנה, דירוגים, רגרסיות; כותב `national_summary_station_year.csv`, `national_summary_station.csv` ופלט.
3. `validate_national_vs_official.py`: משווה ל-API את הערכים הרשמיים שהועתקו מדוחות האיגוד.
4. `audit_recompute.py`: חישוב עצמאי של כל המדדים מהנתונים הגולמיים, בקוד אחר (numpy), והשוואה לתוצאות הצינור.
5. `classification_sensitivity.py`: רגישות הדירוג לסיווג ולהשמטת אזורים.
6. `build_national_report2.py` ו-`build_charts.py`: מייצרים את הדוח והגרפים מהקבצים; כל מספר בדוח מחושב, והבנייה נכשלת אם טענה איכותית שנבדקת בקוד (למשל "טבעון נמוכה מכל האזורים באוזון") אינה נכונה.

**הרצה מחדש:** `python -I fetch_national_year.py 2023` (וכן 2024 ו-2025), `python -I national_analysis.py`, `python -I audit_recompute.py`.

## 5. דוגמת חישוב מלאה: טבעון, 2025

- **PM2.5:** {ex['pm_n']:,} שעות תקפות מתוך 8,760 ({100*ex['pm_n']/8760:.1f}%), סכום {ex['pm_sum']:,.1f}, ממוצע שנתי **{ex['pm_mean']:.2f}** מק"ג/מ"ק. ימים תקפים (18 שעות לפחות): {ex['pm_days']}; מתוכם {ex['pm_gt15']} עם ממוצע יממתי מעל 15, כלומר {100*ex['pm_gt15']/ex['pm_days']:.1f}%.
- **NO2:** {ex['no2_n']:,} שעות תקפות, ממוצע {ex['no2_mean']:.2f} ppb × 1.8804 = **{ex['no2_ug']:.2f}** מק"ג/מ"ק.
- **MDA8, יום לדוגמה 10.7.2025:** ערכי האוזון השעתיים (ppb, שעות 00:00–23:00 לפי שעון חורף קבוע): {ex['o3_day_vals']}. ממוצעי 8 השעות המסתיימים בכל שעה: {ex['o3_day_roll']}. ה-MDA8 של היום = המרבי = **{ex['o3_day_max']}** ppb.
- הערכים לכל שלוש השנים והממוצע התלת-שנתי: בטבלת תחנה-שנה (סעיף 9) ובקובץ `national_summary_station_year.csv`.

## 6. אימות מול הדוחות הרשמיים

{tab_val}

**סיכום:** PM2.5 2023 ו-2025 (22 השוואות, 11 תחנות בכל שנה, איגוד חיפה): תואם; PM10 2023–2024 (14 השוואות): הפער הממוצע המוחלט 0.05, המרבי 0.16. **איגוד אשדוד-חבל יבנה** (PM2.5, 8 תחנות, 2023–2025, 24 השוואות) ו**איגוד אשקלון** (PM2.5 2024, 10 תחנות): טבלאות בסעיף 6א. **PM2.5 ב-2024 לא שימש לאימות:** טבלה 20 בדוח 2024 מוסטת בשורה אחת. הוכחה (פלט `validate_national_vs_official.py`):

```
{valout_shift}```

בטבלה 24 בדוח 2025, כל הערכים אחרי "נשר" זהים לערך בטבלה 22 **במיקום השורה** (לא באותה תחנה), כי שתי תחנות הוסרו מרשימת התוויות והערכים שלהן נשארו.

## 6א. אימות מול דוחות איגודים נוספים (PM2.5)

הדוחות נמצאו בחיפוש ידני (קובץ "היכן חיפשנו ומה לא נמצא") ונבדקו: הקבצים בתיקייה 01. ערכי הדוח הועתקו מהטבלאות בעמודים המצוינים בסעיף 2, והושוו לממוצע שעות תקפות ב-API (`validate_other_associations.py`). **הערה:** בקובץ החיפוש עמוד 56 (2023), 41 (2024) ו-37 (2025) של אשדוד מסומנים כ-PM10, אך בפועל הם טבלאות בנזן; לכן PM10 באשדוד לא אומת.

**איגוד אשדוד-חבל יבנה, PM2.5 2023–2025** ({stat2(v2[v2.assoc.str.contains('אשדוד')])}):

{tab_ash}

**איגוד אשקלון, PM2.5 2024** ({stat2(v2[v2.assoc.str.contains('אשקלון')])}). הוצאה תחנה שבה ל-API פחות מ-50% מהשעות: {exc2}.

{tab_ask}

## 6ב. אימות NO2 ואוזון מול דוחות אשדוד ואשקלון

הערכים הועתקו מהטבלאות בדוחות (אשדוד: NO2 עמ' 53, 38, 34; אוזון עמ' 54, 39, 35; אשקלון 2024: אוזון טבלה 4 עמ' 35, NO2 טבלה 6 עמ' 37) והושוו ל-API (`validate_no2_o3_other_associations.py`, פלט `validate_no2_o3_other_associations_output.txt`). **NO2:** ממוצע API ב-ppb × 1.8804 מול הממוצע הרשמי (מק"ג/מ"ק). **אוזון:** גורם ההמרה אינו מפורסם, ולכן מחושב היחס הרשמי/API; יחס יציב בסביבות 1.96 (הגורם הפיזיקלי ב-25°C) פירושו התאמה.

**תוצאות (תחנות עם כיסוי API של 85% לפחות):** NO2 באשדוד {len(n2_ash)} השוואות, פער ממוצע מוחלט {n2_ash['diff'].abs().mean():.2f} ומרבי {n2_ash['diff'].abs().max():.2f}; באשקלון {len(n2_ask)} השוואות, {n2_ask['diff'].abs().mean():.2f} ו-{n2_ask['diff'].abs().max():.2f}. אוזון: יחס הממוצע השנתי {o3_lo.ratio_mean.mean():.3f} (טווח {o3_lo.ratio_mean.min():.2f}–{o3_lo.ratio_mean.max():.2f}, {len(o3_lo)} השוואות); יחס המרבי השמונה-שעתי {o3_lo.ratio_max8.min():.2f}–{o3_lo.ratio_max8.max():.2f} (ה-API גבוה יותר מהרשמי בשיעור משתנה).

**חריגים:** תחנה 535 (אזור תעשייה צפוני, אשדוד 2025): ב-API כיסוי 63% וממוצע 25.7 מול 14.9 רשמי; תחנת שדרות (126): כיסוי API 4%; תחנה 365 (בני דרום) אינה בנתוני ה-API שנשלפו (הועברה לקבוצת יבנה מערב, 511, בפברואר 2025); תחנה 511 באוזון 2025: כיסוי API 67% וערך רשמי (31.2) שנראה כמספר ppb ולא מק"ג/מ"ק. הם הוצאו מהסטטיסטיקה ומוצגים בטבלאות.

**הערה על יציבות האוזון:** תחנת יד בנימין (122) הוצאה מדירוג האוזון הארצי בכלל היציבות (שונות פי יותר מ-2.5 בין שנים), אך נתוניה תואמים לדוחות האיגוד (ממוצע רשמי 52.9, 63.2, 69.5 ומרבי 132, 153, 182). הכלל מסמן שונות גבוהה, לא בהכרח טעות.

**NO2:**

{tab_n2}

**אוזון:**

{tab_o3}

## 7. בדיקות ביקורת עצמאיות

**חישוב מחדש בקוד נפרד (`audit_recompute.py`):**

```
{aud}```

**רגישות לערכים שליליים וקיצוניים (`audit_sensitivity`):**

```
{sens}```

**רגישות לסיווג ולהשמטת אזורים (`classification_sensitivity.py`):**

```
{clsens}```

## 8. מגבלות ידועות

- נתוני API גולמיים. אומתו מול דוחות: איגוד חיפה (PM2.5 2023 ו-2025; PM10 2023–2024), אשדוד (PM2.5 2023–2025) ואשקלון (PM2.5 2024). לא אומתו: שרון-כרמל, ירושלים ותחנות המשרד להגנת הסביבה, חברת החשמל, הנגב והצפון; וכן NO2 ואוזון מול דוחות.
- שלוש שנים; 2025 שנת אוזון גבוהה בטבעון.
- סיווג התחנות והאזורים היוריסטי, ומרחק מהחוף מקורב.
- כלל ימי האבק פשוט, ואינו זהה לכלל של האיגוד.
- השוואה בין תחנות, לא חשיפת תושבים. תחנת טבעון על גג ברכס (201 מ\').
- ערכים שליליים ב-PM2.5 ו-NO2 נשארו (נבדקה רגישות). תחנות עם נתונים עד 25% חסרים נכללות.
- אין תחנה בטבריה.

## 9. נתוני תחנות

### 9.1 מטא-דאטה, סיווג ואזור (כל התחנות ברשימה, גם אלה שלא עברו בקרת איכות)

{tab_meta}

### 9.2 תוצאות לכל תחנה-שנה (אחרי בקרת איכות; תא ריק = לא עבר את הבקרה או אין מזהם)

{tab_sy}

(הממוצע התלת-שנתי לכל תחנה, כפי שמופיע בדוח, בנספח ב של דוח ההשוואה וב-`national_summary_station.csv`.)

## 10. קבצים ו-SHA-256

__FILELIST__
'''
open(base + r'\נספח - מקורות נתונים וחישובים (השוואה ארצית).md', 'w', encoding='utf-8').write(appendix)
print('appendix written', len(appendix))
json.dump(dict(rep_info=rep_info), open(sp + r'\pkg_info.json', 'w', encoding='utf-8'), ensure_ascii=False, default=str)
