"""National comparison 2023-2025 (guest API, hourly): station-year metrics, classification (class x region), dust-day adjustment, peer groups and
adjusted regressions. Output: ../national_analysis_output.txt (stdout), ../national_tables.md (markdown tables), national_summary_station_year.csv.
Run: python -I national_analysis.py > ../national_analysis_output.txt"""
import sys, os, glob, re
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
YEARS = [2023, 2024, 2025]
st = pd.read_csv('national_2025/_stations.csv').set_index('id')

# ---------- classification ----------
IND = r'מחצב|אבן וסיד|תחנת כוח|תחנת הכוח|ת"כ|MRC|או\.פי|נאות חובב|שברון|מפעלי ים המלח|מועצה נאות|חברת אבן'
TRAF_OWN = r'נתיבי|איילון|רכבת|תחנה מרכזית|התחנה המרכזית'


def klass(r):
    own, tg = str(r.owner), str(r.target)
    if tg in ('תחבורתית', 'תחנות פנים מבניות') or re.search(TRAF_OWN, own):
        return 'תחבורה'
    if tg in ('על הגדר', 'תעשייתית', 'נמלי ים') or re.search(IND, own) or 'תעשיי' in str(r['name']) or str(r.owner).strip() == 'נשר' or 'שפיר' in str(r.owner):
        return 'תעשייה/מחצבה/תחנת כוח'
    return 'רקע עירוני/כללי'


def region(r):
    c, o, la, lo = str(r.city), str(r.owner), r.lat, r.lon
    if r['name'] == 'קריית טבעון' or c.startswith('קיריית טבעון'):
        return 'טבעון'
    if 'ירושלים' in c or (31.74 < la < 31.88 and 35.18 < lo < 35.26):
        return 'ירושלים'
    if c in ('תל אביב-יפו', 'בני ברק', 'רמת גן', 'פתח תקווה', 'חולון', 'בת ים', 'ראשון לציון', 'אור יהודה', 'רמת השרון', 'רעננה') or (31.95 < la < 32.2 and lo < 34.84):
        return 'תל אביב וגוש דן'
    if 'איגוד ערים חיפה' in o or c == 'חיפה' or (32.74 < la < 32.9 and lo < 35.12 and 'חיפה' in c) or c in ('כפר חסידים', 'כפר מסריק', 'קריית אתא', 'קריית ביאליק', 'קריית ים', 'קריית מוצקין', 'נשר'):
        return 'חיפה והקריות'
    if c in ('באר שבע', 'ערד', 'כסייפה') or 'נאות חובב' in c or la < 31.4 and la > 31.1 and 34.7 < lo < 35.3 or c == 'קטורה' or c == 'אילת':
        return 'נגב וערבה (באר שבע, ערד, אילת)'
    if la < 31.3:
        return 'נגב וערבה (באר שבע, ערד, אילת)'
    if 'אשדוד' in o or 'אשקלון' in o or c in ('אשדוד', 'אשקלון', 'שדרות', 'קריית גת', 'קריית מלאכי', 'כפר מנחם', 'תימורים', 'אביגדור', 'בת הדר', 'פלוגות') or (la < 31.85 and lo < 34.85):
        return 'דרום החוף והשפלה הדרומית (אשדוד, אשקלון, קריית גת)'
    if 'שרון-כרמל' in o or c in ('חדרה', 'נתניה', 'חריש', 'פרדס חנה', 'קיסריה', 'נחשולים') or (32.3 < la < 32.7 and lo < 35.12):
        return 'שרון וכרמל (חדרה, קיסריה)'
    if c in ('עפולה', 'כרמיאל', 'גליל עליון', 'עמק המעיינות', 'יחיעם', 'געתון', 'קדרים', 'כחל', 'טורעאן', 'גבעת המורה', 'עין דור', 'דברת', 'בית יוסף') or (lo > 35.2 and la > 32.4):
        return 'עמקים וגליל (עפולה, בית שאן, כרמיאל)'
    return 'שפלה ומודיעין (רחובות, מודיעין, בית שמש)'


st['class'] = st.apply(klass, axis=1)
st['region'] = st.apply(region, axis=1)
st['h'] = pd.to_numeric(st.height, errors='coerce')
# API list data errors: height field holds a longitude value for these stations (train stations Hagana, Yosefthal; Barkai)
st.loc[[384, 385, 454, 563, 586], 'h'] = np.nan  # 384, 385, 454: field holds a longitude; 563 (0 m) and 586 (+232 m in the Jordan valley) are implausible
coast_lat = [31.5, 31.66, 31.8, 32.08, 32.33, 32.45, 32.7, 32.82, 32.9, 33.09]
coast_lon = [34.47, 34.55, 34.64, 34.76, 34.85, 34.88, 34.95, 35.00, 35.07, 35.10]
st['coast_km'] = np.clip((st.lon - np.interp(st.lat, coast_lat, coast_lon)) * 95, 0, None)
st.loc[st.lat < 31.1, 'coast_km'] = np.nan  # the coast line used covers 31.5-33.1N only; Arava, Eilat and Dead Sea stations get no value

# ---------- load ----------
data = {}
for y in YEARS:
    for f in glob.glob(f'national_{y}/st*.csv'):
        sid = int(os.path.basename(f)[2:-4])
        L = pd.read_csv(f)
        if L.empty:
            continue
        L['t'] = pd.to_datetime(L.datetime.str[:19]); L.loc[~L.valid, 'value'] = np.nan
        idx = pd.date_range(f'{y}-01-01', f'{y}-12-31 23:00', freq='h')
        data[(sid, y)] = L.pivot_table(index='t', columns='channel', values='value', aggfunc='first').reindex(idx)

# ---------- regional dust days (per year) ----------
dust = {}
for y in YEARS:
    daily = []
    for (sid, yy), p in data.items():
        if yy == y and 'PM10' in p:
            g = p['PM10'].groupby(p.index.date).agg(['mean', 'count'])
            daily.append(g['mean'].where(g['count'] >= 18).rename(sid))
    D = pd.concat(daily, axis=1)
    med = D.median(axis=1)
    flag = (med > 60)
    flag = flag | flag.shift(1, fill_value=False)
    dust[y] = flag
    print('%d: stations with PM10 %d; days with national median PM10 > 60: %d (incl. following day: %d)' % (y, D.shape[1], int((med > 60).sum()), int(flag.sum())))

# ---------- station-year metrics ----------
rows = []
for (sid, y), p in data.items():
    r = {'id': sid, 'year': y}
    if 'PM2.5' in p:
        s = p['PM2.5']; r['pm25_cov'] = s.notna().mean() * 100; r['pm25'] = s.mean()
        dm = s.groupby(s.index.date).agg(['mean', 'count']); dm = dm[dm['count'] >= 18]['mean']
        r['pm25_days_gt15_pct'] = 100 * (dm > 15).mean() if len(dm) else np.nan
        r['pm25_days_gt37'] = (dm > 37.5).sum()
        nd = dm[~dm.index.map(lambda d: bool(dust[y].get(d, False)))]
        r['pm25_nodust'] = nd.mean() if len(nd) >= 150 else np.nan
    if 'O3' in p:
        s = p['O3']; r['o3_cov'] = s.notna().mean() * 100
        ro = s.rolling(8, min_periods=6).mean(); day = ro.index.normalize()
        ok = ro.groupby(day).count() >= 18; m8 = ro.groupby(day).max().where(ok).dropna().round(6)  # rounding removes floating-point noise at exact ties (e.g. 51.0)
        r['o3_days51'] = len(m8) and (m8 >= 51).sum() * 365.0 / len(m8)  # scaled to a full year
        r['o3_jja'] = m8[m8.index.month.isin([6, 7, 8])].mean()
        r['o3_mean'] = s.mean()
    if 'PM10' in p:
        s10 = p['PM10']; r['pm10_cov'] = s10.notna().mean() * 100; r['pm10'] = s10.mean()
    if 'NO2' in p:
        r['no2'] = p['NO2'].mean() * 1.8804; r['no2_cov'] = p['NO2'].notna().mean() * 100
    rows.append(r)
SY = pd.DataFrame(rows)
# seasonal coverage QC: every season (DJF, MAM, JJA, SON) must have >= 50% valid hours for the metric's channel, otherwise the annual figure is seasonally biased
SEAS = {12: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2, 7: 2, 8: 2, 9: 3, 10: 3, 11: 3}
def seas_ok(p, ch):
    if ch not in p:
        return False
    v = p[ch].notna().groupby(p.index.month.map(SEAS)).mean()
    return bool((v >= 0.5).all()) and len(v) == 4
sq = {}
for (sid, y), p in data.items():
    sq[(sid, y)] = {ch: seas_ok(p, ch) for ch in ['PM2.5', 'O3', 'NO2', 'PM10']}
drop = {'PM2.5': ['pm25', 'pm25_nodust', 'pm25_days_gt15_pct', 'pm25_days_gt37'], 'O3': ['o3_days51', 'o3_jja', 'o3_mean'], 'NO2': ['no2'], 'PM10': ['pm10']}
dropped = []
for i, r in SY.iterrows():
    for ch, cols_ in drop.items():
        if not sq[(int(r.id), int(r.year))][ch] and not pd.isna(r[cols_[0]]):
            dropped.append((int(r.id), int(r.year), ch)); SY.loc[i, cols_] = np.nan
print('seasonal-coverage QC dropped station-year metrics:', len(dropped), dropped)
# QC: implausible PM2.5 annual means (< 5 or > 60 ug/m3, e.g. negative offsets) are set to missing
bad = (SY.pm25 < 5) | (SY.pm25 > 60)
print('QC: station-years with implausible PM2.5 set to NaN:', SY.loc[bad, ['id', 'year', 'pm25']].round(1).values.tolist())
for c in ['pm25', 'pm25_nodust', 'pm25_days_gt15_pct', 'pm25_days_gt37']:
    SY.loc[bad, c] = np.nan
SY.loc[SY.pm25_nodust < 5, 'pm25_nodust'] = np.nan
SY.loc[(SY.pm10 < 15) | (SY.pm10 > 150), 'pm10'] = np.nan  # PM10 below 15 ug/m3 is implausible for Israel (one station-year: Orot Rabin 2024, 13.6)
# ozone stability QC: a station whose yearly value of ozone days varies by more than 2.5x across its valid years is excluded from the ozone ranking (suspected calibration problems)
_o = SY[SY.o3_days51.notna()].groupby('id').o3_days51.agg(['min', 'max', 'count'])
UNSTABLE = _o[(_o['count'] >= 2) & (_o['max'] / _o['min'] > 2.5)].index.tolist()
SY.loc[SY.id.isin(UNSTABLE), ['o3_days51', 'o3_jja', 'o3_mean']] = np.nan
print('ozone stability QC: stations excluded from the ozone ranking (max/min > 2.5 across years):', UNSTABLE)
SY.to_csv('national_summary_station_year.csv', index=False, encoding='utf-8')


def avg(col, covcol, mincov=75, minyears=2):
    x = SY[SY[covcol] >= mincov]
    g = x.groupby('id')[col].agg(['mean', 'count'])
    return g['mean'].where(g['count'] >= minyears)


A = pd.DataFrame({'pm25': avg('pm25', 'pm25_cov'), 'pm25_nodust': avg('pm25_nodust', 'pm25_cov'), 'pm25_days15': avg('pm25_days_gt15_pct', 'pm25_cov'),
                  'o3_days51': avg('o3_days51', 'o3_cov'), 'o3_jja': avg('o3_jja', 'o3_cov'), 'no2': avg('no2', 'no2_cov'), 'pm10': avg('pm10', 'pm10_cov')})
A = A.join(st[['name', 'city', 'owner', 'h', 'coast_km', 'class', 'region', 'lat', 'lon']], how='left')
A.to_csv('national_summary_station.csv', encoding='utf-8')
A.index.name = 'id'
print('\nstations with a 3-year (>=2 valid years) PM2.5 mean:', A.pm25.notna().sum(), '| O3:', A.o3_days51.notna().sum(), '| NO2:', A.no2.notna().sum())
print('classes:', A['class'].value_counts().to_dict())
print('regions:', A['region'].value_counts().to_dict())

TIV = 137
md = []


def rank_line(col, sub, label, high_is_bad=True):
    x = sub[col].dropna()
    if TIV not in x.index:
        return None
    v = x.loc[TIV]
    return '%s: טבעון %.1f; חציון %.1f; טווח %.1f–%.1f; דירוג %d מ-%d (1 = הגבוה ביותר); %.0f%% מהתחנות נמוכות מטבעון' % (label, v, x.median(), x.min(), x.max(), int((x > v).sum()) + 1, len(x), 100 * (x < v).mean())


print('\n===== A. all stations =====')
for col, lab in [('pm25', 'PM2.5 ממוצע שנתי 2023–2025'), ('pm25_nodust', 'PM2.5 ללא ימי אבק אזוריים'), ('pm25_days15', 'אחוז ימים PM2.5>15'), ('o3_days51', 'אוזון ימים>=51 ppb בשנה'), ('o3_jja', 'אוזון MDA8 קיץ ppb'), ('no2', 'NO2')]:
    print(rank_line(col, A, lab))
bg = A[A['class'] == 'רקע עירוני/כללי']
print('\n===== B. background-only stations (no traffic/industry/quarry/power) =====')
for col, lab in [('pm25', 'PM2.5'), ('pm25_nodust', 'PM2.5 ללא אבק'), ('o3_days51', 'אוזון ימים'), ('no2', 'NO2')]:
    print(rank_line(col, bg, lab))
peer = bg[(bg.h >= 100) & (bg.h <= 450) & (bg.index != TIV) | (bg.index == TIV)]
print('\n===== C. peer hill/ridge background stations (100-450 m) n=%d =====' % len(peer))
for col, lab in [('pm25', 'PM2.5'), ('pm25_nodust', 'PM2.5 ללא אבק'), ('o3_days51', 'אוזון ימים'), ('no2', 'NO2')]:
    print(rank_line(col, peer, lab))
print(peer[['name', 'city', 'region', 'h', 'coast_km', 'pm25', 'o3_days51', 'no2']].round(1).sort_values('pm25').to_string())

# ---------- group tables ----------
def grp(df, by, cols):
    out = df.groupby(by).agg(n=('pm25', 'size'), **{c + '_med': (c, 'median') for c in cols}).round(1)
    return out


print('\n===== D. by region x class: median of 3-year station averages =====')
cols = ['pm25', 'pm25_nodust', 'o3_days51', 'no2']
G = A.groupby('region').agg(n=('name', 'size'), pm25=('pm25', 'median'), pm25_nodust=('pm25_nodust', 'median'), pm15=('pm25_days15', 'median'), o3=('o3_days51', 'median'), no2=('no2', 'median')).round(1)
print(G.to_string())
G2 = A.groupby('class').agg(n=('name', 'size'), pm25=('pm25', 'median'), pm25_nodust=('pm25_nodust', 'median'), pm15=('pm25_days15', 'median'), o3=('o3_days51', 'median'), no2=('no2', 'median')).round(1)
print(G2.to_string())
Gbg = bg.groupby('region').agg(n=('name', 'size'), pm25=('pm25', 'median'), pm25_nodust=('pm25_nodust', 'median'), pm15=('pm25_days15', 'median'), o3=('o3_days51', 'median'), no2=('no2', 'median')).round(1)
print('background only by region'); print(Gbg.to_string())

# ---------- regressions ----------
print('\n===== E. adjusted comparison (OLS, HC1): station average ~ class + elevation(100 m) + distance from coast (10 km) =====')
R = A.copy()
R['traffic'] = (R['class'] == 'תחבורה').astype(int); R['ind'] = (R['class'] == 'תעשייה/מחצבה/תחנת כוח').astype(int)
R['h100'] = R.h / 100; R['c10'] = R.coast_km / 10
R = R[(R.h > -100) & (R.coast_km < 80)]  # drop Dead Sea / Arava / Eilat / far Negev
for col, lab in [('pm25', 'PM2.5'), ('pm25_nodust', 'PM2.5 ללא אבק'), ('o3_days51', 'אוזון ימים>=51 ppb'), ('no2', 'NO2')]:
    x = R.dropna(subset=[col, 'h100', 'c10'])
    m = smf.ols(f'{col} ~ traffic + ind + h100 + c10', x).fit(cov_type='HC1')
    pr = m.predict(x.loc[[TIV]])[TIV] if TIV in x.index else np.nan
    res = x.loc[TIV, col] - pr if TIV in x.index else np.nan
    print('%-22s n=%d R2=%.2f | traffic %+.1f (p=%.3f) | industry %+.1f (p=%.3f) | per +100 m %+.2f (p=%.3f) | per +10 km from coast %+.2f (p=%.3f) | Tivon actual %.1f expected %.1f residual %+.1f (resid SD %.1f)' % (
        lab, len(x), m.rsquared, m.params['traffic'], m.pvalues['traffic'], m.params['ind'], m.pvalues['ind'], m.params['h100'], m.pvalues['h100'], m.params['c10'], m.pvalues['c10'], x.loc[TIV, col], pr, res, np.sqrt(m.scale)))

# ---------- by year for Tivon and peers ----------
print('\n===== F. Tivon rank among all stations by year =====')
for y in YEARS:
    x = SY[(SY.year == y) & (SY.pm25_cov >= 75)].set_index('id')
    xo = SY[(SY.year == y) & (SY.o3_cov >= 75)].set_index('id')
    print(y, 'PM2.5 Tivon %.1f rank %d of %d (median %.1f) | O3 days>=51ppb Tivon %.0f rank %d of %d (median %.0f)' % (
        x.loc[TIV, 'pm25'], int((x.pm25 > x.loc[TIV, 'pm25']).sum()) + 1, len(x), x.pm25.median(), xo.loc[TIV, 'o3_days51'], int((xo.o3_days51 > xo.loc[TIV, 'o3_days51']).sum()) + 1, len(xo), xo.o3_days51.median()))

# ---------- named city comparisons ----------
print('\n===== G. named places (background + all) =====')
def place(df, label, mask):
    d = df[mask]
    if len(d):
        print('%-30s n=%2d | PM2.5 %.1f (%.1f–%.1f) | days>15 %.0f%% | O3 days %.0f | NO2 %.1f' % (label, len(d), d.pm25.median(), d.pm25.min(), d.pm25.max(), d.pm25_days15.median(), d.o3_days51.median(), d.no2.median()))
place(A, 'טבעון', A.index == TIV)
place(A, 'תל אביב-יפו (כל)', A.city == 'תל אביב-יפו')
place(A[A['class'] != 'תחבורה'], 'תל אביב-יפו (לא תחבורה)', A.city == 'תל אביב-יפו')
place(A, 'חיפה (עיר, כל)', A.city == 'חיפה')
place(A[A['class'] != 'תחבורה'], 'חיפה (לא תחבורה)', A.city == 'חיפה')
place(A, 'ירושלים (כל)', A.city.astype(str).str.contains('ירושלים'))
place(A[A['class'] != 'תחבורה'], 'ירושלים (לא תחבורה)', A.city.astype(str).str.contains('ירושלים'))
place(A, 'באר שבע', A.city == 'באר שבע')
place(A, 'עפולה', A.city == 'עפולה')
place(A, 'עמק המעיינות (בית שאן)', A.city == 'עמק המעיינות')
place(A, 'כרמיאל', A.city == 'כרמיאל')
place(A, 'קריית אתא', A.city == 'קריית אתא')
place(A, 'אשדוד', A.city == 'אשדוד'); place(A, 'אשקלון', A.city == 'אשקלון'); place(A, 'חדרה', A.city == 'חדרה'); place(A, 'ערד', A.city == 'ערד'); place(A, 'מודיעין', A.city == 'מודיעין')
print('\n(no stations in the MANA list for Tiberias)')

# ---------- full station table ----------
print('\n===== H. all stations, 3-year averages =====')
print(A.assign(mark=np.where(A.index == TIV, '<<< טבעון', ''))[['name', 'city', 'region', 'class', 'h', 'pm25', 'pm25_nodust', 'pm25_days15', 'o3_days51', 'no2', 'mark']].round(1).sort_values('pm25', ascending=False).to_string())
