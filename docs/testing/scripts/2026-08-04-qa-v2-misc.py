# -*- coding: utf-8 -*-
"""v2 misc verification:
1. F2 session judgment with simulated clocks (shipped code, mocked now_utc)
2. F6 volume vs independent yfinance re-query (SKHY 3 days + KB 2 days)
3. F6 history file size check (TSM)
4. WCAG: 4 new color vars in styles.css - independent contrast recompute
5. workflow YAML validity + intraday crons vs PRD F2 schedule
6. static presence: redirect script / theme init / breakpoints (browser BLOCKED substitute)
"""
import io, sys, json, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(r"d:\personal\Claude 프로젝트\Stock tools")
sys.path.insert(0, str(ROOT / "src"))
from fetch_data import is_market_open, market_local_today, drop_in_progress  # noqa: E402
import pandas as pd  # noqa: E402

results = []
def check(name, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    print(f"[{tag}] {name}  {detail}")
    results.append((tag, name, detail))

KST = timezone(timedelta(hours=9))
def kst(y, mo, d, h, mi):
    return datetime(y, mo, d, h, mi, tzinfo=KST).astimezone(timezone.utc)

print("== 1. F2 세션 판정 시뮬레이션 (shipped is_market_open) ==")
# 평일 KST 11:00 (화요일): KRX 개장, TWSE 개장, 미국·런던 폐장
t = kst(2026, 8, 4, 11, 0)
check("KST 11:00 화: KRX open", is_market_open("KRX", t))
check("KST 11:00 화: TWSE open", is_market_open("TWSE", t))
check("KST 11:00 화: Nasdaq closed", not is_market_open("Nasdaq", t))
check("KST 11:00 화: LSE closed", not is_market_open("LSE IOB", t))
# 마감 경계: KRX 15:39 open / 15:40 closed (보수적 창)
check("KST 15:39: KRX open (마감 10분 여유 창)", is_market_open("KRX", kst(2026, 8, 4, 15, 39)))
check("KST 15:40: KRX closed", not is_market_open("KRX", kst(2026, 8, 4, 15, 40)))
# 자정 넘는 세션: 미국 KST 새벽 03:00 (수요일 새벽 = 화요일 세션)
check("KST 수 03:00: Nasdaq open (자정 걸침)", is_market_open("Nasdaq", kst(2026, 8, 5, 3, 0)))
check("KST 수 06:10: Nasdaq closed", not is_market_open("Nasdaq", kst(2026, 8, 5, 6, 10)))
# 런던 KST 새벽 01:00 (수요일 새벽 = 화요일 세션)
check("KST 수 01:00: LSE open (자정 걸침)", is_market_open("LSE IOB", kst(2026, 8, 5, 1, 0)))
# 주말: 토요일 새벽 미국장(금요일 세션)만 허용
check("KST 토 03:00: Nasdaq open (금요일 세션 연장)", is_market_open("Nasdaq", kst(2026, 8, 8, 3, 0)))
check("KST 토 11:00: KRX closed (주말)", not is_market_open("KRX", kst(2026, 8, 8, 11, 0)))
check("KST 일 03:00: Nasdaq closed (일요일)", not is_market_open("Nasdaq", kst(2026, 8, 9, 3, 0)))
# 일일 확정 실행 시각 06:30: 전 시장 폐장 (히스토리 순수성)
t630 = kst(2026, 8, 5, 6, 30)
allclosed = not any(is_market_open(x, t630) for x in ("KRX", "TWSE", "LSE IOB", "Nasdaq", "NYSE"))
check("KST 06:30 (일일 확정): 전 시장 폐장", allclosed)

# drop_in_progress simulation: KRX 장중에 당일 행 제거
idx = pd.DatetimeIndex([pd.Timestamp("2026-08-03"), pd.Timestamp("2026-08-04")])
s = pd.Series([100.0, 101.0], index=idx)
dropped = drop_in_progress(s, "KRX", kst(2026, 8, 4, 11, 0))
check("KRX 장중(11:00): 당일 행 제거", len(dropped) == 1 and dropped.index[-1].strftime("%F") == "2026-08-03")
kept = drop_in_progress(s, "KRX", kst(2026, 8, 4, 16, 0))
check("KRX 마감 후(16:00): 당일 행 유지", len(kept) == 2)

print("\n== 2. F6 거래량 원천 대조 (독립 재조회) ==")
import yfinance as yf
hist_skhy = {r["date"]: r for r in json.load(open(ROOT / "src/web/data/history/SKHY.json", encoding="utf-8"))["rows"]}
df = yf.Ticker("SKHY").history(period="1mo", auto_adjust=False)
df.index = df.index.tz_localize(None).normalize()
for ds in ("2026-07-28", "2026-07-30", "2026-07-31"):
    yv = int(df.loc[pd.Timestamp(ds), "Volume"])
    hv = hist_skhy[ds]["vol_dr"]
    check(f"SKHY {ds} vol_dr {hv:,} == Yahoo {yv:,}", hv == yv)
hist_kb = {r["date"]: r for r in json.load(open(ROOT / "src/web/data/history/KB.json", encoding="utf-8"))["rows"]}
df2 = yf.Ticker("105560.KS").history(period="1mo", auto_adjust=False)
df2.index = df2.index.tz_localize(None).normalize()
for ds in ("2026-07-21", "2026-07-29"):
    yv = int(df2.loc[pd.Timestamp(ds), "Volume"])
    hv = hist_kb[ds]["vol_local"]
    check(f"KB {ds} vol_local {hv:,} == Yahoo(원주) {yv:,}", hv == yv)

print("\n== 3. 파일 크기 ==")
sz = (ROOT / "src/web/data/history/TSM.json").stat().st_size
check(f"TSM history 크기 {sz/1e6:.2f}MB (설계 기록 약 1.07MB, 허용 범위)", sz < 2_000_000)

print("\n== 4. WCAG 신규 색 변수 4종 (독립 재계산) ==")
css = (ROOT / "src/web/styles.css").read_text(encoding="utf-8")
def get_var(theme_sel, name):
    m = re.search(re.escape(theme_sel) + r"\s*\{([^}]*)\}", css, re.S)
    m2 = re.search(re.escape(name) + r":\s*(#[0-9a-fA-F]{6})", m.group(1))
    return m2.group(1) if m2 else None
def lum(hexc):
    hexc = hexc.lstrip('#')
    r, g, b = (int(hexc[i:i+2], 16)/255 for i in (0, 2, 4))
    f = lambda c: c/12.92 if c <= 0.03928 else ((c+0.055)/1.055)**2.4
    return 0.2126*f(r) + 0.7152*f(g) + 0.0722*f(b)
def ratio(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb)+0.05)/(min(la, lb)+0.05)
# 설계 문서 8.2 기록값
design = {
    ("light", "--sma20"): 5.02, ("light", "--sma60"): 5.47,
    ("light", "--avg-line"): 5.43, ("light", "--vol-bar"): 4.29,
    ("dark", "--sma20"): 7.68, ("dark", "--sma60"): 8.66,
    ("dark", "--avg-line"): 6.32, ("dark", "--vol-bar"): 5.15,
}
surface = {"light": "#ffffff", "dark": "#1d2128"}
sel = {"light": ':root[data-theme="light"]', "dark": ':root[data-theme="dark"]'}
for (theme, var), claimed in design.items():
    hexv = get_var(sel[theme], var)
    if not hexv:
        check(f"{theme} {var} 존재", False)
        continue
    r = ratio(hexv, surface[theme])
    # 비텍스트(선·바) 기준 3:1
    check(f"{theme} {var} {hexv} vs surface = {r:.2f}:1 (설계 기록 {claimed}, 기준 3:1)",
          r >= 3.0 and abs(r - claimed) < 0.05)

print("\n== 5. 워크플로 (F2 스케줄) ==")
import yaml
d = yaml.safe_load(open(ROOT / ".github/workflows/update-data.yml", encoding="utf-8"))
on = d.get(True) or d.get("on")
crons = [s["cron"] for s in on["schedule"]]
check("YAML 유효 + 스케줄 존재", len(crons) >= 2, str(crons))
check("일일 확정 21:30 UTC 유지", "30 21 * * *" in crons)
# 아시아 세션 (UTC 0~6 매시), 미국 세션 (UTC 14~21 매시), 마감 확정 06:40
asia = [c for c in crons if re.match(r"^0 0-6", c) or "0-6" in c]
us = [c for c in crons if "14-21" in c]
confirm = [c for c in crons if "40 6" in c]
check("아시아 장중 cron 존재", len(asia) >= 1, str(asia))
check("미국 장중 cron 존재", len(us) >= 1, str(us))
check("아시아 마감 확정(06:40 UTC) cron 존재", len(confirm) >= 1, str(confirm))
jobs = d["jobs"]
check("intraday 스텝에 --intraday 플래그", any("--intraday" in json.dumps(j) for j in jobs.values()))

print("\n== 6. 정적 존재 확인 (브라우저 대체 불가 항목의 부분 확인) ==")
kb_page = (ROOT / "src/web/stocks/kb/index.html").read_text(encoding="utf-8")
main = (ROOT / "src/web/index.html").read_text(encoding="utf-8")
check("해시 리다이렉트 스크립트 존재 (전 페이지)", "location.hash.match" in main and "location.hash.match" in kb_page)
check("테마 초기화 스크립트 존재", "prefers-color-scheme" in main)
check("반응형 브레이크포인트 유지 (900px/560px)", "@media (max-width: 900px)" in css and "@media (max-width: 560px)" in css)
check("touch-action pan-y (F1 터치)", "pan-y" in (ROOT / "src/web/app.js").read_text(encoding="utf-8"))
check("noscript 유지", "<noscript>" in kb_page)

n_pass = sum(1 for t, *_ in results if t == "PASS")
n_fail = sum(1 for t, *_ in results if t == "FAIL")
print(f"\nTOTAL: PASS {n_pass} / FAIL {n_fail}")
for t, n, dd in results:
    if t == "FAIL":
        print(" FAIL -", n, "|", dd)
sys.exit(1 if n_fail else 0)
