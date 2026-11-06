#!/usr/bin/env python3
"""नया मॉक टेस्ट सेट वेबसाइट में जोड़ता है।

उपयोग:
  python3 tools/add_set.py 07 sets/set07.js "मिश्रित स्तर" "07 अक्टूबर 2026" [--server | --sheet-key] [--series vyapam]

--series vyapam : व्यापम समूह-2 (उप-समूह 02) सीरीज़ का सेट (7 भाग: 20+20+20+10+10+10+10)। NN = सीरीज़ का
           क्रमांक (01, 02 …); वेबसाइट में यह सेट 1000+NN क्रमांक और बैज VNN से जुड़ता है (keys/set10NN.key)।

--server : सर्वर-जाँच वाला सेट (apps-script/grader.gs)। सही उत्तर/व्याख्या वेबसाइट में नहीं जाते;
           वे GRADER_SECRET से कूटबद्ध होकर keys/setNN.key में जाते हैं, और प्रिंट-पेपर व .md सूची
           (जिनमें उत्तर-कुंजी है) सार्वजनिक papers/ lists/ के बजाय private/ (gitignored) में बनते हैं।

- sets/setNN.js : node module (module.exports = [ {title, marks, qs:[{q,o,a,d,e}]} × 6 ])
- index.html के DATA में सेट जोड़ता है, डिफ़ॉल्ट चयन नए सेट पर करता है,
  papers/mock-test-NN.html और lists/mock-test-NN.md बनाता है।
- उत्तरों (A/B/C/D) को अपने-आप संतुलित करता है (संख्यात्मक विकल्पों का क्रम नहीं बदलता)।
"""
import json, sys, subprocess, html, re, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'tools')); import series as SER
SNAME, ARGV = SER.arg_series(sys.argv[1:]); SR = SER.get(SNAME); VY = SNAME != 'cspdcl'
SHEET_KEY = '--sheet-key' in ARGV
SERVER = '--server' in ARGV or SHEET_KEY
NN, src, level, date = [x for x in ARGV if x not in ('--server','--sheet-key')][:4]
no = SR['offset'] + int(NN)
FNN = f"{no:02d}"                      # फ़ाइल-नामों का क्रमांक (keys/setFNN.key)
BADGE = SR['badge'] + NN
L = "ABCD"; kh = "ABCDEFG"; e = html.escape
DI = {'सरल': 0, 'मध्यम': 1, 'कठिन': 2}
SHORT = SR['short']
MARKS = SR['marks']

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
assert all(st['no'] != no for st in A['cg']['sets']), f'सेट {BADGE} पहले से मौजूद है'
same = [st['no'] for st in A['cg']['sets'] if SER.series_of(st['no']) == SNAME]
prev = max(same) if same else None
cq = []
for i, s in enumerate(raw):
    for x in s['qs']:
        if SERVER:      # उत्तर/व्याख्या पेज में नहीं; विषयवार अभ्यास-पूल में भी नहीं
            cq.append([DI[x['d']], x['q'], x['o'], -1, ''])
        else:
            A['q'].append([i+1, DI[x['d']], x['q'], x['o'], x['a'], x['e']])
            cq.append([DI[x['d']], x['q'], x['o'], x['a'], x['e']])
meta = {'no': no, 'label': (f'व्यापम मॉक टेस्ट {BADGE} — पूर्ण प्रश्नपत्र ({level})' if VY else f'मॉक टेस्ट {NN} — पूर्ण प्रश्नपत्र ({level})'), 'badge': BADGE, 'q': cq}
if VY:
    meta.update({'series': SNAME, 'exam': SR['exam'], 'sections': [[nm, ln] for nm, ln in zip(SHORT, MARKS)]})
    if not SERVER: meta.update({'neg': SR['neg'], 'minutes': SR['minutes']})
SECS = meta.get('sections') or A['cg']['sections']
if SERVER:
    meta.update({'server': True, 'neg': SR['neg'], 'minutes': SR['minutes']})
    key = {'no': no, 'secs': [[nm, ln] for nm, ln in SECS], 'neg': SR['neg'], 'minutes': SR['minutes'],
           'a': [x['a'] for s in raw for x in s['qs']], 'e': [x['e'] for s in raw for x in s['qs']]}
    assert sum(ln for _, ln in key['secs']) == len(key['a']) == 100
    if SHEET_KEY:
        # ChatGPT automation mode: keep answer-bearing material only in gitignored private/.
        # The automation writes this key into the hidden Google Sheet tab उत्तर-कुंजी (गुप्त).
        (ROOT/'private').mkdir(exist_ok=True)
        (ROOT/f'private/key-set{FNN}.json').write_text(json.dumps(key, ensure_ascii=False))
    else:
        from keycrypt import encrypt, secret
        (ROOT/'keys').mkdir(exist_ok=True)
        (ROOT/f'keys/set{FNN}.key').write_text(encrypt(key, secret()) + '\n')
A['cg']['sets'].append(meta)
idx = save(idx, A, span)
if not VY:   # डिफ़ॉल्ट चयन और गिनती केवल CSPDCL सीरीज़ की
    idx = idx.replace(f"'cg:{prev}'", f"'cg:{no}'")
    n_sets = sum(1 for st in A['cg']['sets'] if SER.series_of(st['no']) == 'cspdcl')
    idx = re.sub(r'\d+ पूर्ण मॉक टेस्ट \(\d+ प्रश्न\)', f'{n_sets} पूर्ण मॉक टेस्ट ({100*n_sets} प्रश्न)', idx)
(ROOT/'index.html').write_text(idx)
if VY: prev = prev or no

# ---- printable paper (template = previous paper)
import glob
tpl_path = sorted(glob.glob(str(ROOT/'papers/mock-test-*.html')))[-1]
tpl = int(re.search(r'mock-test-(\d+)\.html$', tpl_path).group(1))
p = Path(tpl_path).read_text()
OUT = ROOT/'private' if SERVER else ROOT
(OUT/'papers').mkdir(parents=True, exist_ok=True); (OUT/'lists').mkdir(parents=True, exist_ok=True)
secs = ""; key = []; expl = ""
md = [f"# {SR['title']} — मॉक टेस्ट {BADGE} ({level}) | {date}", "", "| क्रमांक | प्रश्न | सही उत्तर |", "|---|---|---|"]
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
p = p.replace(f'मॉक टेस्ट {tpl:02d}', f'मॉक टेस्ट {BADGE}')
if VY: p = p.replace('CSPDCL DEO / स्टेनोग्राफर', SR['title']).replace('CSPDCL', 'व्यापम')
else: p = re.sub(r'CSPDCL मॉक टेस्ट 01–\d\d', f'CSPDCL मॉक टेस्ट 01–{prev:02d}', p)
p = re.sub(r'100 नए बहुविकल्पीय प्रश्न( \| [^<|]*)?(?=<)', f'100 नए बहुविकल्पीय प्रश्न | {level}', p, count=1)
sys.path.insert(0, str(ROOT/'tools')); from fracfmt import frac_html
(OUT/f'papers/{"vyapam" if VY else "mock"}-test-{NN}.html').write_text(frac_html(p))
md += ["", f"उत्तर वितरण: A {dist['A']} | B {dist['B']} | C {dist['C']} | D {dist['D']}"]
from fracfmt import frac_text
(OUT/f'lists/{"vyapam" if VY else "mock"}-test-{NN}.md').write_text(frac_text("\n".join(md) + "\n"))
dif = {}
for s in raw:
    for q in s['qs']: dif[q['d']] = dif.get(q['d'], 0) + 1
print('जोड़ा:', BADGE, f'(क्रमांक {no})', '(सर्वर-जाँच)' if SERVER else '', 'उत्तर-वितरण', dist, 'कठिनाई', dif, 'कुल प्रश्न', len(A['q']))
