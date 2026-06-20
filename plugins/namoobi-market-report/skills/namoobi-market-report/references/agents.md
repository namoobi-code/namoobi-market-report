# 서브에이전트 상세 프롬프트 및 반환 스키마 (v3.7.0)

> 과거 변경이력(v3.x)은 `CHANGELOG.md` 로 분리(런타임 미로딩)했다. 아래 **추가 수집 에이전트·시계열 사양**과 본문 1~7 핵심 에이전트 + (v3.5.0~)·(추가 필드) 섹션을 따른다. 동작·스키마는 그대로다.

## 추가 수집 에이전트·시계열 사양 (현행 — Phase 1 병렬, 결과는 `nmr_*.json` 저장·1줄 요약만 반환)

> ℹ️ `references/data-schema.md` 는 **온디맨드 참조**다 — 스키마 분쟁/신규 필드 설계 때만 열고, 매 실행 로딩하지 않는다(스키마는 본 파일 반환예시 + merge.py/build_report.js 에 내장).

- **美/글로벌 시세(지수·환율·원자재·美ETF·크립토시계열) = `scripts/fetch_us.py`** (sandbox·스레드 병렬 ~4초) → nmr_markets/indexseries/series2/commod/usetf/etfseries/crypto_series.json. (구 MarketsAgent·CommoditiesAgent·UsEtfAgent 폐지·흡수.)
- **한국 시장데이터 = `scripts/fetch_kr.py` (sandbox·stdlib, Chrome/에이전트 불필요)**: 야후 `^KS11`/`^KQ11` 일봉 OHLC + 다음 `market_index/days` 거래량·1년 일별 수급 → `nmr_kr_ohlcv.json`(`kospi_ohlcv`/`kosdaq_ohlcv`/`kospi_flows_daily`/`kosdaq_flows_daily`); 다음 `investor_purchase` 외국인·기관 순매수/순매도 상위 → `nmr_kr_invest.json`; FRED HY OAS(비차단·빠른실패) → `nmr_hy_series.json`. **스레드 병렬 단독 ~10초**, Phase 1 단일 메시지에서 Agent 발행과 함께 **bash 병렬 tool-call** 로 실행. → `gen_kr_candle.py`. (구 KoreaTechFlowsAgent 폐지.)
- **반도체/테마 시계열 = `scripts/fetch_semi.py` (sandbox·stdlib)** → `nmr_kr_series.json`(테마 8·종목 10·ETF 20 시계열, 스레드 병렬 **~1초**). **선정·AUM·노트·테마 방향/코멘트는 KoreaSemiThemeAgent 가 `nmr_semi.json` 으로 계속 제공**(fetch_semi.py 와 **정확히 같은 이름** — merge.py 가 이름으로 join; AUM 상위 20 멤버십 변동 시 에이전트가 플래그→fetch_semi.py 목록 갱신). → `gen_rest_charts.py`(theme_*/semi_s_*/semi_e_*).
- **경기선행지수(월간) = P2 캐시 `leading`**: 통계청/INDEXerGO 순환변동치는 월 1회 갱신 → 매 실행 마커(최신 release 月 `YYYY-MM`)로 `check leading` → reuse 면 스킵. due/미스 시에만 Chrome 으로 `indexergo.com/series/?detailId=11601&frq=M` echarts 수집(curl 403 — Chrome 필요) → `nmr_leading_series.json`·`nmr_leading.json` → `gen_leading_chart.py`.
- **CryptoAgent = 정성 지표만**(CoinInfo MCP: 시장개요·공포탐욕·김프·등락상위) → `nmr_crypto.json`. 1년 시계열(btc/eth/xrp/sol·fng)은 fetch_us.py.
- **美 ETF 30+종**(index·sector·theme[DRAM]·defensive)은 fetch_us.py → `nmr_usetf.json`/`nmr_etfseries.json`. (UsEtfAgent 폐지.)
- **IndexRebalanceAgent → `nmr_rebalance.json`**: S&P500·나스닥100 편입/편출·일정·기준·룰변경(1차 출처 press.spglobal.com·ir.nasdaq.com). **[P2 캐시] 매 실행 S&P/나스닥 최신 구성변경일을 마커로 `check index_rebalance <변경일>` → reuse 면 스킵·캐시; due/확인불가 면 조사 후 `set`.**
- **USMacroExtrasAgent → `nmr_usmacro.json`**: `bigtech_capex`(MSFT·Alphabet·Amazon·Meta 연간) — **실적연도 capex 는 FMP `statements`(`endpoint=cashflow-statement`, period=annual)의 `capitalExpenditure`(음수→절대값)로 정확 수집**(ToolSearch `+statements cashflow` 로 로드 — 현 플랜에서 statements 가용 확인됨, WebSearch 추정 대체). 차기연도 추정(**2027(E) 항상 채움**)·가이던스만 WebSearch. + `fomc_dotplot`(2026·2027·2028말·장기중립 각 행 **jun·mar 중간값 모두**, 빈칸 금지 — 점도표는 API 없음·WebSearch). **병합 carry-forward**: 이번 런에 `bigtech_capex`·`fomc_dotplot`·`us_credit`/`hy_spread` 가 비면 직전 `_market_report_data/report_data_*.json` 에서 가져와 채움. **[P2 캐시] 매 실행 최신 FOMC SEP 발표일을 마커로 `nmr_cache.py check dot_plot <SEP일>` → reuse 면 점도표 조사 스킵·`get`; due/확인불가 면 조사 후 `set dot_plot <as_of> <SEP일>`.**
- **CommoditiesAgent(본문 3) 통합(P3)**: 에너지·금속·농산물·전략광물 현재가·등락률 + **1년 주봉 `nmr_commod.json`** + 각 행 2문장 한글 trend 를 1회 수집으로 산출. (구 CommoditySeriesAgent 흡수.)
- **NewsBerkAgent(AINews+Berkshire) → `nmr_news2.json`**: `events_calendar_longterm` ★★★ 8~10건, `berkshire` 13F(new_buys/added/reduced/exited/top_holdings≤20, 스키마 정확히), `ai_trends` 한/영 병기. **[P2 캐시] 매 실행 Berkshire 최신 13F-HR 제출일(EDGAR)을 마커로 `check berkshire <제출일>` → reuse 면 13F 조사 스킵·캐시; due/확인불가 면 조사 후 `set berkshire`.**
- **HY 스프레드**: FRED `BAMLH0A0HYM2` **월별** series → `gen_hy_chart.py` → `charts/hy_oas.png`(무료 CSV 약 3년 상한). **[P2 캐시] 매 실행 FRED 최신 데이터일(월)을 마커로 `check hy_spread <YYYY-MM>` → reuse 면 히스토리 재사용; due(새 달) 면 최신 점 추가 후 `set`.**
- **차트 생성(Phase 1.5)** = `gen_kr_candle.py` · `gen_leading_chart.py` · `gen_hy_chart.py` · `gen_rest_charts.py` **4종만** (`gen_tech_charts`·`gen_all2`·`gen_semi_etf`·`gen_kr_tech`·`gen_kr_extra`·`gen_kr_flows` 폐기).
- **7 한국 5대 증권사** = 메인세션 Chrome 개별 `navigate→get_page_text`(WebSearch 일괄 우회 금지), 키움 `?dummyVal=0`(iframe 이면 텔레그램 t.me/s/KiwoomResearch 보조). **7·8 신선도** = Daily≤D-1·Weekly/Monthly≤D-3(주말은 금요일까지), 미충족이면 stale 금지·빈값.
- **품질 게이트(Phase 4.5)**: `scripts/verify_report.js` 가 위 항목을 코드로 검사. 미달이면 발송 차단·사용자 질문(조용히 "-"/stale 통과 금지).

수집 에이전트는 전부 **general-purpose** 타입으로 호출한다.
Phase 1 = **수집 에이전트를 단일 메시지로 1회 동시 발행**(P3): News·Crypto(정성)·KoreaSemiTheme(선정·AUM·노트)·GlobalSecurities + (P2 트리거 시)USMacroExtras·IndexRebalance·NewsBerk. **같은 메시지에서 `scripts/fetch_us.py`·`fetch_kr.py`·`fetch_semi.py` 를 bash 병렬 tool-call 로 실행**(美/글로벌·한국 시세·시계열 — 에이전트 아님). **SecuritiesAgent(한국 5대)=메인세션 Chrome 전용** → 동시 진행.
Phase 2 = AnalysisAgent 를 Phase 1 수집 결과와 함께 **단독 호출**(차트 생성 후).

## 공통 반환각(Hallucination) 방지 규칙 — 모든 에이전트 프롬프트에 그대로 포함 (v3.3.0)

아래 블록을 **모든** 서브에이전트 프롬프트 맨 앞에 붙인다.

> **[필수 준수 — 사실성 규칙]**
> 1. **추정 금지 (Grounding)**: 모든 수치·날짜·사실은 반드시 도구 호출 결과 또는 검색으로 직접 확인한 값만 사용한다. 도구/검색으로 확인되지 않은 값은 **절대 기억(학습데이터)으로 채우지 말고** `null`(또는 빈 문자열/빈 배열)로 둔다. "아마", "약", "대략", "추정컨대" 같은 추측성 수치 생성을 금지한다.
> 2. **출처 의무 (RAG)**: 뉴스·이벤트·리서치 등 정성 정보는 **출처(source)와 가능하면 URL·발행일**을 함께 반환한다. 출처를 댈 수 없는 항목은 보고서에 넣지 말고 제외한다.
> 3. **사실 vs 의견 구분**: 확인된 사실과 본인의 해석·전망을 섞지 않는다. 해석은 별도 필드(trend/comment/view)에만 적는다.
> 4. **결정적 출력 (낮은 Temperature 지향)**: 창작·과장·미사여구를 배제하고 사실 기반으로 간결하게. 동일 입력에는 동일 결론이 나오도록 보수적으로 답한다. 확신이 없으면 단정하지 말고 불확실성을 명시한다.
> 5. **도구 로딩**: MCP 도구는 deferred 상태일 수 있다. 사용 전 반드시 `ToolSearch` 키워드 검색으로 로드하라 (예: `+UsStockInfo historical`, `+CoinInfo kimchi`). **UUID 포함 도구명을 하드코딩하지 말 것** (서버 ID는 세션마다 다름).
> 6. **중단 금지**: 실패한 항목은 null/빈 배열로 두고 다음으로 진행한다. 실패를 추측으로 메우지 않는다.
> 7. **저장 규칙**: 최종 JSON 은 outputs 하위 `nmr_<에이전트이름>.json` 파일로 bash heredoc(`<<'EOF'`) 저장하고, 응답으로는 **저장한 파일 경로와 1줄 요약만** 반환할 것 (긴 JSON 본문 출력 금지 — v3.2.3 속도 규칙).

---

## 공통 데이터 소스 폴백 (v3.4.0) — MCP 부재 시 적용

지정 MCP 가 세션에 없으면 추정으로 채우지 말고 아래 폴백을 쓴다. 폴백도 안 되는 칸만 null.

- **증시·환율·원자재 (UsStockInfo MCP 부재 시)** → **Claude in Chrome 으로 Yahoo chart API 직접 호출**.
  절차: `navigate https://finance.yahoo.com` 후 `javascript_tool` 로 async IIFE 안에서
  `await fetch("https://query1.finance.yahoo.com/v8/finance/chart/<TICKER>?range=1y&interval=1wk")` (CORS 허용, **top-level await 금지 → `(async()=>{...})()` 로 감쌀 것**).
  주봉 close 배열 + `meta.regularMarketPrice` 로 1주(7d)/1개월(30d)/3개월(91d)/6개월(182d)/1년(365d) 변화율 계산(타깃일에 가장 가까운 주봉, 허용오차 ~11일).
  결과 JSON 이 길면 `window.__x=obj` 저장 후 8개 키씩 나눠 반환(출력 잘림 회피). **JPYKRW=X 는 100엔 환산이라 current 보존·pct 만 갱신**. CNYKRW 희박 시 USD/KRW ÷ USD/CNY(CNY=X). `web_fetch`·stooq 는 본문 빈값이라 사용 금지(Chrome 만).
- **암호화폐 (CryptoAgent)** → CoinInfo MCP 우선. `get_kimchi_premium` 이 "데이터 부족" 이면 **CoinDesk MCP `fetch_spot_tick`**(market=`upbit`, instruments=`BTC-KRW,ETH-KRW,XRP-KRW,SOL-KRW`)로 업비트 KRW + (market=`binance`, `BTC-USDT,...`) 로 USD 받아 김프=(업비트KRW/(USD×환율)−1)×100. 환율=Yahoo USD/KRW.
  공포·탐욕은 **7개 시점**: `api.alternative.me/fng/?limit=400` (Chrome navigate→get_page_text, body 를 JSON.parse) 에서 현재·1일·1주·1개월·3개월(idx 90)·6개월(idx 182)·1년(idx 365) 값+분류 수집 → `last_3month(_cls)`/`last_6month(_cls)`/`last_year(_cls)` 로 저장. CoinGecko 429 면 ~20초 후 재시도, 실패 시 Crypto.com Exchange MCP/직전값 유지. **한국 거래소 API(업비트·빗썸)는 Chrome 이 차단** → CoinDesk MCP 로만.
- **대형 IPO (NewsAgent)** → SpaceX·OpenAI·Anthropic·Databricks 등 대형 IPO 를 이벤트 캘린더에 포함. 상장일 확정은 `events_calendar`(1개월), 미확정/전망은 `events_calendar_longterm` 에 `(미확정/전망)`·출처와 함께, 날짜 칸엔 `expected_timing` 텍스트.
- **추세 텍스트는 한글로** (trend 필드 영문 금지).

---

## 1. NewsAgent

**임무**: 글로벌 금융시장 Top News 10 + 향후 2주 주요 이벤트 캘린더 + 원화 톤 코멘트.

**도구 (커넥터 우선 · WebSearch 는 보조)**: ① **NaverSearch MCP `search_news`** — 국내·한국어 시황/속보 1순위 ② **UsStockInfo MCP `get_finance_news`(ticker)** — 미국 종목/지수 뉴스(예 NVDA·AAPL·TSLA) ③ web_fetch(한국경제 등 1차 매체 본문) ④ WebSearch — 위 커넥터로 안 잡히는 글로벌·이벤트 보강용. ToolSearch 로 `+NaverSearch news`·`+UsStockInfo news` 로드 후 사용.
naver.com 도메인은 Chrome 에서 차단될 수 있음 → NaverSearch MCP 또는 web_fetch 로 대체.

**프롬프트 골자**:
- 오늘(KST) 기준 글로벌 금융시장에 영향이 큰 뉴스 10개를 선별 (미국·한국·중국·유럽·중동·원자재·코인 균형 있게)
- 각 뉴스: rank / headline / 2~4문장 summary / impact 라벨 / **source(매체명) / source_url(원문 링크) / published_date(YYYY-MM-DD)**
- **(v3.3.0 출처 의무)** 모든 뉴스는 실제 검색·fetch 로 확인한 **출처와 URL**을 반드시 포함한다. URL 을 확보하지 못한 헤드라인은 **목록에서 제외**한다 (출처 없는 뉴스 생성 금지). headline·summary 는 원문 내용에 충실하게 쓰고, 원문에 없는 수치·인용을 지어내지 않는다.
- impact 값 (v3.4.3 — 빌더가 기호별 색으로 렌더): `▲ 강세` (호재·상승 요인) / `▼ 부정` (악재·하락 요인) / `■ 양면` (방향 불확실·혼재). 반드시 이 세 가지 중 하나로 쓰고 맨 앞에 기호(▲/▼/■)를 둔다. 필요시 `▲ 매우 강세 (단기)` 처럼 보강 가능하나 선두 기호는 유지. (구버전 `★`/`중립` 표기 금지)
- **이벤트 캘린더 (2단 수집)**:
  ① `events_calendar` — 향후 1개월(오늘 포함) 시장 영향이 큰 이벤트 7~12건, 전체 중요도(★~★★★), 날짜순.
  ② `events_calendar_longterm` — 1개월 이후 ~ 1년, **중요도 ★★★만** 6~10건, 날짜순. 일정 미확정은 "7월 말 (예정)" 식 표기.
  대상: 중앙은행 회의(FOMC/ECB/BOJ/한은), 주요 경제지표(CPI/PCE/고용/GDP), 선물옵션 만기,
  대형 IPO·실적시즌, 선거·정치, 잭슨홀, MSCI 리뷰, 중국 정책회의,
  **빅테크 신기술·신제품 발표 (v3.4.3 — 필수 수집, 누락 금지)**: 애플 아이폰/WWDC 이벤트·삼성 갤럭시 언팩·엔비디아 GTC/CES 키노트·OpenAI 신모델 발표·구글 I/O·메타 커넥트·MS Build/Ignite·테슬라 이벤트·MWC 등.
  - **(중요)** 빅테크 이벤트는 다른 일정에 묻혀 빠지기 쉬우므로, 캘린더를 채우기 전에 **반드시 별도 WebSearch 를 1회 이상 수행**한다 (예: "big tech product launch events June 2026", "엔비디아 GTC 2026 일정", "애플 이벤트 2026"). 향후 1개월 내 매우 중요한 빅테크 이벤트가 **확인되면 1건이라도 반드시 events_calendar 에 포함**하고, 1개월~1년 내 ★★★급(아이폰 이벤트·GTC·CES·OpenAI 플래그십 발표 등)은 events_calendar_longterm 에 포함한다. 해당 기간에 시장영향이 큰 빅테크 이벤트가 정말 없다고 출처로 확인한 경우에만 생략한다.
  - 빅테크 이벤트의 expected_impact 에는 **관련 종목·섹터 영향**을 적는다 (예: "NVDA·HBM(SK하이닉스·삼성전자) AI 밸류체인 촉매").
  - 시장 영향이 큰 것만 선별 — 일반 개발자 세션·마이너 업데이트 행사는 제외.
  - 날짜 grounding 동일 적용: 공식 발표·언론 보도 출처 필수, 미확정은 "(예상)"/"9월 (예상)" 표기.
  - **(v3.3.0 날짜 grounding)** 이벤트 날짜는 **반드시 공식·1차 출처에서 확인**한다 (중앙은행 IR/통계청·노동부 발표 일정, 거래소 만기 공지, 선거관리 일정 등). `events_calendar` 도구가 있으면 그 결과를 우선 사용한다. **기억에 의존해 날짜를 지어내지 말 것** — 확인되지 않은 일정은 날짜 칸에 `(미확정)` 으로 두고, 가능하면 `source` 에 근거 링크를 적는다. 과거에 지나간 날짜를 향후 일정으로 넣지 않도록 오늘(KST) 기준으로 검증한다.
- 원화 톤: krw_trend 1줄 + krw_comment (환율 수치 추세는 MarketsAgent 가 수집하므로 코멘트만)

**반환 JSON**:
```json
{
  "top_news": [
    {"rank": 1, "headline": "...", "summary": "...", "impact": "▲ 강세",
     "source": "한국경제", "source_url": "https://www.hankyung.com/article/...", "published_date": "2026-06-09"}
  ],
  "events_calendar": [
    {"date": "2026-06-11", "region": "한국", "event": "선물옵션 동시만기", "importance": "★★★",
     "expected_impact": "헤지 청산 시 변동성 급확대", "source": "한국거래소 일정", "source_url": "https://..."}
  ],
  "events_calendar_longterm": [
    {"date": "2026-11-03", "region": "미국", "event": "중간선거", "importance": "★★★",
     "expected_impact": "정책 불확실성·재정 방향 분기점", "source": "...", "source_url": "https://..."}
  ],
  "fx_snapshot": {
    "krw_trend": "원화 약세 지속", "krw_comment": "..."
  }
}
```
> `source_url`·`published_date` 가 없으면 빈 문자열로 둔다 (빌더가 출처 칸을 "-" 로 렌더). 단, top_news 는 출처 없는 항목을 **애초에 넣지 않는 것**이 원칙.
> **(v3.7.1 — 2.2 "-" 재발 방지) `events_calendar_longterm` 항목 완전성**: 각 항목은 반드시 `{date, region, event, importance, expected_impact}` 5필드를 **모두 비지 않게** 채운다. **`event` 가 비거나 null 인 항목은 절대 넣지 말 것**(빌더가 `event` 없는 행을 필터링하지만, 애초에 생성 금지). NewsAgent 와 NewsBerkAgent 가 **동시에** longterm 을 만들면 병합 시 중복·빈칸이 생기므로, longterm 의 단일 소유자는 **NewsAgent** 다 — NewsBerk 는 longterm 을 **반환하지 않는다**.

---

## 2. MarketsAgent · 3. CommoditiesAgent · UsEtfAgent → `scripts/fetch_us.py` (에이전트 폐지)

**美/글로벌 시세는 에이전트 대신 `scripts/fetch_us.py`(sandbox·stdlib·스레드 병렬, 단독 ~4초)가 수집** — Phase 1 단일 메시지에서 fetch_kr.py·fetch_semi.py 와 함께 **bash 병렬 tool-call** 로 실행.
- 산출: `nmr_markets.json`(지수 17+환율 5+fx_usd, 현재가·1주~1년·trend) · `nmr_indexseries.json`(8지수 주봉) · `nmr_series2.json`(fx/commodities/strat_etf 시계열) · `nmr_commod.json`(에너지·금속·농산물·전략금속+군별 코멘트+series) · `nmr_usetf.json`/`nmr_etfseries.json`(美 ETF 33: index 6/sector 11/theme 13[DRAM 포함]/defensive 3) · `nmr_crypto_series.json`(btc/eth/xrp/sol 가격·거래량+fng 1년).
- 표 `trend` 셀은 fetch_us 가 기계 계산(한국 koTrend 스타일과 일관·정확). 군별 서술 코멘트는 기계 1줄, 더 풍부한 해석은 AnalysisAgent(9~12장).
- 美10년 헤드라인=`^TNX`. **전체 국채 커브(`us_treasury_curve`)·CAPEX·점도표는 USMacroExtras(FMP) 유지.** 환율 JPY/KRW ×100·CNY 크로스, 분배금 ETF(SCHD·JEPI·TLT·IEF) 캐비엇 보존. 멤버십/티커 변경 시 fetch_us.py 의 IDX/FX/COMM/ETF 맵 갱신.

## 4. CryptoAgent (정성 지표만 — 시계열은 fetch_us.py)

**임무**: 암호화폐 **정성 지표** → `nmr_crypto.json`. (1년 시계열 btc/eth/xrp/sol·fng 는 `scripts/fetch_us.py` 가 `nmr_crypto_series.json` 으로 산출.)
**도구**: CoinInfo MCP — `get_market_overview`·`get_fear_greed_index`·`get_kimchi_premium`(BTC/ETH/XRP/SOL)·`get_top_gainers`·`get_top_losers`·`get_coin_dominance`. gainers/losers/dominance 간헐 오류는 null/빈배열.
**반환 JSON**: market_overview·fear_greed·kimchi_premium·top_gainers·top_losers (기존 스키마 동일).

## 5. SecuritiesAgent (한국 주요 10사 — 텔레그램 7 + Chrome 3)

**임무**: 한국 주요 증권사 10곳의 최신 리서치 시각을 `nmr_securities.json` 으로 작성. **핵심 6사는 풀(강점·채널·대표리포트·key_message·view), 기타 4사는 1줄 요약(key_message)**.

**소스 (v3.8 하이브리드)**:
| 구분 | 회사 | 소스 |
|------|------|------|
| 텔레그램 7 | 신한·키움·메리츠·하나·교보·유안타·현대차 | **`scripts/fetch_brokers_tele.py`**(curl, Chrome 불필요, 다른 fetch 와 bash 병렬 tool-call) → `nmr_brokers_tele.json`(firm별 최근 메시지). 메리츠 = `meritz_research`+`merITz_tech` 2채널 통합. |
| Chrome 3 | 삼성·미래에셋·한국투자 | 공개 공식 텔레그램 미확인 → 메인세션 Claude in Chrome. **3탭 동시 navigate + `javascript_tool` 타깃추출**(get_page_text 전체 덤프 금지). 삼성=`#bm` 팝업'확인', 한투=`btn-prev`/`&fromDate=YYYY-MM-DD` 직전 거래일(지수종합 jkGubun=99·AIR=34), 미래에셋=리서치 게시판. |

**핵심(풀) 6사**: `samsung·miraeasset·korea_inv·shinhan·kiwoom·meritz`. **요약(1줄) 4사**: `hana·kyobo·yuanta·hyundai`. (빌더 `build_report.js` 의 `coreSet` 과 일치 — 변경 시 동기화.)

**작성 방법**: 메인세션이 `nmr_brokers_tele.json`(텔레그램 7사) + Chrome 3사 추출분을 읽어 firm 엔트리 작성. **텔레그램은 자유서식 — 발행일은 메시지 `datetime` 으로 판단**(거래일/D-1 신선도 동일, 주말은 직전 거래일). 출처 의무: 실제 읽은 메시지·리포트 근거로만 작성, 못 읽었으면 빈 값(빌더가 "(리포트 수집 실패)" 렌더).

**반환 JSON** (`nmr_securities.json`): firm 키 10개 + `common_themes` + `investor_type_recommendation`. 각 firm `{strength, channels:[], key_reports:[{title,(url),date}], key_message, <view>}`. view 키: shinhan=`asset_allocation_view`, miraeasset=`etf_emerging_view`, samsung=`derivatives_view`, korea_inv=`ib_china_view`, kiwoom=`global_etf_view`, meritz=`sector_view`, hana=`china_view`, kyobo=`bond_view`, yuanta=`daily_view`, hyundai=`industrial_view`. (요약 4사는 `key_message` 만 필수.) `key_reports` 는 문자열/객체 배열 모두 허용.

## 6. GlobalSecuritiesAgent (v3.2 신규)

**임무**: 해외 주요 IB 5사(UBS·Goldman Sachs·J.P. Morgan·Morgan Stanley·BlackRock)의 최신 하우스 뷰 수집. SKILL.md 부록 B 의 강점표를 프롬프트에 포함해 각 사의 강점 영역 시각을 우선 수집한다.

**도구**: WebSearch 주력 (예: "UBS CIO daily view", "Goldman Sachs S&P 500 target", "Morgan Stanley Mike Wilson outlook", "BlackRock weekly commentary"), mcp__workspace__web_fetch 로 공개 Insights 페이지 보강. UsStockInfo MCP `get_recommendations` 로 월가 컨센서스 보조 가능. **FMP `analyst`(`price-target-consensus`·`grades-summary`)로 미국 대형주 월가 목표주가·등급 컨센서스를 정량 수집**해 `wall_street_consensus` 보강(무료·미국 한정). (⚠️ Bigdata.com MCP 는 구독 종료로 **사용 불가** — 호출 금지.)
Chrome 브라우저 도구는 사용하지 말 것 (메인 세션/SecuritiesAgent 와 충돌).
> **(v3.7.1 — 속도 우선)** 정량 데이터(목표주가·등급 컨센서스 등)는 **FMP `analyst` MCP 가 웹검색보다 빠르므로 MCP 우선**, 정성 하우스뷰/시황 코멘트는 **WebSearch 가 빠르고 적합**. 같은 정보를 둘 다로 얻을 수 있으면 **더 빠른 경로**를 택한다(불필요한 중복 호출 금지).

**주의**:
- **(v3.7.1) 신선도 기준 + 웹검색 폴백(필수)**: 발행 주기별로 Daily≤D-1·Weekly/Monthly≤D-3 **이내 최신 하우스 뷰/코멘트만** 수집(주말 실행이면 금요일까지 인정). **수집 순서: ① 공식 Insights/CIO 페이지(부록 B URL) 우선 → ② 거기서 기준일 충족 자료가 없으면 반드시 WebSearch 로 보강한다**(예: "Goldman Sachs S&P 500 target June 2026", "UBS CIO view June 19 2026", "JPMorgan equity strategy this week" — Reuters·CNBC·Bloomberg·MarketWatch·Yahoo Finance 등 언론이 인용한 해당 IB 의 최신 하우스 뷰/목표지수). **웹검색까지 했는데도 기준일 충족 자료가 정말 없을 때만** `key_reports: []` + key_message 에 "기준일 충족 신규 공개 자료 미확인"으로 둔다. ⚠️ **수 주~수 개월 지난 낡은(예: 4월) 리포트를 최신인 양 넣지 말 것** — 오래된 건 배제하고 빈값/미확인이 옳다. 웹검색 보강분은 key_message 말미에 매체·날짜를 표기. **(중요) `key_reports` 의 날짜를 비워 신선도 게이트를 우회하지 말 것** — 기준일 밖 자료(연간 전망·수 주 전 목표지수 등)는 '최신'이 아니므로 `key_reports` 는 `[]` 로 두고 key_message 에 "기준일 충족 신규 자료 미확인(최신 공개분 N월N일)"로 정직하게 표기한다.
- 원문 리포트(목표주가 PDF)는 고객 전용 → 공개 채널·언론 보도로 핵심 메시지만 수집.
- 보조: UsStockInfo MCP `get_recommendations` 로 주요 종목 월가 컨센서스 확인 가능.
- 수집 실패한 기관은 key_reports: [], key_message: "" 로 두고 진행.
- **(v3.3.0 출처 의무)** house_view·key_message 는 **실제 읽은 공개 Insights/언론 보도 근거에서만** 작성한다. 확인 못 한 기관의 뷰를 기억으로 지어내지 말 것. 특히 `wall_street_consensus` 의 S&P500 목표지수 등 **구체 수치는 출처(매체·날짜)를 확인한 경우에만** 적고, 확인 불가 시 비워 둔다. `key_reports` 는 가능하면 `{"title","url","date"}` 객체로 출처 링크를 담는다.

**반환 JSON**:
```json
{
  "ubs":            {"strength": "CIO House View 자산배분·일일 시황", "channels": ["UBS CIO Daily"], "key_reports": [{"title": "CIO Daily 2026-06-09", "url": "https://...", "date": "2026-06-09"}], "key_message": "...", "house_view": "..."},
  "goldman":        {"strength": "매크로·원자재·경제전망", "channels": ["GS Insights"], "key_reports": [], "key_message": "", "macro_commodity_view": "..."},
  "jpmorgan":       {"strength": "글로벌 전략·시장 전망", "channels": ["JPM Global Research"], "key_reports": [], "key_message": "", "global_strategy_view": "..."},
  "morgan_stanley": {"strength": "미국주식 전략", "channels": ["Thoughts on the Market"], "key_reports": [], "key_message": "", "us_equity_view": "..."},
  "blackrock":      {"strength": "ETF·자산배분", "channels": ["BII Weekly Commentary"], "key_reports": [], "key_message": "", "etf_allocation_view": "..."},
  "common_themes": ["..."],
  "wall_street_consensus": "S&P500 목표지수 등 월가 컨센서스 1~2문장 (확보 시)"
}
```

---

## 7. AnalysisAgent (마지막 단독 호출)

**임무**: Phase 1 의 6개 JSON 전체를 입력으로 받아 종합 분석과 포트폴리오를 도출. **분석은 의견(opinion)이며, 반드시 Phase 1 에서 수집된 실제 데이터에 근거**해야 한다 — 입력 JSON 에 없는 수치·사실을 새로 만들어내지 말 것.

**프롬프트에 "outputs 의 nmr_*.json 6개 파일을 bash(cat) 로 읽으라"고 지시**하고 (긴 JSON 첨부 불필요 — v3.2.4) 아래를 요구:
- `summary`: 3~5문장 Executive Summary (보고서 맨 앞에 들어감). 입력 데이터에서 드러난 사실만 요약.
- `macro_view`: 매크로 톤 1문단
- `key_themes`: 3~6개 {theme, direction, comment}. **direction 은 반드시 `▲`(강세·상승) / `▼`(부정·하락) / `■`(양면·혼재) 중 하나**로 표기 (빌더가 기호별 색으로 렌더 — ▲ 초록·▼ 빨강·■ 앰버)
- `key_risks`: 3~5개 리스크 문장
- `asset_view`: 자산군별 단·중·장기 견해 1줄씩. **키명은 정확히 다음을 사용**:
  `us_equity, kr_equity, china_equity, japan_equity, em_equity, europe_equity, kr_treasury, us_treasury, gold, oil, btc`
  (빌더 v1.2.2 부터는 `cn_equity/jp_equity/eu_equity/kr_bond/us_bond` 축약 별칭도 수용하지만 위 정식 키를 우선 사용할 것)
- `portfolios`: aggressive/balanced/conservative — label, expected_return, max_drawdown, rebalance, **basis**, allocation[{asset, weight_pct, vehicle}] (비중 합계 100%)
  - **(v3.3.0 수치 환각 방지 — 가장 중요)** `expected_return`·`max_drawdown` 은 **근거 없는 단일 숫자를 지어내지 말 것**. 두 가지 방식만 허용한다:
    ① **계산 근거**: MarketsAgent/CommoditiesAgent 가 수집한 1년 주봉 변화율·구성자산 비중으로 과거 변동성/낙폭을 **계산**해 도출하고, 그 방법을 `basis` 에 명시 (예: "구성자산 1년 실적 변동성 가중평균 기반 추정").
    ② **시나리오 라벨**: 계산이 어려우면 구체 %대신 **범위 + 가정**으로만 표기하고(예: "연 +8~14% (강세 지속 가정)"), `basis` 에 "정성 시나리오 가정치 — 과거 수익률이며 미래 보장 아님" 을 적는다.
    - 어느 경우든 false precision(예: "연 13.7%") 금지. `basis` 필드는 **필수**.
- `action_items`: 단기·중기·장기 체크리스트 5~8개
- **(P3 출력 길이 상한 — 출력 토큰 절감)** macro_view ≤4문장, 각 `key_theme.comment` ≤2문장, 각 `key_risk`·`action_item` 1줄, `asset_view` 항목당 1줄. **분석 깊이·근거·수치는 유지**하되 반복·군더더기 수식어만 줄인다.
- 저장 후 node 로 JSON.parse 검증까지 수행하도록 지시.

**반환 JSON**: 위 필드 구조대로 작성(상세 스키마는 **필요시에만** `data-schema.md` 참조 — 매 실행 로딩 불필요).


## (v3.5.0) 신규 섹션 데이터 수집 — 추가 필드

아래 필드를 담당 에이전트가 수집해 JSON 에 포함한다. 수집 실패 시 해당 키를 생략하면 빌더가 섹션을 자동 생략한다(오류 아님). 모든 수치는 공통 반환각 규칙(추정 금지·출처 의무)을 따른다.

### NewsAgent 추가
- `news.bigtech_events`: [{date, event, importance(★~★★★), expected_impact}] — **매우 중요한 빅테크 신제품·신기술 이벤트만**(삼성 갤럭시 언팩, 애플 9월/폴더블, OpenAI 신모델, NVIDIA GTC·CES 키노트 등). WebSearch 로 공식 일정 확인, 미확정은 날짜에 `(예정)`. `news.bigtech_events_comment` 선택.

### MarketsAgent 추가
- `markets.korea_flows`: [{market(코스피/코스닥/수급 구도), trend(▲/▼ 포함 가능), comment}] — 외국인 순매수 동향(필요시 기관/개인). 출처: 한국거래소·언론. `markets.korea_flows_comment` 선택.
- `markets.korea_leading`: [{period(YYYY.MM), mom(전월비 +x.xp), note}] — 통계청 산업활동동향 경기선행지수 순환변동치 최근 3~4개월(기준선 100 상회=확장). `markets.korea_leading_comment` 선택.
- `markets.korea_themes`: [{theme, direction(▲ 강세/▼ 부정/■ 양면), comment}] — 순환매 관점 주요 테마(반도체·조선·방산·전력[전력기기·송배전·ESS·원전]·증권·로봇[피지컬AI]·우주). 방향은 정성 평가. `markets.korea_themes_intro`/`korea_themes_comment` 선택.
- `markets.us_credit`: {hy_oas, hy_yield, implied_ust, comment} — 美 하이일드. FRED ICE BofA OAS=`BAMLH0A0HYM2`, 유효수익률=`BAMLH0A0HYM2EY` (fred.stlouisfed.org/series/... 를 Chrome get_page_text 로 현재값 확인). 내재국채=유효수익률−OAS. ICE 저작권상 **현재값·요약통계만** 표기.
- `markets.bigtech_capex`: {rows:[{company, y2025, y2026, **y2027, y2028**, comment}], comment} — MSFT·Alphabet·Amazon·Meta 연간 CAPEX. **실적값(과거·당해 FY)은 FMP `statements` `cashflow-statement` 의 `capitalExpenditure`(절대값) 로 정확 수집**(회계연도 기준 — MSFT 6월 결산 명시). `y2027`·`y2028`(전망)은 가이던스·컨센서스를 **확인된 경우에만** 채우고(출처 필수), 미확인은 빈 문자열. 추정 출처: 실적발표/언론/IB.

### CommoditiesAgent 추가
- `commodities.strategic_metals`: {etf:[{name, current, "1w_pct".."1y_pct", trend}], etf_comment, spot:[{item, price, comment}], comment} — ETF 프록시 LIT(리튬)·REMX(희토류)·URA·URNM(우라늄) 주봉 변화율(MarketsAgent 방식) + 현물(탄산리튬·니켈 LME·코발트 LME·우라늄 U3O8·흑연)은 WebSearch.
- `commodities.metals.rare_earth` 는 4.2 표에서 제거됨 — 희토류는 strategic_metals 로 일원화(수집은 계속, 4.2 미표시).

## (v3.6.5) 추가/변경 — 수집 요구 (2026-06-14 사용자 피드백 반영)

아래는 v3.6.5 빌더가 기대하는 필드/시계열이다. 누락 시 해당 섹션·차트는 자동 생략된다.

### IndexSeriesAgent (지수 1년 시계열 — 3.2/3.3/3.4 추세 스파크라인)
- `nmr_indexseries.json`: 17개 지수 1년 **주봉 종가** `{kospi,kosdaq,sp500,nasdaq,dow,vix,dxy,us10y,nikkei,shanghai,hsi,taiwan,sensex,vietnam,stoxx50,dax,ftse}` 각 `[["YYYY-MM-DD",close]..]`. `gen_rest_charts.py` 가 이 파일로 `charts/spark_<key>.png` 를 생성해 3.2/3.3/3.4 표 추세열을 채운다. (없으면 추세열 비어 보임 → 반드시 수집)

### UsEtfAgent → `scripts/fetch_us.py` (폐지)
美 ETF 33종(index 6·sector 11·theme 13[DRAM 메모리 포함]·defensive 3)의 현재가·1주~1년·주봉 시계열은 fetch_us.py 가 `nmr_usetf.json`/`nmr_etfseries.json` 으로 산출. sector `weight`·각 ETF name/desc 는 fetch_us.py ETF 맵에 내장. 신생 ETF(NASA 등) 이력 짧으면 일부 pct null.

### IndexRebalanceAgent (3.2.3 미국 지수 정기 리밸런싱 — S&P 500·나스닥 100, v3.6.9)
**임무**: S&P 500·나스닥 100 정기 리밸런싱의 편입/편출 종목·사업내용·사유, 적용 일정, 편입 기준, 나스닥 패스트엔트리 룰 변경을 수집.
**도구**: WebSearch + web_fetch (먼저 `ToolSearch` 로 `select:WebSearch` 로드). **반드시 1차 출처 우선** — S&P 는 `press.spglobal.com` 보도자료, 나스닥은 `ir.nasdaq.com`·`indexes.nasdaq.com` 방법론 FAQ. 보조로 Reuters·CNBC·Bloomberg. **구성종목을 기억으로 생성 금지** — 확인 안 되면 빈 배열/`미확인`.
**수집 범위**:
- S&P 500: 분기 리밸런싱 일정(발표=둘째 금요일경, 발효=셋째 금요일 마감 후 다음 영업일 개장 전), 최근 2개 분기(직전·당분기) 편입/편출 + 그 사이 비정기(M&A) 변경, 편입 기준(시총 ~$20.5B·흑자·유동성·float·12개월 경과·섹터 대표성), 최신 기준 변경(예: MegaCap 컨설팅 결과).
- 나스닥 100: 연례 재구성(12월)·분기 리뷰·임시 변경의 편입/편출, 2026-05-01 패스트엔트리 룰 변경(상위 ~40위·15거래일 조기편입 / 10% float 폐지→3x cap / 10bp 중간편출 폐지→125위 밖 순위기반 정례편출), 패스트엔트리 후보 대형 IPO(SpaceX·OpenAI·Anthropic 등 시총·상장상태).
**검색 예**: `"S&P 500 index changes <month> 2026 spglobal"`, `"Nasdaq-100 annual reconstitution December 2025"`, `"Nasdaq 100 quarterly changes June 2026"`, `"Nasdaq 100 fast entry rule 2026"`, `"SpaceX OpenAI Anthropic IPO 2026 valuation"`.
**저장**: `markets.index_rebalance` = {sp500:{schedule[], events[], criteria[], criteria_note}, nasdaq100:{schedule[], events[], rule_change{rows[]}, candidates[]}, comment, asof}. 각 편입/편출 항목 `{ticker, name, biz(사업 한 줄), reason(편입/편출 사유)}`. 스키마 상세는 **필요시** `data-schema.md` 참조(매 실행 로딩 불필요). 별도 `nmr_rebalance.json` 저장 후 Phase 3 병합. 날짜·종목은 1차 출처로 grounding, 미확정은 `미확인` 표기.

### KoreaTechAgent / 수급 (3.1.1·3.1.2 — 1년 일별)
- `nmr_kr_ohlcv.json` 의 `kospi_flows_daily`·`kosdaq_flows_daily` 는 **1년치 일별** 투자자 순매수 `[["YYYY-MM-DD", 외국인억원, 기관억원, 개인억원]..]` (1일치만 넣으면 누적순매수 차트가 평평해짐 — 반드시 1년).
  - 네이버금융 레거시 페이지는 SPA 개편으로 404. **다음금융 `finance.daum.net/api/market_index/days`**(market=KOSPI/KOSDAQ, `foreign/institution/individualStraightPurchasePrice` 원→억원 환산)로 1년 일별 수집.
  - **KOSDAQ 거래량**: 야후 `^KQ11` 지수 거래량이 손상(중앙값 1000)되므로 다음금융 `accTradeVolume` 로 교체. KOSPI 거래량은 야후 정상.
- `markets.korea_investor_stocks` = `{asof, kospi_buy[], kospi_sell[], kosdaq_buy[], kosdaq_sell[], note}` — 각 리스트 `{name, detail}` 약 10종(코스피 순매수/순매도·코스닥 순매수/순매도). 빌더가 **4개 리스트**로 렌더. 순매도 일간 종목 랭킹이 비공개/차단이면 빈배열로 두고 `note` 에 사유 명시. (구 `kospi_foreign_buy/kosdaq_strong/aggregate` 폐기)

### 3.1.3 경기선행지수 (markets.korea_leading)
- 각 항목 `{period(YYYY.MM), value(순환변동치 숫자), mom(+x.xp), note}` — **통계청(국가데이터처) 산업활동동향 확정치**를 직접 확인. 배열은 **최신이 맨 앞(내림차순)**. 빌더가 "선행지수↔KOSPI 정비례·약 2개월 선행", "100 이상=확장 / 100 이하=침체" 설명을 자동 표기.

### 3.1.4 테마 (AI·원자력 포함, 순서 고정)
- `markets.korea_themes` 순서: **반도체 · AI · 전력기기 · 조선 · 방산 · 원자력 · 증권 · 로봇 · 우주**. 각 `{theme, direction(▲/▼/■), comment}`.
- 각 테마 대표 ETF 1년 주봉 series 를 `nmr_themeseries1y.json[테마명]` 에 넣으면 `gen_rest_charts.py`(데이터 주도)가 `charts/theme_<테마명>.png` 자동 생성. `markets.korea_theme_etfs[테마]=ETF명`, `markets.korea_theme_charts[테마]="charts/theme_<테마>.png"` 설정. (AI 예: KODEX AI반도체핵심장비 471990.KS / 원자력 예: ACE 원자력테마딥서치 433500.KS)

### 2.3 빅테크 이벤트 (2.1/2.2 와 중복 금지)
- `events_calendar`(2.1)·`events_calendar_longterm`(2.2) 에 들어온 **빅테크 신제품·신기술·빅테크 실적** 이벤트(애플·삼성 언팩·엔비디아 실적/GTC·구글 I/O·메타 커넥트·MS·AWS·테슬라·OpenAI·CES·MWC 등)는 **2.3(`bigtech_events`)에만** 싣고 2.1/2.2 에서는 제외한다(매크로·정책·지표·IPO 만 2.1/2.2). 2.3 는 **날짜 오름차순**, 구체 일자가 캘린더에 있으면 그 일자를 사용(예: 애플 2026-09-08).

### 원자재 섹션별 추세평가 코멘트 / 환율 / 부록A
- `commodities.energy_comment` · `commodities.metals_comment` · `commodities.agri_comment` (4.1/4.2/4.3 각 표 아래 "추세 평가:" 로 렌더). **키명은 `agri_comment`** (agriculture_comment 아님).
- `markets.fx_usd.usd_eur` = **USD/EUR (=1/EURUSD)** 로 저장(EUR/USD 아님).
- 부록A 버크셔 13F (`berkshire`) — 빌더 스키마 **정확히**: `{quarter, filing_date, summary, cash, new_buys[], added[], reduced[], exited[] (각 {name,ticker,detail}), top_holdings[] ({name,ticker,weight_or_value,note}), sources[]}`. `recent_buys/recent_sells` 나 `top_holdings.detail` 로 주면 부록A 가 비므로 금지 — `new_buys/exited`·`weight_or_value/note` 사용.

## (v3.6.7) 3.1.4 반도체/AI 상세표·테마 확장

- `markets.semi_ai_breakdown`: [{name, aum(시총 억원, 문자열 가능), note(간단 설명), chart("charts/semi_<i>.png" 또는 "")}] — 빌더가 [종목·ETF|시총|간단설명|추세(1Y)] 표로 렌더. chart 가 "" 면 추세 셀은 "-". 미존재 ETF 는 넣지 말 것. `markets.semi_ai_comment` 는 표 아래 현황·코멘트.
  - 차트: 각 종목/ETF 1년 주봉 series 로 미니차트(`charts/semi_<i>.png`) 생성(인덱스 = breakdown 행 순서, 시총순). series 가 없거나 매칭 ETF 가 모호하면 chart="".
- `markets.korea_themes` 의 반도체·AI 는 "반도체/AI" 한 행으로 통합하고 `korea_theme_etfs["반도체/AI"]` 는 대표 ETF 하나만. 테마는 자유 확장(신재생에너지·K화장품·K-푸드 등) — 각 테마 1년 series 를 `nmr_themeseries1y.json[테마명]` 에 넣고 `korea_theme_charts[테마]="charts/theme_<테마>.png"`.
- 3.1.2 `kospi_buy/sell`·`kosdaq_buy/sell` detail 은 풍부한 형식(금액·순위·주가±%·외국인지분율). 마감 공개 출처에 확정된 종목만 수록(추정·비교불가 데이터 패딩 금지), 한계는 `note`.
