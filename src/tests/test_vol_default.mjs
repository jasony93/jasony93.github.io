// 거래량 기본 표시(vol: true) 회귀 테스트 (2026-08-05 사용자 지시로 기본값 전환).
//
// 점검 범위: (a) 거래량 데이터 없는 심볼 (b) 주/월 단위 초기 진입
//            (d) 이월 포인트 (e) 패닝·호버 상호작용 + 단기 종목
// 실행: node src/tests/test_vol_default.mjs (test_premium.py가 호출)
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import path from "path";
import vm from "vm";

const SRC = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const code = readFileSync(path.join(SRC, "web", "app.js"), "utf-8");

class N {
  constructor(tag) {
    this.tag = (tag || "").toLowerCase();
    this.children = []; this.attrs = {}; this.style = {};
    this.listeners = {}; this.className = ""; this.textContent = "";
    this.clientWidth = 800;
    const self = this;
    this.classList = {
      add(c) { if (!self._c().includes(c)) self.className = (self.className + " " + c).trim(); },
      remove(c) { self.className = self._c().filter(x => x !== c).join(" "); },
      toggle(c, on) { on ? this.add(c) : this.remove(c); },
      contains(c) { return self._c().includes(c); },
    };
  }
  // SVG 요소는 class를 attribute로 설정하므로 둘 다 합쳐 본다
  _c() {
    return (this.className + " " + (this.attrs["class"] || ""))
      .split(/\s+/).filter(Boolean);
  }
  appendChild(n) { this.children.push(n); return n; }
  insertBefore(n, ref) {
    const i = this.children.indexOf(ref);
    this.children.splice(i < 0 ? this.children.length : i, 0, n); return n;
  }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  removeAttribute(k) { delete this.attrs[k]; }
  set innerHTML(v) { if (v === "") this.children = []; }
  get innerHTML() { return ""; }
  addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); }
  dispatch(t, e) { (this.listeners[t] || []).slice().forEach(f => f(e)); }
  getBoundingClientRect() { return { width: this.clientWidth, left: 0, top: 0 }; }
  setPointerCapture() {}
  querySelector(sel) { return this.queryAll(sel)[0] || null; }
  querySelectorAll(sel) { return this.queryAll(sel); }
  queryAll(sel) {
    const out = [];
    const match = (n) => sel === "svg" ? n.tag === "svg"
      : sel.startsWith(".") ? n._c().includes(sel.slice(1)) : false;
    const walk = (n) => { for (const c of n.children) { if (match(c)) out.push(c); walk(c); } };
    walk(this); return out;
  }
  allText() {
    let s = this.textContent || "";
    for (const c of this.children) s += " " + c.allText();
    return s;
  }
}

const wrap = new N("div"); wrap.className = "chart-wrap";
const toolbarHost = new N("div");
const tabs = ["1M", "3M", "6M", "1Y", "MAX"].map(k => {
  const b = new N("button"); b.className = "period-tab"; b.textContent = k; return b;
});
const sandbox = {
  document: {
    getElementById: (id) => (id === "detail-chart" ? wrap : null),
    querySelector: (s) => (s === ".period-tabs" ? toolbarHost
      : s === ".chart-tooltip" ? wrap.querySelector(".chart-tooltip") : null),
    querySelectorAll: (s) => (s === ".period-tab" ? tabs : []),
    createElement: (t) => new N(t), createElementNS: (ns, t) => new N(t),
    documentElement: { getAttribute: () => null, setAttribute() {} },
    body: { getAttribute: () => null },
  },
  window: { matchMedia: () => ({ matches: false, addEventListener() {} }) },
  localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
  fetch: () => Promise.reject(new Error("stub")),
  requestAnimationFrame: (f) => { f(); return 0; },
  console, Date, Math, JSON,
};
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
const { state, drawDetailChart, aggregate, computeWindow, highlightVolBar } = sandbox;

const fails = [];
const ck = (n, c, d = "") => {
  console.log((c ? "PASS " : "FAIL ") + n + (d ? "  " + d : ""));
  if (!c) fails.push(n);
};

const DATA = path.join(SRC, "web", "data", "history");
let haveData = true;
const load = (id) => {
  try { return JSON.parse(readFileSync(path.join(DATA, id + ".json"), "utf-8")).rows; }
  catch (e) { haveData = false; return null; }
};
const reset = (rows, stock) => {
  wrap.children = []; wrap.className = "chart-wrap";
  state.rows = rows; state.stock = stock;
  state.period = "1Y"; state.unit = "D"; state.endMs = null;
  state.sma20 = false; state.sma60 = false; state.avg = false;
  state.dragging = false; state.hoverIdx = null;
};

// ---- 기본값 계약 ----
ck("vol 기본값 = true (사용자 지시: 토글 없이 거래량 표시)", state.vol === true);
ck("volSeries 기본값 = local(원주)", state.volSeries === "local");
ck("SMA20/60·기간 평균은 기본 꺼짐 유지 (공통 원칙 1)",
  state.sma20 === false && state.sma60 === false && state.avg === false);

const tsm = load("TSM");
if (!haveData || !tsm) {
  console.log("SKIP 실데이터 없음 - fetch_data.py 실행 후 재시도");
  console.log("---");
  console.log("FAIL", fails.length, "건");
  process.exit(fails.length ? 1 : 0);
}

// ---- 최초 렌더 ----
reset(tsm, { id: "TSM", local_currency: "TWD", fx_label: "USD/TWD" });
drawDetailChart();
ck(`최초 렌더에서 vol-bar 생성 (${wrap.querySelectorAll(".vol-bar").length}개)`,
  wrap.querySelectorAll(".vol-bar").length > 0);
ck("거래량 패널 SVG 1개", wrap.querySelectorAll(".vol-panel").length === 1);
ck("색상 기준 안내 문구 노출", wrap.allText().includes("거래량 색:"));

// ---- (a) 거래량 데이터 없는 심볼 ----
reset(tsm.slice(-60).map(r => ({ ...r, vol_dr: null, vol_local: null })),
  { id: "X", local_currency: "TWD", fx_label: "USD/TWD" });
let threw = null;
try { drawDetailChart(); } catch (e) { threw = e; }
ck("(a) 거래량 전무 심볼 렌더 예외 없음", threw === null, threw ? String(threw) : "");
ck("(a) 패널 미생성 (hasVolumeData 분기)",
  wrap.querySelectorAll(".vol-panel").length === 0);
ck("(a) 프리미엄 차트는 정상 렌더", wrap.querySelectorAll("svg").length >= 1);

// ---- (b) 주/월 단위 초기 진입 ----
for (const [unit, period] of [["W", "1Y"], ["M", "MAX"]]) {
  reset(tsm, { id: "TSM", local_currency: "TWD", fx_label: "USD/TWD" });
  state.unit = unit; state.period = period;
  threw = null;
  try { drawDetailChart(); } catch (e) { threw = e; }
  ck(`(b) ${unit} 단위 초기 렌더 예외 없음`, threw === null, threw ? String(threw) : "");
  ck(`(b) ${unit} 단위 거래량 바 생성`, wrap.querySelectorAll(".vol-bar").length > 0);
  ck(`(b) ${unit} 단위 '기간 합계' 라벨`, wrap.allText().includes("기간 합계"));
}

// ---- (d) 이월 포인트 ----
const kb = load("KB");
if (kb) {
  reset(kb, { id: "KB", local_currency: "KRW", fx_label: "USD/KRW" });
  state.period = "3M";
  drawDetailChart();
  const shown = computeWindow(aggregate(kb, "D")).data;
  const nulls = shown.filter(r => r.vol_local === null || r.vol_local === undefined).length;
  const bars = wrap.querySelectorAll(".vol-bar").length;
  ck(`(d) 이월 포인트 바 미생성 (${shown.length}-${nulls}=${bars})`,
    bars === shown.length - nulls);
  ck("(d) volBars 인덱스 정합", state.volBars.length === shown.length);
  ck(`(d) 이월 슬롯 null 유지`, state.volBars.filter(x => x === null).length === nulls);
}

// ---- (e) 패닝·호버 상호작용 ----
reset(tsm, { id: "TSM", local_currency: "TWD", fx_label: "USD/TWD" });
drawDetailChart();
const before = wrap.querySelectorAll(".vol-bar").length;
highlightVolBar(3);
ck("(e) 호버 강조: 대상 불투명도 1",
  !state.volBars[3] || state.volBars[3].style.opacity === "1");
ck("(e) 호버 강조: 나머지 감쇠",
  state.volBars.filter(x => x && x.style.opacity === "0.35").length > 0);
const ev = (x) => ({ clientX: x, clientY: 100, button: 0, pointerId: 1,
  pointerType: "mouse", preventDefault() {} });
wrap.dispatch("pointerdown", ev(400));
wrap.dispatch("pointermove", ev(500));
wrap.dispatch("pointerup", ev(500));
ck(`(e) 패닝 후 거래량 바 유지 (${before} -> ${wrap.querySelectorAll(".vol-bar").length})`,
  wrap.querySelectorAll(".vol-bar").length > 0);
ck("(e) 드래그 시작 시 강조 해제", state.hoverIdx === null);

// ---- 단기 종목 ----
const skhy = load("SKHY");
if (skhy) {
  reset(skhy, { id: "SKHY", local_currency: "KRW", fx_label: "USD/KRW" });
  threw = null;
  try { drawDetailChart(); } catch (e) { threw = e; }
  ck("단기 종목(SKHY) 초기 렌더 예외 없음", threw === null, threw ? String(threw) : "");
  ck("단기 종목 거래량 바 생성", wrap.querySelectorAll(".vol-bar").length > 0);
}

console.log("---");
console.log("FAIL", fails.length, "건");
process.exit(fails.length ? 1 : 0);
