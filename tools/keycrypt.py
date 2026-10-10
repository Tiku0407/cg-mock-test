"""उत्तर-कुंजी का कूटन (encryption) — apps-script/grader.gs के decrypt_ से मेल खाता है।

प्रारूप: base64( nonce[16] | ciphertext | tag[32] )
  encKey = HMAC(secret, "enc"), macKey = HMAC(secret, "mac")
  keystream block i = HMAC(encKey, nonce | i[4 बाइट, big-endian])
  tag = HMAC(macKey, nonce | ciphertext)

गुप्त कुंजी केवल environment variable GRADER_SECRET में रहती है — रिपॉज़िटरी में कभी नहीं।
"""
import base64, hashlib, hmac, json, os


def _h(key, msg):
    return hmac.new(key, msg, hashlib.sha256).digest()


def secret():
    s = os.environ.get('GRADER_SECRET', '').strip()
    if not s:
        raise SystemExit('GRADER_SECRET environment variable नहीं मिला')
    return s


def encrypt(obj, sec):
    sk = sec.encode()
    enc, mac = _h(sk, b'enc'), _h(sk, b'mac')
    pt = json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode()
    nonce = os.urandom(16)
    ks = b''.join(_h(enc, nonce + i.to_bytes(4, 'big')) for i in range((len(pt) + 31) // 32))
    ct = bytes(a ^ b for a, b in zip(pt, ks))
    return base64.b64encode(nonce + ct + _h(mac, nonce + ct)).decode()


def decrypt(b64, sec):
    raw = base64.b64decode(b64)
    nonce, ct, tag = raw[:16], raw[16:-32], raw[-32:]
    sk = sec.encode()
    enc, mac = _h(sk, b'enc'), _h(sk, b'mac')
    if not hmac.compare_digest(_h(mac, nonce + ct), tag):
        raise ValueError('गलत secret या बदली गई फ़ाइल')
    ks = b''.join(_h(enc, nonce + i.to_bytes(4, 'big')) for i in range((len(ct) + 31) // 32))
    return json.loads(bytes(a ^ b for a, b in zip(ct, ks)).decode())
