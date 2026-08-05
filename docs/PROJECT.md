# 프로젝트 개요 — ADR 프리미엄 계산기

## 이력

| 날짜 | 내용 |
|---|---|
| 2026-08-03 | 최초 작성 (사용자 지시 기반) |
| 2026-08-03 | 기획팀 PRD 완료·관리자 검토 통과. 사용자 결정 대기 (종목 범위, 데이터 예산 등) |
| 2026-08-03 | 사용자 피드백 반영 PRD 1차 개정 승인. 전환비율 12종 확정, 삼성전자 GDR 추가, 다크모드·메인 차트 카드 확정. 개발 착수 준비 완료 |

## 목표

미국에 ADR로 상장된 주식과 현지(원주) 시장에 상장된 같은 주식 간의
**프리미엄/디스카운트를 계산하고 차트로 보여주는** 웹사이트를 만든다.
주식·금융 도구 웹사이트의 첫 번째 기능이며, 이후 다른 금융 도구를 추가해 확장한다.

## 배경 (사용자 제공)

- 대표 사례: SK하이닉스 — ADR 가격에 프리미엄이 존재하며, 이를 알고 싶어하는
  수요가 시장에 있는 것으로 보인다.
- SK하이닉스 외 다른 한국 기업들과 TSMC도 포함한다.

## 확정 범위 (2026-08-03 사용자 승인)

- 대상 종목: 11종목 전부 진행 - 한국 ADR 9종(SKHY, PKX, SKM, LPL, KEP, KB, SHG, WF, KT)
  + 삼성전자 런던 GDR(SMSN) + TSMC(TSM). 전환비율 전부 1차 출처로 확정 (PRD 3.0절)
- 핵심 기능: 종목별 프리미엄 계산 + 일별 시계열 차트
- 메인 화면: 차트 카드 그리드, 노출 순서 고정 - SK하이닉스 -> 삼성전자 -> TSMC -> 나머지(시총순)
- 다크모드 지원 필수
- MVP 프로토타입 데이터 소스: yfinance (비공개 검증 한정, 공개 수익화 전 상업 API로 교체)
- 부가 지표(거래량·전환한도)는 2차 이후. 2차 범위 논의 시 사용자 재문의 필수

## 미확정 사항

- 공개 런칭용 상업 데이터 API 예산 (월 $30~$100+ 수준) -> 공개 수익화 전 사용자 결정
- 런던 GDR(SMSN) 시세의 상업 재배포 라이선스 -> 공개 런칭 전 확인
- 기술 스택 -> 개발팀 제안, 관리자 승인
- 수익 모델 -> 마케팅팀 제안, 사용자 승인
- 배포 방식/도메인 -> 추후 결정

## 진행 현황

- [x] 기획: 시장 조사 + PRD → [planning/2026-08-03-adr-premium-prd.md](planning/2026-08-03-adr-premium-prd.md) (관리자 검토 통과, 사용자 결정 대기)
- [x] 개발: MVP 구현 + 설계 문서 → [development/2026-08-03-adr-premium-design.md](development/2026-08-03-adr-premium-design.md)
- [x] 테스트: 1차 PASS 34/FAIL 1 → 수정 → 2차 전체 PASS → [testing/2026-08-03-adr-premium-test.md](testing/2026-08-03-adr-premium-test.md)
- [x] 마케팅: SEO·수익화 전략 → [marketing/2026-08-03-adr-premium-marketing.md](marketing/2026-08-03-adr-premium-marketing.md)

## 손익구조·BM 논의 (2026-08-03, 사용자 지시)

- 마케팅팀 초안: [marketing/2026-08-03-bm-improvement.md](marketing/2026-08-03-bm-improvement.md)
  (광고 외 BM 9종 평가, 손익 개선 3방향, 시나리오 재추산)
- 기획팀 타당성 검토: [planning/2026-08-03-bm-feasibility.md](planning/2026-08-03-bm-feasibility.md)
  (P1~P8 판정, 데이터 소스 상세 조사, 자체 제안 4건, 로드맵)
- 핵심 발견: KRX 무료 API에 상업 이용 금지 조항 가능성(2차 출처) - 고정비 하한은
  유료 API 견적 3건(EODHD B2B, Tiingo, Twelve Data) 회신 후 확정 필요

## SEO 필수 구현 (2026-08-04 완료)

- [x] D1~D5 구현: 프리렌더 14페이지(메인+종목11+가이드2), 메타태그·canonical·OG,
  sitemap/robots, JSON-LD, 자동 갱신 준비물(GitHub Actions 워크플로 + 로컬 배치)
- [x] 가이드 원고 2편 (마케팅팀): ADR 프리미엄 해설, 상호전환 안내
- [x] 테스트: 1차 PASS 30/FAIL 4 -> 수정 -> 2차 전체 PASS
  → [testing/2026-08-04-seo-implementation-test.md](testing/2026-08-04-seo-implementation-test.md)
- 유료 API는 사용자 결정으로 보류 - yfinance 프로토타입 유지 (비공개 한정)

## 2차 기능 F1~F8 (2026-08-04 완료)

- [x] 사용자 확정 8건 구현: 드래그 패닝, 장중 지연 시세(+지연 라벨), 일/주/월 단위,
  전일 대비 %p, SMA 20/60+기간 평균선, 거래량 서브패널, 전환 현황(한도·전환율·
  시장별 금액), 시가총액 -> PRD [planning/2026-08-04-v2-features-prd.md](planning/2026-08-04-v2-features-prd.md)
- [x] 테스트: PASS 43 / FAIL 0 / BLOCKED 5(브라우저 실조작 - 도구 소실로 미실측)
  -> [testing/2026-08-04-v2-features-test.md](testing/2026-08-04-v2-features-test.md)
- [x] F7 데이터 1차 출처 확보: SKHY ADS 잔량 SEC 424B4 근거 격상, 종목별 전환 구조
  각주(conversion_note) 10종 -> [planning/2026-08-04-f7-data-sources.md](planning/2026-08-04-f7-data-sources.md)
- 잔여: 브라우저 실조작 확인(드래그·모바일 스와이프 - 사용자 수동 확인 권고),
  F7 후속 조사(그린슈·소각 누계, 일부 20-F 개별 검증)

## 3차 개선 (2026-08-05 완료)

- [x] 드래그 패닝 버그 수정 (재렌더 시 리스너 파괴 -> wrap 1회 부착으로 재설계)
- [x] Alibaba(BABA) 편입 - 12종목째. 9988.HK, r=8(SEC 20-F), HKD 환율(페그 검증),
  HKEX 세션·휴장 편입, fungible 벤치마크 각주, USD 환산 시총 4위
- [x] 거래량 등락 색상 ("전일 종가 대비 등락 기준" 명시, 체결강도 표현 금지)
- [x] 테스트: PASS 26 / FAIL 0 / BLOCKED 1(패닝 실기기 체감 - 사용자 확인 권고)
  -> [testing/2026-08-05-baba-panning-volume-test.md](testing/2026-08-05-baba-panning-volume-test.md)
- 검토 완료·결정 대기: 1개월 무료 비상업 운영 + 도메인
  -> [planning/2026-08-05-baba-volume-domain.md](planning/2026-08-05-baba-volume-domain.md) 3절

## 4차 개선 + 공개 배포 준비 (2026-08-05 완료)

- [x] 거래량 기본 시리즈 원주 변경 + 차트 호버 시 거래량 바 강조·툴팁 수치
- [x] 프리미엄-거래량 가설 검증 분석 -> [development/2026-08-05-premium-volume-analysis.md](development/2026-08-05-premium-volume-analysis.md)
  (결론: 해소하려는 힘은 실재하나 전환 통로가 열린 종목에서만 가격에 반영.
  BABA 지속성분 SD 0.61 vs TSM 6.44)
- [x] KSD 전환가능주식수량 판별 -> 여유분(headroom)으로 확정, N_dr 아님·상업이용 금지
  -> [development/2026-08-05-ksd-litmus-test.md](development/2026-08-05-ksd-litmus-test.md)
- [x] 배포 절차서 -> [marketing/2026-08-05-deployment-guide.md](marketing/2026-08-05-deployment-guide.md)
- [x] 배포 선행 개발 D-1~D-7 (Pages 배포 job, 검증태그 주입, 푸터 고지, 점검 스크립트)
- [x] 테스트: PASS 32 / FAIL 0 / BLOCKED 2 -> [testing/2026-08-05-volume-deploy-test.md](testing/2026-08-05-volume-deploy-test.md)

## 공개 배포 대기 (사용자 조치 필요)

1. GitHub 저장소 생성(public) + Settings > Pages Source를 "GitHub Actions"로
2. 저장소명·사이트명 확정 -> site.json base_url 교체 후 재빌드
3. Search Console·네이버 서치어드바이저 소유확인 토큰 -> site.json verification
4. (선택) 연락 이메일, 분석 도구 스크립트
5. 1개월 후 판단 기준 확정 (제안: 월 1만 PV 이상 상업 전환 검토 / 3천~1만 연장 / 3천 미만 종료)

## 다음 단계 (공개 런칭 전 남은 것 - 사용자 결정 대기)

- 사용자 결정: 도메인(확정 시 site.json base_url 교체 + 재생성), 데이터 API 예산
  (견적 3건 요청 승인 대기), 런칭 시점, 커뮤니티·SNS 실행 승인, 애드센스·분석 계정
- 인프라: git 저장소·호스팅 생성 (Actions 자동 갱신 활성화 + 배포 스텝 추가)
- 확인: 삼성전자 GDR(LSE) 시세 상업 재배포 라이선스, KRX Open API 약관 원문
