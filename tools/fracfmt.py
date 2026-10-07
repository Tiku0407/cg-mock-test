#!/usr/bin/env python3
"""प्रिंट-पेपर (papers/*.html) में भिन्नों (3/8, 1 3/8) को ऊपर-नीचे (अंश/हर) रूप में बदलता है।

उपयोग:  python3 tools/fracfmt.py papers/mock-test-07.html lists/mock-test-07.md [और फ़ाइलें…]
(.md फ़ाइलों में मिश्र भिन्न '1 3/8' → '1³⁄₈' बनती है।)
add_set.py नया पेपर लिखते समय इसे अपने-आप चलाता है। दोबारा चलाना सुरक्षित है।
"""
import re, sys
from pathlib import Path

FRAC_RE = re.compile(r'(^|[^\d/.,])(?:(\d+)\s+)?(\d+)/(\d+)(?![\d/])')
CSS = ('.frac{display:inline-flex;flex-direction:column;align-items:center;vertical-align:middle;'
       'font-size:.82em;line-height:1.1;margin:0 .12em}'
       '.frac>.fn{border-bottom:1.3px solid currentColor;padding:0 .2em}.frac>.fd{padding:0 .2em}'
       '.mix{white-space:nowrap;font-weight:600}.mix .frac{margin-left:.08em}.frac .sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}')


def _sub(m):
    pre, w, n, d = m.groups()
    f = (f'<span class="frac"><span class="fn">{n}</span>'
         f'<span class="sr">/</span><span class="fd">{d}</span></span>')
    return f'{pre}<span class="mix">{w}{f}</span>' if w else pre + f


SUP = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')
SUB = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')
MIXED_RE = re.compile(r'(^|[^\d/.,])(\d+)\s+(\d+)/(\d+)(?![\d/])')


def frac_text(t: str) -> str:
    """सादे पाठ (.md सूची आदि) में मिश्र भिन्न '1 3/8' को '1³⁄₈' बनाता है, ताकि वह 13/8 न पढ़ा जाए।"""
    return MIXED_RE.sub(lambda m: f'{m[1]}{m[2]}{m[3].translate(SUP)}⁄{m[4].translate(SUB)}', t)


def frac_html(html: str) -> str:
    out, i = [], 0
    # केवल टैग के बाहर का पाठ बदलें; <script>/<style>/<title> के अंदर कुछ न बदलें
    for m in re.finditer(r'<script\b.*?</script>|<style\b.*?</style>|<title\b.*?</title>|<[^>]+>', html, re.S | re.I):
        out.append(FRAC_RE.sub(_sub, html[i:m.start()]))
        out.append(m.group(0))
        i = m.end()
    out.append(FRAC_RE.sub(_sub, html[i:]))
    html = ''.join(out)
    if '.frac{' not in html:
        html = html.replace('</style>', CSS + '</style>', 1)
    return html


if __name__ == '__main__':
    for f in sys.argv[1:]:
        p = Path(f); old = p.read_text()
        new = frac_text(old) if p.suffix == '.md' else frac_html(old)
        if new != old:
            p.write_text(new); print('बदला:', f)
