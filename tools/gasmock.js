// परीक्षण हेतु: Google Apps Script का न्यूनतम नकली रूप, ताकि apps-script/grader.gs को Node में चलाया जा सके (tools/smoke_test.js)।
const fs = require('fs'), vm = require('vm'), crypto = require('crypto');
const s8 = b => Array.from(b, v => v > 127 ? v - 256 : v);
const u8 = a => Buffer.from(a.map(v => v & 255));

function makeGAS({ props = {}, fetchUrl, legacy = null }) {
  const sheets = {};
  function mkSheet(name) {
    const sh = { name, rows: [], hidden: false,
      appendRow(r) { this.rows.push(r.slice()); },
      getDataRange() { const rows = this.rows; return { getValues: () => rows.map(r => r.map(v => (v instanceof Date ? v : v))) }; },
      getRange(r, c, nr, nc) { const self = this; return { setValues(vals) { for (let i = 0; i < nr; i++) for (let j = 0; j < nc; j++) { self.rows[r - 1 + i][c - 1 + j] = vals[i][j]; } } }; },
      setFrozenRows() {}, hideSheet() { this.hidden = true; } };
    return sh;
  }
  const ss = { getSheetByName: n => sheets[n] || null, insertSheet: n => (sheets[n] = mkSheet(n)) };
  const ctx = {
    SpreadsheetApp: { getActiveSpreadsheet: () => ss },
    ContentService: { MimeType: { JSON: 'json' }, createTextOutput: t => ({ text: t, setMimeType() { return this; } }) },
    LockService: { getScriptLock: () => ({ waitLock() {}, releaseLock() {} }) },
    PropertiesService: { getScriptProperties: () => ({ getProperty: k => (k in props ? String(props[k]) : null) }) },
    Utilities: {
      getUuid: () => crypto.randomUUID(),
      base64Decode: s => s8(Buffer.from(s, 'base64')),
      computeHmacSha256Signature: (msg, key) => s8(crypto.createHmac('sha256', u8(key)).update(u8(msg)).digest()),
      newBlob: x => ({ getBytes: () => s8(Buffer.from(String(x), 'utf8')), getDataAsString: () => u8(x).toString('utf8') }),
    },
    UrlFetchApp: { fetch: (url) => { const r = fetchUrl(url); return { getResponseCode: () => r ? 200 : 404, getContentText: () => r || '' }; } },
    Logger: { log: (...a) => console.log('[Logger]', ...a) },
    JSON, Date, Math, Number, String, Array, isNaN, console,
  };
  if (legacy) ctx.legacyDoPost = legacy;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(require('path').join(__dirname, '..', 'apps-script', 'grader.gs'), 'utf8'), ctx);
  return { ctx, sheets, props, post: body => JSON.parse(ctx.doPost({ postData: { contents: typeof body === 'string' ? body : JSON.stringify(body) } }).text) };
}
module.exports = { makeGAS };
