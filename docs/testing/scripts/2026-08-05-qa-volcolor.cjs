/* F6 거래량 색상 독립 검증: 출하 app.js의 volBarColor + drawVolumePanel을
 * FakeDOM으로 실행해 (1) 분기 로직 (2) 실데이터 바 색상 (3) 범례 문구
 * (4) 이월 바 없음 (5) 금지 표현을 검증한다. 표본: KEP·BABA (개발팀과 다른 종목). */
"use strict";
const fs = require("fs");
const path = require("path");

const ROOT = "d:\\personal\\Claude \ud504\ub85c\uc81d\ud2b8\\Stock tools";

class FakeNode {
  constructor(tag) {
    this.tag = (tag || "").toLowerCase();
    this.children = []; this.attrs = {}; this.style = {};
    this.className = ""; this.textContent = "";
    this.clientWidth = 800;
    const self = this;
    this.classList = { add() {}, remove() {}, toggle() {}, contains() { return false; } };
  }
  appendChild(n) { this.children.push(n); return n; }
  insertBefore(n) { this.children.push(n); return n; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  addEventListener() {}
  set innerHTML(v) { if (v === "") this.children = []; }
  get innerHTML() { return ""; }
  getBoundingClientRect() { return { width: 800, left: 0, top: 0, right: 800 }; }
  querySelector() { return null; }
  querySelectorAll() { return []; }
}
global.document = {
  documentElement: { getAttribute: () => null, setAttribute: () => {} },
  getElementById: () => null, querySelector: () => null, querySelectorAll: () => [],
  body: { getAttribute: () => null },
  createElement: (t) => new FakeNode(t),
  createElementNS: (ns, t) => new FakeNode(t),
};
global.window = {};

const src = fs.readFileSync(path.join(ROOT, "src", "web", "app.js"), "utf8");
const api = eval(src + "\n;({volBarColor, drawVolumePanel, state})");

let pass = 0, fail = 0;
function check(name, cond, detail) {
  console.log(`[${cond ? "PASS" : "FAIL"}] ${name}  ${detail || ""}`);
  cond ? pass++ : fail++;
}

// ---- 1. 분기 로직 (경계 포함) ----
check("상승 -> --pos(빨강)", api.volBarColor(100, 101)[0] === "--pos");
check("하락 -> --neg(파랑)", api.volBarColor(101, 100)[0] === "--neg");
check("보합 -> --zero-line(회색)", api.volBarColor(100, 100)[0] === "--zero-line" &&
      api.volBarColor(100, 100)[1] === "\ubcf4\ud569");
check("prev null(첫 포인트/비교불가) -> 회색", api.volBarColor(null, 100)[0] === "--zero-line");
check("cur null -> 회색", api.volBarColor(100, null)[0] === "--zero-line");
check("미세 상승(0.01)도 빨강", api.volBarColor(100, 100.01)[0] === "--pos");

// ---- 2. 실데이터 바 색상 (KEP DR 최근 20일 + BABA 원주 최근 20일) ----
function loadRows(tid) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, "src", "web", "data", "history", tid + ".json"), "utf8")).rows;
}
function panelRects(rows, seriesKey, priceKey) {
  api.state.volSeries = seriesKey === "vol_dr" ? "dr" : "local";
  api.state.unit = "D";
  const wrap = new FakeNode("div");
  const data = rows.slice(-20);
  api.drawVolumePanel(wrap, data, (i) => 46 + i * 30, 800, 46, 12);
  const svg = wrap.children[0];
  const rects = svg.children.filter((c) => c.tag === "rect");
  const note = wrap.children.find((c) => c.className && c.className.includes("vol-color-note"));
  return { data, rects, note };
}
function expectedColors(data, volKey, priceKey) {
  const out = [];
  data.forEach((r, i) => {
    if (r[volKey] === null || r[volKey] === undefined) return; // no bar
    const prev = i > 0 ? data[i - 1][priceKey] : null;
    let c = "--zero-line";
    if (prev !== null && prev !== undefined) {
      if (r[priceKey] > prev) c = "--pos";
      else if (r[priceKey] < prev) c = "--neg";
    }
    out.push(c);
  });
  return out;
}
for (const [tid, volKey, priceKey] of [["KEP", "vol_dr", "p_dr"], ["BABA", "vol_local", "p_local"]]) {
  const rows = loadRows(tid);
  const { data, rects, note } = panelRects(rows, volKey, priceKey);
  const exp = expectedColors(data, volKey, priceKey);
  const got = rects.map((r) => (r.attrs.fill.match(/var\((.*)\)/) || [])[1]);
  const carryCount = data.filter((r) => r[volKey] === null || r[volKey] === undefined).length;
  check(`${tid} ${volKey} 최근 20일: 바 수 = 실거래일 수 (이월 ${carryCount}일 바 없음)`,
        rects.length === exp.length && rects.length === 20 - carryCount,
        `bars=${rects.length}`);
  check(`${tid} 색상 배열 독립 산출과 완전 일치`, JSON.stringify(got) === JSON.stringify(exp),
        `up=${got.filter(c=>c==="--pos").length} down=${got.filter(c=>c==="--neg").length} gray=${got.filter(c=>c==="--zero-line").length}`);
  check(`${tid} 범례 문구 = 확정 문구`,
        note && note.textContent.indexOf("\uac70\ub798\ub7c9 \uc0c9: \ud574\ub2f9 \uc2dc\uc7a5 \uc885\uac00\uc758 \uc804\uc77c \ub300\ube44 \uc0c1\uc2b9(\ube68\uac15)/\ud558\ub77d(\ud30c\ub791)/\ubcf4\ud569\u00b7\uc774\uc6d4(\ud68c\uc0c9)") === 0,
        note ? note.textContent : "no note");
}

// ---- 3. 주 단위: 직전 기간 대비 문구 ----
api.state.unit = "W";
{
  const rows = loadRows("KEP");
  const wrap = new FakeNode("div");
  api.state.volSeries = "dr";
  // aggregate는 이미 검증됨 - 주 데이터로 패널만
  const agg = eval(src + "\n;aggregate")(rows, "W").slice(-8);
  api.drawVolumePanel(wrap, agg, (i) => 46 + i * 30, 800, 46, 12);
  const note = wrap.children.find((c) => c.className && c.className.includes("vol-color-note"));
  check("주 단위 범례에 '직전 기간 대비' 부기", note && note.textContent.includes("\uc9c1\uc804 \uae30\uac04 \ub300\ube44"));
}

// ---- 4. 금지 표현 (사용자 노출 문자열) ----
const uiStrings = src.match(/"[^"\n]*"/g).filter((s) => !s.startsWith('"--') && !s.includes("use strict"));
const banned = ["\ub9e4\uc218 \uc6b0\uc704", "\ub9e4\ub3c4 \uc6b0\uc704", "\uccb4\uacb0\uac15\ub3c4"];
const hits = uiStrings.filter((s) => banned.some((b) => s.includes(b)));
check("app.js 사용자 노출 문자열에 매수/매도 우위·체결강도 없음", hits.length === 0, hits.join(","));

console.log(`\nTOTAL: PASS ${pass} / FAIL ${fail}`);
process.exit(fail ? 1 : 0);
