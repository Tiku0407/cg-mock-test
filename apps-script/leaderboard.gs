/**
 * CGSSB/CSPDCL Leaderboard API
 * Add this as a NEW Apps Script file named: leaderboard.gs
 * Existing grader.gs / doPost logic is untouched.
 *
 * GET:
 *   ?action=leaderboard&type=daily
 *   ?action=leaderboard&type=weekly
 *   ?action=leaderboard&type=monthly
 */
function doGet(e) {
  var action = String((e && e.parameter && e.parameter.action) || '');
  if (action === 'leaderboard') {
    try {
      return outLeaderboard_(buildLeaderboard_(String(e.parameter.type || 'daily')));
    } catch (err) {
      return outLeaderboard_({ ok:false, error:String(err && err.message || err) });
    }
  }
  return outLeaderboard_({ ok:true, app:'CGSSB Mock Test API' });
}

function buildLeaderboard_(type) {
  type = ['daily','weekly','monthly'].indexOf(type) >= 0 ? type : 'daily';
  var sh = ss_().getSheetByName('सर्वर-परिणाम');
  if (!sh) return { ok:true, type:type, generated_at:new Date().toISOString(), rows:[] };

  var vals = sh.getDataRange().getValues();
  if (vals.length < 2) return { ok:true, type:type, generated_at:new Date().toISOString(), rows:[] };

  var head = vals[0], col = {};
  head.forEach(function(h,i){ col[String(h)] = i; });

  var required = ['मोबाइल','नाम','सेट','स्थिति','जमा','लगा समय (मिनट)','अंक','कुल','प्रतिशत','सही','गलत','छोड़े'];
  required.forEach(function(h){ if (col[h] === undefined) throw new Error('Missing column: '+h); });

  var now = new Date();
  var start = periodStart_(type, now);
  var best = {};

  for (var r=1; r<vals.length; r++) {
    var row = vals[r];
    if (String(row[col['स्थिति']]) !== 'जमा') continue;

    var submitted = row[col['जमा']];
    if (!(submitted instanceof Date)) submitted = new Date(submitted);
    if (!submitted || isNaN(submitted.getTime()) || submitted < start || submitted > now) continue;

    var mobile = String(row[col['मोबाइल']] || '').trim();
    var name = String(row[col['नाम']] || '').trim();
    if (!mobile || !name) continue;

    var item = {
      name: name,
      mobile: mobile,
      set: Number(row[col['सेट']]) || row[col['सेट']],
      score: Number(row[col['अंक']]) || 0,
      total: Number(row[col['कुल']]) || 0,
      percentage: Number(row[col['प्रतिशत']]) || 0,
      correct: Number(row[col['सही']]) || 0,
      wrong: Number(row[col['गलत']]) || 0,
      skipped: Number(row[col['छोड़े']]) || 0,
      timeMinutes: Number(row[col['लगा समय (मिनट)']]) || 999999,
      submittedAt: submitted.toISOString()
    };

    var prev = best[mobile];
    if (!prev || item.score > prev.score ||
        (item.score === prev.score && item.timeMinutes < prev.timeMinutes) ||
        (item.score === prev.score && item.timeMinutes === prev.timeMinutes && item.correct > prev.correct)) {
      best[mobile] = item;
    }
  }

  var rows = Object.keys(best).map(function(k){ return best[k]; });
  rows.sort(function(a,b){
    if (b.score !== a.score) return b.score - a.score;
    if (a.timeMinutes !== b.timeMinutes) return a.timeMinutes - b.timeMinutes;
    return b.correct - a.correct;
  });
  rows = rows.slice(0,10).map(function(x,i){ x.rank=i+1; return x; });

  return {
    ok:true,
    type:type,
    period_start:start.toISOString(),
    generated_at:now.toISOString(),
    rule:'Exam server results only; best score per mobile; tie-break: faster time, then more correct answers',
    rows:rows
  };
}

function periodStart_(type, now) {
  var d = new Date(now.getTime());
  if (type === 'daily') {
    d.setHours(0,0,0,0);
    return d;
  }
  if (type === 'weekly') {
    var day = d.getDay(); // Sun=0
    var diff = day === 0 ? 6 : day - 1; // Monday start
    d.setDate(d.getDate() - diff);
    d.setHours(0,0,0,0);
    return d;
  }
  d.setDate(1);
  d.setHours(0,0,0,0);
  return d;
}

function outLeaderboard_(o) {
  return ContentService
    .createTextOutput(JSON.stringify(o))
    .setMimeType(ContentService.MimeType.JSON);
}
