/* ADR 프리미엄 트래커 - 프론트엔드 (프리렌더 하이드레이션, 의존성 없는 순수 JS)
 *
 * 페이지 HTML은 build_pages.py가 사전 생성한다 (SEO - 핵심 콘텐츠는 JS 없이 노출).
 * 이 스크립트는 그 위에 인터랙션만 붙인다:
 *   - 공통: 라이트/다크 테마 토글 (localStorage 유지)
 *   - 종목 상세(body[data-page="stock"]): 기간 탭 + SVG 차트 + 툴팁
 *     v2 (2026-08-04): F1 드래그 패닝, F3 일/주/월 단위, F5 SMA20/60·기간 평균,
 *     F6 거래량 서브패널. 전부 클라이언트 계산 - 데이터 파일은 그대로 소비.
 *
 * 데이터: data/history/<ID>.json (fetch_data.py 생성물). 페이지별 종목 정보는
 * 프리렌더된 <script id="page-data" type="application/json">에서 읽는다.
 */
"use strict";

var PERIODS = [
  { key: "1M", days: 31 },
  { key: "3M", days: 92 },
  { key: "6M", days: 183 },
  { key: "1Y", days: 366 },
  { key: "MAX", days: null }
];

/* F3 조합 규칙: 기간별 허용 단위 */
var UNIT_RULES = {
  "1M": ["D"], "3M": ["D"], "6M": ["D", "W"], "1Y": ["D", "W"],
  "MAX": ["D", "W", "M"]
};
var UNIT_LABELS = { D: "일", W: "주", M: "월" };
var DAY_MS = 86400000;

var state = {
  rows: null, stock: null,
  period: "1Y", unit: "D",
  endMs: null,              // F1 패닝 윈도우 끝 (null = 최신)
  sma20: false, sma60: false, avg: false,
  vol: true, volSeries: "local",    // 거래량 패널 기본 표시 + 기본 시리즈 = 원주 - 2026-08-05 사용자 지시
  dragging: false,
  hoverIdx: null                    // 호버 중인 포인트 인덱스 (거래량 바 강조 연동)
};

/* ---------- 유틸 ---------- */

function el(tag, cls, text) {
  var n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined && text !== null) n.textContent = text;
  return n;
}

function fmtPremium(v) {
  return (v > 0 ? "+" : "") + v.toFixed(2) + "%";
}

function premiumClass(v) { return v >= 0 ? "pos" : "neg"; }

function fmtNum(v, digits) {
  return v.toLocaleString("ko-KR", {
    minimumFractionDigits: digits, maximumFractionDigits: digits
  });
}

function fmtLocalPrice(v, currency) {
  if (currency === "KRW") return fmtNum(v, 0) + "원";
  if (currency === "HKD") return "HK$" + fmtNum(v, 2);
  return fmtNum(v, 1) + " TWD";
}

function fmtUsd(v) { return "$" + fmtNum(v, 2); }

function fmtVolume(v) {
  if (v === null || v === undefined) return "-";
  if (v >= 1e6) return fmtNum(v / 1e6, 1) + "백만 주";
  if (v >= 1e3) return fmtNum(v / 1e3, 0) + "천 주";
  return fmtNum(v, 0) + "주";
}

function dataRoot() {
  return document.body.getAttribute("data-root") || "";
}

function getJSON(url) {
  return fetch(url, { cache: "no-store" }).then(function (res) {
    if (!res.ok) throw new Error("HTTP " + res.status + " (" + url + ")");
    return res.json();
  });
}

function dateMs(iso) { return new Date(iso + "T00:00:00Z").getTime(); }

/* ---------- 테마 ---------- */

function currentTheme() {
  return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
}

function applyTheme(theme, persist) {
  document.documentElement.setAttribute("data-theme", theme);
  var btn = document.getElementById("theme-toggle");
  if (btn) btn.textContent = theme === "dark" ? "라이트 모드" : "다크 모드";
  if (persist) {
    try { localStorage.setItem("theme", theme); } catch (e) { /* 무시 */ }
  }
}

function initTheme() {
  applyTheme(currentTheme(), false);
  var btn = document.getElementById("theme-toggle");
  if (btn) {
    btn.addEventListener("click", function () {
      applyTheme(currentTheme() === "dark" ? "light" : "dark", true);
    });
  }
  if (window.matchMedia) {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function (e) {
      var saved = null;
      try { saved = localStorage.getItem("theme"); } catch (err) {}
      if (!saved) applyTheme(e.matches ? "dark" : "light", false);
    });
  }
}

/* ---------- F3: 일/주/월 집계 (마지막 거래일 값, 이월 플래그 승계) ---------- */

function mondayOf(iso) {
  var d = new Date(iso + "T00:00:00Z");
  var wd = (d.getUTCDay() + 6) % 7; // 월=0
  return new Date(d.getTime() - wd * DAY_MS).toISOString().slice(0, 10);
}

function aggregate(rows, unit) {
  if (unit === "D") return rows;
  var groups = [];
  var curKey = null, cur = null;
  for (var i = 0; i < rows.length; i++) {
    var r = rows[i];
    var key = unit === "W" ? mondayOf(r.date) : r.date.slice(0, 7);
    if (key !== curKey) {
      if (cur) groups.push(cur);
      curKey = key;
      cur = { rows: [], key: key };
    }
    cur.rows.push(r);
  }
  if (cur) groups.push(cur);
  return groups.map(function (g) {
    var last = g.rows[g.rows.length - 1]; // 마지막 거래일 값
    var sumDr = null, sumLocal = null;
    g.rows.forEach(function (r) {
      if (r.vol_dr !== null && r.vol_dr !== undefined) sumDr = (sumDr || 0) + r.vol_dr;
      if (r.vol_local !== null && r.vol_local !== undefined) sumLocal = (sumLocal || 0) + r.vol_local;
    });
    var range = unit === "W"
      ? "주: " + g.key.slice(5) + "~" + last.date.slice(5)
      : "월: " + g.key;
    return {
      date: last.date, premium: last.premium,
      p_dr: last.p_dr, p_local: last.p_local, fx: last.fx,
      ff_dr: last.ff_dr, ff_local: last.ff_local, ff_fx: last.ff_fx,
      range: range, aggregated: true,
      vol_dr: sumDr, vol_local: sumLocal
    };
  });
}

/* ---------- F5: SMA (일 단위 시계열 기준) ---------- */

function smaMap(rows, n) {
  var map = {};
  var sum = 0;
  for (var i = 0; i < rows.length; i++) {
    sum += rows[i].premium;
    if (i >= n) sum -= rows[i - n].premium;
    if (i >= n - 1) map[rows[i].date] = sum / n;
  }
  return map;
}

/* ---------- F1: 윈도우 계산 (기간 탭 = 길이, endMs = 끝 날짜) ---------- */

function computeWindow(points) {
  var p = PERIODS.find(function (x) { return x.key === state.period; });
  var lastMs = dateMs(points[points.length - 1].date);
  var firstMs = dateMs(points[0].date);
  if (!p || p.days === null) {
    return { data: points, panEnabled: false, isPanned: false,
             spanMs: 0, lastMs: lastMs, minEnd: lastMs };
  }
  var spanMs = p.days * DAY_MS;
  var panEnabled = firstMs < lastMs - spanMs;
  var end = state.endMs === null ? lastMs : state.endMs;
  var minEnd = panEnabled ? firstMs + spanMs : lastMs;
  end = Math.min(lastMs, Math.max(minEnd, end));
  state.endMs = (end === lastMs) ? null : end;
  var lo = end - spanMs;
  var data = points.filter(function (r) {
    var m = dateMs(r.date);
    return m > lo && m <= end;
  });
  if (data.length < 2) data = points.slice(-2);
  return {
    data: data, panEnabled: panEnabled,
    isPanned: state.endMs !== null,
    spanMs: spanMs, lastMs: lastMs, minEnd: minEnd
  };
}

/* ---------- 종목 상세 초기화 ---------- */

function initStockPage() {
  var dataTag = document.getElementById("page-data");
  if (!dataTag) return;
  var stock;
  try { stock = JSON.parse(dataTag.textContent); } catch (e) { return; }
  state.stock = stock;

  var tabs = document.querySelectorAll(".period-tab");
  Array.prototype.forEach.call(tabs, function (b) {
    b.addEventListener("click", function () {
      state.period = b.textContent.trim();
      state.endMs = null; // 기간 탭 재선택 = 최신 구간 복귀 (F1)
      if (UNIT_RULES[state.period].indexOf(state.unit) < 0) state.unit = "D";
      Array.prototype.forEach.call(tabs, function (x) { x.classList.remove("active"); });
      b.classList.add("active");
      updateToolbar();
      drawDetailChart();
    });
  });

  buildToolbar();

  getJSON(dataRoot() + "data/history/" + stock.id + ".json").then(function (data) {
    state.rows = data.rows || [];
    updateToolbar();
    drawDetailChart();
  }).catch(function (e) {
    var wrap = document.getElementById("detail-chart");
    if (!wrap) return;
    wrap.innerHTML = "";
    wrap.appendChild(el("p", "fatal-error",
      "차트 데이터를 불러오지 못했습니다. (" + e.message + ") " +
      "위의 최신 스냅샷 값은 마지막 정상 수집분 기준입니다."));
  });
}

/* ---------- 컨트롤 툴바 (단위·오버레이·거래량·패닝 상태) ---------- */

function toggleBtn(label, key) {
  var b = el("button", "chart-toggle", label);
  b.type = "button";
  b.setAttribute("data-key", key);
  b.setAttribute("aria-pressed", "false");
  b.addEventListener("click", function () {
    if (b.disabled) return;
    state[key] = !state[key];
    updateToolbar();
    drawDetailChart();
  });
  return b;
}

function buildToolbar() {
  var tabsEl = document.querySelector(".period-tabs");
  if (!tabsEl) return;
  var bar = el("div", "chart-toolbar");
  bar.id = "chart-toolbar";

  // F3 단위 토글
  var unitGroup = el("div", "unit-group");
  ["D", "W", "M"].forEach(function (u) {
    var b = el("button", "chart-toggle unit-btn", UNIT_LABELS[u]);
    b.type = "button";
    b.setAttribute("data-unit", u);
    b.addEventListener("click", function () {
      if (b.disabled || state.unit === u) return;
      state.unit = u; // 기간 유지 (조합 규칙 내)
      updateToolbar();
      drawDetailChart();
    });
    unitGroup.appendChild(b);
  });
  bar.appendChild(unitGroup);

  // F5 오버레이 토글
  bar.appendChild(toggleBtn("SMA20", "sma20"));
  bar.appendChild(toggleBtn("SMA60", "sma60"));
  bar.appendChild(toggleBtn("기간 평균", "avg"));

  // F6 거래량 (시리즈 기본값 = 원주, 순서도 원주 우선)
  bar.appendChild(toggleBtn("거래량", "vol"));
  var volGroup = el("div", "unit-group vol-series");
  volGroup.id = "vol-series-group";
  [["local", "원주"], ["dr", "DR"]].forEach(function (pair) {
    var b = el("button", "chart-toggle", pair[1]);
    b.type = "button";
    b.setAttribute("data-vol", pair[0]);
    b.addEventListener("click", function () {
      state.volSeries = pair[0];
      updateToolbar();
      drawDetailChart();
    });
    volGroup.appendChild(b);
  });
  bar.appendChild(volGroup);

  // F1 패닝 상태 표시
  var panStatus = el("span", "pan-status", "과거 구간");
  panStatus.id = "pan-status";
  var latestBtn = el("button", "chart-toggle", "최신으로");
  latestBtn.type = "button";
  latestBtn.id = "pan-latest";
  latestBtn.addEventListener("click", function () {
    state.endMs = null;
    updateToolbar();
    drawDetailChart();
  });
  bar.appendChild(panStatus);
  bar.appendChild(latestBtn);

  tabsEl.parentNode.insertBefore(bar, tabsEl.nextSibling);

  var notice = el("p", "chart-note agg-notice",
    "주/월 단위는 해당 기간 마지막 거래일 기준입니다.");
  notice.id = "agg-notice";
  notice.style.display = "none";
  bar.parentNode.insertBefore(notice, bar.nextSibling);
}

function hasVolumeData() {
  if (!state.rows) return false;
  return state.rows.some(function (r) {
    return (r.vol_dr !== null && r.vol_dr !== undefined) ||
           (r.vol_local !== null && r.vol_local !== undefined);
  });
}

function updateToolbar() {
  var bar = document.getElementById("chart-toolbar");
  if (!bar) return;
  var allowed = UNIT_RULES[state.period] || ["D"];
  Array.prototype.forEach.call(bar.querySelectorAll(".unit-btn"), function (b) {
    var u = b.getAttribute("data-unit");
    b.disabled = allowed.indexOf(u) < 0;
    b.classList.toggle("active", state.unit === u);
  });
  // F5: 주/월 단위에서 SMA 비활성 + 데이터 부족 표기
  var dailyCount = state.rows ? state.rows.length : 0;
  Array.prototype.forEach.call(bar.querySelectorAll(".chart-toggle[data-key]"), function (b) {
    var key = b.getAttribute("data-key");
    var on = !!state[key];
    var disabled = false;
    if (key === "sma20" || key === "sma60") {
      disabled = state.unit !== "D";
      var n = key === "sma20" ? 20 : 60;
      if (dailyCount && dailyCount < n) {
        b.textContent = "SMA" + n + " (데이터 부족)";
        disabled = true;
      }
    }
    if (key === "vol" && state.rows && !hasVolumeData()) {
      b.style.display = "none"; // 미제공 심볼: 토글 숨김 (PRD F6)
    }
    b.disabled = disabled;
    b.classList.toggle("active", on && !disabled);
    b.setAttribute("aria-pressed", on && !disabled ? "true" : "false");
  });
  var volGroup = document.getElementById("vol-series-group");
  if (volGroup) {
    volGroup.style.display = state.vol ? "" : "none";
    Array.prototype.forEach.call(volGroup.querySelectorAll("button"), function (b) {
      b.classList.toggle("active", b.getAttribute("data-vol") === state.volSeries);
    });
  }
  var notice = document.getElementById("agg-notice");
  if (notice) notice.style.display = state.unit === "D" ? "none" : "";
  var panned = state.endMs !== null;
  var ps = document.getElementById("pan-status");
  var pl = document.getElementById("pan-latest");
  if (ps) ps.style.display = panned ? "" : "none";
  if (pl) pl.style.display = panned ? "" : "none";
}

/* ---------- 차트 렌더링 ---------- */

function svgEl(name, attrs) {
  var n = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (var k in attrs) n.setAttribute(k, attrs[k]);
  return n;
}

function drawDetailChart() {
  var wrap = document.getElementById("detail-chart");
  var t = state.stock;
  if (!wrap || !t) return;
  var rows = state.rows;
  if (!rows || rows.length === 0) {
    wrap.innerHTML = "";
    wrap.appendChild(el("p", "fatal-error", "표시할 히스토리가 없습니다."));
    return;
  }
  var points = aggregate(rows, state.unit);
  var win = computeWindow(points);
  var data = win.data;
  wrap.innerHTML = "";

  var W = Math.max(320, wrap.clientWidth - 16);
  var H = 320;
  var padL = 46, padR = 12, padT = 10, padB = 24;
  var plotW = W - padL - padR, plotH = H - padT - padB;

  var values = data.map(function (r) { return r.premium; });
  var min = Math.min(0, Math.min.apply(null, values));
  var max = Math.max(0, Math.max.apply(null, values));
  if (max - min < 1e-9) { max += 1; min -= 1; }
  var span = max - min;
  min -= span * 0.06; max += span * 0.06;

  var xOf = function (i) { return padL + (i / Math.max(1, data.length - 1)) * plotW; };
  var yOf = function (v) { return padT + (1 - (v - min) / (max - min)) * plotH; };

  var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", height: H });
  svg.style.touchAction = "pan-y"; // F1: 세로 스크롤 유지, 가로 제스처만 수신

  // Y 그리드 + 라벨
  var ticks = niceTicks(min, max, 5);
  ticks.forEach(function (v) {
    var gy = yOf(v);
    svg.appendChild(svgEl("line", { x1: padL, x2: W - padR, y1: gy, y2: gy,
      stroke: "var(--grid)", "stroke-width": 1 }));
    var label = svgEl("text", { x: padL - 6, y: gy + 4, "text-anchor": "end",
      "font-size": 11, fill: "var(--muted)" });
    label.textContent = v.toFixed(Math.abs(max - min) < 5 ? 1 : 0) + "%";
    svg.appendChild(label);
  });

  // 0% 기준선
  if (min < 0 && max > 0) {
    svg.appendChild(svgEl("line", { x1: padL, x2: W - padR, y1: yOf(0), y2: yOf(0),
      stroke: "var(--zero-line)", "stroke-width": 1.2, "stroke-dasharray": "4 4" }));
  }

  // X 라벨
  var xCount = Math.min(5, data.length);
  for (var i = 0; i < xCount; i++) {
    var idx = Math.round((i / Math.max(1, xCount - 1)) * (data.length - 1));
    var tx = svgEl("text", { x: xOf(idx), y: H - 6,
      "text-anchor": i === 0 ? "start" : (i === xCount - 1 ? "end" : "middle"),
      "font-size": 11, fill: "var(--muted)" });
    tx.textContent = data[idx].date;
    svg.appendChild(tx);
  }

  // F5: SMA 오버레이 (일 단위 전용, 전체 시계열 기준 계산 -> 윈도우에 표시)
  var legend = [];
  if (state.unit === "D") {
    [["sma20", 20, "--sma20"], ["sma60", 60, "--sma60"]].forEach(function (cfg) {
      if (!state[cfg[0]] || rows.length < cfg[1]) return;
      var map = smaMap(rows, cfg[1]);
      var d2 = "";
      data.forEach(function (r, i2) {
        var v = map[r.date];
        if (v === undefined) return;
        d2 += (d2 ? "L" : "M") + xOf(i2).toFixed(2) + " " + yOf(v).toFixed(2) + " ";
      });
      if (d2) {
        svg.appendChild(svgEl("path", { d: d2.trim(), fill: "none",
          stroke: "var(" + cfg[2] + ")", "stroke-width": 1.6 }));
        legend.push(["SMA" + cfg[1], cfg[2]]);
      }
    });
  }

  // F5: 기간 평균선 (표시 중인 윈도우 기준 - 패닝·기간 변경 시 재계산)
  if (state.avg) {
    var mean = values.reduce(function (a, b) { return a + b; }, 0) / values.length;
    var my = yOf(mean);
    svg.appendChild(svgEl("line", { x1: padL, x2: W - padR, y1: my, y2: my,
      stroke: "var(--avg-line)", "stroke-width": 1.4, "stroke-dasharray": "6 4" }));
    var ml = svgEl("text", { x: W - padR - 2, y: my - 4, "text-anchor": "end",
      "font-size": 11, fill: "var(--avg-line)" });
    ml.textContent = "평균 " + fmtPremium(mean);
    svg.appendChild(ml);
    legend.push(["기간 평균", "--avg-line"]);
  }

  // 프리미엄 본선
  var d = values.map(function (v, i2) {
    return (i2 === 0 ? "M" : "L") + xOf(i2).toFixed(2) + " " + yOf(v).toFixed(2);
  }).join(" ");
  svg.appendChild(svgEl("path", { d: d, fill: "none", stroke: "var(--accent)",
    "stroke-width": 2 }));

  // 호버 요소
  var hoverLine = svgEl("line", { y1: padT, y2: padT + plotH,
    stroke: "var(--zero-line)", "stroke-width": 1 });
  hoverLine.style.display = "none";
  svg.appendChild(hoverLine);
  var hoverDot = svgEl("circle", { r: 4, fill: "var(--accent)" });
  hoverDot.style.display = "none";
  svg.appendChild(hoverDot);

  wrap.appendChild(svg);

  // 범례 (오버레이 활성 시)
  if (legend.length) {
    var lg = el("div", "chart-legend");
    var base = el("span", "legend-item", "프리미엄");
    base.insertBefore(legendSwatch("--accent"), base.firstChild);
    lg.appendChild(base);
    legend.forEach(function (item) {
      var s2 = el("span", "legend-item", item[0]);
      s2.insertBefore(legendSwatch(item[1]), s2.firstChild);
      lg.appendChild(s2);
    });
    wrap.appendChild(lg);
  }

  // F6: 거래량 서브패널 (호버 연동용 참조는 state.volBars/volFocus에 저장)
  state.volBars = null;
  state.volFocus = null;
  if (state.vol && hasVolumeData()) {
    drawVolumePanel(wrap, data, xOf, W, padL, padR);
  }

  var tooltip = el("div", "chart-tooltip");
  wrap.appendChild(tooltip);

  attachTooltip(svg, wrap, data, xOf, yOf, hoverLine, hoverDot, tooltip, W, padL, plotW);

  // F1: 패닝 기하를 상태에 게시하고, 리스너는 재렌더에도 유지되는 wrap에 1회만 부착.
  // (svg에 리스너를 걸면 드래그 중 재렌더가 svg를 파괴해 제스처가 끊긴다 - 버그 수정)
  state.pan = { panEnabled: win.panEnabled, spanMs: win.spanMs,
                lastMs: win.lastMs, minEnd: win.minEnd, plotW: plotW, W: W };
  wrap.classList.toggle("pan-enabled", win.panEnabled);
  setupPanning(wrap);
  updateToolbar();
}

function legendSwatch(varName) {
  var s = el("span", "legend-swatch");
  s.style.background = "var(" + varName + ")";
  return s;
}

/* F6: 거래량 바 색상 - 해당 시리즈 종가의 직전 포인트 대비 등락 (2026-08-05).
 * 상승=빨강(--pos)/하락=파랑(--neg)/보합·비교불가·이월=회색(--zero-line).
 * 데이터에 체결 구분이 없으므로 "매수/매도 우위" 표현은 금지 - 등락 기준만 표기.
 * 반환: [CSS 변수명, 등락 텍스트] */
function volBarColor(prevPrice, curPrice) {
  if (prevPrice === null || prevPrice === undefined ||
      curPrice === null || curPrice === undefined) {
    return ["--zero-line", "비교불가"];
  }
  if (curPrice > prevPrice) return ["--pos", "상승"];
  if (curPrice < prevPrice) return ["--neg", "하락"];
  return ["--zero-line", "보합"];
}

/* F6: 거래량 서브패널 (프리미엄 축과 분리된 바 차트) */
function drawVolumePanel(wrap, data, xOf, W, padL, padR) {
  var H = 90, padT = 8, padB = 6;
  var plotH = H - padT - padB;
  var key = state.volSeries === "dr" ? "vol_dr" : "vol_local";
  var maxV = 0;
  data.forEach(function (r) {
    var v = r[key];
    if (v !== null && v !== undefined && v > maxV) maxV = v;
  });
  var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: "100%", height: H,
    "class": "vol-panel" });
  if (maxV === 0) {
    var msg = svgEl("text", { x: W / 2, y: H / 2, "text-anchor": "middle",
      "font-size": 12, fill: "var(--muted)" });
    msg.textContent = "이 구간에는 거래량 데이터가 없습니다";
    svg.appendChild(msg);
    wrap.appendChild(svg);
    return;
  }
  var yOf = function (v) { return padT + (1 - v / maxV) * plotH; };
  var axis = svgEl("text", { x: padL - 6, y: padT + 8, "text-anchor": "end",
    "font-size": 10, fill: "var(--muted)" });
  axis.textContent = fmtVolume(maxV);
  svg.appendChild(axis);
  var unitLabel = svgEl("text", { x: W - padR, y: padT + 8, "text-anchor": "end",
    "font-size": 10, fill: "var(--muted)" });
  unitLabel.textContent = "거래량(" + (state.volSeries === "dr" ? "DR" : "원주") + ")" +
    (state.unit === "D" ? "" : " - 기간 합계");
  svg.appendChild(unitLabel);
  var priceKey = state.volSeries === "dr" ? "p_dr" : "p_local";
  var bw = Math.max(1, (W - padL - padR) / data.length * 0.7);
  state.volBars = [];   // 호버 강조용 참조 (인덱스 -> rect. 이월 포인트는 null)
  data.forEach(function (r, i) {
    var v = r[key];
    if (v === null || v === undefined) { state.volBars.push(null); return; } // 이월: 바 없음
    // 색상: 같은 시리즈의 직전 포인트 종가 대비 (윈도우 첫 포인트는 비교불가=회색)
    var prev = i > 0 ? data[i - 1][priceKey] : null;
    var color = volBarColor(prev, r[priceKey])[0];
    var rect = svgEl("rect", {
      x: xOf(i) - bw / 2, y: yOf(v),
      width: bw, height: Math.max(1, padT + plotH - yOf(v)),
      fill: "var(" + color + ")", "class": "vol-bar"
    });
    svg.appendChild(rect);
    state.volBars.push(rect);
  });
  // 강조된 바를 감싸는 테두리 (색상 의미를 덮지 않도록 fill 없음 - 설계 문서 8.4)
  var focusRing = svgEl("rect", { fill: "none", stroke: "var(--text)",
    "stroke-width": 1.5, rx: 1, "class": "vol-focus" });
  focusRing.style.display = "none";
  svg.appendChild(focusRing);
  state.volFocus = { ring: focusRing, bw: bw, xOf: xOf, top: padT,
                     bottom: padT + plotH };
  wrap.appendChild(svg);
  var note = el("div", "chart-legend vol-color-note",
    "거래량 색: 해당 시장 종가의 전일 대비 상승(빨강)/하락(파랑)/보합·이월(회색)" +
    (state.unit === "D" ? "" : " - 주/월 단위는 직전 기간 대비"));
  wrap.appendChild(note);
}

/* 호버-거래량 연동 (2026-08-05 사용자 지시): 프리미엄 차트에서 활성화된
 * 날짜/기간의 거래량 바를 강조한다. 색상(등락 의미)을 덮지 않도록 색을 바꾸지
 * 않고 (1) 나머지 바 불투명도 감쇠 (2) 해당 바에 테두리 링 방식으로 처리.
 * 주/월 단위에서는 data가 이미 집계 포인트라 합계 바가 그대로 강조된다.
 * idx === null 이면 강조 해제. */
function highlightVolBar(idx) {
  var bars = state.volBars;
  var focus = state.volFocus;
  if (!bars || !focus) return;
  state.hoverIdx = idx;
  for (var i = 0; i < bars.length; i++) {
    if (!bars[i]) continue;
    bars[i].style.opacity = (idx === null || i === idx) ? "1" : "0.35";
  }
  var bar = idx === null ? null : bars[idx];
  if (!bar) {
    focus.ring.style.display = "none";
    return;
  }
  var pad = 1.5;
  focus.ring.setAttribute("x", focus.xOf(idx) - focus.bw / 2 - pad);
  focus.ring.setAttribute("width", focus.bw + pad * 2);
  focus.ring.setAttribute("y", parseFloat(bar.getAttribute("y")) - pad);
  focus.ring.setAttribute("height", parseFloat(bar.getAttribute("height")) + pad * 2);
  focus.ring.style.display = "";
}

/* ---------- 툴팁 ---------- */

function attachTooltip(svg, wrap, data, xOf, yOf, hoverLine, hoverDot, tooltip, W, padL, plotW) {
  function onMove(clientX) {
    if (state.dragging) return; // F1: 드래그 중 툴팁 억제
    var rect = svg.getBoundingClientRect();
    var scale = W / rect.width;
    var mx = (clientX - rect.left) * scale;
    var frac = (mx - padL) / plotW;
    var idx = Math.round(frac * (data.length - 1));
    idx = Math.max(0, Math.min(data.length - 1, idx));
    var r = data[idx];
    var px = xOf(idx), py = yOf(r.premium);
    hoverLine.setAttribute("x1", px); hoverLine.setAttribute("x2", px);
    hoverLine.style.display = "";
    hoverDot.setAttribute("cx", px); hoverDot.setAttribute("cy", py);
    hoverDot.style.display = "";
    highlightVolBar(idx); // 거래량 바 연동 강조

    var ffNotes = [];
    if (r.ff_dr) ffNotes.push("DR 이월가");
    if (r.ff_local) ffNotes.push("원주 이월가");
    if (r.ff_fx) ffNotes.push("환율 이월");
    tooltip.innerHTML = "";
    var title = r.date + (r.range ? " (" + r.range + ")" : "") +
      (ffNotes.length ? " (이월)" : "");
    tooltip.appendChild(el("div", "tt-date", title));
    tooltip.appendChild(el("div", null, "프리미엄 " + fmtPremium(r.premium)));
    tooltip.appendChild(el("div", null,
      "DR " + fmtUsd(r.p_dr) + " · 원주 " + fmtLocalPrice(r.p_local, state.stock.local_currency)));
    tooltip.appendChild(el("div", null, state.stock.fx_label + " " + fmtNum(r.fx, 2)));
    if (state.vol) {
      var key = state.volSeries === "dr" ? "vol_dr" : "vol_local";
      var vLabel = "거래량(" + (state.volSeries === "dr" ? "DR" : "원주") + ") " +
        fmtVolume(r[key]) +
        (r.aggregated && r[key] !== null && r[key] !== undefined ? " (합계)" : "");
      if (r[key] !== null && r[key] !== undefined) {
        var priceKey = state.volSeries === "dr" ? "p_dr" : "p_local";
        var prevP = idx > 0 ? data[idx - 1][priceKey] : null;
        var dir = volBarColor(prevP, r[priceKey])[1];
        vLabel += " · " + (r.aggregated ? "직전 기간" : "전일 종가") + " 대비 " + dir;
      }
      tooltip.appendChild(el("div", null, vLabel));
    }
    if (ffNotes.length) {
      tooltip.appendChild(el("div", "tt-ff", "휴장 이월: " + ffNotes.join(", ")));
    }
    tooltip.style.display = "block";
    var wrapRect = wrap.getBoundingClientRect();
    var pxCss = px / scale + (rect.left - wrapRect.left);
    var left = pxCss + 12;
    if (left + tooltip.offsetWidth > wrapRect.width - 8) {
      left = pxCss - tooltip.offsetWidth - 12;
    }
    tooltip.style.left = Math.max(4, left) + "px";
    tooltip.style.top = "24px";
  }

  function hide() {
    tooltip.style.display = "none";
    hoverLine.style.display = "none";
    hoverDot.style.display = "none";
    highlightVolBar(null); // 거래량 강조 해제
  }

  svg.addEventListener("mousemove", function (e) { onMove(e.clientX); });
  svg.addEventListener("mouseleave", hide);
  svg.addEventListener("touchstart", function (e) {
    if (e.touches.length && !state.dragging) onMove(e.touches[0].clientX);
  }, { passive: true });
  svg.addEventListener("touchmove", function (e) {
    if (e.touches.length && !state.dragging) onMove(e.touches[0].clientX);
  }, { passive: true });
}

/* ---------- F1: 패닝 (포인터 드래그 + 키보드, MAX 비활성) ----------
 *
 * 리스너는 재렌더에도 살아남는 wrap(#detail-chart)에 1회만 부착한다.
 * 드래그 중 매 프레임 재렌더가 svg를 갈아끼우므로, svg에 리스너·포인터 캡처를
 * 걸면 첫 move 틱에서 제스처가 끊긴다 (2026-08-04 사용자 보고 버그의 원인).
 * 윈도우 기하(state.pan)는 drawDetailChart가 매 렌더마다 갱신한다.
 */

function hideTooltipIn(wrap) {
  var tt = wrap.querySelector(".chart-tooltip");
  if (tt) tt.style.display = "none";
  highlightVolBar(null);
}

function setupPanning(wrap) {
  if (wrap._panBound) return; // 1회만 부착 (재렌더 시 중복 방지)
  wrap._panBound = true;

  var mode = null; // null | "pending" | "pan" | "scroll"
  var lastX = 0, startX = 0, startY = 0;
  var raf = null;
  var TOUCH_THRESHOLD = 10;

  function shiftByPx(dxPx) {
    var pan = state.pan;
    if (!pan || !pan.panEnabled) return;
    var svg = wrap.querySelector("svg");
    var rectW = svg ? svg.getBoundingClientRect().width
                    : wrap.getBoundingClientRect().width;
    var scale = rectW ? pan.W / rectW : 1;
    var dMs = (dxPx * scale) / pan.plotW * pan.spanMs;
    var end = (state.endMs === null ? pan.lastMs : state.endMs) - dMs; // +dx = 과거로
    end = Math.min(pan.lastMs, Math.max(pan.minEnd, end)); // 경계 멈춤
    state.endMs = (end >= pan.lastMs) ? null : end;
    if (!raf) {
      raf = requestAnimationFrame(function () {
        raf = null;
        drawDetailChart();
      });
    }
  }

  wrap.addEventListener("pointerdown", function (e) {
    if (!state.pan || !state.pan.panEnabled) return; // MAX·짧은 종목: 비활성
    if (e.button !== undefined && e.button !== 0) return;
    startX = lastX = e.clientX;
    startY = e.clientY;
    mode = e.pointerType === "touch" ? "pending" : "pan";
    if (mode === "pan") {
      state.dragging = true;
      hideTooltipIn(wrap);
      wrap.classList.add("panning");
    }
    try { wrap.setPointerCapture(e.pointerId); } catch (err) {}
    if (e.pointerType !== "touch") e.preventDefault(); // 텍스트 선택 방지
  });
  wrap.addEventListener("pointermove", function (e) {
    if (!mode) return;
    if (mode === "pending") {
      var dx0 = e.clientX - startX, dy0 = e.clientY - startY;
      if (Math.abs(dx0) > TOUCH_THRESHOLD && Math.abs(dx0) > Math.abs(dy0)) {
        mode = "pan"; // 수평 의도 확인 -> 패닝 개시 (F1 터치 구분)
        state.dragging = true;
        hideTooltipIn(wrap);
        wrap.classList.add("panning");
        lastX = e.clientX;
      } else if (Math.abs(dy0) > TOUCH_THRESHOLD) {
        mode = "scroll"; // 세로 스크롤에 양보 (touch-action: pan-y)
        return;
      } else {
        return;
      }
    }
    if (mode !== "pan") return;
    var dx = e.clientX - lastX;
    lastX = e.clientX;
    if (dx !== 0) shiftByPx(dx);
  });
  function endPan() {
    mode = null;
    state.dragging = false;
    wrap.classList.remove("panning");
  }
  wrap.addEventListener("pointerup", endPan);
  wrap.addEventListener("pointercancel", endPan);

  // 키보드: 차트 포커스 후 좌/우 화살표 = 윈도우 길이의 10% 이동
  wrap.setAttribute("tabindex", "0");
  wrap.setAttribute("aria-label", "프리미엄 차트 - 좌우 화살표로 과거/최신 구간 이동");
  wrap.addEventListener("keydown", function (e) {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    var p = PERIODS.find(function (x) { return x.key === state.period; });
    if (!p || p.days === null) return; // MAX: 비활성
    var points = aggregate(state.rows, state.unit);
    var w = computeWindow(points);
    if (!w.panEnabled) return;
    var step = p.days * DAY_MS * 0.1;
    var end = state.endMs === null ? w.lastMs : state.endMs;
    end += (e.key === "ArrowRight" ? step : -step);
    end = Math.min(w.lastMs, Math.max(w.minEnd, end));
    state.endMs = (end >= w.lastMs) ? null : end;
    e.preventDefault();
    drawDetailChart();
  });
}

function niceTicks(min, max, count) {
  var span = max - min;
  var step = Math.pow(10, Math.floor(Math.log10(span / count)));
  var err = span / count / step;
  if (err >= 7.5) step *= 10;
  else if (err >= 3.5) step *= 5;
  else if (err >= 1.5) step *= 2;
  var ticks = [];
  for (var v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) {
    ticks.push(Math.abs(v) < step / 1e6 ? 0 : v);
  }
  return ticks;
}

/* ---------- 초기화 ---------- */

function init() {
  initTheme();
  if (document.body.getAttribute("data-page") === "stock") {
    initStockPage();
  }
}

init();
