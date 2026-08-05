# -*- coding: utf-8 -*-
"""배포 준비(D-2~D-6) 독립 검증. build_all을 임시 디렉토리에 호출해
site.json 원본과 실제 산출물을 건드리지 않는다 (D-7만 별도 스크립트에서 주입 테스트).

D-3: base_url 끝 슬래시 4형식 동일 산출물
D-4: 서브경로 배포 - canonical/sitemap 조합 + 자산·내부 링크 상대경로
D-5: 푸터 고지 2줄 + notices 비우면 사라짐 + 전 15페이지 노출 + contact_email
D-6: verification/analytics 있을 때/없을 때 + 이스케이프(인젝션 시도)
D-2: 워크플로 YAML 구조 (Pages 공식 요구사항 대조)
"""
import io, sys, json, re, tempfile, hashlib
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(r"d:\personal\Claude 프로젝트\Stock tools")
sys.path.insert(0, str(ROOT / "src"))
import build_pages as bp  # noqa: E402

results = []
def check(name, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    print(f"[{tag}] {name}  {detail}")
    results.append((tag, name, detail))

meta = json.load(open(ROOT / "src/web/data/meta.json", encoding="utf-8"))
base_site = json.load(open(ROOT / "src/config/site.json", encoding="utf-8"))
guides = bp.load_guides(ROOT / "docs" / "marketing" / "guides")

def build(site):
    tmp = tempfile.mkdtemp()
    written = bp.build_all(meta, site, guides, Path(tmp))
    return Path(tmp), written

def read(d, rel):
    return (d / rel).read_text(encoding="utf-8")

def sig(d, written):
    """산출물 전체 해시 (파일명 -> sha256)."""
    return {w: hashlib.sha256((d / w).read_bytes()).hexdigest() for w in written}

# ---------- D-3: base_url 4형식 ----------
print("== D-3: base_url 끝 슬래시 4형식 ==")
forms = ["https://ex.example.com", "https://ex.example.com/",
         "https://ex.example.com//", "https://ex.example.com   ".strip() + "/"]
sigs = []
for f in forms:
    s = dict(base_site); s["base_url"] = f
    d, w = build(s)
    sigs.append(sig(d, w))
    if f == forms[0]:
        h = read(d, "stocks/skhy/index.html")
        canon = re.search(r'<link rel="canonical" href="([^"]+)"', h).group(1)
        check("루트 형식 canonical 정상", canon == "https://ex.example.com/stocks/skhy/", canon)
allsame = all(sigs[0] == x for x in sigs[1:])
check("4형식 산출물 완전 동일 (해시 대조, 17개 파일)", allsame,
      f"files={len(sigs[0])}" if allsame else "차이 발생")

# ---------- D-4: 서브경로 ----------
print("\n== D-4: 서브경로(project 사이트) 배포 ==")
s = dict(base_site); s["base_url"] = "https://user.github.io/adr-tracker"
d, w = build(s)
main = read(d, "index.html")
stock = read(d, "stocks/baba/index.html")
guide = read(d, "guide/adr-premium/index.html")
sm = read(d, "sitemap.xml")
canon_m = re.search(r'<link rel="canonical" href="([^"]+)"', main).group(1)
canon_s = re.search(r'<link rel="canonical" href="([^"]+)"', stock).group(1)
check("메인 canonical 서브경로 포함", canon_m == "https://user.github.io/adr-tracker/", canon_m)
check("종목 canonical 서브경로 포함", canon_s == "https://user.github.io/adr-tracker/stocks/baba/", canon_s)
locs = re.findall(r"<loc>(.*?)</loc>", sm)
check("sitemap 15 URL 전부 서브경로", len(locs) == 15 and all(u.startswith("https://user.github.io/adr-tracker/") for u in locs), f"{len(locs)}건")
# 자산·내부 링크는 상대경로여야 함
check("메인 자산 상대경로 (styles.css / app.js)",
      'href="styles.css"' in main and 'src="app.js"' in main)
check("종목 페이지 자산 상대경로 (../../)",
      'href="../../styles.css"' in stock and 'src="../../app.js"' in stock)
check("종목 페이지 data-root=../../ (히스토리 fetch 경로)", 'data-root="../../"' in stock)
check("가이드 자산 상대경로", 'href="../../styles.css"' in guide)
check("내부 링크 절대경로 미사용 (href='/'로 시작하는 내부 링크 없음)",
      not re.search(r'href="/(?!/)', main) and not re.search(r'href="/(?!/)', stock))
rb = read(d, "robots.txt")
check("robots.txt Sitemap 절대 URL", f"Sitemap: https://user.github.io/adr-tracker/sitemap.xml" in rb)

# ---------- D-5: 푸터 고지 ----------
print("\n== D-5: 푸터 고지 ==")
s = dict(base_site)
d, w = build(s)
pages = [x for x in w if x.endswith(".html")]
check("생성 페이지 15개", len(pages) == 15, f"{len(pages)}")
nc = base_site["notices"]["noncommercial"]
ds = base_site["notices"]["data_source"]
allpages = {p: read(d, p) for p in pages}
check("비상업 시험 운영 1줄 = 절차서 6절 문안", all(nc in h for h in allpages.values()) and
      nc == "본 사이트는 비상업 목적의 시험 운영 페이지입니다. 광고·제휴 등 수익 활동을 하지 않습니다.")
check("데이터 출처 1줄 = 절차서 6절 문안", all(ds in h for h in allpages.values()) and
      ds == "시세 데이터 출처: Yahoo Finance (비공식 라이브러리 yfinance 경유).")
check("기존 투자 조언 고지 유지", all("투자 조언이 아닙니다" in h for h in allpages.values()))
check("전 15페이지 동시 노출", sum(1 for h in allpages.values() if nc in h and ds in h) == 15)
# notices 비우기
s2 = dict(base_site); s2["notices"] = {"noncommercial": "", "data_source": "", "contact_email": ""}
d2, _ = build(s2)
h2 = read(d2, "index.html")
check("notices 비우면 두 줄 모두 사라짐", nc not in h2 and ds not in h2)
check("비워도 투자 조언 고지는 유지", "투자 조언이 아닙니다" in h2)
# contact_email
s3 = dict(base_site); s3["notices"] = dict(base_site["notices"]); s3["notices"]["contact_email"] = "qa@example.com"
d3, _ = build(s3)
h3 = read(d3, "index.html")
check("contact_email 설정 시 mailto 링크", 'mailto:qa@example.com' in h3)
check("contact_email 비면 mailto 없음", "mailto:" not in read(d, "index.html"))

# ---------- D-6: verification / analytics ----------
print("\n== D-6: 소유확인 meta + analytics ==")
h_empty = read(d, "index.html")
check("빈 값이면 google/naver meta 미출력",
      "google-site-verification" not in h_empty and "naver-site-verification" not in h_empty)
s4 = dict(base_site)
s4["verification"] = {"google": "gTOKEN123", "naver": "nTOKEN456"}
s4["analytics"] = {"head_html": '<script defer src="https://a.example.com/s.js"></script>'}
d4, _ = build(s4)
h4 = read(d4, "index.html")
h4s = read(d4, "stocks/tsm/index.html")
check("google meta 주입", '<meta name="google-site-verification" content="gTOKEN123">' in h4)
check("naver meta 주입", '<meta name="naver-site-verification" content="nTOKEN456">' in h4)
check("전 페이지에 주입 (종목 페이지 포함)", "gTOKEN123" in h4s and "nTOKEN456" in h4s)
check("analytics head_html 원문 삽입", '<script defer src="https://a.example.com/s.js"></script>' in h4)
check("주입 위치가 head 내부", h4.index("gTOKEN123") < h4.index("</head>") and
      h4.index("https://a.example.com/s.js") < h4.index("</head>"))
# 이스케이프 (인젝션 시도)
s5 = dict(base_site)
s5["verification"] = {"google": '"><script>alert(1)</script><meta x="',
                      "naver": "tok'en<>&"}
d5, _ = build(s5)
h5 = read(d5, "index.html")
m = re.search(r'<meta name="google-site-verification" content="([^"]*)">', h5)
check("google 토큰 이스케이프: content 속성이 닫히지 않고 script 미주입",
      m is not None and "<script>alert(1)</script>" not in h5 and "&lt;script&gt;" in h5,
      (m.group(1)[:60] if m else "meta 파싱 실패"))
m2 = re.search(r'<meta name="naver-site-verification" content="([^"]*)">', h5)
check("naver 토큰 이스케이프 (< > & ')", m2 is not None and "&lt;" in m2.group(1) and "&gt;" in m2.group(1),
      m2.group(1) if m2 else "")
# HTML 구조 무결성
check("이스케이프 후에도 head 구조 정상 (title/canonical 파싱 가능)",
      re.search(r"<title>.*?</title>", h5) is not None and
      re.search(r'<link rel="canonical" href="[^"]+">', h5) is not None)
check("analytics는 원문 삽입 정책 - 문서에 명시(신뢰 소스만)",
      "신뢰할 수 있는 제공자" in base_site.get("_analytics_comment", ""))

# ---------- D-2: 워크플로 ----------
print("\n== D-2: Pages 배포 워크플로 ==")
import yaml
wf = yaml.safe_load(open(ROOT / ".github/workflows/update-data.yml", encoding="utf-8"))
perms = wf.get("permissions", {})
check("permissions 3종 (contents:write, pages:write, id-token:write)",
      perms.get("contents") == "write" and perms.get("pages") == "write"
      and perms.get("id-token") == "write", str(perms))
jobs = wf["jobs"]
check("job 분리: update + deploy", set(jobs) == {"update", "deploy"}, str(list(jobs)))
upd_steps = jobs["update"]["steps"]
uses = [s.get("uses", "") for s in upd_steps]
check("upload-pages-artifact@v3 + path: src/web",
      any(u.startswith("actions/upload-pages-artifact@v3") for u in uses) and
      any(s.get("with", {}).get("path") == "src/web" for s in upd_steps))
dep = jobs["deploy"]
check("deploy job: needs=update", dep.get("needs") == "update")
check("deploy job: environment github-pages + url 출력",
      dep["environment"]["name"] == "github-pages" and "page_url" in str(dep["environment"].get("url", "")))
check("deploy-pages@v4 사용", any(s.get("uses", "").startswith("actions/deploy-pages@v4") for s in dep["steps"]))
check("concurrency 설정 (중복 배포 방지)", "concurrency" in wf, str(wf.get("concurrency")))
check("기존 데이터 커밋 스텝 유지 (git add src/web)",
      any("git add src/web" in str(s.get("run", "")) for s in upd_steps))
check("업로드 스텝이 커밋 스텝 이후 (최신 데이터 배포)",
      next(i for i, s in enumerate(upd_steps) if "git add src/web" in str(s.get("run", ""))) <
      next(i for i, s in enumerate(upd_steps) if s.get("uses", "").startswith("actions/upload-pages-artifact")))
check("기존 스케줄 4종 유지", len(( wf.get(True) or wf.get("on"))["schedule"]) == 4)

n_pass = sum(1 for t, *_ in results if t == "PASS")
n_fail = sum(1 for t, *_ in results if t == "FAIL")
print(f"\nTOTAL: PASS {n_pass} / FAIL {n_fail}")
for t, n, dd in results:
    if t == "FAIL":
        print(" FAIL -", n, "|", dd)
sys.exit(1 if n_fail else 0)
