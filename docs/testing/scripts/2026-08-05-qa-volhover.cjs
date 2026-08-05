/* 거래량 UX 독립 검증 (2026-08-05 개선분)
 * - 기본 시리즈 = 원주(local), 버튼 순서 원주 우선
 * - 호버 강조: 대상 opacity 1 / 나머지 0.35, 포커스 링 fill 없음·기하 일치
 * - 이월 포인트 링 숨김, 토글 꺼짐 무시, 강조 해제
 * - 주/월 집계 바 강조
 * - 툴팁 문구: 등락 표시 + 금지 표현 없음
 * 표본: SHG(DR)·WF(원주)·PKX 주 단위 - 개발팀/직전 회차와 다른 종목
 */
"use strict";
const fs = require("fs");
const path = require("path");
const ROOT = "d:\\personal\\Claude \ud504\ub85c\uc81d\ud2b8\\Stock tools";

class FakeNode {
  constructor(tag) {
    this.tag = (tag || "").toLowerCase();
    this.children = []; this.attrs = {}; this.style = {};
    this.className = ""; this.textContent = ""; this.clientWidth = 800;
    this.listeners = {};
    const self = this;
    this.classList = {
      add(c) { if (!self._c().includes(c)) self.className = (self.className + " " + c).trim(); },
      remove(c) { self.className = self._c().filter(x => x !== c).join(" "); },
      toggle(c, on) { on ? this.add(c) : this.remove(c); },
      contains(c) { return self._c().includes(c); },
    };
  }
  _c() { return this.className.split(/\s+/).filter(Boolean); }
  appendChild(n) { this.children.push(n); return n; }
  insertBefore(n, ref) { const i = this.children.indexOf(ref); this.children.splice(i < 0 ? this.children.length : i, 0, n); return n; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); }
  dispatch(t, ev) { (this.listeners[t] || []).slice().forEach(f => f(ev)); }
  set innerHTML(v) { if (v === "") this.children = []; }
  get innerHTML() { return ""; }
  getBoundingClientRect() { return { width: 800, left: 0, top: 0, right: 800, bottom: 320 }; }
  setPointerCapture() {}
  querySelector(sel) {
    const match = n => (sel === "svg" && n.tag === "svg") || (sel.startsWith(".") && n._c().includes(sel.slice(1)));
    const walk = n => { for (const c of n.children) { if (match(c)) return c; const d = walk(c); if (d) return d; } return null; };
    return walk(this);
  }
  querySelectorAll(sel) {
    const out = []; const match = n => sel.startsWith(".") ? n._c().includes(sel.slice(1)) : n.tag === sel;
    const walk = n => n.children.forEach(c => { if (match(c)) out.push(c); walk(c); });
    walk(this); return out;
  }
  get offsetWidth() { return 100; }
}
global.document = {
  documentElement: { getAttribute: () => null, setAttribute: () => {} },
  getElementById: () => null, querySelector: () => null, querySelectorAll: () => [],
  body: { getAttribute: () => null },
  createElement: t => new FakeNode(t), createElementNS: (ns, t) => new FakeNode(t),
};
global.window = {};

const src = fs.readFileSync(path.join(ROOT, "src", "web", "app.js"), "utf8");
const api = eval(src + "\n;({state, drawVolumePanel, highlightVolBar, attachTooltip, aggregate, volBarColor})");

let pass = 0, fail = 0;
const check = (n, c, d) => { console.log(`[${c ? "PASS" : "FAIL"}] ${n}  ${d || ""}`); c ? pass++ : fail++; };
const rows = tid => JSON.parse(fs.readFileSync(path.join(ROOT, "src", "web", "data", "history", tid + ".json"), "utf8")).rows;

// ---- 1. 기본 시리즈 = 원주 ----
check("state 기본 volSeries = 'local' (원주)", api.state.volSeries === "local", api.state.volSeries);
check("거래량 토글 기본 꺼짐 유지", api.state.vol === false);
const btnOrder = (src.match(/\[\[\s*"local",\s*"원주"\s*\],\s*\[\s*"dr",\s*"DR"\s*\]\]/) ||
                  src.match(/\[\["local", "원주"\], \["dr", "DR"\]\]/));
check("시리즈 버튼 순서 = 원주 우선", !!btnOrder, btnOrder ? "local, dr" : "순서 확인 실패");

// ---- 2. 호버 강조 (SHG DR / WF 원주) ----
function renderPanel(tid, series, unit, n) {
  api.state.volSeries = series; api.state.unit = unit || "D"; api.state.vol = true;
  const all = rows(tid);
  const data = (unit === "W" ? api.aggregate(all, "W") : all).slice(-n);
  const wrap = new FakeNode("div");
  api.drawVolumePanel(wrap, data, i => 46 + i * 30, 800, 46, 12);
  return { wrap, data };
}
for (const [tid, series, label] of [["SHG", "dr", "DR"], ["WF", "local", "원주"]]) {
  const { data } = renderPanel(tid, series, "D", 15);
  const bars = api.state.volBars;
  const focus = api.state.volFocus;
  check(`${tid}(${label}) volBars 배열 길이 = 데이터 수`, bars.length === data.length, `${bars.length}/${data.length}`);
  // 강조 전: 링 숨김
  check(`${tid} 초기 상태 링 숨김`, focus.ring.style.display === "none");
  // 임의 인덱스 강조
  const target = 7;
  api.highlightVolBar(target);
  const opac = bars.map(b => (b ? b.style.opacity : null));
  const okOpac = opac.every((o, i) => o === null || o === (i === target ? "1" : "0.35"));
  check(`${tid} 강조 시 대상 opacity 1 / 나머지 0.35`, okOpac,
        `target=${opac[target]} others=${[...new Set(opac.filter((o,i)=>i!==target&&o))].join(",")}`);
  // 링 기하 = 대상 바 + 패딩, fill 없음
  const bar = bars[target];
  const ring = focus.ring;
  const pad = 1.5;
  const geomOk = Math.abs(parseFloat(ring.attrs.x) - (focus.xOf(target) - focus.bw / 2 - pad)) < 1e-6 &&
                 Math.abs(parseFloat(ring.attrs.width) - (focus.bw + pad * 2)) < 1e-6 &&
                 Math.abs(parseFloat(ring.attrs.y) - (parseFloat(bar.attrs.y) - pad)) < 1e-6 &&
                 Math.abs(parseFloat(ring.attrs.height) - (parseFloat(bar.attrs.height) + pad * 2)) < 1e-6;
  check(`${tid} 포커스 링 기하 = 대상 바 + 패딩 1.5`, geomOk && ring.style.display === "");
  check(`${tid} 포커스 링 fill 없음 (등락 색상 의미 보존)`, ring.attrs.fill === "none" && !!ring.attrs.stroke,
        `fill=${ring.attrs.fill} stroke=${ring.attrs.stroke}`);
  // 바 자체 색상(fill)이 강조로 변하지 않는지
  const fillsBefore = bars.filter(Boolean).map(b => b.attrs.fill);
  api.highlightVolBar(target === 0 ? 1 : 0);
  const fillsAfter = bars.filter(Boolean).map(b => b.attrs.fill);
  check(`${tid} 강조 이동해도 바 fill(등락 색) 불변`, JSON.stringify(fillsBefore) === JSON.stringify(fillsAfter));
  // 해제
  api.highlightVolBar(null);
  check(`${tid} 해제 시 전 바 opacity 1 + 링 숨김`,
        bars.filter(Boolean).every(b => b.style.opacity === "1") && focus.ring.style.display === "none");
}

// ---- 3. 이월 포인트 경계 (BABA 원주: 이월일 포함 구간) ----
{
  const all = rows("BABA");
  const ffIdx = all.findIndex((r, i) => i > all.length - 120 && r.vol_local === null);
  const start = Math.max(0, ffIdx - 5);
  api.state.volSeries = "local"; api.state.unit = "D"; api.state.vol = true;
  const data = all.slice(start, start + 12);
  const wrap = new FakeNode("div");
  api.drawVolumePanel(wrap, data, i => 46 + i * 30, 800, 46, 12);
  const localFf = data.findIndex(r => r.vol_local === null);
  check("BABA 이월일 포함 구간: 해당 인덱스 volBars = null (바 없음)",
        localFf >= 0 && api.state.volBars[localFf] === null, `ffIdx=${localFf}`);
  api.highlightVolBar(localFf);
  check("이월 포인트 강조 시 링 숨김 (바 없음)", api.state.volFocus.ring.style.display === "none");
  // 이월 강조 시 다른 바들은 감쇠되는가 (idx가 유효하므로 감쇠는 적용)
  const others = api.state.volBars.filter(Boolean).map(b => b.style.opacity);
  check("이월 강조 시 나머지 바 감쇠는 적용 (0.35)", others.every(o => o === "0.35"), others[0]);
  api.highlightVolBar(null);
}

// ---- 4. 토글 꺼짐 무시 ----
{
  api.state.volBars = null; api.state.volFocus = null; api.state.vol = false;
  let threw = false;
  try { api.highlightVolBar(3); } catch (e) { threw = true; }
  check("토글 꺼짐(참조 없음) 상태에서 highlightVolBar 무해", !threw);
}

// ---- 5. 주 단위 집계 바 강조 (PKX) ----
{
  const { data } = renderPanel("PKX", "local", "W", 10);
  const bars = api.state.volBars;
  check("PKX 주 단위: 집계 포인트 수 = 바 배열 수", bars.length === data.length);
  api.highlightVolBar(4);
  check("주 집계 바 강조 동작 (링 표시 + 대상 opacity 1)",
        api.state.volFocus.ring.style.display === "" && bars[4].style.opacity === "1");
  api.highlightVolBar(null);
}

// ---- 6. 툴팁 문구 (등락 표기 + 금지 표현) ----
{
  api.state.vol = true; api.state.volSeries = "local"; api.state.unit = "D";
  api.state.stock = { id: "SHG", local_currency: "KRW", fx_label: "USD/KRW" };
  const all = rows("SHG");
  const data = all.slice(-10);
  const wrap = new FakeNode("div");
  const svg = new FakeNode("svg");
  wrap.appendChild(svg);
  // 실제 렌더와 동일한 좌표계: xOf(i) = padL + i/(n-1)*plotW (W=800, padL=46, plotW=700)
  const padL = 46, plotW = 700, W = 800;
  const xOf = i => padL + (i / (data.length - 1)) * plotW;
  api.drawVolumePanel(wrap, data, xOf, W, padL, 12);
  const tooltip = new FakeNode("div");
  const hoverLine = new FakeNode("line"), hoverDot = new FakeNode("circle");
  api.attachTooltip(svg, wrap, data, xOf, () => 100, hoverLine, hoverDot, tooltip, W, padL, plotW);
  // 마지막에서 두 번째 포인트 위 호버 (clientX = 해당 포인트의 화면 x)
  const idx = data.length - 2;
  svg.dispatch("mousemove", { clientX: xOf(idx) });
  const text = tooltip.children.map(c => c.textContent).join(" | ");
  const priceUp = data[idx].p_local > data[idx - 1].p_local;
  const expectDir = priceUp ? "상승" : (data[idx].p_local < data[idx - 1].p_local ? "하락" : "보합");
  check("툴팁에 거래량 + 전일 종가 대비 등락 표기",
        /거래량\(원주\)/.test(text) && text.includes("전일 종가 대비 " + expectDir), text.slice(0, 200));
  const banned = ["매수 우위", "매도 우위", "체결강도", "매수세", "매도세"];
  check("툴팁 문구에 금지 표현 없음", !banned.some(b => text.includes(b)));
  check("호버 시 거래량 바 강조 연동됨", api.state.hoverIdx === idx, `hoverIdx=${api.state.hoverIdx}`);
}

console.log(`\nTOTAL: PASS ${pass} / FAIL ${fail}`);
process.exit(fail ? 1 : 0);
