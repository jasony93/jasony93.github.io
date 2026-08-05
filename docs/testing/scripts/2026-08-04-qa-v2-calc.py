# -*- coding: utf-8 -*-
"""F3/F5/F6 expected values computed independently in Python (from history JSON).

Outputs a JSON of expected values that the browser DOM checks will compare against.
Aggregation rules re-implemented from PRD (not from app.js):
- Week = ISO Mon~Sun, value = last trading day's row, ff flags inherited
- Month = calendar month, same
- SMA_n(d) = mean of last n daily premiums up to d (only when >= n points)
- Period average = mean of premiums in displayed window
- Volume for week/month = sum of non-null volumes in the group
"""
import io, sys, json, datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(r"d:\personal\Claude 프로젝트\Stock tools")

def rows_of(tid):
    return json.load(open(ROOT / "src" / "web" / "data" / "history" / f"{tid}.json",
                          encoding="utf-8"))["rows"]

def iso_monday(iso):
    d = datetime.date.fromisoformat(iso)
    return (d - datetime.timedelta(days=d.weekday())).isoformat()

def group(rows, unit):
    out = []
    curk, cur = None, None
    for r in rows:
        k = iso_monday(r["date"]) if unit == "W" else r["date"][:7]
        if k != curk:
            if cur: out.append(cur)
            curk, cur = k, {"key": k, "rows": []}
        cur["rows"].append(r)
    if cur: out.append(cur)
    return out

exp = {}

# ---- F3 TSM MAX month: count + 3 sample months ----
tsm = rows_of("TSM")
months = group(tsm, "M")
exp["tsm_month_count"] = len(months)
samples = {}
for key in ("2026-05", "2025-11", "2024-03"):
    g = [x for x in months if x["key"] == key][0]
    last = g["rows"][-1]
    samples[key] = {"date": last["date"], "premium": last["premium"]}
exp["tsm_month_samples"] = samples

# ---- F3 KB weeks: 3 samples + ff inheritance week ----
kb = rows_of("KB")
weeks = group(kb, "W")
wsamples = {}
for key in ("2026-07-20", "2026-06-15", "2026-03-02"):
    g = [x for x in weeks if x["key"] == key][0]
    last = g["rows"][-1]
    wsamples[key] = {"date": last["date"], "premium": last["premium"],
                     "ff_dr": last["ff_dr"], "ff_local": last["ff_local"],
                     "vol_dr_sum": sum(r["vol_dr"] for r in g["rows"] if r["vol_dr"] is not None),
                     "vol_local_sum": sum(r["vol_local"] for r in g["rows"] if r["vol_local"] is not None)}
exp["kb_week_samples"] = wsamples
# week containing 2026-06-19 (US Juneteenth, Friday, ff_dr) - last trading day = 6/19
g619 = [x for x in weeks if x["key"] == "2026-06-15"][0]
exp["kb_week_0615_last_is_ff_dr"] = g619["rows"][-1]["date"] == "2026-06-19" and g619["rows"][-1]["ff_dr"]

# ---- F5 SMA: KB last daily point SMA20/SMA60 ----
prem = [r["premium"] for r in kb]
exp["kb_last_date"] = kb[-1]["date"]
exp["kb_sma20_last"] = round(sum(prem[-20:]) / 20, 4)
exp["kb_sma60_last"] = round(sum(prem[-60:]) / 60, 4)
# SMA20 at an interior date too (2026-07-01)
idx = next(i for i, r in enumerate(kb) if r["date"] == "2026-07-01")
exp["kb_sma20_20260701"] = round(sum(prem[idx-19:idx+1]) / 20, 4)

# ---- F5 period average: KB 1Y window (window = last date - 366d, exclusive lo) ----
last_ms = datetime.date.fromisoformat(kb[-1]["date"])
lo = last_ms - datetime.timedelta(days=366)
win = [r["premium"] for r in kb if datetime.date.fromisoformat(r["date"]) > lo]
exp["kb_1y_avg"] = round(sum(win) / len(win), 4)
exp["kb_1y_count"] = len(win)

# ---- F6: daily volume samples (KB 3 days) vs history ----
vol_samples = {}
for r in kb[-40:]:
    if r["date"] in ("2026-07-28", "2026-07-30", "2026-07-31"):
        vol_samples[r["date"]] = {"vol_dr": r["vol_dr"], "vol_local": r["vol_local"]}
exp["kb_vol_samples"] = vol_samples
# ff day volume null check (2026-06-19 ff_dr -> vol_dr None, vol_local not None)
r619 = next(r for r in kb if r["date"] == "2026-06-19")
exp["kb_0619_vol"] = {"vol_dr": r619["vol_dr"], "vol_local": r619["vol_local"],
                      "ff_dr": r619["ff_dr"]}

# ---- SKHY short series: rows < 60 -> SMA60 데이터 부족 ----
skhy = rows_of("SKHY")
exp["skhy_row_count"] = len(skhy)

out_path = Path(__file__).parent / "v2_expected.json"
json.dump(exp, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(exp, ensure_ascii=False, indent=1))
print("\nwritten:", out_path)
