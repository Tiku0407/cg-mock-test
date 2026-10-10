// वेबसाइट का स्वचालित परीक्षण (रोज़ नया सेट जोड़ने के बाद चलाएँ):  node tools/smoke_test.js
// - नवीनतम सेट परीक्षा मोड में खोलता है, नाम "परीक्षण" / मोबाइल 9999999999 भरता है, 1 उत्तर देकर जमा करता है।
// - script.google.com के अनुरोध असली Sheet तक नहीं जाते: सर्वर-जाँच वाले सेट के लिए नकली Apps Script
//   (tools/gasmock.js + apps-script/grader.gs, GRADER_SECRET से) उत्तर देता है; पुराने सेटों के अनुरोध रोके जाते हैं।
// सफल होने पर "PASS" छापता है, अन्यथा "FAIL ..." और exit code 1।
const path = require('path'), fs = require('fs');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/npm-tools/node_modules/playwright')); }
const { makeGAS } = require('./gasmock.js');
const ROOT = path.join(__dirname, '..');

(async () => {
  const errs = [], fail = m => { console.log('FAIL', m, errs); process.exit(1); };
  let legacy = 0, gas = null;
  const getGas = () => gas || (gas = makeGAS({
    props: { GRADER_SECRET: process.env.GRADER_SECRET || '' },
    fetchUrl: u => { try { return fs.readFileSync(path.join(ROOT, 'keys', u.split('/keys/')[1]), 'utf8'); } catch (e) { return null; } },
    legacy: () => { legacy++; return { text: '{"ok":true}' }; },
  }));
  const exe = ['/opt/pw-browsers/chromium-1194/chrome-linux/chrome'].find(f => fs.existsSync(f));
  const b = await chromium.launch(exe ? { executablePath: exe } : {});
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await ctx.route(/script\.google\.com/, r => {
    const body = r.request().postData() || '{}';
    if (!JSON.parse(body).action) { legacy++; return r.abort(); }      // पुराना Sheet-अनुरोध: रोकें
    let out; try { out = getGas().post(body); } catch (e) { out = { ok: false, code: 'mock_error', msg: String(e) }; }
    r.fulfill({ status: 200, contentType: 'application/json', headers: { 'access-control-allow-origin': '*' }, body: JSON.stringify(out) });
  });
  const p = await ctx.newPage();
  p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + path.join(ROOT, 'index.html'));
  const info = await p.evaluate(() => { const no = Math.max(...CG.sets.map(s => s.no)); cfg.set = 'cg:' + no; cfg.mode = 'exam'; saveCfg(); return { no, server: isSrv(cfg), n: CG_IDX[no].length }; });
  if (info.n !== 100) fail('नवीनतम सेट में 100 प्रश्न नहीं: ' + info.n);
  if (info.server && !process.env.GRADER_SECRET) fail('सर्वर-सेट के परीक्षण के लिए GRADER_SECRET चाहिए');
  await p.fill('#st-name', 'परीक्षण'); await p.fill('#st-mob', '9999999999');
  await p.click('#start');
  try { await p.waitForSelector('#exam:not([hidden])', { timeout: 8000 }); } catch (e) { fail('परीक्षा शुरू नहीं हुई: ' + (await p.textContent('#attempt-msg'))); }
  await p.locator('#choices .choice').first().click();
  await p.click('#submit-btn'); await p.click('#cf-yes');
  try { await p.waitForSelector('#result:not([hidden])', { timeout: 15000 }); } catch (e) { fail('परिणाम नहीं दिखा'); }
  const score = (await p.textContent('#r-score')).trim();
  if (info.server) {
    const row = gas.sheets['सर्वर-परिणाम'].rows.find(r => String(r[0]) === '9999999999');
    if (!row || row[3] !== 'जमा' || String(row[7]) !== score) fail('सर्वर-जाँच का अंक मेल नहीं खाया');
    const rev = await p.evaluate(() => document.querySelectorAll('#rev-list .rev-item').length);
    if (rev !== 100) fail('समीक्षा में 100 प्रश्न नहीं: ' + rev);
  } else if (legacy !== 1) fail('Sheet-अनुरोध अपेक्षित 1, मिला ' + legacy);
  if (errs.length) fail('पेज में JS त्रुटि');
  console.log(`PASS — सेट ${info.no} (${info.server ? 'सर्वर-जाँच' : 'ब्राउज़र-जाँच'}), अंक ${score}, Google Sheet में कोई पंक्ति नहीं भेजी गई`);
  await b.close();
})().catch(e => { console.log('FAIL', e); process.exit(1); });
