---
name: namoobi-market-report
description: |
  글로벌 금융시장 종합 시황 보고서를 자동 생성·발송하는 워크플로우. 사용자가
  "글로벌 시황 보고서", "오늘 시장 보고서 보내줘", "global market report",
  "daily market briefing", "매일 시황 발송", "코스피 미국증시 보고서 만들어줘",
  "namoobi 시황 보고서" 등으로 요청할 때 트리거된다. 여러 서브에이전트
  (뉴스/시장데이터/원자재/암호화폐/한국증권사/글로벌IB/시계열·차트/종합분석)를 병렬로 호출해 자료를 수집하고,
  종합 데이터를 JSON으로 정리한 뒤 docx 보고서를 생성하고, Claude in Chrome 가
  로그인된 Gmail 작성창에서 직접 메일을 작성·docx 첨부·발송한다
  (받는사람: namoobi@gmail.com 단독, 숨은참조: 연결폴더 SECURITY 폴더의 수신자 목록 파일에 적힌 주소 —
  예약 실행이면 예약메일수신자.txt, 일반 실행이면 메일수신자.txt).
---


# Namoobi Market Report (plugin v1.21.1 · SKILL v3.54.1)

> 변경이력(배너)은 `CHANGELOG.md` 로 분리 — 런타임 미로딩. 현행 규칙은 아래 '핵심 수집 규칙'과 각 Phase 본문, `references/` 를 따른다.

## 핵심 수집 규칙 (현행 — 매 실행 준수)

> **원칙: "조용히 미표시(-)·carry-forward·stale 로 넘기지 말 것. 결함이 있으면 발송하지 말고 사용자에게 물어라."** 정상 예제(`D:\claudeCowork\GOODREPORT`) 수준을 못 맞추면 Phase 4.5 게이트에서 멈춘다. 아래는 그동안 반복적으로 깨지던 지점의 확정 규칙이다(상세·스키마는 `references/agents.md`).

> **[Big-Arch] 비매일 지표 DB화 (최우선 원칙 · 상세 `references/db-architecture.md`)**: 발표주기가 매일이 아닌 **모든 3.1 매크로 지표**(FOMC 기준금리·6개국 정책금리·FOMC 회의일정·점도표·물가 CPI/CoreCPI/PCE/CorePCE/PPI·고용 7종(초기 실업수당 청구건수 포함)·빅테크 CAPEX·메모리/HBM·경기선행지수(한국)·OECD CLI)는 ① 별도 DB(파일)에 저장하고 ② 매 실행 **변동 여부만** 저렴히 조사해 ③ 변동 시에만 재조사·갱신하며 ④ 변동 없으면 DB값을 그대로 쓴다. 보고서엔 표준 캡션 **"업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지"** 를 명시한다(물가는 `, BEI는 실시간` 부기). **매일 실측(DB화 제외)**: 美 국채금리(10Y·2Y)·장단기차(10Y-2Y)·HY 스프레드·기대인플레(BEI)·심리(VIX·KSVKOSPI·DXY·원/달러·WTI·美10Y). CAPEX·HBM 은 **누적형 DB**(신규 관측치 upsert 로 시계열 계속 업그레이드).
> **Top News 최신성(req1)**: 1.글로벌 Top News 10 은 발행일이 **전일~당일(D-0~D-1)** 인 기사만 사용(2일 이상 지난 뉴스 금지).
> **[Big-Arch 구현] 범용 DB**: `scripts/nmr_db.py`(check/get/set/upsert) + `merge.py` 가 매 실행 **물가·고용·정책금리·FOMC회의·점도표·경기선행·OECD CLI** 7섹션을 `_market_report_data/db/<item>.json` 에 자동 저장하고, 비면 DB값을 재사용한다(변동 시에만 갱신). 에이전트는 섹션 마커(최신 발표/결정일)를 `nmr_db.py check` 로 1회 관측해 reuse 면 수집 스킵 가능. **차트 시계열도 `nmr_db.dbseries` 로 db/series_*.json 에 누적**(부실 수집 보강). 점도표·13F·리밸런싱 포함 모든 비매일 지표를 통합 DB로 일원화 — **구 마커체크(nmr_cache.py)는 폐지**.

**공통 소스·폴백**
- 증시·지수·환율·원자재·美ETF·크립토시계열: **`scripts/fetch_us.py`**(sandbox·stdlib·스레드 병렬, Yahoo+alternative.me, ~4초). 美10년=^TNX, 전체 국채커브·CAPEX·점도표는 USMacroExtras(FMP). 한국 지수/수급/시계열은 fetch_kr.py·fetch_semi.py.
- 암호화폐: CoinInfo MCP 우선. `get_kimchi_premium` 이 null/부족이면 **CoinDesk MCP `fetch_spot_tick`**(upbit `<SYM>-KRW` + binance `<SYM>-USDT`)로 직접 계산. 공포·탐욕 = `api.alternative.me/fng`. 한국 거래소(업비트·빗썸) API 는 Chrome 차단 → CoinDesk MCP 로만.
- 모든 trend/추세 텍스트는 **한글**. **추정 금지** — 도구·검색으로 확인된 값만, 없으면 null(기억으로 채우지 말 것).
- **(FMP 무료 = 미국만 활용)** 美 국채금리/커브는 `economics treasury-rates`, 미국 대형주 월가 컨센서스·목표주가는 `analyst price-target-consensus`/`grades`, 빅테크 capex 는 `statements cashflow` 로 보강. 13F·indexes·news·**한국 데이터**는 FMP 상위플랜 필요(미보유 시 기존 Yahoo/Chrome 유지). **Bigdata MCP 는 구독 만료로 사용 불가.**

**3.1 구성 (v3.49 재배열 — ①~④ 그룹 소제목 + 순차 번호 3.1.1~3.1.13, 방법 B)** — 그룹 소제목(①~④)은 **번호 없는 소제목**(빌더 `gh()`: 좌측 파란 바+연한 음영, 개요 번호 체계 밖)이고 지표 번호는 3.1.1~3.1.13 순차. 렌더 순서는 `renderMacroIndicators` 가 강제한다: **① 매크로(정책·경기)** = 3.1.1 금리·통화정책 / 3.1.2 물가·인플레이션 / 3.1.3 고용·경기 / 3.1.4 OECD 경기선행지수(CLI) / 3.1.5 경기선행지수 순환변동치 → **② 기업 실적** = 3.1.6 Earnings Insight(FactSet) / 3.1.7 미국 빅테크(M7) 실적 전망 / 3.1.8 AI 빅테크 자본지출(CAPEX) → **③ 반도체·한국 연결고리** = 3.1.9 메모리+HBM 지표 / 3.1.10 관세청 수출 잠정치 / 3.1.11 반도체 사이클→코스피 점검판 → **④ 수급·심리(선행신호)** = 3.1.12 심리·자금흐름 보조지표 / 3.1.13 파생시장 포지셔닝 현물 선행신호. (구번호 대응: 舊3.1.4심리→3.1.12, 舊3.1.5FactSet→3.1.6, 舊3.1.6CAPEX→3.1.8, 舊3.1.7A→3.1.9, 舊3.1.7B→3.1.11, 舊3.1.8CLI→3.1.4, 舊3.1.9순환→3.1.5, 舊3.1.20M7→3.1.7, 舊3.1.21파생→3.1.13)

**3.1 주요지표(매크로 대시보드)** — `gen_macro_charts.py` + **MacroAgent**(`nmr_macro.json`). 금리=FMP `economics` `federalFunds`·`treasury-rates`(2Y/10Y); 물가·고용=FMP `economics`(CPI·unemploymentRate·totalNonfarmPayroll·retailSales·realGDP) + **FRED API 직접**(Core CPI=`CPILFESL`·PCE=`PCEPI`·Core PCE=`PCEPILFE`·PPI=`PPIFIS`·10Y기대=`T10YIE` — `fetch_macro.py`+`nmr_fred.py` 가 연결폴더 `SECURITY/secrets.env` 의 `FRED_API_KEY` 로 `api.stlouisfed.org` 호출, 무키/실패 시 `fredgraph.csv` 폴백); ISM 제조/서비스 PMI 는 ISM 공식 보도자료(ismworld.org·PRNewswire) 실측을 WebSearch로 수집('추정' 라벨 금지·release 날짜 정확히·미발표월은 직전 실측월 유지); 한·중 정책금리만 무료 실시간 API 없어 WebSearch 추정('추정' 표기). VIX·DXY·원/달러·WTI·美10년물·**KSVKOSPI(코스피 변동성지수 = CNBC `.KSVKOSPI` 실시간)**은 `fetch_us.py` 시세 **재사용**(merge 주입). `nmr_macro.json` 미수집 시 `merge.py` 내장 예시·추정값(`MACRO_DEFAULT`) — 비차단.
**3.1.6 Earnings Insight (FactSet)** — 매 실행 `https://insight.factset.com/topic/earnings` 최신 블로그 포스트를 확인한다. ⚠️ **(req7 근본원인) 이 topic 페이지는 HubSpot JS 렌더라 `web_fetch`가 캐시된 옛 목록을 반환한다(최신 블로그 누락) → 반드시 메인세션 Claude in Chrome 으로 `navigate`+`javascript_tool`(또는 `get_page_text`)로 JS 렌더된 최신 글 목록을 읽어 '가장 최근 날짜' 블로그를 판별한다.** 주간 `Earnings Insight` PDF(`advantage.factset.com/.../EarningsInsight_MMDDYY.pdf`)는 `web_fetch`로 정독 가능(PDF는 캐시 문제 없음). **DB(`_market_report_data/nmr_factset.json`)보다 새 자료면** 블로그=제목·날짜·링크·핵심 사실 요약, 리포트=리포트날짜·링크·다음 발행일·**전체 리포트 섹션별 요약**(Topic of the Week/Overview/Revisions/Guidance/Growth/Revenue/Margin/Forward Estimates/Targets&Ratings) + **Key Metrics 6패널 대시보드**(gen_factset_chart.py 자체작성→charts/factset_keymetrics.png)를 갱신하고, **새 자료가 없으면 DB값 그대로 사용(carry-forward)**. **(req7) `report.next_date`가 지났으면 신규 회차(`EarningsInsight_MMDDYY.pdf`, 월/일/연 2자리)를 반드시 web_fetch로 다운로드·본문 정독해 `report.full_summary`(섹션별 points)와 date·url을 교체한다 — '이전 자료 잔존' 금지. `fs.topic_url`(insight.factset.com/topic/earnings)을 세팅하면 빌더가 3.1.6 하단에 출처 링크를 렌더한다.** **(req4·req5 2026-07-05) 빌더는 3.1.6 상단에 표준캡션 "업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지" 를 렌더하고, 도입문은 "최신 블로그 포스트와 주간 리포트를 요약한다"(첫 장 아님 — 전체 리포트 섹션별 요약). DB 갱신 시 `report.next_date`(다음 주간 발행일)·`last_checked`(체크일)를 반드시 채운다 — verify req20 이 next_date 공란=경고, next_date 경과·미갱신=발송 차단으로 강제.** ⚠️ **저작권: FactSet 그래프·표 이미지는 복제하지 않고, 사실 요약·수치 + 출처 링크만 수록**. `merge.py`가 `nmr_factset.json`을 `markets.factset`으로 로드 → `build_report.js renderFactSet`가 3.1.6 렌더(블로그 블록 제목=포스트 제목, 리포트 블록 제목='Earnings Insight report'). DB 미존재 시 섹션 자동 생략(비차단).
**3.1.4 OECD 경기선행지수(CLI) (v3.43 — 3.1.5 국내 순환변동치 앞, 방향 신호→확인 신호 순)** — 통합 DB `db/oecd_cli.json`(월별 총기간 × 17개국, 시드=2026-07-03 KOSIS 다운로드분 2022.01~2026.04). **매 실행(매일) 메인세션 Claude in Chrome** 으로 KOSIS 통계표 `https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_2STES045&conn_path=I3` 에 접속(web_fetch 는 세션오류로 불가 — Chrome 전용, 증권사 3사 `browser_batch` 에 1탭 추가)해 **자료갱신일만 싸게 관측** → `nmr_db.py check oecd_cli <자료갱신일>`. `reuse` 면 수집 스킵·DB 그대로, `due` 면 조회 시점을 **전체 기간(월)** 으로 맞춰 그리드에서 국가×월 시계열을 추출해 `$WORK/nmr_oecd_cli.json` 저장(스키마 `{"data_updated":"YYYY-MM-DD","months":["YYYY.MM"..],"series":{"국가":[값..]}}`, 국가명의 `[비회원국]` 접두 제거·값 없으면 null) → merge.py 가 DB 갱신(`_ndb.sync('oecd_cli',…)`), 추출 실패 시 비차단(DB 폴백·캡션에 기존 자료갱신일 표기). 차트=Phase 1.5 `gen_cli_chart.py` → `charts/oecd_cli.png` **전 국가 통합 1장(X축=월별 총기간, Y축=지수(진폭조정), 기준선 100, 대한민국 굵은 선, 우측 국가명·최신값 라벨)**. 빌더 `renderOecdCli` 가 표준캡션+차트+**고정 설명블록**(정의/구성요소/해석방법/한계 — 빌더 내장, 수집 불필요) 렌더. 게이트=verify req19(데이터 있는데 차트 없으면 차단).
**3.1.10 관세청 수출 주요품목별 10일 단위 잠정치 통계 (v3.44 신설 — DB화)** — data.go.kr 15157908 오픈API(`apis.data.go.kr/1220000/prlstMmUtPrviExpAcrs/getPrlstMmUtPrviExpAcrs`, serviceKey=연결폴더 `SECURITY/data.go.kr.txt`, 파라미터 `strtYymm`·`endYymm`=YYYYMM, 조회 10년 제한→청크). **전 기간(2016-01~) 10일 누계(1~10/1~20/1~말일) 수출액(천 달러, 11개 품목: 전체+반도체·철강·승용차·석유·무선통신·선박·자동차부품·컴퓨터주변기기·정밀기기·가전) DB화**(`db/customs.json`). **매일 저렴한 변경체크**(최근 4개월 해시 마커)로 신규 순보/현행화가 있으면 전체 백필·갱신, **변경없으면 DB·차트 그대로 재사용**(표준캡션 "업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지"). 공표: 1~10일분 11일·1~20일분 21일·1~말일분 익월1일(전월까지 현행화·당월 잠정치). `fetch_customs.py`(stdlib, Phase 1 bash 병렬)가 변경 시에만 `nmr_customs.json` 생성 → merge `_ndb.sync('customs')` → `m.customs`. 차트=Phase 1.5 `gen_customs_chart.py` → `charts/수출_전체_24개월.png`·`charts/수출_반도체_24개월.png`(최근 24개월 그룹막대 1~10/1~20/1~말일, 번들 한글폰트). 빌더 `renderCustoms` 가 표준캡션+최근월 요약표(전체·반도체 × 3순보)+차트 2종 렌더. 게이트=verify(데이터 있는데 차트 없으면 차단).
**3.1.9 / 3.1.11 반도체 사이클→코스피 점검판 (v3.45 신설 — DB화)** — 기존 3.1.7 메모리+HBM 지표를 v3.49 재배열로 **3.1.9** 로 재번호(내용·차트 불변). 별도로 **3.1.11 반도체 사이클 → 코스피 점검판** 신설(3.1.10 관세청 뒤)(본문+신호표, **차트 없음**). 목표=반도체 업황(메모리 가격·재고·주문·CAPEX)/업종 사이클(재고·ASP→업체 실적 선행)/반도체 사이클 하강의 코스피 핵심 대형주(삼성전자·SK하이닉스) 압박/확인법(메모리업체 발표·시장조사 보고서)을 한 화면에 점검. **매 실행(매일) 저렴한 변동체크** — HBMAgent(또는 KoreaSemiTheme)가 겸직해 WebSearch+TrendForce/각사 실적으로 3대 조기경보 신호(① 재고주수 ② DRAM 계약가 상승률 QoQ ③ SK하이닉스 CAPEX 증가율 YoY)와 코스피 쏠림 수치를 관측 → **변동 시에만 `nmr_semi_cycle.json` 생성**(스키마=`references/data-schema.md`), **변동 없으면 DB(`db/semi_cycle.json`) 그대로 사용**(표준캡션 "업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지"). merge `_ndb.sync('semi_cycle')`(marker=asof) → `m.semi_cycle` → 빌더 `renderSemiCycle`(③그룹: 3.1.10 관세청 뒤·3.1.12 심리 앞) 가 **(req6 2026-07-05 확장) ① 사이클 단계 바(저점→회복→상승→고점→하강, 현재 단계 강조+예상 고점 캡션) ② 핵심 타일 4(DRAM/NAND 계약가·재고·공급부족) ③ 점검 카드 4(반도체 업황/업종 사이클/코스피 대형주 압박/확인 방법) ④ 핵심 한 줄·읽는 방법·조기 경보 신호·3신호표(현재값·판정·경보 임계선·비고) ⑤ 3대 조기경보 미니차트(charts/semi_cycle_signals.png — gen_hbm_dashboard.py 가 db.series{inventory,price_qoq,capex_yoy}로 생성)·신호별 캡션·출처** 렌더. DB 스키마 확장: stages·tiles·panels·series·chart. 판정 색=안전(초록)/주의·둔화(주황)/경보·하강(빨강). 데이터 없으면 섹션 자동 생략(비차단). 시드=`db/semi_cycle.json`(2026-07-04). 3대 신호 중 **2개 이상 경보면 고점·하강 신호**로 읽는다.
**3.1.7 미국 빅테크(M7) 실적 전망 (v3.46 신설 — 매일)** — 대상 7종목(AAPL·MSFT·NVDA·GOOGL·AMZN·META·TSLA)의 가이던스·애널리스트 추정치/목표주가 리비전을 섹터·시장의 선행 신호로 읽는 표(②그룹: 3.1.6 FactSet 뒤·3.1.8 CAPEX 앞). **매일 갱신**: 시세·평균목표주가·투자의견 분포·목표주가 리비전(1M/1Q/1Y)·등급변경은 매 실행 실측(FMP `analyst` grades-summary·price-target-summary/consensus — 무료플랜 미국 대형주 가용), 가이던스·연간 추정치는 실적 발표 시 WebSearch. 신호=추정치·목표주가 상향(긍정)/실적 호조에도 목표주가 하향·디레이팅(경계)/이익 모멘텀·의견 악화(위험)/안정(중립). `M7OutlookAgent`(Phase 1 병렬, model:sonnet)→`nmr_m7.json`→merge `markets.m7_outlook`→빌더 `renderM7Outlook`. **(req7 2026-07-05) 빌더 캡션은 "업데이트:매일" 로 표기하고, verify req21 이 `m7_outlook.as_of == 실행일` 을 강제한다(불일치=발송 차단 — 내장 스냅샷·전일 잔존 방지).** 미수집 시 빌더 내장 스냅샷(M7_OUTLOOK_DEFAULT)으로 비차단 렌더. 상세=`references/agents.md`·`references/data-schema.md`.
**3.1.13 파생시장 포지셔닝 기반 현물 선행신호 분석 (v3.47 신설 — 매일)** — KOSPI200·S&P500·Nasdaq100의 선물 베이시스·순포지션/수급(美 CFTC COT 레버리지·자산운용 / 韓 외국인·기관)·풋콜비율·IV 스큐·딜러 감마(GEX)를 **롤링 z-score(60거래일)** 로 표준화한 현재 스냅샷(④그룹 마지막: 3.1.12 심리 뒤). **매일 갱신**: `deriv_signals/daily_update.py`(무료 소스 yfinance·CFTC COT·네이버 수급·data.go.kr 파생/지수, `secrets.env`의 DATA_GO_KR_KEY)로 DB 갱신 → `deriv_signals/export_snapshot.py` → `nmr_deriv_positioning.json` → merge `markets.deriv_positioning` → 빌더 `renderDerivPositioning`(① 지수 현황 ② 값·z 매트릭스 |z|≥1.5 강조 ③ 활성 신호 ④ 시장해석 ⑤ 종합). 미수집 시 빌더 내장 스냅샷(DERIV_POS_DEFAULT)으로 **비차단 렌더**. 신호=|z|≥1.5(굵게·파랑 양수/빨강 음수). 선행성 검증(신호일→1/3/5일 현물수익률)은 `deriv_signals/` 파이프라인이 산출. 상세=`references/agents.md`·`references/data-schema.md`. `DerivPositioningAgent`(Phase 1, model:sonnet).
**3.2.1 한국 지수 일봉 캔들** — 차트는 반드시 `scripts/gen_kr_candle.py`(다른 한국지수 생성기 금지). 입력 `nmr_kr_ohlcv.json` 의 OHLC = 야후 `^KS11`/`^KQ11` `interval=1d` **일봉**. 거래량은 다음금융 `accTradeVolume` 로 교체(야후 ^KQ11 손상)하고 비거래일 유령행 제거(KRX 거래일 기준). 일별 수급(`*_flows_daily`)=다음금융 `market_index/days`(Chrome 동일출처 fetch, 1년 오름차순). ⚠️ 다음 charts API `/charts/A{code}/days` 는 403 → 한국 종목/ETF 시계열은 **야후 `.KS`/`.KQ`**.
**3.2.2 종목 수급** — 다음금융 `investor_purchase` API(네이버 차단). 코스피·코스닥 외국인·기관 순매수/순매도 상위 종목 → 빌더가 외국인·기관 병합표로 렌더.
**3.2.3 경기선행지수** — **선행종합지수 순환변동치 월별 실측 = `scripts/fetch_leading.py`(sandbox·stdlib, Chrome 불필요)** 가 e-나라지표 통계표 엔드포인트(`showStblGams3.do?stts_cd=105701&idx_cd=1057&freq=M`, UA+Referer+X-Requested-With 헤더)에서 직접 수집 → `nmr_leading_series.json`(`[["YYYY-MM",value]..]` ~29개월)+`nmr_leading.json`(최신 4개월 desc·mom) → `gen_leading_chart.py`. **Phase 1 bash 병렬 tool-call** 로 실행. 실측만(추정 금지), 실패 시 비차단(캐시/직전값 폴백). (구 INDEXerGO echarts·통계표 Chrome 스크래핑·P2 캐시 경로 폐기 — 항상 sandbox 실측.)
**3.2.4 / 3.2.5 KRX 증시 Brief·공매도 데일리 브리프 (v3.54 신설 — DB화)** — open.krx.co.kr 시장동향>종합시황(`MKD01010000.jsp`) 게시판에서 최신 **'KRX 증시 Brief'(→3.2.4)**·**'공매도 데일리 브리프'(→3.2.5)** PDF를 내려받아 **페이지별 PNG 캡쳐**로 보고서에 삽입한다(3.2.3 순환매 테마 뒤). 수집=`scripts/fetch_krx_brief.py`(sandbox·stdlib·Chrome/쿠키 불필요, **Phase 1 bash 병렬 tool-call**): 목록·첨부·다운로드 모두 `GenerateOTP.jspx`→`OPN99000001.jspx`(다운로드는 `file.krx.co.kr/download.jspx`) OTP 체인(실측 명세=스크립트 헤더 주석). **DB화: 회차 마커=게시글 att_seq** — 영구 저장 `_market_report_data/krx_brief/<key>_<att_seq>/`(pdf+PNG, 항목별 최근 5회차 유지)+`db/krx_brief.json`. **기존꺼랑 같으면(마커 불변) 다운로드·캡쳐 생략, 저장본 PNG 재사용**; 새 회차면 다운로드→`pdftocairo -r110`(폴백 pdftoppm) 캡쳐→저장. 재사용/신규 공통 charts/ 복사(`krx_brief_p*.png`·`short_brief_p*.png`)+`$WORK/nmr_krx_brief.json` 산출 → merge `m['krx_brief']`(파일 없으면 DB 폴백) → 빌더 렌더(표준캡션 "업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지"+제목·등록일+캡쳐+출처, 항목 데이터 없으면 자동 생략·비차단). 수집 실패 시 직전 회차(DB) 폴백·`stale_note` 표기. 게이트=verify **req22**(데이터 있는데 캡쳐 PNG 없으면 발송 차단, 데이터 없으면 warning).
**3.2.3 테마·반도체** — 테마 **12종** 고정순서(반도체/AI·전력기기·조선·방산·원자력·증권·로봇·우주·**건설(v3.50, KODEX 건설 117700)**·**건설기계(v3.50.1, KODEX 기계장비 102960 프록시)**·**항공(v3.50.1, TIGER 여행레저 228800 프록시)**·**정유(v3.50.1, KODEX 에너지화학 117460 프록시)**) 10년 월별 series → `gen_rest_charts.py`. 반도체/AI **종목 10 + ETF 정확히 20**(다음금융 AUM 상위, 단일종목 레버리지 포함) 추세차트.
**3.1.9 메모리+HBM 지표 대시보드 (구 3.2.5)** — `gen_hbm_dashboard.py` → `charts/hbm_dashboard.png`(6패널 + HBM 3사 EPS/PER 표). HBM 스팟가격·ASP·출하량·점유율·EPS/PER 은 무료 실시간 API 가 없으므로 **HBMAgent 가 WebSearch+뉴스(TrendForce·각사 실적 컨센서스·언론)로 분기 추정치**를 `nmr_hbm.json` 으로 저장(스키마=`references/data-schema.md`). **모든 수치는 '추정' 명시**, 확인 불가 분기는 빈값. `nmr_hbm.json` 미수집 시 내장 예시·추정값으로 차트 생성('예시·추정' 표기 유지) — 3.1.9 는 비차단(차트 없으면 섹션 자동 생략).
**3.3.1 빅테크 CAPEX** — MSFT·Alphabet·Amazon·Meta 연간. 실적값은 **FMP `statements` cashflow 의 `capitalExpenditure`**(절대값)로 정확 수집, 추정연도(**2027(E) 항상 채움**)만 WebSearch. 표 전체폭. **(req8) 미확인 칸은 빈값으로 두고 "확인불가"/"미공개" 문자열 금지 — 빌더가 전 기업에서 데이터가 전무한 (전망)연도 컬럼을 통째로 드롭하고 "확인불가"→"-"로 정규화한다. 2028~2029(E)는 회사 가이던스/애널리스트 컨센서스가 확인될 때만 채우고, 없으면 빈값(해당 컬럼 자동 드롭).** **(v3.9.0) 표 맨 아래 차트 2종(`gen_capex_chart.py`): 5개사(+오라클) CAPEX 스택바+Capex/매출 비율선, FCF 추이선 — 2023~2025 실적·2026 가이던스·2027~2029 전망(E). 차트는 내장 기본 데이터로 항상 생성되며, `bigtech_capex.{capex,rev,fcf}_series` 제공 시 라이브 오버라이드.**
**3.3.2 FOMC 점도표** — 2026·2027·2028말·장기중립 각 행에 **jun·mar 중간값 모두**(빈칸 금지).
**3.3.3 HY 스프레드** — FRED `BAMLH0A0HYM2` 일별 series = `fetch_kr.py` 가 **FRED API 키 직접 호출**(1순위, `nmr_fred.py`·SECURITY/secrets.env `FRED_API_KEY`) → equibles 미러 → 영구캐시 폴백 → `gen_hy_chart.py` → `charts/hy_oas.png`. ⚠️ FRED 는 ICE 라이선스로 이 시리즈를 **최근 약 3년만 제공(API 키로도 동일 — 2026-07-07 실측 확인)**, 초과 시 한계 명시.
**3.3.x 미국 ETF·리밸런싱** — `us_etfs` 30종(③ 테마에 **DRAM=Roundhill Memory ETF** 항상 포함). S&P500·나스닥100 정기 리밸런싱(편입/편출·일정·룰변경).
**3.4.1 아시아 주요 ETF (한국 상장 · v3.46 신설)** — 3.4 아시아 증시 표 바로 뒤에 한국거래소 상장 아시아 국가·테마 대표 ETF 14종을 6그룹(① 아시아 통합·② 중국·③ 일본·④ 대만·⑤ 인도·⑥ 베트남)으로 묶어 `us_etfs` 와 동일한 추세표(현재가·1일·1주·1개월·3개월·6개월·1년·추세(1Y 스파크라인)·추세평가)로 렌더한다. 시세=야후 `<코드>.KS` 일봉 2년 → `scripts/fetch_asia_etf.py`(sandbox·stdlib·스레드 병렬, Phase 1 bash 병렬)가 merge.py `ret()` 동일 산출로 `nmr_asia_etf.json`(그룹별 rows)+`nmr_asia_etf_series.json`(스파크라인) 생성. merge `m['asia_etfs']=LCF('nmr_asia_etf.json')` → 빌더 `renderAsiaEtfs`(3.4 뒤, 데이터 없으면 자동 생략). 차트=`gen_rest_charts.py` 가 `charts/spark_aetf_<코드>.png` 생성. 종목: ACE 아시아TOP50S&P(277540)·TIGER 차이나CSI300(192090)·KODEX 차이나H(099140)·TIGER 차이나항셍테크(371160)·TIGER 차이나과창판STAR50합성(414780)·KODEX 차이나심천ChiNext합성(256750)·TIGER 일본니케이225(241180)·KODEX 일본TOPIX100(101280)·TIGER 일본반도체FACTSET(465660)·TIGER 대만TAIEX선물H(253990,야후 ETF 이력 미제공→기초지수 TAIEX(^TWII)로 수익률·추세 대체·현재가는 ETF 실값)·TIGER TSMC밸류체인FACTSET(453950,대만 반도체 밸류체인)·TIGER 인도니프티50(453870)·TIGER 인도빌리언컨슈머(479730)·ACE 베트남VN30합성(245710). 추정 금지·이력 없으면 '-'(비차단). **(v3.50) 미국거래소 상장 아시아 ETF 15종을 같은 나라 그룹에 병합**(달러 종가 `$` 표기, `ccy:"USD"`): 중국·홍콩=MCHI·FXI·KWEB·EWH / 일본=EWJ·DXJ / 대만=EWT / 인도=INDA / 베트남=VNM·VNAM / **⑦ 동남아(sea) 신설**=EIDO(인니)·EPHE(필리핀)·EWM(말련)·THD(태국)·EWS(싱가포르) — 총 29종(한국 14+미국 15), fetch_asia_etf.py 가 미국 티커는 `.KS` 미부착·Daum 폴백 없이 야후 직수집, comment 는 한국/미국 분리 평균.
**3.6/3.7 북미&중남미·호주&중동 증시 (v3.50 신설)** — 3.5.1 유럽 ETF 뒤. 미국 상장 국가 대표 ETF 추세표(3.5.1과 동형·달러 기준): 3.6=EWW(멕시코)·EWZ(브라질)·EWC(캐나다), 3.7=EWA(호주)·KSA(사우디)·UAE·QAT(카타르). `fetch_us.py` 의 `AMER_ETF`/`AUME_ETF` 맵 → `nmr_amer_etf.json`/`nmr_aume_etf.json` → merge `m['americas_etfs']`/`m['aume_etfs']` → 빌더 `renderAmericasEtfs`/`renderAumeEtfs`(데이터 없으면 자동 생략). 스파크=etfseries 편입으로 `charts/spark_etf_<sym>.png` 자동 생성. 게이트=verify(항목수 3/4·스파크 커버리지 warning).
**[부록C] AI 반도체 밸류체인 (v3.51 신설 · v3.52.1 46종 확장)** — 부록B 뒤. 글로벌 개별종목 **46종**을 8개 분류(①빅테크 수요처5 ②팹리스/가속기8 ③파운드리/제조3 ④메모리2 ⑤소재/부품2 ⑥전공정 장비7 ⑦후공정/패키징8 ⑧데이터센터 전력·인프라11)로 묶은 추세표(현재가/1일/1주/1개월/3개월/6개월/1년/추세1Y/추세평가). `scripts/fetch_appc.py`(sandbox·stdlib·스레드, Phase 1 bash 병렬)가 야후 일봉 2년 → `nmr_appc.json`(그룹별 rows·ccy)+`nmr_appc_series.json` → merge `m['appendix_c']` → 빌더 `renderAppendixC`(데이터 없으면 자동 생략, 통화 접두 $/¥/₩=미/일/한). 스파크=gen_rest_charts `charts/spark_c_<심볼(.→_)>.png`. 게이트=verify [AppC](46종 미달·스파크 커버리지 warning). 멤버십 변경 시 fetch_appc.py `ROWS` 갱신(+부록D 관계도 assets/gen_appd_valuechain.py 재생성). 커버리지 근거(2026-07-05 헤지 검토): 테스트·그라인더(Advantest·Disco)/인터커넥트 짝(ALAB)/웨이퍼 짝(SUMCO) 보강, (v3.52.1) ORCL·이수페타시스(007660)·AMKR 추가로 부록D 관계도와 46종 동기화.
**[부록D] AI 반도체 밸류체인 관계도 (v3.52 신설)** — 부록C 뒤. 부록C 종목들이 '왜 중요한지·어떤 해자를 가졌는지'를 수요(빅테크 CAPEX)→설계→장비·소재→제조→후공정→전력 인프라 6단 흐름 + 해자 배지(파랑=독점·준독점, 황색=과점·복점·양강)로 그린 **정적 관계도 이미지 3장**(부록C와 동일 46종 — v3.52.1 동기화). 원본=repo `assets/appd_valuechain_{1..3}.png`(생성기 `assets/gen_appd_valuechain.py` — weasyprint+pdftocairo, **종목 구성 변경 시에만 1회 재실행**; 매일 파이프라인 아님). 빌더 `renderAppendixD` 가 `charts/` 미존재 시 `/sessions/*/mnt` 에서 assets 를 find→PNG 무결성(IEND) 검증→잘림이면 `git show HEAD:assets/...` 폴백→charts/ 복사 후 삽입(TOC 부록D 포함, 이미지 없으면 자동 생략·비차단). 수집·에이전트·verify 게이트 변경 없음.
**5 환율 스파크라인** — 원화 5쌍(usd/eur/jpy/cny/hkd_krw) 1년 주봉.
**6.2/6.3 코인** — BTC·ETH·XRP·SOL 1년 + 공포·탐욕 1년 차트. 김프 4종(특히 SOL) 항상 채움.
**7 한국 주요 증권사(10) = 텔레그램 7 + Chrome 3** — 신한·키움·메리츠·하나·교보·유안타·현대차는 **공식 텔레그램** `scripts/fetch_brokers_tele.py`(curl·bash 병렬, Chrome 불필요). 삼성·미래에셋·한투는 **메인세션 Claude in Chrome — `browser_batch` 로 3탭 navigate 를 묶고 `javascript_tool` 타깃추출(단계별 screenshot 금지·토큰 절감)**(공개 리서치 페이지 정상 접속됨 — 삼성=`samsungpop … research_pop.jsp#bm`(팝업'확인'), 미래에셋=`miraeasset … list.do?categoryId=1521`, 한투=`koreainvestment … Strategy.jsp?jkGubun=99`·`34`; 상세 URL `references/agents.md`. get_page_text 덤프 금지; "미확인/로그인전용" 오판 금지). 핵심 6사 풀·기타 4사 1줄 요약.
**7·8 신선도** — Daily≤D-1, Weekly/Monthly≤D-3(주말은 금요일까지). 미충족이면 **stale 로 채우지 말고 빈값**("기준일 충족 최신 공개 자료 미확인"). 글로벌 IB(UBS·GS·JPM·MS·BlackRock)는 WebSearch+Bigdata MCP(Chrome 금지=메인세션과 충돌).
**[DB화 v2 · 통합 DB — 마커체크 폐지] (2026-06)** — 점도표·버핏13F·지수리밸런싱·HY·주의사항/출처를 포함한 **모든 비매일 지표**는 통합 DB(`_market_report_data/db/`, 표 rows + **차트 시계열** 모두)에 저장한다. **대원칙: 매 실행 항상 최신값 조사**하되, 발표주기가 매일이 아닌 지표는 변동 시에만 DB 갱신·미변동이면 DB값 그대로 사용하고 캡션 "업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지" 를 표기한다. 차트 시계열은 `nmr_db.dbseries`(날짜 union 누적)로 매 실행 누적돼 부실 수집 회차도 과거 DB로 보강된다(기준금리·곡선·us2y·물가·BEI·고용). **구 마커체크(nmr_cache.py·Phase 1.0)는 폐지** — 별도 마커 관측 없이 통합 DB 가 변동체크·재사용을 담당한다. (CAPEX 표=차트 풀매트릭스 보강·HBM 누적 DB 동일.)
**차트 생성(Phase 1.5)** — `gen_kr_candle.py` · `gen_leading_chart.py` · `gen_hy_chart.py` · `gen_rest_charts.py` · `gen_capex_chart.py` · `gen_hbm_dashboard.py` · `gen_macro_charts.py` · `gen_cli_chart.py` · `gen_customs_chart.py` **9종만** 사용(`gen_tech_charts`·`gen_all2`·`gen_semi_etf`·`gen_kr_tech`·`gen_kr_extra`·`gen_kr_flows` 는 폐기). `gen_capex_chart.py` → `charts/capex_stack_ratio.png`·`charts/capex_fcf.png`(3.2.1 빅테크 CAPEX 차트, cwd 상대 출력). `gen_hbm_dashboard.py` → `charts/hbm_dashboard.png`(3.2.5 메모리+HBM 대시보드). `gen_macro_charts.py` → `charts/macro_*.png`·`charts/spark_*.png`(3.1 주요지표 13종; `nmr_macro.json` 있으면 라이브, 없으면 내장 예시·추정값). **(R1) gen_macro_charts.py 는 반드시 `NMR_OUT="$WORK"` 환경변수로 실행** — us2y_daily 시계열을 `$WORK/nmr_indexseries.json` 에 주입해 美2년물 스파크가 정상 생성된다(미설정 시 상위 outputs 에 기록돼 美2년물 스파크가 10년물과 동일 모양으로 깨짐). **고용은 7패널 항상 표시**(맨앞=초기 실업수당 청구건수, 빈 시계열은 '데이터 미확보' 자리표시). **(req1·req2 2026-07-05) NFP·소매판매는 레벨·증감 "혼합" 시계열 내성 변환(_mixfix: 연속 레벨 구간만 차분/전월비 변환, 레벨→증감 경계 미변환)으로 절벽 스파이크를 방지한다 — db/series_emp_nfp·retail 오염분은 2026-07-05 클린 재작성.** `gen_leading_chart.py` → `charts/leading_cycle.png`(3.2.3 — 입력 `nmr_leading_series.json` = `fetch_leading.py` 실측 ~29개월). `gen_cli_chart.py` → `charts/oecd_cli.png`(3.1.4 OECD CLI 전 국가 통합 — 입력 `nmr_oecd_cli.json`(신규 스크랩) 또는 DB `db/oecd_cli.json` 폴백, 항상 생성 가능). `gen_customs_chart.py` → `charts/수출_전체_24개월.png`·`charts/수출_반도체_24개월.png`(3.1.10 관세청 수출 잠정치 2년치 그룹막대 — 입력 `nmr_customs.json`(변경시) 또는 DB `db/customs.json` 폴백; fresh 없고 두 차트 존재 시 스킵→기존 유지).
**작성주체 익명화** — 표지·면책·13장에서 'Claude' 미표기('AI Research'/'AI').

## 보고서 품질 기준 (반드시 충족)

생성되는 docx 는 다음 10개 항목을 모두 포함해야 한다. 하나라도 누락되면 재작업 대상.

1. **글로벌 Top News 10** — 헤드라인 + 2~4문장 요약 + 임팩트 라벨(`▲ 강세`/`▼ 부정`/`■ 양면` — 기호+색 구분). **헤드라인·요약은 항상 한글**(외신도 한글 번역, 출처/URL 만 원문)
2. **글로벌 주요 이벤트 캘린더** — ① 향후 1개월 전체 중요도(★~★★★) ② 1개월~1년 중장기는 ★★★만 (날짜·지역·이벤트·예상 영향). **빅테크 주요 이벤트(아이폰·갤럭시 언팩·GTC·CES·OpenAI 신모델 등)가 향후 일정에 있으면 누락 금지** (NewsAgent 가 별도 검색으로 확인)
3. **단·중·장기 추세** — 모든 자산을 1주/1개월/3개월/6개월/1년 변화율로 제시
4. **글로벌 증시 풀커버리지** — 한국(코스피·코스닥)·미국·홍콩·중국·일본·**대만**·인도·베트남·유럽 + **(v3.50) 북미&중남미(3.6: EWW·EWZ·EWC)·호주&중동(3.7: EWA·KSA·UAE·QAT)**
5. **매크로 지표** — 달러지수(DXY), VIX, 美 10년 국채금리
6. **원자재 풀커버리지** — 에너지(WTI·천연가스) + 금속(금·은·구리) + 농산물(4.3: 핵심곡물[옥수수·대두·소맥] + 기후충격[설탕·커피·오렌지주스] + 비용·종합[CRB 상품지수·BDI 운임, 프록시 ^TRCCRB·BDRY] + 농업ETF[DBA] + 비료·농기계 대장주[DE·NTR]) — 각 소그룹 추세표(현재가/1일/1주/1개월/3개월/6개월/1년/추세1Y/추세평가)
7. **주요 환율 추세** — USD/EUR/JPY/CNY/HKD vs KRW 단·중·장기 추세 + **달러인덱스(DXY)** 병기 + 원화 톤
8. **암호화폐** — 시장 개요 + 공포·탐욕 지수(현재/1일/1주/1개월) + 김치프리미엄(BTC/ETH/XRP/SOL)
9. **글로벌 주요 IB 리서치** — UBS·Goldman Sachs·J.P. Morgan·Morgan Stanley·BlackRock 하우스 뷰 (한국 주요 증권사와 동일 구조)
10. **종합 분석 + 포트폴리오** — 매크로 톤·테마·리스크 + 공격형/중립형/안정형 3개 모델 + 액션 아이템 (각 포트폴리오 `basis` 산출근거 포함)

11. **국내 순환매 테마·수급** — 외국인 순매수(코스피/코스닥) + 경기선행지수 순환변동치 + 순환매 테마별 현황(반도체·조선·방산·전력·증권·로봇·우주)
12. **미국 신용·ETF·리밸런싱·CAPEX** — 하이일드(HY) 신용 스프레드(OAS·유효수익률·국채분해) + 주요 미국 ETF(지수·섹터·테마·방어형 29종, 1년 추세) + 지수 정기 리밸런싱(S&P 500·나스닥 100 편입/편출·일정·룰변경) + AI 빅테크 자본지출(CAPEX)
13. **전략광물·배터리 금속** — 리튬·니켈·코발트·우라늄·희토류·흑연(ETF 프록시+현물) + 빅테크 신제품·신기술 핵심 이벤트

추가 품질 기준 (v3.3.0 반환각 보완):
- **출처(grounding)**: Top News 와 증권사/IB 대표 리포트는 원문 링크(source_url)를 포함한다. 출처를 댈 수 없는 항목은 수록하지 않는다.
- **수치 근거**: 포트폴리오 기대수익·MDD 는 단일 false-precision 숫자가 아니라 계산근거 또는 범위+가정으로 표기하고 `basis` 를 명시한다.
- **디스클레이머**: 표지 AI·환각 경고 배너와 14장 출처·면책 고지가 반드시 포함된다.

## 워크플로우 개요

```
[Phase 0: 사전 점검]  실행 모드 판정(예약/일반) / 날짜·시작시각 기록 / 연결 폴더(D:\claudeCowork) / Chrome / 빌드환경·무결성(자동복구)
        ↓
[Phase 1.0: (폐지) 마커체크 제거]  비매일 지표는 Phase 1 에서 항상 수집 시도 → 통합 DB(merge.py + nmr_db.dbseries)가 변동체크·미변동 재사용·차트 시계열 누적을 담당(구 nmr_cache 마커체크 미사용)
        ↓
[Phase 1: 병렬 수집 — 모든 수집 에이전트를 단일 메시지로 1회 발행 (P3 통합) · 수집 에이전트 model:sonnet]
  ├─ News / Crypto(정성: CoinInfo) / Macro(FMP economics·treasury + FRED → nmr_macro.json)
  ├─ KoreaSemiTheme(선정·AUM·노트) / GlobalSecurities  + (상시 수집 — DB가 변동체크·재사용) USMacroExtras·IndexRebalance·NewsBerk·HBM
  ├─ [bash 병렬 tool-call] scripts/fetch_us.py + fetch_kr.py + fetch_semi.py + fetch_leading.py + fetch_asia_etf.py + fetch_appc.py + fetch_brokers_tele.py + fetch_krx_brief.py  (美/글로벌·한국 시세·시계열·경기선행·부록C 밸류체인·증권사 텔레그램 7사·KRX 브리프 2종, Chrome 불필요)
  ├─ [bash 비차단] deriv_signals/run_for_report.py "$WORK/nmr_deriv_positioning.json" "<_market_report_data>/deriv_signals.db"  (3.1.13 파생 포지셔닝 라이브 — 런처가 ①의존성 자동설치 ②DB없으면 run_backfill(1회 1년)·있으면 daily_update ③export_snapshot→JSON. **완전 비차단**: 실패해도 빌더 내장 스냅샷(DERIV_POS_DEFAULT)으로 렌더. DB는 다른 DB섹션과 동일하게 `_market_report_data\deriv_signals.db` 영구 경로에 두어 매 실행 재백필 방지(2번째 인자 또는 DERIV_DB 환경변수). data.go.kr 키는 상위 `SECURITY/secrets.env` 자동 탐색 — 없으면 KOSPI200 선물/옵션만 skip. 큰 모듈 truncation 방지 위해 $RUN 추출본에서 실행)
  └─ SecuritiesAgent=삼성·미래에셋·한투 3사만 메인세션 Chrome(`browser_batch` 3탭 navigate·`javascript_tool` 타깃추출·단계별 screenshot 금지) + KOSIS OECD CLI 자료갱신일 체크 1탭(3.1.4 — reuse면 스킵); 텔레그램 7사는 fetch_brokers_tele.py. 배치 발행 직후 동시 진행
        ↓
[Phase 1.5: 차트 생성 (분석 전)]  gen_kr_candle.py·gen_leading_chart.py·gen_hy_chart.py·gen_rest_charts.py·gen_capex_chart.py·gen_hbm_dashboard.py·gen_macro_charts.py·gen_cli_chart.py → charts/*.png
        ↓
[Phase 2: AnalysisAgent 단독 호출 · model:opus]  Phase 1 수집 데이터+차트를 입력으로 9~12장(종합분석·자산별견해·포트폴리오·액션) 도출
        ↓
[Phase 3: 데이터 종합 → JSON 저장 + 유효성 검증]
        ↓
[Phase 3.5: 반환각 점검 — 최소화(P3)]  verify_report.js 코드 게이트(req9~12: 누락섹션·출처·basis·날짜) + 메인세션 인라인 점검(별도 에이전트 없음)
        ↓
[Phase 4: 보고서 생성]  node build_report.js <json> <out.docx> → 연결 폴더에 저장
        ↓
[Phase 4.5: 품질 게이트 + GOODREPORT 비교 (v3.6.32 — 차단)]  node verify_report.js → problems 있으면 발송 보류·사용자에 질문(조용히 -/stale 통과 금지)
        ↓
[Phase 5: 이메일 발송]  Claude in Chrome → 로그인된 Gmail 직접 발송(docx 첨부) + 모드별 수신자 파일 (references/email-sending.md)
        ↓
[Phase 6: 결과 보고]  헤드라인 3개 + 포트폴리오 톤 + 시작/완료/소요시간
```

## Phase 0: 사전 점검

0. **실행 모드 판정 (v3.4.3 — Phase 5 수신자 결정)**: 이번 실행이 **예약(scheduled)** 인지 **일반(normal)** 인지 먼저 판정한다.
   - **예약 모드 조건** (하나라도 해당): 스킬 인자(ARGUMENTS)에 `scheduled`/`schedule`/`예약` 포함 / 예약 작업 프롬프트가 예약 실행임을 명시(예: "이 실행은 예약 실행") / 세션이 사용자 입력 없이 스케줄러로 자동 시작됨.
   - **일반 모드**: 그 외 모두 (사용자가 채팅에서 직접 `/namoobi-market-report` 실행, 인자 `direct` 등).
   - 판정 결과를 메모해 두고(예: `$WORK/nmr_mode.txt` 에 `scheduled` 또는 `normal` 기록) Phase 5 에서 수신자 파일을 고른다:
     예약 → `SECURITY\예약메일수신자.txt`, 일반 → `SECURITY\메일수신자.txt`. (애매하면 **일반 모드**로 처리하고 Phase 6 에 모드를 명시한다.)
1. **날짜·시작시각**: `TZ=Asia/Seoul date '+%Y-%m-%d %H:%M:%S'` 로 오늘(KST)과 **워크플로우 시작시각**을 확정. `YYYYMMDD` 압축형도 함께 만든다. 시작시각(사람이 읽는 형식 + epoch)은 Phase 6 소요시간 계산에 쓰므로 아래 3번에서 `$WORK/nmr_start_epoch.txt` 로 기록한다.
2. **연결 폴더 확인**: D:\claudeCowork 가 세션에 연결돼 있는지 확인. **`request_cowork_directory` 는 절대 호출하지 않는다**(매 실행 권한창의 원인). 미연결이면 outputs 에서 진행하고, Phase 6 보고에 "연결 폴더 미연결 — docx 사본 미생성·메일 첨부 불가"를 명시한다.
3. **Chrome (v3.53 — 미연결 시 직접 실행 루틴)**: `mcp__Claude_in_Chrome__list_connected_browsers` 로 연결 확인. **일반(normal) 브라우저 창**이 있어야 한다. (발송 직전이 아니라 지금 미리 확인해 두면 Phase 5 실패를 줄인다.) **결과가 빈 배열(`[]`)이면 사용자에게 떠넘기지 말고 computer-use 로 크롬을 직접 실행한다**:
   1. `mcp__computer-use__request_access(apps=["Google Chrome"], reason="크롬을 실행해 Claude 확장을 연결하고 시황 보고서를 Gmail 로 발송")` — 브라우저는 tier "read" 라 "It is rare for this to be required…" 경고가 뜨면 **같은 턴에서 즉시 한 번 더** `request_access` 를 호출해 확정한다(권한창은 그 재시도가 띄운다). 여기서 얻는 read 권한은 **크롬을 포그라운드로 띄우기(`open_application`)** 용이며, 실제 웹 조작은 전부 Claude-in-Chrome 확장으로 한다.
   2. `mcp__computer-use__open_application(app="Google Chrome")` → `wait(3초)` → `list_connected_browsers` 재확인.
   3. **프로필 선택 화면("Chrome 사용자 선택")이 뜨면**(computer-use `screenshot` 로 확인) 브라우저는 read 전용이라 Claude 가 클릭할 수 없다 → 사용자에게 **namoobi 프로필 카드를 한 번 클릭**해 달라고 요청(1회 클릭이면 확장이 붙는다). 프로필 피커를 끄고 싶으면 크롬 프로필 설정에서 "시작 시 표시" 체크 해제를 안내한다.
   4. 확장이 붙어 `list_connected_browsers` 가 기기를 반환하면 그대로 진행. 재실행·프로필 클릭 후에도 계속 `[]` 이면 그때만 Phase 6 에 "Chrome 미연결 — 메일 미발송(docx 는 연결 폴더 저장 완료)"으로 보고하고 발송은 보류한다. (상세 절차·함정은 `references/email-sending.md` "Chrome 미연결 시 직접 실행" 참조.)
4-0. **(v3.42 근본해결) 실행 스크립트는 설치본이 아니라 로컬 repo git HEAD 에서 추출 — 마운트 잘림 영구 회피**:
   D: 마운트가 큰 파일(merge.py·gen_macro_charts.py 등)을 **설치 시점에 간헐적으로 잘라 기록**해 `.remote-plugins` 설치본이 손상될 수 있다(자가점검 SC=2의 실제 원인). 따라서 **매 실행, 로컬 repo(`D:\claudeCowork\namoobi-market-report`)의 git 객체에서 완전한 스크립트를 추출해 그걸로 실행**한다(git show=마운트 미경유·절대 안 잘림):
   ```bash
   SRC0="$(dirname "$(find /sessions/*/mnt/.remote-plugins -path '*namoobi-market-report/scripts/build_report.js' 2>/dev/null | head -1)")"
   RUN="$(python3 "$SRC0/nmr_runsrc.py" 2>/dev/null | sed -n 's/^RUNSRC=//p')"
   if [ -n "$RUN" ] && [ -f "$RUN/merge.py" ]; then SRC="$RUN"; echo "✅ git HEAD 완전 스크립트로 실행: $SRC"; else SRC="$SRC0"; echo "⚠️ repo 없음 → 설치본 사용(잘림 주의)"; fi
   ```
   이후 모든 스크립트 호출은 `$SRC` 를 쓴다. (`nmr_runsrc.py` 가 36파일을 git 에서 추출·무결성검증 후 경로 반환. 자가점검은 참고용이 되고, 실행 자체는 항상 완전판으로 보장.)

4. **빌드 환경 준비 + 무결성 검사·자동복구** — 플러그인 마운트는 읽기 전용이므로 쓰기 가능한 outputs 에 복사해 빌드한다:

```bash
SRC="$(dirname "$(find /sessions/*/mnt -path '*namoobi-market-report/scripts/build_report.js' 2>/dev/null | head -1)")"
WORK="$(ls -d /sessions/*/mnt/outputs 2>/dev/null | head -1)/nmr_build"
rm -rf "$WORK"; mkdir -p "$WORK"
date +%s > "$WORK/nmr_start_epoch.txt"   # v3.2.4 시작시각 기록
TZ=Asia/Seoul date '+%Y-%m-%d %H:%M:%S' > "$WORK/nmr_start_human.txt"
echo "$(date +%s) phase0_setup" > "$WORK/nmr_phase_times.txt"   # v3.21 Phase별 계측 시작
cp "$SRC/build_report.js" "$SRC/package.json" "$WORK/"
cp -r "$SRC/fonts" "$WORK/fonts" 2>/dev/null && echo "폰트 OK ($(wc -c < "$WORK/fonts/nmr_kr.ttf")B)"  # v3.4.2 한글 임베드 폰트
cd "$WORK"
[ -d "$WORK/node_modules/docx" ] || npm install docx --no-fund --no-audit
node -e "require('$WORK/node_modules/docx'); console.log('docx OK')"
# 무결성 검사 (v3.2.6) — 샌드박스 마운트가 큰 파일을 잘라 읽는 사례가 있음 (호스트 원본은 정상)
if ! tail -1 "$WORK/build_report.js" | grep -q "EOF — namoobi-market-report"; then
  echo "⚠️ 잘림 감지 → git 원본에서 재복사"
  cp "$SRC/build_report.js" "$WORK/build_report.js"
fi
tail -1 "$WORK/build_report.js" | grep -q "EOF — namoobi-market-report" \
  && node --check "$WORK/build_report.js" && echo "script OK" \
  || echo "❌ 여전히 잘림 — 호스트 git 원본을 Read 도구로 읽어(마운트 bash 금지) WORK 에 재구성할 것"
```

> ⚠️ `/tmp` 는 이전 세션 잔존물로 권한 오류가 날 수 있으니 사용하지 말 것. 항상 outputs 하위에서 빌드.
> ⚠️ 마운트 읽기 잘림이 의심되면(EOF 마커 없음) 호스트 git 원본을 **Read 도구** 또는 `git show HEAD:<path>` 로 읽어 WORK 에 재구성한다 — 둘 다 잘리지 않는다.

5. **(v3.39 필수) 설치본 자가점검 — stale 방지**: 매 실행, 빌드에 쓸 `$SRC`(현재 실행 중인 설치본 스크립트)가 GitHub repo HEAD 와 일치하는지 확인한다.

```bash
TOKP="$(ls /sessions/*/mnt/claudeCowork/SECURITY/githubtoken.txt 2>/dev/null | head -1)"
python3 "$SRC/nmr_selfcheck.py" "$SRC" "$TOKP"; SC=$?
```

`SC=2`(설치본이 GitHub 보다 옛 버전 = 플러그인 미업데이트)면 **여기서 멈추고** 사용자에게 알린다: "플러그인을 업데이트해야 최신 수정본이 적용됩니다(설정→Capabilities/플러그인). 지금 실행하면 옛 결과가 나옵니다 — 그래도 진행할까요?" 승인 없이는 진행하지 않는다. (`SC=0`=최신→진행 / 네트워크·토큰 실패 등 기타 코드→경고만 남기고 진행.) 이 점검이 "고쳐서 push 했는데 새 실행에 반영 안 되는" 문제를 매 실행 입구에서 잡는다.

## ⏱ Phase별 계측 (v3.21 — 병목 가시화)

각 Phase **시작 시** 1줄로 벽시계를 마킹한다(저비용·비차단). 어느 Phase(수집/발송/게이트 재작업)에 시간이 쏠리는지 매 실행 수치로 확인하기 위함이다.

- **마킹**(각 Phase 진입 직후 1회): `echo "$(date +%s) <라벨>" >> "$WORK/nmr_phase_times.txt"` — 새 bash 호출이라 `$WORK` 가 비었으면 `WORK="$(ls -d /sessions/*/mnt/outputs 2>/dev/null|head -1)/nmr_build"` 로 재유도. 라벨 순서: `phase1_collect`(Phase 1 배치 발행 직후)·`phase1_5_charts`·`phase2_analysis`·`phase3_merge`·`phase4_build`·`phase4_5_gate`·`phase5_send`.
- **리포트**(Phase 6): 발송 확인 직후 `phase6_report` 마킹 후 `SRC="$(dirname "$(find /sessions/*/mnt -path '*namoobi-market-report/scripts/nmr_timer.py'|head -1)")"; python3 "$SRC/nmr_timer.py" report "$WORK/nmr_phase_times.txt"` 출력을 결과 보고 [실행 시간] 아래에 붙인다.
- 마킹 일부 누락돼도 비차단 — 기록된 구간만 집계된다.

## Phase 1–2: 서브에이전트 호출

상세 프롬프트와 각 에이전트의 반환 JSON 스키마는 **`references/agents.md`** 를 읽고 그대로 사용한다.

핵심 규칙:
- **(v3.16 모델 티어링) 서브에이전트 `model` 인자를 반드시 명시한다.** 수집 에이전트(News·Crypto·Macro·KoreaSemiTheme·GlobalSecurities·USMacroExtras·IndexRebalance·NewsBerk·HBM)는 전부 **`model:"sonnet"`**, 종합·추론하는 AnalysisAgent(Phase 2)만 **`model:"opus"`**. 미지정 시 부모(Opus) 상속이라 토큰·지연이 커지므로 누락 금지 — 수집은 검색→추출→저장 작업이라 Sonnet 으로 충분하고 "추정 금지·도구값만" 규칙으로 품질이 유지된다.
- Phase 1의 **수집 에이전트를 단일 메시지에서 1회 동시 발행** (general-purpose · model:sonnet): News·Crypto(정성)·KoreaSemiTheme(선정·AUM·노트)·GlobalSecurities·**MacroAgent(3.1 주요지표: FMP economics/treasury + FRED API → nmr_macro.json)** + **(상시 수집 — DB가 변동체크·재사용)** USMacroExtras(점도표 due 또는 CAPEX 창)·IndexRebalance(리밸런싱 due)·NewsBerk(ai_trends 때문에 상시, 단 13F 서브태스크는 berkshire due일 때만)·HBM(분기 창). **마커 reuse·창밖이면 해당 에이전트 미발행·캐시 재사용.** **같은 메시지에서 `scripts/fetch_us.py`·`fetch_kr.py`·`fetch_semi.py`·`fetch_leading.py`·`fetch_customs.py`(3.1.10 관세청 수출 잠정치 — 매일 최근4개월 해시로 변경체크, 변경시만 전체백필)·`fetch_asia_etf.py`(3.4.1 아시아 ETF 29종)·`fetch_appc.py`([부록C] AI 반도체 밸류체인 43종)·`fetch_krx_brief.py`(3.2.4/3.2.5 KRX 증시 Brief·공매도 데일리 브리프 — 회차 att_seq 변동시만 다운로드·캡쳐, 불변이면 저장본 재사용) 를 bash 병렬 tool-call** 로 실행(美/글로벌·한국 시세·시계열, 스레드 병렬 각 ~1~10초; 에이전트 아님). **SecuritiesAgent=삼성·미래에셋·한투 3사만 메인세션 Chrome(`browser_batch` 로 3탭 navigate 묶고 `javascript_tool` 타깃추출, 단계별 screenshot 금지·get_page_text 덤프 금지); 텔레그램 7사(신한·키움·메리츠·하나·교보·유안타·현대차)는 `fetch_brokers_tele.py`.** 같은 Chrome 배치에 **KOSIS OECD CLI 자료갱신일 체크 1탭**을 추가한다(3.1.4 규칙 — `nmr_db.py check oecd_cli <자료갱신일>` reuse면 그대로, due면 전체기간 시계열 추출→`nmr_oecd_cli.json`).
- AnalysisAgent 는 6개 결과를 모두 받은 뒤 **마지막에 단독 호출**(general-purpose · model:opus). 6개 JSON 을 프롬프트에 붙이는 대신 "outputs 의 nmr_*.json 6개를 bash 로 읽으라"고 지시해도 된다 (재타이핑 절감).
- **(v3.2.3 속도)** MarketsAgent·CommoditiesAgent 프롬프트에 `period="1y", interval="1wk"`(주봉) 사용을 명시한다 — 일봉 금지. 1주 변화율은 직전 주봉 종가 기준.
- **(v3.2.3 속도)** 각 에이전트 프롬프트에 "최종 JSON 을 outputs 하위 `nmr_<이름>.json` 파일로 bash heredoc 저장하고, 응답으로는 저장 경로와 1줄 요약만 반환하라"를 명시한다. 메인 세션이 긴 JSON 을 받아 재타이핑하는 것을 금지.
- MCP 도구는 deferred 상태일 수 있으므로 각 에이전트 프롬프트에 "먼저 `ToolSearch` 키워드 검색(예: `+UsStockInfo historical`, `+CoinInfo fear greed`)으로 도구를 로드한 뒤 사용하라"고 명시한다. **UUID 가 포함된 도구명을 하드코딩하지 말 것** — 서버 ID는 세션마다 다를 수 있다.
- 서브에이전트가 API 오류(소켓 끊김 등)로 결과 파일을 저장하지 못했으면 해당 에이전트만 재실행한다 (파일 존재 여부로 판단).
- 실패한 데이터는 null / 빈 배열로 두고 진행한다. 빌더가 "-" 로 렌더링한다.

## Phase 3: 데이터 종합 및 저장

에이전트·스크립트가 저장한 `nmr_*.json` 을 **`python3 scripts/merge.py $WORK YYYYMMDD` 로 병합**해 (메인 세션 재타이핑 금지)
outputs 하위 `_market_report_data/report_data_YYYYMMDD.json` 으로 저장한다(merge.py 가 수익률·추세·경기선행 코멘트 계산, longterm 빈event 필터, metadata 추가).

> ⚠️ 직접 heredoc 작성이 불가피한 경우: 한글 JSON 은 단일 인용 heredoc(`<<'JSONEOF'`)으로 변수확장을 막을 것.
> 병합 후 JSON 사본을 연결 폴더 `D:\claudeCowork\_market_report_data\` 에도 복사한다 (새 파일 생성은 허용됨).

저장 후 검증은 **Phase 4.5 `verify_report.js` 단일 코드 게이트로 일원화**(P3). 구 `build_report.js --validate`(누락 섹션·출처 없는 뉴스·basis 누락 포트폴리오)는 verify_report.js `req9~12` 로 흡수했으므로 **별도 validate 호출 불필요**(누락 섹션 등은 Phase 4.5 warnings 로 보고).

## Phase 3.5: 반환각(Hallucination) 점검 — 최소화 (P3)

검증은 **Phase 4.5 `verify_report.js` 코드 게이트로 일원화**한다(별도 서브에이전트 발행 안 함 — spin-up 절감). 게이트가 `req9~12` 로 **누락 섹션·`top_news.source_url`·포트폴리오 `basis`·`events_calendar` 날짜 sanity**를 자동 점검(구 `--validate` + 환각검증의 코드화 가능 항목 흡수).

코드로 못 잡는 **판단 필요 항목만** 메인세션이 종합 JSON 에서 **인라인으로 짧게** 확인한다:
- **수치 모순**: `analysis` 방향성이 수집된 `markets`/`commodities`/`crypto` 수치와 모순되지 않는지(예: "증시 강세"인데 주요 지수 1개월 일제히 음수).
- **환각 의심**: 출처 없이 단정한 구체 수치·목표주가·인용이 있는지.

의심되면 해당 필드를 null/수정 후 재검증. 검증 대부분이 Phase 4.5 코드 게이트로 강제되므로 별도 에이전트 없이 동등 이상이며, 게이트 `problems` 가 있으면 Phase 4.5 에서 발송 차단·사용자 질문은 그대로.

## Phase 4: 보고서 생성 (docx 전용)

> **최종 산출물 = docx.** soffice→PDF 변환은 이 환경에서 자주 hang/실패하므로 폐지했다. 빌더가 만든 docx 를 그대로 연결 폴더에 저장하고 메일에 첨부한다(한글 폰트는 빌더가 docx 에 임베드하므로 별도 변환 불필요).

1. **docx 생성** — outputs 에 생성:
```bash
cd "$WORK"
# (R1~R3 · req0/req3 — merge 직후·build 직전 필수) 결측 셀에 정확한 사유/계산값 주입:
#   물가 MoM = FRED 지수 전월비 직접 계산(nmr_mom.json) · BEI = 수준값 표기 · 고용 발표일 보강 · KSVKOSPI = investing.com 파싱 실측(anchors) 주입
python3 "$SRC/nmr_reasons.py" <outputs>/_market_report_data/report_data_YYYYMMDD.json
# (req5 · v3.41) 표=차트 일치: merge 후 report_data 로 CAPEX 차트 재생성 (Phase 1.5 는 머지 전이라 내장 기본값으로 그려져 표와 어긋날 수 있음)
python3 "$SRC/gen_capex_chart.py" <outputs>/_market_report_data/report_data_YYYYMMDD.json
node build_report.js \
  <outputs>/_market_report_data/report_data_YYYYMMDD.json \
  <outputs>/global_market_report_YYYYMMDD_HHMM.docx
```
빌드 후 파일 크기와 `unzip -l` 무결성, 표 개수(`<w:tbl>`)를 점검한다.

2. **(필수) docx 를 연결 폴더 `D:\claudeCowork` 최상위에 저장한다.** ⚠️ file_upload 는 `D:\claudeCowork\...` Windows 경로만 받으므로(outputs·VM 경로 거부) **메일 첨부를 하려면 docx 가 연결 폴더에 반드시 있어야 한다.**
   연결 폴더는 기존 파일 덮어쓰기가 차단될 수 있으므로, 동일 파일명이 이미 있으면 실행 시각 접미사(`_HHMM`)를 붙여 **새 파일**로 저장하고, 그 실제 파일명을 Phase 5 첨부에 사용한다.
   복사 후 **반드시 크기를 비교 검증**한다 (`wc -c` 원본=사본). 연결 폴더가 없으면 첨부가 불가하므로 Phase 6 에 "연결 폴더 미연결 — docx 첨부 불가"를 명시한다.

## Phase 4.5: 품질 게이트 + GOODREPORT 비교 (v3.6.32 — 필수·차단)

> **이 단계를 통과하지 못하면 Phase 5(발송)로 절대 진행하지 않는다.** 목적: 결함을 조용히 미표시(-)·carry-forward·stale 로 통과시키지 않고, 사용자에게 보고·질문한다.

1. **코드 게이트 실행**:
```bash
cd "$WORK" && node verify_report.js <outputs>/_market_report_data/report_data_YYYYMMDD.json "$WORK"
echo "verify exit=$?"   # 0=통과, 1=결함
```
   `{ok,problems[],warnings[]}` 가 출력된다. `problems` 가 있으면 그 목록이 곧 "정상 예제 수준 미달 항목"이다(예: `3.1.1 코스피 차트가 캔들이 아님(flows 폴백)`, `반도체 ETF 17<20`, `증권사 신한 리포트 stale: 2026-05-11`).

2. **GOODREPORT 비교**:
```bash
GOLD="$(ls -t /sessions/*/mnt/claudeCowork/GOODREPORT/*.docx 2>/dev/null | head -1)"
gn=$(unzip -l "$GOLD" 2>/dev/null | grep -c 'word/media/'); nn=$(unzip -l "<새 docx>" | grep -c 'word/media/')
echo "golden media=$gn  new media=$nn"   # new < gold*0.9 이면 결함
```
   (GOODREPORT 가 비었거나 '깨진 회차' 파일만 있으면 사용자에게 어떤 파일을 기준으로 쓸지 먼저 확인한다 — 임의 진행 금지.)

3. **결함이 있으면(필수)**: **발송하지 말고**, problems 와 미디어 개수 차이를 사용자에게 그대로 제시하고 다음 중 무엇을 할지 **묻는다**:
   - (a) 해당 섹션을 재수집·재생성한 뒤 다시 게이트 → 통과하면 발송,
   - (b) 결함을 안고 그대로 발송(사용자가 명시 승인 시에만),
   - (c) 이번 회차 발송 보류.
   **예약(scheduled) 실행도 동일** — 자동 발송하지 말고, Phase 6 결과 보고에 결함 목록과 "사용자 확인 대기"를 남긴다. (낡은·깨진 보고서를 무인 자동 발송하는 것이 그동안의 반복 문제였다.)

4. 게이트 `ok:true` + 미디어 개수 정상이면 Phase 5 로 진행한다.

## Phase 5: 이메일 발송

**`references/email-sending.md` 를 읽고 절차를 그대로 따른다.** 요점:
- SMTP·Gmail MCP 초안 방식 금지. **Claude in Chrome 로그인된 Gmail 직접 발송만** 사용.
- **(v3.53) Chrome 확장 미연결이면 먼저 직접 실행**: `list_connected_browsers` 가 `[]` 면 Phase 0-3 루틴대로 computer-use `request_access(["Google Chrome"])`(경고 시 같은 턴 재요청)→`open_application("Google Chrome")`→`wait(3)`→재확인. 프로필 피커가 뜨면 사용자에게 namoobi 프로필 1회 클릭 요청. 확장이 붙은 뒤 아래 절차 진행.
- **Gmail 이 안 켜져 있으면** Claude in Chrome 으로 `https://mail.google.com/mail/u/0/?ogbl#inbox` 로 navigate (로그인 상시 유지 — 비밀번호 단계 불필요).
- **첨부는 docx** — 연결 폴더(`D:\claudeCowork\...docx`) Windows 경로로 첨부 (outputs·VM 경로는 거부됨). (`references/email-sending.md` 의 PDF 언급은 docx 로 간주 — 차기 정리 대상.)
- **받는사람(To)**: `namoobi@gmail.com` 단독.
- **숨은참조(BCC) — 실행 모드별 파일 (v3.4.3)**: Phase 0 에서 판정한 모드에 따라
  **예약** → `D:\claudeCowork\SECURITY\예약메일수신자.txt`, **일반** → `D:\claudeCowork\SECURITY\메일수신자.txt` 의 주소를 읽어 넣는다 (해당 파일 없으면 BCC 생략·보고에 명시).
- **`//` 주석 제외**: 라인 맨 앞(공백 허용)이 `//` 인 줄은 BCC 대상에서 제외. 읽기: `grep -vE '^[[:space:]]*//' <모드별 파일> | grep -oE '<email>'`. 유효 주소 0개면 To 만 발송·"BCC 0명(전부 주석)" 보고.
- BCC 주소는 비공개 정보 — 채팅·보고에 평문 노출 금지, **인원 수만** 보고 (예: "BCC 2명").
- 사용자가 자동발송을 승인한 세션에서는 추가 확인 없이 발송. 단, 로그인(비밀번호 입력)은 정책상 대신 수행 불가.
- 수신자 칩 클릭 금지. **(v3.18 경량화) 입력은 `browser_batch` 로 묶고 단계마다 screenshot 금지 — 검증은 발송 직전 1회, 우선 `get_page_text`(패시브 읽기·토큰 저렴) 로 To/BCC 칩·제목·첨부 확인, 애매할 때만 screenshot 1장.** 상세 함정 목록은 reference 참조.
- "메시지 전송됨" 확인 직후 완료시각을 기록한다: `TZ=Asia/Seoul date '+%Y-%m-%d %H:%M:%S'` + `date +%s`

## Phase 6: 결과 보고

소요시간 계산: `END=$(date +%s); START=$(cat "$WORK/nmr_start_epoch.txt"); echo $(( (END-START)/60 ))분 $(( (END-START)%60 ))초`

**Phase별 소요(v3.21)**: 발송 확인 후 `echo "$(date +%s) phase6_report" >> "$WORK/nmr_phase_times.txt"` 마킹 → `python3 "$SRC/nmr_timer.py" report "$WORK/nmr_phase_times.txt"` 출력을 아래 [실행 시간] 블록에 포함한다(병목 Phase 확인용).

```
📋 글로벌 시황 보고서 발송 완료
실행 모드: 예약 / 일반  (수신자 파일: 예약메일수신자.txt / 메일수신자.txt)
생성: global_market_report_YYYYMMDD_HHMM.docx (NN KB)
수신: namoobi@gmail.com (To) + 숨은참조 N명 (주소 비공개)
수집: 뉴스 N / 증시 N / 원자재 N / 코인 N / 증권사 N+IB N
검증(Phase 4.5 코드 게이트): problems N건 / warnings N건
[실행 시간]
- 시작: YYYY-MM-DD HH:MM:SS (KST)
- 완료(메일 발송 확인): YYYY-MM-DD HH:MM:SS (KST)
- 소요: M분 S초
- Phase별 소요: (nmr_timer.py report 출력 — 예: phase1_collect 23분 / phase5_send 10분 …)
[핵심 헤드라인 3개]
1~3. (top_news 상위 3개)
[추천 포트폴리오 톤]
- 공격형/중립형/안정형 1줄씩
```
연결 폴더 미연결로 docx 를 연결 폴더에 두지 못해 첨부할 수 없었으면 그 사실도 함께 보고한다.

## 트러블슈팅 (요약)

| 증상 | 대처 |
|------|------|
| Chrome "Tabs can only be moved to and from normal windows" | 일반 크롬 창 없음 → 사용자에게 열어달라 요청 후 `tabs_context_mcp(createIfEmpty=true)` 재시도 |
| Chrome 확장 미연결(`list_connected_browsers`=`[]`) | computer-use 로 직접 실행: `request_access(["Google Chrome"])`(read 경고 시 같은 턴 재요청)→`open_application("Google Chrome")`→`wait(3)`→재확인. 프로필 피커("Chrome 사용자 선택") 뜨면 사용자에게 namoobi 프로필 1회 클릭 요청(브라우저 read 전용이라 Claude 클릭 불가) |
| Gmail 로그인 안 됨 | 비밀번호 대리 입력 불가 → 사용자가 직접 로그인 후 재시도 |
| 작성창이 닫히고 초안만 남음 | `#drafts` 에서 초안 다시 열어 이어서 작성·발송 (email-sending.md) |
| 작성창이 최소화돼 "새 메일" 바만 보임 | 하단 "새 메일" 바 클릭해 펼친 뒤 진행 |
| 제목 입력이 누락됨 | 발송 전 screenshot 검증에서 제목 칸 확인, 비었으면 제목 칸 다시 클릭 후 입력 |
| Write/Edit "outside connected folders" | bash heredoc 으로 저장 |
| npm/cp 권한 오류 | /tmp 금지, outputs/nmr_build 에서 빌드 |
| 파일이 중간에 잘려 보임 (마운트 잘림) | 호스트 원본은 정상 — Read 도구 또는 `git show HEAD:<path>` 로 읽으면 완전하다. Phase 0 EOF 마커 검사 실패 시 git 원본에서 재복사. 복사·패키징 후 크기·EOF 검증 필수 |
| 빌드 exit 0 인데 docx 미생성 | 스크립트 잘림 — Phase 0 EOF 검사·자동복구 수행 여부 확인 |
| 연결 폴더 미연결 | **`request_cowork_directory` 호출 금지**(권한창 원인) — outputs 진행 + Phase 6 에 "연결 폴더 미연결" 명시 |
| 연결 폴더 cp "Permission denied" | 동일 파일명 존재 (덮어쓰기 차단) → `_HHMM` 접미사 새 파일명으로 저장 |
| 첨부 시 "only files the user has shared" | file_upload 는 `D:\claudeCowork\...docx` Windows 경로만 허용 — outputs·`/sessions/...` VM 경로는 거부. docx 를 연결 폴더에 두고 그 경로로 첨부 |
| 예약/일반 수신자 혼동 | Phase 0 모드 판정 결과로 결정 — 예약=예약메일수신자.txt, 일반=메일수신자.txt. 예약 작업 프롬프트에 `scheduled` 인자 전달 확인 |
| 서브에이전트 API 오류로 결과 누락 | nmr_*.json 존재 여부 확인 후 해당 에이전트만 재실행 |
| Chrome 차단 도메인(naver.com 등) | NaverSearch MCP / web_fetch 로 대체 |
| VNINDEX 데이터 부재 | VNM ETF (VanEck Vietnam) 로 대체 |
| 선물 티커 실패(PL=F 등) | current:null → 빌더가 "-" 렌더 |
| CoinInfo gainers/losers 간헐 오류 (429 등) | null/빈배열로 두고 진행 |
| 한글 폰트 깨짐 | 빌더가 docx 에 NanumBarunGothic 임베드 — 별도 설치 불필요(임베드 무시하는 뷰어면 시스템 한글폰트 확인) |

## 플러그인 유지보수·배포 (git push)

플러그인 파일(SKILL.md·references·scripts·plugin.json 등)을 수정한 뒤 GitHub(origin main)에 반영할 때 따른다.

1. **토큰 자동 사용 — 추가 질문 없이 push**: `D:\claudeCowork\SECURITY\githubtoken.txt` 가 있고 그 안에 GitHub 토큰(`ghp_…`/`github_pat_…`)이 있으면, 사용자에게 다시 묻지 말고 그 토큰으로 `git push origin main` 한다. 파일이 없거나 비어 있을 때만 사용자에게 토큰을 요청하거나 사용자가 직접 푸시하도록 안내한다.
2. **토큰 취급 (비공개)**: 토큰은 채팅·로그·커밋·remote URL 어디에도 평문 노출 금지. URL 에 토큰을 박지 말고 일회성 credential helper(환경변수)로만 전달한다:

    ```bash
    # ⚠️ 토큰은 Read 도구(호스트 직접)로 전체값을 확인해 쓴다 — 마운트 bash 의 grep 은 긴 fine-grained 토큰을 잘라 읽는다.
    # ⚠️ credential helper 는 별도 프로세스라 GH_TOKEN 을 반드시 export 해야 보인다 (export 안 하면 빈 값 → "Invalid username or token").
    export GH_TOKEN='<githubtoken.txt 의 전체 토큰값>'
    git -c credential.helper='!f(){ echo username=namoobi-code; echo "password=$GH_TOKEN"; };f' push origin main 2>&1 | sed "s/$GH_TOKEN/***REDACTED***/g"
    unset GH_TOKEN
    # (검증된 one-shot 대안) git push "https://namoobi-code:<토큰>@github.com/namoobi-code/namoobi-market-report.git" main   # 토큰이 명령행에 남으니 마스킹 필수
    ```

    (push 출력에 토큰이 섞일 수 있으면 `| sed "s/$GH_TOKEN/***REDACTED***/g"` 로 마스킹한다.)
3. **SECURITY 폴더 커밋 금지**: `D:\claudeCowork\SECURITY` 는 레포(`D:\claudeCowork\namoobi-market-report`) 밖이고 `.gitignore` 에도 `SECURITY/` 가 있다. 토큰·수신자 파일은 절대 커밋하지 않는다.
4. **마운트 잘림 회피 커밋 절차**: 샌드박스 D: 마운트가 큰 파일(SKILL.md·build_report.js 등)을 간헐적으로 잘라 읽고/쓴다. 워킹트리에서 바로 `git add` 하면 잘린 blob 이 커밋될 수 있으니 금지. 대신 ① 편집은 Read/Write/Edit(호스트 직접) 도구로 하고, ② 커밋은 `git show HEAD:<path>` 로 원본을 받아(객체는 git 이 완전히 읽음) 메모리에서 동일 편집을 적용한 뒤 `git hash-object -w --stdin` 으로 blob 을 만들고 `git cat-file` 로 무결성(끝부분 마커·바이트수)을 검증한다. ③ 인덱스는 마운트가 아닌 tmpfs(`GIT_INDEX_FILE=/dev/shm/idx`)에 두고 `read-tree HEAD` → `update-index --cacheinfo` → `write-tree` → `commit-tree -p HEAD` → `update-ref refs/heads/main` 순으로 커밋한 뒤 push 한다.
5. **`.git/index.lock` 이 안 지워질 때**: 마운트 캐시 때문에 `rm` 이 'Operation not permitted' 가 나면 `mcp__cowork__allow_cowork_file_delete` 로 삭제 권한을 받은 뒤 제거한다.
6. **로컬 인덱스 복구 (자동)**: 작업 후 `.git/index` 가 손상돼 `git status` 가 "index file corrupt"/"bad signature" 를 띄우면, 사용자에게 미루지 말고 직접 `git read-tree HEAD`(또는 `git reset`)로 HEAD 기준 깨끗한 인덱스를 재생성한다. 푸시에는 영향 없다.
7. **(v3.39 필수) 커밋·push 후 작업트리 동기화**: 위 mount-safe 방식은 `refs/heads/main`(HEAD)만 옮기고 **디스크 작업파일·인덱스는 옛 버전으로 남는다**. 커밋·push 직후 반드시 `git reset --hard HEAD`(잘림 의심 시 파일별 `git show HEAD:<path>` 로 재기록 후 검증)로 **디스크 = HEAD** 동기화한다. 빠뜨리면 ① 플러그인이 옛 디스크 파일로 설치돼 새 실행에서 수정 누락, ② 다음 `git add -A` 가 옛 파일을 커밋해 수정이 통째로 되돌려진다. 동기화 후 `git status --porcelain` 이 비어야 정상.

## 부록 A: 주요 증권사 강점 사전 정의

| 증권사 | 핵심 강점 | 대표 채널 | 추천 투자자 |
|--------|-----------|-----------|-------------|
| 신한투자증권 | 자산배분 통합 (주식·채권·원자재·대안), 매크로 일관성 | 카카오채널 '쏠쏠한 리포트', 신한 알파 앱 | 장기 자산배분형 |
| 미래에셋증권 | 12개국 현지법인, ETF 특화, 신흥국(베트남·인도·인니) | m.Global 앱, 디지털리서치 숏폼 | 해외주식·ETF·신흥국 |
| 삼성증권 | SGR 독립 싱크탱크, 파생·선물, SPOT 코멘트, POP TV | mPOP 앱, 유튜브 '글로벌 마켓토크' | 단기 트레이더·매크로 |
| 한국투자증권 | JP모간·골드만삭스 IB 리포트 독점, 중국 국태해통 | 한투 앱 '독점 글로벌 리서치' | 기관 수준 분석 선호·중국 |
| 키움증권 | 텔레그램 실시간, 글로벌 ETF 전략, 중국·신흥국 섹션 | 텔레그램 t.me/s/KiwoomResearch | ETF·속보성 중시 |

복수 구독 전략: 자산배분 큰 그림(신한) + 해외 종목(한투 IB) + ETF(키움) + 신흥국(미래에셋) 조합.

## 부록 B: 해외 주요 IB 5사 강점 사전 정의 (무료 공개 채널)

| 기관 | 핵심 강점 | 무료 공개 채널 | 갱신 주기 |
|------|-----------|----------------|-----------|
| UBS | CIO House View — 자산배분·일일 시황 (시황보고서에 최적) | ubs.com/global/en/wealthmanagement/insights (CIO Daily) | 매일 |
| Goldman Sachs | 매크로·원자재·경제전망 | goldmansachs.com/insights | 수시 |
| J.P. Morgan | 글로벌 전략·시장 전망 | jpmorgan.com/insights/global-research | 수시 |
| Morgan Stanley | 미국주식 전략 (Thoughts on the Market) | morganstanley.com/insights | 주간 |
| BlackRock | ETF·자산배분 (BII Weekly Commentary, 매주 월요일) | blackrock.com/corporate/insights/blackrock-investment-institute | 주간 |


수집 시 주의:
- **원문 리포트(목표주가·종목분석 PDF)는 고객 전용** — 공개 Insights 페이지와 언론 보도(Reuters/CNBC 등, 예: "Goldman S&P target" 검색)로 하우스 뷰 핵심 메시지만 수집한다.
- 보조 수단: UsStockInfo MCP `get_recommendations`(종목별 월가 컨센서스), Bigdata.com MCP `bigdata_search`(있으면).
