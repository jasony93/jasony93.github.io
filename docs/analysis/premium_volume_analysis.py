"""프리미엄-거래량 상관관계 및 평균회귀 분석 (2026-08-05).

사용자 가설: "프리미엄이 +/- 한쪽으로 크게 기울면 시장에서 이를 해소하려는
심리가 있을 것이다" -> 검증 대상은 (1) 괴리 크기와 거래량의 동행성
(2) 극단 프리미엄 이후의 평균회귀 (3) 전환 자유도(BABA fungible vs SKHY/TSM
제한)에 따른 차이.

입력: src/web/data/history/<ID>.json (파이프라인 생성물 - 읽기만 함)
출력: 표준출력 (결과 문서 docs/development/2026-08-05-premium-volume-analysis.md의 근거)

실행:
    python docs/analysis/premium_volume_analysis.py
    python docs/analysis/premium_volume_analysis.py --json   (기계 판독용)

의존성: 표준 라이브러리 + pandas(기존 의존성)만 사용. scipy 미설치 환경이므로
상관계수·p-value(t 근사, 정규 근사 CDF)를 직접 구현한다.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HIST = ROOT / "src" / "web" / "data" / "history"
META = ROOT / "src" / "web" / "data" / "meta.json"

# 전환 자유도 그룹 (기획 문서 근거: BABA 완전 fungible / SKHY·TSM 전환 제한)
GROUPS = {
    "BABA": "fungible(자유)",
    "SKHY": "제한(한도 소진)",
    "TSM": "제한(승인제)",
}


# ---------- 통계 유틸 (직접 구현) ----------

def mean(xs):
    return sum(xs) / len(xs)


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = mean(xs), mean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def rankdata(xs):
    """평균 순위(동점 처리) - 스피어만용."""
    idx = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(idx):
        j = i
        while j + 1 < len(idx) and xs[idx[j + 1]] == xs[idx[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[idx[k]] = avg
        i = j + 1
    return ranks


def spearman(xs, ys):
    if len(xs) < 3:
        return None
    return pearson(rankdata(xs), rankdata(ys))


def _norm_cdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def corr_pvalue(r, n):
    """상관계수의 양측 p-value. t = r*sqrt((n-2)/(1-r^2)), 큰 n에서 정규 근사."""
    if r is None or n < 4 or abs(r) >= 1:
        return None
    t = r * math.sqrt((n - 2) / (1 - r * r))
    # df가 크므로(수백~수천) 정규 근사 오차는 무시 가능
    return 2 * (1 - _norm_cdf(abs(t)))


def welch_t_pvalue(a, b):
    """두 표본 평균 차이의 양측 p-value (Welch, 정규 근사)."""
    if len(a) < 3 or len(b) < 3:
        return None
    ma, mb = mean(a), mean(b)
    va = sum((x - ma) ** 2 for x in a) / (len(a) - 1)
    vb = sum((x - mb) ** 2 for x in b) / (len(b) - 1)
    se = math.sqrt(va / len(a) + vb / len(b))
    if se == 0:
        return None
    return 2 * (1 - _norm_cdf(abs(ma - mb) / se))


def one_sample_p(xs, mu=0.0):
    """평균이 mu와 다른지 (양측, 정규 근사)."""
    if len(xs) < 3:
        return None
    m = mean(xs)
    v = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    se = math.sqrt(v / len(xs))
    if se == 0:
        return None
    return 2 * (1 - _norm_cdf(abs(m - mu) / se))


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def quantile(xs, q):
    s = sorted(xs)
    if not s:
        return None
    pos = q * (len(s) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def stdev(xs):
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) if len(xs) > 1 else 0.0


# ---------- 데이터 로드 ----------

def load_rows(tid):
    with open(HIST / f"{tid}.json", encoding="utf-8") as f:
        return json.load(f)["rows"]


def load_ids():
    with open(META, encoding="utf-8") as f:
        return json.load(f)["order"]


def prep(rows, vol_key):
    """분석용 시리즈 구성.

    - 이월 포인트(해당 시장 휴장)는 거래량이 null이므로 거래량 분석에서 제외.
    - 거래량은 로그 변환(장기 추세·스케일 차이 완화) 후 250거래일 롤링 중앙값
      대비 상대값으로 정규화한다 (거래량의 구조적 증가 추세 제거).
    """
    out = []
    for r in rows:
        v = r.get(vol_key)
        out.append({
            "date": r["date"], "premium": r["premium"],
            "vol": None if v in (None, 0) else float(v),
        })
    # 롤링 중앙값(과거 250개, 현재 제외 - 룩어헤드 방지)
    hist = []
    for rec in out:
        if rec["vol"] is not None and len(hist) >= 60:
            med = median(hist[-250:])
            rec["logvol_rel"] = math.log(rec["vol"] / med) if med > 0 else None
        else:
            rec["logvol_rel"] = None
        if rec["vol"] is not None:
            hist.append(rec["vol"])
    return out


# ---------- 분석 항목 ----------

def analyze_ticker(tid):
    rows = load_rows(tid)
    res = {"id": tid, "n_rows": len(rows),
           "first": rows[0]["date"], "last": rows[-1]["date"],
           "group": GROUPS.get(tid, "기타")}

    prem_all = [r["premium"] for r in rows]
    res["premium_mean"] = mean(prem_all)
    res["premium_sd"] = stdev(prem_all)
    res["premium_abs_median"] = median([abs(p) for p in prem_all])

    for series, vol_key in (("dr", "vol_dr"), ("local", "vol_local")):
        recs = prep(rows, vol_key)
        # (1) |P| vs 정규화 로그 거래량 (동시점)
        pairs = [(abs(r["premium"]), r["logvol_rel"]) for r in recs
                 if r["logvol_rel"] is not None]
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        n = len(pairs)
        r_p = pearson(xs, ys) if n >= 30 else None
        r_s = spearman(xs, ys) if n >= 30 else None
        res[f"absP_vol_{series}"] = {
            "n": n, "pearson": r_p, "spearman": r_s,
            "p_pearson": corr_pvalue(r_p, n), "p_spearman": corr_pvalue(r_s, n),
        }
        # (2) |delta P| vs 거래량 (동시점) - 변동성-거래량 관계
        dpairs = []
        for i in range(1, len(recs)):
            if recs[i]["logvol_rel"] is None:
                continue
            dpairs.append((abs(recs[i]["premium"] - recs[i - 1]["premium"]),
                           recs[i]["logvol_rel"]))
        n2 = len(dpairs)
        r_p2 = pearson([d[0] for d in dpairs], [d[1] for d in dpairs]) if n2 >= 30 else None
        r_s2 = spearman([d[0] for d in dpairs], [d[1] for d in dpairs]) if n2 >= 30 else None
        res[f"absDelta_vol_{series}"] = {
            "n": n2, "pearson": r_p2, "spearman": r_s2,
            "p_pearson": corr_pvalue(r_p2, n2), "p_spearman": corr_pvalue(r_s2, n2),
        }
        # (3) 시차 상관: t일 거래량 vs t+1일 프리미엄 변화(부호 있는), 그리고
        #     "해소 방향" 검증용으로 t일 프리미엄 부호를 곱한 값도 본다.
        lag_x, lag_y, lag_resolve = [], [], []
        for i in range(len(recs) - 1):
            if recs[i]["logvol_rel"] is None:
                continue
            dnext = recs[i + 1]["premium"] - recs[i]["premium"]
            lag_x.append(recs[i]["logvol_rel"])
            lag_y.append(dnext)
            # 해소량: 프리미엄이 양수면 하락이 해소(+), 음수면 상승이 해소(+)
            sign = 1 if recs[i]["premium"] > 0 else (-1 if recs[i]["premium"] < 0 else 0)
            lag_resolve.append(-sign * dnext)
        n3 = len(lag_x)
        r_lag = pearson(lag_x, lag_y) if n3 >= 30 else None
        r_res = pearson(lag_x, lag_resolve) if n3 >= 30 else None
        res[f"lagVol_nextDelta_{series}"] = {
            "n": n3, "pearson": r_lag, "p": corr_pvalue(r_lag, n3),
        }
        res[f"lagVol_resolution_{series}"] = {
            "n": n3, "pearson": r_res, "p": corr_pvalue(r_res, n3),
        }

    # (4) 평균회귀: z-score(과거 250거래일 롤링 평균·표준편차, 현재 제외) 극단 이후
    #     N일 프리미엄 변화. "해소" = 프리미엄이 0 방향으로 이동한 양(부호 정규화).
    res["reversion"] = reversion_test(rows)
    # (5) 분위 기반(z-score 대안): 상하위 10% 분위 극단
    res["reversion_q"] = reversion_test(rows, method="quantile")
    # (6) 회귀 속도(AR1)·극단 시점 데이터 품질 진단
    res["ar1"] = ar1_and_halflife(rows)
    res["diag"] = extreme_diagnostics(rows)
    # (7) 지속/일시 성분 분해 + 평활 후 회귀 (인공물 분리)
    res["decomp"] = variance_decomposition(rows)
    res["smooth_rev"] = smoothed_reversion(rows)
    return res


def ar1_and_halflife(rows):
    """프리미엄의 AR(1) 계수와 반감기 - 평균회귀 속도의 스케일 무관 지표.

    P[t+1] - m = phi * (P[t] - m) + e  ->  phi < 1 이면 회귀. 반감기 = ln(0.5)/ln(phi).
    """
    prem = [r["premium"] for r in rows]
    if len(prem) < 60:
        return None
    m = mean(prem)
    x = [p - m for p in prem[:-1]]
    y = [p - m for p in prem[1:]]
    denom = sum(v * v for v in x)
    if denom == 0:
        return None
    phi = sum(a * b for a, b in zip(x, y)) / denom
    hl = None
    if 0 < phi < 1:
        hl = math.log(0.5) / math.log(phi)
    return {"phi": phi, "half_life_days": hl, "n": len(x)}


def extreme_diagnostics(rows, window=250, z_thr=2.0):
    """극단 판정 시점의 데이터 품질 진단.

    - ff_share: 극단 시점이 이월(휴장 대체) 포인트인 비율. 높으면 '해소'가
      시장 행동이 아니라 이월 해제에 따른 기계적 되돌림일 수 있다.
    - one_day_share: 극단 다음날 |P|가 극단 직전 수준(전일)으로 돌아간 비율
      (1일 스파이크 = 비동시성 종가 아티팩트 의심 지표).
    """
    prem = [r["premium"] for r in rows]
    n_ext = ff_ext = one_day = 0
    for t in range(window, len(prem) - 1):
        hist = prem[t - window:t]
        m, sd = mean(hist), stdev(hist)
        if sd == 0 or abs((prem[t] - m) / sd) < z_thr:
            continue
        n_ext += 1
        r = rows[t]
        if r.get("ff_dr") or r.get("ff_local"):
            ff_ext += 1
        # 전일 대비 스파이크였고 다음날 전일 수준 부근(스파이크 폭의 50% 이내)으로 복귀
        spike = prem[t] - prem[t - 1]
        back = prem[t + 1] - prem[t - 1]
        if abs(spike) > 0 and abs(back) < abs(spike) * 0.5:
            one_day += 1
    if n_ext == 0:
        return None
    return {"n_extreme": n_ext, "ff_share": ff_ext / n_ext,
            "one_day_spike_share": one_day / n_ext}


def reversion_test(rows, method="z", horizons=(1, 5, 20), window=250, z_thr=2.0):
    """극단 프리미엄 이후 평균회귀 검증.

    각 시점 t에서 과거 window개(현재 제외)로 기준을 만들고, t가 극단이면
    t+N의 프리미엄 변화(P[t+N] - P[t])를 수집한다. 부호를 정규화해
    "0 방향 이동량(해소량)"으로 바꾼다: 양의 극단이면 -(변화), 음의 극단이면 +(변화).
    양수 평균 = 0으로 수렴(가설 지지), 음수 = 오히려 확대.
    """
    prem = [r["premium"] for r in rows]
    out = {"method": method, "horizons": {}}
    picks = {"high": [], "low": []}
    for t in range(window, len(prem) - max(horizons)):
        hist = prem[t - window:t]
        cur = prem[t]
        if method == "z":
            m, sd = mean(hist), stdev(hist)
            if sd == 0:
                continue
            z = (cur - m) / sd
            hi, lo = z >= z_thr, z <= -z_thr
            score = z
        else:
            q90, q10 = quantile(hist, 0.9), quantile(hist, 0.1)
            hi, lo = cur >= q90, cur <= q10
            score = cur
        if not (hi or lo):
            continue
        picks["high" if hi else "low"].append((t, score))
    for h in horizons:
        resolves, closed_frac = [], []
        for side, items in picks.items():
            sign = 1 if side == "high" else -1
            for t, _ in items:
                if t + h >= len(prem):
                    continue
                d = prem[t + h] - prem[t]
                resolves.append(-sign * d)  # 0 방향 이동량
                # 스케일 무관 지표: 괴리의 몇 %가 닫혔나 (|P_t| 대비)
                if abs(prem[t]) > 1e-9:
                    closed_frac.append((abs(prem[t]) - abs(prem[t + h])) / abs(prem[t]))
        if len(resolves) >= 10:
            out["horizons"][h] = {
                "n": len(resolves),
                "mean_resolution_pp": mean(resolves),
                "median_resolution_pp": median(resolves),
                "share_positive": sum(1 for x in resolves if x > 0) / len(resolves),
                "p_value": one_sample_p(resolves, 0.0),
                "median_gap_closed_pct": (median(closed_frac) * 100
                                          if closed_frac else None),
            }
        else:
            out["horizons"][h] = {"n": len(resolves)}
    out["n_high"] = len(picks["high"])
    out["n_low"] = len(picks["low"])
    return out


def moving_average(xs, n):
    out, s = [], 0.0
    for i, v in enumerate(xs):
        s += v
        if i >= n:
            s -= xs[i - n]
        out.append(s / min(i + 1, n))
    return out


def variance_decomposition(rows, n=20):
    """프리미엄을 지속 성분(MA20)과 일별 잔차로 분해.

    비동시성 종가(현지 종가 D + DR 종가 D, 8~13시간 후) 때문에 일별 프리미엄에는
    'DR의 야간 변동' 성분이 섞인다. 이 성분은 다음날 현지 시장이 열리면 흡수돼
    기계적으로 되돌아간다 - 시장의 '해소 심리'와 구분해야 한다.
    """
    prem = [r["premium"] for r in rows]
    if len(prem) < n * 3:
        return None
    ma = moving_average(prem, n)
    resid = [p - m for p, m in zip(prem, ma)]
    sd_ma, sd_resid = stdev(ma[n:]), stdev(resid[n:])
    tot = sd_ma ** 2 + sd_resid ** 2
    return {"sd_persistent": sd_ma, "sd_transient": sd_resid,
            "persistent_share": (sd_ma ** 2 / tot) if tot > 0 else None,
            "n": len(prem) - n}


def smoothed_reversion(rows, n=5, horizons=(5, 20), window=250, z_thr=2.0):
    """일별 노이즈를 5일 평균으로 걷어낸 뒤의 평균회귀 검증.

    여기서도 해소가 관측되면 '구조적 괴리의 회귀'라 말할 근거가 되고,
    사라지면 앞선 결과는 비동시성 노이즈의 기계적 되돌림이었다는 뜻이다.
    """
    prem_raw = [r["premium"] for r in rows]
    if len(prem_raw) < window + max(horizons) + n:
        return None
    prem = moving_average(prem_raw, n)
    out = {"n_smooth": n, "horizons": {}}
    picks = []
    for t in range(window, len(prem) - max(horizons)):
        hist = prem[t - window:t]
        m, sd = mean(hist), stdev(hist)
        if sd == 0:
            continue
        z = (prem[t] - m) / sd
        if abs(z) >= z_thr:
            picks.append((t, 1 if z > 0 else -1))
    for h in horizons:
        resolves, closed = [], []
        for t, sign in picks:
            if t + h >= len(prem):
                continue
            resolves.append(-sign * (prem[t + h] - prem[t]))
            if abs(prem[t]) > 1e-9:
                closed.append((abs(prem[t]) - abs(prem[t + h])) / abs(prem[t]))
        if len(resolves) >= 10:
            out["horizons"][h] = {
                "n": len(resolves),
                "mean_resolution_pp": mean(resolves),
                "median_gap_closed_pct": median(closed) * 100 if closed else None,
                "share_positive": sum(1 for x in resolves if x > 0) / len(resolves),
                "p_value": one_sample_p(resolves, 0.0),
            }
        else:
            out["horizons"][h] = {"n": len(resolves)}
    return out


def baseline_drift(rows, horizons=(1, 5, 20)):
    """대조군: 전 구간 무조건부 |프리미엄| 감소량 (극단 조건 없이).

    극단 조건부 해소량이 이 값보다 확실히 커야 '극단에서의 해소'라 말할 수 있다.
    """
    prem = [r["premium"] for r in rows]
    out = {}
    for h in horizons:
        vals = []
        for t in range(len(prem) - h):
            vals.append(abs(prem[t]) - abs(prem[t + h]))  # 양수 = 괴리 축소
        if vals:
            out[h] = {"n": len(vals), "mean_abs_shrink_pp": mean(vals),
                      "median": median(vals), "p_value": one_sample_p(vals, 0.0)}
    return out


def fmt(v, nd=4):
    return "N/A" if v is None else f"{v:.{nd}f}"


def main():
    ids = load_ids()
    results = {}
    for tid in ids:
        try:
            r = analyze_ticker(tid)
            r["baseline"] = baseline_drift(load_rows(tid))
            results[tid] = r
        except Exception as e:
            print(f"[SKIP] {tid}: {type(e).__name__}: {e}", file=sys.stderr)

    if "--json" in sys.argv[1:]:
        print(json.dumps(results, ensure_ascii=False, indent=1))
        return 0

    print("=" * 78)
    print("프리미엄-거래량 상관 및 평균회귀 분석")
    print("=" * 78)

    print("\n[1] 데이터 개요")
    print(f"{'종목':6s} {'그룹':16s} {'행수':>6s} {'시작':>11s} {'|P| 중앙값':>10s} {'P 표준편차':>10s}")
    for tid, r in results.items():
        print(f"{tid:6s} {r['group']:16s} {r['n_rows']:6d} {r['first']:>11s} "
              f"{r['premium_abs_median']:10.2f} {r['premium_sd']:10.2f}")

    print("\n[2] |프리미엄| vs 정규화 로그 거래량 (동시점 상관)")
    print(f"{'종목':6s} {'시리즈':6s} {'n':>6s} {'pearson':>9s} {'p':>9s} {'spearman':>9s} {'p':>9s}")
    for tid, r in results.items():
        for s in ("local", "dr"):
            d = r[f"absP_vol_{s}"]
            print(f"{tid:6s} {s:6s} {d['n']:6d} {fmt(d['pearson'],3):>9s} "
                  f"{fmt(d['p_pearson'],4):>9s} {fmt(d['spearman'],3):>9s} "
                  f"{fmt(d['p_spearman'],4):>9s}")

    print("\n[3] |프리미엄 변화| vs 거래량 (동시점 상관)")
    print(f"{'종목':6s} {'시리즈':6s} {'n':>6s} {'pearson':>9s} {'p':>9s} {'spearman':>9s}")
    for tid, r in results.items():
        for s in ("local", "dr"):
            d = r[f"absDelta_vol_{s}"]
            print(f"{tid:6s} {s:6s} {d['n']:6d} {fmt(d['pearson'],3):>9s} "
                  f"{fmt(d['p_pearson'],4):>9s} {fmt(d['spearman'],3):>9s}")

    print("\n[4] 시차: t일 거래량 -> t+1일 프리미엄 '해소 방향' 이동 상관")
    print("    (양수 = 거래량 많은 날 다음날 괴리가 줄어드는 경향)")
    print(f"{'종목':6s} {'시리즈':6s} {'n':>6s} {'r_해소':>9s} {'p':>9s} {'r_원변화':>9s}")
    for tid, r in results.items():
        for s in ("local", "dr"):
            d = r[f"lagVol_resolution_{s}"]
            d2 = r[f"lagVol_nextDelta_{s}"]
            print(f"{tid:6s} {s:6s} {d['n']:6d} {fmt(d['pearson'],4):>9s} "
                  f"{fmt(d['p'],4):>9s} {fmt(d2['pearson'],4):>9s}")

    print("\n[5] 평균회귀 (z>=+/-2 극단 이후 0 방향 이동량, %p)")
    print(f"{'종목':6s} {'H':>3s} {'n':>6s} {'평균':>8s} {'중앙값':>8s} {'양수비율':>8s} {'p':>9s}")
    for tid, r in results.items():
        rv = r["reversion"]
        for h, d in rv["horizons"].items():
            if d.get("n", 0) < 10:
                print(f"{tid:6s} {h:3d} {d.get('n',0):6d}  (표본 부족)")
                continue
            print(f"{tid:6s} {h:3d} {d['n']:6d} {d['mean_resolution_pp']:8.3f} "
                  f"{d['median_resolution_pp']:8.3f} {d['share_positive']*100:7.1f}% "
                  f"{fmt(d['p_value'],4):>9s}")

    print("\n[6] 평균회귀 (상하위 10% 분위 기준)")
    print(f"{'종목':6s} {'H':>3s} {'n':>6s} {'평균':>8s} {'중앙값':>8s} {'양수비율':>8s} {'p':>9s}")
    for tid, r in results.items():
        for h, d in r["reversion_q"]["horizons"].items():
            if d.get("n", 0) < 10:
                continue
            print(f"{tid:6s} {h:3d} {d['n']:6d} {d['mean_resolution_pp']:8.3f} "
                  f"{d['median_resolution_pp']:8.3f} {d['share_positive']*100:7.1f}% "
                  f"{fmt(d['p_value'],4):>9s}")

    print("\n[7] 대조군: 무조건부 |프리미엄| 축소량 (극단 조건 없음, %p)")
    print(f"{'종목':6s} {'H':>3s} {'n':>6s} {'평균':>8s} {'중앙값':>8s} {'p':>9s}")
    for tid, r in results.items():
        for h, d in r["baseline"].items():
            print(f"{tid:6s} {h:3d} {d['n']:6d} {d['mean_abs_shrink_pp']:8.4f} "
                  f"{d['median']:8.4f} {fmt(d['p_value'],4):>9s}")

    print("\n[8] 스케일 무관 비교: 극단 시 괴리가 몇 % 닫혔나 (중앙값)")
    print(f"{'종목':6s} {'그룹':16s} {'H=1':>8s} {'H=5':>8s} {'H=20':>8s} {'n':>6s}")
    for tid, r in results.items():
        hz = r["reversion"]["horizons"]
        if hz.get(1, {}).get("n", 0) < 10:
            continue
        vals = [hz.get(h, {}).get("median_gap_closed_pct") for h in (1, 5, 20)]
        print(f"{tid:6s} {r['group']:16s} " +
              " ".join(f"{(v if v is not None else float('nan')):7.1f}%" for v in vals) +
              f" {hz[1]['n']:6d}")

    print("\n[9] 회귀 속도(AR1)와 극단 시점 데이터 품질 진단")
    print(f"{'종목':6s} {'AR1 phi':>8s} {'반감기(일)':>10s} {'극단수':>6s} "
          f"{'이월비율':>8s} {'1일스파이크':>10s}")
    for tid, r in results.items():
        a = r.get("ar1") or {}
        d = r.get("diag") or {}
        hl = a.get("half_life_days")
        hl_s = f"{hl:10.1f}" if hl else "N/A".rjust(10)
        ff_s = f"{d['ff_share'] * 100:7.1f}%" if d else "N/A".rjust(8)
        sp_s = f"{d['one_day_spike_share'] * 100:9.1f}%" if d else "N/A".rjust(10)
        print(f"{tid:6s} {fmt(a.get('phi'), 4):>8s} {hl_s} "
              f"{d.get('n_extreme', 0):6d} {ff_s} {sp_s}")

    print("\n[10] 프리미엄 분산 분해: 지속 성분(MA20) vs 일별 잔차")
    print(f"{'종목':6s} {'그룹':16s} {'SD지속':>8s} {'SD일별':>8s} {'지속비중':>8s}")
    for tid, r in results.items():
        d = r.get("decomp")
        if not d:
            continue
        print(f"{tid:6s} {r['group']:16s} {d['sd_persistent']:8.3f} "
              f"{d['sd_transient']:8.3f} {d['persistent_share'] * 100:7.1f}%")

    print("\n[11] 평활(5일 평균) 후 극단 평균회귀 - 노이즈 제거 시에도 남는가")
    print(f"{'종목':6s} {'H':>3s} {'n':>6s} {'평균해소':>9s} {'닫힌비율':>9s} {'양수':>7s} {'p':>9s}")
    for tid, r in results.items():
        sr = r.get("smooth_rev")
        if not sr:
            continue
        for h, d in sr["horizons"].items():
            if d.get("n", 0) < 10:
                continue
            gc = d.get("median_gap_closed_pct")
            print(f"{tid:6s} {h:3d} {d['n']:6d} {d['mean_resolution_pp']:9.3f} "
                  f"{(f'{gc:8.1f}%' if gc is not None else 'N/A'.rjust(9))} "
                  f"{d['share_positive'] * 100:6.1f}% {fmt(d['p_value'], 4):>9s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
