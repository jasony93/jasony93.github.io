// F1 패닝 드래그 시퀀스 회귀 테스트 (Node 하니스)
//
// 2026-08-04 사용자 보고 버그 재현 구조: 드래그 중 매 move마다 재렌더가 일어나
// svg가 교체된다. 리스너·캡처가 svg에 있으면 첫 틱 이후 제스처가 끊긴다.
// 본 하니스는 requestAnimationFrame을 동기 실행(최대 적대 조건)으로 두고
// pointerdown -> move -> move -> up 시퀀스 후 윈도우가 누적 이동했는지 검증한다.
//
// 실행: node src/tests/test_panning.mjs  (test_premium.py의 TestPanningHarness가 호출)
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import path from "path";
import vm from "vm";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const code = readFileSync(path.join(ROOT, "web", "app.js"), "utf-8");

// ---- 최소 가짜 DOM ----
class FakeNode {
  constructor(tag) {
    this.tag = (tag || "").toLowerCase();
    this.children = [];
    this.attrs = {};
    this.style = {};
    this.listeners = {};
    this.className = "";
    this.textContent = "";
    this.clientWidth = 800;
    const self = this;
    this.classList = {
      add(c) { if (!self._cls().includes(c)) self.className = (self.className + " " + c).trim(); },
      remove(c) { self.className = self._cls().filter(x => x !== c).join(" "); },
      toggle(c, on) { on ? this.add(c) : this.remove(c); },
      contains(c) { return self._cls().includes(c); },
    };
  }
  _cls() { return this.className.split(/\s+/).filter(Boolean); }
  appendChild(n) { this.children.push(n); return n; }
  insertBefore(n, ref) {
    const i = this.children.indexOf(ref);
    this.children.splice(i < 0 ? this.children.length : i, 0, n);
    return n;
  }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  removeAttribute(k) { delete this.attrs[k]; }
  set innerHTML(v) { if (v === "") this.children = []; }
  get innerHTML() { return ""; }
  addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); }
  dispatch(t, ev) { (this.listeners[t] || []).slice().forEach(f => f(ev)); }
  getBoundingClientRect() { return { width: 800, left: 0, top: 0, right: 800, bottom: 320 }; }
  setPointerCapture() {}
  querySelector(sel) {
    const match = (n) => (sel === "svg" && n.tag === "svg") ||
      (sel.startsWith(".") && n._cls().includes(sel.slice(1)));
    const walk = (n) => {
      for (const c of n.children) {
        if (match(c)) return c;
        const d = walk(c);
        if (d) return d;
      }
      return null;
    };
    return walk(this);
  }
  querySelectorAll() { return []; }
  closest() { return null; }
}

const wrap = new FakeNode("div");
wrap.className = "chart-wrap";
let drawCount = 0;

const sandbox = {
  document: {
    getElementById: (id) => (id === "detail-chart" ? wrap : null),
    querySelector: () => null,
    querySelectorAll: () => [],
    createElement: (t) => new FakeNode(t),
    createElementNS: (ns, t) => new FakeNode(t),
    documentElement: { getAttribute: () => null, setAttribute() {} },
    body: { getAttribute: () => null },
  },
  window: { matchMedia: () => ({ matches: false, addEventListener() {} }) },
  localStorage: { getItem: () => null, setItem() {} },
  fetch: () => Promise.reject(new Error("stub")),
  // 최대 적대 조건: rAF 즉시 동기 실행 -> 매 move마다 svg 교체
  requestAnimationFrame: (f) => { f(); return 0; },
  console, Date, Math, JSON,
};
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
const { state, drawDetailChart } = sandbox;

// 재렌더 횟수 추적
const origDraw = sandbox.drawDetailChart;
sandbox.drawDetailChart = function () { drawCount++; return origDraw(); };

const tsm = JSON.parse(readFileSync(
  path.join(ROOT, "web", "data", "history", "TSM.json"), "utf-8")).rows;

state.stock = { id: "TSM", local_currency: "TWD", fx_label: "USD/TWD" };
state.rows = tsm;
state.period = "1Y";
state.unit = "D";
state.endMs = null;

const fails = [];
function check(name, cond, detail = "") {
  console.log((cond ? "PASS" : "FAIL"), name, detail);
  if (!cond) fails.push(name);
}
function ev(x, y, extra) {
  return Object.assign({ clientX: x, clientY: y, button: 0, pointerId: 1,
    pointerType: "mouse", preventDefault() {}, key: null }, extra);
}

// ---- 초기 렌더 ----
origDraw();
const svg1 = wrap.querySelector("svg");
check("초기 렌더: svg 생성 + 패닝 활성", !!svg1 && state.pan.panEnabled === true);
const lastMs = state.pan.lastMs;
const plotW = state.pan.plotW;
const spanMs = state.pan.spanMs;
// CSS 렌더 폭(800px) 대비 뷰박스 좌표(W)의 스케일 - shiftByPx와 동일한 환산
const scale = state.pan.W / 800;

// ---- 마우스 드래그: down -> move(+100px, 재렌더 발생) -> move(+100px) -> up ----
wrap.dispatch("pointerdown", ev(400, 100));
check("드래그 시작: dragging=true", state.dragging === true &&
  wrap.classList.contains("panning"));
wrap.dispatch("pointermove", ev(500, 100)); // +100px -> 재렌더로 svg 교체됨
const afterFirst = state.endMs;
const expected1 = lastMs - (100 * scale / plotW) * spanMs;
check(`1차 이동: endMs ${afterFirst} ~= 기대 ${Math.round(expected1)}`,
  afterFirst !== null && Math.abs(afterFirst - expected1) < 3600 * 1000);
const svg2 = wrap.querySelector("svg");
check("재렌더로 svg 교체 확인 (적대 조건 성립)", svg2 !== svg1 && drawCount >= 1);

// 핵심 회귀: 교체 이후의 move도 계속 반영돼야 한다 (수정 전에는 여기서 실패)
wrap.dispatch("pointermove", ev(600, 100)); // 추가 +100px
const afterSecond = state.endMs;
const expected2 = lastMs - (200 * scale / plotW) * spanMs;
check(`2차 이동(재렌더 후 제스처 유지): endMs ${afterSecond} ~= 기대 ${Math.round(expected2)}`,
  afterSecond !== null && Math.abs(afterSecond - expected2) < 3600 * 1000);
check("이동 방향: 오른쪽 드래그 = 과거로", afterSecond < afterFirst);

wrap.dispatch("pointerup", ev(600, 100));
check("드래그 종료: dragging=false", state.dragging === false &&
  !wrap.classList.contains("panning"));

// ---- 경계 클램프: 대량 드래그 -> minEnd에서 멈춤 ----
wrap.dispatch("pointerdown", ev(400, 100));
for (let i = 0; i < 60; i++) wrap.dispatch("pointermove", ev(400 + (i + 1) * 700, 100));
wrap.dispatch("pointerup", ev(0, 0));
check(`경계 클램프: endMs ${state.endMs} = minEnd ${state.pan.minEnd}`,
  state.endMs === state.pan.minEnd);

// ---- "최신으로" 복귀 (endMs=null 재렌더) ----
state.endMs = null;
origDraw();
check("최신 복귀", state.pan.lastMs === lastMs && state.endMs === null);

// ---- 터치: 세로 스와이프 -> 스크롤 양보 (이동 없음) ----
wrap.dispatch("pointerdown", ev(400, 100, { pointerType: "touch" }));
wrap.dispatch("pointermove", ev(403, 180, { pointerType: "touch" })); // 세로 80px
check("터치 세로: 패닝 미개시", state.endMs === null && state.dragging === false);
wrap.dispatch("pointerup", ev(403, 180, { pointerType: "touch" }));

// ---- 터치: 가로 스와이프 -> 패닝 개시 ----
wrap.dispatch("pointerdown", ev(400, 100, { pointerType: "touch" }));
wrap.dispatch("pointermove", ev(430, 103, { pointerType: "touch" })); // 가로 30px
wrap.dispatch("pointermove", ev(480, 103, { pointerType: "touch" }));
check("터치 가로: 패닝 개시 + 이동", state.endMs !== null && state.dragging === true);
wrap.dispatch("pointerup", ev(480, 103, { pointerType: "touch" }));

// ---- MAX: 패닝 비활성 ----
state.endMs = null;
state.period = "MAX";
origDraw();
wrap.dispatch("pointerdown", ev(400, 100));
wrap.dispatch("pointermove", ev(700, 100));
check("MAX: 드래그해도 이동 없음", state.endMs === null && state.pan.panEnabled === false);
wrap.dispatch("pointerup", ev(700, 100));

// ---- 키보드 ----
state.period = "1Y";
origDraw();
wrap.dispatch("keydown", ev(0, 0, { key: "ArrowLeft" }));
check("키보드 좌: 윈도우 10% 과거 이동",
  state.endMs !== null && Math.abs((lastMs - state.endMs) - spanMs * 0.1) < 1000);
wrap.dispatch("keydown", ev(0, 0, { key: "ArrowRight" }));
check("키보드 우: 최신 복귀", state.endMs === null);

console.log("---");
console.log("FAIL", fails.length, "건");
process.exit(fails.length ? 1 : 0);
