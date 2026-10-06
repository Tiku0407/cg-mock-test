#!/usr/bin/env python3
"""नए सेट के प्रश्नों का पुराने सभी सेटों से दोहराव-मिलान।

उपयोग:  python3 tools/dupcheck.py sets/set07.js

तीन जाँच:
 1. उद्धृत शब्द (‘…’) और सही उत्तर पुराने प्रश्नों में मिलते हैं या नहीं
 2. दैनिक सेट 06 और CSPDCL सेटों से प्रश्न-पाठ की समानता (साथ में सही उत्तर भी वही हो)
 3. दैनिक सेट 01–05 (PDF पाठ) से प्रश्न-पाठ की समानता
फ़्लैग हुए हर प्रश्न को स्वयं पढ़कर तय करें; सामान्य उत्तर (जैसे 'बस्तर', '25%') झूठे फ़्लैग दे सकते हैं।
असली दोहराव = वही तथ्य/वही अवधारणा, चाहे शब्द या विकल्प बदले हों।
"""
import re, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
C = ROOT/'tools'/'corpus'

def norm(s): return re.sub(r'[\s​‌‍\'"‘’“”?।,.:;()\-–—]', '', s)
def G(s, n=3):
    s = norm(s); return {s[i:i+n] for i in range(max(1, len(s)-n+1))}

pdf = (C/'daily_sets_01_05.txt').read_text()
d06 = json.loads((C/'daily_set_06.json').read_text())
idx = (ROOT/'index.html').read_text(); a = idx.find('const DATA = ')+13; b = idx.find(';\n', a)
A = json.loads(idx[a:b])
old = [(f"CSPDCL-{s['badge']}#{i}", q[1], q[2][q[3]]) for s in A['cg']['sets'] for i, q in enumerate(s['q'], 1)]
old += [(f"दैनिक-06#{i}", q['q'], q['o'][q['a']]) for i, q in enumerate(d06, 1)]
P = []
for bl in re.split(r'(?:\n|\s)(?=\d{1,3}\.\s)', pdf):
    m = re.match(r'(\d{1,3})\.\s(.*)', bl, re.S)
    if m:
        q = m.group(2).split('[')[0]
        if 6 < len(q) < 300: P.append((q, m.group(2)[:400]))
texts = {'दैनिक-PDF': norm(pdf)}
for src, q, ans in old: texts.setdefault(src.split('#')[0], ''); texts[src.split('#')[0]] += norm(q + ' ' + ans) + '|'

new = json.loads(subprocess.check_output(['node', '-e',
    f"const s=require({json.dumps(str(Path(sys.argv[1]).resolve()))});console.log(JSON.stringify(s.flatMap(x=>x.qs.map(q=>[q.q,q.o[q.a]]))))"]))
flags = 0
for n, (q, ans) in enumerate(new, 1):
    out = []
    keys = [k for k in re.findall(r"[‘'“\"]([^’'”\"]{2,40})[’'”\"]", q) if len(norm(k)) >= 3]
    for k in keys + ([ans] if len(norm(ans)) >= 4 else []):
        hit = [nm for nm, t in texts.items() if norm(k) in t]
        if hit: out.append(f"शब्द '{k}' → {', '.join(hit)}")
    gq = G(q)
    for src, oq, oa in old:
        go = G(oq); s = len(gq & go) / max(1, min(len(gq), len(go)))
        same = norm(oa) == norm(ans)
        if (s > 0.8 and (same or len(norm(q)) > 30)) or (same and s > 0.45):
            out.append(f"समान ({s:.2f}) {src}: {oq[:70]} → {oa}")
    for oq, body in P:
        go = G(oq)
        if not go: continue
        s = len(gq & go) / min(len(gq), len(go))
        if s > 0.8 or (s > 0.55 and len(norm(ans)) >= 2 and norm(ans) in norm(body)):
            out.append(f"समान ({s:.2f}) दैनिक-PDF: {re.sub(chr(10), ' ', body)[:90]}")
    if out:
        flags += 1
        print(f"\nप्र.{n}: {q[:80]} → {ans}")
        for o in out[:6]: print('   ', o)
print(f"\nफ़्लैग हुए प्रश्न: {flags} (हर एक को स्वयं जाँचें)")
