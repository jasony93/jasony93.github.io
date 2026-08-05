# 거래량 UX 개선·배포 선행 작업(D-1~D-7) 테스트 리포트

## 이력

| 날짜 | 회차 | 결과 요약 |
|---|---|---|
| 2026-08-05 | 1차 | PASS 32 / FAIL 0 / BLOCKED 2. 거래량 UX(26항목)·배포 D-1~D-7(40+8항목) 전부 실행 검증 통과. BLOCKED 2건은 (1) D-2 워크플로 실제 실행(저장소 미생성 - 지시상 BLOCKED 처리) (2) 브라우저 실조작(도구 미가용, 3회차 연속) |

## 1. 테스트 대상

- 거래량 UX: `src/web/app.js` (기본 시리즈 local 전환, 버튼 순서, highlightVolBar 호버 연동, 포커스 링, 툴팁 등락 표기)
- 배포 준비: `.gitignore`(D-1), `.github/workflows/update-data.yml`(D-2), `src/config/site.json`(D-3~D-6 설정), `src/build_pages.py`(D-4~D-6 주입·고지), `src/scripts/check_deploy.py`(D-7)
- 판정 기준: `docs/marketing/2026-08-05-deployment-guide.md` 10절(D-1~D-7 요구)·6절(고지 문안), 설계 문서 최신 이력
- 참고: 절차서 3·5·7절의 사용자 조치 항목(Pages Source 설정, base_url 실값 교체, 소유확인 토큰 기입)은 개발팀 범위 밖 - 본 검증은 "값이 들어오면 올바르게 동작하는가"까지 확인

## 2. 테스트 환경과 실행 방법

- 환경: Windows 11 Home, Python 3.11.9, Node.js v24.18.0. 로컬 정적 서버 2개(8765 기존, 8799 서브경로 픽스처). 실행 시각 2026-08-05 12:10~12:50 KST
- 실행 절차:
  1. `python -m unittest discover -s src/tests` (97건) + `node src/tests/test_panning.mjs` (14케이스)
  2. `docs/testing/scripts/2026-08-05-qa-volhover.cjs` - 출하 app.js를 Node로 로드해 drawVolumePanel·highlightVolBar·attachTooltip을 실데이터로 실행 (표본 SHG DR·WF 원주·BABA 이월 구간·PKX 주 단위 - 개발팀 및 직전 회차와 다른 종목)
  3. `docs/testing/scripts/2026-08-05-qa-deploy-verify.py` - build_all을 **임시 디렉토리**로 호출해 base_url 4형식·서브경로·notices·verification/analytics를 산출물 해시까지 대조 (원본 산출물 미변경)
  4. D-7: site.json base_url을 로컬 서버로 임시 교체·재빌드 -> 정상 점검(FAIL 0 확인) -> **고의 오류 5종 주입**(canonical 변조/데이터 노후화/fetch_error+종목 수 부족/페이지 부재/서브경로) 각각 검출 확인 -> 전부 원상복구·재빌드
  5. 회귀: verify_samples, SEO 96항목, v2 계산 하니스 34항목, HKEX·세션 16항목
- 오류 주입은 전부 원상복구했다. 최종 상태 검증: site.json base_url = 플레이스홀더 복귀, verification·analytics 공란, 메인 canonical 원복, 주입 문자열(wrong.example.org·gTOKEN·localhost) 잔존 0, meta 12종목·fetch_error 0, stocks 페이지 12개, 임시 서버·픽스처 정리 완료. 소스 코드 무수정.

## 3. 항목별 결과

### 3.1 거래량 UX 개선

| # | 테스트 항목 | 절차 | 기대 결과 | 실제 결과 | 판정 |
|---|---|---|---|---|---|
| 1 | 기본 시리즈 = 원주 | app.js state 초기값 + 버튼 배열 검사 | volSeries "local", 버튼 원주 우선 | state.volSeries="local", 배열 [["local","원주"],["dr","DR"]] 순서 확인. 거래량 토글 기본 꺼짐 유지 | PASS |
| 2 | 호버 강조 - 불투명도 (SHG DR·WF 원주 각 15일) | highlightVolBar(idx) 실행 후 전 바 opacity 판독 | 대상 1 / 나머지 0.35 | 2종목 모두 정확 (대상 "1", 나머지 전부 "0.35") | PASS |
| 3 | 포커스 링 기하·스타일 | 링 x/y/width/height를 대상 바 + 패딩 1.5로 독립 계산해 대조 | 대상 바를 감싸고 fill 없음 | 4속성 전부 오차 1e-6 이내 일치, fill="none" + stroke=var(--text) | PASS |
| 4 | 등락 색상 의미 보존 | 강조 대상을 이동시키며 전 바의 fill 값 비교 | 강조로 색이 바뀌지 않음 | 강조 이동 전후 fill 배열 완전 동일 (링은 fill 없음이라 색 위에 덮이지 않음) | PASS |
| 5 | 강조 해제 | highlightVolBar(null) | 전 바 opacity 1 + 링 숨김 | 2종목 모두 정확. 초기 상태에서도 링 숨김 | PASS |
| 6 | 이월 포인트 경계 (BABA 원주) | 이월일 포함 12일 구간 렌더 후 이월 인덱스 강조 | 바 없음(null) + 링 숨김 | volBars[ff]=null, 링 display="none". 나머지 바 감쇠(0.35)는 정상 적용 | PASS |
| 7 | 토글 꺼짐 경계 | 참조 없는 상태(vol=false)에서 highlightVolBar 호출 | 예외 없이 무시 | 예외 미발생 (조기 반환) | PASS |
| 8 | 주/월 집계 바 강조 (PKX 주 10구간) | 주 단위 렌더 후 강조 | 집계 바 수 = 포인트 수, 강조 동작 | 바 배열 = 집계 포인트 수 일치, 링 표시 + 대상 opacity 1 | PASS |
| 9 | 툴팁 거래량·등락 표기 | 실제 좌표계로 mousemove 디스패치 후 툴팁 텍스트 판독 | 거래량 + 전일 종가 대비 등락 | "거래량(원주) 991천 주 · 전일 종가 대비 상승" - 원천 종가 등락과 일치 (집계 시 "직전 기간 대비") | PASS |
| 10 | 호버-거래량 연동 인덱스 | 툴팁이 가리키는 행과 강조 인덱스 대조 | 동일 인덱스 | state.hoverIdx = 툴팁 행 인덱스 일치 (8/8) | PASS |
| 11 | 금지 표현 | 툴팁 텍스트 + app.js 사용자 노출 문자열 + 생성 페이지 grep | "매수/매도 우위·체결강도" 없음 | 툴팁 0건, 사용자 노출 0건 (유일 출현은 금지를 명시한 코드 주석) | PASS |

### 3.2 배포 선행 작업 D-1~D-6

| # | 테스트 항목 | 절차 | 기대 결과 | 실제 결과 | 판정 |
|---|---|---|---|---|---|
| 12 | D-1 .gitignore·데이터 정책 | 파일 검사 + 워크플로 대조 | 데이터 커밋 포함 확정, 근거 기록, 캐시·로그 제외 | `src/web/data` 제외 규칙 없음(커밋 포함) + 정책 근거·크기 주석 기재. `__pycache__`·`update_data.log`·에디터/OS·임시 파일 제외. 워크플로 `git add src/web`과 정합 | PASS |
| 13 | D-2 워크플로 구조 | PyYAML 파싱 + Pages 공식 요구사항 대조 | permissions 3종, job 분리, artifact path src/web, environment, concurrency | 10/10 통과: permissions(contents/pages/id-token: write), job=update+deploy, upload-pages-artifact@v3 path=src/web, deploy job needs=update + environment github-pages + page_url, deploy-pages@v4, concurrency(pages-deploy, cancel-in-progress:false) | PASS |
| 14 | D-2 기존 job 무손상 | 스텝 순서·스케줄 검사 | 데이터 커밋 유지 + 업로드가 커밋 이후 | `git add src/web` 커밋 스텝 유지, 업로드 스텝이 그 뒤에 위치(최신 데이터 배포), 기존 cron 4종 유지 | PASS |
| 15 | D-3 base_url 4형식 | 끝 슬래시 0/1/2개 변형으로 각각 빌드 후 **산출물 17파일 해시 전량 대조** | 완전 동일 | 4형식 해시 100% 동일. 루트 canonical 정상 조합 | PASS |
| 16 | D-4 서브경로 canonical·sitemap | base_url=`https://user.github.io/adr-tracker`로 빌드 | 서브경로 포함 정확 조합 | 메인·종목 canonical 정확, sitemap 15 URL 전부 서브경로, robots Sitemap 절대 URL | PASS |
| 17 | D-4 상대경로 자산·링크 | 메인·종목·가이드 HTML 검사 | 절대경로 미사용 | 메인 `styles.css`/`app.js`, 종목·가이드 `../../styles.css`, data-root="../../", 내부 링크에 루트 절대경로 0건 | PASS |
| 18 | D-4 robots 루트 제약 | site.json 주석 + 점검 스크립트 경고 | 명시돼 있음 | site.json `_base_url_format`에 경고 기재 + check_deploy가 서브경로 감지 시 WARN 출력(#25에서 실측) | PASS |
| 19 | D-5 고지 문안 = 절차서 6절 | 문자열 완전 일치 비교 | 비상업 1줄 + 출처 1줄 | 두 문안 모두 절차서 6절 원문과 완전 일치, 기존 투자 조언 고지 유지 | PASS |
| 20 | D-5 전 15페이지 노출·비우기·연락처 | notices 3케이스 빌드 | 15/15 노출, 비우면 사라짐, contact_email mailto | 15/15 동시 노출, 비우면 두 줄 제거(투자 조언 고지는 유지), contact_email 설정 시 mailto 링크·비면 미출력 | PASS |
| 21 | D-6 verification 주입/미주입 | 값 있음·없음 2케이스 | 있으면 head meta, 없으면 미출력 | 빈 값: google/naver meta 0건. 값 설정: `<meta name="google-site-verification" content="gTOKEN123">` 등 정확 주입, 종목 페이지 포함 전 페이지, head 내부 위치 확인 | PASS |
| 22 | D-6 analytics 삽입 | head_html 설정/공란 | 원문 삽입 / 미출력 | 스니펫 원문이 head 내부 삽입, 공란이면 0건. 정책(신뢰 소스 한정)이 site.json 주석에 명시 | PASS |
| 23 | D-6 이스케이프·인젝션 | 토큰에 `"><script>alert(1)</script>` 및 `tok'en<>&` 주입 후 빌드 | 속성 이탈·스크립트 실행 불가 | `&quot;&gt;&lt;script&gt;...` 로 이스케이프, 실행 가능한 script 태그 미생성, `&#x27;`·`&lt;`·`&gt;`·`&amp;` 처리. head 구조(title·canonical) 정상 파싱 | PASS |

### 3.3 D-7 배포 후 점검 스크립트 (오류 검출력)

| # | 테스트 항목 | 절차 | 기대 결과 | 실제 결과 | 판정 |
|---|---|---|---|---|---|
| 24 | 정상 상태 오탐 없음 | base_url을 로컬 서버로 교체·재빌드 후 실행 | FAIL 0 | **FAIL 0 / WARN 0** (메인·canonical·sitemap 15 URL 전수 200·robots·meta 12종목·신선도·history·styles·app) | PASS |
| 25 | 플레이스홀더·URL 불일치 경고 | 미교체 상태로 실행 | WARN + 원인 안내 | "base_url이 플레이스홀더", "점검 URL != base_url" 경고 정확 출력 | PASS |
| 26 | 주입 1: canonical 변조 | index.html canonical을 타 도메인으로 변조 | 검출 | `FAIL 메인 canonical = 배포 URL (https://wrong.example.org/)` 검출 | PASS |
| 27 | 주입 2: 데이터 노후화 | generated_at을 4일 전으로 변조 | 48시간 기준 검출 | `FAIL 데이터 신선도 48시간 이내 (99.1시간 전)` 검출 | PASS |
| 28 | 주입 3: fetch_error + 종목 수 부족 | KT fetch_error 주입 + order 11종으로 축소 | 둘 다 검출 | `FAIL meta.json 종목 수 >= 12 (11종목)`, `FAIL fetch_error 없음 (KT)` 검출 | PASS |
| 29 | 주입 4: sitemap URL 페이지 부재 | /stocks/baba/ 디렉토리 임시 이동 | 404 검출 | `FAIL sitemap의 모든 URL 200 (.../stocks/baba/(404))` 검출 | PASS |
| 30 | 주입 5: 서브경로 배포 경고 | 서브경로 픽스처(8799/sub) 빌드·서빙 후 실행 | 전 항목 통과 + robots 경고 | FAIL 0 + `WARN 서브경로 배포 - robots.txt는 도메인 루트에서만 크롤러가 읽는다` (D-4 제약과 정합) | PASS |
| 31 | 접근 불가 시 조기 중단 | 존재하지 않는 서브경로로 실행 | 명확히 실패·중단 | `FAIL 메인 페이지 200 (404)` 후 "접근할 수 없어 중단" 반환 1 | PASS |

### 3.4 회귀

| # | 테스트 항목 | 절차 | 기대 결과 | 실제 결과 | 판정 |
|---|---|---|---|---|---|
| 32 | 전체 회귀 | 단위 97 + 패닝 하니스 14 + verify_samples + SEO 96 + v2 계산 하니스 34 + HKEX·세션 16 | 전부 통과 | **97/97, 14/14, 전체 PASS, 96/96, 34/34, 16/16** - 기존 기능(패닝·SMA·기간 평균·F3 집계·F7 전환 현황·프리렌더 15페이지·BABA) 무손상 | PASS |

### 3.5 BLOCKED

| # | 항목 | 사유 | 판정 |
|---|---|---|---|
| B1 | D-2 워크플로 **실제 실행**(Pages 배포 성공 여부) | git 저장소 미생성 - 관리자 지시상 BLOCKED 처리. 구조·권한·스텝은 #13~14로 정적 검증. 저장소 생성 후 workflow_dispatch 1회 수동 실행 확인 권고 | BLOCKED |
| B2 | 브라우저 실조작 (호버 강조 시각 확인, 패닝 드래그, 375px 레이아웃) | 브라우저 자동화 도구 미가용(3회차 연속). 호버 연동·강조 로직은 출하 코드 실행으로 검증(#2~10)했으나 실제 시각 효과(감쇠 0.35의 체감, 링 가시성)는 육안 확인 필요 | BLOCKED |

## 4. FAIL 항목 상세

없음. (실행 중 나온 검사 실패는 전부 QA 스크립트의 노후 패턴으로 확인 - 4건 모두 개별 재확인함: (1) 비대칭 각주는 존재하나 문구가 갱신됨 - 5절 O-1 (2) 수식 7.2 정의 존재 확인 (3) SKHY DR 라벨은 데이터 갱신으로 날짜만 변경(2026-08-04 Nasdaq 종가) (4) 스파크라인 11 -> 12개(BABA 편입). 제품 결함 0건)

## 5. 관찰 (FAIL 아님)

| # | 내용 |
|---|---|
| O-1 | **SKHY 전환한도 출처·문구가 갱신됨**: 기준일 2026-07-29(컨콜 발언) -> **2026-07-10(SEC 424B4, Reg. No. 333-296987, 총발행의 2.5% IPO 전량 소진)**, 비대칭 각주 문구도 "ADR -> 원주 전환은 자유, 원주 -> ADR 추가 발행은 한도 전량 소진으로 신규 절차 승인 전 불가"로 변경. 1차 출처 등급이 보도 -> SEC 공시로 상향된 개선이며 PRD 요구(비대칭 각주 노출)는 계속 충족. 이번 지시 범위 밖 변경이라 별도 검증은 하지 않았고, 값 자체(17,790,000주)는 불변 |
| O-2 | check_deploy가 로컬 점검 시 base_url 불일치를 WARN으로 처리하는 설계는 적절 - 실제 배포 점검에서는 두 값이 같아야 한다는 안내도 함께 출력된다 |
| O-3 | analytics.head_html은 원문 삽입 정책이라 이스케이프 대상이 아니다(설정 주석에 "신뢰할 수 있는 제공자의 공식 스니펫만" 명시). 설정 파일 접근 권한이 곧 코드 주입 권한이므로, 운영 시 site.json 변경은 검토 대상으로 관리하는 편이 안전 |
| O-4 | 서브경로 배포 시 robots.txt 무시는 GitHub Pages 구조상 불가피 - 루트(user/org) 사이트 권장이 문서·경고에 일관되게 반영돼 있다 |

## 6. 종합 판정

- **PASS 32 / FAIL 0 / BLOCKED 2**
- **실행 가능한 전 항목 PASS.** 거래량 UX는 기본 시리즈 전환·호버 연동(불투명도/포커스 링 기하)·이월 및 토글 경계·주월 집계 강조·툴팁 등락 표기까지 출하 코드 실행으로 26항목 검증했고, 특히 **링에 fill이 없어 등락 색상 의미가 보존됨**을 강조 이동 전후 fill 배열 대조로 확인했다. 배포 준비는 D-1~D-6을 40항목으로 검증(base_url 4형식 산출물 해시 100% 동일, 서브경로 canonical·상대경로, 고지 3케이스, 토큰 인젝션 시도 차단)했고, D-7은 정상 상태 무오탐 + **고의 오류 5종 전부 검출**로 실효성을 확인했다.
- BLOCKED 2건은 환경 제약: D-2 실제 배포 실행(저장소 미생성 - 지시상 BLOCKED)과 브라우저 실조작(도구 미가용). 전자는 저장소 생성 후 workflow_dispatch 1회, 후자는 사용자 육안 확인 또는 브라우저 가용 환경에서의 후속 확인을 권고한다.
- 배포 전 잔여 사용자 조치(절차서 10.1절): Pages Source를 "GitHub Actions"로 설정, base_url 실제 URL 교체 후 재빌드, 소유확인 토큰 기입, 연락 이메일 결정. 모두 개발팀 범위 밖이며 코드는 값이 들어오면 정상 동작함을 확인했다.

---
*작성: 테스트팀, 2026-08-05. 검증 스크립트: `docs/testing/scripts/2026-08-05-qa-volhover.cjs`(거래량 UX), `2026-08-05-qa-deploy-verify.py`(D-2~D-6). D-7은 로컬 서버 + 오류 주입 5종으로 실행 검증했고 전부 원상복구했다. 본 리포트의 수치는 검증 시점 조회 기준이며 투자 조언이 아님.*
