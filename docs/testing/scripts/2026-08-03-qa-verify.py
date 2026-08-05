# -*- coding: utf-8 -*-
"""QA independent verification - does NOT import fetch_data (formula reimplemented).

Checks (dates/tickers deliberately different from dev team's verify_samples.py):
 1. Manual recalc vs pipeline JSON: 3 dates x 3 tickers (SKHY/TSM/SMSN) on
    2026-07-14 / 2026-07-21 / 2026-07-24, tolerance +/-0.1%p (PRD 5)
 2. Extra tickers with tricky ratios: SKM(5/9), WF(3), PKX(0.25), KEP(0.5), LPL(0.5)
    on 2026-06-12 and 2026-07-17
 3. SKHY IPO check per PRD rev.2: (a) FX 1385 -> ~ -5.6%  (b) actual FX on
    2026-07-09 -> within +/-1%p of press-reported +3%
 4. FX cross-application: ALL rows of ALL 11 tickers (not just recent 250)
 5. Holiday forward-fill on dates the dev team did NOT use:
    - 2026-07-03 US Independence Day observed (KRX open) -> KB ff_dr, value = 07-02 DR close
    - 2026-05-05 Korean Children's Day (US open)          -> KB ff_local, value = 05-04 local close
    - 2026-05-25 US Memorial Day + UK Spring Bank holiday -> KB ff_dr and SMSN ff_dr
    - 2026-06-19 Taiwan Dragon Boat Festival (US open)    -> TSM ff_local
    - weekend absence: 2026-08-01, 2026-08-02 not in any grid
 6. Snapshot internal consistency: premium/implied_local recomputable from its own
    p_dr/fx/p_local/ratio; spark = subset of history rows within last 30 calendar days
 7. History coverage: >= 1 year for all except SKHY (>= listing 2026-07-10);
    ratio-changed tickers start exactly at history_start
 8. Config ratios vs PRD 3.0 fixed values (11 tickers), read directly from JSON
"""
import json, sys
from pathlib import Path
import pandas as pd
import yfinance as yf

ROOT = Path(r"D:\personal\Claude 프로젝트\Stock tools")
DATA = ROOT / "src" / "web" / "data"
HIST = DATA / "history"
CFG = json.load(open(ROOT / "src" / "config" / "tickers.json", encoding="utf-8"))

results = []
def check(name, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    print(f"[{tag}] {name}  {detail}")
    results.append((tag, name, detail))

def prem(p_dr, fx, p_local, r):  # independent reimplementation of PRD 3.3
    return (p_dr * fx / (p_local * r) - 1.0) * 100.0

def series(sym):
    df = yf.Ticker(sym).history(period="max", auto_adjust=False)
    s = df["Close"].dropna()
    s.index = pd.DatetimeIndex(s.index.tz_localize(None)).normalize()
    return s[~s.index.duplicated(keep="last")].sort_index()

def rows_of(tid):
    return {r["date"]: r for r in json.load(open(HIST / f"{tid}.json", encoding="utf-8"))["rows"]}

meta = json.load(open(DATA / "meta.json", encoding="utf-8"))
tickers = {t["id"]: t for t in CFG["tickers"]}

# ---------- 8. config ratios vs PRD 3.0 ----------
print("== 8. config ratio vs PRD 3.0 ==")
prd = {"SKHY": 0.1, "SMSN": 25, "TSM": 5, "PKX": 0.25, "SKM": 5/9,
       "LPL": 0.5, "KEP": 0.5, "KB": 1, "SHG": 1, "WF": 3, "KT": 0.5}
check("config has exactly 11 tickers", len(tickers) == 11, str(len(tickers)))
for tid, r in prd.items():
    ok = tid in tickers and abs(tickers[tid]["ratio"] - r) < 1e-12
    check(f"ratio {tid} == {r}", ok, f"config={tickers.get(tid,{}).get('ratio')}")

# ---------- 1+2. manual recalc ----------
print("\n== 1+2. manual recalc vs pipeline (+/-0.1%p) ==")
cache = {}
def S(sym):
    if sym not in cache: cache[sym] = series(sym)
    return cache[sym]

plan = [
    ("SKHY", ["2026-07-14", "2026-07-21", "2026-07-24"]),
    ("TSM",  ["2026-07-14", "2026-07-21", "2026-07-24"]),
    ("SMSN", ["2026-07-14", "2026-07-21", "2026-07-24"]),
    ("SKM",  ["2026-06-12", "2026-07-17"]),
    ("WF",   ["2026-06-12", "2026-07-17"]),
    ("PKX",  ["2026-06-12", "2026-07-17"]),
    ("KEP",  ["2026-06-12", "2026-07-17"]),
    ("LPL",  ["2026-06-12", "2026-07-17"]),
]
for tid, dates in plan:
    t = tickers[tid]
    dr, loc, fx = S(t["dr_yahoo"]), S(t["local_yahoo"]), S(t["fx_yahoo"])
    rows = rows_of(tid)
    for ds in dates:
        d = pd.Timestamp(ds)
        if d not in dr.index or d not in loc.index or d not in fx.index:
            check(f"{tid} {ds} all three sources traded", False, "source missing - replace sample date")
            continue
        m = prem(float(dr.loc[d]), float(fx.loc[d]), float(loc.loc[d]), t["ratio"])
        p = rows.get(ds, {}).get("premium")
        ok = p is not None and abs(m - p) <= 0.1
        check(f"{tid} {ds} manual {m:+.4f} vs pipeline {p}", ok,
              f"diff {abs(m - (p if p is not None else 0)):.6f}%p")
        # also confirm the pipeline row is not marked forward-filled on a full trading day
        rr = rows.get(ds)
        if rr:
            check(f"{tid} {ds} no ff flags on full trading day",
                  not (rr["ff_dr"] or rr["ff_local"] or rr["ff_fx"]),
                  f"ff_dr={rr['ff_dr']} ff_local={rr['ff_local']} ff_fx={rr['ff_fx']}")

# ---------- 3. SKHY IPO ----------
print("\n== 3. SKHY IPO check (PRD rev.2 criteria) ==")
a = prem(149.0, 1385.0, 2186000.0, 0.1)
check(f"(a) FX 1385 example -> {a:+.3f}% ~= -5.6%", abs(a - (-5.597)) < 0.05)
fxk = S("KRW=X")
d = pd.Timestamp("2026-07-09")
fx709 = float(fxk.loc[:d].iloc[-1])
b = prem(149.0, fx709, 2186000.0, 0.1)
check(f"(b) actual FX {fx709:.2f} -> {b:+.2f}% within +/-1%p of press +3%",
      abs(b - 3.0) <= 1.0, f"diff {abs(b-3.0):.2f}%p")

# ---------- 4. FX cross-application, ALL rows ----------
print("\n== 4. FX cross-application (all rows) ==")
for tid, t in tickers.items():
    rows = rows_of(tid)
    vals = [r["fx"] for r in rows.values()]
    if t["local_currency"] == "TWD":
        ok = all(15 <= v <= 45 for v in vals)
        check(f"{tid} all fx in TWD range 15~45", ok, f"min={min(vals):.2f} max={max(vals):.2f} n={len(vals)}")
    else:
        ok = all(700 <= v <= 2100 for v in vals)
        check(f"{tid} all fx in KRW range 700~2100", ok, f"min={min(vals):.2f} max={max(vals):.2f} n={len(vals)}")

# ---------- 5. holiday forward-fill (QA-selected dates) ----------
print("\n== 5. holiday forward-fill ==")
kb, smsn, tsm = rows_of("KB"), rows_of("SMSN"), rows_of("TSM")

r = kb.get("2026-07-03"); pv = kb.get("2026-07-02")
check("KB 2026-07-03 (US Jul4 observed): ff_dr=True, DR carried from 07-02",
      r is not None and r["ff_dr"] and not r["ff_local"] and pv is not None and r["p_dr"] == pv["p_dr"],
      f"row={r}")
r = kb.get("2026-05-05"); pv = kb.get("2026-05-04")
check("KB 2026-05-05 (KR Children's Day): ff_local=True, local carried from 05-04",
      r is not None and r["ff_local"] and not r["ff_dr"] and pv is not None and r["p_local"] == pv["p_local"],
      f"row={r}")
r = kb.get("2026-05-25")
check("KB 2026-05-25 (US Memorial Day): ff_dr=True",
      r is not None and r["ff_dr"] and not r["ff_local"], f"row={r}")
r = smsn.get("2026-05-25")
check("SMSN 2026-05-25 (UK Spring Bank Holiday): ff_dr=True",
      r is not None and r["ff_dr"] and not r["ff_local"], f"row={r}")
r = tsm.get("2026-06-19"); pv = tsm.get("2026-06-18")
check("TSM 2026-06-19 (TW Dragon Boat): ff_local=True, local carried from 06-18",
      r is not None and r["ff_local"] and not r["ff_dr"] and pv is not None and r["p_local"] == pv["p_local"],
      f"row={r}")
for wd in ("2026-08-01", "2026-08-02"):
    absent = all(wd not in rows_of(tid) for tid in tickers)
    check(f"{wd} (weekend) absent from every grid", absent)

# forward-filled row premium must equal recompute with carried values
r = kb.get("2026-07-03")
if r:
    m = prem(r["p_dr"], r["fx"], r["p_local"], tickers["KB"]["ratio"])
    check("KB 2026-07-03 premium consistent with carried values",
          abs(m - r["premium"]) < 0.001, f"recomputed {m:+.4f} vs stored {r['premium']}")

# ---------- 6. snapshot + spark consistency ----------
print("\n== 6. snapshot / spark internal consistency ==")
for tid in meta["order"]:
    e = meta["tickers"][tid]
    s = e["snapshot"]
    m = prem(s["p_dr"], s["fx"], s["p_local"], e["ratio"])
    check(f"{tid} snapshot premium consistent", abs(m - s["premium"]) < 0.001,
          f"recomputed {m:+.4f} vs stored {s['premium']}")
    implied = s["p_dr"] * s["fx"] / e["ratio"]
    check(f"{tid} implied_local consistent", abs(implied - s["implied_local"]) < 0.01,
          f"{implied:.2f} vs {s['implied_local']}")
    rows = rows_of(tid)
    last = pd.Timestamp(e["last_date"]); cutoff = last - pd.Timedelta(days=30)
    expect = [[dstr, rows[dstr]["premium"]] for dstr in sorted(rows) if pd.Timestamp(dstr) >= cutoff]
    check(f"{tid} spark == last-30d history subset ({len(expect)} pts)", e["spark"] == expect)

# ---------- 7. coverage ----------
print("\n== 7. history coverage ==")
today = pd.Timestamp("2026-08-03")
for tid in meta["order"]:
    e = meta["tickers"][tid]
    first, last = pd.Timestamp(e["first_date"]), pd.Timestamp(e["last_date"])
    if tid == "SKHY":
        check("SKHY history starts at listing 2026-07-10", e["first_date"] == "2026-07-10")
    else:
        check(f"{tid} >= 1 year of history", (today - first).days >= 365,
              f"first={e['first_date']}")
    check(f"{tid} last date fresh (within 4 days)", (today - last).days <= 4, f"last={e['last_date']}")
hs = {"SMSN": "2018-05-04", "SKM": "2021-10-28", "SHG": "2012-10-15"}
for tid, d0 in hs.items():
    check(f"{tid} history starts exactly at ratio-valid date {d0}",
          meta["tickers"][tid]["first_date"] == d0,
          f"first={meta['tickers'][tid]['first_date']}")

n_pass = sum(1 for t, *_ in results if t == "PASS")
n_fail = sum(1 for t, *_ in results if t == "FAIL")
print(f"\nTOTAL: PASS {n_pass} / FAIL {n_fail}")
if n_fail:
    print("FAILED ITEMS:")
    for t, n, d in results:
        if t == "FAIL": print(" -", n, d)
sys.exit(1 if n_fail else 0)
