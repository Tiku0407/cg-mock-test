#!/usr/bin/env python3
"""प्रगतिशील कठिनाई: सेट-क्रमांक के अनुसार लक्ष्य स्तर और भागवार सरल/मध्यम/कठिन संख्या।

उपयोग:
  python3 tools/level.py 11                  # सेट 11 का लक्ष्य दिखाएँ
  python3 tools/level.py 11 private/set11.js # बने हुए सेट को लक्ष्य से मिलाएँ (अंतर हो तो exit 1)
"""
import json, subprocess, sys
from pathlib import Path

# (पहला सेट, स्तर, सरल, मध्यम, कठिन) — हर 3 सेट पर एक सीढ़ी ऊपर
LADDER = [
    (1, 0, 50, 0, 50),     # सेट 01–10: पुराना "मिश्रित" स्तर
    (11, 1, 40, 20, 40),
    (14, 2, 30, 30, 40),
    (17, 3, 20, 35, 45),
    (20, 4, 15, 35, 50),
    (23, 5, 10, 30, 60),   # अंतिम (परीक्षा से कठिन) स्तर — आगे यही रहेगा
]
SECS = [('छत्तीसगढ़ GK + समसामयिकी', 25), ('कम्प्यूटर', 15), ('मानसिक योग्यता', 15),
        ('सामान्य गणित', 15), ('सामान्य हिन्दी', 20), ('सामान्य अंग्रेजी', 10)]
D = ['सरल', 'मध्यम', 'कठिन']


def target(no):
    row = [r for r in LADDER if no >= r[0]][-1]
    lvl, tot = row[1], row[2:]
    # भागवार बाँटें (largest remainder), ताकि हर भाग और कुल दोनों मेल खाएँ
    out = [[0, 0, 0] for _ in SECS]
    for d in range(3):
        want = tot[d]
        raw = [n * want / 100 for _, n in SECS]
        base = [int(x) for x in raw]
        for i in sorted(range(len(SECS)), key=lambda i: raw[i] - base[i], reverse=True)[:want - sum(base)]:
            base[i] += 1
        for i in range(len(SECS)): out[i][d] = base[i]
    for i, (_, n) in enumerate(SECS):          # गोलाई से भाग का योग बिगड़े तो मध्यम से संतुलित करें
        out[i][1] += n - sum(out[i])
    return lvl, tot, out


def label(no):
    lvl = target(no)[0]
    return 'मिश्रित स्तर' if lvl == 0 else f'प्रगतिशील स्तर {lvl}'


if __name__ == '__main__':
    no = int(sys.argv[1]); lvl, tot, out = target(no)
    print(f'सेट {no:02d}: {label(no)} — कुल सरल {tot[0]} · मध्यम {tot[1]} · कठिन {tot[2]}')
    for (nm, n), o in zip(SECS, out):
        print(f'  {nm} ({n}): सरल {o[0]}, मध्यम {o[1]}, कठिन {o[2]}')
    if len(sys.argv) > 2:
        raw = json.loads(subprocess.check_output(['node', '-e',
            f"const s=require({json.dumps(str(Path(sys.argv[2]).resolve()))});console.log(JSON.stringify(s.map(x=>x.qs.map(q=>q.d))))"]))
        bad = 0
        for (nm, n), o, ds in zip(SECS, out, raw):
            got = [ds.count(d) for d in D]
            if got != o: bad += 1; print(f'  ✗ {nm}: लक्ष्य {o}, बना {got}')
        print('✓ कठिनाई लक्ष्य से मेल खाती है' if not bad else '✗ कठिनाई-स्तर बदलें')
        sys.exit(1 if bad else 0)
