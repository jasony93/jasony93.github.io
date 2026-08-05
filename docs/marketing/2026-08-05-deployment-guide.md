# 1개월 무료 비상업 공개 운영 - 배포 절차서 (크리미엄 / www.kremium.com)

## 이력

| 날짜 | 내용 |
|---|---|
| 2026-08-05 | 최초 작성 (사용자 확정 방침: yfinance 유지 + 무료 도메인으로 1개월 비상업 공개. 사용자가 직접 실행할 절차서 - 마케팅팀은 실행하지 않음) |
| 2026-08-05 | 1차 개정 (사용자 배포 착수 결정, 실제 값 확정): (1) 플레이스홀더를 실제 값으로 전면 교체 - 계정 jasony93, 저장소 premium_website, 사이트명 "크리미엄" (2) **커스텀 도메인(www.kremium.com) 절차 신설 - 4절** (3) 서브경로 배포 문제와 커스텀 도메인이 이를 해소하는 관계 명시 (4) 검색엔진 등록을 www.kremium.com 기준으로 갱신 (5) 배포 후 확인 체크리스트를 실제 URL로 작성 |

**본 문서는 실행 절차서다. 마케팅팀은 어떤 계정 생성·DNS 변경·저장소 생성·배포·
등록도 실행하지 않았다.** 아래 단계는 전부 사용자(또는 관리자)가 직접 수행한다.

## 확정된 값 (2026-08-05)

| 항목 | 값 |
|---|---|
| GitHub 계정 | `jasony93` |
| 저장소 | `premium_website` (https://github.com/jasony93/premium_website) |
| 기본 Pages URL (커스텀 도메인 적용 전) | `https://jasony93.github.io/premium_website` (서브경로 - 4.1절 문제 참고) |
| **최종 사이트 주소** | **https://www.kremium.com** |
| 사이트명(브랜드) | **크리미엄** |
| base_url (site.json에 넣을 값) | **https://www.kremium.com** |

참조: `docs/planning/2026-08-05-baba-volume-domain.md` 3절,
`docs/development/2026-08-03-adr-premium-design.md`,
`docs/marketing/2026-08-03-adr-premium-marketing.md` 2.4절.

---

## 0. 먼저 읽을 것 - 리스크 고지 (사용자 인지·선택 사항)

**이번 공개 운영은 yfinance(비공식 Yahoo Finance 라이브러리)를 데이터 소스로
유지한 채 진행한다. 야후 약관은 데이터의 공개 표시·재배포를 사전 동의 없이
금지하며, 이 조항은 상업/비상업 여부와 별개다. 즉 "광고를 붙이지 않는 비상업
운영"이어도 약관 위반 소지는 남아 있다. 기획팀 검토(
`docs/planning/2026-08-05-baba-volume-domain.md` 3.2절)의 1안은 무료 공식 API
부분 전환이었으나, 사용자는 실험 속도를 우선해 yfinance 유지를 선택했다. 이는
사용자가 리스크를 인지하고 내린 결정이며 본 문서에 그 사실을 기록한다.**
약관 출처: https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.html ,
yfinance 고지: https://ranaroussi.github.io/yfinance/

리스크 완화를 위해 이번 운영에서 지키는 것:
- 수익 장치(광고·제휴·후원) 일절 미부착 (7절)
- 데이터 출처·지연 표기, 비상업 실험 운영 고지 명시 (7절)
- 기간 1개월 한정, 종료 시점에 재결정 (12절-7)

**차단 발생 시 증상과 대응**: 야후가 레이트리밋·차단을 걸면 법적 통보가 아니라
**데이터 갱신이 조용히 멈추는 형태**로 나타난다. 증상은 (a) Actions 워크플로
실패(빨간 X) 또는 (b) 워크플로는 성공하는데 값이 갱신되지 않음 (c) 사이트에
"갱신 실패, OO 기준" 배지가 뜸(구현되어 있음). 대응 순서: 1) Actions 로그에서
실패 종목·에러 확인 2) 일시적 레이트리밋이면 수 시간 후 자동 회복 여부 관찰
3) 지속되면 즉시 공개 중단(10절 롤백) 또는 무료 공식 API 전환(KRX OpenAPI·TWSE
OpenAPI·한국은행 ECOS + 미국 DR용 무료 티어)을 개발팀에 요청. 전환 경로는
기획 문서 3.2절 옵션(ii)에 정리되어 있다.

---

## 1. 사전 준비 (체크리스트)

| # | 준비물 | 상태·비고 |
|---|---|---|
| 1 | GitHub 계정 `jasony93` | 확보됨. 무료(GitHub Free) 플랜이면 **저장소가 public이어야 Pages 게시 가능**(2.1절) |
| 2 | Git 설치 (로컬 PC) | `git --version`으로 확인. 없으면 https://git-scm.com/ |
| 3 | 도메인 `kremium.com` | 사용자 보유. **현재 www가 52.20.84.62(AWS 계열)를 가리키고 있어 DNS 레코드 교체 필요**(4.3절) |
| 4 | 도메인 등록기관(또는 DNS 관리 콘솔) 로그인 정보 | 레코드 편집 권한 필요. 어디서 DNS를 관리하는지(등록기관 기본 DNS / Route 53 / Cloudflare 등) 먼저 확인할 것 |
| 5 | Google 계정 | Search Console 등록용 (8절) |
| 6 | 네이버 계정 | 네이버 서치어드바이저 등록용 (8절) |

소요 예상: 전체 **집중해서 2~3시간** + DNS 전파 대기(수분~수시간, 최대 24시간)
+ HTTPS 인증서 발급 대기(최대 24시간). 검색 색인 반영은 별도로 수일.

**권장 실행 순서**: 2절(저장소) -> 3절(Pages) -> **4절(커스텀 도메인)** ->
5절(base_url 교체·재빌드) -> 6절(자동 갱신) -> 7절(고지) -> 8절(검색등록) ->
9절(확인 체크리스트).
**4절을 5절보다 먼저 하는 이유**: base_url을 서브경로로 넣었다가 도메인 붙이고
다시 바꾸면 재빌드·재푸시를 두 번 하게 된다. 도메인을 먼저 연결하고 base_url은
처음부터 `https://www.kremium.com`으로 한 번만 설정한다.

---

## 2. 저장소 생성과 코드 업로드

현재 프로젝트 폴더는 **git 저장소가 아니다**. `git init`부터 시작한다.

### 2.1 public 저장소 (사실상 강제)

| 항목 | public | private |
|---|---|---|
| GitHub Pages 게시 | 무료 플랜에서 가능 | **무료 플랜 불가** - Pro/Team/Enterprise 필요. 출처: https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site |
| Actions 사용료 | **무료·무제한**(GitHub 호스팅 표준 러너). 출처: https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions | Free 플랜 월 2,000분 한도 |
| 코드 노출 | 소스·데이터 공개 | 비공개 |

-> **public으로 생성한다.** 우리 워크플로는 장중 스냅샷 포함 하루 20회 이상
실행되므로 private였다면 월 2,000분 한도가 빠듯해질 수 있다(추정).

### 2.2 명령어 절차 (로컬 PowerShell - 그대로 복사 가능)

```powershell
# 프로젝트 폴더로 이동
cd "d:\personal\Claude 프로젝트\Stock tools"

# 1) git 저장소 초기화
git init
git branch -M main

# 2) 최초 커밋 (개발팀 D-1: .gitignore 확정이 선행되어야 함 - 11절)
git add .
git commit -m "chore: initial commit (ADR premium tracker MVP)"

# 3) GitHub에서 빈 저장소 생성 (웹 UI)
#    github.com -> 우측 상단 + -> New repository
#    - Repository name: premium_website
#    - Public 선택
#    - "Add a README file" 등 초기화 옵션은 전부 체크 해제 (충돌 방지)
#    -> Create repository

# 4) 원격 연결·푸시
git remote add origin https://github.com/jasony93/premium_website.git
git push -u origin main
```

푸시 시 인증창이 뜨면 GitHub 계정으로 로그인(또는 Personal Access Token 사용).

---

## 3. GitHub Pages 배포 설정

### 3.1 방식 - GitHub Actions 방식 (권고·확정)

| 방식 | 내용 | 적합성 |
|---|---|---|
| 브랜치 방식 | 브랜치의 **루트(`/`) 또는 `/docs` 폴더만** 게시 가능. 출처: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site | **부적합** - 우리 정적 파일은 `src/web/`에 있어 두 선택지 어디에도 없음 |
| **GitHub Actions 방식** | `actions/upload-pages-artifact`(path: src/web) + `actions/deploy-pages` | **적합** - 경로 자유, 기존 update-data 워크플로와 연결. 시간당 10빌드 소프트 리밋도 커스텀 워크플로엔 미적용(출처: Pages limits 문서) |

### 3.2 UI 설정 절차

1. https://github.com/jasony93/premium_website -> 상단 **Settings** 탭
2. 좌측 메뉴 **Pages** (Code and automation 섹션)
3. **Build and deployment** -> **Source** 를 **GitHub Actions** 로 선택
4. 배포 워크플로가 1회 실행되면 같은 화면에 사이트 URL이 표시된다
   (이 시점의 URL은 `https://jasony93.github.io/premium_website` - 4절에서 교체)

참고 한도(전부 소프트 리밋, 우리 규모에선 문제없음 - 추정): 사이트 1GB,
대역폭 월 100GB, 배포 10분 타임아웃.
출처: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits

---

## 4. 커스텀 도메인 연결 (www.kremium.com) - 이번 개정의 핵심

### 4.1 왜 커스텀 도메인이 "있으면 좋은 것"이 아니라 필요한가

저장소명이 `premium_website`이므로 GitHub Pages 기본 주소는 **project 사이트**
형태인 `https://jasony93.github.io/premium_website` 가 된다. 즉 사이트가
**서브경로**에 놓인다(출처:
https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages
- project 사이트는 `http(s)://<owner>.github.io/<repositoryname>`).

서브경로 배포의 문제:

| 문제 | 설명 |
|---|---|
| **robots.txt가 무효** | robots.txt는 **호스트 루트에만** 유효하다. 우리 빌드가 만든 robots.txt는 `.../premium_website/robots.txt`에 놓이는데, 검색엔진이 읽는 것은 `https://jasony93.github.io/robots.txt`(= jasony93 계정 user 사이트 소유)다. 우리가 통제할 수 없다 |
| sitemap 신뢰성 저하 | sitemap 자체는 제출로 보완되나, robots.txt의 Sitemap 지시문 경로가 위 이유로 무효 |
| 자산·링크 경로 위험 | 절대경로(`/styles.css`)를 쓰는 부분이 있으면 서브경로에서 깨진다 |
| 브랜드·신뢰도 | 금융 정보 사이트로서 도메인 신뢰도 |

**커스텀 도메인을 연결하면 사이트가 `https://www.kremium.com/` 루트로 서빙되므로
위 문제가 전부 해소된다.** robots.txt는 `https://www.kremium.com/robots.txt`로
정상 인식되고, 내부 경로도 `/stocks/skhy/` 그대로 유효해진다. 그래서 이번
배포에서는 커스텀 도메인 연결이 선택이 아니라 **필수 단계**다.

### 4.2 DNS 레코드 값 (GitHub 공식 문서 확인값)

출처: https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site

**(A) www 서브도메인 - 우리의 정본 주소**

| 타입 | 이름(호스트) | 값 |
|---|---|---|
| CNAME | `www` | `jasony93.github.io` |

- 값은 저장소명을 **포함하지 않는다**. `jasony93.github.io/premium_website`가
  아니라 `jasony93.github.io` 다 (흔한 실수).
- 콘솔에 따라 끝에 마침표가 붙은 `jasony93.github.io.` 형태로 저장될 수 있다
  (대부분 자동 처리).

**(B) apex 도메인(kremium.com)도 함께 쓰려면 - 권고**

apex에는 CNAME을 쓸 수 없으므로 A 레코드(+AAAA)를 사용한다.

| 타입 | 이름 | 값 |
|---|---|---|
| A | `@` (apex) | 185.199.108.153 |
| A | `@` | 185.199.109.153 |
| A | `@` | 185.199.110.153 |
| A | `@` | 185.199.111.153 |
| AAAA | `@` | 2606:50c0:8000::153 |
| AAAA | `@` | 2606:50c0:8001::153 |
| AAAA | `@` | 2606:50c0:8002::153 |
| AAAA | `@` | 2606:50c0:8003::153 |

- 공식 문서는 A 레코드와 **AAAA 레코드를 함께 설정할 것을 강력 권장**한다.
- DNS 제공자가 지원하면 A/AAAA 대신 **ALIAS 또는 ANAME** 레코드로 `@` ->
  `jasony93.github.io` 설정도 공식 인정 방식이다.
- apex를 설정해 두면 `kremium.com`으로 접속해도 도달한다. GitHub가 apex <-> www
  간 리다이렉트를 제공하는 것으로 알려져 있으나 이번 조사에서 공식 문서로 직접
  확인하지 못했다(**확인 필요**). 실제 동작은 9절 체크리스트 4번으로 검증한다.

### 4.3 기존 레코드 교체 - 가장 주의할 지점

**현재 www.kremium.com은 52.20.84.62(AWS 계열)를 가리키고 있다(관리자 DNS 조회
확인). 이 기존 레코드를 반드시 제거·교체해야 한다.**

1. **같은 이름에 CNAME과 다른 레코드는 공존할 수 없다**(DNS 규칙). `www`에 기존
   A 레코드가 있다면 **CNAME 추가 전에 기존 A 레코드를 삭제**해야 한다. 삭제하지
   않으면 콘솔이 저장을 거부하거나, 저장돼도 예측 불가하게 동작한다.
2. apex(`@`)에도 기존 A 레코드(AWS IP)가 있을 수 있다. apex를 함께 쓸 계획이면
   4.2(B) 값으로 **전부 교체**한다. apex를 쓰지 않더라도 기존 AWS 레코드가 남으면
   방문자가 `kremium.com` 접속 시 엉뚱한 페이지·오류를 보게 되므로 정리 권고.
3. **기존 서비스 확인**: 그 AWS IP에서 현재 무언가 운영 중이라면 끊긴다.
   사용하지 않는 예전 설정인지 사용자가 먼저 확인할 것.
4. **변경 전 기존 레코드를 스크린샷·메모**해 둔다(롤백용 - 10절).
5. **TTL**: 교체 전에 TTL을 낮게(예: 300초) 바꿔 두면 전파가 빨라진다. 이미
   높은 TTL로 캐시된 뒤라면 그만큼 대기해야 할 수 있다.
6. **전파 대기**: 보통 수분~수시간, 최대 24시간. 확인 명령(로컬 PowerShell):
   ```powershell
   nslookup www.kremium.com
   # jasony93.github.io 또는 185.199.x.153 계열로 바뀌면 전파된 것
   # 52.20.84.62가 그대로면 아직 전파 전이거나 레코드 미교체
   ```

### 4.4 GitHub 저장소 설정

1. https://github.com/jasony93/premium_website -> **Settings** -> **Pages**
2. **Custom domain** 입력란에 `www.kremium.com` 입력 -> **Save**
3. GitHub가 DNS를 확인한다. 아직 전파 전이면 경고가 표시되며, 전파 후 자동으로
   해소된다(재입력 불필요).
4. **Enforce HTTPS** 체크박스를 활성화한다.
   - 인증서 발급까지 **최대 24시간** 걸릴 수 있다(공식 문서). 발급 전에는
     체크박스가 비활성일 수 있으니 나중에 다시 들어와 켠다.
   - 켜지 않으면 http 접속자가 그대로 http를 쓰게 되어 SEO·신뢰도에 불리하다.
     **반드시 켠다.**

### 4.5 CNAME 파일과 저장소 설정의 관계 (개발팀 작업과 연결)

- 브랜치 방식 배포에서는 Custom domain 저장 시 소스 브랜치 루트에 `CNAME` 파일이
  자동 생성된다.
- **그러나 우리처럼 커스텀 GitHub Actions 워크플로로 배포하면 CNAME 파일은 자동
  생성되지 않고, 기존 CNAME 파일이 있어도 무시되며 필수가 아니다.** 즉
  **저장소 Settings의 Custom domain 입력값이 실질적 기준**이다.
  (출처: 4.2절과 동일한 공식 문서 - 커스텀 Actions 워크플로 사용 시 "CNAME
  파일이 생성되지 않으며 기존 CNAME 파일은 무시되고 필수가 아니다")
- 개발팀이 `src/web/CNAME`을 생성 중이라면: **무해하지만 그것만으로는 도메인이
  연결되지 않는다.** 4.4절 UI 입력이 반드시 필요하다(11절 D-8).

### 4.6 도메인 검증 (권고 - 도메인 탈취 방지)

출처: https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages

- 위치: **저장소 설정이 아니라 계정 설정** - github.com 우측 상단 프로필 ->
  Settings -> 좌측 **Pages** -> **Add a domain** -> `kremium.com` 입력
- 안내되는 TXT 레코드를 DNS에 추가한다. 이름 형식은
  `_github-pages-challenge-jasony93.kremium.com`
  (콘솔에 따라 상대 이름 `_github-pages-challenge-jasony93`만 입력),
  값은 GitHub가 제공하는 토큰 문자열.
- 효과: 저장소 삭제·플랜 변경 등으로 연결이 풀려도 **타인이 이 도메인으로 Pages를
  붙이지 못하게 막는다**(탈취 방지). 검증한 도메인의 직속 서브도메인도 보호된다.
- 와일드카드 DNS 레코드(`*.kremium.com`)는 사용하지 말 것(공식 권고).

---

## 5. 설정값 교체 (base_url·사이트명)

`src/config/site.json`은 현재 플레이스홀더 상태이며, 이 값은 canonical·sitemap·
robots·OG URL에 전부 쓰인다. 잘못된 값으로 공개하면 검색엔진이 존재하지 않는
도메인을 정본으로 인식해 색인이 어그러진다.

**교체할 값 (그대로 사용 가능):**

```json
{
  "site_name": "크리미엄",
  "base_url": "https://www.kremium.com"
}
```

- `base_url`은 **www 포함, https, 끝 슬래시 없음** 기준이다. 끝 슬래시 처리는
  build_pages.py 구현에 따르므로 개발팀 확인 항목(11절 D-3).
- 사이트명 "크리미엄"은 페이지 title 끝의 `- 크리미엄`과 JSON-LD에 반영된다.
  개발팀이 브랜드 반영 작업 중이므로 코드 내 표기와 일치하는지 확인 필요(D-9).

교체 후 **반드시 재빌드**하고 확인한다:

```powershell
cd "d:\personal\Claude 프로젝트\Stock tools"
python src/build_pages.py
python -m http.server 8765 -d src/web   # 별도 창에서 실행 -> http://localhost:8765

git add -A
git commit -m "chore: set production base_url (www.kremium.com) and site name"
git push
```

---

## 6. 자동 갱신 활성화

`.github/workflows/update-data.yml`은 이미 저장소에 존재한다. **푸시하는 순간
GitHub가 인식하며 별도 활성화 버튼은 없다.**

### 6.1 1회 수동 실행으로 검증 (workflow_dispatch)

1. https://github.com/jasony93/premium_website -> **Actions** 탭
2. 좌측 목록에서 **update-data** 선택
3. 우측 **Run workflow** -> `mode` 입력란 `full` -> **Run workflow**
4. 로그 확인: `Fetch data (full)` 성공 -> `Build static pages` 성공 ->
   `Run unit tests` 성공 -> `Commit and push updates` 커밋 생성(또는 "변경 없음")
5. 실패 시 실패 스텝 로그를 개발팀에 전달(0절 차단 증상 참고)

### 6.2 갱신 -> 재배포 흐름 (현재 끊겨 있음 - 개발팀 작업 필요)

현 워크플로는 데이터 커밋에서 끝나고 파일 말미에
`# 배포: 정적 호스팅 선택 확정 후 이 뒤에 배포 스텝을 추가한다.` 로 되어 있다.
**지금 상태로는 데이터가 갱신돼도 사이트에 반영되지 않는다.** 배포 스텝 추가는
개발팀 작업(11절 D-2). 완성 후 흐름:

```
스케줄 트리거 -> fetch_data.py -> build_pages.py -> src/web 커밋
   -> upload-pages-artifact(path: src/web) -> deploy-pages -> www.kremium.com 반영
```

`deploy-pages`는 `permissions: pages: write, id-token: write`와
`environment: github-pages`를 요구한다(출처: https://github.com/actions/deploy-pages ).
기존 `permissions: contents: write`(커밋용)와 병존하도록 구성해야 한다.

### 6.3 스케줄 운영 유의사항

- **60일 무활동 시 스케줄 자동 비활성화**: public 저장소에서 60일간 커밋 활동이
  없으면 예약 워크플로가 꺼진다. **새 커밋만 활동으로 인정**된다. 매일 데이터
  커밋이 생기므로 실질 해소되나, **연속 실패로 커밋이 멈추면 60일 후 스케줄까지
  죽는 이중 장애**가 된다. 출처: https://github.com/orgs/community/discussions/57858
- 알림이 눈에 잘 띄지 않으므로 **주 1회 Actions 탭에서 최근 실행이 녹색인지
  확인**하는 것을 운영 루틴에 넣는다.
- 스케줄은 정시 보장이 없고 10~30분 지연이 흔하다.

---

## 7. 비상업 운영 명확화

1. **수익 장치 미부착**: 애드센스·제휴 링크·후원 버튼·스폰서 배너 일절 없음.
2. **푸터 고지 문안 (개발팀 작업 D-5)**:

   ```
   본 사이트는 비상업 목적의 시험 운영 페이지입니다. 광고·제휴 등 수익 활동을
   하지 않습니다.
   모든 정보는 참고용이며 투자 조언이 아닙니다. 데이터는 지연·종가 기준이며
   정확성을 보장하지 않습니다.
   시세 데이터 출처: Yahoo Finance (비공식 라이브러리 yfinance 경유).
   최종 갱신: <자동 표기>
   ```
   - 기존 "투자 조언 아님" 고지는 이미 전 페이지 푸터에 있다. **비상업 시험 운영
     1줄과 데이터 출처 1줄이 추가 항목**이다.
   - 출처 표기가 약관 문제를 해소하지는 않는다(0절). 투명성 목적이다.
3. **연락 경로**: 문의·삭제 요청을 받을 이메일 1개를 푸터에 두는 것을 권고한다
   (사용자 결정 - 12절).

---

## 8. 검색엔진 등록·측정 설정 (www.kremium.com 기준)

측정이 없으면 1개월 실험이 무의미하다. 필수 항목이다.

### 8.1 Google Search Console - 도메인 속성 권고

1. https://search.google.com/search-console -> Google 계정 로그인
2. 속성 유형 선택:

   | 유형 | 커버 범위 | 소유확인 | 평가 |
   |---|---|---|---|
   | **도메인 속성** (`kremium.com`) | www/apex, http/https 전부 통합 | **DNS TXT 레코드** | **권고.** 도메인을 보유했고 DNS를 편집할 수 있다. www·apex 데이터가 나뉘지 않고, 4.6절 도메인 검증 TXT를 넣는 김에 함께 처리 가능. **개발팀의 meta 태그 주입(D-6) 없이 등록 가능**한 것이 실무상 큰 장점 |
   | URL 접두어 (`https://www.kremium.com`) | 해당 접두어만 | HTML 태그/파일 등 | 차선. meta 태그 주입 필요 |

3. **도메인 속성** 선택 -> `kremium.com` 입력 -> 안내된 TXT 레코드를 DNS에 추가
   -> 전파 후 **확인** 클릭
4. 확인 후 좌측 **Sitemaps** -> `sitemap.xml` 제출
   (최종 URL: https://www.kremium.com/sitemap.xml )
5. **URL 검사** 도구로 메인·`/stocks/skhy/`를 개별 색인 요청하면 초기 색인이
   빨라진다(일반론). 색인 반영에는 통상 수일.

### 8.2 네이버 서치어드바이저

1. https://searchadvisor.naver.com -> 네이버 로그인 -> 웹마스터 도구
2. 사이트 등록: `https://www.kremium.com` (네이버는 도메인 속성 개념 없이 URL
   단위 등록)
3. 소유확인: **HTML 파일 업로드** 방식이 우리 구조에 가장 간단하다 - 제공되는
   검증 파일을 `src/web/` 아래에 두고 커밋·푸시하면 배포와 함께 루트로 올라간다
   (meta 태그 주입 D-6을 기다리지 않아도 됨). HTML 태그 방식을 쓰려면 D-6 필요.
   - **주의**: 빌드가 `src/web`을 정리·덮어쓰는 동작이 있으면 검증 파일이 사라질
     수 있다 - 개발팀 확인 항목(11절 D-10)
4. 등록 후 **요청 -> 사이트맵 제출**로 `https://www.kremium.com/sitemap.xml` 제출
5. **웹페이지 수집 요청**으로 메인·SKHY 상세·가이드 2편 URL 개별 요청 권고

한국어 검색 수요의 상당 부분이 네이버에서 발생한다(추정)이므로 생략하지 않는다.

### 8.3 방문 분석 도구 (무료)

| 후보 | 장점 | 단점 |
|---|---|---|
| Cloudflare Web Analytics | 무료, 쿠키 없음·경량, 설정 단순 | 지표 단순 |
| Google Analytics 4 | 무료, 상세 | 무거움, 개인정보 처리방침 필요, 설정 복잡 |

**권고: Cloudflare Web Analytics.** 절차: Cloudflare 계정 -> Web Analytics ->
Add a site -> `www.kremium.com` -> 제공 스크립트 1줄을 모든 페이지에 삽입
(개발팀 D-6 경로).
- **확인 필요**: Cloudflare에 호스팅되지 않은 사이트(GitHub Pages)에 스크립트
  방식 적용이 현재도 가능한지 등록 시점에 확인할 것(과거 가능했으나 정책 변경
  여부 미확인).

### 8.4 실험 중 기록할 지표 (주 1회)

주간 UV/PV, 페이지별 조회 상위 5개, 검색 유입 쿼리(Search Console), 재방문 비율,
유입 경로(검색/직접/추천). -> 12절-7 판단 기준에 사용.

---

## 9. 배포 후 확인 체크리스트 (실제 URL 기준)

브라우저와 PowerShell로 순서대로 확인한다. 전부 통과해야 "배포 완료"다.

| # | 확인 항목 | 방법 / 기대 결과 |
|---|---|---|
| 1 | DNS 전파 | `nslookup www.kremium.com` -> `jasony93.github.io` 또는 185.199.x.153 계열 (52.20.84.62면 아직 미교체·미전파) |
| 2 | 메인 접속 | https://www.kremium.com/ 열림, 카드 그리드 정상 |
| 3 | **HTTPS 적용** | 자물쇠 표시·인증서 오류 없음. http://www.kremium.com 접속 시 https로 리다이렉트(Enforce HTTPS 효과) |
| 4 | apex 접속 | https://kremium.com/ -> www로 이동하거나 정상 표시 (4.2절 미확인 항목 실측) |
| 5 | 종목 상세 | https://www.kremium.com/stocks/skhy/ 정상, 프리미엄 수치·차트·원천값 4종 표시 |
| 6 | 종목 전수 | 각 `/stocks/<티커>/` 접속 (skhy, smsn, tsm, baba, kb, shg, wf, pkx, kep, skm, kt, lpl - 실제 목록은 sitemap 기준) |
| 7 | 가이드 페이지 | https://www.kremium.com/guide/adr-premium/ , /guide/adr-conversion/ 정상 |
| 8 | **sitemap** | https://www.kremium.com/sitemap.xml 열림. 내부 URL이 전부 `https://www.kremium.com/...` 로 시작 (github.io나 example.com이 남아 있으면 base_url 교체·재빌드 누락) |
| 9 | **robots.txt** | https://www.kremium.com/robots.txt 열림, Sitemap 지시문이 위 주소를 가리킴 |
| 10 | **canonical** | 각 페이지 소스보기(Ctrl+U) -> `<link rel="canonical" href="https://www.kremium.com/...">` 가 현재 URL과 일치 |
| 11 | OG 태그 | og:url·og:title이 실제 URL·브랜드("크리미엄") 반영 |
| 12 | 브랜드 표기 | title 끝이 `- 크리미엄`, 헤더·푸터 브랜드 일치 |
| 13 | 구 URL 리다이렉트 | `https://www.kremium.com/#/SKHY` -> `/stocks/skhy/` 이동 |
| 14 | 비상업 고지 | 푸터에 비상업 시험 운영·데이터 출처·투자 조언 아님 3종 노출 |
| 15 | 모바일 | 375px 폭에서 레이아웃 깨짐·가로 스크롤 없음 |
| 16 | 콘솔 에러 | 개발자도구 Console 에러 0건 (특히 404 자산 - 서브경로 잔재 여부) |
| 17 | 자동 갱신 | Actions 최근 실행 녹색 + 실행 후 사이트 "최종 갱신" 표기 변경 확인 |
| 18 | 검색 등록 | Search Console 소유확인 완료·sitemap "성공". 네이버 동일 |

문제 발생 시 우선 확인: 8·9·10번이 틀리면 대부분 **base_url 교체 후 재빌드를
안 했거나**(5절) 푸시가 안 된 것이다.

---

## 10. 중단·롤백 절차 (필요 시)

1. 저장소 Settings -> Pages -> Source **None** (게시 중단)
   - 또는 Settings 최하단 **Change repository visibility**로 private 전환
     (무료 플랜에서 private면 Pages 자동 중단 - 2.1절 근거)
2. Actions 탭 -> update-data -> `...` -> **Disable workflow** (갱신 중단)
3. 도메인 원상 복구: DNS의 CNAME/A 레코드를 이전 값(AWS)으로 되돌린다.
   **4.3절-4에서 메모해 둔 기존 값 사용**
4. Search Console·서치어드바이저 속성 삭제(선택)
5. 로컬 데이터·코드는 남으므로 재개는 역순으로 가능

---

## 11. 개발팀 선행·병행 작업 목록 (관리자가 개발팀에 전달)

| # | 작업 | 내용 | 필수도 |
|---|---|---|---|
| D-1 | `.gitignore` + 데이터 커밋 정책 확정 | 설계 문서는 `src/web/data`를 "커밋 대상 아님"이라 했으나 Pages 배포엔 데이터가 필요하고 워크플로도 `git add src/web`을 한다. 상충 해소 | 필수(2절 전) |
| D-2 | 워크플로에 Pages 배포 스텝 추가 | `upload-pages-artifact@v3`(path: src/web) + `deploy-pages@v4`, `permissions: pages: write / id-token: write`, `environment: github-pages`. 기존 contents:write와 병존 | 필수 |
| D-3 | base_url 형식 검증 | `https://www.kremium.com`(끝 슬래시 없음) 기준으로 canonical·sitemap·OG URL 조합이 올바른지 | 필수(5절 전) |
| D-4 | 자산 경로 점검 | 커스텀 도메인 루트 서빙에서는 절대경로(`/styles.css`)가 정상 동작. 도메인 연결 전 임시 확인 시 서브경로에서 깨질 수 있음을 인지 | 권장 |
| D-5 | 푸터 고지 문안 추가 | 7절-2의 비상업 1줄 + 데이터 출처 1줄 | 필수 |
| D-6 | 검증 태그·분석 스크립트 주입 경로 | site.json 설정값으로 받아 전 페이지 head에 주입(값 없으면 미출력). **Search Console은 도메인 속성(DNS)으로 우회 가능하나 분석 스크립트에는 여전히 필요** | 필수 |
| D-7 | 배포 후 점검 스크립트/체크리스트 | 9절 중 8·9·10(sitemap·robots·canonical) 자동 점검 | 권장 |
| D-8 | **CNAME 파일 관련 정정 인지** | 커스텀 Actions 워크플로 배포에서는 `src/web/CNAME`이 **무시되며 필수가 아니다**. 도메인 연결 기준은 저장소 Settings > Pages의 Custom domain 입력(4.5절, 공식 문서). 파일은 무해하나 그것만으로 연결되지 않음 | 필수 인지 |
| D-9 | 브랜드명 일관성 | site.json `site_name`="크리미엄"과 코드 내 표기(헤더·푸터·OG·JSON-LD) 일치 | 필수 |
| D-10 | 검증 파일 보존 확인 | 네이버 소유확인 HTML 파일을 `src/web/`에 둘 때 빌드가 삭제·덮어쓰지 않는지(8.2절) | 권장 |

---

## 12. 사용자가 결정·실행해야 할 항목

| # | 항목 | 상태·권고 |
|---|---|---|
| 1 | 저장소 public 동의 (소스·데이터 공개) | 무료 플랜 Pages의 사실상 전제 |
| 2 | **기존 AWS DNS 레코드 정리 여부 확인** | **52.20.84.62에서 현재 운영 중인 것이 있는지 먼저 확인.** 있으면 끊긴다 |
| 3 | apex(kremium.com) 함께 연결할지 | 권고: 연결(4.2절 B). `kremium.com` 직접 입력 접속 가능성이 높음 |
| 4 | 도메인 검증(4.6절) 수행 여부 | 권고: 수행(탈취 방지, TXT 1건 추가) |
| 5 | 푸터 공개 연락 이메일 | 공개할 주소 1개 결정 |
| 6 | 분석 도구 선택 | 권고: Cloudflare Web Analytics |
| 7 | **1개월 후 판단 기준 - 미확정** | 마케팅팀 제안 유지: **상업 전환 검토 = 월 누적 10,000 PV 이상 또는 주간 UV 4주 연속 증가 / 연장 = 3,000~10,000 PV / 종료(비공개 회귀) = 3,000 PV 미만.** 시작 전에 확정해야 실험이 의미를 갖는다 |
| 8 | 실험 시작일 D 확정 | D+30 판단일을 함께 기록 |

### 상업 전환 시 선행 조건 (판단 결과가 "상업 전환"일 경우)

1. **상업 데이터 API 교체가 최우선** - yfinance 상태로 광고를 붙이면 "비상업"
   이라는 유일한 완충재가 사라진다 (PRD 3.4절 후보, BM 문서 1.2절 비용 최적화안)
2. 도메인은 이미 www.kremium.com이므로 **추가 이전 비용이 없다** - github.io로
   시작했다면 필요했을 리다이렉트 관리·서치콘솔 이관·순위 재안착이 원천 불필요해졌다
   (커스텀 도메인을 처음부터 쓰는 이번 구성의 이점)
3. 수익화 장치(광고·제휴)는 1이 끝난 뒤 착수 (마케팅 문서 3절 단계안)

---

## 부록: 확인한 출처

- Pages 개요·URL 형태(project 사이트 = `<owner>.github.io/<repo>`): https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages
- Pages 생성 조건(무료 플랜은 public 필수): https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site
- publishing source(브랜치는 root 또는 /docs만, Actions 방식): https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- **커스텀 도메인 관리(CNAME 대상값, apex A/AAAA IP, Enforce HTTPS, CNAME 파일 취급)**: https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site
- **도메인 검증(TXT `_github-pages-challenge-<user>`, 탈취 방지)**: https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages
- Pages 사용량 한도: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- Actions 요금(public 무료, Free private 월 2,000분): https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions
- deploy-pages 액션 권한·예시: https://github.com/actions/deploy-pages
- 60일 무활동 스케줄 비활성화: https://github.com/orgs/community/discussions/57858
- yfinance·야후 약관: https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.html , https://ranaroussi.github.io/yfinance/

**확인 필요(미확인) 항목**:
- GitHub Pages의 apex <-> www 자동 리다이렉트 동작 (4.2절 - 9절 체크리스트 4번으로 실측)
- Cloudflare Web Analytics의 외부 호스팅 사이트 적용 가능 여부 (8.3절)
- 빌드가 `src/web` 내 수동 배치 파일(네이버 검증 파일)을 보존하는지 (8.2절·D-10)

---
*작성: 마케팅팀, 2026-08-05 (1차 개정). 본 문서는 절차서이며 마케팅팀은 어떤
단계도 실행하지 않았다(계정·DNS·저장소·배포·등록 전부 사용자 실행 사항).
0절 데이터 라이선스 리스크는 사용자가 인지하고 선택한 사항으로 기록한다.*
