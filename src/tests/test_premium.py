"""단위 테스트 (네트워크 불필요) - 계산 로직·이월 처리·설정 무결성.

실행: python -m unittest discover -s src/tests -v
   (프로젝트 루트에서) 또는 python src/tests/test_premium.py
"""
import json
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datetime import datetime, timezone  # noqa: E402

from fetch_data import (  # noqa: E402
    CONFIG_PATH, apply_prev_delta, build_history, build_snapshot,
    compute_conversion, compute_premium, drop_in_progress, is_market_open,
    load_config, merge_meta, apply_failure,
)


def series(pairs):
    idx = pd.DatetimeIndex([p[0] for p in pairs])
    return pd.Series([float(p[1]) for p in pairs], index=idx)


class TestPremiumFormula(unittest.TestCase):
    def test_prd_example_skhy_ipo(self):
        """PRD 3.3절 검산 예 1: 공모가 $149, 원주 2,186,000원, r=0.1, FX 1385(예시)."""
        p = compute_premium(p_dr=149, fx=1385, p_local=2186000, ratio=0.1)
        # 149*1385/218600 - 1 = -0.0559698 -> 약 -5.6% (디스카운트)
        self.assertAlmostEqual(p, -5.59698, places=3)
        self.assertLess(p, 0)

    def test_zero_premium(self):
        self.assertAlmostEqual(compute_premium(100, 1000, 100000, 1), 0.0)

    def test_gdr_path_ratio_25(self):
        """PRD 검산 예 2 구조: SMSN $4188, r=25, FX 1385 -> 원주 환산 약 232,015원."""
        implied = 4188 * 1385 / 25
        self.assertAlmostEqual(implied, 232015.2, places=1)
        p = compute_premium(4188, 1385, 232015.2, 25)
        self.assertAlmostEqual(p, 0.0, places=4)

    def test_fx_cross_misapplication_detected(self):
        """환율 교차 오적용 시 프리미엄이 수십 배 틀어짐을 확인 (테스트 근거)."""
        correct = compute_premium(404.25, 32.43, 2370, 5)   # TSM + USD/TWD
        wrong = compute_premium(404.25, 1428.5, 2370, 5)    # TSM + USD/KRW (오적용)
        self.assertLess(abs(correct), 15)
        self.assertGreater(abs(wrong), 1000)


class TestBuildHistory(unittest.TestCase):
    def setUp(self):
        # DR: 1/5(월)~1/9(금) 중 1/7 휴장, 원주: 1/7 거래·1/8 휴장, 환율: 매영업일
        self.dr = series([("2026-01-05", 10), ("2026-01-06", 11),
                          ("2026-01-08", 12), ("2026-01-09", 13)])
        self.local = series([("2026-01-05", 10000), ("2026-01-06", 10100),
                             ("2026-01-07", 10200), ("2026-01-09", 10300)])
        self.fx = series([("2026-01-05", 1000), ("2026-01-06", 1000),
                          ("2026-01-07", 1005), ("2026-01-08", 1010),
                          ("2026-01-09", 1010)])

    def test_grid_is_union_of_trading_dates(self):
        rows = build_history(self.dr, self.local, self.fx, ratio=1)
        self.assertEqual([r["date"] for r in rows],
                         ["2026-01-05", "2026-01-06", "2026-01-07",
                          "2026-01-08", "2026-01-09"])

    def test_forward_fill_dr_with_flag(self):
        """DR 휴장일(1/7): 직전 DR 종가(11) 이월 + ff_dr 플래그."""
        rows = build_history(self.dr, self.local, self.fx, ratio=1)
        r = next(r for r in rows if r["date"] == "2026-01-07")
        self.assertTrue(r["ff_dr"])
        self.assertFalse(r["ff_local"])
        self.assertEqual(r["p_dr"], 11)
        expected = compute_premium(11, 1005, 10200, 1)
        self.assertAlmostEqual(r["premium"], expected, places=4)

    def test_forward_fill_local_with_flag(self):
        """원주 휴장일(1/8): 직전 원주 종가(10200) 이월 + ff_local 플래그."""
        rows = build_history(self.dr, self.local, self.fx, ratio=1)
        r = next(r for r in rows if r["date"] == "2026-01-08")
        self.assertTrue(r["ff_local"])
        self.assertFalse(r["ff_dr"])
        self.assertEqual(r["p_local"], 10200)

    def test_both_closed_date_skipped(self):
        """양쪽 모두 휴장(주말 등)인 날짜는 그리드에 없음."""
        rows = build_history(self.dr, self.local, self.fx, ratio=1)
        self.assertNotIn("2026-01-10", [r["date"] for r in rows])

    def test_history_start_cut(self):
        rows = build_history(self.dr, self.local, self.fx, ratio=1,
                             history_start="2026-01-07")
        self.assertEqual(rows[0]["date"], "2026-01-07")

    def test_no_leading_rows_before_all_series_exist(self):
        dr_late = series([("2026-01-08", 12), ("2026-01-09", 13)])
        rows = build_history(dr_late, self.local, self.fx, ratio=1)
        self.assertEqual(rows[0]["date"], "2026-01-08")

    def test_snapshot_uses_latest_of_each_series(self):
        snap = build_snapshot(self.dr, self.local, self.fx, ratio=1)
        self.assertEqual(snap["p_dr"], 13)
        self.assertEqual(snap["p_local"], 10300)
        self.assertEqual(snap["p_dr_date"], "2026-01-09")
        self.assertAlmostEqual(snap["premium"],
                               compute_premium(13, 1010, 10300, 1), places=4)


class TestConfig(unittest.TestCase):
    def test_config_loads_and_validates(self):
        cfg = load_config(CONFIG_PATH)
        self.assertEqual(len(cfg["tickers"]), 12)  # 2026-08-05 BABA 편입
        self.assertEqual(cfg["order"][:4], ["SKHY", "SMSN", "TSM", "BABA"])
        ids = {t["id"] for t in cfg["tickers"]}
        self.assertEqual(set(cfg["order"]), ids)

    def test_fx_mapping_by_currency(self):
        """통화별 환율 매핑 (교차 오적용 방지): KRW=X / TWD=X / HKD=X."""
        cfg = load_config(CONFIG_PATH)
        for t in cfg["tickers"]:
            if t["id"] == "TSM":
                self.assertEqual(t["fx_yahoo"], "TWD=X")
                self.assertEqual(t["local_currency"], "TWD")
            elif t["id"] == "BABA":
                self.assertEqual(t["fx_yahoo"], "HKD=X")
                self.assertEqual(t["local_currency"], "HKD")
                self.assertTrue(t["local_yahoo"].endswith(".HK"))
            else:
                self.assertEqual(t["fx_yahoo"], "KRW=X")
                self.assertEqual(t["local_currency"], "KRW")

    def test_prd_ratios(self):
        """확정 전환비율과 설정 파일 일치 (1차 PRD 3.0절 + BABA 기획 2026-08-05)."""
        expected = {"SKHY": 0.1, "SMSN": 25, "TSM": 5, "PKX": 0.25,
                    "SKM": 5 / 9, "LPL": 0.5, "KEP": 0.5, "KB": 1,
                    "SHG": 1, "WF": 3, "KT": 0.5, "BABA": 8}
        cfg = load_config(CONFIG_PATH)
        for t in cfg["tickers"]:
            self.assertAlmostEqual(t["ratio"], expected[t["id"]], places=12,
                                   msg=t["id"])

    def test_baba_config(self):
        """BABA 등록값 = 기획 문서 1.1절 (2026-08-05)."""
        cfg = load_config(CONFIG_PATH)
        b = next(t for t in cfg["tickers"] if t["id"] == "BABA")
        self.assertEqual(b["local_yahoo"], "9988.HK")
        self.assertEqual(b["ratio"], 8)
        self.assertEqual(b["history_start"], "2019-11-26")
        self.assertIn("fungible", b["conversion_note"])
        self.assertIn("sec.gov", b["_f7_refs"])


class TestPrevDelta(unittest.TestCase):
    """F4: 직전 데이터 포인트 대비 변동(%p)."""

    ROWS = [{"date": "2026-01-07", "premium": 10.0},
            {"date": "2026-01-08", "premium": 12.5},
            {"date": "2026-01-09", "premium": 11.0}]

    def test_daily_final_uses_second_to_last(self):
        """일일 확정: 스냅샷 날짜 = 마지막 행 날짜 -> 직전 행 대비."""
        snap = {"premium": 11.0, "p_dr_date": "2026-01-09", "p_local_date": "2026-01-09"}
        apply_prev_delta(snap, self.ROWS)
        self.assertEqual(snap["prev_date"], "2026-01-08")
        self.assertAlmostEqual(snap["delta_pp"], -1.5, places=4)

    def test_intraday_uses_last_confirmed(self):
        """장중: 스냅샷 날짜가 히스토리보다 앞 -> 마지막 확정 행 대비."""
        snap = {"premium": 13.2, "p_dr_date": "2026-01-09", "p_local_date": "2026-01-12"}
        apply_prev_delta(snap, self.ROWS)
        self.assertEqual(snap["prev_date"], "2026-01-09")
        self.assertAlmostEqual(snap["delta_pp"], 2.2, places=4)

    def test_no_prev_point(self):
        """상장 첫 데이터: 직전 포인트 없음 -> null (표시 생략)."""
        snap = {"premium": 5.0, "p_dr_date": "2026-01-07", "p_local_date": "2026-01-07"}
        apply_prev_delta(snap, self.ROWS)
        self.assertIsNone(snap["delta_pp"])
        self.assertIsNone(snap["prev_date"])


class TestVolumeFields(unittest.TestCase):
    """F6: 히스토리 포인트 vol_dr/vol_local - 이월 포인트는 null."""

    def test_volume_and_ff_null(self):
        dr = series([("2026-01-05", 10), ("2026-01-06", 11), ("2026-01-08", 12)])
        local = series([("2026-01-05", 1000), ("2026-01-06", 1010),
                        ("2026-01-07", 1020), ("2026-01-08", 1030)])
        fx = series([("2026-01-05", 1400), ("2026-01-06", 1400),
                     ("2026-01-07", 1400), ("2026-01-08", 1400)])
        vol_dr = series([("2026-01-05", 111), ("2026-01-06", 222), ("2026-01-08", 444)])
        vol_local = series([("2026-01-05", 5000), ("2026-01-06", 5100),
                            ("2026-01-07", 5200), ("2026-01-08", 5300)])
        rows = build_history(dr, local, fx, 1, vol_dr=vol_dr, vol_local=vol_local)
        by_date = {r["date"]: r for r in rows}
        self.assertEqual(by_date["2026-01-06"]["vol_dr"], 222)
        self.assertEqual(by_date["2026-01-06"]["vol_local"], 5100)
        # 2026-01-07: DR 휴장(이월) -> vol_dr null, 원주는 실거래
        self.assertIsNone(by_date["2026-01-07"]["vol_dr"])
        self.assertEqual(by_date["2026-01-07"]["vol_local"], 5200)

    def test_volume_omitted_when_series_absent(self):
        dr = series([("2026-01-05", 10), ("2026-01-06", 11)])
        local = series([("2026-01-05", 1000), ("2026-01-06", 1010)])
        fx = series([("2026-01-05", 1400), ("2026-01-06", 1400)])
        rows = build_history(dr, local, fx, 1)
        self.assertIsNone(rows[0]["vol_dr"])
        self.assertIsNone(rows[0]["vol_local"])


class TestConversionValidation(unittest.TestCase):
    """F7 검증 A/B (PRD 7.4 완료 기준: 모의값 3케이스)."""

    F7 = {"auto_reject_threshold": 0.9, "limit_margin": 1.05}
    TCFG = {"id": "TEST", "ratio": 0.1,
            "conversion_limit_local": 17790000,
            "limit_as_of": "2026-07-29", "limit_src": "테스트 출처"}
    N_TOTAL = 709854891

    def test_case1_company_wide_rejected(self):
        """검증 A: 전사 발행량의 ADS 환산치(원주환산 100%) -> 기각."""
        cands = {"sharesOutstanding": self.N_TOTAL * 10}  # r=0.1 -> 환산 100%
        conv = compute_conversion(self.TCFG, self.F7, self.N_TOTAL, cands,
                                  150.0, 1600000.0, "2026-08-04")
        self.assertEqual(len(conv["rejected_auto"]), 1)
        self.assertIn("검증 A 기각", conv["rejected_auto"][0]["reason"])
        # 수동값 없음 -> 미확인 (cv 없음)
        self.assertIsNone(conv["n_dr"])
        self.assertNotIn("cv", conv)

    def test_case2_limit_violation_rejected(self):
        """검증 B: 원주환산이 한도 * 1.05 초과 -> 기각."""
        cands = {"sharesOutstanding": 200000000}  # 환산 2,000만주 > 1,779만 * 1.05
        conv = compute_conversion(self.TCFG, self.F7, self.N_TOTAL, cands,
                                  150.0, 1600000.0, "2026-08-04")
        self.assertEqual(len(conv["rejected_auto"]), 1)
        self.assertIn("검증 B 기각", conv["rejected_auto"][0]["reason"])
        self.assertIsNone(conv["n_dr"])

    def test_case3_valid_candidate_adopted(self):
        """정상 모의값 -> 자동 채택 + cv/lu/금액 계산 검증."""
        cands = {"sharesOutstanding": 170000000}  # 환산 1,700만주 (2.39%, 한도 내)
        conv = compute_conversion(self.TCFG, self.F7, self.N_TOTAL, cands,
                                  150.0, 1600000.0, "2026-08-04")
        self.assertEqual(conv["n_dr"], 170000000)
        self.assertEqual(conv["n_dr_source"], "auto")
        self.assertAlmostEqual(conv["cv"], 17000000 / self.N_TOTAL * 100, places=3)
        self.assertAlmostEqual(conv["lu"], 17000000 / 17790000 * 100, places=3)
        self.assertAlmostEqual(conv["v_dr_usd"], 170000000 * 150.0, places=1)
        self.assertAlmostEqual(
            conv["v_local"], (self.N_TOTAL - 17000000) * 1600000.0, delta=1)

    def test_manual_fallback_used_after_rejection(self):
        """자동 기각 시 수동 폴백 채택 + 출처 라벨 필드."""
        tcfg = dict(self.TCFG)
        tcfg.update({"dr_outstanding_manual": 177900000,
                     "dr_outstanding_as_of": "2026-07-31",
                     "dr_outstanding_src": "테스트 수동 출처"})
        cands = {"sharesOutstanding": self.N_TOTAL * 10}
        conv = compute_conversion(tcfg, self.F7, self.N_TOTAL, cands,
                                  150.0, 1600000.0, "2026-08-04")
        self.assertEqual(conv["n_dr_source"], "manual")
        self.assertEqual(conv["n_dr"], 177900000)
        self.assertEqual(conv["n_dr_as_of"], "2026-07-31")
        # 한도 소진율 100% (한도 전량)
        self.assertAlmostEqual(conv["lu"], 100.0, places=2)

    def test_conversion_note_passthrough(self):
        """conversion_note가 설정 파일에서 conversion dict로 전달된다."""
        tcfg = dict(self.TCFG)
        tcfg["conversion_note"] = "테스트 구조 각주"
        conv = compute_conversion(tcfg, self.F7, self.N_TOTAL, {},
                                  150.0, 1600000.0, "2026-08-04")
        self.assertEqual(conv["note"], "테스트 구조 각주")
        # 미기재 종목은 None
        conv2 = compute_conversion(self.TCFG, self.F7, self.N_TOTAL, {},
                                   150.0, 1600000.0, "2026-08-04")
        self.assertIsNone(conv2["note"])

    def test_no_limit_stock_skips_lu(self):
        """한도 미확인 종목: lu/limit_pct 없음(null), cv는 계산."""
        tcfg = {"id": "X", "ratio": 1}
        cands = {"sharesOutstanding": 30000000}
        conv = compute_conversion(tcfg, self.F7, 300000000, cands,
                                  100.0, 100000.0, "2026-08-04")
        self.assertEqual(conv["n_dr"], 30000000)
        self.assertIsNone(conv["lu"])
        self.assertIsNone(conv["limit_pct"])
        self.assertAlmostEqual(conv["cv"], 10.0, places=4)


class TestIntradayHelpers(unittest.TestCase):
    """F2: 세션 창·진행 중 행 제거."""

    def test_krx_open_and_closed(self):
        # 2026-08-04(화) KST 11:00 = UTC 02:00 -> KRX 개장
        open_t = datetime(2026, 8, 4, 2, 0, tzinfo=timezone.utc)
        self.assertTrue(is_market_open("KRX", open_t))
        # KST 06:30 (일일 확정 실행 시각) -> 전 시장 폐장
        daily_t = datetime(2026, 8, 3, 21, 30, tzinfo=timezone.utc)
        for ex in ("KRX", "TWSE", "Nasdaq", "NYSE", "LSE IOB"):
            self.assertFalse(is_market_open(ex, daily_t), ex)

    def test_us_open_at_kst_night(self):
        # KST 23:30 = UTC 14:30 -> 미국 개장
        t = datetime(2026, 8, 4, 14, 30, tzinfo=timezone.utc)
        self.assertTrue(is_market_open("Nasdaq", t))
        self.assertFalse(is_market_open("KRX", t))

    def test_hkex_session(self):
        """HKEX: KST 10:30~17:10 창 (점심 휴장 포함 - 당일 값 미확정 판정 목적)."""
        # KST 11:00 (오전 세션) -> 개장
        self.assertTrue(is_market_open("HKEX",
                        datetime(2026, 8, 4, 2, 0, tzinfo=timezone.utc)))
        # KST 12:30 = HKT 11:30 점심 전 오전 세션 -> 개장.
        # KST 13:30 = HKT 12:30 점심 휴장 -> 창 취급(당일 종가 미확정이므로 의도)
        self.assertTrue(is_market_open("HKEX",
                        datetime(2026, 8, 4, 4, 30, tzinfo=timezone.utc)))
        # KST 17:30 = HKT 16:30 마감 후 -> 폐장
        self.assertFalse(is_market_open("HKEX",
                         datetime(2026, 8, 4, 8, 30, tzinfo=timezone.utc)))
        # KST 09:00 개장 전 -> 폐장
        self.assertFalse(is_market_open("HKEX",
                         datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)))
        # 일일 확정 실행 시각(KST 06:30) -> 폐장
        self.assertFalse(is_market_open("HKEX",
                         datetime(2026, 8, 3, 21, 30, tzinfo=timezone.utc)))

    def test_drop_in_progress_removes_today_row(self):
        # KRX 개장 중(KST 11:00), 마지막 행이 KRX 오늘(2026-08-04) -> 제거
        now = datetime(2026, 8, 4, 2, 0, tzinfo=timezone.utc)
        s = series([("2026-08-01", 100), ("2026-08-04", 105)])
        out = drop_in_progress(s, "KRX", now)
        self.assertEqual(len(out), 1)
        self.assertEqual(out.index[-1].strftime("%Y-%m-%d"), "2026-08-01")

    def test_drop_in_progress_keeps_confirmed(self):
        # 폐장 시각이면 오늘 행이라도 유지 (확정 종가)
        now = datetime(2026, 8, 4, 8, 0, tzinfo=timezone.utc)  # KST 17:00
        s = series([("2026-08-01", 100), ("2026-08-04", 105)])
        out = drop_in_progress(s, "KRX", now)
        self.assertEqual(len(out), 2)


class TestPanningHarness(unittest.TestCase):
    """F1 패닝 드래그 시퀀스 (Node 하니스 test_panning.mjs 위임 실행).

    드래그 중 재렌더로 svg가 교체돼도 제스처가 유지되는지 검증
    (2026-08-04 사용자 보고 버그 회귀 방지).
    """

    def test_drag_sequence(self):
        import shutil
        import subprocess
        node = shutil.which("node")
        if not node:
            self.skipTest("node 미설치 - 하니스 실행 불가")
        mjs = Path(__file__).resolve().parent / "test_panning.mjs"
        if not (Path(__file__).resolve().parents[1] / "web" / "data" /
                "history" / "TSM.json").exists():
            self.skipTest("TSM 히스토리 데이터 없음 - fetch_data.py 선실행 필요")
        res = subprocess.run([node, str(mjs)], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=60)
        self.assertEqual(res.returncode, 0,
                         f"패닝 하니스 실패:\n{res.stdout}\n{res.stderr}")

    def test_chart_calcs(self):
        """F6 거래량 등락 색상·HKD 표기 (Node 하니스 test_chart.mjs 위임 실행)."""
        self._run_node_harness("test_chart.mjs", "차트 계산")

    def test_volume_default_regression(self):
        """거래량 기본 표시 전환 회귀 (test_vol_default.mjs 위임 실행).

        데이터 없는 심볼·주/월 단위·이월 포인트·패닝/호버 상호작용 점검.
        """
        self._run_node_harness("test_vol_default.mjs", "거래량 기본 표시")

    def _run_node_harness(self, filename: str, label: str):
        import shutil
        import subprocess
        node = shutil.which("node")
        if not node:
            self.skipTest("node 미설치 - 하니스 실행 불가")
        mjs = Path(__file__).resolve().parent / filename
        res = subprocess.run([node, str(mjs)], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=60)
        self.assertEqual(res.returncode, 0,
                         f"{label} 하니스 실패:\n{res.stdout}\n{res.stderr}")


class TestFailureMerge(unittest.TestCase):
    def test_failure_keeps_previous_entry(self):
        """조회 실패 시 직전 정상 데이터 유지 + fetch_error 설정 (PRD 5절 갱신 실패 기준)."""
        old = {"tickers": {"KB": {"id": "KB", "snapshot": {"premium": -0.78},
                                  "fetch_error": None}}}
        meta = merge_meta({"order": ["KB"]}, old)
        apply_failure(meta, "KB", "RuntimeError: boom")
        entry = meta["tickers"]["KB"]
        self.assertEqual(entry["snapshot"]["premium"], -0.78)
        self.assertEqual(entry["fetch_error"], "RuntimeError: boom")

    def test_failure_without_previous_data(self):
        meta = merge_meta({"order": ["KB"]}, None)
        apply_failure(meta, "KB", "boom")
        self.assertEqual(meta["tickers"]["KB"]["fetch_error"], "boom")
        self.assertNotIn("snapshot", meta["tickers"]["KB"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
