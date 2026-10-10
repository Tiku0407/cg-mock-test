/**
 * CSPDCL मॉक टेस्ट — सर्वर-जाँच (Google Apps Script)
 *
 * यह फ़ाइल आपकी Google Sheet से जुड़े Apps Script प्रोजेक्ट में एक नई फ़ाइल के रूप में जोड़ें।
 * लगाने की पूरी विधि: apps-script/SETUP.md
 *
 * क्या करता है:
 *  - परीक्षा मोड में "शुरू" होते ही मोबाइल + सेट दर्ज करता है; उसी मोबाइल से वही सेट दोबारा नहीं (किसी भी फ़ोन/ब्राउज़र से)।
 *  - सही उत्तर वेबसाइट में नहीं रहते; जमा करने पर उत्तरों की जाँच यहीं (सर्वर पर) होती है और अंक Sheet में लिखे जाते हैं।
 *  - समय-सीमा सर्वर की घड़ी से जाँची जाती है; देर से जमा होने पर "देर" लिखा जाता है।
 *  - उत्तर-कुंजी वेबसाइट पर कूटबद्ध (encrypted) फ़ाइल keys/setNN.key में रहती है; इसे केवल यही स्क्रिप्ट
 *    Script Property GRADER_SECRET से खोल सकती है।
 *  - पुराने (action रहित) अनुरोध पहले की तरह आपके पुराने doPost (अब legacyDoPost) को भेजे जाते हैं।
 *
 * Script Properties (Project Settings → Script properties):
 *  GRADER_SECRET        (अनिवार्य)  उत्तर-कुंजी खोलने की गुप्त कुंजी — Claude द्वारा दी गई।
 *  SITE_URL             (वैकल्पिक) डिफ़ॉल्ट https://tiku0407.github.io/cg-mock-test/
 *  REVIEW_AFTER_HOURS   (वैकल्पिक) सेट प्रकाशित होने के कितने घंटे बाद जमा करने वालों को सही उत्तर/व्याख्या दिखें। डिफ़ॉल्ट 0 (तुरंत)।
 *  PRACTICE_OPEN_HOURS  (वैकल्पिक) कितने घंटे बाद बिना परीक्षा दिए भी अभ्यास मोड खुले। डिफ़ॉल्ट 24।
 *  GRACE_MINUTES        (वैकल्पिक) समय-सीमा के बाद कितने मिनट तक जमा "समय पर" माना जाए। डिफ़ॉल्ट 3।
 *  SHEET_ID             (वैकल्पिक) केवल तब, जब यह स्क्रिप्ट किसी Sheet से जुड़ी (bound) न हो।
 */

var RESULT_SHEET = 'सर्वर-परिणाम';
var KEY_SHEET = 'उत्तर-कुंजी (गुप्त)';
var RESULT_HEAD = ['मोबाइल', 'नाम', 'सेट', 'स्थिति', 'शुरू', 'जमा', 'लगा समय (मिनट)', 'अंक', 'कुल', 'प्रतिशत',
  'सही', 'गलत', 'छोड़े', 'भागवार', 'चेतावनियाँ', 'स्वतः जमा', 'समय', 'टोकन', 'start_ms', 'submit_ms', 'उत्तर'];
var C = {}; RESULT_HEAD.forEach(function (h, i) { C[h] = i; });

function doPost(e) {
  var body = {};
  try { body = JSON.parse((e && e.postData && e.postData.contents) || '{}'); } catch (err) { body = {}; }
  if (!body.action) {
    if (typeof legacyDoPost === 'function') return legacyDoPost(e);
    return out_({ ok: false, code: 'no_action' });
  }
  var lock = LockService.getScriptLock();
  lock.waitLock(25000);
  try {
    if (body.action === 'start') return out_(start_(body));
    if (body.action === 'submit') return out_(submit_(body));
    if (body.action === 'key') return out_(key_(body));
    return out_({ ok: false, code: 'bad_action' });
  } catch (err) {
    return out_({ ok: false, code: 'error', msg: String(err && err.message || err) });
  } finally {
    lock.releaseLock();
  }
}

// ---------- actions ----------
function start_(b) {
  var mob = String(b.mobile || ''), set = Number(b.set), name = String(b.name || '').slice(0, 60);
  if (!/^[6-9]\d{9}$/.test(mob)) return { ok: false, code: 'bad_mobile' };
  var K = getKey_(set);
  if (!K) return { ok: false, code: 'no_key' };
  var sh = resultSheet_(), rows = sh.getDataRange().getValues(), now = Date.now();
  for (var r = 1; r < rows.length; r++) {
    if (String(rows[r][C['मोबाइल']]) === mob && Number(rows[r][C['सेट']]) === set) {
      if (rows[r][C['स्थिति']] === 'जमा') {
        return { ok: false, code: 'done', score: rows[r][C['अंक']], total: rows[r][C['कुल']] };
      }
      return { ok: true, token: rows[r][C['टोकन']], start: Number(rows[r][C['start_ms']]), now: now, minutes: K.minutes, resumed: true };
    }
  }
  var token = Utilities.getUuid(), row = blankRow_();
  row[C['मोबाइल']] = mob; row[C['नाम']] = name; row[C['सेट']] = set; row[C['स्थिति']] = 'शुरू';
  row[C['शुरू']] = new Date(now); row[C['टोकन']] = token; row[C['start_ms']] = now;
  sh.appendRow(row);
  return { ok: true, token: token, start: now, now: now, minutes: K.minutes };
}

function submit_(b) {
  var token = String(b.token || ''), sh = resultSheet_(), rows = sh.getDataRange().getValues();
  var r = -1;
  for (var i = 1; i < rows.length; i++) if (String(rows[i][C['टोकन']]) === token) { r = i; break; }
  if (r < 0) return { ok: false, code: 'bad_token' };
  var row = rows[r], set = Number(row[C['सेट']]), K = getKey_(set);
  if (!K) return { ok: false, code: 'no_key' };
  var res;
  if (row[C['स्थिति']] === 'जमा') {                       // दोबारा भेजा गया — वही परिणाम लौटाएँ
    res = JSON.parse(row[C['उत्तर']] || '{}').res || {};
  } else {
    var ans = Array.isArray(b.answers) ? b.answers : [];
    var ok = 0, bad = 0, skip = 0, secs = [], k = 0;
    K.secs.forEach(function (s) {
      var got = 0;
      for (var j = 0; j < s[1]; j++, k++) {
        var a = ans[k];
        if (a === null || a === undefined || a === '') skip++;
        else if (Number(a) === K.a[k]) { ok++; got++; }
        else bad++;
      }
      secs.push([s[0], got, s[1]]);
    });
    var n = K.a.length, score = Math.round((ok - bad * K.neg) * 100) / 100;
    var now = Date.now(), start = Number(row[C['start_ms']]);
    var grace = num_('GRACE_MINUTES', 3) * 60000, late = now - start > K.minutes * 60000 + grace;
    res = { score: score, total: n, pct: Math.max(0, Math.round(score / n * 100)), correct: ok, wrong: bad, skipped: skip,
      sections: secs, late: late, used_min: Math.round((now - start) / 60000) };
    row[C['स्थिति']] = 'जमा'; row[C['जमा']] = new Date(now); row[C['submit_ms']] = now;
    row[C['लगा समय (मिनट)']] = res.used_min; row[C['अंक']] = score; row[C['कुल']] = n; row[C['प्रतिशत']] = res.pct;
    row[C['सही']] = ok; row[C['गलत']] = bad; row[C['छोड़े']] = skip;
    row[C['भागवार']] = secs.map(function (s) { return s[0] + ' ' + s[1] + '/' + s[2]; }).join(', ');
    row[C['चेतावनियाँ']] = Number(b.violations) || 0; row[C['स्वतः जमा']] = b.auto ? 'हाँ' : '';
    row[C['समय']] = late ? 'देर से जमा' : 'समय पर';
    row[C['उत्तर']] = JSON.stringify({ ans: ans.slice(0, n), res: res });
    sh.getRange(r + 1, 1, 1, row.length).setValues([row]);
  }
  var out = { ok: true };
  for (var p in res) out[p] = res[p];
  var openAt = K.pub + num_('REVIEW_AFTER_HOURS', 0) * 3600000;
  if (Date.now() >= openAt) { out.a = K.a; out.e = K.e; } else out.review_at = openAt;
  return out;
}

function key_(b) {
  var mob = String(b.mobile || ''), set = Number(b.set), K = getKey_(set);
  if (!K) return { ok: false, code: 'no_key' };
  var now = Date.now(), reviewAt = K.pub + num_('REVIEW_AFTER_HOURS', 0) * 3600000;
  var openAll = K.pub + Math.max(num_('REVIEW_AFTER_HOURS', 0), num_('PRACTICE_OPEN_HOURS', 24)) * 3600000;
  var done = false, rows = resultSheet_().getDataRange().getValues();
  for (var r = 1; r < rows.length; r++)
    if (String(rows[r][C['मोबाइल']]) === mob && Number(rows[r][C['सेट']]) === set && rows[r][C['स्थिति']] === 'जमा') done = true;
  if ((done && now >= reviewAt) || now >= openAll) return { ok: true, a: K.a, e: K.e };
  return { ok: false, code: 'locked', open_at: done ? reviewAt : openAll, done: done };
}

// ---------- उत्तर-कुंजी ----------
function getKey_(set) {
  if (!(set > 0)) return null;
  var sh = keySheet_(), rows = sh.getDataRange().getValues();
  for (var r = 1; r < rows.length; r++) if (Number(rows[r][0]) === set) return parseKey_(rows[r]);
  var site = PropertiesService.getScriptProperties().getProperty('SITE_URL') || 'https://tiku0407.github.io/cg-mock-test/';
  var url = site.replace(/\/?$/, '/') + 'keys/set' + (set < 10 ? '0' : '') + set + '.key';
  var resp = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  if (resp.getResponseCode() !== 200) return null;
  var K = decrypt_(resp.getContentText().trim());
  if (!K || Number(K.no) !== set) return null;
  var row = [set, new Date(), Date.now(), JSON.stringify({ secs: K.secs, neg: K.neg, minutes: K.minutes, a: K.a }), JSON.stringify(K.e)];
  sh.appendRow(row);
  return parseKey_(row);
}
function parseKey_(row) {
  var m = JSON.parse(row[3]);
  return { secs: m.secs, neg: Number(m.neg) || 0, minutes: Number(m.minutes) || 120, a: m.a, e: JSON.parse(row[4] || '[]'), pub: Number(row[2]) };
}

// HMAC-SHA256 आधारित कूटन: base64( nonce[16] | ciphertext | tag[32] )
function decrypt_(b64) {
  var secret = PropertiesService.getScriptProperties().getProperty('GRADER_SECRET');
  if (!secret) throw new Error('Script Property GRADER_SECRET सेट नहीं है');
  var all = u8_(Utilities.base64Decode(b64));
  if (all.length < 49) return null;
  var nonce = all.slice(0, 16), ct = all.slice(16, all.length - 32), tag = all.slice(all.length - 32);
  var sk = u8_(Utilities.newBlob(secret).getBytes());
  var encKey = hmac_(u8_(Utilities.newBlob('enc').getBytes()), sk), macKey = hmac_(u8_(Utilities.newBlob('mac').getBytes()), sk);
  var calc = hmac_(nonce.concat(ct), macKey), diff = 0;
  for (var i = 0; i < 32; i++) diff |= calc[i] ^ tag[i];
  if (diff) return null;                                         // गलत secret या बदली गई फ़ाइल
  var pt = [];
  for (var blk = 0; blk * 32 < ct.length; blk++) {
    var ks = hmac_(nonce.concat([(blk >>> 24) & 255, (blk >>> 16) & 255, (blk >>> 8) & 255, blk & 255]), encKey);
    for (var j = 0; j < 32 && blk * 32 + j < ct.length; j++) pt.push(ct[blk * 32 + j] ^ ks[j]);
  }
  return JSON.parse(Utilities.newBlob(s8_(pt)).getDataAsString('UTF-8'));
}
function hmac_(msgU8, keyU8) { return u8_(Utilities.computeHmacSha256Signature(s8_(msgU8), s8_(keyU8))); }
function u8_(a) { var o = []; for (var i = 0; i < a.length; i++) o.push(a[i] & 255); return o; }
function s8_(a) { var o = []; for (var i = 0; i < a.length; i++) o.push(a[i] > 127 ? a[i] - 256 : a[i]); return o; }

// ---------- sheets ----------
function ss_() {
  var id = PropertiesService.getScriptProperties().getProperty('SHEET_ID');   // स्क्रिप्ट Sheet से जुड़ी न हो तो
  return id ? SpreadsheetApp.openById(id) : SpreadsheetApp.getActiveSpreadsheet();
}
function resultSheet_() {
  var sh = ss_().getSheetByName(RESULT_SHEET);
  if (!sh) { sh = ss_().insertSheet(RESULT_SHEET); sh.appendRow(RESULT_HEAD); sh.setFrozenRows(1); }
  return sh;
}
function keySheet_() {
  var sh = ss_().getSheetByName(KEY_SHEET);
  if (!sh) { sh = ss_().insertSheet(KEY_SHEET); sh.appendRow(['सेट', 'लोड हुआ', 'pub_ms', 'कुंजी', 'व्याख्या']); sh.hideSheet(); }
  return sh;
}
function blankRow_() { var r = []; for (var i = 0; i < RESULT_HEAD.length; i++) r.push(''); return r; }
function num_(k, d) { var v = PropertiesService.getScriptProperties().getProperty(k); return v === null || v === '' || isNaN(Number(v)) ? d : Number(v); }
function out_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }

/** सेटअप के बाद एक बार चलाएँ: अनुमतियाँ देने और कुंजी-जाँच के लिए (Run → testSetup) */
function testSetup() {
  resultSheet_(); keySheet_();
  var p = PropertiesService.getScriptProperties();
  if (!p.getProperty('GRADER_SECRET')) throw new Error('पहले Script Property GRADER_SECRET जोड़ें');
  var site = p.getProperty('SITE_URL') || 'https://tiku0407.github.io/cg-mock-test/';
  var resp = UrlFetchApp.fetch(site.replace(/\/?$/, '/') + 'keys/test.key', { muteHttpExceptions: true });
  if (resp.getResponseCode() !== 200) throw new Error('keys/test.key नहीं मिली (' + resp.getResponseCode() + ')');
  var t = decrypt_(resp.getContentText().trim());
  if (!t || t.test !== 'ठीक है') throw new Error('GRADER_SECRET गलत है — कुंजी खुल नहीं रही');
  Logger.log('सब ठीक है ✓ — कुंजी खुल गई, Sheets तैयार हैं।');
}
