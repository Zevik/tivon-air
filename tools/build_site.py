"""בונה את אתר העמוד האחד לפריסה ב-Vercel (תיקיית site/).
index.html = הגרפים; report.html, appendix.html, main-report.html = המסמכים מומרים מ-Markdown.
הרצה: python -I tools/build_site.py (מתיקיית הפרויקט)."""
import html as H
import os
import re
import sys
import urllib.parse

import markdown

sys.stdout.reconfigure(encoding='utf-8')
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = os.path.join(root, 'site')
os.makedirs(out, exist_ok=True)
GH = 'https://github.com/Zevik/tivon-air'

PAGES = {  # שם קובץ md -> (קובץ html, כותרת)
    'השוואה ארצית - קריית טבעון מול שאר הארץ.md': ('report.html', 'דוח ההשוואה הארצית'),
    'נספח - מקורות נתונים וחישובים (השוואה ארצית).md': ('appendix.html', 'נספח המקורות והחישובים'),
    'איכות האוויר בקריית טבעון — מחקר עומק.md': ('main-report.html', 'איכות האוויר בקריית טבעון: מחקר עומק'),
    'סיכום בשפה פשוטה - השוואה ארצית.md': ('summary.html', 'סיכום בשפה פשוטה'),
    'דוח ביקורת פנימית - השוואה ארצית.md': ('audit.html', 'דוח ביקורת פנימית'),
}
EVID = 'חבילת ראיות - השוואה ארצית'


def fix_href(h):
    if re.match(r'^(https?:|mailto:|#)', h):
        return h
    path, _, frag = h.partition('#')
    d = urllib.parse.unquote(path)
    if d in PAGES:
        return PAGES[d][0] + ('#' + frag if frag else '')
    if d == 'השוואה ארצית - גרפים.html':
        return './'
    return GH + '/blob/main/' + urllib.parse.quote(d)


CSS = """:root{--bg:#fff;--ink:#1c2430;--muted:#5d6b7b;--line:#dfe5ec;--accent:#1a5fb4;--card:#f6f8fa}
@media (prefers-color-scheme:dark){:root{--bg:#12161c;--ink:#e6ebf1;--muted:#9aa7b6;--line:#2a323d;--accent:#7db3f5;--card:#1a2029}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.75 system-ui,"Segoe UI",Arial,sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:20px 16px 60px}
a{color:var(--accent)}nav{font-size:.9rem;margin-bottom:18px}
h1,h2,h3{line-height:1.35}
.tbl{overflow-x:auto;margin:12px 0}table{border-collapse:collapse;font-size:.9rem}
th,td{border:1px solid var(--line);padding:5px 9px;text-align:start;vertical-align:top}th{background:var(--card)}
code{background:var(--card);padding:1px 5px;border-radius:4px;direction:ltr;unicode-bidi:embed}
pre{background:var(--card);padding:10px;overflow-x:auto;direction:ltr}img{max-width:100%}
blockquote{border-inline-start:3px solid var(--line);margin:0;padding-inline-start:14px;color:var(--muted)}"""

for name, (fn, title) in PAGES.items():
    src = os.path.join(root, name)
    body = markdown.markdown(open(src, encoding='utf-8').read(), extensions=['tables', 'fenced_code', 'sane_lists'])
    body = re.sub(r'href="([^"]+)"', lambda m: 'href="%s"' % fix_href(H.unescape(m.group(1))), body)
    body = body.replace('<table>', '<div class="tbl"><table>').replace('</table>', '</table></div>')
    page = f"""<!doctype html>
<html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{H.escape(title)}</title><style>{CSS}</style></head>
<body><div class="wrap"><nav><a href="./">← טבעון מול שאר הארץ</a></nav>
{body}</div></body></html>"""
    open(os.path.join(out, fn), 'w', encoding='utf-8').write(page)
    print(fn, len(page) // 1024, 'KB')

# עמוד הגרפים: החלפת קישורי הפוטר
idx = open(os.path.join(root, 'השוואה ארצית - גרפים.html'), encoding='utf-8').read()
n0 = idx.count('.md"')
idx = idx.replace('href="השוואה%20ארצית%20-%20קריית%20טבעון%20מול%20שאר%20הארץ.md"', 'href="report"')
idx = idx.replace('href="נספח%20-%20מקורות%20נתונים%20וחישובים%20%28השוואה%20ארצית%29.md"', 'href="appendix"')
tree = GH + '/tree/main/' + urllib.parse.quote(EVID)
idx = idx.replace('ותיקיית "חבילת ראיות - השוואה ארצית"', f'ותיקיית <a href="{tree}">"חבילת ראיות - השוואה ארצית"</a>')
assert '.md"' not in idx and 'href="report"' in idx and 'href="appendix"' in idx and tree in idx, (n0)
open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(idx)
print('index.html OK')
