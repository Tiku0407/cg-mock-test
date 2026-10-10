#!/usr/bin/env python3
"""नया मॉक टेस्ट सेट वेबसाइट में जोड़ता है।

उपयोग:
  python3 tools/add_set.py 07 sets/set07.js "मिश्रित स्तर" "07 अक्टूबर 2026"

- sets/setNN.js : node module (module.exports = [ {title, marks, qs:[{q,o,a,d,e}]} × 6 ])
- index.html के DATA में सेट जोड़ता है, डिफ़ॉल्ट चयन नए सेट पर करता है,
  papers/mock-test-NN.html और lists/mock-test-NN.md बनाता है।
- उत्तरों (A/B/C/D) को अपने-आप संतुलित करता है (संख्यात्मक विकल्पों का क्रम नहीं बदलता)।
"""
import json, sys, subprocess, html, re, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NN, src, level, date = sys.argv[1:5]
no = int(NN)
L = "ABCD"; kh = "ABCDEF"; e = html.escape
DI = {'सरल': 0, 'मध्यम': 1, 'कठिन': 2}
SHORT = ['छत्तीसगढ़ GK', 'कम्प्यूटर', 'मानसिक योग्यता', 'सामान्य गणित', 'सामान्य हिन्दी', 'सामान्य अंग्रेजी']
MARKS = [25, 15, 15, 15, 20, 10]

raw = json.loads(subprocess.check_output(['node', '-e',
    f"const s=require({json.dumps(str(Path(src).resolve()))});console.log(JSON.stringify(s))"]))
assert [len(s['qs']) for s in raw] == MARKS, [len(s['qs']) for s in raw]
for s in raw:
    for q in s['qs']:
        assert len(q['o']) == 4 and 0 <= q['a'] < 4 and q['d'] in DI, q['q']
        assert len(set(q['o'])) == 4, 'दोहराए विकल्प: ' + q['q']

# ---- balance answer positions
def is_num(q): return all(re.search(r'\d', o) for o in q['o'])
best = None
for seed in range(400):
    rnd = random.Random(seed); cnt = [0]*4; plan = []
    for s in raw:
        for q in s['qs']:
            t = q['a'] if is_num(q) else rnd.randrange(4)
            plan.append(t); cnt[t] += 1
    spread = max(cnt) - min(cnt)
    if best is None or spread < best[0]: best = (spread, plan)
it = iter(best[1])
for s in raw:
    for q in s['qs']:
        t = next(it)
        if t != q['a']:
            q['o'][t], q['o'][q['a']] = q['o'][q['a']], q['o'][t]; q['a'] = t

# ---- live page
idx = (ROOT/'index.html').read_text()
sys.path.insert(0, str(ROOT/'tools')); from datacodec import load, save
A, span = load(idx)
assert all(st['no'] != no for st in A['cg']['sets']), f'सेट {NN} पहले से मौजूद है'
prev = max(st['no'] for st in A['cg']['sets'])
cq = []
for i, s in enumerate(raw):
    for x in s['qs']:
        A['q'].append([i+1, DI[x['d']], x['q'], x['o'], x['a'], x['e']])
        cq.append([DI[x['d']], x['q'], x['o'], x['a'], x['e']])
A['cg']['sets'].append({'no': no, 'label': f'मॉक टेस्ट {NN} — पूर्ण प्रश्नपत्र ({level})', 'badge': NN, 'q': cq})
idx = save(idx, A, span)
idx = idx.replace(f"'cg:{prev}'", f"'cg:{no}'")
n_sets = len(A['cg']['sets'])
idx = re.sub(r'\d+ पूर्ण मॉक टेस्ट \(\d+ प्रश्न\)', f'{n_sets} पूर्ण मॉक टेस्ट ({100*n_sets} प्रश्न)', idx)
(ROOT/'index.html').write_text(idx)

# ---- printable paper (template = previous paper)
p = (ROOT/f'papers/mock-test-{prev:02d}.html').read_text()
secs = ""; key = []; expl = ""
md = [f"# CSPDCL DEO / स्टेनोग्राफर — मॉक टेस्ट {NN} ({level}) | {date}", "", "| क्रमांक | प्रश्न | सही उत्तर |", "|---|---|---|"]
for i, s in enumerate(raw):
    t = s['title'].split(':', 1)[1].strip()
    secs += f'<h2 class="sec"><span>खंड {kh[i]}</span>{e(t)} <small>({MARKS[i]} अंक)</small></h2>\n'
    expl += f'<h3>खंड {kh[i]} — {e(t)}</h3>\n'
    for q in s['qs']:
        n = len(key) + 1; key.append((n, L[q['a']]))
        cls = "two" if any(len(o) > 26 for o in q['o']) else "four"
        secs += f'<div class="q"><p><b>{n}.</b> {e(q["q"])} <span class="d">[{q["d"]}]</span></p><ol class="{cls}">' + \
                "".join(f'<li><b>({L[k]})</b> {e(o)}</li>' for k, o in enumerate(q['o'])) + '</ol></div>\n'
        expl += f'<p><b>{n}. ({L[q["a"]]}) {e(q["o"][q["a"]])}</b> — {e(q["e"])}</p>\n'
        md.append(f'| {n} | {q["q"].replace("|", "/")} | ({L[q["a"]]}) {q["o"][q["a"]].replace("|", "/")} |')
x = p.find('<h2 class="sec"><span>खंड A'); y = p.find('<section class="page">'); p = p[:x] + secs + p[y:]
x = p.find('<div class="grid">') + 18; y = p.find('</div>\n<p class="d" style="text-align:center">')
p = p[:x] + "".join(f'<div><b>{u}</b> – {v}</div>' for u, v in key) + p[y:]
x = p.find('<div class="ex">') + 16; y = p.find('</div>\n<p class="d">नोट'); p = p[:x] + expl + p[y:]
dist = {c: sum(1 for _, v in key if v == c) for c in L}
p = re.sub(r'उत्तर वितरण: A – \d+ \| B – \d+ \| C – \d+ \| D – \d+',
           f'उत्तर वितरण: A – {dist["A"]} | B – {dist["B"]} | C – {dist["C"]} | D – {dist["D"]}', p)
p = p.replace(f'मॉक टेस्ट {prev:02d}', f'मॉक टेस्ट {NN}')
p = re.sub(r'CSPDCL मॉक टेस्ट 01–\d\d', f'CSPDCL मॉक टेस्ट 01–{prev:02d}', p)
p = re.sub(r'100 नए बहुविकल्पीय प्रश्न( \| [^<|]*)?(?=<)', f'100 नए बहुविकल्पीय प्रश्न | {level}', p, count=1)
sys.path.insert(0, str(ROOT/'tools')); from fracfmt import frac_html
(ROOT/f'papers/mock-test-{NN}.html').write_text(frac_html(p))
md += ["", f"उत्तर वितरण: A {dist['A']} | B {dist['B']} | C {dist['C']} | D {dist['D']}"]
from fracfmt import frac_text
(ROOT/f'lists/mock-test-{NN}.md').write_text(frac_text("\n".join(md) + "\n"))
dif = {}
for s in raw:
    for q in s['qs']: dif[q['d']] = dif.get(q['d'], 0) + 1
print('जोड़ा:', NN, 'उत्तर-वितरण', dist, 'कठिनाई', dif, 'कुल प्रश्न', len(A['q']))
