// 차트 계산 함수 테스트: F6 거래량 등락 색상 + HKD 표기 (2026-08-05)
// 실행: node src/tests/test_chart.mjs (test_premium.py TestPanningHarness가 호출)
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import path from "path";
import vm from "vm";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const code = readFileSync(path.join(ROOT, "web", "app.js"), "utf-8");

// 속성을 실제로 보관하는 스텁 (highlightVolBar가 y/height를 읽어 링을 맞춘다)
const stubEl = () => {
  const attrs = {};
  return {
    attrs, style: {},
    setAttribute(k, v) { attrs[k] = String(v); },
    getAttribute(k) { return k in attrs ? attrs[k] : null; },
    addEventListener() {}, appendChild() {}, insertBefore() {},
    classList: { toggle() {}, remove() {}, add() {} },
  };
};
const sandbox = {
  document: {
    getElementById: () => null, querySelector: () => null, querySelectorAll: () => [],
    createElement: stubEl, createElementNS: stubEl,
    documentElement: { getAttribute: () => null, setAttribute() {} },
    body: { getAttribute: () => null },
  },
  window: { matchMedia: () => ({ matches: false, addEventListener() {} }) },
  localStorage: { getItem: () => null, setItem() {} },
  fetch: () => Promise.reject(new Error("stub")),
  requestAnimationFrame: (f) => f(),
  console, Date, Math, JSON,
};
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
const { volBarColor, fmtLocalPrice, aggregate, state, highlightVolBar } = sandbox;

const fails = [];
function check(name, cond, detail = "") {
  console.log((cond ? "PASS" : "FAIL"), name, detail);
  if (!cond) fails.push(name);
}

// ---- F6 거래량 색상 분기 (전일 종가 대비) ----
check("상승 -> 빨강(--pos)", JSON.stringify(volBarColor(100, 101)) === '["--pos","상승"]');
check("하락 -> 파랑(--neg)", JSON.stringify(volBarColor(100, 99)) === '["--neg","하락"]');
check("보합 -> 회색(--zero-line)", JSON.stringify(volBarColor(100, 100)) === '["--zero-line","보합"]');
check("직전값 없음(윈도우 첫 포인트) -> 회색/비교불가",
  volBarColor(null, 100)[0] === "--zero-line" && volBarColor(null, 100)[1] === "비교불가");
check("현재값 없음 -> 회색/비교불가", volBarColor(100, null)[0] === "--zero-line");

// ---- 실데이터 표본 5일: 색상 = 원천 종가 등락과 일치 (BABA 원주 시리즈) ----
let rows = [];
try {
  rows = JSON.parse(readFileSync(
    path.join(ROOT, "web", "data", "history", "BABA.json"), "utf-8")).rows;
} catch (e) { /* 데이터 없으면 아래 체크 스킵 */ }
if (rows.length > 10) {
  const sample = rows.slice(-6); // 직전값 필요해서 6개
  let ok = true;
  for (let i = 1; i < sample.length; i++) {
    const [color] = volBarColor(sample[i - 1].p_local, sample[i].p_local);
    const diff = sample[i].p_local - sample[i - 1].p_local;
    const expected = diff > 0 ? "--pos" : diff < 0 ? "--neg" : "--zero-line";
    if (color !== expected) ok = false;
  }
  check("BABA 실데이터 표본 5일: 색상 = 원천 종가 등락 일치", ok);
  // 이월 포인트(vol null)는 바를 그리지 않음 - 데이터 계약 확인
  const ffRow = rows.find(r => r.ff_local);
  check("이월 포인트 vol_local=null (바 미표시 계약)",
    !ffRow || ffRow.vol_local === null);
} else {
  console.log("SKIP BABA 실데이터 표본 (히스토리 없음 - fetch 후 재실행)");
}

// ---- HKD 표기 ----
check("HKD 가격 표기", fmtLocalPrice(128.5, "HKD") === "HK$128.50");
check("KRW 표기 회귀 없음", fmtLocalPrice(1567000, "KRW") === "1,567,000" + "원");
check("TWD 표기 회귀 없음", fmtLocalPrice(2370, "TWD").indexOf("TWD") > 0);

// ---- 주 단위 집계의 가격 승계 (색상 비교 기반) ----
if (rows.length > 30) {
  const weekly = aggregate(rows, "W");
  const last = weekly[weekly.length - 1];
  check("주 집계 포인트에 p_local 존재 (직전 기간 대비 색상 계산 가능)",
    typeof last.p_local === "number");
}

// ---- 2026-08-05 작업 1: 거래량 기본 시리즈 = 원주 ----
check("거래량 기본 시리즈 = local(원주)", state.volSeries === "local");
check("거래량 패널 기본 켜짐 (사용자 지시 2026-08-05: 토글 없이 바로 보이게)", state.vol === true);

// ---- 2026-08-05 작업 2: 호버-거래량 바 연동 ----
function mkBar(y, h) {
  const b = stubEl();
  b.setAttribute("y", y);
  b.setAttribute("height", h);
  return b;
}
state.volBars = [mkBar(10, 40), null, mkBar(20, 30), mkBar(5, 45)]; // idx 1 = 이월(바 없음)
const ring = stubEl();
state.volFocus = { ring, bw: 8, xOf: (i) => 100 + i * 20, top: 8, bottom: 82 };

highlightVolBar(2);
check("강조 대상 바 불투명도 1", state.volBars[2].style.opacity === "1");
check("나머지 바 감쇠 0.35",
  state.volBars[0].style.opacity === "0.35" && state.volBars[3].style.opacity === "0.35");
check("포커스 링 표시 + 위치가 대상 바에 맞음",
  ring.style.display === "" &&
  Math.abs(parseFloat(ring.getAttribute("x")) - (140 - 4 - 1.5)) < 0.01 &&
  Math.abs(parseFloat(ring.getAttribute("y")) - (20 - 1.5)) < 0.01 &&
  Math.abs(parseFloat(ring.getAttribute("height")) - (30 + 3)) < 0.01);
check("링은 fill 없음(등락 색 의미 보존)", ring.getAttribute("fill") === null ||
  ring.getAttribute("fill") === "none");
check("hoverIdx 상태 반영", state.hoverIdx === 2);

highlightVolBar(1); // 이월 포인트(바 없음)
check("이월 포인트 호버: 링 숨김", ring.style.display === "none");

highlightVolBar(null);
check("강조 해제: 전 바 불투명도 복원 + 링 숨김",
  state.volBars[0].style.opacity === "1" && state.volBars[2].style.opacity === "1" &&
  ring.style.display === "none" && state.hoverIdx === null);

state.volBars = null; state.volFocus = null;
let threw = false;
try { highlightVolBar(3); } catch (e) { threw = true; }
check("거래량 패널 없을 때(토글 꺼짐) 안전 무시", !threw);

console.log("---");
console.log("FAIL", fails.length, "건");
process.exit(fails.length ? 1 : 0);
