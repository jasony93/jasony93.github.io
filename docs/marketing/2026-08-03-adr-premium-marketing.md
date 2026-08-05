# ADR 프리미엄 트래커 — SEO·수익화 전략 (공개 런칭 대비)

## 이력

| 날짜 | 내용 |
|---|---|
| 2026-08-03 | 최초 작성 (마케팅팀: 키워드·수요 조사, SEO 전략, 유입 채널, 수익화 전략, 결정 필요 사항) |
| 2026-08-04 | 관리자 정정: 2.3절 메인 title 템플릿에서 "실시간" 삭제 - 데이터가 일별 종가(EOD)라 과장 표기에 해당 (테스트 리포트 2026-08-04 FAIL #3 판정. 구현 코드의 "추적" 표기가 정확) |

참조 문서: `docs/PROJECT.md`, `docs/planning/2026-08-03-adr-premium-prd.md`(1절 시장
조사 승계), `docs/development/2026-08-03-adr-premium-design.md`.
검색량 수치는 본 조사에서 직접 확인할 수 없었으므로(네이버 검색광고·구글 키워드
플래너는 계정 로그인 필요) 모든 규모 판단은 "추정"이며, 근거는 뉴스 보도량·커뮤니티
언급·경쟁 서비스 존재로 갈음했다.

---

## 1. 수요 조사

### 1.1 수요의 구조 (기획팀 조사 승계 + 추가 확인)

기획팀 PRD 1절이 이미 확인한 사실(SKHY 상장 후 프리미엄 3% -> 51% -> 축소가 연일
헤드라인, 개인투자자가 프리미엄을 매매 판단에 사용, 계산법을 어려워함)에 더해,
마케팅 관점에서 다음을 추가 확인했다.

1. **수요는 뉴스 사이클에 강하게 연동된다.** 프리미엄이 급등/급락할 때마다 기사가
   쏟아지고(헤럴드경제, 서울경제, 파이낸셜뉴스 등), 그때 검색이 몰린다.
   "역김치 프리미엄"이라는 신조어까지 등장했다(서울경제 국문·영문 기사 모두 사용).
   - https://www.sedaily.com/article/20069098 ("역김치 프리미엄 25%")
   - https://en.sedaily.com/finance/2026/07/20/sk-hynix-adr-holds-25-percent-reverse-kimchi-premium-as
   - https://en.sedaily.com/international/2026/07/27/half-price-in-korea-sk-hynix-adr-draws-warning-as-premium
2. **커뮤니티에서 실제로 화제다.** 디시인사이드 한국주식 마이너갤러리·실시간 베스트에
   ADR 관련 글이 올라오고, Threads·인스타그램에 프리미엄 수치 공유/계산법 설명
   게시물이 유통된다.
   - https://gall.dcinside.com/mgallery/board/view/?id=krstock&no=2539148 (하닉 ADR / 삼성전자)
   - https://gall.dcinside.com/board/view/?id=dcbest&no=444612 (SK하이닉스 ADR 14% 상승 출발 - 실베)
   - https://www.threads.com/@kayros7777/post/Da1AMyQExS6/ (프리미엄 50% 수준 확대 해설)
   - https://www.instagram.com/p/DaycoZ6zpTL/ ("본주-ADR 괴리율, 상한가로도 못 메운다")
3. **개인들이 직접 도구를 만들 만큼 수요가 검증됐다.** skhypremium.com 외에도
   개인 제작 추적기(GitHub SKHY-Monitor), 블로그 계산법 해설(monheca.com),
   블로그형 계산기(newskurly.com)가 난립 중이다. "도구가 여럿 생긴다 = 검색 수요가
   있다"는 방증이다.
   - https://github.com/cjLee-cmd/SKHY-Monitor
   - https://monheca.com/sk%ED%95%98%EC%9D%B4%EB%8B%89%EC%8A%A4-skhy-%EA%B4%B4%EB%A6%AC%EC%9C%A8-%EB%9C%BB%EA%B3%BC-%EA%B3%84%EC%82%B0%EB%B2%95-%EB%82%B4%EC%9D%BC-%EA%B5%AD%EB%82%B4-%EC%A3%BC%EA%B0%80-%EB%AF%B8%EB%A6%AC/
4. **삼성전자 쪽 수요는 "야간 시세" 성격이 강하다.** "밤새 런던/프랑크푸르트 GDR을
   보며 내일 삼성전자 시초가를 가늠한다"는 보도가 있고, 이 수요를 노린 사이트가 이미
   2개 이상 운영 중이다(yasun.gg, sonmul.co.kr). 우리 MVP는 일별 종가 기반이라 이
   수요를 완전히 흡수하진 못하지만, "삼성전자 GDR 프리미엄"이라는 인접 키워드는
   잡을 수 있다 (1.4절 경쟁 분석 참고).
   - https://www.sedaily.com/article/20047550 ("GDR... 독일·런던장 먼저 본다")
   - http://www.iminju.net/news/articleView.html?idxno=163650 ("런던 삼성전자 챙겨본다")
5. **영어권 수요도 확인된다.** TSMC ADR 프리미엄은 Bogleheads 스레드·GitHub 분석
   리포지토리·Substack 글("don't buy TSM ADRs")이 있을 만큼 오래된 관심사이고,
   SK하이닉스 프리미엄은 Yahoo Finance·Benzinga 등 영문 매체가 다루고 있다.
   - https://www.bogleheads.org/forum/viewtopic.php?t=461211
   - https://github.com/chungderson/tsmc-adr-premium
   - https://brosef.substack.com/p/6-dont-buy-tsm-adrs
   - https://finance.yahoo.com/markets/stocks/articles/sk-hynix-share-conversion-mean-005605511.html

### 1.2 타깃 키워드 목록과 우선순위

검색량 수치는 미확인(도구 접근 불가). 우선순위는 (a) 뉴스·커뮤니티 언급 빈도
(b) 경쟁 서비스/콘텐츠 존재 (c) 우리 제품과의 적합도를 종합한 정성 판단(추정)이다.
용어 관찰: 언론은 "프리미엄", 커뮤니티·블로그는 "괴리율"도 많이 쓴다. 둘 다 잡는다.

**1군 (핵심 - 종목 상세 페이지가 랜딩)**

| 키워드 | 언어 | 근거 |
|---|---|---|
| SK하이닉스 ADR 프리미엄 | 한 | 뉴스 헤드라인 다수(헤럴드·서울경제·fn 등), 경쟁 사이트 도메인명 자체가 이 키워드 |
| 하이닉스 ADR 괴리율 / SKHY 괴리율 | 한 | 블로그(monheca)·개인 추적기(SKHY-Monitor)·hlkr.co.kr 페이지 제목이 "괴리율" 사용 |
| SKHY 주가 / SK하이닉스 미국 주가 | 한 | 증권플러스·토스·인베스팅이 상위 - 시세 자체는 대형 포털이 장악(추정). "환산/프리미엄" 수식어 조합을 노림 |
| SK하이닉스 ADR 환산 (원주 환산가) | 한 | Threads 계산법 게시물 유통, "1주에 얼마야?" 기사 존재 - 계산을 어려워하는 수요 직접 증거 |
| 삼성전자 GDR / 삼성전자 런던 주가 | 한 | yasun.gg·sonmul.co.kr가 이 수요로 운영 중, 보도 다수 |
| TSMC ADR 프리미엄 / TSM 2330 비교 | 한·영 | Bogleheads·GitHub·Apify(중단됨) - 영어권 수요가 구조적, 한국어 콘텐츠는 희소(추정) |
| TSMC ADR premium (영) | 영 | 상동. 영문 UI 전 단계에서도 영문 메타·콘텐츠로 일부 흡수 가능 |
| 역김치 프리미엄 | 한 | 서울경제 국·영문 기사에서 사용된 신조어. 경쟁 밀도 낮을 때 선점 가치(추정) |

**2군 (보조 - 정보성 콘텐츠 페이지가 랜딩)**

| 키워드 | 언어 | 근거 |
|---|---|---|
| ADR 프리미엄이란 / ADR이란 | 한 | KB증권 콘텐츠·tradingkey 해설 등 정보성 수요 확인 |
| ADR 괴리율 계산법 / 계산기 | 한 | newskurly 계산기, monheca 계산법 글 존재 |
| ADR 원주 전환 (상호전환) | 한 | 전환 개시(7/29) 관련 보도 다수, 전환비율·기간·수수료 질문 수요(추정) |
| 삼성전자 야간 시세 | 한 | sonmul.co.kr·yasun.gg가 타깃 중. 우리는 일별 종가라 부분 적합 - 콘텐츠로 우회 흡수 |
| Korean ADR premium / Korea ADR discount | 영 | 서울경제 영문판 기사, S&P Korea ADR Index(^BKKR) 존재 |
| KB금융/신한지주/POSCO ADR (개별) | 한·영 | 검색량 낮을 것(추정)이나 경쟁 부재 - 롱테일로 종목 페이지가 자동 커버 |

**3군 (지켜볼 것)**

- "SK하이닉스 ADR 전환" 물량/한도 관련: 전환한도 소진 이슈가 보도됨(Yahoo Finance).
  부가 지표(전환한도)는 2차 범위라 지금은 콘텐츠(글)로만 대응.
- "코스피 야간선물", "하이닉스 야간 시세": 실시간 야간 데이터가 필요해 MVP 범위 밖.
  2차 논의 후보(사용자 재문의 필수 - PRD 4절).

### 1.3 검색량 확인 방법 (관리자 실행 필요)

네이버 검색광고(searchad.naver.com) 키워드도구와 Google Keyword Planner는 계정이
필요해 이번 조사에서 실측하지 못했다. 런칭 전 관리자(또는 사용자) 계정으로 1군
키워드의 월간 조회수를 실측해 이 문서를 갱신할 것을 권고한다. 무료 보조 도구로
구글 트렌드(trends.google.com)에서 "SK하이닉스 ADR" 급등 시점 확인 가능.

### 1.4 경쟁 서비스 분석 (유입 채널·수익 모델)

| 서비스 | 내용 | 유입 채널(관찰) | 수익 모델(관찰) | 대비 우리 강점 |
|---|---|---|---|---|
| skhypremium.com | SKHY 단일, 실시간 프리미엄+기간 차트, 영/한 | Vercel 커뮤니티 쇼케이스 게시 확인, 도메인=키워드(EMD)로 검색 유입(추정) | 미확인 (Vercel Hobby 플랜으로 운영 언급 - 저비용 개인 프로젝트로 추정) | 11종목, 계산 근거 투명성, 장기 히스토리 |
| hlkr.co.kr/adr | SKHY 괴리율 + 24시간 perp 가격 연계 | 검색(추정). 직접 확인 실패(HTTP 403) - 검색 결과 스니펫 기반 | 미확인 | 정규 시장 데이터 기반 신뢰성, 멀티 종목 |
| yasun.gg | 삼성전자 런던 GDR 실시간 차트·야간 환산 시세 (야간선물 사이트의 하위 기능) | 검색(추정: "삼성전자 GDR/야간 시세" 계열). 직접 확인 실패(HTTP 403) | 미확인 | 프리미엄 계산·히스토리 관점은 우리가 유일(추정) |
| sonmul.co.kr | 코스피 야간선물 대시보드 + 프랑크푸르트 GDR 1분봉 KRW 환산 | 검색(추정) | 미확인 | 상동 |
| newskurly.com | 블로그형 SKHY 계산기 | 검색(블로그 SEO) | 블로그 광고(추정) | 차트·히스토리·멀티 종목 |
| 증권플러스·토스·인베스팅 | SKHY 시세 페이지 | 브랜드·앱 | 자체 사업 | "시세" 키워드는 이들이 장악(추정) - 우리는 "프리미엄/괴리율/환산" 키워드에 집중 |

시사점:
- "SKHY 프리미엄" 단일 키워드는 이미 경쟁자가 있으나, **"전 종목 + 히스토리 + 계산
  근거 투명성"을 가진 곳은 없다** (PRD 1.2절 결론 유지 - 이번 조사에서도 반증 없음).
- 경쟁 사이트들이 대부분 개인 프로젝트 수준이라 콘텐츠 SEO(정보성 글, 구조화
  데이터)를 거의 안 하고 있을 것(추정) - 콘텐츠+기술 SEO로 추월 여지가 있다.
- 도메인명이 키워드인 경쟁자(skhypremium.com)가 있으므로, 우리도 기억하기 쉽고
  키워드 연관성 있는 도메인이 필요하다 (5절 결정 사항).

---

## 2. SEO 전략

### 2.1 구조적 문제: 해시 라우팅은 SEO에 불리한가 -> 그렇다 (치명적)

현 구현(설계 문서 2절)은 `#/SKHY` 해시 라우팅 단일 페이지다. 검색엔진은 URL의
해시 프래그먼트를 별도 페이지로 취급하지 않으므로, **구글·네이버에는 사실상
"페이지 1개"만 존재**하게 된다. 종목별 키워드(1군 대부분)가 각자의 랜딩 페이지를
가질 수 없어 1절의 키워드 전략 전체가 무력화된다. 또한 현재 데이터가 클라이언트
fetch로만 렌더되므로 초기 HTML에 콘텐츠(프리미엄 수치·종목명)가 없어, JS 렌더링
의존도가 높은 네이버 검색에서 특히 불리하다(네이버의 JS 렌더링 수집은 구글보다
제한적이라는 것이 통설 - 추정).

**해결 권고: 정적 페이지 사전 생성(prerender).** 이미 Python 파이프라인이 정적
JSON을 생성하는 구조이므로, 같은 파이프라인이 종목별 HTML 11개 + 메인 1개를 함께
찍어내는 것이 가장 작은 변경이다(SSR 서버·프레임워크 도입 불필요, "의존성 0" 원칙
유지 가능). 초기 HTML에 종목명·현재 프리미엄·계산 근거 4종·안내 문구가 텍스트로
포함되어야 한다. 차트·인터랙션은 기존 app.js가 그대로 담당하면 된다.
구체 구현 항목은 2.6절(개발팀 목록) 참고.

### 2.2 URL 구조 (권고안)

```
/                    메인 (카드 그리드)
/stocks/skhy/        SK하이닉스 상세   (소문자 DR 티커 기반)
/stocks/smsn/        삼성전자 GDR 상세
/stocks/tsm/         TSMC 상세
... (11종목 동일 패턴)
/guide/adr-premium/  "ADR 프리미엄이란" 정보성 페이지 (2.5 콘텐츠)
/guide/adr-conversion/  "ADR 원주 전환 안내" 정보성 페이지
```

- 티커 기반 경로: 짧고, 영문 확장 시에도 그대로 쓸 수 있다. 한글 슬러그
  (`/sk하이닉스/`)는 인코딩 문제 대비 이득이 적어 비권고.
- 기존 해시 URL(`#/SKHY`)은 새 경로로 JS 리다이렉트 처리(공유된 구링크 대비).
- trailing slash 여부는 개발팀이 호스팅 환경에 맞춰 한쪽으로 통일(중복 URL 방지,
  canonical 명시).

### 2.3 페이지 제목·메타 설명 (템플릿 + 예시)

원칙: 제목 앞부분에 1군 키워드, "프리미엄"과 "괴리율" 병기, 숫자(현재 프리미엄)는
메타 설명에 넣어 클릭 유도. 제목은 빌드 시점 데이터로 갱신하지 않는다(검색 결과
스냅샷과 불일치 방지). 사이트명은 도메인 확정 후 치환(아래에서는 `[사이트명]`).

| 페이지 | title (약 30자 내) | meta description (약 80자 내) |
|---|---|---|
| 메인 | 한국·대만 ADR 프리미엄 추적 - [사이트명] | SK하이닉스 SKHY, 삼성전자 GDR, TSMC 등 11종목의 ADR 프리미엄(괴리율)을 계산 근거와 함께 매일 차트로 보여드립니다. |
| SKHY | SK하이닉스 ADR 프리미엄(SKHY 괴리율) 차트 - [사이트명] | SKHY와 원주(000660) 간 프리미엄을 가격·환율·전환비율(10:1) 근거와 함께 계산. 원주 환산가와 일별 추이 차트 제공. |
| SMSN | 삼성전자 GDR(SMSN) 프리미엄 차트 - 런던 시세 환산 - [사이트명] | 런던 상장 삼성전자 GDR(1주=보통주 25주)의 원주 대비 프리미엄을 매일 계산. 계산 근거와 히스토리 차트 제공. |
| TSM | TSMC ADR 프리미엄(TSM vs 2330) 차트 - [사이트명] | TSM과 대만 원주 2330 간 프리미엄(ADR 1주=원주 5주)을 환율 근거와 함께 계산. 장기 히스토리 차트 제공. |
| 기타 8종 | [기업명] ADR 프리미엄([티커] 괴리율) 차트 - [사이트명] | 동일 템플릿: 전환비율 명시 + "계산 근거·일별 차트" 문구 |
| 가이드 | ADR 프리미엄(괴리율)이란? 계산법과 해석 - [사이트명] | 수식·전환비율·환율·기준시점까지, ADR가 원주보다 비싸지는 이유와 계산법을 예시로 설명합니다. |

- OG 태그(og:title/description/image)도 동일 내용으로. 커뮤니티 공유 시 미리보기가
  유입률을 좌우한다. 종목별 OG 이미지(차트 스냅샷)는 있으면 좋으나 2차로 미뤄도 됨.

### 2.4 구조화 데이터·기술 SEO

| 항목 | 내용 |
|---|---|
| JSON-LD `WebSite` + `Organization` | 메인에 사이트명·URL 명시 |
| JSON-LD `BreadcrumbList` | 종목 상세: 홈 > 종목명 |
| JSON-LD `FAQPage` | 가이드 페이지의 Q&A(프리미엄이란/왜 생기나/괴리율과 차이)에 한정 적용. 남용 시 리치결과 제외 위험이 있어 종목 페이지에는 넣지 않음 |
| sitemap.xml / robots.txt | 파이프라인이 페이지 생성 시 함께 생성 |
| canonical | 전 페이지 자기 참조 canonical |
| 서치콘솔 등록 | Google Search Console + **네이버 서치어드바이저** (한국어 수요의 상당 부분이 네이버 검색 - 추정. 사이트 소유 확인·sitemap 제출) - 실행은 관리자 |
| 성능 | 의존성 0 정적 페이지라 Core Web Vitals는 이미 유리. 프리렌더 시 초기 콘텐츠 페인트도 개선됨 |
| hreflang | 영문 버전 도입 시(2차) ko/en 상호 지정 |

### 2.5 콘텐츠 전략

1. **종목 상세 = 키워드 랜딩** (1군): 프리렌더된 HTML에 프리미엄 수치, 계산 근거
   4종, 수식 설명, "이월가" 등 용어 설명이 텍스트로 존재해야 한다. 현 UI의 수식
   안내 섹션(PRD 3.1)이 그대로 SEO 콘텐츠 역할을 한다 - 추가 집필 비용이 거의 없다.
2. **가이드 페이지 2~3개** (2군, 마케팅팀이 초안 집필 가능):
   - "ADR 프리미엄(괴리율)이란" - 계산법·왜 생기나·역김치 프리미엄 용어 설명
   - "ADR 원주 상호전환 안내" - 전환비율 표(11종목, PRD 3.0절 1차 출처 인용)·기간·
     한도 개념. SEC·예탁은행 출처를 명시하면 경쟁 블로그 대비 신뢰성 우위.
   - (선택) "삼성전자를 밤에 보는 법 - GDR 이해하기" - 야간 시세 수요를 우회 흡수
3. **영문 대응(경량)**: 영문 UI는 2차이지만, TSM·Korea ADR 영어 수요가 확인되므로
   가이드 1개("Korean ADR premium explained")의 영문판만 먼저 내는 것을 2차 초입에
   검토. (구현 부담과 hreflang 필요 - 지금은 하지 않음)
4. **주의(법규)**: 모든 콘텐츠는 정보 제공에 한정하고 매수/매도 판단 표현 금지.
   "투자 조언 아님" 고지 유지(이미 구현됨). 유사투자자문업 오인 소지를 만들지 않는다.

### 2.6 개발팀 구현 필요 항목 (관리자가 개발팀에 전달)

우선순위순. D1~D5가 공개 런칭 전 필수라고 판단한다.

| # | 항목 | 내용 | 우선도 |
|---|---|---|---|
| D1 | 정적 페이지 사전 생성 | 해시 라우팅 -> 경로 기반(2.2절). 파이프라인이 메인 1 + 종목 11 + 가이드 페이지 HTML 생성, 초기 HTML에 핵심 텍스트 포함. 기존 해시 URL은 새 경로로 리다이렉트 | 필수 |
| D2 | 페이지별 title·meta·OG·canonical | 2.3절 템플릿 적용 | 필수 |
| D3 | sitemap.xml·robots.txt 자동 생성 | 파이프라인에 통합 | 필수 |
| D4 | JSON-LD 구조화 데이터 | 2.4절 표 범위 | 필수 |
| D5 | 데이터 자동 갱신 스케줄 | 일 1회 이상 자동 재수집·재배포(GitHub Actions cron 등). 갱신이 멈춘 사이트는 신뢰·재방문·검색 순위 모두 잃는다 | 필수 |
| D6 | 방문 분석 도구 부착 | GA4 또는 경량 대안(Cloudflare Web Analytics 등). 키워드 성과 측정에 필요 | 권장 |
| D7 | 종목별 OG 이미지 생성 | 차트 스냅샷 이미지. 공유 클릭률 개선 | 2차 |
| D8 | 광고 슬롯 영역 | 수익화 모델 확정 후(3절). 레이아웃 침해 없는 위치 협의 | 승인 후 |
| D9 | 영문 페이지·hreflang | 2차 범위 논의와 함께 | 2차 |

(참고: 상업 데이터 API 전환은 SEO 항목이 아니라 공개 런칭 전제 조건이며 PRD 6절-1·2
에서 이미 추적 중이다. 3.3절 손익에 반영.)

---

## 3. 수익화 전략

### 3.1 모델 비교

| 모델 | 장점 | 단점 | 현 단계 적합성 |
|---|---|---|---|
| 디스플레이 광고 (구글 애드센스) | 즉시 시작 가능, 트래픽만 있으면 수익. 금융 주제는 단가 높은 편(금융 니치 RPM $10~50 주장 자료 있음 - 콘텐츠 사이트 기준, 도구 사이트는 그보다 낮을 것으로 추정) | 도구성 페이지는 체류 짧고 광고 클릭률 낮음(추정). 저트래픽 초기엔 소액. 심사 통과 필요(콘텐츠 페이지가 있어야 유리) | **1순위 시작점**. 가이드 페이지(2.5)와 병행하면 심사·단가 모두 유리 |
| 카카오 애드핏 등 국내 광고망 | 심사 상대적으로 용이(추정), 국내 트래픽 최적 | 단가 일반적으로 애드센스보다 낮음(추정) | 애드센스 보조/대체로 검토 |
| 제휴 - 증권사 계좌개설 CPA | 타깃(주식 투자자)과 완벽히 일치, 건당 단가 높음(리더스CPA 등 국내 제휴 플랫폼 존재: https://leaderscpa.com/leaderscpa/m/sub/service.asp ) | 금융상품 광고는 금소법상 심의·표기 의무 등 규제 확인 필요. 제휴 플랫폼별 금융 캠페인 유무·조건 미확인 | 트래픽 확보 후 2단계. 규제 검토 선행 필수 |
| 쿠팡 파트너스 등 일반 제휴 | 진입 쉬움 | 타깃 부적합(주식 도구 방문자에게 일반 상품), 수익 미미 예상(추정) | 비권고 |
| 프리미엄 구독 (알림·고급 기능) | 반복 수익, 광고 무관 | 결제할 만한 기능(프리미엄 임계값 알림, 실시간, API)이 전부 2차 범위 밖. 계정·결제 인프라 필요 | 3단계(장기). 2차 기능 논의 시 함께 |
| 후원 (Buy Me a Coffee 등) | 구현 비용 0 | 수익 미미(추정) | 초기 병행 가능 (부담 없음) |
| 데이터 API 판매 | 차별화 데이터 자산 활용 | 데이터 원천이 상업 API 재배포 계약 조건에 묶임 - 재판매는 별도 라이선스 필요 가능성 높음(추정) | 장기 검토만 |

### 3.2 단계별 실행안 (트래픽 규모 연동)

트래픽 기준은 페이지뷰(PV)/월. 수치는 전부 추정 기준선이다.

- **0단계 - 런칭 준비 (현재)**: 수익 장치 없음. 무료 정적 호스팅(GitHub Pages/
  Cloudflare Pages 등)으로 비용 0원 유지. 단, **공개 런칭 자체가 상업 데이터 API
  전환(PRD 6절-1·2)에 막혀 있다** - 회사 목적이 수익화이므로 무광고 공개도 yfinance
  약관 위험을 안고 갈 수 없다. 데이터 예산 승인이 런칭의 선행 조건.
- **1단계 - 런칭 ~ 월 1만 PV**: 애드센스 신청·부착(가이드 페이지 갖춘 뒤), 후원
  버튼. 목표는 수익보다 검색 순위 안착과 재방문 확보. SKHY 프리미엄 뉴스 사이클이
  살아있는 동안 진입하는 것이 중요(1.1절-1).
- **2단계 - 월 1만~10만 PV**: 광고 배치 최적화, 증권사 계좌개설 CPA 제휴 검토
  (규제 확인 후), 영문 콘텐츠로 TSM 트래픽 확장.
- **3단계 - 월 10만 PV 이상 또는 뚜렷한 재방문층**: 프리미엄 알림 등 유료 기능을
  2차 범위 논의(사용자 재문의 필수)와 함께 설계.

### 3.3 손익 추산 - 상업 API 비용을 언제 상쇄하나 (전부 추정)

- 고정비(추정): 상업 데이터 API 월 $30~100+(PRD 6절-1) + 도메인 연 1~3만원
  + 호스팅 0원(정적) = **월 약 $32~105**.
- 광고 수익 가정: 도구성 페이지 중심 사이트의 페이지 RPM을 보수적으로
  **$2~5**로 가정(금융 콘텐츠 니치 RPM $10~50 주장 자료(
  https://www.ranktracker.com/ko/blog/understanding-rpm-revenue-per-mille-in-adsense-what-it-means-and-how-to-optimize-it/ ,
  국내 블로그들은 금융·IT 주제 RPM 1만~3만원 언급)가 있으나 이는 검색형 콘텐츠
  기준이라, 체류가 짧은 도구 페이지는 하향 적용 - 추정).
- 손익분기 PV(월):
  - 비용 $32/월 (API $30 하한): RPM $5 -> 약 6,400 PV, RPM $2 -> 약 16,000 PV
  - 비용 $105/월 (API $100 상향): RPM $5 -> 약 21,000 PV, RPM $2 -> 약 52,500 PV
- 해석: **월 1만~2만 PV(일 350~700 PV)** 수준이면 하한 예산의 API 비용을 상쇄할
  수 있다(추정). SKHY 프리미엄 이슈의 보도량·커뮤니티 화제성을 볼 때 뉴스 사이클
  내 진입 시 도달 가능한 범위로 판단하나, 근거 수치가 없으므로 1단계에서 실측
  (D6 분석 도구)으로 검증한다. 이슈가 식으면(프리미엄 수렴 후) 트래픽이 급감할
  리스크가 있으므로, 고정비는 하한($30대 API)에서 시작하는 것을 권고.

---

## 4. 실행 계획 (승인 필요 항목 구분)

### 4.1 유입 채널 계획 (검색 외, 무비용 우선)

실행은 전부 관리자·사용자 승인 후 별도 진행한다. 마케팅팀은 계획까지만.

| 채널 | 계획 | 비용 | 비고 |
|---|---|---|---|
| 커뮤니티 (디시 한국주식 마이너갤·주갤, 클리앙, 뽐뿌 재테크, 에펨코리아 주식판, 네이버 카페) | 프리미엄 급변 시점에 "전 종목 프리미엄 현황 + 계산 근거" 스크린샷과 링크를 정보성 글로 공유. 노골적 홍보 금지 규정이 있는 곳이 많으므로 각 커뮤니티 규칙 확인 후, 데이터 인용 중심으로 | 0 | 승인 필요. 뉴스 사이클 타이밍이 핵심 |
| Threads / X | 일별 프리미엄 요약 카드(이미지) 정기 게시용 계정 운영. 이미 Threads에서 계산법 게시물이 화제가 된 전례(1.1절-2)가 포맷 검증 | 0 | 계정 개설은 실행 - 승인 필요 |
| Reddit (r/stocks, r/Semiconductors 등) | TSM 프리미엄 데이터 인용 코멘트 수준. 서브레딧 자기홍보 규칙 엄격 - 링크 스팸 금지 | 0 | 영문 페이지 준비 후 |
| GitHub | 계산 방법론 공개 문서(수식·출처)를 공개 리포지토리로 - 개발자·퀀트층 백링크 확보. skhypremium이 Vercel 쇼케이스로 노출된 것과 유사한 경로 | 0 | 공개 범위는 관리자 결정 |
| 언론 인용 유도 | 프리미엄 데이터가 필요한 기자들이 인용할 수 있게 "출처 표기 조건 자유 인용" 문구 게시. 헤드라인이 반복되는 주제라 인용 기회가 많음(추정) | 0 | 문구만 - 즉시 가능 |
| 유료 광고 (검색·SNS) | 현 단계 비권고 - 무료 채널·SEO 성과 실측 후 재논의 | - | - |

### 4.2 단계별 체크리스트

1. [승인 대기] 도메인·데이터 API 예산·런칭 시점 결정 (5절)
2. [개발팀] D1~D5 구현 (2.6절) + 상업 API 전환 (PRD 6절)
3. [마케팅팀] 가이드 페이지 원고 2편 집필, 키워드 검색량 실측 후 본 문서 갱신
4. [관리자] 서치콘솔·서치어드바이저 등록, 애드센스 신청 (계정 주체 결정 필요)
5. [승인 후 실행] 커뮤니티·SNS 채널 개시 (4.1)

---

## 5. 관리자·사용자 결정 필요 사항

| # | 결정 사항 | 선택지·권고 |
|---|---|---|
| 1 | **도메인** | 키워드 연관+확장성 고려. 후보 예: adrpremium.kr / drpremium.com / (확장 대비 일반명) 등 - 가용성 미확인, 등록 전 확인 필요. 연 1~3만원. 첫 제품 키워드에 완전 종속되는 이름(skhy 계열)은 확장성 때문에 비권고 |
| 2 | **데이터 API 예산 상한** (PRD 6절-1 재청구) | 권고: 하한($30대/월)에서 시작. 3.3절 손익분기 추산 참고. 이 결정 없이는 공개 런칭 불가 |
| 3 | **런칭 시점** | 권고: 가능한 한 빨리. SKHY 프리미엄 뉴스 사이클(현재 진행형)이 최대 유입 기회이며, 식은 뒤에는 초기 견인이 훨씬 어려움(추정) |
| 4 | 삼성전자 GDR(LSE) 시세 재배포 라이선스 확인 (PRD 6절-2 재청구) | 미해결 시 대안: 삼성전자 페이지만 "참고 지표" 수준으로 축소 또는 일시 제외 - 상세 옵션은 라이선스 확인 결과 후 |
| 5 | 애드센스·분석 도구 계정 주체 | 회사(사용자) 계정으로 개설 필요 - 마케팅팀이 대행 불가 |
| 6 | 커뮤니티·SNS 실행 승인 | 4.1절 채널별 개시 여부와 계정 운영 주체 |
| 7 | 영문 대응 시점 | 2차 범위 논의(사용자 재문의 필수)와 함께. TSM 영어 수요 근거는 1.1절-5 |

---

## 부록: 조사 출처 전체 목록

뉴스·시장 상황:
- https://biz.heraldcorp.com/article/10817177 (ADR 프리미엄에 개미들 고심)
- https://biz.heraldcorp.com/article/10822793 (동 후속)
- https://biz.heraldcorp.com/article/10809827 (상장 사흘만에 51%)
- https://www.sedaily.com/article/20069098 (역김치 프리미엄 25%)
- https://www.sedaily.com/article/20047550 (GDR 독일·런던장 먼저 본다)
- https://en.sedaily.com/finance/2026/07/20/sk-hynix-adr-holds-25-percent-reverse-kimchi-premium-as
- https://en.sedaily.com/international/2026/07/27/half-price-in-korea-sk-hynix-adr-draws-warning-as-premium
- https://www.fnnews.com/news/202607261031099815 (서학개미 7300억 매수)
- https://v.daum.net/v/BD9GhWvmoB , https://v.daum.net/v/zydKgr3GXe
- http://www.iminju.net/news/articleView.html?idxno=163650
- https://kr.investing.com/news/stock-market-news/article-2015570
- https://finance.yahoo.com/markets/stocks/articles/sk-hynix-share-conversion-mean-005605511.html
- https://kbthink.com/investment/issues/sk-hynix-nasdaq-adr.html
- https://www.tradingkey.com/kr/analysis/stocks/us-stocks/262053818-skhynix-dram-mu-tsm-skhy-sndk-nvda-samsung-tradingkey

커뮤니티·SNS:
- https://gall.dcinside.com/mgallery/board/view/?id=krstock&no=2539148
- https://gall.dcinside.com/board/view/?id=dcbest&no=444612
- https://www.threads.com/@kayros7777/post/Da1AMyQExS6/
- https://www.threads.com/@marketmentorhd/post/DaueYh5HaEj/
- https://www.instagram.com/p/DaycoZ6zpTL/
- https://www.bogleheads.org/forum/viewtopic.php?t=461211
- https://brosef.substack.com/p/6-dont-buy-tsm-adrs

경쟁·유사 서비스:
- https://www.skhypremium.com/
- https://community.vercel.com/t/showcase-skhy-premium-real-time-adr-premium-calculator-for-korean-stock-investors/46605
- https://hlkr.co.kr/adr (직접 확인 실패 - HTTP 403, 검색 스니펫 기반)
- https://yasun.gg/samsung-gdr , https://yasun.gg/samsung-night (직접 확인 실패 - HTTP 403, 검색 스니펫 기반)
- https://sonmul.co.kr/overnight/SAMSUNG
- https://newskurly.com/sk%ED%95%98%EC%9D%B4%EB%8B%89%EC%8A%A4-adr-%EA%B4%B4%EB%A6%AC%EC%9C%A8-%EA%B3%84%EC%82%B0%EA%B8%B0/
- https://monheca.com/sk%ED%95%98%EC%9D%B4%EB%8B%89%EC%8A%A4-skhy-%EA%B4%B4%EB%A6%AC%EC%9C%A8-%EB%9C%BB%EA%B3%BC-%EA%B3%84%EC%82%B0%EB%B2%95-%EB%82%B4%EC%9D%BC-%EA%B5%AD%EB%82%B4-%EC%A3%BC%EA%B0%80-%EB%AF%B8%EB%A6%AC/
- https://github.com/cjLee-cmd/SKHY-Monitor
- https://github.com/chungderson/tsmc-adr-premium
- https://apify.com/quiet_dictionary/taiwan-adr-premium-tracker (중단됨)
- https://www.stockplus.com/m/stocks/USA-SKHY , https://www.tossinvest.com/stocks/NAS2607010002/order , https://kr.investing.com/equities/sk-hynix-adr

수익화 참고:
- https://www.ranktracker.com/ko/blog/understanding-rpm-revenue-per-mille-in-adsense-what-it-means-and-how-to-optimize-it/
- https://adsensefarm.kr/%EC%95%A0%EB%93%9C%EC%84%BC%EC%8A%A4-%EA%B4%91%EA%B3%A0-%EB%8B%A8%EA%B0%80-%EC%98%AC%EB%A6%AC%EA%B8%B0-rpm-cpc-%EB%8B%A8%EA%B0%80-10%EB%B0%B0-%EC%98%AC%EB%A6%AC%EB%8A%94-%EA%BF%80%ED%8C%81/
- https://leaderscpa.com/leaderscpa/m/sub/service.asp
- https://www.shopify.com/kr/blog/cpa-marketing

---
*작성: 마케팅팀, 2026-08-03. 검색량·RPM·트래픽 수치는 실측 도구 미접근으로 전부
추정이며, 런칭 전 네이버 검색광고·키워드 플래너 실측으로 갱신 예정. 본 문서는
전략 계획이며 광고 집행·계정 생성·외부 게시 등 실행을 포함하지 않는다.*
