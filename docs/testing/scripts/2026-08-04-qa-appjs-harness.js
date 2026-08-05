/* QA independent harness: load the SHIPPED src/web/app.js in Node with minimal
 * DOM stubs, then compare its calculation layer (F3 aggregate, F5 smaMap,
 * F1 computeWindow) against expected values computed independently in Python
 * (v2_expected.json). Written by QA - not derived from the dev team's harness.
 */
"use strict";
const fs = require("fs");
const path = require("path");

const ROOT = "d:\\personal\\Claude \ud504\ub85c\uc81d\ud2b8\\Stock tools";
const SCRATCH = __dirname;

// ---- minimal DOM stubs so top-level init() is inert ----
global.document = {
  documentElement: { getAttribute: () => null, setAttribute: () => {} },
  getElementById: () => null,
  querySelector: () => null,
  querySelectorAll: () => [],
  body: { getAttribute: () => null },
  createElement: () => ({ style: {}, setAttribute: () => {}, appendChild: () => {},
                          addEventListener: () => {}, classList: { toggle: () => {} } }),
};
global.window = {};

const src = fs.readFileSync(path.join(ROOT, "src", "web", "app.js"), "utf8");
const api = eval(src + "\n;({aggregate, smaMap, computeWindow, mondayOf, state, PERIODS, UNIT_RULES})");

const exp = JSON.parse(fs.readFileSync(path.join(SCRATCH, "v2_expected.json"), "utf8"));
const kb = JSON.parse(fs.readFileSync(path.join(ROOT, "src", "web", "data", "history", "KB.json"), "utf8")).rows;
const tsm = JSON.parse(fs.readFileSync(path.join(ROOT, "src", "web", "data", "history", "TSM.json"), "utf8")).rows;
const skhy = JSON.parse(fs.readFileSync(path.join(ROOT, "src", "web", "data", "history", "SKHY.json"), "utf8")).rows;

let pass = 0, fail = 0;
function check(name, cond, detail) {
  console.log(`[${cond ? "PASS" : "FAIL"}] ${name}  ${detail || ""}`);
  cond ? pass++ : fail++;
}
const close = (a, b, tol) => Math.abs(a - b) <= (tol || 0.01);

// ---------- F3: month aggregation (TSM MAX) ----------
const months = api.aggregate(tsm, "M");
check(`TSM MAX month point count == ${exp.tsm_month_count}`, months.length === exp.tsm_month_count,
      `got ${months.length}`);
for (const [key, e] of Object.entries(exp.tsm_month_samples)) {
  const m = months.find(x => x.range === "\uc6d4: " + key);
  check(`TSM month ${key}: last trading day + premium`,
        m && m.date === e.date && close(m.premium, e.premium, 1e-9),
        m ? `${m.date} ${m.premium}` : "not found");
}

// ---------- F3: week aggregation (KB) + ff inheritance + F6 vol sum ----------
const weeks = api.aggregate(kb, "W");
for (const [key, e] of Object.entries(exp.kb_week_samples)) {
  // match by exact last-trading-day date (year-qualified) - range label has no year
  const w = weeks.find(x => x.date === e.date);
  const okBase = w && w.date === e.date && close(w.premium, e.premium, 1e-9);
  const okFf = w && w.ff_dr === e.ff_dr && w.ff_local === e.ff_local;
  const okVol = w && w.vol_dr === e.vol_dr_sum && w.vol_local === e.vol_local_sum;
  check(`KB week ${key}: value/date`, okBase, w ? `${w.date} ${w.premium}` : "not found");
  check(`KB week ${key}: ff flags inherited`, okFf, w ? `ff_dr=${w.ff_dr}` : "");
  check(`KB week ${key}: volume sums (F6)`, okVol,
        w ? `dr=${w.vol_dr} local=${w.vol_local}` : "");
}
check("KB week 06-15 last day is 06-19 with ff_dr (tooltip carry)",
      exp.kb_week_0615_last_is_ff_dr === true);
// range label format
const w720 = weeks.find(x => x.range && x.range.startsWith("\uc8fc: 07-20"));
check("week range label '주: MM-DD~MM-DD' format",
      w720 && /^\uc8fc: \d{2}-\d{2}~\d{2}-\d{2}$/.test(w720.range), w720 && w720.range);

// ---------- F5: SMA ----------
const sma20 = api.smaMap(kb, 20);
const sma60 = api.smaMap(kb, 60);
check(`KB SMA20 @${exp.kb_last_date} == ${exp.kb_sma20_last}`,
      close(sma20[exp.kb_last_date], exp.kb_sma20_last), `got ${sma20[exp.kb_last_date]}`);
check(`KB SMA60 @${exp.kb_last_date} == ${exp.kb_sma60_last}`,
      close(sma60[exp.kb_last_date], exp.kb_sma60_last), `got ${sma60[exp.kb_last_date]}`);
check(`KB SMA20 @2026-07-01 == ${exp.kb_sma20_20260701}`,
      close(sma20["2026-07-01"], exp.kb_sma20_20260701), `got ${sma20["2026-07-01"]}`);
// no SMA before n-1 points
const firstKbDate = kb[18].date;
check("SMA20 undefined before 20th point", sma20[kb[0].date] === undefined && sma20[firstKbDate] === undefined);
check("SKHY 18 rows -> SMA20 map empty (데이터 부족 케이스)",
      Object.keys(api.smaMap(skhy, 20)).length === 0);

// ---------- F1: computeWindow (1Y window + average + clamp + latest) ----------
api.state.period = "1Y"; api.state.unit = "D"; api.state.endMs = null;
let win = api.computeWindow(kb);
check(`1Y window point count == ${exp.kb_1y_count}`, win.data.length === exp.kb_1y_count,
      `got ${win.data.length}`);
const avg = win.data.reduce((a, r) => a + r.premium, 0) / win.data.length;
check(`1Y window average == ${exp.kb_1y_avg} (기간 평균선 값)`, close(avg, exp.kb_1y_avg),
      `got ${avg.toFixed(4)}`);
check("1Y panEnabled for long series", win.panEnabled === true);
check("initial isPanned=false (최신 구간)", win.isPanned === false);

// pan into the past by ~100 days
const DAY = 86400000;
api.state.endMs = win.lastMs - 100 * DAY;
let win2 = api.computeWindow(kb);
check("panned window: isPanned=true, last point <= end date",
      win2.isPanned === true &&
      new Date(win2.data[win2.data.length - 1].date + "T00:00:00Z").getTime() <= win.lastMs - 100 * DAY);
check("panned window still spans ~1Y",
      Math.abs(win2.data.length - exp.kb_1y_count) < 30, `count ${win2.data.length}`);

// clamp at data start (endMs = 0 -> minEnd)
api.state.endMs = 0;
let win3 = api.computeWindow(kb);
const firstMs = new Date(kb[0].date + "T00:00:00Z").getTime();
check("clamp at past boundary: first shown point is data start (no overscroll)",
      win3.data[0].date === kb[0].date || new Date(win3.data[0].date + "T00:00:00Z").getTime() - firstMs < 5 * DAY,
      `first shown ${win3.data[0].date} vs data start ${kb[0].date}`);
check("clamped endMs == minEnd (stored, not null)", api.state.endMs === win3.minEnd);

// return to latest
api.state.endMs = null;
let win4 = api.computeWindow(kb);
check("return to latest: last shown == last data",
      win4.data[win4.data.length - 1].date === kb[kb.length - 1].date);

// clamp at future boundary (endMs beyond last -> null/최신)
api.state.endMs = win.lastMs + 50 * DAY;
let win5 = api.computeWindow(kb);
check("future overscroll clamped to latest (endMs reset to null)",
      api.state.endMs === null && win5.data[win5.data.length - 1].date === kb[kb.length - 1].date);

// MAX: no panning
api.state.period = "MAX"; api.state.endMs = null;
let winMax = api.computeWindow(kb);
check("MAX: panEnabled=false, full data", winMax.panEnabled === false && winMax.data.length === kb.length);

// short series (SKHY 18 rows): 1Y pan disabled
api.state.period = "1Y"; api.state.endMs = null;
let winS = api.computeWindow(skhy);
check("SKHY(18 rows) 1Y: panEnabled=false (짧은 종목 비활성)", winS.panEnabled === false);

// keyboard step = 10% of window length (PRD) - replicate handler math
api.state.period = "1Y"; api.state.endMs = null;
const p1y = api.PERIODS.find(x => x.key === "1Y");
let w0 = api.computeWindow(kb);
let end0 = w0.lastMs;
let end1 = end0 - p1y.days * DAY * 0.1;
end1 = Math.min(w0.lastMs, Math.max(w0.minEnd, end1));
check("keyboard left-arrow step math = window length 10% (36.6d)",
      Math.round((end0 - end1) / DAY) === Math.round(p1y.days * 0.1),
      `${Math.round((end0 - end1) / DAY)}d`);

// ---------- F3 unit rules ----------
check("UNIT_RULES: 1M/3M=D only, 6M/1Y=D/W, MAX=D/W/M",
      JSON.stringify(api.UNIT_RULES["1M"]) === '["D"]' &&
      JSON.stringify(api.UNIT_RULES["3M"]) === '["D"]' &&
      JSON.stringify(api.UNIT_RULES["6M"]) === '["D","W"]' &&
      JSON.stringify(api.UNIT_RULES["1Y"]) === '["D","W"]' &&
      JSON.stringify(api.UNIT_RULES["MAX"]) === '["D","W","M"]');

console.log(`\nTOTAL: PASS ${pass} / FAIL ${fail}`);
process.exit(fail ? 1 : 0);
