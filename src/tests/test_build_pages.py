"""프리렌더 생성기(build_pages.py) 단위 테스트 (네트워크 불필요).

실행: python -m unittest discover -s src/tests -p "test_*.py" -v
"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_pages as bp  # noqa: E402

SITE = {"site_name": "테스트 트래커", "base_url": "https://test.example.com"}


def fake_meta():
    def entry(tid, name, dr_type="ADR", currency="KRW", fx_label="USD/KRW",
              fetch_error=None):
        return {
            "id": tid, "name": name, "dr_ticker": tid, "dr_exchange": "NYSE",
            "dr_type": dr_type, "local_code": "000001", "local_exchange": "KRX",
            "local_currency": currency, "fx_label": fx_label, "ratio": 0.5,
            "ratio_display": "0.5 (ADS 1주 = 보통주 1/2주)",
            "snapshot": {"premium": 12.3456, "p_dr": 143.73, "p_dr_date": "2026-07-31",
                         "p_local": 1567000, "p_local_date": "2026-08-03",
                         "fx": 1428.5, "fx_date": "2026-08-03",
                         "implied_local": 2053000.0},
            "spark": [["2026-07-01", 1.0], ["2026-07-02", -2.0], ["2026-07-03", 3.0]],
            "fetch_error": fetch_error,
        }
    return {
        "generated_at": "2026-08-03T10:00:00Z",
        "order": ["SKHY", "SMSN"],
        "tickers": {
            "SKHY": entry("SKHY", "SK하이닉스"),
            "SMSN": entry("SMSN", "삼성전자", dr_type="GDR"),
        },
    }


GUIDE_WITH_FAQ = """---
title: ADR 프리미엄이란?
description: 프리미엄 계산법 설명.
---

## 개요

**프리미엄**은 가격 차이 비율이다. [출처](https://example.com/a) 참고.

- 항목 하나
- 항목 둘

## FAQ

### 프리미엄이 뭔가요?

가격 차이 비율입니다.

### 왜 생기나요?

수급 차이 때문입니다.
"""

GUIDE_NO_FAQ = """---
title: 전환 안내
description: 전환 절차.
---

## 절차

전환은 예탁은행을 통한다.
"""


class TestBuildAll(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        out = Path(cls.tmp.name)
        guides = [
            {"slug": "adr-premium", **cls._parse(GUIDE_WITH_FAQ)},
            {"slug": "adr-conversion", **cls._parse(GUIDE_NO_FAQ)},
        ]
        cls.written = bp.build_all(fake_meta(), SITE, guides, out)
        cls.out = out

    @staticmethod
    def _parse(text):
        fm, body = bp.parse_front_matter(text)
        h, faqs = bp.md_to_html(body)
        return {"title": fm["title"], "description": fm.get("description", ""),
                "html": h, "faqs": faqs}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def read(self, rel):
        return (self.out / rel).read_text(encoding="utf-8")

    # ---- D1: 핵심 콘텐츠가 초기 HTML에 텍스트로 존재 ----

    def test_main_has_core_content(self):
        h = self.read("index.html")
        for needle in ("SK하이닉스", "+12.35%", "투자 조언이 아닙니다",
                       'href="stocks/skhy/"', "card-spark", "<path",
                       "DR $143.73", "원주 1,567,000원"):
            self.assertIn(needle, h, needle)

    def test_stock_page_has_core_content(self):
        h = self.read("stocks/skhy/index.html")
        for needle in ("SK하이닉스", "+12.35%", "DR 가격", "원주 가격",
                       "환율 (USD/KRW)", "전환비율 r", "2026-07-31",
                       "계산 방식", "투자 조언이 아닙니다",
                       "0.5 (ADS 1주 = 보통주 1/2주)"):
            self.assertIn(needle, h, needle)

    def test_gdr_page_has_notice(self):
        h = self.read("stocks/smsn/index.html")
        self.assertIn("GDR(런던)", h)
        self.assertIn("런던증권거래소(IOB)", h)

    def test_stock_page_has_hydration_hooks(self):
        h = self.read("stocks/skhy/index.html")
        self.assertIn('data-page="stock"', h)
        self.assertIn('data-root="../../"', h)
        self.assertIn('id="page-data"', h)
        self.assertIn('class="period-tab', h)
        self.assertIn("noscript", h)

    def test_hash_redirect_script_present(self):
        h = self.read("index.html")
        self.assertIn('location.hash.match', h)
        self.assertIn('"skhy"', h)  # known ticker 목록 포함
        self.assertIn('location.replace("stocks/" + t + "/")', h)

    # ---- D2: 메타태그 ----

    def test_main_meta_tags(self):
        h = self.read("index.html")
        self.assertIn("<title>한국·대만 ADR 프리미엄 추적 - 테스트 트래커</title>", h)
        self.assertIn('<meta name="description"', h)
        self.assertIn('<link rel="canonical" href="https://test.example.com/">', h)
        self.assertIn('<meta property="og:title"', h)
        self.assertIn('<meta property="og:description"', h)

    def test_stock_meta_override_and_default(self):
        skhy = self.read("stocks/skhy/index.html")
        self.assertIn("SK하이닉스 ADR 프리미엄(SKHY 괴리율) 차트 - 테스트 트래커", skhy)
        self.assertIn('href="https://test.example.com/stocks/skhy/"', skhy)
        smsn = self.read("stocks/smsn/index.html")
        self.assertIn("삼성전자 GDR(SMSN) 프리미엄 차트", smsn)

    def test_default_seo_template_for_non_override(self):
        meta = fake_meta()
        meta["order"] = ["KB"]
        t = dict(meta["tickers"]["SKHY"])
        t.update({"id": "KB", "name": "KB금융", "dr_ticker": "KB",
                  "local_code": "105560"})
        meta["tickers"] = {"KB": t}
        title, desc = bp.stock_seo(t, SITE)
        self.assertEqual(title, "KB금융 ADR 프리미엄(KB 괴리율) 차트 - 테스트 트래커")
        self.assertIn("원주(105560)", desc)
        self.assertIn("전환비율(0.5)", desc)

    # ---- D3: sitemap / robots ----

    def test_sitemap(self):
        s = self.read("sitemap.xml")
        self.assertEqual(s.count("<url>"), 5)  # 메인 1 + 종목 2 + 가이드 2
        self.assertIn("https://test.example.com/stocks/smsn/", s)
        self.assertIn("https://test.example.com/guide/adr-premium/", s)
        self.assertIn("<lastmod>2026-08-03</lastmod>", s)

    def test_robots(self):
        r = self.read("robots.txt")
        self.assertIn("User-agent: *", r)
        self.assertIn("Sitemap: https://test.example.com/sitemap.xml", r)

    # ---- D4: JSON-LD ----

    def test_main_jsonld_website_org(self):
        h = self.read("index.html")
        self.assertIn('"@type": "WebSite"', h)
        self.assertIn('"@type": "Organization"', h)

    def test_stock_jsonld_breadcrumb(self):
        h = self.read("stocks/skhy/index.html")
        self.assertIn('"@type": "BreadcrumbList"', h)
        self.assertIn('"name": "SK하이닉스"', h)

    def test_guide_faq_jsonld_only_when_faq_exists(self):
        with_faq = self.read("guide/adr-premium/index.html")
        self.assertIn('"@type": "FAQPage"', with_faq)
        self.assertIn('"프리미엄이 뭔가요?"', with_faq.replace('"name": ', '"'))
        without = self.read("guide/adr-conversion/index.html")
        self.assertNotIn("FAQPage", without)

    # ---- 가이드 변환 ----

    def test_guide_markdown_rendering(self):
        h = self.read("guide/adr-premium/index.html")
        self.assertIn("<h1>ADR 프리미엄이란?</h1>", h)
        self.assertIn("<strong>프리미엄</strong>", h)
        self.assertIn('<a href="https://example.com/a" rel="noopener">출처</a>', h)
        self.assertIn("<li>항목 하나</li>", h)
        self.assertIn("투자 조언이 아닙니다", h)

    def test_guide_listed_on_main(self):
        h = self.read("index.html")
        self.assertIn('href="guide/adr-premium/"', h)


class TestFailureRendering(unittest.TestCase):
    def test_fetch_error_badge_prerendered(self):
        meta = fake_meta()
        meta["tickers"]["SKHY"]["fetch_error"] = "boom"
        with tempfile.TemporaryDirectory() as tmp:
            bp.build_all(meta, SITE, [], Path(tmp))
            main = (Path(tmp) / "index.html").read_text(encoding="utf-8")
            self.assertIn("갱신 실패, 2026-07-31 기준", main)
            stock = (Path(tmp) / "stocks/skhy/index.html").read_text(encoding="utf-8")
            self.assertIn("마지막 정상값(2026-07-31 기준)", stock)

    def test_no_snapshot_renders_placeholder(self):
        meta = fake_meta()
        meta["tickers"]["SKHY"]["snapshot"] = None
        meta["tickers"]["SKHY"]["fetch_error"] = "no data"
        with tempfile.TemporaryDirectory() as tmp:
            bp.build_all(meta, SITE, [], Path(tmp))
            main = (Path(tmp) / "index.html").read_text(encoding="utf-8")
            self.assertIn("데이터 없음 (갱신 실패)", main)


class TestMarkdownParser(unittest.TestCase):
    def test_front_matter(self):
        fm, body = bp.parse_front_matter("---\ntitle: T\ndescription: D\n---\n\n본문")
        self.assertEqual(fm["title"], "T")
        self.assertEqual(fm["description"], "D")
        self.assertIn("본문", body)

    def test_faq_extraction(self):
        _, faqs = bp.md_to_html("## FAQ\n\n### 질문1?\n\n답1.\n\n### 질문2?\n\n답2.")
        self.assertEqual(len(faqs), 2)
        self.assertEqual(faqs[0]["question"], "질문1?")
        self.assertEqual(faqs[0]["answer"], "답1.")

    def test_no_faq_outside_faq_section(self):
        _, faqs = bp.md_to_html("## 일반 섹션\n\n### 소제목\n\n내용.")
        self.assertEqual(faqs, [])

    def test_html_escaped(self):
        h, _ = bp.md_to_html("일반 <script>alert(1)</script> 텍스트")
        self.assertNotIn("<script>", h)
        self.assertIn("&lt;script&gt;", h)

    # ---- 마케팅팀 실수신 원고 형식 (2026-08-03 수신분) ----

    def test_comment_front_matter(self):
        text = ("<!--\ntitle: 제목 T\nmeta_description: 설명 D\n"
                "slug: /guide/x/\ntarget_keywords: a, b\n-->\n\n# 제목 T\n\n본문.")
        fm, body = bp.parse_front_matter(text)
        self.assertEqual(fm["title"], "제목 T")
        self.assertEqual(fm["description"], "설명 D")
        self.assertNotIn("<!--", body)

    def test_h1_skipped_in_body(self):
        h, _ = bp.md_to_html("# 중복 제목\n\n## 섹션\n\n본문.")
        self.assertNotIn("<h1>", h)
        self.assertIn("<h2>섹션</h2>", h)

    def test_qa_faq_format(self):
        md = ("## 자주 묻는 질문 (FAQ)\n\n"
              "**Q. 프리미엄이란 무엇인가요?**\n"
              "A. 가격 차이 비율입니다.\n답의 두 번째 문장입니다.\n\n"
              "**Q. 왜 생기나요?**\nA. 수급 때문입니다.\n")
        h, faqs = bp.md_to_html(md)
        self.assertEqual(len(faqs), 2)
        self.assertEqual(faqs[0]["question"], "프리미엄이란 무엇인가요?")
        self.assertEqual(faqs[0]["answer"], "가격 차이 비율입니다. 답의 두 번째 문장입니다.")
        self.assertEqual(faqs[1]["answer"], "수급 때문입니다.")
        self.assertIn("<strong>Q. 프리미엄이란 무엇인가요?</strong>", h)

    def test_table_rendering(self):
        md = "| 기업 | r |\n|---|---|\n| SK하이닉스 | 0.1 |\n| TSMC | 5 |"
        h, _ = bp.md_to_html(md)
        self.assertIn('<div class="table-wrap"><table>', h)
        self.assertIn("<th>기업</th>", h)
        self.assertIn("<td>SK하이닉스</td>", h)
        self.assertEqual(h.count("<tr>"), 3)

    def test_horizontal_rule_and_italic(self):
        h, _ = bp.md_to_html("본문.\n\n---\n\n*정보 제공 목적이며 투자 조언이 아닙니다.*")
        self.assertIn("<hr>", h)
        self.assertIn("<em>정보 제공 목적이며 투자 조언이 아닙니다.</em>", h)

    def test_bare_url_autolink(self):
        h, _ = bp.md_to_html("출처: https://www.sec.gov/a/b.htm 참고.")
        self.assertIn('<a href="https://www.sec.gov/a/b.htm" rel="noopener">', h)

    def test_markdown_link_not_double_linked(self):
        h, _ = bp.md_to_html("[출처](https://example.com/a) 참고.")
        self.assertEqual(h.count("<a "), 1)

    # ---- 2026-08-04 QA 리포트 FAIL #1/#2 회귀 테스트 ----

    def test_code_fence_rendered_verbatim(self):
        """FAIL #1-(1): 펜스 내부는 이스케이프만 - 줄바꿈 유지, * 보존, 백틱 미노출."""
        md = ("본문.\n\n```\nADR 이론가(달러) = (P_local * r) / FX\n"
              "프리미엄(%) = (P_dr * FX / (P_local * r) - 1) * 100\n```\n\n다음 문단.")
        h, _ = bp.md_to_html(md)
        self.assertIn("<pre><code>", h)
        self.assertIn("(P_local * r) / FX\n프리미엄(%)", h)  # 줄바꿈 유지 + * 보존
        self.assertNotIn("<em>", h)
        self.assertNotIn("```", h)
        self.assertNotIn("``", h)

    def test_code_fence_no_markdown_inside(self):
        h, _ = bp.md_to_html("```\n**굵게 아님** [링크 아님](https://x.com) - 목록 아님\n```")
        self.assertNotIn("<strong>", h)
        self.assertNotIn("<a ", h)
        self.assertNotIn("<ul>", h)
        self.assertIn("**굵게 아님**", h)

    def test_unclosed_fence_does_not_crash(self):
        h, _ = bp.md_to_html("```\n닫히지 않은 펜스")
        self.assertIn("<pre><code>", h)
        self.assertIn("닫히지 않은 펜스", h)

    def test_multiline_list_item_merged(self):
        """FAIL #1-(2): 여러 줄 목록 항목이 직전 li에 병합, ul 안에 p 없음."""
        md = ("- **전환 제약**: 원주와 ADR 간 전환이 자유롭지 않으면 차익거래가\n"
              "  막혀 가격 차이가 유지된다.\n"
              "- 두 번째 항목은 한 줄.\n")
        h, _ = bp.md_to_html(md)
        self.assertEqual(h.count("<li>"), 2)
        self.assertIn("차익거래가 막혀 가격 차이가 유지된다.", h)
        self.assertNotIn("<ul><p>", h.replace("</li>", "").replace("<li>", ""))
        self.assertNotIn("<p>", h)  # 목록만 있는 입력 - p 조각이 없어야 함

    def test_multiline_ordered_list_item_merged(self):
        md = ("1. **거래시간이 겹치지 않는다.** 한국 장과 미국 정규장은\n"
              "   겹치는 시간이 없다.\n"
              "2. 둘째.\n")
        h, _ = bp.md_to_html(md)
        self.assertEqual(h.count("<li>"), 2)
        self.assertIn("미국 정규장은 겹치는 시간이 없다.", h)

    def test_hr_terminates_faq_collection(self):
        """FAIL #2: --- 이후 말미 문구가 마지막 FAQ 답변에 유입되지 않는다."""
        md = ("## FAQ\n\n**Q. 질문?**\nA. 답변입니다.\n\n---\n\n"
              "*본 글은 정보 제공 목적이며 투자 조언이 아닙니다.*\n")
        h, faqs = bp.md_to_html(md)
        self.assertEqual(len(faqs), 1)
        self.assertEqual(faqs[0]["answer"], "답변입니다.")
        self.assertNotIn("투자 조언", faqs[0]["answer"])
        self.assertIn("<hr>", h)
        self.assertIn("<em>본 글은 정보 제공 목적이며 투자 조언이 아닙니다.</em>", h)

    def test_multiplication_asterisks_not_italicized(self):
        """FAIL #1-(3): 공백 둘러싸인 *는 곱셈 기호 - <em> 변환 금지."""
        md = "프리미엄(%) = (ADR 가격 * 환율 / (원주 가격 * 전환비율) - 1) * 100 입니다."
        h, _ = bp.md_to_html(md)
        self.assertNotIn("<em>", h)
        self.assertEqual(h.count("*"), 3)  # 곱셈 기호 3개 그대로 보존

    def test_faq_answer_with_multiplication_stays_verbatim(self):
        md = ("## FAQ\n\n**Q. 어떻게 계산하나요?**\n"
              "A. 프리미엄(%) = (ADR 가격 * 환율 / (원주 가격 * 전환비율) - 1) * 100 입니다.\n")
        h, faqs = bp.md_to_html(md)
        self.assertEqual(faqs[0]["answer"],
                         "프리미엄(%) = (ADR 가격 * 환율 / (원주 가격 * 전환비율) - 1) * 100 입니다.")
        self.assertNotIn("<em>", h)


class TestV2Rendering(unittest.TestCase):
    """v2 F4/F8/F7/F2 프리렌더 (2026-08-04 PRD)."""

    @staticmethod
    def meta_v2():
        m = fake_meta()
        t = m["tickers"]["SKHY"]
        t["snapshot"].update({
            "delta_pp": 1.2534, "prev_premium": 11.0922, "prev_date": "2026-08-01",
            "p_dr_intraday": False, "p_local_intraday": False, "fx_intraday": False,
        })
        t["collected_at_kst"] = "08/04 06:31"
        t["shares"] = {"n_total": 709854891, "n_total_field": "info.sharesOutstanding",
                       "n_total_as_of": "2026-08-03", "mcap_local": 1112342615397000.0,
                       "mcap_yahoo": None, "mcap_warn": False}
        t["conversion"] = {
            "limit": 17790000, "limit_as_of": "2026-07-10",
            "limit_src": "SEC 424B4 (Reg. No. 333-296987) - 총발행의 2.5%, IPO로 전량 소진",
            "n_dr": 177900000, "n_dr_source": "manual",
            "n_dr_as_of": "2026-07-10",
            "n_dr_src": "SEC 424B4 발행 시점(2026-07-10) 기준 - 이후 소각분 미반영 가능",
            "note": "ADR -> 원주 전환은 자유, 원주 -> ADR 추가 발행은 한도(총발행의 2.5%) "
                    "전량 소진으로 신규 절차 승인 전 불가",
            "n_dr_local": 17790000, "cv": 2.5061, "lu": 100.0, "limit_pct": 2.5061,
            "v_dr_usd": 25569000000.0, "v_local": 1084468496000000.0,
            "rejected_auto": [{"field": "sharesOutstanding", "value": 7098548910,
                               "reason": "검증 A 기각: ..."}],
        }
        # SMSN: 미확인 폴백 (자동 기각 + 수동 없음 + note 없음 - 구조 미조사)
        m["tickers"]["SMSN"]["conversion"] = {
            "limit": None, "limit_as_of": None, "limit_src": None,
            "n_dr": None, "n_dr_source": None, "n_dr_as_of": None, "n_dr_src": None,
            "note": None,
            "rejected_auto": [{"field": "sharesOutstanding", "value": 271707008,
                               "reason": "검증 A 기각: ..."}],
        }
        return m

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        bp.build_all(cls.meta_v2(), SITE, [], cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def read(self, rel):
        return (self.out / rel).read_text(encoding="utf-8")

    # F4
    def test_delta_on_card_and_detail(self):
        main = self.read("index.html")
        self.assertIn("(+1.25%p)", main)
        self.assertIn('title="08/01 대비"', main)
        detail = self.read("stocks/skhy/index.html")
        self.assertIn("(+1.25%p, 08/01 대비)", detail)

    def test_delta_omitted_without_prev(self):
        smsn = self.read("stocks/smsn/index.html")  # delta 필드 없음
        self.assertNotIn("%p,", smsn)

    # F8
    def test_market_cap_card(self):
        detail = self.read("stocks/skhy/index.html")
        self.assertIn("원주 시가총액", detail)
        self.assertIn("1,112.3조원", detail)
        self.assertIn("2026-08-03 종가 기준", detail)
        self.assertIn("약 $", detail)  # USD 병기

    # F7
    def test_conversion_section_full(self):
        detail = self.read("stocks/skhy/index.html")
        for needle in ("전환 현황", "전환한도: 원주 기준 17,790,000주",
                       "기준일 2026-07-10", "SEC 424B4 (Reg. No. 333-296987)",
                       "현재 전환율", "2.51%",
                       "한도 소진율", "100.00%", "DR 시장 금액", "현지 시장 금액",
                       "SEC 424B4 발행 시점(2026-07-10) 기준 - 이후 소각분 미반영 가능",
                       "gauge-limit",
                       "두 시장 금액의 합은 시가총액과 일치하지 않을 수"):
            self.assertIn(needle, detail, needle)

    def test_conversion_note_rendered(self):
        """conversion_note: 값 있는 종목(SKHY)과 미확인 종목 모두에서 각주 표시."""
        detail = self.read("stocks/skhy/index.html")
        self.assertIn("전량 소진으로 신규 절차 승인 전 불가", detail)
        self.assertIn('class="chart-note conv-note"', detail)
        # 미확인 + note 있는 종목: 수치 없이도 구조 각주 표시
        m = self.meta_v2()
        m["tickers"]["SMSN"]["conversion"]["note"] = (
            "원주 -> ADR 신규 예탁은 소각분 범위 내 + 초과 시 발행사 동의 필요 (테스트)")
        with tempfile.TemporaryDirectory() as tmp:
            bp.build_all(m, SITE, [], Path(tmp))
            page = (Path(tmp) / "stocks/smsn/index.html").read_text(encoding="utf-8")
            self.assertIn("데이터 미확인", page)
            self.assertIn("초과 시 발행사 동의 필요 (테스트)", page)

    def test_conversion_note_absent_when_missing(self):
        """note 없는 종목(SMSN - 구조 미조사): conv-note 각주 미표시."""
        smsn = self.read("stocks/smsn/index.html")
        self.assertNotIn("conv-note", smsn)

    def test_conversion_amounts_abbreviated(self):
        detail = self.read("stocks/skhy/index.html")
        self.assertIn("$256억", detail)      # V_dr = 177.9M * $143.73 (유효숫자 3자리)
        self.assertIn("1,084.5조원", detail)  # V_local

    def test_conversion_unknown_fallback(self):
        smsn = self.read("stocks/smsn/index.html")
        self.assertIn("데이터 미확인", smsn)
        self.assertIn("전사 발행량의 ADS 환산치로 확인되어", smsn)
        self.assertNotIn("전환한도:", smsn)  # 한도 미확인 -> 행 미표시
        # 전환 섹션에 소진율 행 없음 (수식 안내의 일반 정의는 존재 가능)
        self.assertNotIn("한도 소진율</span>", smsn)

    def test_formula_additions(self):
        detail = self.read("stocks/skhy/index.html")
        for needle in ("전일 대비(%p)", "SMA_n(d)", "기간 평균",
                       "현재 전환율(%) = N_dr_local / N_total * 100",
                       "현지 시장 금액 = (N_total - N_dr_local) * P_local"):
            self.assertIn(needle, detail, needle)

    # F2
    def test_intraday_labels(self):
        m = self.meta_v2()
        s = m["tickers"]["SKHY"]["snapshot"]
        s["p_local_intraday"] = True
        m["tickers"]["SKHY"]["collected_at_kst"] = "08/04 11:02"
        with tempfile.TemporaryDirectory() as tmp:
            bp.build_all(m, SITE, [], Path(tmp))
            detail = (Path(tmp) / "stocks/skhy/index.html").read_text(encoding="utf-8")
            self.assertIn("장중 지연 시세 (수집 11:02)", detail)
            self.assertIn("장중 지연 시세 기준 - 수집 08/04 11:02 KST", detail)
            self.assertIn("2026-07-31 NYSE 종가", detail)  # DR는 확정 종가 라벨 유지
            main = (Path(tmp) / "index.html").read_text(encoding="utf-8")
            self.assertIn("원주 장중", main)
            self.assertIn("장중 지연 시세 기준", main)

    def test_intraday_footnote_always_present(self):
        detail = self.read("stocks/skhy/index.html")
        self.assertIn("거래소 지연(최대 20분)과 갱신 주기(최대 60분)", detail)


class TestDeploymentPrep(unittest.TestCase):
    """D-3~D-6 배포 선행 작업 (2026-08-05 절차서 10절)."""

    SITE_FULL = {
        "site_name": "테스트 트래커",
        "base_url": "https://user.github.io/repo",
        "notices": {
            "noncommercial": "본 사이트는 비상업 목적의 시험 운영 페이지입니다.",
            "data_source": "시세 데이터 출처: Yahoo Finance (yfinance 경유).",
            "contact_email": "test@example.com",
        },
        "verification": {"google": "GTOKEN123", "naver": "NTOKEN456"},
        "analytics": {"head_html": '<script data-x="1">/*stub*/</script>'},
    }

    def build(self, site, meta=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name)
        bp.build_all(meta or fake_meta(), site, [], out)
        return out

    # D-5
    def test_footer_notices_present(self):
        out = self.build(self.SITE_FULL)
        for rel in ("index.html", "stocks/skhy/index.html"):
            h = (out / rel).read_text(encoding="utf-8")
            self.assertIn("비상업 목적의 시험 운영", h, rel)
            self.assertIn("Yahoo Finance (yfinance 경유)", h, rel)
            self.assertIn('href="mailto:test@example.com"', h, rel)
            self.assertIn("투자 조언이 아닙니다", h, rel)  # 기존 고지 유지

    def test_footer_notices_omitted_when_empty(self):
        out = self.build(SITE)  # notices 키 자체가 없음
        h = (out / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("footer-notice", h)
        self.assertIn("투자 조언이 아닙니다", h)

    def test_partial_notices(self):
        site = dict(SITE, notices={"noncommercial": "비상업 문구만",
                                   "data_source": "", "contact_email": ""})
        h = (self.build(site) / "index.html").read_text(encoding="utf-8")
        self.assertIn("비상업 문구만", h)
        self.assertEqual(h.count("footer-notice"), 1)
        self.assertNotIn("mailto:", h)

    # D-6
    def test_verification_and_analytics_injected(self):
        out = self.build(self.SITE_FULL)
        for rel in ("index.html", "stocks/skhy/index.html"):
            h = (out / rel).read_text(encoding="utf-8")
            self.assertIn('<meta name="google-site-verification" content="GTOKEN123">', h)
            self.assertIn('<meta name="naver-site-verification" content="NTOKEN456">', h)
            self.assertIn('<script data-x="1">/*stub*/</script>', h)
            # head 안에 들어갔는지 (stylesheet 링크보다 앞)
            self.assertLess(h.index("google-site-verification"), h.index("styles.css"))

    def test_verification_omitted_when_empty(self):
        site = dict(SITE, verification={"google": "", "naver": "  "},
                    analytics={"head_html": ""})
        h = (self.build(site) / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("site-verification", h)

    def test_verification_value_escaped(self):
        site = dict(SITE, verification={"google": 'a"><script>x</script>'})
        h = (self.build(site) / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('content="a"><script>', h)
        self.assertIn("&quot;", h)

    # D-3 / D-4
    def test_base_url_trailing_slash_equivalence(self):
        a = self.build(dict(SITE, base_url="https://user.github.io"))
        b = self.build(dict(SITE, base_url="https://user.github.io/"))
        for rel in ("index.html", "stocks/skhy/index.html", "sitemap.xml", "robots.txt"):
            self.assertEqual((a / rel).read_text(encoding="utf-8"),
                             (b / rel).read_text(encoding="utf-8"), rel)

    def test_subpath_deploy_urls_and_relative_assets(self):
        out = self.build(dict(SITE, base_url="https://user.github.io/repo"))
        main = (out / "index.html").read_text(encoding="utf-8")
        stock = (out / "stocks/skhy/index.html").read_text(encoding="utf-8")
        self.assertIn('<link rel="canonical" href="https://user.github.io/repo/">', main)
        self.assertIn('<link rel="canonical" href="https://user.github.io/repo/stocks/skhy/">',
                      stock)
        self.assertIn("<loc>https://user.github.io/repo/</loc>",
                      (out / "sitemap.xml").read_text(encoding="utf-8"))
        # 자산·내부 링크는 전부 상대경로여야 서브경로에서 깨지지 않는다
        # (2026-08-05 캐시버스팅 도입 후 ?v=<hash>가 붙는다)
        self.assertIn('href="styles.css?v=', main)
        self.assertIn('href="../../styles.css?v=', stock)
        self.assertNotIn('href="/styles.css', main + stock)
        self.assertIn('class="card" href="stocks/skhy/"', main)
        self.assertIn('data-root="../../"', stock)


class TestLandingIntro(unittest.TestCase):
    """작업 1 (2026-08-06): 메인 랜딩 소개 블록."""

    def build(self, guides=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name)
        bp.build_all(fake_meta(), SITE, guides or [], out)
        return out

    def test_intro_prerendered_as_text(self):
        """크롤러가 읽어야 하므로 JS 없이 텍스트로 존재해야 한다."""
        main = (self.build() / "index.html").read_text(encoding="utf-8")
        self.assertIn('class="intro"', main)
        self.assertIn(bp.INTRO_HEADLINE, main)
        self.assertIn("12개 종목", main)
        self.assertIn("그대로 공개", main)          # 차별점 서술
        self.assertIn("양수(빨강)", main)            # 읽는 법
        self.assertIn("음수(파랑)", main)

    def test_intro_precedes_card_grid(self):
        main = (self.build() / "index.html").read_text(encoding="utf-8")
        self.assertLess(main.index('class="intro"'), main.index('class="card-grid"'))

    def test_intro_headline_is_h1(self):
        main = (self.build() / "index.html").read_text(encoding="utf-8")
        self.assertIn('<h1 class="intro-headline">', main)
        self.assertEqual(main.count("<h1"), 1)  # 메인의 h1은 하나만

    def test_guide_link_present_only_when_guide_exists(self):
        guide = {"slug": "adr-premium", "title": "T", "description": "D",
                 "html": "<p>x</p>", "faqs": []}
        with_guide = (self.build([guide]) / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="guide/adr-premium/"', with_guide)
        self.assertIn(bp.INTRO_GUIDE_TEXT, with_guide)
        without = (self.build([]) / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("intro-link", without)

    def test_intro_only_on_main(self):
        out = self.build()
        stock = (out / "stocks/skhy/index.html").read_text(encoding="utf-8")
        self.assertNotIn('class="intro"', stock)

    def test_no_duplicate_disclaimer(self):
        """푸터의 '투자 조언 아님' 고지와 중복 서술을 넣지 않는다."""
        main = (self.build() / "index.html").read_text(encoding="utf-8")
        self.assertEqual(main.count("투자 조언이 아닙니다"), 1)
        intro = re.search(r'<section class="intro">.*?</section>', main, re.S).group(0)
        self.assertNotIn("투자 조언", intro)


class TestBareUrlDisplay(unittest.TestCase):
    """작업 2 (2026-08-06): 링크 표시 글자 개선."""

    def test_markdown_link_syntax(self):
        h, _ = bp.md_to_html("출처: [KB증권 해설](https://kbthink.com/a.html) 참고")
        self.assertIn('<a href="https://kbthink.com/a.html" rel="noopener">'
                      "KB증권 해설</a>", h)

    def test_bare_url_shows_domain_only(self):
        url = "https://www.sec.gov/Archives/edgar/data/0002120882/x.htm"
        h, _ = bp.md_to_html(f"출처 {url} 끝")
        self.assertIn(f'<a href="{url}" rel="noopener">sec.gov</a>', h)
        self.assertNotIn(f">{url}<", h)  # 표시 글자로 전체 URL 노출 금지

    def test_display_domain_helper(self):
        self.assertEqual(bp._display_domain("https://www.nasdaq.com/a/b"), "nasdaq.com")
        self.assertEqual(bp._display_domain("https://github.com/x/y"), "github.com")
        self.assertEqual(bp._display_domain("http://kr.investing.com/a"),
                         "kr.investing.com")

    def test_href_preserved_for_bare_url(self):
        url = "https://finance.yahoo.com/markets/stocks/articles/a-b-c-005605511.html"
        h, _ = bp.md_to_html(f"({url})")
        self.assertIn(f'href="{url}"', h)

    def test_markdown_link_not_double_processed(self):
        h, _ = bp.md_to_html("[표시](https://example.com/a)")
        self.assertEqual(h.count("<a "), 1)
        self.assertIn(">표시</a>", h)


class TestCacheBusting(unittest.TestCase):
    """작업 1 (2026-08-05): 정적 자산 캐시버스팅."""

    def test_asset_version_is_content_hash(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.css"
            p.write_bytes(b"body{}")
            v1 = bp.asset_version(p)
            self.assertEqual(v1, hashlib.sha256(b"body{}").hexdigest()[:8])
            self.assertEqual(len(v1), 8)
            # 내용 미변경 -> 값 동일 (캐시 유지)
            self.assertEqual(bp.asset_version(p), v1)
            # 내용 변경 -> 값 변경 (캐시 무효화)
            p.write_bytes(b"body{color:red}")
            self.assertNotEqual(bp.asset_version(p), v1)

    def test_asset_version_missing_file(self):
        self.assertEqual(bp.asset_version(Path("/no/such/file.css")), "0")

    def test_pages_reference_versioned_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            bp.build_all(fake_meta(), SITE, [], out)
            css_v = bp.asset_version(bp.WEB_DIR / "styles.css")
            js_v = bp.asset_version(bp.WEB_DIR / "app.js")
            main = (out / "index.html").read_text(encoding="utf-8")
            stock = (out / "stocks/skhy/index.html").read_text(encoding="utf-8")
            self.assertIn(f'href="styles.css?v={css_v}"', main)
            self.assertIn(f'src="app.js?v={js_v}"', main)
            self.assertIn(f'href="../../styles.css?v={css_v}"', stock)
            self.assertIn(f'src="../../app.js?v={js_v}"', stock)
            # 버전 없는 참조가 남아 있으면 캐시 문제가 재발한다
            self.assertNotIn('href="styles.css"', main)
            self.assertNotIn('src="app.js"', main)


class TestDeployConfig(unittest.TestCase):
    """배포 설정 구조 (2026-08-05 사용자 확정: B안 - GitHub Pages 무료 도메인).

    base_url = https://jasony93.github.io (user 사이트, 루트 배포).
    커스텀 도메인으로 옮길 때도 site.json 두 값만 교체하면 되는 구조를 유지한다.
    """

    def test_site_json_uses_confirmed_domain(self):
        with open(bp.SITE_CONFIG_PATH, encoding="utf-8") as f:
            site = json.load(f)
        base = site["base_url"]
        # 소유하지 않은 도메인·플레이스홀더를 canonical/sitemap에 넣지 않는다
        self.assertNotIn("example.com", base)
        self.assertNotIn("kremium", base)
        self.assertEqual(base, "https://jasony93.github.io")
        self.assertTrue(site["site_name"])

    def test_no_cname_file(self):
        """CNAME은 커스텀 도메인을 붙일 때만 필요 (Actions 배포에선 필수도 아님)."""
        self.assertFalse((bp.WEB_DIR / "CNAME").exists())

    def test_base_url_change_propagates_everywhere(self):
        """설정값 하나만 바꾸면 전 산출물에 반영되는 구조 유지."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            site = dict(SITE, base_url="https://future-domain.example",
                        site_name="새브랜드")
            bp.build_all(fake_meta(), site, [], out)
            main = (out / "index.html").read_text(encoding="utf-8")
            stock = (out / "stocks/skhy/index.html").read_text(encoding="utf-8")
            sm = (out / "sitemap.xml").read_text(encoding="utf-8")
            rb = (out / "robots.txt").read_text(encoding="utf-8")
            for blob in (main, stock, sm, rb):
                self.assertIn("future-domain.example", blob)
                self.assertNotIn("test.example.com", blob)
            self.assertIn("- 새브랜드</title>", stock)

    def test_build_preserves_unmanaged_files(self):
        """빌드는 파일을 쓰기만 하고 삭제하지 않는다(CNAME 등 수동 파일 보존)."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "CNAME").write_text("example.test\n", encoding="utf-8")
            written = bp.build_all(fake_meta(), SITE, [], out)
            self.assertTrue((out / "CNAME").exists())
            self.assertEqual((out / "CNAME").read_text(encoding="utf-8").strip(),
                             "example.test")
            self.assertNotIn("CNAME", written)


class TestConversionStructure(unittest.TestCase):
    """작업 3 (2026-08-05): 전환 구조 시각화·배지."""

    @staticmethod
    def meta_with_types():
        m = TestV2Rendering.meta_v2()
        m["tickers"]["SKHY"]["conversion"]["type"] = "dr_to_local_free"
        m["tickers"]["SMSN"]["conversion"]["type"] = None  # 미조사
        return m

    def build(self, meta):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name)
        bp.build_all(meta, SITE, [], out)
        return out

    def test_badge_by_type(self):
        self.assertIn("전환 자유",
                      bp.conversion_badge_html({"conversion": {"type": "both_free"}}))
        self.assertIn("전환 제한", bp.conversion_badge_html(
            {"conversion": {"type": "dr_to_local_free"}}))
        self.assertEqual(bp.conversion_badge_html({"conversion": {"type": None}}), "")
        self.assertEqual(bp.conversion_badge_html({}), "")

    def test_diagram_both_free(self):
        svg = bp.conversion_diagram_svg("both_free", "원주", "ADR")
        self.assertIn('role="img"', svg)
        self.assertIn("양방향 전환이 모두 자유", svg)
        self.assertIn("원주 -&gt; DR 자유", svg)
        self.assertNotIn("stroke-dasharray", svg)  # 막힌 방향 없음
        self.assertNotIn("stroke-linecap", svg)    # X 표시 없음

    def test_diagram_one_way(self):
        svg = bp.conversion_diagram_svg("dr_to_local_free", "원주", "ADR")
        self.assertIn("원주 -&gt; DR 제한", svg)
        self.assertIn("DR -&gt; 원주 자유", svg)
        self.assertIn("stroke-dasharray", svg)     # 막힌 방향 점선
        self.assertIn("stroke-linecap", svg)       # X 표시
        self.assertIn("var(--conv-blocked)", svg)
        self.assertIn("var(--conv-open)", svg)
        self.assertIn("제한됩니다", svg)            # aria-label

    def test_no_external_image_dependency(self):
        svg = bp.conversion_diagram_svg("dr_to_local_free", "원주", "ADR")
        self.assertNotIn("<img", svg)
        self.assertNotIn("http", svg.replace("http://www.w3.org", ""))

    def test_detail_renders_structure_and_badge(self):
        out = self.build(self.meta_with_types())
        skhy = (out / "stocks/skhy/index.html").read_text(encoding="utf-8")
        self.assertIn('class="conv-structure"', skhy)
        self.assertIn('<svg class="conv-diagram"', skhy)
        self.assertIn("conv-badge-limited", skhy)
        # 텍스트 설명 유지(접근성·SEO) + 하단 중복 각주 제거
        self.assertIn("전량 소진으로 신규 절차 승인 전 불가", skhy)
        self.assertEqual(skhy.count("전량 소진으로 신규 절차 승인 전 불가"), 1)

    def test_main_cards_have_badges(self):
        out = self.build(self.meta_with_types())
        main = (out / "index.html").read_text(encoding="utf-8")
        self.assertIn("conv-badge-limited", main)

    def test_unknown_type_renders_nothing(self):
        out = self.build(self.meta_with_types())
        smsn = (out / "stocks/smsn/index.html").read_text(encoding="utf-8")
        self.assertNotIn("conv-badge", smsn)
        self.assertNotIn("conv-diagram", smsn)


class TestAbbreviations(unittest.TestCase):
    def test_krw(self):
        self.assertEqual(bp.abbrev_krw(293.5e12), "293.5조원")
        self.assertEqual(bp.abbrev_krw(3.7e12), "3.7조원")
        self.assertEqual(bp.abbrev_krw(4.58e11), "4,580억원")
        self.assertEqual(bp.abbrev_krw(50000), "50,000원")

    def test_usd(self):
        self.assertEqual(bp.abbrev_usd(212e9), "$2,120억")
        self.assertEqual(bp.abbrev_usd(2.67e9), "$26.7억")
        self.assertEqual(bp.abbrev_usd(5e6), "$500만")

    def test_twd(self):
        self.assertEqual(bp.abbrev_twd(30.5e12), "NT$30.5조")
        self.assertEqual(bp.abbrev_twd(2.5e11), "NT$2,500억")

    def test_pp(self):
        self.assertEqual(bp.fmt_pp(1.25), "+1.25%p")
        self.assertEqual(bp.fmt_pp(-0.3), "-0.30%p")

    def test_hkd(self):
        """2026-08-05 BABA 편입: HK$ 표기·축약."""
        self.assertEqual(bp.fmt_local(128.5, "HKD"), "HK$128.50")
        self.assertEqual(bp.abbrev_hkd(2.45e12), "HK$2.5조")
        self.assertEqual(bp.abbrev_hkd(3.2e11), "HK$3,200억")
        self.assertEqual(bp.abbrev_local(2.45e12, "HKD"), "HK$2.5조")


class TestSparklineSvg(unittest.TestCase):
    def test_svg_structure(self):
        svg = bp.sparkline_svg([["d1", 1.0], ["d2", -1.0], ["d3", 2.0]])
        self.assertIn("<svg", svg)
        self.assertIn("stroke-dasharray", svg)  # 0% 기준선
        self.assertIn("<path", svg)

    def test_too_few_points(self):
        svg = bp.sparkline_svg([["d1", 1.0]])
        self.assertNotIn("<path", svg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
