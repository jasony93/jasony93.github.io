"""배포 후 점검 스크립트 (D-7).

배포된 사이트 URL을 받아 필수 항목이 정상 응답하는지 확인한다.
로컬 서버(http://localhost:8765)에도 그대로 쓸 수 있다.

실행:
    python src/scripts/check_deploy.py https://<계정명>.github.io
    python src/scripts/check_deploy.py            # 기본값: site.json의 base_url

점검 항목:
  1. 메인·종목 12페이지·가이드 페이지 200 응답
  2. sitemap.xml의 모든 URL이 실제로 200인지 + 개수 일치
  3. robots.txt 응답과 Sitemap 라인
  4. canonical 이 배포 URL과 일치하는지 (base_url 교체 누락 검출)
  5. 데이터 파일(meta.json, history/*.json) 응답
  6. 핵심 콘텐츠 텍스트 존재 (JS 없이 노출되는지)
  7. 갱신 신선도: meta.json generated_at 이 며칠 지났는지
의존성: 표준 라이브러리만.
"""
from __future__ import annotations

import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE_JSON = ROOT / "src" / "config" / "site.json"
CTX = ssl.create_default_context()
UA = {"User-Agent": "adr-premium-deploy-check/1.0"}

fails: list[str] = []
warns: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    print(("PASS " if ok else "FAIL ") + name + (f"  {detail}" if detail else ""))
    if not ok:
        fails.append(name)
    return ok


def warn(name: str, detail: str = "") -> None:
    print("WARN " + name + (f"  {detail}" if detail else ""))
    warns.append(name)


def get(url: str, timeout: int = 20) -> tuple[int | None, str]:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def main() -> int:
    with open(SITE_JSON, encoding="utf-8") as f:
        configured = json.load(f)["base_url"].rstrip("/")
    if len(sys.argv) > 1:
        base = sys.argv[1].rstrip("/")
    else:
        base = configured
        print("(인자 없음 - site.json의 base_url 사용)")
    print(f"점검 대상: {base}")
    print(f"site.json base_url: {configured}\n" + "=" * 60)

    if "example.com" in configured:
        warn("site.json base_url이 플레이스홀더",
             "배포 전 실제 URL로 교체 후 python src/build_pages.py 재실행 필요")
    if base != configured:
        warn("점검 URL != site.json base_url",
             "canonical·sitemap 항목은 site.json 값 기준이라 불일치가 정상일 수 있음 "
             "(로컬 서버 점검 시). 실제 배포 점검에서는 두 값이 같아야 한다")

    # 1. 메인
    st, body = get(base + "/")
    if not check("메인 페이지 200", st == 200, f"status={st}"):
        print("\n메인 페이지에 접근할 수 없어 중단합니다.")
        return 1
    for needle in ("ADR", "프리미엄", "투자 조언이 아닙니다"):
        check(f"메인 콘텐츠 '{needle}'", needle in body)
    m = re.search(r'<link rel="canonical" href="([^"]+)"', body)
    check("메인 canonical = 배포 URL", bool(m) and m.group(1).rstrip("/") == base,
          m.group(1) if m else "없음")

    # 2. sitemap
    st, sm = get(base + "/sitemap.xml")
    check("sitemap.xml 200", st == 200, f"status={st}")
    locs = re.findall(r"<loc>([^<]+)</loc>", sm) if st == 200 else []
    check("sitemap URL 개수 >= 15", len(locs) >= 15, f"{len(locs)}건")
    bad = []
    for loc in locs:
        s, _ = get(loc)
        if s != 200:
            bad.append(f"{loc}({s})")
    check("sitemap의 모든 URL 200", not bad, ", ".join(bad[:5]))

    # 3. robots
    st, rb = get(base + "/robots.txt")
    check("robots.txt 200", st == 200, f"status={st}")
    if st == 200:
        check("robots.txt Sitemap 라인", "Sitemap:" in rb)
        if base.count("/") > 2:  # 서브경로 배포
            warn("서브경로 배포", "robots.txt는 도메인 루트에서만 크롤러가 읽는다")

    # 4. 데이터 파일
    st, meta_txt = get(base + "/data/meta.json")
    if check("data/meta.json 200", st == 200, f"status={st}"):
        try:
            meta = json.loads(meta_txt)
            ids = meta.get("order", [])
            check("meta.json 종목 수 >= 12", len(ids) >= 12, f"{len(ids)}종목")
            errs = [t for t, e in meta.get("tickers", {}).items() if e.get("fetch_error")]
            check("fetch_error 없음", not errs, ", ".join(errs))
            gen = meta.get("generated_at", "")
            if gen:
                age = (datetime.now(timezone.utc)
                       - datetime.strptime(gen, "%Y-%m-%dT%H:%M:%SZ").replace(
                           tzinfo=timezone.utc)).total_seconds() / 3600
                check("데이터 신선도 48시간 이내", age <= 48, f"{age:.1f}시간 전 ({gen})")
            if ids:
                s, _ = get(f"{base}/data/history/{ids[0]}.json")
                check(f"history/{ids[0]}.json 200", s == 200, f"status={s}")
        except Exception as e:
            check("meta.json 파싱", False, str(e))

    # 5. 정적 자산
    for path in ("/styles.css", "/app.js"):
        s, _ = get(base + path)
        check(f"{path} 200", s == 200, f"status={s}")

    print("=" * 60)
    print(f"결과: FAIL {len(fails)}건, WARN {len(warns)}건")
    if fails:
        print("실패 항목:", ", ".join(fails))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
