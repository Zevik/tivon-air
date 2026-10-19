"""Bearings and distances from Tivon (137) to all stations in the saved MANA station list (../מקורות/mana_stations_list_2026-10-17.json)."""
import sys, json
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
d = json.load(open('../מקורות/mana_stations_list_2026-10-17.json', encoding='utf-8'))
d = d if isinstance(d, list) else d.get('data', d)
S = {s['stationId']: s for s in d}
T = S[137]['location']
la0, lo0 = T['latitude'], T['longitude']
def brg(la, lo):
    p1, p2, dl = np.radians(la0), np.radians(la), np.radians(lo - lo0)
    y = np.sin(dl) * np.cos(p2); x = np.cos(p1) * np.sin(p2) - np.sin(p1) * np.cos(p2) * np.cos(dl)
    return (np.degrees(np.arctan2(y, x)) + 360) % 360
def km(la, lo): return np.hypot((la - la0) * 111.2, (lo - lo0) * 111.2 * np.cos(np.radians(la0)))
rows = []
for s in d:
    l = s.get('location') or {}
    if l.get('latitude') and s.get('active', True) and 32.6 < l['latitude'] < 32.95 and 34.95 < l['longitude'] < 35.2 and s['stationId'] != 137:
        rows.append((brg(l['latitude'], l['longitude']), km(l['latitude'], l['longitude']), s['stationId'], s['name'], s.get('owner'), s.get('height'), l['latitude'], l['longitude']))
print('Tivon 137: %.5f, %.5f' % (la0, lo0))
print('%-6s %-6s %-5s %-28s %-22s %-5s %s' % ('bear', 'km', 'id', 'name', 'owner', 'h', 'lat,lon'))
for r in sorted(rows):
    print('%5.1f %5.1f %5d %-28s %-22s %-5s %.4f,%.4f' % r)
