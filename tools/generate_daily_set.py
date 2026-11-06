#!/usr/bin/env python3
import os, json, re, subprocess, sys
from pathlib import Path
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent

def latest_set():
    code = "import sys;sys.path.insert(0,'tools');from datacodec import load;A,_=load(open('index.html').read());print(max(s['no'] for s in A['cg']['sets'] if not s.get('series')))"
    return int(subprocess.check_output([sys.executable, "-c", code], cwd=ROOT).decode().strip())

def level_name(no):
    out = subprocess.check_output([sys.executable, "tools/level.py", str(no)], cwd=ROOT).decode("utf-8", "ignore")
    return out.splitlines()[0].strip()

def extract_json(text):
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise RuntimeError("Model output did not contain JSON")
    return json.loads(m.group(0))

def validate(data):
    if not isinstance(data, dict) or "sections" not in data:
        raise ValueError("Missing sections")
    expected = [25,15,15,15,20,10]
    if len(data["sections"]) != 6:
        raise ValueError("Need 6 sections")
    for si, (sec,n) in enumerate(zip(data["sections"], expected)):
        qs = sec.get("questions",[])
        if len(qs) != n:
            raise ValueError(f"Section {si+1}: expected {n}, got {len(qs)}")
        for q in qs:
            if not isinstance(q.get("q"), str) or len(q["q"].strip()) < 5: raise ValueError("Bad question")
            o=q.get("o")
            if not isinstance(o,list) or len(o)!=4 or len(set(map(str,o)))!=4: raise ValueError("Bad options")
            a=q.get("a")
            if not isinstance(a,int) or a<0 or a>3: raise ValueError("Bad answer")
            if q.get("d") not in ("सरल","मध्यम","कठिन"): raise ValueError("Bad difficulty")
            if not isinstance(q.get("e"),str) or not q["e"].strip(): raise ValueError("Missing explanation")

def to_js(data, outpath):
    titles = [
      "भाग-एक : छत्तीसगढ़ का सामान्य ज्ञान",
      "भाग-दो : कम्प्यूटर की सामान्य जानकारी",
      "भाग-तीन : सामान्य मानसिक योग्यता",
      "भाग-चार : सामान्य गणित",
      "भाग-पाँच : सामान्य हिन्दी",
      "भाग-छह : सामान्य अंग्रेजी"
    ]
    marks=[25,15,15,15,20,10]
    parts=[]
    for i,sec in enumerate(data["sections"]):
        qs=[]
        for q in sec["questions"]:
            obj={"q":q["q"],"o":q["o"],"a":q["a"],"d":q["d"],"e":q["e"]}
            qs.append(json.dumps(obj,ensure_ascii=False,separators=(",",":")))
        parts.append("{title:"+json.dumps(titles[i],ensure_ascii=False)+",marks:"+str(marks[i])+",qs:["+",\n".join(qs)+"]}")
    outpath.write_text("module.exports = [\n"+",\n".join(parts)+"\n];\n",encoding="utf-8")

def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY missing")
    no=latest_set()+1
    lvl=level_name(no)
    rules=(ROOT/"tools/DAILY_SET.md").read_text(encoding="utf-8")
    client=OpenAI()
    prompt=f"""
आप CSPDCL DEO / स्टेनोग्राफर Grade-III के लिए Daily Mock Test {no:02d} बना रहे हैं।
Difficulty target: {lvl}

नीचे repository के authoritative daily rules हैं। इन्हें अक्षरशः follow करें:
--- RULES ---
{rules[:22000]}
--- END RULES ---

Output केवल valid JSON object हो, markdown नहीं।
Schema:
{{
  "sections":[
    {{"questions":[{{"q":"...","o":["...","...","...","..."],"a":0,"d":"सरल|मध्यम|कठिन","e":"..."}}]}},
    ... कुल 6 sections
  ]
}}
Question counts exactly 25,15,15,15,20,10 हों।
हर प्रश्न का एक ही निर्विवाद सही उत्तर हो।
पुराने sets की concepts/questions repeat न हों; नीचे repository duplicate checker बाद में भी जाँचेगा।
Math/reasoning answers internally solve/verify करें।
Current-affairs questions में web search अनिवार्य है और DAILY_SET.md में अनुमति दिए गए newspapers से ही facts लें। Explanation के अंत में source newspaper name/date दें।
No URLs in question text. No answer leakage outside JSON answer index.
"""
    resp=client.responses.create(
        model=os.getenv("OPENAI_MODEL","gpt-6-astra"),
        tools=[{"type":"web_search","search_context_size":"high"}],
        input=prompt,
    )
    data=extract_json(resp.output_text)
    validate(data)
    private=ROOT/"private"; private.mkdir(exist_ok=True)
    out=private/f"set{no:02d}.js"
    to_js(data,out)
    print(f"Generated {out}")
    print(f"SET_NO={no:02d}")
    print(f"LEVEL_NAME={lvl}")

if __name__=="__main__":
    main()
