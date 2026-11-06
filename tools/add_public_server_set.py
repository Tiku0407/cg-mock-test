#!/usr/bin/env python3
"""Publish newest public server set (questions/options only) into encrypted DATA in index.html.
Answers/explanations must already exist in Google Sheet hidden key tab.
Safe for public GitHub: input files contain no answer key.
"""
import json, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'tools'))
from datacodec import load, save
from series import get, series_of

files=sorted((ROOT/'sets').glob('public-set*.js'))
if not files:
    raise SystemExit('No sets/public-setNN.js file found')
src=files[-1]
m=re.search(r'public-set(\d+)\.js$',src.name)
no=int(m.group(1))
SR=get('cspdcl')
raw=json.loads(subprocess.check_output(['node','-e',f"const s=require({json.dumps(str(src.resolve()))});console.log(JSON.stringify(s))"]))
if [len(s['qs']) for s in raw] != SR['marks']:
    raise SystemExit('Wrong section counts')
DI={'सरल':0,'मध्यम':1,'कठिन':2}
for sec in raw:
    for q in sec['qs']:
        if len(q.get('o',[]))!=4 or len(set(q['o']))!=4 or q.get('d') not in DI:
            raise SystemExit('Invalid question: '+str(q.get('q','')))

idx=(ROOT/'index.html').read_text(encoding='utf-8')
A,span=load(idx)
if any(int(st['no'])==no for st in A['cg']['sets']):
    print(f'Set {no} already published')
    raise SystemExit(0)

prev=max(st['no'] for st in A['cg']['sets'] if series_of(st['no'])=='cspdcl')
cq=[]
for sec in raw:
    for q in sec['qs']:
        cq.append([DI[q['d']],q['q'],q['o'],-1,''])
meta={'no':no,'label':f'मॉक टेस्ट {no:02d} — पूर्ण प्रश्नपत्र (प्रगतिशील स्तर 5)','badge':f'{no:02d}',
      'q':cq,'server':True,'neg':0.25,'minutes':120}
A['cg']['sets'].append(meta)
idx=save(idx,A,span)
idx=idx.replace(f"'cg:{prev}'",f"'cg:{no}'")
n_sets=sum(1 for st in A['cg']['sets'] if series_of(st['no'])=='cspdcl')
idx=re.sub(r'\d+ पूर्ण मॉक टेस्ट \(\d+ प्रश्न\)',f'{n_sets} पूर्ण मॉक टेस्ट ({100*n_sets} प्रश्न)',idx)
(ROOT/'index.html').write_text(idx,encoding='utf-8')
print(f'Published Set {no:02d} into index.html; answers remain server-side')
