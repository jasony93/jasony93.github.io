# -*- coding: utf-8 -*-
"""Triage of first-pass anomalies.

A. What is missing on 2026-07-17 for KRX ADR pairs? (which series)
B. TSM fx outliers: list rows with fx outside 15~45, when, and impact on premium
C. Corrected holiday checks:
   - KB 2026-06-19 (US Juneteenth, KRX open)   -> ff_dr=True
   - KB 2026-01-19 (US MLK Day, KRX open)      -> ff_dr=True
   - SMSN 2026-04-06 (UK Easter Monday, KRX open) -> ff_dr=True
   - TSM 2026-02-17 (TW Lunar New Year, NYSE open) -> ff_local=True
   - confirm 2026-05-25 / 2026-06-19(TSM) rows absent because BOTH markets closed
D. implied_local recheck with relative tolerance (rounding-aware)
E. Replacement extra-ticker sample date for 2026-07-17 -> 2026-07-08
"""
import json
from pathlib import Path
import pandas as pd
import yfinance as yf

ROOT = Path(r"D:\personal\Claude 프로젝트\Stock tools")
DATA = ROOT / "src" / "web" / "data"
HIST = DATA / "history"
CFG = {t["id"]: t for t in json.load(open(ROOT / "src" / "config" / "tickers.json", encoding="utf-8"))["tickers"]}

def series(sym):
    df = yf.Ticker(sym).history(period="max", auto_adjust=False)
    s = df["Close"].dropna()
    s.index = pd.DatetimeIndex(s.index.tz_localize(None)).normalize()
    return s[~s.index.duplicated(keep="last")].sort_index()

def rows_of(tid):
    return {r["date"]: r for r in json.load(open(HIST / f"{tid}.json", encoding="utf-8"))["rows"]}

def prem(p_dr, fx, p_local, r):
    return (p_dr * fx / (p_local * r) - 1.0) * 100.0

print("== A. 2026-07-17 which series missing (SKM pair) ==")
d = pd.Timestamp("2026-07-17")
for sym in ("SKM", "017670.KS", "KRW=X", "KB", "105560.KS"):
    s = series(sym)
    print(f"  {sym:12s} has 2026-07-17: {d in s.index}")
skm_rows = rows_of("SKM")
print("  pipeline SKM row 2026-07-17:", skm_rows.get("2026-07-17"))

print("\n== B. TSM fx outliers (outside 15~45) ==")
tsm = rows_of("TSM")
bad = [r for r in tsm.values() if not (15 <= r["fx"] <= 45)]
print(f"  count={len(bad)} of {len(tsm)}")
if bad:
    dates = [r["date"] for r in bad]
    print("  first:", dates[0], " last:", dates[-1])
    print("  examples:", [(r['date'], r['fx'], r['premium']) for r in bad[:8]])
    years = {}
    for r in bad:
        years[r["date"][:4]] = years.get(r["date"][:4], 0) + 1
    print("  by year:", dict(sorted(years.items())))
    # worst premium distortion among bad rows
    worst = max(bad, key=lambda r: abs(r["premium"]))
    print("  worst premium among bad-fx rows:", worst)
# does any bad fx fall in the default 1Y view window?
recent_bad = [r for r in bad if r["date"] >= "2025-08-03"]
print("  bad fx within last 1Y:", len(recent_bad))

print("\n== B2. KRW=X early data sanity (KB rows fx<950) ==")
kb = rows_of("KB")
kbad = [r for r in kb.values() if r["fx"] < 950]
print(f"  count={len(kbad)}; range:", (kbad[0]['date'], kbad[-1]['date']) if kbad else None)

print("\n== C. corrected holiday checks ==")
def chk(name, cond, detail=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}  {detail}")

r = kb.get("2026-06-19"); pv = kb.get("2026-06-18")
chk("KB 2026-06-19 (US Juneteenth): ff_dr=True, carried from 06-18",
    r is not None and r["ff_dr"] and not r["ff_local"] and pv and r["p_dr"] == pv["p_dr"], f"row={r}")
r = kb.get("2026-01-19"); pv = kb.get("2026-01-16")
chk("KB 2026-01-19 (US MLK Day): ff_dr=True, carried from 01-16",
    r is not None and r["ff_dr"] and not r["ff_local"] and pv and r["p_dr"] == pv["p_dr"], f"row={r}")
smsn = rows_of("SMSN")
r = smsn.get("2026-04-06"); pv = smsn.get("2026-04-03")
chk("SMSN 2026-04-06 (UK Easter Monday): ff_dr=True",
    r is not None and r["ff_dr"] and not r["ff_local"], f"row={r}")
r = tsm.get("2026-02-17");
chk("TSM 2026-02-17 (TW Lunar New Year): ff_local=True",
    r is not None and r["ff_local"] and not r["ff_dr"], f"row={r}")
# both-closed omissions
us = series("KB"); kr = series("105560.KS")
d1 = pd.Timestamp("2026-05-25")
chk("2026-05-25 both closed (KR substitute holiday + US Memorial Day) -> omitted",
    d1 not in us.index and d1 not in kr.index and "2026-05-25" not in kb,
    f"US traded={d1 in us.index} KR traded={d1 in kr.index}")
tw = series("2330.TW"); tsm_us = series("TSM")
d2 = pd.Timestamp("2026-06-19")
chk("TSM 2026-06-19 both closed (TW Dragon Boat + US Juneteenth) -> omitted",
    d2 not in tw.index and d2 not in tsm_us.index and "2026-06-19" not in tsm,
    f"US traded={d2 in tsm_us.index} TW traded={d2 in tw.index}")

print("\n== D. implied_local relative tolerance ==")
meta = json.load(open(DATA / "meta.json", encoding="utf-8"))
for tid in ("SKHY", "PKX"):
    e = meta["tickers"][tid]; s = e["snapshot"]
    implied = s["p_dr"] * s["fx"] / e["ratio"]
    rel = abs(implied - s["implied_local"]) / s["implied_local"]
    chk(f"{tid} implied_local relative diff < 1e-6 (rounding artifact)", rel < 1e-6, f"rel={rel:.2e}")

print("\n== E. replacement sample date 2026-07-08 for extra tickers ==")
for tid in ("SKM", "WF", "PKX", "KEP", "LPL"):
    t = CFG[tid]
    dr, loc, fx = series(t["dr_yahoo"]), series(t["local_yahoo"]), series(t["fx_yahoo"])
    d = pd.Timestamp("2026-07-08")
    if d in dr.index and d in loc.index and d in fx.index:
        m = prem(float(dr.loc[d]), float(fx.loc[d]), float(loc.loc[d]), t["ratio"])
        p = rows_of(tid).get("2026-07-08", {}).get("premium")
        chk(f"{tid} 2026-07-08 manual {m:+.4f} vs pipeline {p}",
            p is not None and abs(m - p) <= 0.1, f"diff {abs(m-(p or 0)):.6f}%p")
    else:
        chk(f"{tid} 2026-07-08 sources traded", False)
