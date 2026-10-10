"""index.html के प्रश्न-डेटा (DATA) को पढ़ने/लिखने का साझा कोड।

वेबसाइट में DATA खुले JSON के रूप में नहीं रखा जाता, ताकि 'View Source' से
सही उत्तर सीधे न दिखें: JSON → zlib → XOR(KEY) → base64, और पेज में
`const DATA = JSON.parse(_dx("…"));` के रूप में रहता है (_dx पेज में pako से खोलता है)।
यह केवल छिपाना है, पूरी सुरक्षा नहीं।

    from datacodec import load, save
    A, span = load(html)          # A = DATA (dict)
    html = save(html, A, span)
"""
import base64, json, zlib

KEY = b'cg-mock-test::cspdcl'
MARK = 'const DATA = JSON.parse(_dx("'
END = '"));'


def _x(b):
    return bytes(c ^ KEY[i % len(KEY)] for i, c in enumerate(b))


def encode(A):
    raw = json.dumps(A, ensure_ascii=False, separators=(',', ':')).encode()
    return base64.b64encode(_x(zlib.compress(raw, 9))).decode()


def decode(s):
    return json.loads(zlib.decompress(_x(base64.b64decode(s))).decode())


def load(html):
    """(DATA, (a, b)) लौटाता है; html[a:b] पूरी `const DATA = …;` पंक्ति है।"""
    i = html.find(MARK)
    if i >= 0:
        j = html.find(END, i)
        return decode(html[i + len(MARK):j]), (i, j + len(END))
    i = html.find('const DATA = ')          # पुराना (खुला JSON) रूप
    j = html.find(';\n', i)
    return json.loads(html[i + 13:j]), (i, j + 1)


def save(html, A, span):
    a, b = span
    return html[:a] + MARK + encode(A) + END + html[b:]
