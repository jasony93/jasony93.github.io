"""ADR/GDR 프리미엄 데이터 수집·계산 파이프라인.

yfinance에서 DR 가격·원주 가격·환율의 일별 종가 히스토리를 받아
PRD 3.3절 수식과 3.3.1절 규칙 B(일별 히스토리)에 따라 프리미엄을 계산하고,
웹 UI가 읽는 정적 JSON(src/web/data/)을 생성한다.

실행:
  python src/fetch_data.py              전체 실행 (히스토리 + 스냅샷 + F7/F8 통계)
  python src/fetch_data.py --intraday   장중 스냅샷만 갱신 (F2 - history 파일 불변)

- 종목별 조회 실패 시 해당 종목의 기존 데이터(직전 정상값)를 유지하고
  fetch_error 플래그만 갱신한다 (전체 파이프라인은 죽지 않는다).

v2 확장 (2026-08-04, F1~F8 PRD):
- F4: 스냅샷에 직전 포인트 대비 변동(delta_pp)·기준일 추가
- F6: 히스토리 포인트에 vol_dr/vol_local (이월 포인트는 null)
- F7: DR 발행 잔량 자동 조회 + 검증 A/B + 수동 폴백, 전환율·시장별 금액 계산
- F8: 원주 총발행주식수(N_total)·시가총액 (info 우선, fast_info 교차 검증)
- F2: --intraday 모드(스냅샷 전용 경량 수집), 장중 여부 플래그·수집 시각(KST),
      전체 실행 시 개장 중 시장의 진행 중 당일 행을 히스토리에서 제외 (확정 종가만)
"""
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

KST = timezone(timedelta(hours=9))

# 시장 세션 (KST 기준 분 단위, 자정 넘어가면 1440+). 서머타임 고정 오프셋(하계) +
# 마감 10분 여유의 보수적 창 - 경계 오차는 "지연 시세" 라벨 방향으로만 작용한다.
SESSIONS_KST = {
    "KRX": (9 * 60, 15 * 60 + 40),
    "TWSE": (10 * 60, 14 * 60 + 40),
    # HKEX 09:30-16:00 HKT(점심 휴장 12:00-13:00 포함) = KST 10:30-17:00 + 여유.
    # 점심 휴장도 '개장 창'으로 취급 - 당일 값이 미확정이라는 판정 목적상 올바름.
    "HKEX": (10 * 60 + 30, 17 * 60 + 10),
    "LSE IOB": (16 * 60, 24 * 60 + 100),   # 16:00 ~ 익일 01:40
    "Nasdaq": (22 * 60 + 30, 24 * 60 + 370),  # 22:30 ~ 익일 06:10
    "NYSE": (22 * 60 + 30, 24 * 60 + 370),
}

# 시장 현지 날짜 계산용 UTC 오프셋(시간, 하계 고정 - 설계 문서 제약 참조.
# 홍콩은 서머타임 없음 - 연중 +8 고정)
MARKET_UTC_OFFSET = {"KRX": 9, "TWSE": 8, "HKEX": 8, "LSE IOB": 1,
                     "Nasdaq": -4, "NYSE": -4}


def is_market_open(exchange: str, now_utc: datetime | None = None) -> bool:
    """보수적 세션 창 기준 개장 여부 (KST 벽시계)."""
    if exchange not in SESSIONS_KST:
        return False
    now = (now_utc or datetime.now(timezone.utc)).astimezone(KST)
    if now.weekday() >= 5:  # 주말(KST) - 미국 금요일 밤장은 KST 토요일 새벽이므로 예외
        # 토요일 새벽의 미국장(금요일 세션 연장분)만 허용
        if not (now.weekday() == 5 and exchange in ("Nasdaq", "NYSE") and now.hour < 7):
            return False
    m = now.hour * 60 + now.minute
    start, end = SESSIONS_KST[exchange]
    if end > 1440:
        return m >= start or m < (end - 1440)
    return start <= m < end


def market_local_today(exchange: str, now_utc: datetime | None = None) -> str:
    now = now_utc or datetime.now(timezone.utc)
    off = MARKET_UTC_OFFSET.get(exchange, 0)
    return (now + timedelta(hours=off)).strftime("%Y-%m-%d")


def drop_in_progress(series: pd.Series | None, exchange: str,
                     now_utc: datetime | None = None) -> pd.Series | None:
    """개장 중 시장의 '진행 중 당일 행'을 제거 (F2 차트 분리 원칙 - 확정 종가만).

    마지막 행 날짜가 해당 시장의 현지 오늘이고 지금 개장 중이면 그 행을 버린다.
    """
    if series is None or series.empty:
        return series
    if is_market_open(exchange, now_utc):
        today = market_local_today(exchange, now_utc)
        if series.index[-1].strftime("%Y-%m-%d") == today:
            return series.iloc[:-1]
    return series

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config" / "tickers.json"
DATA_DIR = ROOT / "web" / "data"
HISTORY_DIR = DATA_DIR / "history"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    # 설정 무결성 검증: 환율 교차 오적용 방지 (PRD 5절 완료 기준)
    for t in cfg["tickers"]:
        if t["local_currency"] == "KRW":
            assert t["fx_yahoo"] == "KRW=X", f"{t['id']}: KRW 종목에 잘못된 환율 {t['fx_yahoo']}"
            assert t["local_yahoo"].endswith(".KS"), f"{t['id']}: KRW 종목의 원주 티커 오류"
        elif t["local_currency"] == "TWD":
            assert t["fx_yahoo"] == "TWD=X", f"{t['id']}: TWD 종목에 잘못된 환율 {t['fx_yahoo']}"
            assert t["local_yahoo"].endswith(".TW"), f"{t['id']}: TWD 종목의 원주 티커 오류"
        elif t["local_currency"] == "HKD":
            assert t["fx_yahoo"] == "HKD=X", f"{t['id']}: HKD 종목에 잘못된 환율 {t['fx_yahoo']}"
            assert t["local_yahoo"].endswith(".HK"), f"{t['id']}: HKD 종목의 원주 티커 오류"
        else:
            raise AssertionError(f"{t['id']}: 알 수 없는 통화 {t['local_currency']}")
        assert t["ratio"] > 0, f"{t['id']}: 전환비율은 양수여야 함"
    return cfg


def _clean_index(s: pd.Series) -> pd.Series:
    s.index = pd.DatetimeIndex(s.index.tz_localize(None)).normalize()
    return s[~s.index.duplicated(keep="last")].sort_index()


def fetch_close_volume(symbol: str, period: str = "max") -> tuple[pd.Series, pd.Series | None]:
    """일별 원시 종가 + 거래량(F6). 인덱스는 시장 현지 날짜(tz 제거)."""
    import yfinance as yf

    df = yf.Ticker(symbol).history(period=period, auto_adjust=False)
    if df.empty:
        raise RuntimeError(f"빈 히스토리: {symbol}")
    close = _clean_index(df["Close"].dropna())
    vol = None
    if "Volume" in df.columns:
        vol = _clean_index(df["Volume"].dropna())
    return close, vol


def fetch_close_series(symbol: str) -> pd.Series:
    """일별 원시 종가(Close, 수정주가 아님) 시리즈. 인덱스는 시장 현지 날짜(tz 제거)."""
    return fetch_close_volume(symbol)[0]


def compute_premium(p_dr: float, fx: float, p_local: float, ratio: float) -> float:
    """PRD 3.3절: Premium(%) = (P_dr * FX / (P_local * r) - 1) * 100"""
    return (p_dr * fx / (p_local * ratio) - 1.0) * 100.0


def _take(series: pd.Series, d: pd.Timestamp):
    """날짜 d의 값. 없으면 직전 값 이월(forward-fill)하고 플래그 True.

    반환: (값 또는 None, 이월 여부)
    """
    if d in series.index:
        return float(series.loc[d]), False
    prev = series.loc[:d]
    if prev.empty:
        return None, True
    return float(prev.iloc[-1]), True


def _vol_at(vol: pd.Series | None, d: pd.Timestamp, is_ff: bool) -> int | None:
    """F6: 해당 날짜 실거래 거래량. 이월 포인트(휴장)는 거래가 없으므로 null."""
    if vol is None or is_ff or d not in vol.index:
        return None
    v = vol.loc[d]
    return None if pd.isna(v) else int(v)


def build_history(dr: pd.Series, local: pd.Series, fx: pd.Series,
                  ratio: float, history_start: str | None = None,
                  vol_dr: pd.Series | None = None,
                  vol_local: pd.Series | None = None) -> list[dict]:
    """규칙 B 일별 히스토리.

    - 날짜 그리드: DR·원주 중 한쪽이라도 거래된 캘린더 날짜의 합집합
      (양쪽 모두 휴장이면 그리드에 없음 -> 포인트 생략, PRD 3.3.1).
    - 휴장 쪽 값은 직전 거래일 종가 이월 + ff_* 플래그.
    - 시작일: 세 시리즈가 모두 존재하는 시점과 history_start(전환비율 유효 시작일) 중 늦은 날.
    """
    first = max(dr.index[0], local.index[0], fx.index[0])
    if history_start:
        first = max(first, pd.Timestamp(history_start))
    dates = sorted(set(dr.index) | set(local.index))
    rows: list[dict] = []
    for d in dates:
        if d < first:
            continue
        p_dr, ff_dr = _take(dr, d)
        p_local, ff_local = _take(local, d)
        p_fx, ff_fx = _take(fx, d)
        if p_dr is None or p_local is None or p_fx is None:
            continue
        rows.append({
            "date": d.strftime("%Y-%m-%d"),
            "premium": round(compute_premium(p_dr, p_fx, p_local, ratio), 4),
            "p_dr": round(p_dr, 4),
            "p_local": round(p_local, 4),
            "fx": round(p_fx, 4),
            "ff_dr": ff_dr,
            "ff_local": ff_local,
            "ff_fx": ff_fx,
            "vol_dr": _vol_at(vol_dr, d, ff_dr),
            "vol_local": _vol_at(vol_local, d, ff_local),
        })
    return rows


def build_snapshot(dr: pd.Series, local: pd.Series, fx: pd.Series, ratio: float) -> dict:
    """규칙 A(현재값)의 종가 기반 근사: 각 시리즈의 가장 최근 종가 + 각각의 기준 날짜.

    MVP는 지연/종가 기반이므로 기준 시점 라벨을 정확히 붙이는 것으로 갈음 (PRD 3.3.1 규칙 A 단서).
    """
    p_dr, d_dr = float(dr.iloc[-1]), dr.index[-1]
    p_local, d_local = float(local.iloc[-1]), local.index[-1]
    p_fx, d_fx = float(fx.iloc[-1]), fx.index[-1]
    return {
        "premium": round(compute_premium(p_dr, p_fx, p_local, ratio), 4),
        "p_dr": round(p_dr, 4),
        "p_dr_date": d_dr.strftime("%Y-%m-%d"),
        "p_local": round(p_local, 4),
        "p_local_date": d_local.strftime("%Y-%m-%d"),
        "fx": round(p_fx, 4),
        "fx_date": d_fx.strftime("%Y-%m-%d"),
        "implied_local": round(p_dr * p_fx / ratio, 2),
    }


def apply_prev_delta(snapshot: dict, rows: list[dict]) -> None:
    """F4: 규칙 B 시계열의 직전 데이터 포인트 대비 변동(%p)을 스냅샷에 기록.

    기준: 스냅샷 날짜(max(p_dr_date, p_local_date))보다 앞선 마지막 확정 포인트.
    직전 포인트가 없으면(상장 첫 데이터) 필드를 null로 둔다.
    """
    snap_date = max(snapshot["p_dr_date"], snapshot["p_local_date"])
    prev = None
    for r in reversed(rows):
        if r["date"] < snap_date:
            prev = r
            break
    if prev is None:
        snapshot["prev_premium"] = None
        snapshot["prev_date"] = None
        snapshot["delta_pp"] = None
    else:
        snapshot["prev_premium"] = prev["premium"]
        snapshot["prev_date"] = prev["date"]
        snapshot["delta_pp"] = round(snapshot["premium"] - prev["premium"], 4)


def apply_intraday_flags(snapshot: dict, tcfg: dict,
                         now_utc: datetime | None = None) -> None:
    """F2: 각 원천값이 '장중(진행 중) 값'인지 플래그. 수집 시각(KST)도 기록."""
    now = now_utc or datetime.now(timezone.utc)
    dr_ex = tcfg.get("dr_exchange", "")
    loc_ex = tcfg.get("local_exchange", "")
    snapshot["p_dr_intraday"] = bool(
        is_market_open(dr_ex, now)
        and snapshot["p_dr_date"] == market_local_today(dr_ex, now))
    snapshot["p_local_intraday"] = bool(
        is_market_open(loc_ex, now)
        and snapshot["p_local_date"] == market_local_today(loc_ex, now))
    # 환율은 24시간 거래 - 환율 날짜가 오늘(UTC 또는 KST)이면 진행 중 값으로 본다.
    today_utc = now.strftime("%Y-%m-%d")
    today_kst = now.astimezone(KST).strftime("%Y-%m-%d")
    snapshot["fx_intraday"] = snapshot["fx_date"] in (today_utc, today_kst)


def now_kst_label(now_utc: datetime | None = None) -> str:
    now = (now_utc or datetime.now(timezone.utc)).astimezone(KST)
    return now.strftime("%m/%d %H:%M")


# ---------- F7/F8: 발행주식수·전환 현황 ----------

def fetch_share_stats(dr_yahoo: str, local_yahoo: str) -> dict:
    """DR 발행 잔량 후보 3종 + 원주 총발행주식수(N_total) + 야후 시총(교차 검증).

    N_total은 info.sharesOutstanding 우선 - 실조회 결과(PRD 9절) 삼성전자의
    fast_info shares(6.57B)는 우선주 포함치이고 info(5.76B)가 보통주로 확인됨.
    """
    import yfinance as yf

    out: dict = {"dr_candidates": {}, "n_total": None, "n_total_field": None,
                 "mcap_yahoo": None, "errors": []}
    dr = yf.Ticker(dr_yahoo)
    try:
        info = dr.info or {}
        out["dr_candidates"]["sharesOutstanding"] = info.get("sharesOutstanding")
        out["dr_candidates"]["impliedSharesOutstanding"] = info.get("impliedSharesOutstanding")
    except Exception as e:
        out["errors"].append(f"dr.info: {type(e).__name__}")
    try:
        out["dr_candidates"]["fast_shares"] = dr.fast_info.get("shares")
    except Exception as e:
        out["errors"].append(f"dr.fast_info: {type(e).__name__}")
    loc = yf.Ticker(local_yahoo)
    try:
        info_l = loc.info or {}
        if info_l.get("sharesOutstanding"):
            out["n_total"] = int(info_l["sharesOutstanding"])
            out["n_total_field"] = "info.sharesOutstanding"
    except Exception as e:
        out["errors"].append(f"local.info: {type(e).__name__}")
    try:
        fi = loc.fast_info
        if out["n_total"] is None and fi.get("shares"):
            out["n_total"] = int(fi.get("shares"))
            out["n_total_field"] = "fast_info.shares"
        out["mcap_yahoo"] = fi.get("market_cap")
    except Exception as e:
        out["errors"].append(f"local.fast_info: {type(e).__name__}")
    return out


def compute_conversion(tcfg: dict, f7cfg: dict, n_total: int | None,
                       dr_candidates: dict, p_dr: float, p_local: float,
                       today: str) -> dict:
    """F7 (PRD 7.2/7.3): 자동 후보 검증 A/B -> 수동 폴백 -> 미확인.

    검증 A: cand * r / N_total >= auto_reject_threshold 이면 전사 환산치로 기각.
    검증 B: 한도 확인 종목은 cand * r <= L * limit_margin 이어야 함.
    """
    r = tcfg["ratio"]
    threshold = f7cfg.get("auto_reject_threshold", 0.9)
    margin = f7cfg.get("limit_margin", 1.05)
    limit = tcfg.get("conversion_limit_local")
    conv: dict = {
        "limit": limit,
        "limit_as_of": tcfg.get("limit_as_of"),
        "limit_src": tcfg.get("limit_src"),
        "n_dr": None, "n_dr_source": None, "n_dr_as_of": None, "n_dr_src": None,
        "note": tcfg.get("conversion_note"),
        "type": tcfg.get("conversion_type"),
        "rejected_auto": [],
    }
    # (1) 자동 후보 (우선순위 순)
    if n_total:
        for field in ("sharesOutstanding", "impliedSharesOutstanding", "fast_shares"):
            cand = dr_candidates.get(field)
            if not cand:
                continue
            frac = cand * r / n_total
            if frac >= threshold:
                conv["rejected_auto"].append(
                    {"field": field, "value": int(cand),
                     "reason": f"검증 A 기각: 원주환산/총주식 {frac * 100:.1f}% >= {threshold * 100:.0f}% (전사 환산치 의심)"})
                continue
            if limit and cand * r > limit * margin:
                conv["rejected_auto"].append(
                    {"field": field, "value": int(cand),
                     "reason": f"검증 B 기각: 원주환산 {cand * r:,.0f}주 > 한도 {limit:,}주 * {margin}"})
                continue
            conv.update({"n_dr": int(cand), "n_dr_source": "auto",
                         "n_dr_as_of": today,
                         "n_dr_src": f"자동 조회(Yahoo {field})"})
            break
    # (2) 수동 폴백
    if conv["n_dr"] is None and tcfg.get("dr_outstanding_manual"):
        conv.update({"n_dr": int(tcfg["dr_outstanding_manual"]),
                     "n_dr_source": "manual",
                     "n_dr_as_of": tcfg.get("dr_outstanding_as_of"),
                     "n_dr_src": tcfg.get("dr_outstanding_src")})
    # (3) 계산
    if conv["n_dr"] is not None and n_total:
        n_dr_local = conv["n_dr"] * r
        conv["n_dr_local"] = round(n_dr_local)
        conv["cv"] = round(n_dr_local / n_total * 100, 4)
        conv["lu"] = round(n_dr_local / limit * 100, 4) if limit else None
        conv["limit_pct"] = round(limit / n_total * 100, 4) if limit else None
        conv["v_dr_usd"] = round(conv["n_dr"] * p_dr, 2)
        conv["v_local"] = round((n_total - n_dr_local) * p_local, 2)
    return conv


def build_spark(rows: list[dict], days: int = 30) -> list[list]:
    """최근 30일(캘린더 기준) [날짜, 프리미엄] 목록 - 메인 카드 스파크라인용."""
    if not rows:
        return []
    last = pd.Timestamp(rows[-1]["date"])
    cutoff = last - pd.Timedelta(days=days)
    return [[r["date"], r["premium"]] for r in rows if pd.Timestamp(r["date"]) >= cutoff]


def process_ticker(tcfg: dict, fx_cache: dict, f7cfg: dict | None = None) -> tuple[dict, list[dict]]:
    """한 종목의 메타 엔트리와 히스토리 행 목록을 생성 (전체 실행)."""
    now_utc = datetime.now(timezone.utc)
    dr, vol_dr = fetch_close_volume(tcfg["dr_yahoo"])
    local, vol_local = fetch_close_volume(tcfg["local_yahoo"])
    fx_sym = tcfg["fx_yahoo"]
    if fx_sym not in fx_cache:
        fx_cache[fx_sym] = fetch_close_series(fx_sym)
    fx = fx_cache[fx_sym]

    # F2 차트 분리: 히스토리는 확정 종가만 - 개장 중 시장의 진행 중 당일 행 제외
    dr_hist = drop_in_progress(dr, tcfg.get("dr_exchange", ""), now_utc)
    local_hist = drop_in_progress(local, tcfg.get("local_exchange", ""), now_utc)
    rows = build_history(dr_hist, local_hist, fx, tcfg["ratio"],
                         tcfg.get("history_start"),
                         vol_dr=vol_dr, vol_local=vol_local)
    if not rows:
        raise RuntimeError("계산 가능한 히스토리 행이 없음")

    # 스냅샷(규칙 A 근사)은 최신값 그대로 - 장중이면 F2 플래그로 표기
    snapshot = build_snapshot(dr, local, fx, tcfg["ratio"])
    apply_prev_delta(snapshot, rows)
    apply_intraday_flags(snapshot, tcfg, now_utc)

    # F7/F8: 발행주식수·시가총액·전환 현황 (일일 확정 실행에서만 계산)
    stats = fetch_share_stats(tcfg["dr_yahoo"], tcfg["local_yahoo"])
    shares = None
    conversion = None
    if stats["n_total"]:
        mcap_calc = round(stats["n_total"] * snapshot["p_local"], 2)
        mcap_warn = False
        if stats["mcap_yahoo"]:
            diff = abs(mcap_calc - stats["mcap_yahoo"]) / stats["mcap_yahoo"]
            mcap_warn = diff > 0.05
            if mcap_warn:
                print(f"[WARN] {tcfg['id']}: 시총 교차 검증 {diff * 100:.1f}% 차이 "
                      f"(계산 {mcap_calc:,.0f} vs Yahoo {stats['mcap_yahoo']:,.0f})",
                      file=sys.stderr)
        shares = {
            "n_total": stats["n_total"],
            "n_total_field": stats["n_total_field"],
            "n_total_as_of": snapshot["p_local_date"],
            "mcap_local": mcap_calc,
            "mcap_yahoo": stats["mcap_yahoo"],
            "mcap_warn": mcap_warn,
        }
        conversion = compute_conversion(
            tcfg, f7cfg or {}, stats["n_total"], stats["dr_candidates"],
            snapshot["p_dr"], snapshot["p_local"],
            now_utc.astimezone(KST).strftime("%Y-%m-%d"))
    else:
        # N_total 미확보 - 한도 정보(수동)만이라도 유지
        conversion = compute_conversion(
            tcfg, f7cfg or {}, None, stats["dr_candidates"],
            snapshot["p_dr"], snapshot["p_local"],
            now_utc.astimezone(KST).strftime("%Y-%m-%d"))

    entry = {
        **{k: tcfg[k] for k in (
            "id", "name", "dr_ticker", "dr_exchange", "dr_type",
            "local_code", "local_exchange", "local_currency",
            "fx_label", "ratio", "ratio_display")},
        "snapshot": snapshot,
        "shares": shares,
        "conversion": conversion,
        "spark": build_spark(rows),
        "first_date": rows[0]["date"],
        "last_date": rows[-1]["date"],
        "row_count": len(rows),
        "collected_at_kst": now_kst_label(now_utc),
        "fetch_error": None,
        "fetched_at": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return entry, rows


def process_ticker_intraday(tcfg: dict, fx_cache: dict, old_entry: dict) -> dict:
    """F2 장중 모드: 최근 5일 종가만 수집해 스냅샷을 갱신. 히스토리 파일 불변.

    F7/F8 값(shares/conversion)·스파크라인 등 일일 확정 필드는 기존 엔트리 유지
    (시총·전환 금액은 종가 기준 - PRD F8 갱신 주기 방침).
    """
    now_utc = datetime.now(timezone.utc)
    dr, _ = fetch_close_volume(tcfg["dr_yahoo"], period="5d")
    local, _ = fetch_close_volume(tcfg["local_yahoo"], period="5d")
    fx_sym = tcfg["fx_yahoo"]
    if fx_sym not in fx_cache:
        fx_cache[fx_sym] = fetch_close_volume(fx_sym, period="5d")[0]
    fx = fx_cache[fx_sym]

    snapshot = build_snapshot(dr, local, fx, tcfg["ratio"])
    # 직전 확정 포인트: 기존 히스토리 파일 기준 (당일 포인트는 존재하지 않음)
    rows = []
    hist_path = HISTORY_DIR / f"{tcfg['id']}.json"
    if hist_path.exists():
        with open(hist_path, encoding="utf-8") as f:
            rows = json.load(f).get("rows", [])
    apply_prev_delta(snapshot, rows)
    apply_intraday_flags(snapshot, tcfg, now_utc)

    entry = dict(old_entry)
    entry["snapshot"] = snapshot
    entry["collected_at_kst"] = now_kst_label(now_utc)
    entry["fetch_error"] = None
    entry["fetched_at"] = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    return entry


def merge_meta(cfg: dict, old_meta: dict | None) -> dict:
    """새 meta 골격. 종목 처리 실패 시 old_meta의 기존 엔트리를 재사용하기 위한 헬퍼."""
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "order": cfg["order"],
        "tickers": {},
        "_old": (old_meta or {}).get("tickers", {}),
    }


def apply_failure(meta: dict, tid: str, error: str) -> None:
    """조회 실패 종목: 직전 정상 데이터가 있으면 유지하고 fetch_error만 설정."""
    old = meta["_old"].get(tid)
    if old:
        entry = dict(old)
        entry["fetch_error"] = error
        meta["tickers"][tid] = entry
    else:
        meta["tickers"][tid] = {"id": tid, "fetch_error": error}


def run_full() -> int:
    cfg = load_config()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    old_meta = None
    meta_path = DATA_DIR / "meta.json"
    if meta_path.exists():
        try:
            with open(meta_path, encoding="utf-8") as f:
                old_meta = json.load(f)
        except Exception:
            old_meta = None

    meta = merge_meta(cfg, old_meta)
    fx_cache: dict = {}
    failures = 0

    for tcfg in cfg["tickers"]:
        tid = tcfg["id"]
        try:
            entry, rows = process_ticker(tcfg, fx_cache, cfg.get("f7", {}))
            meta["tickers"][tid] = entry
            with open(HISTORY_DIR / f"{tid}.json", "w", encoding="utf-8") as f:
                json.dump({"id": tid, "rows": rows}, f, ensure_ascii=False)
            print(f"[OK]   {tid:5s} rows={len(rows)} "
                  f"{rows[0]['date']}..{rows[-1]['date']} "
                  f"premium={entry['snapshot']['premium']:+.2f}%")
        except Exception as e:
            failures += 1
            apply_failure(meta, tid, f"{type(e).__name__}: {e}")
            print(f"[FAIL] {tid:5s} {type(e).__name__}: {e}", file=sys.stderr)
            traceback.print_exc()

    del meta["_old"]
    meta["mode"] = "full"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    print(f"완료(전체): {len(cfg['tickers']) - failures}/{len(cfg['tickers'])} 종목 성공, "
          f"출력 -> {DATA_DIR}")
    return 0 if failures == 0 else 2


def run_intraday() -> int:
    """F2: 장중 스냅샷 전용 갱신. history/*.json은 읽기만 하고 쓰지 않는다."""
    cfg = load_config()
    meta_path = DATA_DIR / "meta.json"
    if not meta_path.exists():
        print("meta.json이 없습니다. 먼저 전체 실행(python src/fetch_data.py)을 하세요.",
              file=sys.stderr)
        return 1
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    fx_cache: dict = {}
    failures = 0
    for tcfg in cfg["tickers"]:
        tid = tcfg["id"]
        old_entry = meta["tickers"].get(tid)
        if not old_entry or not old_entry.get("snapshot"):
            print(f"[SKIP] {tid}: 기존 전체 실행 데이터 없음", file=sys.stderr)
            continue
        try:
            meta["tickers"][tid] = process_ticker_intraday(tcfg, fx_cache, old_entry)
            s = meta["tickers"][tid]["snapshot"]
            live = "장중" if (s.get("p_dr_intraday") or s.get("p_local_intraday")) else "종가"
            print(f"[OK]   {tid:5s} snapshot={s['premium']:+.2f}% ({live})")
        except Exception as e:
            failures += 1
            entry = dict(old_entry)
            entry["fetch_error"] = f"{type(e).__name__}: {e}"
            meta["tickers"][tid] = entry
            print(f"[FAIL] {tid:5s} {type(e).__name__}: {e}", file=sys.stderr)

    meta["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta["mode"] = "intraday"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    print(f"완료(장중 스냅샷): 실패 {failures}건, history 파일 불변")
    return 0 if failures == 0 else 2


def main() -> int:
    if "--intraday" in sys.argv[1:]:
        return run_intraday()
    return run_full()


if __name__ == "__main__":
    sys.exit(main())
