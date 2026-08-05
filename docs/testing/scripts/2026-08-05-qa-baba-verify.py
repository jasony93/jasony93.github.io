# -*- coding: utf-8 -*-
"""BABA 편입 독립 검증 (PRD 2026-08-05 1.4절 완료 기준) + 회귀 앵커.

1. 설정 = PRD 1.1 (r=8, HKD=X, history_start 2019-11-26)
2. 프리미엄 수기 재계산 3일 (yfinance 독립 조회, 개발팀과 다른 표본)
3. fungible 정합: 표본 5일 |premium| < 3%
4. HKD 페그: 전 행 7.5~8.1 + 타 종목 교차 오적용 없음
5. 홍콩 휴장 이월 (HK-only / US-only / 양쪽) - QA 선정 날짜
6. history_start / MAX 시작
7. 프리렌더: /stocks/baba/ 페이지·HK$ 표기·fungible 각주·USD/HKD 카드·메타태그
8. sitemap 15 URL / 메인 12카드 순서 (BABA 4위) / USD 환산 시총 순위 검증
9. 회귀 앵커: BABA 추가 전 기록값(과거 회차 리포트 수치)과 기존 종목 히스토리 대조
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

# ---------- 1. 설정 ----------
print("== 1. 설정 = PRD 1.1 ==")
b = tickers["BABA"]
check("r=8 / 9988.HK / HKD=X / history_start=2019-11-26 / NYSE / HKEX",
      b["ratio"] == 8 and b["local_yahoo"] == "9988.HK" and b["fx_yahoo"] == "HKD=X"
      and b["history_start"] == "2019-11-26" and b["dr_exchange"] == "NYSE"
      and b["local_exchange"] == "HKEX" and b["local_currency"] == "HKD")
check("conversion_note (fungible) 설정 존재", "fungible" in b.get("conversion_note", "")
      or "양방향" in b.get("conversion_note", ""))
check("전환한도 필드 없음 (한도 행 미표시 대상)", "conversion_limit_local" not in b)

# ---------- 2. 프리미엄 수기 재계산 3일 ----------
print("\n== 2. 프리미엄 수기 재계산 (2026-07-16 / 07-23 / 07-30) ==")
import yfinance as yf
import pandas as pd
def series(sym):
    df = yf.Ticker(sym).history(period="1y", auto_adjust=False)
    s = df["Close"].dropna()
    s.index = pd.DatetimeIndex(s.index.tz_localize(None)).normalize()
    return s[~s.index.duplicated(keep="last")].sort_index()
dr, loc, fx = series("BABA"), series("9988.HK"), series("HKD=X")
rows = {r["date"]: r for r in rows_of("BABA")}
for ds in ("2026-07-16", "2026-07-23", "2026-07-30"):
    d = pd.Timestamp(ds)
    if d not in dr.index or d not in loc.index or d not in fx.index:
        check(f"BABA {ds} 3원천 거래일", False, "표본일 교체 필요")
        continue
    manual = (float(dr.loc[d]) * float(fx.loc[d]) / (float(loc.loc[d]) * 8) - 1) * 100
    p = rows.get(ds, {}).get("premium")
    check(f"BABA {ds} 수기 {manual:+.4f}% vs 파이프라인 {p}",
          p is not None and abs(manual - p) <= 0.1, f"차이 {abs(manual-(p or 0)):.6f}%p")
    rr = rows.get(ds)
    if rr:
        check(f"BABA {ds} ff 플래그 없음(정상 거래일)",
              not (rr["ff_dr"] or rr["ff_local"] or rr["ff_fx"]))

# ---------- 3. fungible 정합 ----------
print("\n== 3. fungible: 표본 5일 |premium| < 3% ==")
sample_days = ["2026-07-16", "2026-07-23", "2026-07-30", "2026-06-10", "2026-05-15"]
vals = []
for ds in sample_days:
    r = rows.get(ds)
    if r:
        vals.append((ds, r["premium"]))
ok = all(abs(v) < 3 for _, v in vals) and len(vals) == 5
check("5일 전부 |premium| < 3%", ok, str(vals))
# 최근 1년 전체 분포도 참고 확인
recent = [r["premium"] for r in rows_of("BABA") if r["date"] >= "2025-08-05"]
frac_small = sum(1 for v in recent if abs(v) < 3) / len(recent)
check(f"최근 1년 {len(recent)}일 중 |premium|<3% 비율 {frac_small*100:.1f}% (>=95% 기대)",
      frac_small >= 0.95)

# ---------- 4. HKD 페그 전 행 + 교차 오적용 ----------
print("\n== 4. 환율 검증 ==")
fx_all = [r["fx"] for r in rows_of("BABA")]
check(f"BABA 전 {len(fx_all)}행 fx 7.5~8.1: min={min(fx_all):.4f} max={max(fx_all):.4f}",
      all(7.5 <= v <= 8.1 for v in fx_all))
# 타 종목 최근 250행 재확인 (KRW/TWD에 HKD 미유입)
for tid, lo, hi in (("KB", 800, 2000), ("TSM", 20, 45)):
    vals2 = [r["fx"] for r in rows_of(tid)[-250:]]
    check(f"{tid} 최근 250행 fx 범위 유지", all(lo <= v <= hi for v in vals2),
          f"min={min(vals2):.2f} max={max(vals2):.2f}")

# ---------- 5. 휴장 이월 (QA 선정 날짜) ----------
print("\n== 5. 홍콩·미국 휴장 이월 ==")
r = rows.get("2026-07-01"); prev = rows.get("2026-06-30")
check("2026-07-01 (홍콩 특별행정구 수립일, NYSE 개장): ff_local=True + 원주 이월",
      r is not None and r["ff_local"] and not r["ff_dr"]
      and prev is not None and r["p_local"] == prev["p_local"], f"row={r}")
r = rows.get("2026-06-19")
check("2026-06-19 (미 준틴스, HKEX 개장): ff_dr=True",
      r is not None and r["ff_dr"] and not r["ff_local"], f"row={r}")
r = rows.get("2026-02-17")
check("2026-02-17 (구정 연휴, NYSE 개장): ff_local=True",
      r is not None and r["ff_local"] and not r["ff_dr"], f"row={r}")
check("2026-04-03 (성금요일 - 양쪽 휴장): 포인트 생략", "2026-04-03" not in rows)
r = rows.get("2026-04-06")
check("2026-04-06 (부활절 월요일, 홍콩 휴장·NYSE 개장): ff_local=True",
      r is not None and r["ff_local"] and not r["ff_dr"], f"row={r}")
# 이월일 거래량 null (색상 회색 전제)
r = rows.get("2026-07-01")
check("이월일 vol_local=null (바 미표시 전제)", r is not None and r["vol_local"] is None)

# ---------- 6. history_start ----------
print("\n== 6. history_start ==")
first = rows_of("BABA")[0]
check("첫 행 = 2019-11-26 (9988.HK 상장일)", first["date"] == "2019-11-26", first["date"])
check("meta first_date 일치", meta["tickers"]["BABA"]["first_date"] == "2019-11-26")

# ---------- 7. 프리렌더 ----------
print("\n== 7. 프리렌더 /stocks/baba/ ==")
h = (WEB / "stocks" / "baba" / "index.html").read_text(encoding="utf-8")
s = meta["tickers"]["BABA"]["snapshot"]
check("페이지 존재 + 알리바바 + BABA (NYSE) vs 9988 (HKEX)",
      "알리바바" in h and "9988" in h and "HKEX" in h)
check("프리미엄 수치 = meta", f"{s['premium']:+.2f}%" in h)
check("원주 가격 HK$ 표기", "HK$" in h)
check("환율 카드 USD/HKD", "USD/HKD" in h)
check("전환비율 8 표기", "8 (ADS 1주 = 보통주 8주)" in h)
check("fungible 각주 노출", "양방향 전환이 자유" in h and "벤치마크" in h)
check("한도 행 미표시", "전환한도" not in h)
title = re.search(r"<title>(.*?)</title>", h).group(1)
check("메타 title 기본 템플릿", title == "알리바바 ADR 프리미엄(BABA 괴리율) 차트 - ADR 프리미엄 트래커", title)
desc = re.search(r'<meta name="description" content="(.*?)">', h).group(1)
check("메타 desc: 원주 코드 + 전환비율", "9988" in desc and "8" in desc, desc)
canon = re.search(r'<link rel="canonical" href="(.*?)">', h).group(1)
check("canonical /stocks/baba/", canon.endswith("/stocks/baba/"))
check("BreadcrumbList JSON-LD", '"BreadcrumbList"' in h and '"알리바바"' in h)

# ---------- 8. sitemap / 메인 순서 / 시총 순위 ----------
print("\n== 8. sitemap·메인 순서·시총 ==")
sm = (WEB / "sitemap.xml").read_text(encoding="utf-8")
locs = re.findall(r"<loc>(.*?)</loc>", sm)
check("sitemap 15 URL", len(locs) == 15, f"got {len(locs)}")
check("sitemap에 /stocks/baba/", any(u.endswith("/stocks/baba/") for u in locs))
main = (WEB / "index.html").read_text(encoding="utf-8")
hrefs = re.findall(r'href="stocks/([a-z]+)/"', main)
seen = list(dict.fromkeys(hrefs))
check("메인 12카드 순서 = order (BABA 4위)",
      seen == [t.lower() for t in meta["order"]] and seen[3] == "baba", str(seen))
# USD 환산 시총 순위: BABA vs KB (4위 근거)
sh_b = meta["tickers"]["BABA"]["shares"]; sh_kb = meta["tickers"]["KB"]["shares"]
fx_b = meta["tickers"]["BABA"]["snapshot"]["fx"]; fx_kb = meta["tickers"]["KB"]["snapshot"]["fx"]
usd_b = sh_b["mcap_local"] / fx_b; usd_kb = sh_kb["mcap_local"] / fx_kb
check(f"USD 환산 시총: BABA ${usd_b/1e9:.0f}B > KB ${usd_kb/1e9:.0f}B (4위 배치 근거)",
      usd_b > usd_kb)
# 고정 3종 아래 나머지가 USD 환산 시총 내림차순인지
usd_all = []
for tid in meta["order"][3:]:
    e = meta["tickers"][tid]
    if e.get("shares"):
        usd_all.append((tid, e["shares"]["mcap_local"] / e["snapshot"]["fx"]))
sorted_ok = all(usd_all[i][1] >= usd_all[i+1][1] for i in range(len(usd_all)-1))
check("4위 이하 USD 환산 시총 내림차순", sorted_ok,
      str([(t, f"{v/1e9:.0f}B") for t, v in usd_all]))

# ---------- 9. 회귀 앵커 (BABA 추가 전 기록값 대조) ----------
print("\n== 9. 기존 종목 회귀 앵커 ==")
anchors = [  # (tid, date, premium) - 과거 회차 리포트·검증에서 기록된 값
    ("KB", "2026-06-19", 3.7052), ("KB", "2025-11-27", 1.2531),
    ("KB", "2026-03-06", 0.1229),
    ("TSM", "2026-05-29", 11.672), ("TSM", "2024-03-29", 12.2697),
    ("SKHY", "2026-07-14", 51.8212), ("SMSN", "2026-04-06", -5.5208),
    ("SKM", "2026-06-12", 1.6144), ("WF", "2026-06-12", 1.1262),
]
for tid, ds, expv in anchors:
    rr = {r["date"]: r for r in rows_of(tid)}.get(ds)
    check(f"{tid} {ds} = {expv} (변동 없음)",
          rr is not None and abs(rr["premium"] - expv) < 1e-6,
          f"got {rr['premium'] if rr else None}")

n_pass = sum(1 for t, *_ in results if t == "PASS")
n_fail = sum(1 for t, *_ in results if t == "FAIL")
print(f"\nTOTAL: PASS {n_pass} / FAIL {n_fail}")
for t, n, d in results:
    if t == "FAIL":
        print(" FAIL -", n, "|", d)
sys.exit(1 if n_fail else 0)
