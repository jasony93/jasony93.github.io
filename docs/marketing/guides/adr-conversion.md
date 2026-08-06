<!--
title: ADR 원주 상호전환 안내 - 전환비율 총정리
meta_description: SK하이닉스 등 한국 ADR 9종·삼성전자 GDR·TSMC의 전환비율을 SEC 공시 기준으로 정리. 상호전환 개념과 전환이 프리미엄에 미치는 영향 설명.
slug: /guide/adr-conversion/
target_keywords: ADR 원주 전환, SK하이닉스 ADR 전환, ADR 전환비율
-->

# ADR 원주 상호전환 안내 - 전환비율 총정리

## 상호전환이란

ADR(미국예탁증서)는 예탁은행이 원주를 보관하고 그 근거로 발행하는 증권이므로,
일정 절차를 거쳐 원주를 ADR로 바꾸거나(발행), ADR를 해지해 원주로 되돌릴 수
있다. 이를 상호전환이라고 한다. SK하이닉스의 경우 2026년 7월 29일부터 원주와
ADR 간 상호전환이 개시됐으며, 예탁은행은 씨티은행이다([인베스트조선](https://www.investchosun.com/site/data/html_dir/2026/07/08/2026070880088.html)).

전환할 때 기준이 되는 것이 **전환비율**이다. 종목마다 "ADR 1주 = 원주 몇 주"가
공시로 정해져 있고, 이 비율을 모르면 두 시장의 가격을 비교할 수 없다.

## 주요 종목 전환비율 표

아래 비율(r)은 "예탁증서 1주가 대표하는 원주 수"이며, 전부 SEC 공시·예탁은행
공지·거래소 공식 종목명 등 1차 출처 기준이다.

| 기업 | DR 티커 (거래소) | 원주 코드 | r (원주/DR 1주) | 출처 |
|---|---|---|---|---|
| SK하이닉스 | SKHY (나스닥, ADR) | 000660 | 0.1 (ADR 10주 = 원주 1주) | [SEC 424B4](https://www.sec.gov/Archives/edgar/data/0002120882/000119312526299963/d32785d424b4.htm) |
| 삼성전자 | SMSN (런던 IOB, GDR) | 005930 | 25 (GDR 1주 = 보통주 25주) | [삼성전자 IR](https://www.samsung.com/global/ir/stock-information/listing-Info) , [씨티 예탁 공지](https://depositaryreceipts.citi.com/adr/common/file.aspx?idf=6925) |
| TSMC | TSM (NYSE, ADR) | 2330 | 5 (ADR 1주 = 원주 5주) | [FX Broker Trust 분석](https://www.fxbrokertrust.com/insights/tsmc-adr-vs-2330-conversion-premiums-and-costs) |
| POSCO홀딩스 | PKX (NYSE, ADR) | 005490 | 0.25 (ADR 4주 = 원주 1주) | [나스닥 종목 정보](https://www.nasdaq.com/market-activity/stocks/pkx) |
| SK텔레콤 | SKM (NYSE, ADR) | 017670 | 5/9 (ADS 9주 = 원주 5주) | [SEC 6-K(2021)](https://www.sec.gov/Archives/edgar/data/1015650/000119312521267172/d221165dex991.htm) |
| LG디스플레이 | LPL (NYSE, ADR) | 034220 | 0.5 (ADS 1주 = 보통주 1/2주) | [SEC 424B4](https://www.sec.gov/Archives/edgar/data/1290109/000119312504119654/d424b4.htm) |
| 한국전력 | KEP (NYSE, ADR) | 015760 | 0.5 (ADS 1주 = 보통주 1/2주) | [SEC 20-F](https://www.sec.gov/Archives/edgar/data/887225/000119312522132015/d276732d20f.htm) |
| KB금융 | KB (NYSE, ADR) | 105560 | 1 (ADS 1주 = 보통주 1주) | [SEC 20-F](https://www.sec.gov/Archives/edgar/data/0001445930/000119312518136720/d543858d20f.htm) |
| 신한지주 | SHG (NYSE, ADR) | 055550 | 1 (ADS 1주 = 보통주 1주) | [SEC 6-K(2012, 비율 변경)](https://www.sec.gov/Archives/edgar/data/0001263043/000119312512386238/d408169d6k.htm) |
| 우리금융지주 | WF (NYSE, ADR) | 316140 | 3 (ADS 1주 = 보통주 3주) | [나스닥 공식 종목명](https://www.nasdaq.com/market-activity/stocks/wf) |
| KT | KT (NYSE, ADR) | 030200 | 0.5 (ADS 1주 = 보통주 1/2주) | [SEC 20-F](https://www.sec.gov/Archives/edgar/data/0000892450/000119312513180088/d525828d20f.htm) |

참고: 삼성전자는 미국 ADR가 없고, 런던증권거래소(IOB)에 상장된 GDR(글로벌
예탁증서)가 달러로 거래된다. 가격 비교 방식은 ADR와 동일하다.

## 전환비율은 바뀔 수 있다

전환비율은 액면분할·자본 변동 등으로 변경된다. 실제 사례:

- 삼성전자: 2018년 5월 액면분할(1 -> 50) 이후 GDR 1주 = 보통주 25주
  ([씨티 예탁 공지](https://depositaryreceipts.citi.com/adr/common/file.aspx?idf=6925))
- SK텔레콤: 2021년 10월 액면분할(1 -> 5) 이후 1 ADS = 보통주 5/9주
  ([씨티 비율 변경 공지](https://depositaryreceipts.citi.com/adr/common/file.aspx?idf=5726))
- 신한지주: 2012년 10월 비율 변경(1 ADR = 2주 -> 1 ADR = 1주)
  ([SEC 6-K](https://www.sec.gov/Archives/edgar/data/0001263043/000119312512386238/d408169d6k.htm))

과거 가격을 비교할 때는 당시 비율이 지금과 달랐을 수 있다는 점에 유의해야 한다.

## 전환이 프리미엄에 미치는 영향

상호전환이 자유로우면 두 시장의 가격 차이(프리미엄)는 차익거래로 좁혀지는
경향이 있다. 싼 쪽을 사서 비싼 쪽으로 전환해 팔 수 있기 때문이다. SK하이닉스도
전환 개시가 프리미엄 수렴·변동 요인으로 지목됐고(인베스트조선, 위 링크), 실제로
상장 직후 51%까지 치솟았던 프리미엄이 이후 28%, 16% 수준으로 축소되는 흐름이
보도됐다([파이낸셜뉴스](https://www.fnnews.com/news/202607281438264228)).

다만 전환이 제한되면 프리미엄이 유지될 수 있다. SK하이닉스는 ADR로 전환할 수
있는 물량 한도(총 주식의 2.5%)가 소진되어, 기존 ADR가 해지되지 않는 한 추가
전환이 어려운 상태가 보도됐다([야후 파이낸스](https://finance.yahoo.com/markets/stocks/articles/sk-hynix-share-conversion-mean-005605511.html)).
같은 보도는 한국 ADR의 전환 소요 기간을 3~5일 수준으로 예상하는 시장 참가자
견해를 전했다. TSMC처럼 원주에서 ADR로의 전환이 어려운 구조에서는 프리미엄이
장기간 유지되기도 한다([TSMC 프리미엄 분석 리포지토리](https://github.com/chungderson/tsmc-adr-premium)).

## 자주 묻는 질문 (FAQ)

**Q. 개인 투자자도 ADR를 원주로 전환할 수 있나요?**
A. 전환은 예탁은행 절차를 통해 이뤄지며, 증권사 경유 여부·수수료·소요 기간 등
구체 조건은 종목과 증권사마다 다릅니다. 실제 전환을 원하면 이용 중인 증권사와
해당 종목 예탁은행의 안내를 확인해야 합니다.

**Q. 전환에 시간이 얼마나 걸리나요?**
A. SK하이닉스 관련 보도 기준으로 시장 참가자들은 다른 한국 ADR와 비슷한 3~5일
수준을 예상했습니다(야후 파이낸스, 본문 링크). 종목·시점에 따라 다를 수 있습니다.

**Q. 전환비율이 바뀌면 프리미엄 계산도 달라지나요?**
A. 그렇습니다. 프리미엄 계산에는 해당 시점에 유효한 전환비율을 써야 합니다. 본
사이트는 비율 변경 이력이 확인된 종목(삼성전자·SK텔레콤·신한지주)에 대해 현재
비율이 유효한 기간의 데이터만 차트에 표시합니다.

---

*본 글은 정보 제공 목적이며 투자 조언이 아닙니다. 특정 종목의 매수·매도를
권유하지 않으며, 전환 절차·비용·과세는 각 증권사·예탁은행·세무 안내를 통해
확인하시기 바랍니다.*
