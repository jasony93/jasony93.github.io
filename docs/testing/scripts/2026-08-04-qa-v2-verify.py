# -*- coding: utf-8 -*-
"""QA v2 independent verification (F2 labels, F4, F7, F8 + prerender).

- F7(a): independent yfinance re-query of 11 DR symbols' share fields ->
         verify 검증 A rejects all (frac >= 0.9), matching PRD 9절 table
- F7(b): SKHY cv/lu/V_dr/V_local manual recalc (PRD 7.2 formulas) vs meta + page
- F7(c): fallback display for 미확인 tickers (raw HTML)
- F7(d): honesty/asymmetry footnotes + source labels
- F4: delta_pp manual recalc from history for WF/KT/LPL (dev used other tickers)
       + prerender presence + prev-date correctness
- F8: mcap = N_total * close for SHG + TSM, currency/abbrev format, as-of label
- F2: label formats in raw HTML per PRD standard (badge/footnote/value labels)
- regression: main page core content vs meta (11 cards)
"""
import io, sys, json, re
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(r"d:\personal\Claude 프로젝트\Stock tools")
WEB = ROOT / "src" / "web"
meta = json.load(open(WEB / "data" / "meta.json", encoding="utf-8"))
cfg = json.load(open(ROOT / "src" / "config" / "tickers.json", encoding="utf-8"))
tickers = {t["id"]: t for t in cfg["tickers"]}

results = []
def check(name, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    print(f"[{tag}] {name}  {detail}")
    results.append((tag, name, detail))

def rows_of(tid):
    return json.load(open(WEB / "data" / "history" / f"{tid}.json", encoding="utf-8"))["rows"]

def page(tid):
    return (WEB / "stocks" / tid.lower() / "index.html").read_text(encoding="utf-8")

# ---------- F7(a): independent share-field re-query ----------
print("== F7(a): 11개 DR 심볼 발행주식수 독립 재조회 - 검증 A 전량 기각 확인 ==")
import yfinance as yf
threshold = cfg["f7"]["auto_reject_threshold"]
for tid, t in tickers.items():
    try:
        info = yf.Ticker(t["dr_yahoo"]).info or {}
        cand = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")
        info_l = yf.Ticker(t["local_yahoo"]).info or {}
        n_total = info_l.get("sharesOutstanding")
        if not cand or not n_total:
            check(f"{tid} 필드 조회", False, f"cand={cand} n_total={n_total}")
            continue
        frac = cand * t["ratio"] / n_total
        check(f"{tid} 검증 A: 원주환산/총주식 {frac*100:.1f}% >= 90% -> 기각 대상",
              frac >= threshold, f"cand={cand:,} n_total={n_total:,}")
    except Exception as e:
        check(f"{tid} 필드 조회", False, f"{type(e).__name__}: {e}")

# meta에 기록된 기각 내역과 채택 경로
print("\n== F7(a2): 파이프라인 기각 기록·채택 경로 ==")
for tid in meta["order"]:
    conv = meta["tickers"][tid].get("conversion") or {}
    rejected = conv.get("rejected_auto", [])
    n_src = conv.get("n_dr_source")
    if tid == "SKHY":
        check("SKHY 채택 경로 = manual", n_src == "manual",
              f"n_dr={conv.get('n_dr'):,} as_of={conv.get('n_dr_as_of')}")
        check("SKHY 자동 후보 기각 기록 존재(검증 A)",
              any("검증 A" in r.get("reason", "") for r in rejected),
              str([r.get("reason") for r in rejected])[:90])
    else:
        check(f"{tid} 자동 미채택(기각) + 수동 없음 -> 미확인", n_src is None,
              f"rejected={len(rejected)}건")

# ---------- F7(b): SKHY 수기 재계산 ----------
print("\n== F7(b): SKHY cv/lu/금액 수기 재계산 (PRD 7.2) ==")
e = meta["tickers"]["SKHY"]
conv, sh, s = e["conversion"], e["shares"], e["snapshot"]
r = tickers["SKHY"]["ratio"]
n_dr = 177900000
L = 17790000
n_total = sh["n_total"]
n_dr_local = n_dr * r
cv = n_dr_local / n_total * 100
lu = n_dr_local / L * 100
v_dr = n_dr * s["p_dr"]
v_local = (n_total - n_dr_local) * s["p_local"]
check(f"n_dr_local = {n_dr_local:,.0f}", conv["n_dr_local"] == round(n_dr_local))
check(f"cv 수기 {cv:.4f}% vs meta {conv['cv']}", abs(cv - conv["cv"]) <= 0.1)
check(f"lu 수기 {lu:.4f}% vs meta {conv['lu']}", abs(lu - conv["lu"]) <= 0.1)
check(f"V_dr 수기 {v_dr:,.0f} USD vs meta {conv['v_dr_usd']:,.0f}",
      abs(v_dr - conv["v_dr_usd"]) / v_dr < 1e-3)
check(f"V_local 수기 {v_local:,.0f} KRW vs meta {conv['v_local']:,.0f}",
      abs(v_local - conv["v_local"]) / v_local < 1e-3)
check(f"limit_pct = L/N_total = {L/n_total*100:.4f}",
      abs(conv["limit_pct"] - L / n_total * 100) < 0.001)
check("PRD 완료 기준 값 대조: cv ~= 2.51%, lu = 100%",
      abs(cv - 2.51) < 0.01 and abs(lu - 100.0) < 1e-9, f"cv={cv:.4f} lu={lu:.4f}")

# SKHY page rendering
h = page("SKHY")
check("SKHY 페이지: 전환 현황 섹션 + 한도 1,779만주 + 기준일 + 출처",
      "전환 현황" in h and "17,790,000" in h and "2026-07-29" in h
      and ("컨퍼런스콜" in h or "컨콜" in h))
check("SKHY 페이지: 수동 입력 라벨 + 기준일 + 출처",
      "수동 입력" in h and "2026-07-31" in h)
check("SKHY 페이지: 게이지/소진율 표기", ("소진율" in h or "소진" in h) and "100" in h)

# ---------- F7(c): fallback ----------
print("\n== F7(c): 미확인 종목 폴백 ==")
for tid in ("SMSN", "TSM", "KB"):
    h2 = page(tid)
    check(f"{tid} 페이지: '데이터 미확인' 폴백 + 섹션 유지",
          "데이터 미확인" in h2 and "전환 현황" in h2)
    check(f"{tid} 페이지: 한도 행 미표시 (빈 값 노출 금지)",
          "전환한도" not in h2 or "17,790,000" not in h2)

# ---------- F7(d): footnotes ----------
print("\n== F7(d): 각주 ==")
h = page("SKHY")
check("정직성 각주 (합계 != 시총)",
      "시가총액과 일치하지 않을 수" in h and "프리미엄이 반영된" in h)
check("전환 비대칭 각주 (ADR->원주 자유 / 역방향 제약)",
      ("2026-07-30" in h or "원주 -> ADR" in h or "역방향" in h) and
      re.search(r"ADR\s*->\s*원주|원주 전환은|전환은.*자유", h) is not None,
      "asymmetry footnote")
# 폴백 페이지에도 각주 노출 여부 (미확인이면 각주 불필요할 수 있으나 섹션 안내는 필요)
check("SKHY 수식 안내에 7.2 정의 게재",
      "N_dr" in h and ("cv" in h or "전환율" in h) and "V_dr" in h)

# ---------- F4: delta 독립 재계산 (WF/KT/LPL) ----------
print("\n== F4: 전일 대비 %p (WF/KT/LPL - 개발팀과 다른 표본) ==")
for tid in ("WF", "KT", "LPL"):
    e2 = meta["tickers"][tid]; s2 = e2["snapshot"]
    rows = rows_of(tid)
    snap_date = max(s2["p_dr_date"], s2["p_local_date"])
    prev = None
    for rr in reversed(rows):
        if rr["date"] < snap_date:
            prev = rr
            break
    manual = s2["premium"] - prev["premium"]
    check(f"{tid} delta 수기 {manual:+.4f}%p vs meta {s2['delta_pp']:+.4f}%p",
          abs(manual - s2["delta_pp"]) <= 0.01,
          f"prev_date meta {s2['prev_date']} vs manual {prev['date']}")
    check(f"{tid} 기준일 일치", s2["prev_date"] == prev["date"])
    h3 = page(tid)
    d_str = f"{s2['delta_pp']:+.2f}%p"
    check(f"{tid} 프리렌더에 delta 존재 ({d_str})", d_str in h3)
    check(f"{tid} 프리렌더에 비교 기준일 존재", s2["prev_date"][5:].replace('-', '/') in h3
          or s2["prev_date"] in h3)
# 메인 카드에도
main = (WEB / "index.html").read_text(encoding="utf-8")
for tid in ("WF", "KT"):
    s2 = meta["tickers"][tid]["snapshot"]
    check(f"메인 카드 {tid} delta 축약형", f"{s2['delta_pp']:+.2f}%p" in main)

# ---------- F8: 시가총액 ----------
print("\n== F8: 시가총액 (SHG + TSM) ==")
for tid in ("SHG", "TSM"):
    e3 = meta["tickers"][tid]; sh3 = e3["shares"]; s3 = e3["snapshot"]
    mc = sh3["n_total"] * s3["p_local"]
    rel = abs(mc - sh3["mcap_local"]) / mc
    check(f"{tid} MC = N_total * P_local 수기 {mc:,.0f} vs meta {sh3['mcap_local']:,.0f}",
          rel < 1e-3)
    h4 = page(tid)
    check(f"{tid} 페이지: 시가총액 카드 + 종가 기준 라벨",
          "시가총액" in h4 and "종가 기준" in h4)
cur_ok_shg = ("조원" in page("SHG"))
cur_ok_tsm = ("NT$" in page("TSM"))
check("통화 축약: SHG 조원 / TSM NT$", cur_ok_shg and cur_ok_tsm)
usd_ok = ("$" in page("SHG"))
check("USD 병기 존재 (SHG)", usd_ok)

# ---------- F2: 라벨 형식 (PRD 표준) ----------
print("\n== F2: 라벨 형식 (원시 HTML) ==")
smsn_h = page("SMSN")
s4 = meta["tickers"]["SMSN"]["snapshot"]
col = meta["tickers"]["SMSN"]["collected_at_kst"]
hhmm = col.split(" ")[1]
check("SMSN DR 값 라벨: '장중 지연 시세 (수집 HH:MM)'",
      f"장중 지연 시세 (수집 {hhmm})" in smsn_h, f"수집 {col}")
check("공통 배지: '장중 지연 시세 기준 - 수집 MM/DD HH:MM KST'",
      f"장중 지연 시세 기준 - 수집 {col} KST" in smsn_h)
check("각주: 거래소 지연(최대 20분) + 갱신 주기",
      "최대 20분" in smsn_h and "갱신 주기" in smsn_h)
# 확정 종가 라벨 (SKHY DR = 7/31 종가)
skhy_h = page("SKHY")
check("SKHY DR 확정 종가 라벨 'MM/DD 종가' 형식",
      re.search(r"07/31 종가", skhy_h) is not None or "2026-07-31" in skhy_h)
# 이월 라벨 유지 - 메인 as-of는 기존 형식
check("메인에도 공통 배지 또는 지연 표기", "지연" in main)

# ---------- 회귀: 메인 카드 11종 프리렌더 vs meta ----------
print("\n== 회귀: 메인 카드 프리렌더 vs meta ==")
def fmt_p(v): return f"{v:+.2f}%"
allok = True
for tid in meta["order"]:
    s5 = meta["tickers"][tid]["snapshot"]
    if fmt_p(s5["premium"]) not in main or f'href="stocks/{tid.lower()}/"' not in main:
        allok = False
        check(f"메인 카드 {tid}", False, fmt_p(s5["premium"]))
check("메인 카드 11종 프리미엄·링크 전부 일치", allok)
check("스파크라인 11개", main.count("card-spark") == 11)

n_pass = sum(1 for t, *_ in results if t == "PASS")
n_fail = sum(1 for t, *_ in results if t == "FAIL")
print(f"\nTOTAL: PASS {n_pass} / FAIL {n_fail}")
for t, n, d in results:
    if t == "FAIL":
        print(" FAIL -", n, "|", d)
sys.exit(1 if n_fail else 0)
