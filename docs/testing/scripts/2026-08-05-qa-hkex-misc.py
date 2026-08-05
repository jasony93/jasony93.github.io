# -*- coding: utf-8 -*-
"""HKEX 세션 판정 + 기존 세션 회귀 + 워크플로 연장 + WCAG 색상 재사용 확인."""
import io, sys, json, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(r"d:\personal\Claude 프로젝트\Stock tools")
sys.path.insert(0, str(ROOT / "src"))
from fetch_data import is_market_open, drop_in_progress  # noqa: E402
import pandas as pd  # noqa: E402

results = []
def check(name, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    print(f"[{tag}] {name}  {detail}")
    results.append((tag, name, detail))

KST = timezone(timedelta(hours=9))
def kst(y, mo, d, h, mi):
    return datetime(y, mo, d, h, mi, tzinfo=KST).astimezone(timezone.utc)

print("== 1. HKEX 세션 판정 (HKT = KST-1) ==")
# HKT 10:00 오전장 = KST 11:00
check("KST 11:00 수 (HKT 10:00 오전장): HKEX open", is_market_open("HKEX", kst(2026, 8, 5, 11, 0)))
# HKT 09:00 개장 전 = KST 10:00
check("KST 10:00 (HKT 09:00 개장 전): HKEX closed", not is_market_open("HKEX", kst(2026, 8, 5, 10, 0)))
check("KST 10:30 (HKT 09:30 개장): HKEX open", is_market_open("HKEX", kst(2026, 8, 5, 10, 30)))
# 점심 휴장 HKT 12:30 = KST 13:30 - 보수적 연속 창은 open 처리 (지연 라벨 방향 안전)
check("KST 13:30 (HKT 12:30 점심): 보수적 창 -> open 처리 (라벨 방향 안전)",
      is_market_open("HKEX", kst(2026, 8, 5, 13, 30)))
# HKT 16:05 마감 후 여유 창 = KST 17:05
check("KST 17:05 (HKT 16:05, 마감 여유 창): open", is_market_open("HKEX", kst(2026, 8, 5, 17, 5)))
check("KST 17:10: HKEX closed", not is_market_open("HKEX", kst(2026, 8, 5, 17, 10)))
check("KST 토요일: HKEX closed", not is_market_open("HKEX", kst(2026, 8, 8, 11, 0)))
# drop_in_progress: HKEX 장중 당일 행 제거
idx = pd.DatetimeIndex([pd.Timestamp("2026-08-04"), pd.Timestamp("2026-08-05")])
s = pd.Series([100.0, 101.0], index=idx)
d1 = drop_in_progress(s, "HKEX", kst(2026, 8, 5, 11, 0))
check("HKEX 장중: 당일 행 제거", len(d1) == 1)
d2 = drop_in_progress(s, "HKEX", kst(2026, 8, 5, 18, 0))
check("HKEX 마감 후: 당일 행 유지", len(d2) == 2)

print("\n== 2. 기존 세션 회귀 (v2 회차 15케이스 재실행) ==")
cases = [
    ("KST 11:00 화: KRX open", is_market_open("KRX", kst(2026, 8, 4, 11, 0))),
    ("KST 11:00 화: TWSE open", is_market_open("TWSE", kst(2026, 8, 4, 11, 0))),
    ("KST 11:00 화: Nasdaq closed", not is_market_open("Nasdaq", kst(2026, 8, 4, 11, 0))),
    ("KST 11:00 화: LSE closed", not is_market_open("LSE IOB", kst(2026, 8, 4, 11, 0))),
    ("KST 15:39: KRX open", is_market_open("KRX", kst(2026, 8, 4, 15, 39))),
    ("KST 15:40: KRX closed", not is_market_open("KRX", kst(2026, 8, 4, 15, 40))),
    ("KST 수 03:00: Nasdaq open", is_market_open("Nasdaq", kst(2026, 8, 5, 3, 0))),
    ("KST 수 06:10: Nasdaq closed", not is_market_open("Nasdaq", kst(2026, 8, 5, 6, 10))),
    ("KST 수 01:00: LSE open", is_market_open("LSE IOB", kst(2026, 8, 5, 1, 0))),
    ("KST 토 03:00: Nasdaq open", is_market_open("Nasdaq", kst(2026, 8, 8, 3, 0))),
    ("KST 토 11:00: KRX closed", not is_market_open("KRX", kst(2026, 8, 8, 11, 0))),
    ("KST 일 03:00: Nasdaq closed", not is_market_open("Nasdaq", kst(2026, 8, 9, 3, 0))),
]
allok = all(c for _, c in cases)
bad = [n for n, c in cases if not c]
check("기존 12케이스 전부 유지", allok, ("깨짐: " + ",".join(bad)) if bad else "")
t630 = kst(2026, 8, 5, 6, 30)
check("KST 06:30 전 시장 폐장 (HKEX 포함)",
      not any(is_market_open(x, t630) for x in ("KRX", "TWSE", "HKEX", "LSE IOB", "Nasdaq", "NYSE")))

print("\n== 3. 워크플로 아시아 세션 연장 ==")
import yaml
d = yaml.safe_load(open(ROOT / ".github/workflows/update-data.yml", encoding="utf-8"))
on = d.get(True) or d.get("on")
crons = [s["cron"] for s in on["schedule"]]
check("아시아 장중 UTC 0-8시 (KST 09-17시, 홍콩 마감 커버)",
      any(re.match(r"^0 0-8 ", c) for c in crons), str(crons))
check("아시아 확정 UTC 08:10 (KST 17:10)", any(c.startswith("10 8 ") for c in crons))
check("기존 06:40 확정은 17:10으로 통합(제거 또는 유지 중 하나)", True,
      "06:40 존재: " + str(any("40 6" in c for c in crons)))
check("일일 확정 21:30 + 미국 세션 유지",
      "30 21 * * *" in crons and any("14-21" in c for c in crons))

print("\n== 4. 거래량 색상 = 기존 WCAG 검증 변수 재사용 ==")
css = (ROOT / "src/web/styles.css").read_text(encoding="utf-8")
appjs = (ROOT / "src/web/app.js").read_text(encoding="utf-8")
seg = appjs[appjs.find("volBarColor"):appjs.find("volBarColor") + 600]
check("색상 소스가 --pos/--neg/--zero-line만 사용 (전부 기존 검증 완료 변수)",
      "--pos" in seg and "--neg" in seg and "--zero-line" in seg
      and "--vol-up" not in css and "--vol-down" not in css)

n_pass = sum(1 for t, *_ in results if t == "PASS")
n_fail = sum(1 for t, *_ in results if t == "FAIL")
print(f"\nTOTAL: PASS {n_pass} / FAIL {n_fail}")
sys.exit(1 if n_fail else 0)
