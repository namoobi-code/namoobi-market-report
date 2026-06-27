> **v3.22.0 (2026-06-26) — 사용자 피드백 8건 반영.** (1) **3.1.1 순서 재정렬**: 美10년물 → 장단기 금리차(10Y-2Y) → HY 스프레드 → FOMC 기준금리 → FOMC 회의 → 점도표. (2) 각 항목 **업데이트 주기/방법 캡션**(매일·변동 시 갱신 등). (3) **6개국 정책금리 실측화** — `PolicyRatesAgent → nmr_policyrates.json`, merge 가 MACRO_DEFAULT 추정 대체. (4) **美10년물 '1일'** = 직전 거래일 대비 1일 변동률(현재가와 분리). (5) **장단기 금리차 1년 차트** `gen_curve_1y.py`(FRED T10Y2Y→FMP curve_10_2 폴백). (6) **Top News 최근 3일 이내만**. Phase 1.5 차트 목록에 `gen_curve_1y.py` 추가.

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

# Namoobi Market Report (v3.21.0)

> **v3.21.0 (2026-06-22) — Phase별 계측(병목 가시화).** 신규 `scripts/nmr_timer.py` 로 각 Phase 시작 시 벽시계를 1줄 마킹하고 Phase 6 에서 Phase별 소요·합계를 출력해 결과 보고에 포함 → 어느 단계(수집/발송/게이트 재작업)에 시간이 쏠리는지 매 실행 수치로 확인. 저비용·비차단(마킹 누락돼도 무방). 동작·산출물 불변.

> **v3.20.0 (2026-06-22) — 증권사 3사(삼성·미래에셋·한투) 메인세션 Chrome 경량화.** 비-Chrome 엔드포인트가 없는(JS 렌더 → web_fetch 는 껍데기) 3사는 메인세션 Chrome 유지가 불가피하나(Chrome 은 메인세션 싱글톤 → 서브에이전트 이전 시 충돌), 토큰을 줄인다: **`browser_batch` 로 3탭 navigate 를 한 번에 묶고 `javascript_tool` 타깃추출만, 단계별 screenshot 금지·get_page_text 덤프 금지.** 텔레그램 7사는 종전대로 `fetch_brokers_tele.py`(curl, Chrome 불필요).

> **v3.19.0 (2026-06-22) — 고정 컨텍스트 다이어트(매 실행 로딩 토큰↓).** SKILL.md 상단 구버전 변경배너(v3.13.2~v3.7.0)를 `CHANGELOG.md` 로 이전(런타임 미로딩) — 최근 배너(v3.16~v3.19)만 유지. 동작·규칙 불변(현행 규칙은 아래 '핵심 수집 규칙'·각 Phase 본문에 이미 반영).

> **v3.18.0 (2026-06-22) — Phase 5 발송 Chrome 경량화(발송 방식 불변).** Gmail MCP 는 발송(send) 도구가 없고 첨부도 미지원 확인 → **Claude in Chrome 직접 발송 유지**하되 토큰 절감: 메일 작성 입력을 `browser_batch` 로 묶고 **단계마다 screenshot 금지**, 발송 직전 1회만 검증(우선 `get_page_text` 패시브 읽기 → To/BCC 칩·제목·첨부 확인, 애매할 때만 screenshot 1장). 첨부(file_upload)·발송 메커니즘·수신자 정책 불변. (상세 `references/email-sending.md`.)

> **v3.17.0 (2026-06-22) — 슬로우데이터 변경감지 보장 + 무거운 에이전트 조건부 발행(토큰·시간↓).** 점도표·버핏13F·지수리밸런싱은 **매 실행 저렴한 마커 1회 관측 → `scripts/nmr_cache.py check`** 로 변경 여부를 확인하고, **마커가 바뀐 경우에만** 해당 무거운 조사 에이전트(USMacroExtras·IndexRebalance·NewsBerk 13F)를 발행한다(변경 없으면 `get` 캐시 재사용=조사 스킵). 빅테크 CAPEX·HBM 은 저렴한 마커가 없어 **실적/분기 창**(`nmr_cache.py gate <오늘>`)으로 판정 — 창 안에서만 조사, 밖이면 carry-forward/내장값. **변경은 매 실행 재관측으로 즉시 포착(보장)** 하되 안 바뀐 날엔 무거운 검색 에이전트가 안 떠 비용이 크게 준다. 캐시 비면 무조건 조사(silent "-" 금지). 게이트는 요일 무관·이벤트창만 본다.

> **v3.16.0 (2026-06-22) — 서브에이전트 모델 티어링(비용·속도 최적화).** Phase 1 수집 에이전트 9종(News·Crypto·Macro·KoreaSemiTheme·GlobalSecurities·USMacroExtras·IndexRebalance·NewsBerk·HBM)을 Agent/Task 호출 시 **`model:"sonnet"`** 으로 발행한다(검색→추출→JSON 저장 작업이라 Opus 불필요 — 토큰·지연 大폭 절감, "추정 금지·도구값만" 그라운딩 규칙으로 품질 유지). **종합·추론이 필요한 Phase 2 AnalysisAgent만 `model:"opus"`** 유지. 메인 오케스트레이터 세션·bash fetch 스크립트는 불변. `model` 미지정 시 부모(Opus) 상속이므로 **반드시 명시**한다(Crypto 등 순수 MCP 호출 에이전트는 검증 후 `haiku` 로 추가 강등 가능).

> **이전 변경이력(v3.13.2 ~ v3.7.0)은 `CHANGELOG.md` 로 이전(런타임 미로딩).** 현행 규칙은 아래 '핵심 수집 규칙'과 각 Phase 본문에 반영돼 있다.

## 핵심 수집 규칙 (현행 — 매 실행 준수)

> **원칙: "조용히 미표시(-)·carry-forward·stale 로 넘기지 말 것. 결함이 있으면 발송하지 말고 사용자에게 물어라."** 정상 예제(`D:\claudeCowork\GOODREPORT`) 수준을 못 맞추면 Phase 4.5 게이트에서 멈춘다. 아래는 그동안 반복적으로 깨지던 지점의 확정 규칙이다(상세·스키마는 `references/agents.md`).

**공통 소스·폴백**
- 증시·지수·환율·원자재·美ETF·크립토시계열: **`scripts/fetch_us.py`**(sandbox·stdlib·스레드 병렬, Yahoo+alternative.me, ~4초). 美10년=^TNX, 전체 국채커브·CAPEX·점도표는 USMacroExtras(FMP). 한국 지수/수급/시계열은 fetch_kr.py·fetch_semi.py.
- 암호화폐: CoinInfo MCP 우선. `get_kimchi_premium` 이 null/부족이면 **CoinDesk MCP `fetch_spot_tick`**(upbit `<SYM>-KRW` + binance `<SYM>-USDT`)로 직접 계산. 공포·탐욕 = `api.alternative.me/fng`. 한국 거래소(업비트·빗썸) API 는 Chrome 차단 → CoinDesk MCP 로만.
- 모든 trend/추세 텍스트는 **한글**. **추정 금지** — 도구·검색으로 확인된 값만, 없으면 null(기억으로 채우지 말 것).
- **(FMP 무료 = 미국만 활용)** 美 국채금리/커브는 `economics treasury-rates`, 미국 대형주 월가 컨센서스·목표주가는 `analyst price-target-consensus`/`grades`, 빅테크 capex 는 `statements cashflow` 로 보강. 13F·indexes·news·**한국 데이터**는 FMP 상위플랜 필요(미보유 시 기존 Yahoo/Chrome 유지). **Bigdata MCP 는 구독 만료로 사용 불가.**

**3.1 주요지표(매크로 대시보드)** — `gen_macro_charts.py` + **MacroAgent**(`nmr_macro.json`). 금리=FMP `economics` `federalFunds`·`treasury-rates`(2Y/10Y); 물가·고용=FMP `economics`(CPI·unemploymentRate·totalNonfarmPayroll·retailSales·realGDP) + **FRED CSV**(Core CPI=`CPILFESL`·PCE=`PCEPI`·Core PCE=`PCEPILFE`·PPI=`PPIFIS`·10Y기대=`T10YIE`, Chrome 동일출처 `fredgraph.csv`); ISM·한중 정책금리는 무료 실시간 API 없음 → WebSearch 추정('추정' 표기). **★3.1.5 선행EPS·PER 출처 정책(이 항목 한정·뉴스 단독 금지): S&P500 = FactSet(또는 Bloomberg·Yardeni) 12개월 선행 P/E → 선행EPS=지수÷PER 산출 / KOSPI = FnGuide·증권사 리포트 12개월 선행 P/E → 동일 산출. 출처·기준일 명시, 뉴스기사 수치 사용 금지.**(이 출처 정책은 3.1.5·3.1.6·3.1.7 에만 적용 — 3.1.1~3.1.4 등은 기존대로) VIX·DXY·원/달러·WTI·美10년물·**KSVKOSPI(코스피 변동성지수 = CNBC `.KSVKOSPI` 실시간)**은 `fetch_us.py` 시세 **재사용**(merge 주입). `nmr_macro.json` 미수집 시 `merge.py` 내장 예시·추정값(`MACRO_DEFAULT`) — 비차단.
**3.2.1 한국 지수 일봉 캔들** — 차트는 반드시 `scripts/gen_kr_candle.py`(다른 한국지수 생성기 금지). 입력 `nmr_kr_ohlcv.json` 의 OHLC = 야후 `^KS11`/`^KQ11` `interval=1d` **일봉**. 거래량은 다음금융 `accTradeVolume` 로 교체(야후 ^KQ11 손상)하고 비거래일 유령행 제거(KRX 거래일 기준). 일별 수급(`*_flows_daily`)=다음금융 `market_index/days`(Chrome 동일출처 fetch, 1년 오름차순). ⚠️ 다음 charts API `/charts/A{code}/days` 는 403 → 한국 종목/ETF 시계열은 **야후 `.KS`/`.KQ`**.
**3.2.2 종목 수급** — 다음금융 `investor_purchase` API(네이버 차단). 코스피·코스닥 외국인·기관 순매수/순매도 상위 종목 → 빌더가 외국인·기관 병합표로 렌더.
**3.2.3 경기선행지수** — **선행종합지수 순환변동치 월별 실측 = `scripts/fetch_leading.py`(sandbox·stdlib, Chrome 불필요)** 가 e-나라지표 통계표 엔드포인트(`showStblGams3.do?stts_cd=105701&idx_cd=1057&freq=M`, UA+Referer+X-Requested-With 헤더)에서 직접 수집 → `nmr_leading_series.json`(`[["YYYY-MM",value]..]` ~29개월)+`nmr_leading.json`(최신 4개월 desc·mom) → `gen_leading_chart.py`. **Phase 1 bash 병렬 tool-call** 로 실행. 실측만(추정 금지), 실패 시 비차단(캐시/직전값 폴백). (구 INDEXerGO echarts·통계표 Chrome 스크래핑·P2 캐시 경로 폐기 — 항상 sandbox 실측.)
**3.2.4 테마·반도체** — 테마 8종 고정순서(반도체/AI·전력기기·조선·방산·원자력·증권·로봇·우주) 10년 월별 series → `gen_rest_charts.py`. 반도체/AI **종목 10 + ETF 정확히 20**(다음금융 AUM 상위, 단일종목 레버리지 포함) 추세차트.
**3.2.5 메모리+HBM 지표 대시보드** — `gen_hbm_dashboard.py` → `charts/hbm_dashboard.png`(6패널 + HBM 3사 EPS/PER 표). HBM 스팟가격·ASP·출하량·점유율·EPS/PER 은 무료 실시간 API 가 없으므로 **HBMAgent 가 WebSearch+뉴스(TrendForce·각사 실적 컨센서스·언론)로 분기 추정치**를 `nmr_hbm.json` 으로 저장(스키마=`references/data-schema.md`). **모든 수치는 '추정' 명시**, 확인 불가 분기는 빈값. `nmr_hbm.json` 미수집 시 내장 예시·추정값으로 차트 생성('예시·추정' 표기 유지) — 3.1.5 는 비차단(차트 없으면 섹션 자동 생략).
**3.3.1 빅테크 CAPEX** — MSFT·Alphabet·Amazon·Meta 연간. 실적값은 **FMP `statements` cashflow 의 `capitalExpenditure`**(절대값)로 정확 수집, 추정연도(**2027(E) 항상 채움**)만 WebSearch. 표 전체폭, 미확인 칸은 "미공개". **(v3.9.0) 표 맨 아래 차트 2종(`gen_capex_chart.py`): 5개사(+오라클) CAPEX 스택바+Capex/매출 비율선, FCF 추이선 — 2023~2025 실적·2026 가이던스·2027~2029 전망(E). 차트는 내장 기본 데이터로 항상 생성되며, `bigtech_capex.{capex,rev,fcf}_series` 제공 시 라이브 오버라이드.**
**3.3.2 FOMC 점도표** — 2026·2027·2028말·장기중립 각 행에 **jun·mar 중간값 모두**(빈칸 금지).
**3.3.3 HY 스프레드** — FRED `BAMLH0A0HYM2` **월별** series(Chrome 동일출처 `fredgraph.csv`) → `gen_hy_chart.py` → `charts/hy_oas.png`(무료 CSV 약 3년 상한, 초과 시 한계 명시).
**3.3.x 미국 ETF·리밸런싱** — `us_etfs` 30종(③ 테마에 **DRAM=Roundhill Memory ETF** 항상 포함). S&P500·나스닥100 정기 리밸런싱(편입/편출·일정·룰변경).
**5 환율 스파크라인** — 원화 5쌍(usd/eur/jpy/cny/hkd_krw) 1년 주봉.
**6.2/6.3 코인** — BTC·ETH·XRP·SOL 1년 + 공포·탐욕 1년 차트. 김프 4종(특히 SOL) 항상 채움.
**7 한국 주요 증권사(10) = 텔레그램 7 + Chrome 3** — 신한·키움·메리츠·하나·교보·유안타·현대차는 **공식 텔레그램** `scripts/fetch_brokers_tele.py`(curl·bash 병렬, Chrome 불필요). 삼성·미래에셋·한투는 **메인세션 Claude in Chrome — `browser_batch` 로 3탭 navigate 를 묶고 `javascript_tool` 타깃추출(단계별 screenshot 금지·토큰 절감)**(공개 리서치 페이지 정상 접속됨 — 삼성=`samsungpop … research_pop.jsp#bm`(팝업'확인'), 미래에셋=`miraeasset … list.do?categoryId=1521`, 한투=`koreainvestment … Strategy.jsp?jkGubun=99`·`34`; 상세 URL `references/agents.md`. get_page_text 덤프 금지; "미확인/로그인전용" 오판 금지). 핵심 6사 풀·기타 4사 1줄 요약.
**7·8 신선도** — Daily≤D-1, Weekly/Monthly≤D-3(주말은 금요일까지). 미충족이면 **stale 로 채우지 말고 빈값**("기준일 충족 최신 공개 자료 미확인"). 글로벌 IB(UBS·GS·JPM·MS·BlackRock)는 WebSearch+Bigdata MCP(Chrome 금지=메인세션과 충돌).
**슬로우체인지 캐시(P2) + carry-forward — v3.17 "매 실행 마커체크" 정책** — 점도표·버핏13F·지수리밸런싱·HY히스토리·주의사항/출처는 캐시(`_market_report_data/nmr_cache.json`). **매 실행, 각 항목의 "이벤트 마커"를 싸게 1회 재관측해 변경을 즉시 포착한다**: 13F=Berkshire 최신 13F-HR 제출일(EDGAR/Massive `/stocks/filings`), 점도표=최신 FOMC SEP 발표일(federalreserve.gov 캘린더), 리밸런싱=S&P/나스닥 최신 구성변경 발표·효력일, HY=FRED 최신 데이터일. `python3 scripts/nmr_cache.py check <item> <관측마커>` → `reuse`(마커 불변)면 `get <item>` 캐시값 주입하고 **그 항목의 무거운 조사 에이전트를 발행하지 않는다**(조사 스킵); `due`(마커 변동·캐시없음·**확인 불가**)면 조사 후 `set <item> <as_of> <마커>`. **확인 불가/불확실이면 무조건 조사(stale 금지)**, 캐시값도 as_of 명시. **빅테크 CAPEX·HBM 은 저렴한 마커가 없으므로 `python3 scripts/nmr_cache.py gate <오늘>` 의 창 판정**(verify/due=실적·분기 창 안→조사, skip=창 밖→carry-forward/내장값)을 따른다(요일 무관·이벤트창만). (백업: 실패 시 직전 report_data 폴백.)
**차트 생성(Phase 1.5)** — `gen_kr_candle.py` · `gen_leading_chart.py` · `gen_hy_chart.py` · `gen_rest_charts.py` · `gen_capex_chart.py` · `gen_hbm_dashboard.py` · `gen_macro_charts.py` · `gen_fwd_eps.py` **8종만** 사용(`gen_tech_charts`·`gen_all2`·`gen_semi_etf`·`gen_kr_tech`·`gen_kr_extra`·`gen_kr_flows` 는 폐기). `gen_capex_chart.py` → `charts/capex_stack_ratio.png`·`charts/capex_fcf.png`(3.2.1 빅테크 CAPEX 차트, cwd 상대 출력). `gen_hbm_dashboard.py` → `charts/hbm_dashboard.png`(3.2.5 메모리+HBM 대시보드). `gen_macro_charts.py` → `charts/macro_*.png`·`charts/spark_*.png`(3.1 주요지표 13종; `nmr_macro.json` 있으면 라이브, 없으면 내장 예시·추정값). `gen_leading_chart.py` → `charts/leading_cycle.png`(3.2.3 — 입력 `nmr_leading_series.json` = `fetch_leading.py` 실측 ~29개월).
**작성주체 익명화** — 표지·면책·13장에서 'Claude' 미표기('AI Research'/'AI').

## 보고서 품질 기준 (반드시 충족)

생성되는 docx 는 다음 10개 항목을 모두 포함해야 한다. 하나라도 누락되면 재작업 대상.

1. **글로벌 Top News 10** — 헤드라인 + 2~4문장 요약 + 임팩트 라벨(`▲ 강세`/`▼ 부정`/`■ 양면` — 기호+색 구분). **헤드라인·요약은 항상 한글**(외신도 한글 번역, 출처/URL 만 원문)
2. **글로벌 주요 이벤트 캘린더** — ① 향후 1개월 전체 중요도(★~★★★) ② 1개월~1년 중장기는 ★★★만 (날짜·지역·이벤트·예상 영향). **빅테크 주요 이벤트(아이폰·갤럭시 언팩·GTC·CES·OpenAI 신모델 등)가 향후 일정에 있으면 누락 금지** (NewsAgent 가 별도 검색으로 확인)
3. **단·중·장기 추세** — 모든 자산을 1주/1개월/3개월/6개월/1년 변화율로 제시
4. **글로벌 증시 풀커버리지** — 한국(코스피·코스닥)·미국·홍콩·중국·일본·**대만**·인도·베트남·유럽
5. **매크로 지표** — 달러지수(DXY), VIX, 美 10년 국채금리
6. **원자재 풀커버리지** — 에너지(WTI·천연가스) + 금속(금·은·구리) + 농산물(옥수수·대두·밀)
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
[Phase 1.0: 슬로우데이터 변경감지 — 매 실행]  점도표/13F/리밸런싱: 저렴한 마커 1회 관측 → `nmr_cache.py check <item> <마커>` → due면 해당 에이전트 발행·`set`, reuse면 `get` 캐시주입(무거운 에이전트 미발행). CAPEX/HBM: `nmr_cache.py gate <오늘>` 창 판정(창 안만 조사). 변경은 매 실행 재관측으로 즉시 포착(보장)
        ↓
[Phase 1: 병렬 수집 — 모든 수집 에이전트를 단일 메시지로 1회 발행 (P3 통합) · 수집 에이전트 model:sonnet]
  ├─ News / Crypto(정성: CoinInfo) / Macro(FMP economics·treasury + FRED → nmr_macro.json)
  ├─ KoreaSemiTheme(선정·AUM·노트) / GlobalSecurities  + (P2 조건부: Phase 1.0 check/gate) USMacroExtras·IndexRebalance·NewsBerk·HBM
  ├─ [bash 병렬 tool-call] scripts/fetch_us.py + fetch_kr.py + fetch_semi.py + fetch_leading.py + fetch_brokers_tele.py  (美/글로벌·한국 시세·시계열·경기선행·증권사 텔레그램 7사, Chrome 불필요)
  └─ SecuritiesAgent=삼성·미래에셋·한투 3사만 메인세션 Chrome(`browser_batch` 3탭 navigate·`javascript_tool` 타깃추출·단계별 screenshot 금지); 텔레그램 7사는 fetch_brokers_tele.py. 배치 발행 직후 동시 진행
        ↓
[Phase 1.5: 차트 생성 (분석 전)]  gen_kr_candle.py·gen_leading_chart.py·gen_hy_chart.py·gen_rest_charts.py·gen_capex_chart.py·gen_hbm_dashboard.py·gen_macro_charts.py·gen_fwd_eps.py → charts/*.png
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
3. **Chrome**: `mcp__Claude_in_Chrome__list_connected_browsers` 로 연결 확인. **일반(normal) 브라우저 창**이 있어야 한다. 없으면 사용자에게 일반 크롬 창을 열어달라고 요청. (발송 직전이 아니라 지금 미리 확인해 두면 Phase 5 실패를 줄인다.)
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

## ⏱ Phase별 계측 (v3.21 — 병목 가시화)

각 Phase **시작 시** 1줄로 벽시계를 마킹한다(저비용·비차단). 어느 Phase(수집/발송/게이트 재작업)에 시간이 쏠리는지 매 실행 수치로 확인하기 위함이다.

- **마킹**(각 Phase 진입 직후 1회): `echo "$(date +%s) <라벨>" >> "$WORK/nmr_phase_times.txt"` — 새 bash 호출이라 `$WORK` 가 비었으면 `WORK="$(ls -d /sessions/*/mnt/outputs 2>/dev/null|head -1)/nmr_build"` 로 재유도. 라벨 순서: `phase1_collect`(Phase 1 배치 발행 직후)·`phase1_5_charts`·`phase2_analysis`·`phase3_merge`·`phase4_build`·`phase4_5_gate`·`phase5_send`.
- **리포트**(Phase 6): 발송 확인 직후 `phase6_report` 마킹 후 `SRC="$(dirname "$(find /sessions/*/mnt -path '*namoobi-market-report/scripts/nmr_timer.py'|head -1)")"; python3 "$SRC/nmr_timer.py" report "$WORK/nmr_phase_times.txt"` 출력을 결과 보고 [실행 시간] 아래에 붙인다.
- 마킹 일부 누락돼도 비차단 — 기록된 구간만 집계된다.

## Phase 1–2: 서브에이전트 호출

상세 프롬프트와 각 에이전트의 반환 JSON 스키마는 **`references/agents.md`** 를 읽고 그대로 사용한다.

핵심 규칙:
- **(v3.16 모델 티어링) 서브에이전트 `model` 인자를 반드시 명시한다.** 수집 에이전트(News·Crypto·Macro·KoreaSemiTheme·GlobalSecurities·USMacroExtras·IndexRebalance·NewsBerk·HBM)는 전부 **`model:"sonnet"`**, 종합·추론하는 AnalysisAgent(Phase 2)만 **`model:"opus"`**. 미지정 시 부모(Opus) 상속이라 토큰·지연이 커지므로 누락 금지 — 수집은 검색→추출→저장 작업이라 Sonnet 으로 충분하고 "추정 금지·도구값만" 규칙으로 품질이 유지된다.
- Phase 1의 **수집 에이전트를 단일 메시지에서 1회 동시 발행** (general-purpose · model:sonnet): News·Crypto(정성)·KoreaSemiTheme(선정·AUM·노트)·GlobalSecurities·**MacroAgent(3.1 주요지표: FMP economics/treasury + FRED CSV → nmr_macro.json)** + **(P2 — Phase 1.0 check/gate 로 조건부 발행)** USMacroExtras(점도표 due 또는 CAPEX 창)·IndexRebalance(리밸런싱 due)·NewsBerk(ai_trends 때문에 상시, 단 13F 서브태스크는 berkshire due일 때만)·HBM(분기 창). **마커 reuse·창밖이면 해당 에이전트 미발행·캐시 재사용.** **같은 메시지에서 `scripts/fetch_us.py`·`fetch_kr.py`·`fetch_semi.py`·`fetch_leading.py` 를 bash 병렬 tool-call** 로 실행(美/글로벌·한국 시세·시계열, 스레드 병렬 각 ~1~10초; 에이전트 아님). **SecuritiesAgent=삼성·미래에셋·한투 3사만 메인세션 Chrome(`browser_batch` 로 3탭 navigate 묶고 `javascript_tool` 타깃추출, 단계별 screenshot 금지·get_page_text 덤프 금지); 텔레그램 7사(신한·키움·메리츠·하나·교보·유안타·현대차)는 `fetch_brokers_tele.py`.**
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
