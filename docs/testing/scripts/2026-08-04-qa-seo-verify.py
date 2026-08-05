# -*- coding: utf-8 -*-
"""QA independent verification for SEO D1~D4 (file-level, no JS).

1. D1: raw HTML of all 14 pages contains core content as text;
   prerendered numbers cross-checked against meta.json for ALL 11 stocks + main cards
2. D2: title/description vs marketing doc 2.3 templates; canonical/OG from site.json;
   title uniqueness across all pages
3. D3: sitemap.xml URL set == actually existing pages; robots.txt validity
4. D4: JSON-LD parses on every page; required fields per type
"""
import io, sys, json, re
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(r"D:\personal\Claude 프로젝트\Stock tools")
WEB = ROOT / "src" / "web"
meta = json.load(open(WEB / "data" / "meta.json", encoding="utf-8"))
site = json.load(open(ROOT / "src" / "config" / "site.json", encoding="utf-8"))
BASE = site["base_url"].rstrip("/")
NAME = site["site_name"]

results = []
def check(name, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    print(f"[{tag}] {name}  {detail}")
    results.append((tag, name, detail))

def fmt_premium(v): return f"{v:+.2f}%"
def fmt_usd(v): return f"${v:,.2f}"
def fmt_local(v, cur):
    if cur == "KRW": return f"{v:,.0f}원"
    if cur == "HKD": return f"HK${v:,.2f}"
    return f"{v:,.1f} TWD"
def fmt_fx(v): return f"{v:,.2f}"

def read(rel): return (WEB / rel).read_text(encoding="utf-8")

def strip_tags(h):
    h = re.sub(r"<script.*?</script>", "", h, flags=re.S)
    return re.sub(r"<[^>]+>", " ", h)

# ---------------- D1: main page ----------------
print("== D1: main page prerender vs meta.json ==")
main = read("index.html")
main_text = strip_tags(main)
order_pos = []
for tid in meta["order"]:
    t = meta["tickers"][tid]
    s = t["snapshot"]
    ok_all = (t["name"] in main_text and fmt_premium(s["premium"]) in main_text
              and fmt_usd(s["p_dr"]) in main and fmt_local(s["p_local"], t["local_currency"]) in main
              and f'href="stocks/{tid.lower()}/"' in main)
    check(f"main card {tid}: name+premium+prices+link prerendered", ok_all,
          fmt_premium(s["premium"]))
    order_pos.append(main.find(f'href="stocks/{tid.lower()}/"'))
check("main card order matches meta order", order_pos == sorted(order_pos))
check("main spark SVGs prerendered (order 수만큼 paths + zero-lines)",
      main.count("card-spark") == len(meta["order"]) and
      len(re.findall(r'card-spark[^>]*>\s*<svg', main)) == len(meta["order"]) and
      main.count("stroke-dasharray") >= len(meta["order"]))
check("main disclaimer + formula in footer", "투자 조언이 아닙니다" in main_text
      and "프리미엄(%) = (DR 가격 * 환율 / (원주 가격 * 전환비율) - 1) * 100" in main_text)
check("main guide links", 'href="guide/adr-premium/"' in main and 'href="guide/adr-conversion/"' in main)
check("main data timestamp shown", meta["generated_at"].replace("T", " ").replace("Z", " UTC") in main)

# ---------------- D1: stock pages ----------------
print("\n== D1: 11 stock pages prerender vs meta.json ==")
for tid in meta["order"]:
    t = meta["tickers"][tid]
    s = t["snapshot"]
    h = read(f"stocks/{tid.lower()}/index.html")
    txt = strip_tags(h)
    checks = {
        "name": t["name"] in txt,
        "premium": fmt_premium(s["premium"]) in txt,
        "dr price": fmt_usd(s["p_dr"]) in h,
        "dr date": s["p_dr_date"] in h,
        "local price": fmt_local(s["p_local"], t["local_currency"]) in h,
        "local date": s["p_local_date"] in h,
        "fx": fmt_fx(s["fx"]) in h,
        "fx date": s["fx_date"] in h,
        "ratio": t["ratio_display"] in txt,
        "formula": "프리미엄(%) = (DR 가격(USD) * 환율 / (원주 가격 * 전환비율 r) - 1) * 100" in txt,
        "disclaimer": "투자 조언이 아닙니다" in txt,
        "implied": fmt_local(round(s["implied_local"]), t["local_currency"]) in h,
        "noscript": "<noscript>" in h,
        "tabs": h.count("period-tab") >= 5,
        "hydration hooks": 'data-page="stock"' in h and 'id="page-data"' in h
                            and f'data-ticker="{tid}"' in h,
    }
    bad = [k for k, v in checks.items() if not v]
    check(f"stock {tid}: 15 prerender checks", not bad, ("missing: " + ",".join(bad)) if bad else "all present")
smsn = read("stocks/smsn/index.html")
check("SMSN GDR notice + badge prerendered",
      "GDR(런던)" in smsn and "런던증권거래소(IOB)" in smsn)
others_no_gdr = all("gdr-notice" not in read(f"stocks/{tid.lower()}/index.html")
                    for tid in meta["order"] if tid != "SMSN")
check("GDR notice absent on other 10 stocks", others_no_gdr)

# ---------------- D2: meta tags ----------------
print("\n== D2: title/description/canonical/OG ==")
def head_tag(h, pattern):
    m = re.search(pattern, h)
    return m.group(1) if m else None

pages = {"/": "index.html"}
for tid in meta["order"]:
    pages[f"/stocks/{tid.lower()}/"] = f"stocks/{tid.lower()}/index.html"
pages["/guide/adr-premium/"] = "guide/adr-premium/index.html"
pages["/guide/adr-conversion/"] = "guide/adr-conversion/index.html"

titles = {}
for path, rel in pages.items():
    h = read(rel)
    title = head_tag(h, r"<title>(.*?)</title>")
    desc = head_tag(h, r'<meta name="description" content="(.*?)">')
    canon = head_tag(h, r'<link rel="canonical" href="(.*?)">')
    ogt = head_tag(h, r'<meta property="og:title" content="(.*?)">')
    ogd = head_tag(h, r'<meta property="og:description" content="(.*?)">')
    ogu = head_tag(h, r'<meta property="og:url" content="(.*?)">')
    ogs = head_tag(h, r'<meta property="og:site_name" content="(.*?)">')
    titles[path] = title
    ok = (canon == BASE + path and ogu == canon and ogt == title and ogd == desc
          and ogs == NAME and title and desc)
    check(f"{path}: canonical/OG consistent", ok,
          f"canonical={canon}")
check("all titles unique across 15 pages", len(set(titles.values())) == len(titles))
check("all titles end with site name", all(t and t.endswith(NAME) for t in titles.values()))

# marketing 2.3 exact template comparisons
mk = {
 "/": ("한국·대만 ADR 프리미엄 추적 - " + NAME,  # 2026-08-04 관리자 정정 반영 (마케팅 2.3절 개정: "실시간" 삭제)
       "SK하이닉스 SKHY, 삼성전자 GDR, TSMC 등 11종목의 ADR 프리미엄(괴리율)을 계산 근거와 함께 매일 차트로 보여드립니다."),
 "/stocks/skhy/": ("SK하이닉스 ADR 프리미엄(SKHY 괴리율) 차트 - " + NAME,
       "SKHY와 원주(000660) 간 프리미엄을 가격·환율·전환비율(10:1) 근거와 함께 계산. 원주 환산가와 일별 추이 차트 제공."),
 "/stocks/smsn/": ("삼성전자 GDR(SMSN) 프리미엄 차트 - 런던 시세 환산 - " + NAME,
       "런던 상장 삼성전자 GDR(1주=보통주 25주)의 원주 대비 프리미엄을 매일 계산. 계산 근거와 히스토리 차트 제공."),
 "/stocks/tsm/": ("TSMC ADR 프리미엄(TSM vs 2330) 차트 - " + NAME,
       "TSM과 대만 원주 2330 간 프리미엄(ADR 1주=원주 5주)을 환율 근거와 함께 계산. 장기 히스토리 차트 제공."),
}
for path, (exp_t, exp_d) in mk.items():
    h = read(pages[path])
    got_t = head_tag(h, r"<title>(.*?)</title>")
    got_d = head_tag(h, r'<meta name="description" content="(.*?)">')
    check(f"{path} title == marketing 2.3", got_t == exp_t,
          f"got={got_t!r}" if got_t != exp_t else "")
    check(f"{path} description == marketing 2.3", got_d == exp_d,
          f"got={got_d!r}" if got_d != exp_d else "")
# default template for a non-override stock (KB)
kb = read("stocks/kb/index.html")
check("/stocks/kb/ default template title",
      head_tag(kb, r"<title>(.*?)</title>") == f"KB금융 ADR 프리미엄(KB 괴리율) 차트 - {NAME}")
kb_desc = head_tag(kb, r'<meta name="description" content="(.*?)">')
check("/stocks/kb/ default template desc has local code + ratio",
      kb_desc is not None and "원주(105560)" in kb_desc and "전환비율(1)" in kb_desc, kb_desc)
# guide description from front matter
gp = read("guide/adr-premium/index.html")
check("guide adr-premium description == 원고 meta_description",
      head_tag(gp, r'<meta name="description" content="(.*?)">') ==
      "ADR가 원주보다 비싸지는 이유와 프리미엄(괴리율) 계산 수식을 SK하이닉스 실제 사례로 설명합니다. 역김치 프리미엄 뜻과 해석 시 주의점까지.")
check("guide og:type=article, stock og:type=website",
      'content="article"' in gp and 'content="website"' in kb)

# ---------------- D3: sitemap / robots ----------------
print("\n== D3: sitemap / robots ==")
sm = read("sitemap.xml")
locs = re.findall(r"<loc>(.*?)</loc>", sm)
expected = [BASE + p for p in pages.keys()]
check("sitemap has exactly 15 URLs (2026-08-05 BABA 편입 반영)", len(locs) == 15, f"got {len(locs)}")
check("sitemap URL set == existing pages", set(locs) == set(expected),
      f"diff={set(locs) ^ set(expected)}" if set(locs) != set(expected) else "")
lastmods = set(re.findall(r"<lastmod>(.*?)</lastmod>", sm))
check("sitemap lastmod = meta date (W3C date)",
      lastmods == {meta["generated_at"][:10]}, str(lastmods))
check("sitemap XML well-formed", sm.startswith('<?xml version="1.0"'))
import xml.etree.ElementTree as ET
try:
    ET.fromstring(sm)
    check("sitemap parses as XML", True)
except Exception as e:
    check("sitemap parses as XML", False, str(e))
rb = read("robots.txt")
check("robots.txt valid", "User-agent: *" in rb and "Allow: /" in rb
      and f"Sitemap: {BASE}/sitemap.xml" in rb)

# ---------------- D4: JSON-LD ----------------
print("\n== D4: JSON-LD ==")
def jsonlds(h):
    return [json.loads(m) for m in
            re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S)]

lds = jsonlds(main)
types = []
for ld in lds:
    graph = ld.get("@graph", [ld])
    types += [g.get("@type") for g in graph]
    for g in graph:
        if g.get("@type") in ("WebSite", "Organization"):
            check(f"main {g['@type']} has name+url",
                  g.get("name") == NAME and g.get("url") == BASE + "/")
check("main has WebSite + Organization", "WebSite" in types and "Organization" in types, str(types))

for tid in meta["order"]:
    h = read(f"stocks/{tid.lower()}/index.html")
    lds = jsonlds(h)
    ok = False
    for ld in lds:
        if ld.get("@type") == "BreadcrumbList":
            items = ld.get("itemListElement", [])
            ok = (len(items) == 2 and items[0]["position"] == 1
                  and items[0]["name"] == "홈" and items[0]["item"] == BASE + "/"
                  and items[1]["position"] == 2
                  and items[1]["name"] == meta["tickers"][tid]["name"]
                  and items[1]["item"] == f"{BASE}/stocks/{tid.lower()}/")
    check(f"stock {tid} BreadcrumbList valid", ok)

src_faq = {
 "adr-premium": ["ADR 프리미엄이란 무엇인가요?", "ADR 프리미엄과 괴리율은 다른 건가요?",
                 "역김치 프리미엄은 무슨 뜻인가요?", "ADR 프리미엄은 어떻게 계산하나요?",
                 "프리미엄이 크면 원주를 사는 것이 유리한가요?"],
 "adr-conversion": ["개인 투자자도 ADR를 원주로 전환할 수 있나요?", "전환에 시간이 얼마나 걸리나요?",
                    "전환비율이 바뀌면 프리미엄 계산도 달라지나요?"],
}
for slug, qs in src_faq.items():
    h = read(f"guide/{slug}/index.html")
    lds = [ld for ld in jsonlds(h) if ld.get("@type") == "FAQPage"]
    check(f"guide {slug} FAQPage present", len(lds) == 1)
    if lds:
        ents = lds[0]["mainEntity"]
        got_q = [e["name"] for e in ents]
        check(f"guide {slug} FAQ questions == 원고 ({len(qs)}개)", got_q == qs,
              f"got={got_q}" if got_q != qs else "")
        struct_ok = all(e.get("@type") == "Question"
                        and e["acceptedAnswer"].get("@type") == "Answer"
                        and e["acceptedAnswer"].get("text") for e in ents)
        check(f"guide {slug} FAQ required fields", struct_ok)
        # answer purity: no trailing-disclaimer bleed. (수식 원문의 '*'는 정당한
        # 내용이므로 검사하지 않는다 - 1차 회차에서 원고와 문자열 완전 일치 확인)
        for e in ents:
            a = e["acceptedAnswer"]["text"]
            check(f"guide {slug} FAQ answer clean: '{e['name'][:20]}...'",
                  "본 글은 정보 제공" not in a,
                  "trailing disclaimer bleed" if "본 글은 정보 제공" in a else "")
        if slug == "adr-premium":
            calc = next(e["acceptedAnswer"]["text"] for e in ents
                        if "계산하나요" in e["name"])
            src = ("프리미엄(%) = (ADR 가격 * 환율 / (원주 가격 * 전환비율) - 1) * 100 입니다. "
                   "전환비율(ADR 1주가 대표하는 원주 수)을 빠뜨리면 완전히 다른 값이 나옵니다.")
            check("guide adr-premium formula FAQ answer == 원고 원문", calc == src)

n_pass = sum(1 for t, *_ in results if t == "PASS")
n_fail = sum(1 for t, *_ in results if t == "FAIL")
print(f"\nTOTAL: PASS {n_pass} / FAIL {n_fail}")
for t, n, d in results:
    if t == "FAIL":
        print(" FAIL -", n, "|", d)
sys.exit(1 if n_fail else 0)
