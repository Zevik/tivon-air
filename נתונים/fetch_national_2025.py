"""Fetch 2025 hourly PM2.5, PM10, O3, NO2 for all active non-mobile MANA stations that list PM2.5 or O3 (guest API, token refreshed on 401).
Output: national_2025/st<ID>.csv (datetime,channel,value,valid,units) and national_2025/_stations.csv."""
import csv, datetime as dt, json, re, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.stdout.reconfigure(encoding='utf-8')
UA = {'User-Agent': 'Mozilla/5.0'}
tok = {'v': None}
def refresh():
    html = urllib.request.urlopen(urllib.request.Request('https://air.sviva.gov.il/', headers=UA), timeout=60).read().decode('utf-8', 'ignore')
    tok['v'] = 'ApiToken ' + re.search(r"ApiToken ([0-9a-f-]+)", html).group(1)
refresh()
d = json.load(open('../מקורות/mana_stations_list_2026-10-17.json', encoding='utf-8'))
sel = []
for s in d:
    mon = {m['name'] for m in s.get('monitors') or []}
    if str(s.get('active')) == 'True' and str(s.get('mobile')) != 'True' and ('PM2.5' in mon or 'O3' in mon):
        sel.append(s)
with open('national_2025/_stations.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['id', 'name', 'city', 'owner', 'height', 'lat', 'lon', 'target'])
    for s in sel:
        l = s.get('location') or {}
        w.writerow([s['stationId'], s['name'], s['city'], s['owner'], s['height'], l.get('latitude'), l.get('longitude'), s['StationTarget']])
print(len(sel), 'stations', flush=True)
KEEP = {'PM2.5', 'PM10', 'O3', 'NO2'}
def get(url):
    for t in range(6):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={**UA, 'Authorization': tok['v']}), timeout=120))
        except urllib.error.HTTPError as e:
            if e.code == 401: refresh()
            time.sleep(2 * (t + 1))
        except Exception:
            time.sleep(3 * (t + 1))
    return None
def one(s):
    import os
    sid = s['stationId']; rows = []; fail = 0
    if os.path.exists(f'national_2025/st{sid}.csv') and os.path.getsize(f'national_2025/st{sid}.csv') > 200: return
    for m in range(1, 13):
        a = dt.date(2025, m, 1); b = dt.date(2025 + (m == 12), m % 12 + 1, 1)
        j = get(f'https://air-papi.sviva.gov.il/v1/envista/stations/{sid}/data?timebase=60&from={a:%Y/%m/%d}&to={b:%Y/%m/%d}')
        if j is None: fail += 1; continue
        for rec in j['data']:
            for ch in rec['channels']:
                if ch['name'] in KEEP: rows.append((rec['datetime'], ch['name'], ch['value'], ch['valid'], ch['units']))
    with open(f'national_2025/st{sid}.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['datetime', 'channel', 'value', 'valid', 'units']); w.writerows(rows)
    print(sid, s['city'], len(rows), 'failed months', fail, flush=True)
with ThreadPoolExecutor(24) as ex: list(ex.map(one, sel))
print('DONE', flush=True)
