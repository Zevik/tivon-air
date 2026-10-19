"""Download hourly (timebase=60) data for one MANA station via the public site's guest API.
Usage: python -I fetch_station.py <stationId> <out.csv> [from_year] [to_year] [comma-separated years to keep]
The guest ApiToken is read from the public home page (it rotates), refreshed on HTTP 401."""
import csv
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.request

sid, out = sys.argv[1], sys.argv[2]
y0 = int(sys.argv[3]) if len(sys.argv) > 3 else 2021
y1 = int(sys.argv[4]) if len(sys.argv) > 4 else 2026
ONLY = set(int(x) for x in sys.argv[5].split(',')) if len(sys.argv) > 5 else None
UA = {'User-Agent': 'Mozilla/5.0'}
tok = {'v': None}


def refresh():
    html = urllib.request.urlopen(urllib.request.Request('https://air.sviva.gov.il/', headers=UA), timeout=60).read().decode('utf-8', 'ignore')
    tok['v'] = 'ApiToken ' + re.search(r"ApiToken ([0-9a-f-]+)", html).group(1)


refresh()
B = f'https://air-papi.sviva.gov.il/v1/envista/stations/{sid}/data?timebase=60&from=%s&to=%s'
rows = []
d = dt.date(y0, 1, 1)
end = min(dt.date(2026, 10, 18), dt.date(y1 + 1, 1, 1))
while d < end:
    n = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    url = B % (d.strftime('%Y/%m/%d'), n.strftime('%Y/%m/%d'))
    j = None
    if ONLY is not None and d.year not in ONLY:
        d = n
        continue
    for t in range(6):
        try:
            j = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={**UA, 'Authorization': tok['v']}), timeout=120))
            break
        except urllib.error.HTTPError as e:
            if e.code == 401:
                refresh()
            time.sleep(2 * (t + 1))
        except Exception:
            time.sleep(3 * (t + 1))
    if j is None:
        print('FAILED', d, flush=True)
    else:
        for rec in j['data']:
            for ch in rec['channels']:
                rows.append((rec['datetime'], ch['name'], ch['value'], ch['status'], ch['valid'], ch['units']))
        print(sid, d, len(j['data']), flush=True)
    d = n
with open(out, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['datetime', 'channel', 'value', 'status', 'valid', 'units'])
    w.writerows(rows)
