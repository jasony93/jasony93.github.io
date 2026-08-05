# F7(전환 현황) 데이터 1차 출처 조사 (기획팀)

## 이력

| 날짜 | 내용 |
|---|---|
| 2026-08-04 | 최초 작성 (관리자 지시: SKHY ADS 잔량 1차 출처 보강, 타 10종 전환한도 구조 조사, tickers.json 반영 제안) |
| 2026-08-05 | 2차 심층 재조사 (사용자 지시: 전 종목 F7 데이터 재조사). 전 12종목 기준 표 재작성. **신규: 한국물 DR 잔량의 유력 경로 발견(KSD/금융위 국제거래종목정보 OpenAPI - "전환가능주식수량" 항목)**, 예탁은행 8종 특정, 전환비율 2종 외부 교차검증, BABA 총발행주식수 1차 출처 확보, 조사 경로 3건 배제 기록(db.com DR Universe 잔량 미게시, 20-F 표지 ADS 미기재, F-6 등록 상한 비채택) |
| 2026-08-05 | 3차 조사 - 거래소 공시 경로 (사용자 착안). **신규 N_dr 확보 0건.** OPEN DART 정형 공시에 DR 발행 항목 없음 확인(경로 배제), 삼성전자 IR에 GDR 수량 미기재 확인(원주 공식 수치는 확보 - SMSN.IL 전사 환산 판별을 공식 수치로 재확인), LSE·Nasdaq 종목 페이지는 기술적 접근 실패(미확인, 재시도 필요). 2.6절 신설 |
| 2026-08-05 | **4차 조사 - 거래소 내부 API 직접 호출 (개발팀, 3차의 기술적 실패 재시도). 신규 N_dr 확보 0건 - 경로 2건 종결.** LSE 내부 API는 접근 성공했으나 "shares in issue" 필드 자체를 제공하지 않음(경로 배제). Nasdaq API는 robots.txt 전면 Disallow로 **시도하지 않음**(정책 준수). 2.7절 신설 |

## 0. 요약

### 0.1 2차 조사 결과 (2026-08-05)

- **화면에 바로 넣을 수 있는 신규 확정 수치(N_dr): 0건.** 11종 모두 실제 DR
  발행 잔량의 1차 출처를 찾지 못했다 (정직한 결론).
- **다만 유력 경로 1건을 발견했다**: 한국예탁결제원(KSD) 원천의 공공
  OpenAPI(금융위원회_국제거래종목정보)에 DR 종목별 **"예탁기관명 + 전환비율 +
  전환가능주식수량"** 항목이 존재한다. 이 값의 의미(실제 잔량 vs 전환 가능
  여유)를 개발팀 실조회로 판정하면 **한국물 8~9종을 한 번에 해결할 수 있다.**
  2.1절 참조 - 이번 조사의 최대 수확.
- 부수 확보: 예탁은행 8종 특정, 전환비율 2종(LPL·SKM) 외부 1차 교차검증,
  BABA 총발행주식수(N_total) 1차 출처, 조사 경로 3건 배제 기록.

### 0.3 3차 조사 결과 (2026-08-05, 거래소 공시 경로)

- **신규 확보 N_dr: 0건.** 거래소·법정공시 경로 어디서도 DR 발행 잔량을 얻지
  못했다. 성과 없음이 결론이며, 아래 배제·미확인 구분은 다음 조사의 출발점이다.
- 확정적 성과 1건(배제): **OPEN DART 정형 공시에 DR 발행 항목이 없다**는 것을
  확인했다(2.6절). 한국 법정공시 정형 데이터 경로는 닫혔다.
- 미확인 2건(기술적 실패 - 경로 자체는 살아 있음): LSE·Nasdaq 종목 페이지.
- 부수 확보: 삼성전자 원주 공식 수치로 SMSN.IL 값의 전사 환산 판별을 재확인.

### 0.2 전 종목 현황표 (12종)

| 종목 | (a) 예탁은행 | (b) DR 발행 잔량(N_dr)·기준일·출처 | (c) 한도 유무·구조 | (d) 채택 권고 |
|---|---|---|---|---|
| SKHY | Citi | **177,900,000 ADS / 2026-07-10 / SEC 424B4** (발행 시점 수량. 7-30 소각 개시 후 실잔량은 이 값 이하) | **한도 있음** - 원주 1,779만주(총발행 2.5%), IPO로 전량 소진 | **채택 유지** (라벨 조건 - 1.1절) |
| PKX (POSCO홀딩스) | 미확인 (2차 출처의 Deutsche Bank 언급은 미검증) | 미확인 | 한국물 표준 동적 headroom (추정 - 20-F 원문 미확인) | 미확인 폴백. KSD API 확인 대상 |
| SKM (SK텔레콤) | **Citi** (db.com DR Universe 프로파일 "CIT") | 미확인 | 동적 headroom (20-F 조항 확인) | 미확인 폴백. KSD API 확인 대상 |
| LPL (LG디스플레이) | **Citi** (db.com 프로파일 "CIT" - 2차 출처의 "Deutsche Bank" 표기는 **오류**) | 미확인 ("No Outstanding Balance data to display") | 동적 headroom (추정) | 미확인 폴백. KSD API 확인 대상 |
| KEP (한국전력) | **Citi** (Citi 선임 공지) | 미확인 | 동적 headroom (추정) | 미확인 폴백. KSD API 확인 대상 |
| KB (KB금융) | **BNY Mellon** (2012-11 승계 선임) | 미확인 | 동적 headroom (20-F 조항 확인) | 미확인 폴백. KSD API 확인 대상 |
| SHG (신한지주) | **Citi** (2012 6-K) | 미확인 | 동적 headroom (20-F 조항 확인) | 미확인 폴백. KSD API 확인 대상 |
| WF (우리금융지주) | 미확인 | 미확인 | 동적 headroom (추정) | 미확인 폴백. KSD API 확인 대상 |
| KT | 미확인 | 미확인 | 동적 headroom (20-F 조항 확인) | 미확인 폴백. KSD API 확인 대상 |
| SMSN (삼성전자 GDR) | **Citi** (1차 조사) | 미확인 | 미확인 (GDR 규제 구조 미조사) | 미확인 폴백. KSD API 포함 여부 확인 |
| TSM | **Citi** | 미확인 - **20-F 표지에 보통주 수만 기재, ADS 잔량 항목 없음을 확인**. 2차 출처 "전체의 약 20%"뿐 | 고정 수치 한도 없음 - 대만 규제상 신규 ADR 창출 승인제(소각은 자유) | 미확인 폴백 + 구조 각주 |
| BABA | **Citi** (홍콩 지점 custodian) | 미확인 - 20-F는 **총발행 보통주** 18,669,888,147주(as of 2026-05-18)만 기재 | 한도 없음 - 완전 fungible(양방향 자유) | 미확인 폴백 + 구조 각주. N_total은 채택 가능 |

**주의**: 위 표의 "총발행 보통주 / r" 값(예: BABA 18.67억/8 = 약 23.3억 ADS)은
**전사 환산치이지 DR 발행 잔량이 아니다.** 검색 요약 등에서 이 계산값이 "ADS
발행 수"처럼 제시되는 경우가 있으나 채택하면 안 된다. v2 PRD 7.3의 검증 A가
정확히 이런 값을 기각하도록 설계돼 있다.

## 1. SKHY - SK하이닉스 (1차 조사 결과 유지)

### 1.1 ADS 발행 수량의 1차 출처 (확보)

- SEC 424B4 (Registration No. 333-296987): **공모 ADS 177,900,000주** (= 원주
  17,790,000주, ADS 1주 = 원주 1/10주, 공모가 $149.00, 나스닥 SKHY).
  - https://www.sec.gov/Archives/edgar/data/2120882/000119312526299963/d32785d424b4.htm
  - 보조: https://www.sahmcapital.com/news/content/sk-hynix-files-prospectus-to-sell-1779m-adss-each-representing-one-tenth-of-a-common-share-2026-07-06
- F-1 및 정정서류: https://www.sec.gov/Archives/edgar/data/2120882/000119312526280172/d32785df1.htm ,
  https://www.sec.gov/Archives/edgar/data/0002120882/000119312526295501/d32785df1a.htm
- **미확인 1건**: 초과배정(그린슈) 행사 여부 - 행사됐다면 발행 시점 ADS가
  1.779억보다 많을 수 있다. 후속 과제.

### 1.2 전환한도 구조 (1차+보도 교차 확인)

- 한도 = 원주 1,779만 주 = **총발행의 2.5%**, 7/10 IPO로 **전량 소진**. 추가
  발행은 신규 절차(주주 수요 + 당국·이사회 승인) 필요.
  - https://en.sedaily.com/news/2026/07/19/sk-hynix-25-percent-adr-conversion-talk-debunked-25-percent
  - https://finance.yahoo.com/markets/stocks/articles/sk-hynix-51-arbitrage-trade-073703063.html
  - https://www.newspim.com/news/view/20260729000369 , http://www.inews24.com/view/1989786
- 역방향(ADR 소각 -> 원주)은 제한 없음:
  https://en.sedaily.com/finance/2026/07/23/korea-depository-chief-dismisses-sk-hynix-adr-conversion
- 따라서 7-30 이후 잔량은 **감소만 가능** -> 발행 시점 수량은 **상한값**이다.

### 1.3 현재 잔량의 일별 출처 (미확인)

- Citi 잔량 데이터는 발행사 전용 Issuer Access(비공개):
  https://services.citi.com/solutions/issuer-services
- 소각 누계 공시(6-K 등)는 발견하지 못함. 분기 1회 수동 점검으로 관리.
- **2차 조사 추가**: KSD OpenAPI(2.1절)로 SKHY 잔량이 조회되면 이 문제가 해결될
  수 있다 - 개발팀 실조회 시 SKHY를 반드시 포함할 것.

## 2. 2차 조사 신규 발견

### 2.1 KSD 국제거래종목정보 OpenAPI - 한국물 잔량의 유력 경로 (최우선 확인)

- **서비스**: 공공데이터포털 "금융위원회_국제거래종목정보" (원천: 한국예탁결제원)
  - https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15059582
  - 관련: 한국예탁결제원_국제거래정보서비스 https://www.data.go.kr/data/15001135/openapi.do ,
    금융위원회_국제거래외화증권예탁결제정보 https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15043445
- **제공 항목 (오퍼레이션 1: DR종목 조회)**: 기준일·법인등록번호 기반 조회로
  DR 발행회사명, 주식종류, 종목단축코드, ISIN, 거래소 정보, **예탁기관명**,
  **전환비율**, **전환가능주식수량** 제공. (오퍼레이션 2는 사유별 일정정보)
- **웹 화면 버전(동일 원천, 직접 확인)**: SEIBRO 해외DR 발행종목 -
  https://m.seibro.or.kr/cnts/ovssec/selectOverSecDRPubSearch.do
  실제 화면 컬럼: `발행회사 | 원주 종류 | DR ISIN | DR전환가능주식수량`,
  검색 조건에 **기준일**이 있다(= as of 날짜가 명확한 데이터).
- **핵심 미확인 사항 (개발팀 실조회로 판정)**: "DR전환가능주식수량"의 정의가
  (i) 현재 DR로 발행돼 있는 원주 수량(= 우리가 원하는 N_dr의 원주 환산)인지
  (ii) 앞으로 DR로 전환 가능한 여유 한도(headroom)인지 불명확하다. 명칭만으로는
  (ii)로 읽힐 소지가 있다(추정).
  - **판정 방법**: SKHY로 조회해 검증한다. 값이 17,790,000(원주 기준)에 근접하면
    (i) 잔량이고, 0이거나 매우 작으면 (ii) 여유 한도다(한도 전량 소진 상태이므로
    여유는 0이어야 함). **SKHY가 리트머스 시험지 역할을 한다** - 1차 조사에서
    확보한 SKHY 수치의 부수적 가치.
  - (i)로 판정되면: 한국물 8종 + SKHY의 N_dr을 **기준일이 명시된 공식 데이터**로
    조회 가능 -> F7 전면 활성화. SMSN(GDR) 포함 여부도 함께 확인.
  - (ii)로 판정되면: "추가 발행 여유"라는 별도 가치가 있다 - 화면 설계 재검토
    대상(전환율 분모로는 사용 불가).
- **부수 이점**: 예탁기관명·전환비율도 제공되므로 우리 설정값의 정기 검증
  소스로 활용 가능(분기 점검 자동화).
- **제약 확인 필요**: 인증키 발급, 트래픽 제한, 상업적 이용 조건(공공데이터라
  대체로 허용되나 약관 확인 필요 - 추정), GDR·홍콩물 미포함 가능성.

### 2.2 예탁은행 특정 (8종 확보)

| 종목 | 예탁은행 | 출처 |
|---|---|---|
| KEP | Citi | Citi 선임 공지: https://depositaryreceipts.citi.com/adr/common/file.aspx?idf=3211 |
| KB | BNY Mellon | 2012-11 승계 선임: https://www.prnewswire.com/news-releases/bny-mellon-appointed-as-successor-depositary-by-kb-financial-group-inc-180821231.html , https://www.globalcustodian.com/kb-financial-appoints-bny-mellon-for-adr-program/ |
| SKM | Citi | db.com DR Universe 프로파일(직접 조회 2026-08-05): https://adr.db.com//drwebrebrand/dr-universe/dr_details.html?identifier=11977 |
| LPL | Citi | db.com DR Universe 프로파일(직접 조회): https://adr.db.com/drwebrebrand/dr-universe/dr_details.html?identifier=3574 |
| SHG | Citi | 2012 6-K (1차 조사) |
| SMSN | Citi | 1차 조사 |
| TSM | Citi | 20-F/F-6 계열 문서 |
| BABA | Citi (홍콩 지점 custodian) | 20-F |
| PKX, WF, KT | 미확인 | PKX는 2차 출처에 Deutsche Bank 언급이 있으나 미검증 (LPL 사례처럼 오류 가능) |

- **주의(정정)**: 검색 요약 등에 "LG디스플레이·POSCO의 예탁은행 = Deutsche
  Bank"라는 서술이 보이나, LPL은 db.com 자체 프로파일에서 예탁은행이 **CIT(Citi)**
  로 표기된다. adr.db.com의 "DR Universe"는 **타사 프로그램까지 수록한 정보
  서비스**이므로 수록 사실이 곧 자사 예탁을 뜻하지 않는다. PKX도 같은 이유로
  미확인 처리했다.

### 2.3 전환비율 외부 교차검증 (2종)

db.com DR Universe 프로파일의 ratio(ORD:DR) 표기가 우리 설정값과 일치했다:

- LPL: `1:2` = 원주 1주 : DR 2주 -> DR 1주당 원주 0.5주 = **우리 r=0.5 일치**
- SKM: `5:9` = 원주 5주 : DR 9주 -> DR 1주당 원주 5/9주 = **우리 r=5/9 일치**

(1차 PRD의 SEC 기반 확정값이 독립 소스로 재확인됨 - 추가 조치 불요)

### 2.4 조사 경로 배제 기록 (다음 조사에서 반복하지 않기 위함)

| 경로 | 결과 |
|---|---|
| Deutsche Bank DR Universe(adr.db.com) 종목 프로파일 | **잔량 미게시.** LPL·SKM 2종 직접 조회 결과 모두 "No Outstanding Balance data to display". Outstanding Balance 섹션 자체는 존재하나 값이 비어 있다(자사 예탁 프로그램 한정 게시로 추정). 효익 낮음 |
| 20-F 표지의 발행증권 수 | **ADS 잔량 미기재.** TSM은 보통주 수만(예: 25,902,706,622주 as of 2009-12-31), BABA도 총발행 보통주만(18,669,888,147주 as of 2026-05-18). 한국물도 동일 관행으로 추정. N_total 확보용으로는 유효 |
| Citi 예탁은행 공개 페이지 | 잔량은 발행사 전용 Issuer Access(비공개). 공개 페이지는 공지·가이드 위주 |
| F-6 등록서류의 등록 ADS 수 | **비채택 권고.** F-6는 "발행 가능하도록 등록한 상한"이며 실제 잔량과 무관하게 여유 있게 등록하는 것이 일반적(추정). 전환율 분자·분모로 쓰면 실제와 크게 다른 수치가 표시돼 오도 위험이 크다 - 투명성 원칙상 부적합 |

### 2.5 BABA 총발행주식수 (N_total 1차 출처 확보)

- **18,669,888,147 보통주 (as of 2026-05-18)** - 20-F FY2026.
  - https://www.sec.gov/Archives/edgar/data/0001577552/000119312526231755/baba-ex2_46.htm
  - 홍콩 공시(참고): https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0513/2026051300653.pdf
- 용도: F7·F8의 N_total 교차 검증값(현재는 yfinance 조회값 사용). 기준일이
  명확해 자동 조회값 이상 검증에 유용.

### 2.6 3차 조사 - 거래소·법정공시 경로 (2026-08-05)

착안점: Yahoo의 DR 발행주식수는 전 종목 전사 환산치로 확인됐고(관리자 실측),
Yahoo 내부 수치만으로는 "시총 = 주가 x 주식수"의 순환 논리를 벗어날 수 없다.
**거래소·법정공시가 상장 증권 수량을 독자 공시한다면 순환이 깨진다**는 가설로
조사했다.

| 경로 | 대상 | 결과 | 판정 |
|---|---|---|---|
| **OPEN DART 사업보고서 주요정보조회** | 한국물 9종 | 제공 정형 항목이 "주식의 총수 현황", "자기주식 취득·처분 현황", "배당", "증자(감자) 현황", "채무증권 발행실적" 등이며 **해외 예탁증서(DR) 발행 항목은 없다**. https://opendart.fss.or.kr/disclosureinfo/biz/main.do (직접 조회 2026-08-05) | **경로 배제** (정형 데이터 한정). 사업보고서 *본문 서술*에 GDR/ADR 언급이 있을 가능성은 남음 - 원문 확인은 미시도 |
| **삼성전자 IR 상장정보** | SMSN | GDR 종목코드·ISIN·상장거래소만 기재. **GDR 발행 수량·전환비율·예탁은행·기준일 모두 미기재.** 원주는 명시: 보통주 5,919,637,922주 / 우선주 815,974,664주 (2026년 1분기말 기준). https://www.samsung.com/sec/ir/stock-information/listing-info | GDR 잔량 **미확인**. 원주 수치는 확보(아래 판별에 사용) |
| **런던증권거래소(LSE) 종목 페이지** | SMSN | 페이지가 JS 렌더링 방식이라 본문 콘텐츠를 취득하지 못했다("London Stock Exchange" 제목만 반환). https://www.londonstockexchange.com/stock/SMSN/samsung-electronics-co-ltd-att | **미확인 (기술적 실패)**. "Shares in issue" 게시 여부 자체를 확인 못 함 - 재시도 대상 |
| **Nasdaq 종목 페이지** | SKHY, KB (2건 시도) | 두 건 모두 60초 타임아웃으로 응답 없음 (2026-08-05). https://www.nasdaq.com/market-activity/stocks/skhy , https://www.nasdaq.com/market-activity/stocks/kb | **미확인 (기술적 실패)**. 과거 조사에서 Nasdaq 페이지의 *종목 정식 명칭*(예: WF "each representing three (3) shares")은 취득된 바 있으나, shares outstanding 게시 여부는 미확인 - 재시도 대상 |
| **TWSE / HKEX 공시** | TSM, BABA | 위 경로들의 실패로 예산 소진, **미시도** | 미확인 |

**부수 성과 - SMSN.IL 판별의 공식 수치 재확인**

- 삼성전자 공식 IR 수치(2026 1Q말): 보통주 5,919,637,922 + 우선주 815,974,664
  = 총 **6,735,612,586주**.
- Yahoo SMSN.IL 발행주식수 271,707,008 x r(25) = 6,792,675,200주.
- 총발행주식수 대비 **100.85%** -> v2 PRD 검증 A 기준(90% 이상이면 전사 환산치로
  기각)에 따라 **기각 확정**. 보통주만으로 보면 114.7%로 더욱 성립 불가.
- 참고: 관리자 실측 메모의 수치(총 약 67.93억, 보통주 57.64억)와 공식 IR
  수치(67.36억, 59.20억) 사이에 소폭 차이가 있으나(기준일 차이로 추정),
  **판별 결론은 동일**하다 - GDR 잔량일 수 없다.

**3차 조사의 시사점**: 공개 웹 경로(거래소 페이지·발행사 IR·법정공시 정형
데이터)에서 DR 잔량을 얻는 것은 현재로선 막혀 있다.

**[관리자 정정 2026-08-05]** 3차 조사 보고서가 "KSD OpenAPI 실조회가 사실상 유일한
유망 경로"라고 기재했으나 이는 **오류다. KSD 경로는 이미 종결·배제됐다.**
개발팀이 2026-08-05 SEIBRO 직접 조회(인증키 불필요 경로)로 리트머스 테스트를
완료했고, "전환가능주식수량"은 **(ii) 추가 전환 여유분(headroom)**으로 판정됐다
(SKHY 값 = 0, 우리금융 값 = 총발행의 88.76%). 우리가 필요한 N_dr이 아니며,
공공저작물 제2유형(상업적 이용 금지)이라 상업 사이트 표시도 불가하다.
근거: `docs/development/2026-08-05-ksd-litmus-test.md`.

따라서 **남은 실효 경로는 LSE·Nasdaq 등 거래소의 상장 증권 수량 공시(기술적
실패로 미확인 상태)**와 사업보고서 본문 서술 확인이다.
-> **4차 조사(2.7절)에서 이 중 거래소 경로 2건이 종결됐다.**

### 2.7 4차 조사 - 거래소 내부 API 직접 호출 (개발팀, 2026-08-05)

3차에서 "기술적 실패(JS 렌더링·타임아웃)"로 남은 LSE·Nasdaq 경로를, SEIBRO를
뚫었던 것과 같은 방식(사이트가 내부적으로 호출하는 API를 직접 요청)으로 재시도했다.

**결론: 신규 N_dr 확보 0건. 두 경로 모두 종결한다.**

| # | 대상 | 시도한 엔드포인트 | 응답 | 결과 |
|---|---|---|---|---|
| 1 | LSE SMSN | `GET https://api.londonstockexchange.com/api/gw/lse/instruments/alldata/SMSN` | **200 (JSON 68필드)** | **"shares in issue" 필드 없음** - 발행 수량 미제공 |
| 2 | LSE SMSN | 같은 경로의 `/fundamentals`, `/keystats`, `/summary`, `/company`, `/keyfundamentals` | 전부 404 | 수량 제공 하위 엔드포인트 부재 |
| 3 | LSE SMSN | `/api/v1/components/refresh?path=...` (구 웹 컴포넌트 API) | 405 Method Not Allowed | GET 미허용 |
| 4 | **Nasdaq (SKHY·KB 등)** | `api.nasdaq.com` 계열 | **시도하지 않음** | **robots.txt가 `User-agent: * / Disallow: /`로 전면 금지** - 정책상 호출하지 않음 |

**LSE 상세 (경로 배제 근거)**

- LSE API는 인증 없이 정상 응답하며 ISIN·전환비율 설명(`GDR (EACH REP 25 COM STK
  KRW100)`)·가격·시총 등을 제공한다. 우리 설정값(r=25) 재확인에는 쓸 수 있다.
- 그러나 **발행 수량(shares in issue) 필드는 존재하지 않는다.** 수량 관련 필드는
  `marketcapitalization` 하나뿐이다.
- 시총을 가격으로 나눈 파생 추정으로 판별을 시도한 결과:

| 항목 | 값 |
|---|---|
| marketcapitalization | 765,765,107,804 |
| lastclose (USD) | 4,444 |
| 파생 "shares" (시총/가격) | 172,314,381 |
| x r(25) = 원주 환산 | 4,307,859,517 |
| vs 보통주 5,764,191,903 | **74.7%** |
| vs 총발행(보통+우선, 약 67.4억) | **63.9%** |

- 판별 임계값(90%)에는 미달하지만 **채택하지 않는다**. 이유:
  1. LSE가 "GDR 발행 수량"으로 제공한 값이 아니라 시총/가격 **파생 추정치**다.
  2. `marketcapitalization` 정의(전사 기준 vs GDR 라인 기준)가 문서화돼 있지 않다.
  3. 값의 크기 자체가 GDR 잔량으로 **경제적 상식에 반한다** - 삼성전자 GDR이
     보통주의 74.7%일 수 없다. 절대 규모도 $765.8B로 회사 전체 시총(약 $970B,
     2026-08-05 기준 추산)에 근접해 사실상 전사 기준 값으로 보인다(추정).
- -> **부정확한 수치 표시 금지 원칙에 따라 tickers.json 미반영.**

**Nasdaq 상세 (정책상 미시도)**

- `https://api.nasdaq.com/robots.txt` 원문: `# This robots.txt file disallows all
  web crawlers ... User-agent: * / Disallow: /`
- 관리자 지시("robots.txt 위반 금지")에 따라 **엔드포인트를 호출하지 않았다.**
  Nasdaq/NYSE 경로로 ADR 잔량을 얻으려면 robots 정책을 준수하는 다른 방법
  (공식 데이터 라이선스, 사람이 직접 웹 화면 확인)이 필요하다.
- `www.nasdaq.com`은 `Crawl-delay: 30`이며 API 경로 자체는 위 서브도메인이다.

**미시도 (지시 범위)**: TWSE(TSM)·HKEX(BABA)는 "1·2가 빠르게 풀리면"이라는
조건부 지시였고 1·2가 풀리지 않아 착수하지 않았다.

**남은 경로 (기획팀 판단 필요)**: 예탁은행 프로그램별 잔량 공시(계약 필요 가능성),
20-F/사업보고서 본문 서술, 상업 데이터 벤더. **기술적 스크래핑 경로는 이번 4차로
사실상 소진됐다고 본다.**

## 3. 한국물 8종 - 한도 구조 (1차 조사 결과 유지)

20-F 표준 조항: 예탁은행은 "누적 발행량과 현재 잔량의 차이"(소각으로 생긴
여유분)를 초과하는 신규 예탁에 발행사 사전 동의가 필요하며, 소각 후 재예탁이
불가할 수 있다는 경고가 명시된다. **SKHY형 고정 수치 한도는 비적용**이다.

- SK텔레콤 20-F FY2023: https://www.sec.gov/Archives/edgar/data/1015650/000119312524119709/d610408d20f.htm
- SK텔레콤 20-F FY2015: https://www.sec.gov/Archives/edgar/data/0001015650/000119312516566089/d167185d20f.htm
- 신한지주 20-F FY2021: https://www.sec.gov/Archives/edgar/data/1263043/000119312522110321/d438053d20f.htm
- KB금융 20-F FY2008: https://www.sec.gov/Archives/edgar/data/0001445930/000095012309013901/h03411e20vf.htm
- KT 20-F FY2004: https://www.sec.gov/Archives/edgar/data/0000892450/000114554905001159/u99857e20vf.htm

미확인(개별 원문): PKX, LPL, KEP, WF - 동일 표준 조항으로 추정.

## 4. TSM / SMSN / BABA 구조

- **TSM**: 원주 -> ADR 신규 창출은 대만 당국 승인 필요·엄격 통제, ADR -> 원주
  소각은 자유. 이 비대칭이 구조적 프리미엄의 원인으로 설명된다.
  - https://github.com/chungderson/tsmc-adr-premium ,
    https://www.fxbrokertrust.com/insights/tsmc-adr-vs-2330-conversion-premiums-and-costs ,
    https://invezz.com/news/2026/07/23/sk-hynix-stock-gains-adr-conversion-cap-could-keep-us-shares-trading-at-a-premium/
  - 잔량: 2차 출처 "전체의 약 20%"( https://www.acadian-asset.com/investment-insights/owenomics/tsmc-totally-stupid-market-chaos )
    뿐. 1차 미확인(20-F 표지 미기재 확인). 후속: TSMC IR FAQ
    https://investor.tsmc.com/english/faq
- **SMSN**: GDR 발행 잔량·규제 구조 모두 미확인. 3차 조사에서 발행사 IR에
  GDR 수량이 없음을 확인했고(2.6절), LSE 페이지는 접근 실패로 게시 여부 자체가
  미확인이다. 남은 단서 2개: LSE "Shares in issue" 재시도, KSD API 포함 여부.
  참고로 Yahoo SMSN.IL 수치는 전사 환산치로 **기각 확정**(2.6절 판별).
- **BABA**: 완전 fungible(양방향 자유) - 한도 개념 없음. 잔량 미확인.

## 5. tickers.json 반영 제안 값 (문서 제안만 - 파일 수정은 개발팀)

SKHY (1차 조사분 유지):

```
"conversion_limit_local": 17790000,
"limit_as_of": "2026-07-10",
"limit_src": "https://www.sec.gov/Archives/edgar/data/2120882/000119312526299963/d32785d424b4.htm (424B4, 총발행의 2.5%, IPO로 전량 소진)",
"dr_outstanding_manual": 177900000,
"dr_outstanding_as_of": "2026-07-10",
"dr_outstanding_src": "SEC 424B4 공모 수량 (발행 시점 기준. 2026-07-30 전환 개시 이후 소각분 미반영 - 실제 잔량은 이 값 이하. 그린슈 행사 여부 미확인)",
"conversion_note": "ADR -> 원주 전환은 자유, 원주 -> ADR 추가 발행은 한도(총발행의 2.5%) 전량 소진으로 신규 절차 승인 전 불가"
```

나머지 11종: **수치 필드 기재하지 않음(미확인 폴백 유지)**. 구조 각주만 제안:

```
(PKX, SKM, LPL, KEP, KB, SHG, WF, KT)
"conversion_note": "원주 -> ADR 신규 예탁은 소각분 범위 내 + 초과 시 발행사 동의 필요 (20-F 예탁계약 조항)"

(TSM)
"conversion_note": "대만 규제상 원주 -> ADR 신규 전환은 승인 필요로 제한적, ADR -> 원주는 자유"

(BABA)
"conversion_note": "ADR와 홍콩 보통주 간 양방향 전환이 자유로워 괴리가 작게 유지됩니다"

(SMSN)
conversion_note 없음 (구조 미조사 - 부정확한 문구 게재 금지)
```

## 6. 후속 조사·확인 과제 (우선순위 순)

1. **[최우선·개발팀] KSD 국제거래종목정보 API 실조회** - "DR전환가능주식수량"의
   정의를 SKHY 값으로 판정(2.1절). 한국물 8~9종 F7 활성화 여부가 여기서 갈린다.
   인증키 발급·트래픽·상업 이용 약관도 함께 확인.
2. **[3차 조사 잔여] LSE·Nasdaq 종목 페이지 재시도** - 둘 다 기술적 실패로
   "게시 여부 자체"를 확인하지 못했다(2.6절). JS 렌더링·타임아웃 회피 수단
   (브라우저 도구 등)이 있으면 확인 가치가 있다. LSE에 "Shares in issue"가
   게시되고 그 값 x 25가 삼성전자 총발행주식수의 90% 미만이면 **SMSN의 GDR
   잔량 확보**를 뜻한다.
3. SKHY 그린슈 행사 여부 (424B4 옵션 조항 + 상장 후 6-K).
4. TSM ADS 잔량 1차 출처 - TSMC IR FAQ·연차보고서, TWSE 공시 확인(3차 미시도).
   BABA는 HKEX 공시 확인(3차 미시도).
5. 한국물 사업보고서 **본문 서술** 확인 - OPEN DART 정형 항목에는 없으나
   본문에 DR 발행 현황이 서술될 가능성(2.6절). 삼성전자·SK하이닉스 표본 확인.
4. PKX·WF·KT 예탁은행 특정, PKX·LPL·KEP·WF 20-F 예탁 조항 원문 확인.
5. SMSN GDR 발행 잔량·규제 구조 (삼성전자 사업보고서 DART 확인 포함).
6. SKHY 소각 누계의 공개 출처 (분기 1회 수동 점검 절차에 편입).

---
*작성: 기획팀, 2026-08-04 / 2차 조사 2026-08-05. 미확인 항목은 미확인으로
명기했으며 추정치를 수치로 채우지 않았다. 본 문서는 투자 조언이 아니다.*
