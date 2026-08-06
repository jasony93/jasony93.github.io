"""정적 페이지 프리렌더 생성기 (SEO D1~D4).

fetch_data.py가 생성한 meta.json을 소비해 완전한 HTML 페이지를 생성한다.
계산·수집 로직은 건드리지 않는다 (검증 완료된 파이프라인의 소비자).

생성물 (src/web/ 하위):
  index.html                메인 - 카드 그리드 프리렌더 (스파크라인 SVG 포함)
  stocks/<ticker>/index.html  종목 상세 11개 (소문자 DR 티커 경로)
  guide/<slug>/index.html   가이드 (docs/marketing/guides/*.md 원고가 있을 때)
  sitemap.xml, robots.txt

실행:  python src/build_pages.py   (fetch_data.py 실행 후)

SEO 구성 (마케팅 문서 2.2~2.4절):
  - 초기 HTML에 핵심 콘텐츠 텍스트 포함 (JS 불필요)
  - 페이지별 title/meta description/OG/canonical (site.json의 사이트명·기본 URL)
  - JSON-LD: 메인 WebSite+Organization, 종목 BreadcrumbList, 가이드 FAQPage(Q&A 존재 시)
  - 기존 해시 URL(#/SKHY)은 인라인 스크립트로 새 경로 리다이렉트
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parent
SITE_CONFIG_PATH = ROOT / "config" / "site.json"
DATA_DIR = ROOT / "web" / "data"
WEB_DIR = ROOT / "web"
GUIDES_DIR = ROOT.parent / "docs" / "marketing" / "guides"

DISCLAIMER = "본 사이트의 모든 정보는 참고용이며 <strong>투자 조언이 아닙니다</strong>. 데이터는 지연·종가 기반이며 정확성을 보장하지 않습니다."
FORMULA_TEXT = "프리미엄(%) = (DR 가격 * 환율 / (원주 가격 * 전환비율) - 1) * 100"

# ---- 페이지별 title / meta description (마케팅 문서 2.3절 템플릿) ----
# 제목·설명은 빌드 시점 수치를 넣지 않는다 (검색 결과 스냅샷과 불일치 방지).
# 메인 랜딩 소개 블록 (2026-08-06 사용자 지시). 문구 수정은 여기만 고치면 된다.
# 원칙: 간결하게(장황 금지), 계산 근거 공개라는 차별점 명시, 푸터의 "투자 조언
# 아님" 고지와 중복하지 않는다.
INTRO_HEADLINE = "해외에 상장된 우리 주식, 지금 얼마나 비싼가?"
INTRO_BODY = (
    "미국·런던·홍콩에 상장된 예탁증서(ADR·GDR)와 현지 시장 원주의 가격 차이를 "
    "매일 계산해 보여줍니다. SK하이닉스·삼성전자·TSMC를 포함한 12개 종목이 대상이며, "
    "환율과 전환비율(예탁증서 1주가 대표하는 원주 수)을 반영해 계산합니다. "
    "쓰인 가격·환율·전환비율과 각각의 기준 시점을 그대로 공개하니 직접 검산할 수 있습니다."
)
INTRO_READING = ("보는 법: 양수(빨강)는 해외가 더 비싼 상태(프리미엄), "
                 "음수(파랑)는 더 싼 상태(디스카운트)입니다.")
INTRO_GUIDE_SLUG = "adr-premium"      # 링크 대상 가이드 슬러그
INTRO_GUIDE_TEXT = "ADR 프리미엄이란? 계산법과 해석"

MAIN_TITLE = Template("한국·대만 ADR 프리미엄 추적 - $site_name")
MAIN_DESC = ("SK하이닉스 SKHY, 삼성전자 GDR, TSMC 등 11종목의 ADR 프리미엄(괴리율)을 "
             "계산 근거와 함께 매일 차트로 보여드립니다.")
STOCK_SEO_OVERRIDES = {
    "SKHY": ("SK하이닉스 ADR 프리미엄(SKHY 괴리율) 차트 - $site_name",
             "SKHY와 원주(000660) 간 프리미엄을 가격·환율·전환비율(10:1) 근거와 함께 계산. "
             "원주 환산가와 일별 추이 차트 제공."),
    "SMSN": ("삼성전자 GDR(SMSN) 프리미엄 차트 - 런던 시세 환산 - $site_name",
             "런던 상장 삼성전자 GDR(1주=보통주 25주)의 원주 대비 프리미엄을 매일 계산. "
             "계산 근거와 히스토리 차트 제공."),
    "TSM": ("TSMC ADR 프리미엄(TSM vs 2330) 차트 - $site_name",
            "TSM과 대만 원주 2330 간 프리미엄(ADR 1주=원주 5주)을 환율 근거와 함께 계산. "
            "장기 히스토리 차트 제공."),
}
STOCK_TITLE_DEFAULT = Template("$name ADR 프리미엄($ticker 괴리율) 차트 - $site_name")
STOCK_DESC_DEFAULT = Template("$ticker와 원주($local_code) 간 프리미엄을 가격·환율·"
                              "전환비율($ratio_short) 근거와 함께 계산. 계산 근거와 일별 차트 제공.")


# ---------- 숫자 포맷 (app.js와 동일 규칙) ----------

def fmt_premium(v: float) -> str:
    return f"{v:+.2f}%"


def premium_class(v: float) -> str:
    return "pos" if v >= 0 else "neg"


def fmt_usd(v: float) -> str:
    return f"${v:,.2f}"


def fmt_local(v: float, currency: str) -> str:
    if currency == "KRW":
        return f"{v:,.0f}원"
    if currency == "HKD":
        return f"HK${v:,.2f}"
    return f"{v:,.1f} TWD"


def fmt_fx(v: float) -> str:
    return f"{v:,.2f}"


def short_date(iso: str) -> str:
    return iso[5:].replace("-", "/") if iso else "-"


def fmt_pp(v: float) -> str:
    """F4: 전일 대비 변동 - 단위 %p, 부호 항상 병기."""
    return f"{v:+.2f}%p"


def abbrev_krw(v: float) -> str:
    if abs(v) >= 1e12:
        return f"{v / 1e12:,.1f}조원"
    if abs(v) >= 1e8:
        return f"{v / 1e8:,.0f}억원"
    return f"{v:,.0f}원"


def abbrev_twd(v: float) -> str:
    if abs(v) >= 1e12:
        return f"NT${v / 1e12:,.1f}조"
    if abs(v) >= 1e8:
        return f"NT${v / 1e8:,.0f}억"
    return f"NT${v:,.0f}"


def abbrev_usd(v: float) -> str:
    """억 달러 단위 축약 (1e8 USD = 1억 달러)."""
    if abs(v) >= 1e10:
        return f"${v / 1e8:,.0f}억"
    if abs(v) >= 1e8:
        return f"${v / 1e8:,.1f}억"
    if abs(v) >= 1e4:
        return f"${v / 1e4:,.0f}만"
    return f"${v:,.0f}"


def abbrev_hkd(v: float) -> str:
    if abs(v) >= 1e12:
        return f"HK${v / 1e12:,.1f}조"
    if abs(v) >= 1e8:
        return f"HK${v / 1e8:,.0f}억"
    return f"HK${v:,.0f}"


def abbrev_local(v: float, currency: str) -> str:
    if currency == "KRW":
        return abbrev_krw(v)
    if currency == "HKD":
        return abbrev_hkd(v)
    return abbrev_twd(v)


def delta_html(s: dict, compact: bool = False) -> str:
    """F4: 프리미엄 옆 (+x.xx%p, M/D 대비). 직전 포인트 없으면 빈 문자열."""
    d = s.get("delta_pp")
    if d is None:
        return ""
    cls = premium_class(d)
    prev = short_date(s.get("prev_date"))
    if compact:
        return (f'<span class="card-delta {cls}" title="{prev} 대비">'
                f'({fmt_pp(d)})</span>')
    return f'<span class="detail-delta {cls}">({fmt_pp(d)}, {prev} 대비)</span>'


def _collect_hm(t: dict) -> str:
    """collected_at_kst 'MM/DD HH:MM'에서 HH:MM만."""
    c = t.get("collected_at_kst") or ""
    return c.split(" ")[-1] if " " in c else c


def value_date_label(date: str, intraday: bool, t: dict, suffix: str = "종가") -> str:
    """F2 지연 라벨 표준: 장중 수집 값 vs 확정 종가."""
    if intraday:
        return f"장중 지연 시세 (수집 {_collect_hm(t)})"
    return f"{date} {suffix}"


def snapshot_is_live(s: dict) -> bool:
    return bool(s.get("p_dr_intraday") or s.get("p_local_intraday"))


def live_badge_html(t: dict) -> str:
    return (f'<div class="live-badge">장중 지연 시세 기준 - '
            f'수집 {html.escape(t.get("collected_at_kst") or "")} KST</div>')


# ---------- 스파크라인 SVG (app.js sparklineSVG와 동일한 계산) ----------

def sparkline_svg(spark: list, width: int = 260, height: int = 56) -> str:
    if not spark or len(spark) < 2:
        return f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none"></svg>'
    values = [p[1] for p in spark]
    vmin = min(0.0, min(values))
    vmax = max(0.0, max(values))
    if vmax - vmin < 1e-9:
        vmax += 1
        vmin -= 1
    pad = (vmax - vmin) * 0.08
    vmin -= pad
    vmax += pad

    def y(v):
        return height - ((v - vmin) / (vmax - vmin)) * height

    def x(i):
        return (i / (len(values) - 1)) * width

    zero_y = y(0)
    d = " ".join(f"{'M' if i == 0 else 'L'}{x(i):.2f} {y(v):.2f}"
                 for i, v in enumerate(values))
    return (
        f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" '
        f'role="img" aria-label="최근 30일 프리미엄 추이">'
        f'<line x1="0" x2="{width}" y1="{zero_y:.2f}" y2="{zero_y:.2f}" '
        f'stroke="var(--zero-line)" stroke-width="1" stroke-dasharray="3 3" '
        f'vector-effect="non-scaling-stroke"/>'
        f'<path d="{d}" fill="none" stroke="var(--accent)" stroke-width="1.8" '
        f'vector-effect="non-scaling-stroke"/></svg>'
    )


# ---------- 공통 페이지 골격 ----------

PAGE_TMPL = Template("""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<meta name="description" content="$description">
<link rel="canonical" href="$canonical">
<meta property="og:title" content="$title">
<meta property="og:description" content="$description">
<meta property="og:type" content="$og_type">
<meta property="og:url" content="$canonical">
<meta property="og:site_name" content="$site_name">
$verification$analytics<link rel="stylesheet" href="${root}styles.css?v=$css_v">
<script>
// 첫 페인트 전 테마 적용 (깜빡임 방지)
(function () {
  var saved = null;
  try { saved = localStorage.getItem("theme"); } catch (e) {}
  var theme = saved || (window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.documentElement.setAttribute("data-theme", theme);
})();
// 구 해시 URL(#/SKHY) -> 새 경로 리다이렉트
(function () {
  var m = location.hash.match(/^#\\/([A-Za-z0-9]+)/);
  if (!m) return;
  var t = m[1].toLowerCase();
  var known = $known_tickers;
  if (known.indexOf(t) >= 0) { location.replace("${root}stocks/" + t + "/"); }
  else if (m[1] === "/" || m[1] === "") { location.replace("$home_href"); }
})();
</script>
$jsonld
</head>
<body data-page="$page_type" data-root="$root"$body_extra>
<header class="site-header">
  <a class="site-title" href="$home_href">$site_name</a>
  <button id="theme-toggle" class="theme-toggle" type="button"
          aria-label="라이트/다크 테마 전환">다크 모드</button>
</header>

<main id="view" class="view">
$content
</main>

<footer class="site-footer">
  <p>$disclaimer</p>
$notices  <p class="footer-sub">$formula</p>
</footer>

$page_data<script src="${root}app.js?v=$js_v"></script>
</body>
</html>
""")


def asset_version(path: Path) -> str:
    """정적 자산의 캐시버스팅 값 - 파일 내용 SHA-256 앞 8자리.

    내용이 바뀔 때만 값이 변하므로 (a) 배포 직후 사용자가 구 파일을 계속 쓰는
    문제를 없애고 (b) 변경이 없으면 브라우저 캐시가 그대로 유효하다.
    타임스탬프 방식은 매 빌드마다 값이 바뀌어 캐시 효율을 죽이므로 쓰지 않는다.
    파일이 없으면 "0" (빌드는 계속 진행).
    """
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:8]
    except OSError:
        return "0"


def jsonld_tag(obj: dict) -> str:
    return ('<script type="application/ld+json">'
            + json.dumps(obj, ensure_ascii=False) + "</script>")


def verification_tags(site: dict) -> str:
    """D-6: 검색엔진 소유확인 meta 태그. 값이 비면 태그를 넣지 않는다."""
    v = site.get("verification") or {}
    out = []
    for key, name in (("google", "google-site-verification"),
                      ("naver", "naver-site-verification")):
        token = (v.get(key) or "").strip()
        if token:
            out.append(f'<meta name="{name}" content="{html.escape(token, quote=True)}">')
    return ("\n".join(out) + "\n") if out else ""


def analytics_tag(site: dict) -> str:
    """D-6: 분석 스크립트. site.json의 HTML 원문을 그대로 head에 삽입."""
    snippet = ((site.get("analytics") or {}).get("head_html") or "").strip()
    return snippet + "\n" if snippet else ""


def notice_lines(site: dict) -> str:
    """D-5: 푸터 고지(비상업 시험 운영·데이터 출처·연락처). 빈 값은 줄 자체를 생략."""
    n = site.get("notices") or {}
    out = []
    for key, cls in (("noncommercial", "footer-notice"),
                     ("data_source", "footer-notice")):
        text = (n.get(key) or "").strip()
        if text:
            out.append(f'  <p class="{cls}">{html.escape(text)}</p>')
    email = (n.get("contact_email") or "").strip()
    if email:
        esc = html.escape(email)
        out.append(f'  <p class="footer-notice">문의: '
                   f'<a href="mailto:{esc}">{esc}</a></p>')
    return ("\n".join(out) + "\n") if out else ""


def render_page(*, site: dict, title: str, description: str, path: str, root: str,
                page_type: str, content: str, jsonld: dict | None,
                known_tickers: list[str], og_type: str = "website",
                body_extra: str = "", page_data: str = "",
                assets: dict | None = None) -> str:
    base = site["base_url"].rstrip("/")
    assets = assets or {}
    return PAGE_TMPL.substitute(
        css_v=assets.get("css", "0"),
        js_v=assets.get("js", "0"),
        title=html.escape(title, quote=True),
        description=html.escape(description, quote=True),
        canonical=base + path,
        og_type=og_type,
        site_name=html.escape(site["site_name"], quote=True),
        root=root,
        home_href=root if root else "./",
        known_tickers=json.dumps(known_tickers),
        jsonld=jsonld_tag(jsonld) if jsonld else "",
        verification=verification_tags(site),
        analytics=analytics_tag(site),
        notices=notice_lines(site),
        page_type=page_type,
        body_extra=body_extra,
        content=content,
        disclaimer=DISCLAIMER,
        formula=FORMULA_TEXT,
        page_data=page_data,
    )


# ---------- 메인 페이지 ----------

def build_card_html(t: dict, root: str) -> str:
    tid = t["id"]
    href = f"{root}stocks/{tid.lower()}/"
    name = html.escape(t.get("name", tid))
    parts = [f'<a class="card" href="{href}">', '<div class="card-head">',
             f'<span class="card-name">{name}</span>']
    if t.get("dr_ticker"):
        parts.append(f'<span class="card-ticker">{t["dr_ticker"]} · '
                     f'{html.escape(t.get("dr_exchange", ""))}</span>')
        if t.get("dr_type") == "GDR":
            tip = ("이 종목은 미국 ADR가 아닌 런던증권거래소(IOB) 상장 글로벌 예탁증서(GDR)입니다. "
                   "USD로 거래되며 프리미엄 계산 방식은 ADR와 동일합니다.")
            parts.append(f'<span class="badge badge-gdr" title="{tip}">GDR(런던)</span>')
        else:
            parts.append('<span class="badge">ADR</span>')
    parts.append(conversion_badge_html(t))  # 전환 자유도 배지
    parts.append("</div>")

    s = t.get("snapshot")
    if not s:
        parts.append('<div class="card-premium">-</div>')
        parts.append('<div class="stale-badge">데이터 없음 (갱신 실패)</div>')
        parts.append("</a>")
        return "".join(parts)

    parts.append(f'<div class="card-premium {premium_class(s["premium"])}">'
                 f'{fmt_premium(s["premium"])}{delta_html(s, compact=True)}</div>')
    parts.append(f'<div class="card-spark">{sparkline_svg(t.get("spark", []))}</div>')
    parts.append(f'<div class="card-prices">DR {fmt_usd(s["p_dr"])} · '
                 f'원주 {fmt_local(s["p_local"], t["local_currency"])}</div>')
    asof_dr = "장중" if s.get("p_dr_intraday") else f'{short_date(s["p_dr_date"])} 종가'
    asof_local = "장중" if s.get("p_local_intraday") else f'{short_date(s["p_local_date"])} 종가'
    parts.append(f'<div class="card-asof">DR {asof_dr} · 원주 {asof_local} · '
                 f'환율 {short_date(s["fx_date"])}</div>')
    if snapshot_is_live(s):
        parts.append(live_badge_html(t))
    if t.get("fetch_error"):
        parts.append(f'<div class="stale-badge">갱신 실패, '
                     f'{s.get("p_dr_date", "직전값")} 기준</div>')
    parts.append("</a>")
    return "".join(parts)


def build_intro_html(guides: list[dict], root: str = "") -> str:
    """메인 랜딩 소개 블록. 프리렌더 HTML에 텍스트로 포함된다(SEO)."""
    link = ""
    if any(g["slug"] == INTRO_GUIDE_SLUG for g in guides):
        link = (f' <a class="intro-link" href="{root}guide/{INTRO_GUIDE_SLUG}/">'
                f'{html.escape(INTRO_GUIDE_TEXT)} &gt;</a>')
    return ('<section class="intro">'
            f'<h1 class="intro-headline">{html.escape(INTRO_HEADLINE)}</h1>'
            f'<p class="intro-body">{html.escape(INTRO_BODY)}</p>'
            f'<p class="intro-reading">{html.escape(INTRO_READING)}{link}</p>'
            "</section>")


def build_main_content(meta: dict, guides: list[dict], root: str = "") -> str:
    gen = meta.get("generated_at", "").replace("T", " ").replace("Z", " UTC")
    out = [build_intro_html(guides, root),
           f'<p class="updated-at">데이터 생성: {gen}· 일별 종가 기반 (지연 데이터)</p>'
           if gen else "", '<div class="card-grid">']
    for tid in meta["order"]:
        t = meta["tickers"].get(tid)
        if t:
            out.append(build_card_html(t, root))
    out.append("</div>")
    if guides:
        out.append('<section class="guide-list"><h2>가이드</h2><ul>')
        for g in guides:
            out.append(f'<li><a href="{root}guide/{g["slug"]}/">'
                       f'{html.escape(g["title"])}</a></li>')
        out.append("</ul></section>")
    return "\n".join(x for x in out if x)


def build_main_page(meta: dict, site: dict, guides: list[dict],
                    known: list[str], assets: dict | None = None) -> str:
    base = site["base_url"].rstrip("/")
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "name": site["site_name"], "url": base + "/"},
        {"@type": "Organization", "name": site["site_name"], "url": base + "/"},
    ]}
    return render_page(
        site=site, title=MAIN_TITLE.substitute(site_name=site["site_name"]),
        description=MAIN_DESC, path="/", root="", page_type="main",
        content=build_main_content(meta, guides), jsonld=jsonld,
        known_tickers=known, assets=assets)


# ---------- 종목 상세 페이지 ----------

def ratio_short(t: dict) -> str:
    disp = t.get("ratio_display", str(t.get("ratio", "")))
    return disp.split(" ")[0] if disp else str(t.get("ratio", ""))


def stock_seo(t: dict, site: dict) -> tuple[str, str]:
    tid = t["id"]
    if tid in STOCK_SEO_OVERRIDES:
        title_tmpl, desc = STOCK_SEO_OVERRIDES[tid]
        return Template(title_tmpl).substitute(site_name=site["site_name"]), desc
    title = STOCK_TITLE_DEFAULT.substitute(
        name=t.get("name", tid), ticker=t.get("dr_ticker", tid),
        site_name=site["site_name"])
    desc = STOCK_DESC_DEFAULT.substitute(
        ticker=t.get("dr_ticker", tid), local_code=t.get("local_code", "-"),
        ratio_short=ratio_short(t))
    return title, desc


def source_item_html(label: str, value: str, date: str) -> str:
    return (f'<div class="source-item"><div class="source-label">{label}</div>'
            f'<div class="source-value">{value}</div>'
            f'<div class="source-date">{date}</div></div>')


# F7 v2 (2026-08-05): 전환 구조 시각화. 유형별 배지·다이어그램 정의.
#   both_free        - 원주 <-> DR 양방향 자유 (BABA)
#   dr_to_local_free - DR -> 원주만 자유, 원주 -> DR은 제한/승인제 (그 외 확인 종목)
#   (없음)           - 미조사 (SMSN) -> 배지·다이어그램 미표시
CONV_BADGE = {
    "both_free": ("전환 자유", "conv-badge-free",
                  "원주와 DR 사이 양방향 전환이 자유로워 괴리가 작게 유지됩니다"),
    "dr_to_local_free": ("전환 제한", "conv-badge-limited",
                         "DR을 원주로 바꾸는 방향만 자유롭고, 원주를 DR로 만드는 "
                         "방향은 제한돼 괴리가 오래 유지될 수 있습니다"),
}


def conversion_badge_html(t: dict) -> str:
    """전환 자유도 배지 (메인 카드·상세 상단). 유형 미확인 종목은 빈 문자열."""
    ctype = (t.get("conversion") or {}).get("type")
    info = CONV_BADGE.get(ctype)
    if not info:
        return ""
    label, cls, tip = info
    return (f'<span class="badge conv-badge {cls}" title="{html.escape(tip, quote=True)}">'
            f'{label}</span>')


def conversion_diagram_svg(ctype: str, local_label: str, dr_label: str) -> str:
    """전환 구조 인라인 SVG (외부 이미지·아이콘 라이브러리 없음).

    위 화살표 = 원주 -> DR, 아래 화살표 = DR -> 원주.
    열린 방향은 실선 + 강조색, 막힌 방향은 점선 + 회색 + X 표시.
    """
    both = ctype == "both_free"
    up_stroke = "var(--conv-open)" if both else "var(--conv-blocked)"
    up_dash = "" if both else ' stroke-dasharray="5 4"'
    aria = ("원주와 DR 사이 양방향 전환이 모두 자유롭습니다" if both else
            "DR에서 원주로 가는 전환은 자유롭지만, 원주에서 DR로 가는 전환은 제한됩니다")
    # 막힌 방향 표시용 X (화살표 중앙)
    blocked_mark = "" if both else (
        '<g stroke="var(--conv-blocked)" stroke-width="2.5" stroke-linecap="round">'
        '<line x1="146" y1="26" x2="158" y2="38"/>'
        '<line x1="158" y1="26" x2="146" y2="38"/></g>')
    up_label = "자유" if both else "제한"
    return f"""<svg class="conv-diagram" viewBox="0 0 304 104" role="img" aria-label="{aria}">
<defs>
<marker id="ah-open" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="var(--conv-open)"/></marker>
<marker id="ah-up" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{up_stroke}"/></marker>
</defs>
<rect x="1" y="26" width="86" height="52" rx="9" fill="var(--badge-bg)" stroke="var(--border)"/>
<text x="44" y="57" text-anchor="middle" font-size="13" fill="var(--text)">{html.escape(local_label)}</text>
<rect x="217" y="26" width="86" height="52" rx="9" fill="var(--badge-bg)" stroke="var(--border)"/>
<text x="260" y="57" text-anchor="middle" font-size="13" fill="var(--text)">{html.escape(dr_label)}</text>
<line x1="92" y1="32" x2="212" y2="32" stroke="{up_stroke}" stroke-width="2.5"{up_dash} marker-end="url(#ah-up)"/>
<text x="152" y="20" text-anchor="middle" font-size="11" fill="{up_stroke}">원주 -&gt; DR {up_label}</text>
{blocked_mark}
<line x1="212" y1="72" x2="92" y2="72" stroke="var(--conv-open)" stroke-width="2.5" marker-end="url(#ah-open)"/>
<text x="152" y="95" text-anchor="middle" font-size="11" fill="var(--conv-open)">DR -&gt; 원주 자유</text>
</svg>"""


def build_conversion_html(t: dict, s: dict) -> str:
    """F7 전환 현황 섹션 (PRD 7절). 폴백 계층: 값 있음 -> 게이지+금액 / 없음 -> 미확인."""
    conv = t.get("conversion")
    if conv is None:
        return ""
    cur = t["local_currency"]
    out = ['<section class="conv-section"><h3>전환 현황</h3>']

    # 전환 구조 시각화 (2026-08-05): 다이어그램 + 유형 배지 + 텍스트 설명.
    # 텍스트는 접근성·SEO를 위해 유지하되 시각 요소를 먼저 배치한다.
    ctype = conv.get("type")
    if ctype in CONV_BADGE:
        label, cls, _ = CONV_BADGE[ctype]
        out.append('<div class="conv-structure">'
                   + conversion_diagram_svg(ctype, "원주",
                                            t.get("dr_type") or "DR")
                   + f'<div class="conv-structure-text">'
                   f'<span class="badge conv-badge {cls}">{label}</span>'
                   + (f'<p>{html.escape(conv["note"])}</p>' if conv.get("note") else "")
                   + "</div></div>")

    limit = conv.get("limit")
    if limit:
        out.append(f'<p class="conv-limit">전환한도: 원주 기준 {limit:,}주 '
                   f'(기준일 {conv.get("limit_as_of", "-")}, '
                   f'출처: {html.escape(conv.get("limit_src") or "-")})</p>')

    if conv.get("n_dr") is not None and conv.get("cv") is not None:
        cv = conv["cv"]
        limit_pct = conv.get("limit_pct")
        # 게이지 바: 0~100% 축에 현재 전환율. 한도 위치 눈금 병기.
        fill_w = max(cv, 0.5)
        gauge = [f'<div class="gauge" role="img" aria-label="현재 전환율 {cv:.2f}%">',
                 f'<div class="gauge-fill" style="width:{fill_w:.2f}%"></div>']
        if limit_pct:
            gauge.append(f'<div class="gauge-limit" style="left:{min(limit_pct, 100):.2f}%" '
                         f'title="전환한도 위치 ({limit_pct:.2f}%)"></div>')
        gauge.append('</div>')
        out.append("".join(gauge))
        rows = [f'<div class="conv-row"><span>현재 전환율 (DR 형태 주식 비중)</span>'
                f'<strong>{cv:.2f}%</strong></div>']
        if conv.get("lu") is not None:
            rows.append(f'<div class="conv-row"><span>한도 소진율</span>'
                        f'<strong>{conv["lu"]:.2f}%</strong></div>')
        out.append("".join(rows))
        # 시장별 주식 금액 (해당 시장 통화 우선 + 상대 통화 병기)
        v_dr = conv.get("v_dr_usd")
        v_local = conv.get("v_local")
        fx = s.get("fx")
        if v_dr is not None and v_local is not None and fx:
            dr_txt = f'{abbrev_usd(v_dr)} (약 {abbrev_local(v_dr * fx, cur)})'
            local_txt = f'{abbrev_local(v_local, cur)} (약 {abbrev_usd(v_local / fx)})'
            out.append('<div class="conv-markets">'
                       f'<div class="conv-market"><div class="source-label">DR 시장 금액</div>'
                       f'<div class="source-value">{dr_txt}</div></div>'
                       f'<div class="conv-market"><div class="source-label">현지 시장 금액</div>'
                       f'<div class="source-value">{local_txt}</div></div></div>')
        # 출처·기준일 라벨 (필수). 수동값은 설정 파일의 화면 문구를 그대로 표시
        # (예: SKHY "SEC 424B4 발행 시점(2026-07-10) 기준 - 이후 소각분 미반영 가능")
        if conv.get("n_dr_source") == "auto":
            src_line = f'자동 조회(Yahoo) 기준, {conv.get("n_dr_as_of", "-")}'
        else:
            src_line = html.escape(conv.get("n_dr_src") or
                                   f'수동 입력 기준일 {conv.get("n_dr_as_of", "-")}')
        out.append(f'<p class="source-date">DR 발행 잔량 {conv["n_dr"]:,}주 - {src_line}</p>')
    else:
        # 최종 폴백: 데이터 미확인 (오류처럼 보이지 않게 회색 처리)
        out.append('<div class="conv-unknown">'
                   '<div class="conv-row"><span>현재 전환율</span><strong>-</strong></div>'
                   '<div class="conv-row"><span>시장별 주식 금액</span><strong>-</strong></div>'
                   '<p class="source-date">데이터 미확인 - DR 발행 잔량의 신뢰할 수 있는 '
                   '출처를 확보하지 못했습니다. Yahoo의 DR 발행주식수 필드는 전사 발행량의 '
                   'ADS 환산치로 확인되어 사용하지 않습니다(검증 기각).</p></div>')

    out.append('<p class="chart-note">두 시장 금액의 합은 시가총액과 일치하지 않을 수 '
               '있습니다. DR 시장 금액은 프리미엄이 반영된 DR 가격 기준이기 때문입니다.</p>')
    # 전환 구조 각주 (설정 파일 conversion_note - 종목별 조사 확인분만.
    # 수치 미확인 상태에서도 구조 설명은 정보 가치가 있어 항상 표시)
    # 유형이 확인된 종목은 위 conv-structure에서 이미 note를 보여주므로 중복 생략.
    if conv.get("note") and ctype not in CONV_BADGE:
        out.append(f'<p class="chart-note conv-note">{html.escape(conv["note"])}</p>')
    out.append('</section>')
    return "".join(out)


def build_stock_content(t: dict, root: str) -> str:
    tid = t["id"]
    name = html.escape(t.get("name", tid))
    dr_type = t.get("dr_type", "DR")
    out = [f'<a class="back-link" href="{root}">&lt; 전체 종목으로</a>']
    out.append('<div class="detail-head">'
               f'<h1 class="detail-name">{name}</h1>'
               f'<span class="detail-ticker">{t.get("dr_ticker", tid)} '
               f'({html.escape(t.get("dr_exchange", "-"))}) vs {t.get("local_code", "-")} '
               f'({html.escape(t.get("local_exchange", "-"))})</span>'
               + (f'<span class="badge badge-gdr">GDR(런던)</span>' if dr_type == "GDR"
                  else '<span class="badge">ADR</span>')
               + conversion_badge_html(t)
               + "</div>")
    if dr_type == "GDR":
        out.append('<div class="gdr-notice">이 종목은 미국 ADR가 아닌 런던증권거래소(IOB) '
                   '상장 글로벌 예탁증서(GDR)입니다. USD로 거래되며 프리미엄 계산 방식은 '
                   'ADR와 동일합니다.</div>')

    s = t.get("snapshot")
    if not s:
        out.append(f'<p class="fatal-error">이 종목의 데이터가 없습니다. '
                   f'({html.escape(str(t.get("fetch_error") or "원인 미상"))})</p>')
        return "\n".join(out)

    out.append(f'<div class="detail-premium {premium_class(s["premium"])}">'
               f'{fmt_premium(s["premium"])}{delta_html(s)}</div>')
    sign = "" if s["premium"] >= 0 else "-"
    out.append(f'<div class="detail-implied">원주 환산가: DR {fmt_usd(s["p_dr"])} -&gt; '
               f'약 {fmt_local(round(s["implied_local"]), t["local_currency"])} '
               f'(프리미엄 {sign}{abs(s["premium"]):.2f}%)</div>')
    if snapshot_is_live(s):
        out.append(live_badge_html(t))
    if t.get("fetch_error"):
        out.append(f'<div class="stale-badge">데이터 갱신 실패 - 마지막 정상값'
                   f'({s["p_dr_date"]} 기준)을 표시 중입니다.</div>')

    # F2: 원천값 카드 라벨 (장중 지연 시세 vs 확정 종가)
    dr_label = value_date_label(s["p_dr_date"], s.get("p_dr_intraday", False), t,
                                f'{html.escape(t.get("dr_exchange", ""))} 종가')
    local_label = value_date_label(s["p_local_date"], s.get("p_local_intraday", False), t,
                                   f'{html.escape(t.get("local_exchange", ""))} 종가')
    fx_label_txt = value_date_label(s["fx_date"], s.get("fx_intraday", False), t, "기준")
    grid_items = (
        source_item_html(f'DR 가격 ({dr_type}, USD)', fmt_usd(s["p_dr"]), dr_label)
        + source_item_html(f'원주 가격 ({t["local_currency"]})',
                           fmt_local(s["p_local"], t["local_currency"]), local_label)
        + source_item_html(f'환율 ({t["fx_label"]})', fmt_fx(s["fx"]), fx_label_txt)
        + source_item_html('전환비율 r', html.escape(t.get("ratio_display", str(t.get("ratio")))),
                           '예탁은행 공시 기준 (설정 파일 관리)')
    )
    # F8: 원주 시가총액 카드 (종가 기준, 일 1회 갱신)
    shares = t.get("shares")
    if shares and shares.get("mcap_local"):
        mc = shares["mcap_local"]
        mc_usd = mc / s["fx"] if s.get("fx") else None
        mc_text = abbrev_local(mc, t["local_currency"])
        if mc_usd:
            mc_text += f" (약 {abbrev_usd(mc_usd)})"
        grid_items += source_item_html("원주 시가총액", mc_text,
                                       f'{shares.get("n_total_as_of", "-")} 종가 기준')
    out.append(f'<div class="source-grid">{grid_items}</div>')
    out.append('<p class="chart-note snap-footnote">장중 값은 거래소 지연(최대 20분)과 '
               '갱신 주기(최대 60분)로 실제 현재가와 다를 수 있습니다.</p>')

    # F7: 전환 현황 섹션
    out.append(build_conversion_html(t, s))

    tabs = "".join(
        f'<button type="button" class="period-tab{" active" if k == "1Y" else ""}">{k}</button>'
        for k in ("1M", "3M", "6M", "1Y", "MAX"))
    out.append(f'<div class="period-tabs">{tabs}</div>')
    out.append('<div class="chart-wrap" id="detail-chart">'
               '<p class="loading">차트 데이터를 불러오는 중...</p>'
               '<noscript><p class="chart-note">일별 차트 표시는 JavaScript가 필요합니다. '
               '위의 프리미엄·원천값은 최신 스냅샷 기준입니다.</p></noscript></div>')
    out.append('<p class="chart-note">일별 프리미엄: 같은 캘린더 날짜의 원주 종가와 DR 시장 '
               '종가로 계산합니다. 원주 장 마감 수 시간 후 DR 시장이 마감하므로, 이 수치는 '
               '"DR 시장이 원주 종가 대비 얼마나 앞서갔나"로 해석됩니다. 한쪽 시장 휴장일은 '
               '직전 거래일 종가를 이월해 계산하며 툴팁에 (이월)로 표시합니다.</p>')

    items = [
        f'DR 가격: 예탁증서({dr_type}) 1주의 시장 가격 (USD)',
        f'원주 가격: 현지 시장({html.escape(t.get("local_exchange", "-"))}) 원주 1주 가격 '
        f'({t["local_currency"]})',
        f'환율: {t["fx_label"]} (USD 1달러당 {t["local_currency"]})',
        f'전환비율 r: DR 1주가 대표하는 원주 수 = {html.escape(t.get("ratio_display", ""))}',
        '프리미엄 &gt; 0 이면 DR가 원주보다 비쌉니다(프리미엄), &lt; 0 이면 디스카운트입니다.',
    ]
    extra_formulas = (
        "전일 대비(%p) = 오늘 프리미엄 - 직전 데이터 포인트 프리미엄\n"
        "SMA_n(d) = 직전 n개 데이터 포인트(거래일 기준, d 포함) 프리미엄의 단순 평균\n"
        "기간 평균 = 현재 화면에 표시 중인 구간의 프리미엄 단순 평균\n"
        "주/월 단위 값 = 해당 주(ISO, 월-일)/캘린더 월의 마지막 거래일 값\n"
        "주/월 단위 거래량 = 해당 기간 실거래일 거래량 합계")
    conv_formulas = (
        "DR 물량의 원주 환산: N_dr_local = N_dr * r\n"
        "현재 전환율(%) = N_dr_local / N_total * 100  (DR 형태로 예탁된 비중)\n"
        "한도 소진율(%) = N_dr_local / L * 100  (L = 전환한도, 확인 종목만)\n"
        "DR 시장 금액 = N_dr * P_dr  (USD)\n"
        "현지 시장 금액 = (N_total - N_dr_local) * P_local")
    out.append('<div class="formula-box"><h3>계산 방식</h3>'
               f'<code>프리미엄(%) = (DR 가격(USD) * 환율 / (원주 가격 * 전환비율 r) - 1) * 100</code>'
               '<ul>' + "".join(f"<li>{i}</li>" for i in items) + "</ul>"
               f'<h3>보조 지표</h3><code>{extra_formulas}</code>'
               f'<h3>전환 현황 지표</h3><code>{conv_formulas}</code>'
               '<ul><li>N_dr: DR 발행 잔량(ADS 주 수), N_total: 원주 총발행주식수</li>'
               '<li>SMA는 일 단위 시계열 기준으로 정의하며 주/월 단위 화면에서는 표시하지 않습니다.</li></ul>'
               '<p>본 정보는 투자 조언이 아니며, 데이터 오류·지연이 있을 수 있습니다.</p></div>')
    return "\n".join(out)


def build_stock_page(t: dict, site: dict, known: list[str],
                     assets: dict | None = None) -> str:
    tid = t["id"]
    base = site["base_url"].rstrip("/")
    path = f"/stocks/{tid.lower()}/"
    title, desc = stock_seo(t, site)
    jsonld = {"@context": "https://schema.org", "@type": "BreadcrumbList",
              "itemListElement": [
                  {"@type": "ListItem", "position": 1, "name": "홈",
                   "item": base + "/"},
                  {"@type": "ListItem", "position": 2,
                   "name": t.get("name", tid), "item": base + path},
              ]}
    page_data = ('<script id="page-data" type="application/json">'
                 + json.dumps({"id": tid,
                               "local_currency": t.get("local_currency", "KRW"),
                               "fx_label": t.get("fx_label", "")},
                              ensure_ascii=False)
                 + "</script>\n")
    return render_page(
        site=site, title=title, description=desc, path=path, root="../../",
        page_type="stock", content=build_stock_content(t, "../../"),
        jsonld=jsonld, known_tickers=known, og_type="website",
        body_extra=f' data-ticker="{tid}"', page_data=page_data, assets=assets)


# ---------- 가이드 페이지 (최소 마크다운 변환) ----------

_INLINE_PATTERNS = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<strong>\1</strong>"),
    # 기울임: 표준 마크다운처럼 별표 안쪽이 공백이 아닐 때만 적용.
    # "a * b" 같은 곱셈 기호(공백 둘러싸임)는 변환하지 않는다.
    (re.compile(r"(?<!\*)\*(\S(?:[^*\n]*\S)?)\*(?!\*)"), r"<em>\1</em>"),
    (re.compile(r"`([^`]+)`"), r"<code>\1</code>"),
    (re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)"),
     r'<a href="\2" rel="noopener">\1</a>'),
    # 본문에 그대로 쓴 URL 자동 링크 (위 마크다운 링크가 만든 href 내부는 제외).
    # 표시 글자는 도메인만 쓴다 - 긴 주소가 본문에 노출되면 가독성이 나쁘다.
    # href는 항상 전체 URL을 유지한다.
    (re.compile(r'(?<!["=>])(https?://[^\s<>"\')]+)'), lambda m: _bare_link(m.group(1))),
]


def _display_domain(url: str) -> str:
    """맨 URL의 화면 표시용 도메인 (www. 제거). 파싱 실패 시 원본 반환."""
    try:
        netloc = urllib.parse.urlparse(url).netloc
    except ValueError:
        return url
    if not netloc:
        return url
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def _bare_link(url: str) -> str:
    return f'<a href="{url}" rel="noopener">{_display_domain(url)}</a>'


def _inline(text: str) -> str:
    out = html.escape(text, quote=False)
    for pat, repl in _INLINE_PATTERNS:
        out = pat.sub(repl, out)
    return out


def parse_front_matter(text: str) -> tuple[dict, str]:
    """머리말 파싱. 두 형식 지원:
    (1) '---' 블록 (README 안내 형식)
    (2) '<!-- key: value -->' HTML 주석 블록 (마케팅팀 원고 실수신 형식)
    meta_description 키는 description으로 정규화한다.
    """
    meta: dict = {}
    body = text
    lines = text.split("\n")
    if text.startswith("---"):
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                body = "\n".join(lines[i + 1:])
                break
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    elif text.lstrip().startswith("<!--"):
        for i, line in enumerate(lines):
            s = line.strip()
            if s.endswith("-->"):
                body = "\n".join(lines[i + 1:])
                break
            if ":" in s and not s.startswith("<!--"):
                k, v = s.split(":", 1)
                meta[k.strip()] = v.strip()
    if "meta_description" in meta and "description" not in meta:
        meta["description"] = meta["meta_description"]
    return meta, body


_QA_ANSWER_PREFIX = re.compile(r"^A\.\s*")


def _clean_question(text: str) -> str:
    q = text.strip().strip("*").strip()
    q = re.sub(r"^Q\.\s*", "", q)
    return q


def md_to_html(body: str) -> tuple[str, list[dict]]:
    """최소 마크다운 부분집합 -> HTML. 반환: (html, faq 목록[{question, answer}]).

    지원: ## ~ #### 제목('#' 단독 H1은 title 중복이므로 생략), 문단, -/1. 목록
    (여러 줄 항목은 직전 항목에 병합), ``` 코드 펜스(내부는 이스케이프만 - 마크다운
    변환 없음), '|' 표(구분행 |---| 지원), '---' 가로줄, > 인용, **굵게**,
    *기울임*(별표 안쪽 비공백일 때만 - 수식의 곱셈 기호 보호), 백틱 코드,
    마크다운 링크, 본문 URL 자동 링크.
    FAQ 추출 (FAQPage JSON-LD 재료) - 'FAQ' 또는 '자주 묻는'이 든 '##' 섹션에서:
      (1) '### 질문' 제목 + 본문 형식 (README 안내 형식)
      (2) '**Q. 질문**' + 'A. 답변' 문단 형식 (마케팅팀 원고 실수신 형식)
    FAQ 수집은 다음 제목·가로줄에서 종료된다 (말미 면책 문구 유입 방지).
    """
    out: list[str] = []
    faqs: list[dict] = []
    in_faq = False
    cur_q: str | None = None
    cur_a: list[str] = []
    list_tag: str | None = None
    list_items: list[str] = []
    para: list[str] = []
    table_rows: list[list[str]] = []
    table_has_sep = False
    in_fence = False
    fence_lines: list[str] = []

    def flush_para():
        nonlocal para
        if para:
            text = _inline(" ".join(para))
            out.append(f"<p>{text}</p>")
            if cur_q is not None:
                cur_a.append(" ".join(para))
            para = []

    def flush_list():
        nonlocal list_tag, list_items
        if list_tag:
            out.append(f"<{list_tag}>" + "".join(
                f"<li>{_inline(i)}</li>" for i in list_items) + f"</{list_tag}>")
            if cur_q is not None:
                cur_a.extend(list_items)
        list_tag, list_items = None, []

    def flush_table():
        nonlocal table_rows, table_has_sep
        if table_rows:
            rows_html = []
            for i, cells in enumerate(table_rows):
                tag = "th" if (i == 0 and table_has_sep) else "td"
                rows_html.append("<tr>" + "".join(
                    f"<{tag}>{_inline(c)}</{tag}>" for c in cells) + "</tr>")
            out.append('<div class="table-wrap"><table>'
                       + "".join(rows_html) + "</table></div>")
        table_rows, table_has_sep = [], False

    def flush_fence():
        nonlocal fence_lines
        # 펜스 내부는 HTML 이스케이프만 - 인라인 마크다운 변환 없음 (수식 보호)
        code = html.escape("\n".join(fence_lines), quote=False)
        out.append(f"<pre><code>{code}</code></pre>")
        fence_lines = []

    def flush_faq():
        nonlocal cur_q, cur_a
        if cur_q and cur_a:
            answer = _QA_ANSWER_PREFIX.sub("", " ".join(cur_a)).strip()
            if answer:
                faqs.append({"question": cur_q, "answer": answer})
        cur_q, cur_a = None, []

    for raw in body.split("\n"):
        line = raw.rstrip()
        stripped = line.strip()
        if in_fence:
            if stripped.startswith("```"):
                in_fence = False
                flush_fence()
            else:
                fence_lines.append(line)
            continue
        if stripped.startswith("```"):
            flush_para(); flush_list(); flush_table()
            in_fence = True
            continue
        m_h = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m_h:
            flush_para(); flush_list(); flush_table()
            level = len(m_h.group(1))
            text = m_h.group(2).strip()
            if level == 1:
                continue  # H1은 title에서 생성 - 본문 '#' 제목은 중복이라 생략
            if level == 2:
                flush_faq()
                in_faq = "FAQ" in text.upper() or "자주 묻는" in text
            elif level == 3 and in_faq:
                flush_faq()
                cur_q = _clean_question(text)
            out.append(f"<h{level}>{_inline(text)}</h{level}>")
            continue
        if not stripped:
            flush_para(); flush_list(); flush_table()
            continue
        if re.fullmatch(r"-{3,}", stripped):
            flush_para(); flush_list(); flush_table()
            flush_faq()  # 가로줄 = FAQ 섹션 종료 (말미 문구가 답변에 붙는 것 방지)
            in_faq = False
            out.append("<hr>")
            continue
        if stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2:
            flush_para(); flush_list()
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-+:?", c) for c in cells):
                table_has_sep = True
            else:
                table_rows.append(cells)
            continue
        if in_faq and stripped.startswith("**Q."):
            flush_para(); flush_list(); flush_table(); flush_faq()
            cur_q = _clean_question(stripped)
            out.append(f"<p>{_inline(stripped)}</p>")
            continue
        m_ul = re.match(r"^-\s+(.*)$", stripped)
        m_ol = re.match(r"^\d+\.\s+(.*)$", stripped)
        if m_ul or m_ol:
            flush_para(); flush_table()
            tag = "ul" if m_ul else "ol"
            if list_tag != tag:
                flush_list()
                list_tag = tag
            list_items.append((m_ul or m_ol).group(1))
            continue
        if stripped.startswith("> "):
            flush_para(); flush_list(); flush_table()
            out.append(f"<blockquote><p>{_inline(stripped[2:])}</p></blockquote>")
            continue
        if list_tag and not para:
            # 목록 항목의 연속 줄(줄바꿈된 긴 항목) - 직전 항목에 병합
            list_items[-1] += " " + stripped
            continue
        para.append(stripped)
    if in_fence:
        flush_fence()  # 닫히지 않은 펜스 방어
    flush_para(); flush_list(); flush_table(); flush_faq()
    return "\n".join(out), faqs


def load_guides(guides_dir: Path) -> list[dict]:
    guides = []
    if not guides_dir.is_dir():
        return guides
    for f in sorted(guides_dir.glob("*.md")):
        if f.name.upper() == "README.MD":
            continue
        slug = f.stem.lower()
        if not re.fullmatch(r"[a-z0-9-]+", slug):
            print(f"[WARN] 가이드 슬러그 부적합(영문 소문자·하이픈만): {f.name} - 건너뜀",
                  file=sys.stderr)
            continue
        fm, body = parse_front_matter(f.read_text(encoding="utf-8"))
        body_html, faqs = md_to_html(body)
        guides.append({
            "slug": slug,
            "title": fm.get("title", slug),
            "description": fm.get("description", ""),
            "html": body_html,
            "faqs": faqs,
        })
    return guides


def build_guide_page(g: dict, site: dict, known: list[str],
                     assets: dict | None = None) -> str:
    base = site["base_url"].rstrip("/")
    path = f"/guide/{g['slug']}/"
    jsonld = None
    if g["faqs"]:
        jsonld = {"@context": "https://schema.org", "@type": "FAQPage",
                  "mainEntity": [
                      {"@type": "Question", "name": f["question"],
                       "acceptedAnswer": {"@type": "Answer", "text": f["answer"]}}
                      for f in g["faqs"]]}
    content = ('<article class="guide-article">'
               f'<h1>{html.escape(g["title"])}</h1>\n{g["html"]}\n'
               '<p class="chart-note">본 글은 정보 제공 목적이며 투자 조언이 아닙니다.</p>'
               '</article>')
    return render_page(
        site=site, title=f'{g["title"]} - {site["site_name"]}',
        description=g["description"] or g["title"], path=path, root="../../",
        page_type="guide", content=content, jsonld=jsonld,
        known_tickers=known, og_type="article", assets=assets)


# ---------- sitemap / robots ----------

def build_sitemap(site: dict, stock_ids: list[str], guide_slugs: list[str],
                  lastmod: str) -> str:
    base = site["base_url"].rstrip("/")
    urls = [base + "/"]
    urls += [f"{base}/stocks/{t.lower()}/" for t in stock_ids]
    urls += [f"{base}/guide/{s}/" for s in guide_slugs]
    entries = "\n".join(
        f"  <url><loc>{u}</loc><lastmod>{lastmod}</lastmod></url>" for u in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{entries}\n</urlset>\n")


def build_robots(site: dict) -> str:
    base = site["base_url"].rstrip("/")
    return f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n"


# ---------- 전체 빌드 ----------

def build_all(meta: dict, site: dict, guides: list[dict], out_dir: Path) -> list[str]:
    """모든 정적 페이지를 out_dir에 생성. 반환: 생성한 상대 경로 목록."""
    written: list[str] = []
    stock_ids = [tid for tid in meta["order"] if tid in meta["tickers"]]
    known = [t.lower() for t in stock_ids]

    # 캐시버스팅: 정적 자산 내용 해시. 원본은 항상 소스 트리(src/web)의 파일을
    # 기준으로 계산한다 (out_dir가 임시 폴더인 테스트에서도 동일하게 동작).
    assets = {"css": asset_version(WEB_DIR / "styles.css"),
              "js": asset_version(WEB_DIR / "app.js")}

    def write(rel: str, text: str):
        p = out_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        written.append(rel)

    write("index.html", build_main_page(meta, site, guides, known, assets))
    for tid in stock_ids:
        write(f"stocks/{tid.lower()}/index.html",
              build_stock_page(meta["tickers"][tid], site, known, assets))
    for g in guides:
        write(f"guide/{g['slug']}/index.html",
              build_guide_page(g, site, known, assets))
    lastmod = (meta.get("generated_at") or
               datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))[:10]
    write("sitemap.xml", build_sitemap(site, stock_ids,
                                       [g["slug"] for g in guides], lastmod))
    write("robots.txt", build_robots(site))
    return written


def main() -> int:
    with open(SITE_CONFIG_PATH, encoding="utf-8") as f:
        site = json.load(f)
    meta_path = DATA_DIR / "meta.json"
    if not meta_path.exists():
        print("meta.json이 없습니다. 먼저 python src/fetch_data.py 를 실행하세요.",
              file=sys.stderr)
        return 1
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    guides = load_guides(GUIDES_DIR)
    written = build_all(meta, site, guides, WEB_DIR)
    print(f"생성 완료: 페이지 {len(written) - 2}개 + sitemap.xml + robots.txt "
          f"(가이드 {len(guides)}개 포함) -> {WEB_DIR}")
    for w in written:
        print(f"  {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
