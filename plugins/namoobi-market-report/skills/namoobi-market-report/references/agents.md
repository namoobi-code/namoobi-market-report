> **[DB화 v2 · 2026-06] 마커체크 폐지 + 차트 시계열 DB.** 구 '에이전트 마커체크(조사 스킵)'·Phase 1.0(nmr_cache)은 폐지. 비매일 지표는 매 실행 수집 시도 후 통합 DB(merge.py + `nmr_db.dbseries`)가 변동체크·미변동 재사용·**차트 시계열 누적**(`db/series_*.json`)을 담당 — 수집이 부실해도 과거 DB로 차트가 완전해진다. (USMacroExtras·IndexRebalance·NewsBerk·HBM 은 상시 수집, DB가 재사용 판단.)

> **[R1~R3 데이터 정확성 규칙 · 2026-06-29] (req0~10 재발방지 — 반드시 준수)**
> 1. **물가 MoM**: "미수집/미집계" 사유로 방치 금지. **FRED 지수(CPILFESL·PCEPILFE·PCEPI·PPIFIS) 전월비 직접 계산** → `nmr_mom.json` = {core_cpi/core_pce/pce/ppi/cpi:{mom,asof,prev,latest_idx,prev_idx}}. `nmr_reasons.py` 가 inflation rows.mom 에 주입.
> 2. **BEI(기대인플레 10Y)**: 수준지표 → inflation row 의 yoy 칸에 `"X.XX% (수준)"` 표기(yoy=null·"-" 금지). `nmr_reasons.py` 처리.
> 3. **FOMC 점도표**: rows 는 `year` 키 허용(빌더가 `item||year` 폴백). jun/mar 빈칸은 "미공개".
> 4. **고용 NFP**: NFP 시계열 = **FRED PAYEMS 레벨의 전월 차분(천명)**. MoM%·지수값 혼입 절대 금지(과거 0.1·0.0… 오염 사례). employment 6종(nfp·unemp·retail·ism_mfg·ism_svc·gdp) ~24개월. 오염된 `db/series_emp_nfp.json` 발견 시 클린값으로 덮어쓴다. **gen_macro_charts 는 6패널 항상**(빈건 '데이터 미확보').
> 5. **美2년물**: `us2y_daily` 1년 시계열(FMP treasury year2)을 `macro.series.us2y_daily` 로 제공. **gen_macro_charts 는 `NMR_OUT="$WORK"` 로 실행**해야 us2y 가 `$WORK/nmr_indexseries.json` 에 주입돼 스파크가 10년물과 다른 정상 모양이 된다.
> 6. **KSVKOSPI**: 메인세션 Claude in Chrome 으로 `https://kr.investing.com/indices/kospi-volatility` 파싱. **성과 라벨은 "달"**(1일/1주/1달/3달/6달/1년) — "개월" 아님(파서 라벨 주의!). current·prev_close·anchors(1d/1w/1mo/3mo/6mo/1y)+23일 시계열 → `nmr_vkospi_history.json`. `nmr_reasons.py` 가 KSVKOSPI 행에 주입(빌더 day1pct 용 `prev_pct` 포함).
> 8. **CAPEX**: **웹서치 실측+컨센서스** → `nmr_capex.json`(MSFT 2026E≈190 캘린더연 컨센서스 등 GOODREPORT 수준; 90 같은 FY부분배분 금지). actual(2024~25)·estimate(2026~29E) 분리표기.
> 9. **HBM**: 항목별 출처링크 `sources[]`(item·value·source·url·asof·type) → build 가 3.1.9 표·그래프 아래 렌더. eps_per 키는 `eps_2026E`(E접미사) — merge 가 `eps_yearly`(y2026_eps) 로 매핑.
> 10. **nmr_reasons.py**: merge 직후·build 직전 1회 실행(SKILL Phase 4) — 위 1·2·4(발표일)·6 을 report_data 에 주입. **누락 시 결측이 "-"로 새어 req0 위반**.

> **v3.39.0 — 휘발 데이터 carry-forward 계약.** HBMAgent·CapexAgent 는 **연결폴더 `_market_report_data/nmr_hbm.json`·`nmr_capex.json` 영구본을 베이스로 로드 → 새로 조사된 값만 갱신 → 저장**한다(merge.py `LCF()` 가 자동으로 WORK 우선·없으면 영구본·사용분 재저장). 즉 매 실행 값은 개선만 되고, 수집 실패해도 내장 예시·추정 기본값으로 되돌아가지 않는다. (손편집 JSON 은 휘발이므로 금지 — 반드시 에이전트 산출/영구본 경유.)

> **v3.35.0 — 3.1.8 CAPEX 데이터 확장(매출·FCF 실측).** CapexAgent 는 5개사(MSFT·GOOGL·AMZN·META·ORCL) 연도별 **CAPEX·매출·FCF** 를 모두 수집해 `nmr_capex.json` rows 에 `y{YYYY}`(capex)·`rev{YYYY}`·`fcf{YYYY}`·`ratio{YYYY}` 로 저장한다. 출처: FMP `statements` income-statement(revenue)·cashflow-statement(freeCashFlow,capitalExpenditure) 실측(2024~25), FMP `analyst` financial-estimates(revenueAvg) 컨센서스(2026~29E). 전망 FCF=직전 영업현금흐름×(매출_y/매출_25)−CAPEX_y 추정. Capex/매출=CAPEX÷매출. 표는 기업별 4행, 두 차트(gen_capex_chart.py)는 rows 의 capex/rev/fcf 로 그려 표·그래프 100% 일치. ORCL statements 플랜 제한 시 공개치·추정 폴백(표기). 단위 십억$.




## 추가 규칙 — 2026-06-26 (라운드6) 변동이력·표 정비

- **변동이력(빨간색, 표 위)**: nmr_changelog.py 가 비일간 지표(정책금리·물가·고용·CAPEX) 최종값을 `_market_report_data/nmr_valcache.json` 에 저장 → 매 실행 직전값과 비교, 변경분만 change_log 로 부착(merge 후·build 전 실행). build 가 각 표 **위에 빨간색**으로 렌더(변경 없으면 미표시).
- 3.1.12 심리표 우측열 헤더 = '시장 영향'.
- KSVKOSPI: investing.com 1년 일별(nmr_vkospi_hist.json)로 현재·1주~1년·스파크 산출.
- 3.1.8 CAPEX change_log 표 위. 3.1.9 gen_hbm_dashboard EPS패널 제거 + nmr_hbm_eps.json 3사 연도별 EPS/PER 표(2025~2028E, build).
- 3.1.3 GDP 분기 별도 차트(nmr_gdp.json, gen_macro2). 고용 통합차트는 월별 5종.

---

## 추가 규칙 — 2026-06-26 (라운드6) 3.1.2/3.1.3 표 스키마

- **3.1.2 물가 표**: 컬럼 = 지표·최신값 YoY·최신값 MoM·기준월·**발표날짜**·의미·시장영향. 행 6개 = CPI·Core CPI·PCE·Core PCE·PPI·**기대인플레 10Y BEI(표 행으로 통합)**. yoy/mom 은 숫자(자동 % 포맷) 또는 문자열(BEI 등) 모두 허용. inflation.rows[]={name,yoy,mom,asof,release,meaning,impact}. 별도 BEI 소절 제거, 통합 추이 그래프 1개(macro_inflation.png).
- **3.1.3 고용 표**: 컬럼 = 지표·최신 수치·기준·**발표일자**·의미·시장영향. employment.rows[]={name,value,asof,release,meaning,freq,impact}.
- 발표날짜/발표일자는 각 지표의 공식 발표일(BLS/BEA/ISM/Census). BEI 는 '실시간 변동'.

---

## 추가 규칙 — 2026-06-26 (라운드5) 3.1 실측 확장

- 매크로 시계열은 FMP **historical 24개월** 확보(latest 1개 금지): inflation 5종+MoM, employment 6종, BEI. gen_macro2.py 가 렌더.
- 美 국채금리: **10년물+2년물**(FMP treasury year10/year2) 모두 수록(rates.us10y/us2y). build 가 2행 표로 렌더.
- CAPEX: nmr_capex.bigtech_capex.rows 에 y2024~y2029(2024~25 실측, 26~29 E=가이던스/IB 컨센서스)+trend(charts/capex_spark_i.png). build 6년+추세 스파크열.
- HBM: gen_hbm_dashboard.py 대시보드 복원 + eps_per 실측 표(둘 다 렌더).
- KSVKOSPI: investing.com web_fetch(현재/1일/1년 실측). 무료 일별이력 제한 구간은 '-'.
- (r0) 갱신원칙: 매일 최신 조사, 비일간 지표는 변동 체크 후 변동 시만 갱신·각 항목 주기 표기.

---

## 추가 규칙 — 2026-06-26 (라운드3) 매크로 실측 강화

- **MacroAgent series 포맷 + 출처 (v3.41 차트 완전성 — req21·26)**: gen_macro_charts 스키마(평면 숫자배열)로 산출. **반드시 인플레 5라인·고용 6패널을 모두 채운다**: `inflation`={"CPI":[..],"Core CPI":[..],"PCE":[..],"Core PCE":[..],"PPI":[..]}(각 ~24개월 YoY %), `employment`={"nfp":[..],"unemp":[..],"retail":[..],"ism_mfg":[..],"ism_svc":[..],"gdp":[..]}, + `fed_funds_5y`·`curve_10_2`+`curve_labels`.
  - **출처(검증됨)**: ① **CPI·실업률·NFP(=totalNonfarmPayroll 월차)·소매(RetailSales MoM)·GDP(realGDP 연율) = FMP `economics-indicators`**(endpoint=economics-indicators, name별, from_date≈36개월 전) — **안정적**. ② **Core CPI·PCE·Core PCE·PPI·BEI = FRED CSV**(CPILFESL·PCEPI·PCEPILFE·PPIFIS·T10YIE) 를 **`mcp__workspace__web_fetch`** 로 받아 YoY 계산. ③ **ISM 제조/서비스 = WebSearch**(월별 공개치). 없는 달은 비우고(추정 금지) DB 가 채운다.
  - ⚠️ **샌드박스 urllib·fetch_*.py 스크립트는 `fred.stlouisfed.org` 에 도달하지 못한다(allowlist timeout). FRED 시계열은 반드시 web_fetch/에이전트 경로로 수집** (sandbox 직접조회 금지). FMP MCP 는 도달 가능.
  - **[Big-Arch DB 누적]** 물가·고용 series 는 `_market_report_data/db/inflation.json`·`db/employment.json` 에 **월키로 upsert 누적**(매 실행 새 달만 추가) → 한 번에 다 못 구해도 시계열이 매 실행 향상되어 항상 5라인·6패널이 그려진다. **물가 `inflation` 각 라인은 길이가 달라도 날짜축에 정렬되도록 `[["YYYY-MM",값]..]` 날짜쌍으로 산출**(gen_macro_charts 가 날짜쌍·평면 모두 처리하지만, 라인별 기간이 다르면 반드시 날짜쌍). 고용 `employment` 패널은 각자 독립이라 평면배열 허용.
  - **10Y-2Y 곡선(req2·7)**: `curve_10_2` = **FMP `treasury-rates`(endpoint=treasury-rates, from_date=1년전~당일) 의 일별 `year10`-`year2` 스프레드**(%, ~250 일별) + `curve_labels`=날짜(YYYY-MM-DD). 점 30개 초과·라벨이 날짜면 생성기가 일별 날짜축 면적차트로 렌더(GOODREPORT 수준). FRED T10Y2Y 는 샌드박스 불가 → **FMP treasury-rates 사용**.
  - **기준금리 차트(req13)**: `fed_funds_5y` = **FMP `economics-indicators`(name=federalFunds, from_date≈5년전) 월별 ~60개**. **24개 미만이면 생성기가 5년 내장 기본값으로 폴백**(짧은 시계열로 그래프가 깨지지 않도록). 1~2개월치만 주지 말 것.
  - **美 2년물 변동%·스파크(req3)**: `rates.us2y` 에 `current`(최신 year2)뿐 아니라 `1d_pct/1w_pct/1mo_pct/3mo_pct/6mo_pct/1y_pct` 를 **FMP `treasury-rates` 일별 year2** 로 계산해 채운다(10년물처럼). 스파크는 `nmr_indexseries.json` 에 `us2y` 일별 추가 → gen 이 spark 생성. 값만 있고 변동칸이 "-"로 비지 않게.
  - **기대인플레 10Y BEI 일일차트(req7)**: 일별 BEI 는 FRED T10YIE(샌드박스 차단)·FMP 미보유 → **메인세션 Claude in Chrome 으로 `https://fred.stlouisfed.org/graph/?id=T10YIE` 또는 investing.com BEI 페이지를 `get_page_text`(JS 렌더)로 통째 읽어** 일별 시계열 파싱 → `_market_report_data/db/bei_daily.json` 에 **월키/일키 upsert 누적**(Big-Arch DB). gen 이 이 DB 로 `macro_infl_exp.png` 를 **일일선**으로 렌더. 실패 시 직전 DB 재사용.
  - **KSVKOSPI 1주~1년·스파크(req9)**: 현재값은 CNBC `.KSVKOSPI`(도달 가능)·일별캐시. 1주~1년 변동·스파크는 **메인세션 Claude in Chrome 으로 `https://kr.investing.com/indices/kospi-volatility-historical-data` 페이지를 통째(`get_page_text`)로 읽어** 일별 종가표 파싱 → `_market_report_data/nmr_vkospi_history.json` 에 누적 → merge `_vkospi_cache_enrich` 가 1주~1년·anchors 산출(투자 페이지가 urllib 403 이어도 Chrome 렌더는 통과).
- **CAPEX**: CAPEXAgent → `nmr_capex.json`(`{bigtech_capex:{rows:[{company,y2024,y2025,y2026,comment}]}}`, FMP cash-flow-statement `capitalExpenditure` 실측). merge 가 `m['bigtech_capex']` 로 주입(2026E 미확정은 빈값).
- **HBM**: HBMAgent → `nmr_hbm.json`(`{eps_per:[SK하이닉스·삼성·Micron EPS/PER FMP·UsStockInfo 실측]}`). 스팟가격·ASP·출하량·점유율은 무료 실측 부재로 **미수록**(추정 금지). build 가 eps_per 표 렌더(추정 대시보드 제거).
- **KSVKOSPI**: `web_fetch` investing.com `kospi-volatility` 로 현재/전일/1일/1년 **실측** → `nmr_markets` vkospi(CNBC 는 폴백). 일중 1주~6개월 이력 미확보 시 해당 칸 '-'(추정 금지).
- **gen_macro_charts 측정전용**: 기준금리=미국 실효만(추정 국가선 제거), 고용=실측 패널만(실업률·소매·GDP), 물가=CPI(동적 x), BEI 무측정 시 '미표시' 플레이스홀더, ISM·추정 스파크 제거(스파크는 gen_rest_charts 측정치 사용).

---

## 추가 규칙 — 2026-06-26 사용자 피드백 반영 (항상 준수)

- **(REQ1) Top News 최신성**: `top_news` 10개는 발행일이 실행일 기준 **최대 하루 전(D-0~D-1)** 이내인 기사만 사용(전일~당일). 2일 이상 지난 기사는 제외(부족하면 같은 기간 추가 검색).
- **(REQ3) 정책금리 실측 — PolicyRatesAgent**: Phase 1 배치에 PolicyRatesAgent(general-purpose·sonnet) 추가 → 미·한·일·중·유로존·영국 **현재 정책금리 실측치**(추정 금지)를 출처·기준일과 함께 `nmr_policyrates.json`(`{"policy_rates":[{country,rate,asof,source,note}]}`)로 저장. merge.py 가 MACRO_DEFAULT 추정치를 이 실측치로 대체.
- **(REQ5) 美10년물 '1일' 열**: 현재가와 분리해 '1일'=직전 거래일 종가 대비 1일 변동률(`1d_pct`). 추세 스파크는 `nmr_indexseries.json` us10y 실측(`gen_curve_1y.py`).
- **(REQ6) 장단기 금리차(10Y-2Y) 1년 차트**: `gen_curve_1y.py` 로 FRED `T10Y2Y`(일별 1년) → `nmr_macro.json` `curve_10_2`(FMP 월별 13개월) → 기존 차트 복사 순으로 `charts/macro_curve_1y.png`. merge 가 yield_curve.chart 를 이 경로로 지정.
- **(REQ2·4·7·8) 3.1.1 순서·캡션**: build_report.js 가 美10년물→장단기차→HY→기준금리→FOMC회의→점도표 순으로 렌더하고 각 항목에 업데이트 주기/방법 캡션 표기.

---

# 서브에이전트 상세 프롬프트 및 반환 스키마 (v3.7.0)

> 과거 변경이력(v3.x)은 `CHANGELOG.md` 로 분리(런타임 미로딩)했다. 아래 **추가 수집 에이전트·시계열 사양**과 본문 1~7 핵심 에이전트 + (v3.5.0~)·(추가 필드) 섹션을 따른다. 동작·스키마는 그대로다.

## 추가 수집 에이전트·시계열 사양 (현행 — Phase 1 병렬, 결과는 `nmr_*.json` 저장·1줄 요약만 반환)

> ℹ️ `references/data-schema.md` 는 **온디맨드 참조**다 — 스키마 분쟁/신규 필드 설계 때만 열고, 매 실행 로딩하지 않는다(스키마는 본 파일 반환예시 + merge.py/build_report.js 에 내장).

- **美/글로벌 시세(지수·환율·원자재·美ETF·크립토시계열) = `scripts/fetch_us.py`** (sandbox·스레드 병렬 ~4초) → nmr_markets/indexseries/series2/commod/usetf/etfseries/crypto_series.json. (구 MarketsAgent·CommoditiesAgent·UsEtfAgent 폐지·흡수.)
- **한국 시장데이터 = `scripts/fetch_kr.py` (sandbox·stdlib, Chrome/에이전트 불필요)**: 야후 `^KS11`/`^KQ11` 일봉 OHLC + 다음 `market_index/days` 거래량·1년 일별 수급 → `nmr_kr_ohlcv.json`(`kospi_ohlcv`/`kosdaq_ohlcv`/`kospi_flows_daily`/`kosdaq_flows_daily`); 다음 `investor_purchase` 외국인·기관 순매수/순매도 상위 → `nmr_kr_invest.json`; FRED HY OAS(비차단·빠른실패) → `nmr_hy_series.json`. **스레드 병렬 단독 ~10초**, Phase 1 단일 메시지에서 Agent 발행과 함께 **bash 병렬 tool-call** 로 실행. → `gen_kr_candle.py`. (구 KoreaTechFlowsAgent 폐지.)
- **반도체/테마 시계열 = `scripts/fetch_semi.py` (sandbox·stdlib)** → `nmr_kr_series.json`(테마 8·종목 10·ETF 20 시계열, 스레드 병렬 **~1초**). **선정·AUM·노트·테마 방향/코멘트는 KoreaSemiThemeAgent 가 `nmr_semi.json` 으로 계속 제공**(fetch_semi.py 와 **정확히 같은 이름** — merge.py 가 이름으로 join; AUM 상위 20 멤버십 변동 시 에이전트가 플래그→fetch_semi.py 목록 갱신). → `gen_rest_charts.py`(theme_*/semi_s_*/semi_e_*).
- **경기선행지수(월간) = `scripts/fetch_leading.py`(sandbox·stdlib, Chrome 불필요)**: e-나라지표 통계표 AJAX 엔드포인트(`showStblGams3.do?stts_cd=105701&idx_cd=1057&freq=M`, UA+Referer+X-Requested-With 헤더 → 200)에서 선행종합지수 순환변동치 월별 실측(~29개월)을 직접 파싱 → `nmr_leading_series.json`(`[["YYYY-MM",v]..]`)+`nmr_leading.json`(`{korea_leading:[{period,value,mom,note}]}` 최신 4개월 desc) → `gen_leading_chart.py`. **Phase 1 bash 병렬 tool-call** 로 실행(fetch_us·kr·semi·brokers_tele 와 함께). 실패 시 비차단(파일 미생성 → merge 가 캐시/직전 report_data 폴백). (구 P2 캐시·INDEXerGO echarts(curl 403)·통계표 Chrome 스크래핑 경로 폐기 — 항상 sandbox 실측.)
- **CryptoAgent = 정성 지표만**(CoinInfo MCP: 시장개요·공포탐욕·김프·등락상위) → `nmr_crypto.json`. 1년 시계열(btc/eth/xrp/sol·fng)은 fetch_us.py.
- **美 ETF 30+종**(index·sector·theme[DRAM]·defensive)은 fetch_us.py → `nmr_usetf.json`/`nmr_etfseries.json`. (UsEtfAgent 폐지.)
- **IndexRebalanceAgent → `nmr_rebalance.json`**: S&P500·나스닥100 편입/편출·일정·기준·룰변경(1차 출처 press.spglobal.com·ir.nasdaq.com). **[P2 — v3.17 매 실행 마커체크] 매 실행 S&P/나스닥 최신 구성변경일을 저렴하게 1회 관측 → `nmr_cache.py check index_rebalance <변경일>`. reuse(변경없음)면 이 에이전트를 발행하지 말고 `get` 캐시 재사용; due(변경·확인불가·캐시없음)면 조사 후 `set`. 비정기(M&A) 변경도 매 실행 재관측으로 즉시 포착.**
- **USMacroExtrasAgent → `nmr_usmacro.json`**: `bigtech_capex`(MSFT·Alphabet·Amazon·Meta 연간) — **실적연도 capex 는 FMP `statements`(`endpoint=cashflow-statement`, period=annual)의 `capitalExpenditure`(음수→절대값)로 정확 수집**(ToolSearch `+statements cashflow` 로 로드 — 현 플랜에서 statements 가용 확인됨, WebSearch 추정 대체). 차기연도 추정(**2027(E) 항상 채움**)·가이던스만 WebSearch. **[3.1.8 CAPEX 추정 출처 정책: 회사 IR·실적발표 가이던스·애널리스트 컨센서스(데이터벤더) 우선, 뉴스기사 단독 수치 사용 금지·출처 명시]** + `fomc_dotplot`(2026·2027·2028말·장기중립 각 행 **jun·mar 중간값 모두**, 빈칸 금지 — 점도표는 API 없음·WebSearch). **병합 carry-forward**: 이번 런에 `bigtech_capex`·`fomc_dotplot`·`us_credit`/`hy_spread` 가 비면 직전 `_market_report_data/report_data_*.json` 에서 가져와 채움. **[P2 — v3.17] dot_plot: 매 실행 최신 FOMC SEP 발표일 마커로 `check dot_plot <SEP일>` → reuse면 점도표 `get`(조사 스킵); due면 조사·`set`. bigtech_capex 는 저렴한 마커가 없어 `nmr_cache.py gate <오늘>` 창(verify/due=실적시즌→CAPEX 조사, skip→carry-forward)으로 판정. dot_plot reuse 이고 capex skip 이면 USMacroExtras 자체를 발행하지 말 것.** **[v3.9.0] 3.2.1 빅테크 CAPEX 차트(`gen_capex_chart.py`)는 내장 기본 데이터(2023~2025 실적·2026 가이던스·2027~2029 전망E, 5개사 Microsoft·Amazon·Alphabet·Meta·Oracle, 십억 달러)로 항상 생성된다. 라이브 갱신은 `bigtech_capex` 에 `capex_series`/`rev_series`/`fcf_series`={"years":[...],"<Company>":[...]} 를 추가하면 차트가 오버라이드(없으면 내장값). 오라클 capex 는 FMP 가용 시 표·시리즈에 포함.**
- **CommoditiesAgent(본문 3) 통합(P3)**: 에너지·금속·농산물·전략광물 현재가·등락률 + **1년 주봉 `nmr_commod.json`** + 각 행 2문장 한글 trend 를 1회 수집으로 산출. (구 CommoditySeriesAgent 흡수.)
- **NewsBerkAgent(AINews+Berkshire) → `nmr_news2.json`**: `events_calendar_longterm` ★★★ 8~10건, `berkshire` 13F(new_buys/added/reduced/exited/top_holdings≤20, 스키마 정확히), `ai_trends`(국·영 병기·**항상 정확히 10개** — 빌더 부록B 가 items[] 렌더). **반드시 구조**: `ai_trends={"as_of":"YYYY-MM-DD","sources_checked":[..],"items":[{"tag":"<분류>","title":"<국문 제목>","summary":"<국문 2~3문장>","title_en":"<EN title>","summary_en":"<EN 1~2 sentences>","source":"<매체>","date":"YYYY-MM-DD","url":"<링크>"}, ...**정확히 10개**]}`. AI 트렌드 items 는 **항상 10개**를 채운다(부족하면 추가 WebSearch 로 보강; 단 출처 URL 확인된 항목만 — 7~8개로 끝내지 말 것). ⚠️ **`detail` 키 금지** — 빌더는 `summary`/`title_en`/`summary_en` 를 읽으므로 국문=`summary`, 영문=`summary_en` 로 분리한다. **[P2 — v3.17] NewsBerk 는 ai_trends(상시) 때문에 매 실행 발행하되 13F 서브태스크만 게이트: 매 실행 Berkshire 최신 13F-HR 제출일(EDGAR) 마커로 `check berkshire <제출일>` → reuse면 13F는 `get` 캐시 재사용(조사 스킵), due면 조사 후 `set berkshire`. ai_trends 10개는 항상 수집.**
- **HY 스프레드**: FRED `BAMLH0A0HYM2` **월별** series → `gen_hy_chart.py` → `charts/hy_oas.png`(무료 CSV 약 3년 상한). **[P2 캐시] 매 실행 FRED 최신 데이터일(월)을 마커로 `check hy_spread <YYYY-MM>` → reuse 면 히스토리 재사용; due(새 달) 면 최신 점 추가 후 `set`.**
- **차트 생성(Phase 1.5)** = `gen_kr_candle.py` · `gen_leading_chart.py` · `gen_hy_chart.py` · `gen_rest_charts.py` · `gen_capex_chart.py` · `gen_hbm_dashboard.py` **6종만** (`gen_tech_charts`·`gen_all2`·`gen_semi_etf`·`gen_kr_tech`·`gen_kr_extra`·`gen_kr_flows` 폐기). `gen_capex_chart.py`→3.2.1 CAPEX, `gen_hbm_dashboard.py`→3.1.6 메모리+HBM 대시보드(`nmr_hbm.json` 라이브 또는 내장 예시·추정값, cwd 상대 `charts/` 출력).
- **7 한국 5대 증권사** = 메인세션 Chrome 개별 `navigate→get_page_text`(WebSearch 일괄 우회 금지), 키움 `?dummyVal=0`(iframe 이면 텔레그램 t.me/s/KiwoomResearch 보조). **7·8 신선도** = Daily≤D-1·Weekly/Monthly≤D-3(주말은 금요일까지), 미충족이면 stale 금지·빈값.
- **품질 게이트(Phase 4.5)**: `scripts/verify_report.js` 가 위 항목을 코드로 검사. 미달이면 발송 차단·사용자 질문(조용히 "-"/stale 통과 금지).

수집 에이전트는 전부 **general-purpose** 타입 + **`model:"sonnet"`** 으로 호출한다(v3.16 모델 티어링 — 검색·추출·저장 작업이라 Opus 불필요, 토큰·지연 절감·품질 불변). **종합·추론하는 AnalysisAgent(Phase 2)만 `model:"opus"`.** `model` 미지정 시 부모(Opus) 상속이므로 반드시 명시.
Phase 1 = **수집 에이전트를 단일 메시지로 1회 동시 발행**(P3): News·Crypto(정성)·KoreaSemiTheme(선정·AUM·노트)·GlobalSecurities + **(P2 — Phase 1.0 check/gate 로 조건부 발행: 마커 reuse 또는 창밖이면 미발행)** USMacroExtras·IndexRebalance·NewsBerk·HBM. **같은 메시지에서 `scripts/fetch_us.py`·`fetch_kr.py`·`fetch_semi.py`·`fetch_leading.py` 를 bash 병렬 tool-call 로 실행**(美/글로벌·한국 시세·시계열 — 에이전트 아님). **SecuritiesAgent(한국 5대)=메인세션 Chrome 전용** → 동시 진행. **(v3.16) 위 수집 에이전트는 전부 `model:"sonnet"` 로 발행한다.**
Phase 2 = AnalysisAgent 를 Phase 1 수집 결과와 함께 **단독 호출**(차트 생성 후) — **model:"opus"**.

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
- **암호화폐 (CryptoAgent)** → CoinInfo MCP 우선. `get_kimchi_premium` 이 "데이터 부족" 이면 **CoinDesk MCP `fetch_spot_tick`**(market=`upbit`, instruments=`BTC-KRW,ETH-KRW,XRP-KRW,SOL-KRW`)로 업비트 KRW + (market=`binance`, `BTC-USDT,...`) 로 USD 받아 김프=(업비트KRW/(USD×환율)−1)×100. 환율=Yahoo USD/KRW. **각 코인의 `upbit_krw`(KRW 절대가)·`binance_usd`(USD 절대가)·`premium_pct` 를 모두 채워 `kimchi_premium.coins[]` 로 반환**(빌더 6.3 표가 업비트/바이낸스/프리미엄 3열을 렌더). SOL 포함 4종 필수.
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
- **(v3.3.0 출처 의무)** 모든 뉴스는 실제 검색·fetch 로 확인한 **출처와 URL**을 반드시 포함한다. URL 을 확보하지 못한 헤드라인은 **목록에서 제외**한다 (출처 없는 뉴스 생성 금지). headline·summary 는 원문 내용에 충실하게 쓰고, 원문에 없는 수치·인용을 지어내지 않는다. **(필수) headline·summary 는 반드시 한글로 작성한다 — 외신(영어·중국어 등) 원문도 자연스러운 한글로 번역하며, `source`·`source_url` 만 원문 그대로 둔다. 영어 헤드라인을 그대로 두지 말 것(1장 핵심 헤드라인·1.글로벌 Top News 10 모두 한글로 렌더된다).**
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
- 산출: `nmr_markets.json`(지수 17+환율 5+fx_usd, 현재가·1주~1년·trend) · `nmr_indexseries.json`(8지수 주봉) · `nmr_series2.json`(fx/commodities/strat_etf 시계열) · `nmr_commod.json`(에너지·금속·농산물·전략금속+군별 코멘트+series) · `nmr_usetf.json`/`nmr_etfseries.json`(美 ETF 33: index 6/sector 11/theme 13[DRAM 포함]/defensive 3) · `nmr_euetf.json`(3.5.1 유럽 주요 ETF 12: 국내 .KS 7+미국 5 — merge 가 LCF 로 markets.europe_etfs 주입, 시리즈는 etfseries 합류→spark_etf_<sym> 자동생성) · `nmr_crypto_series.json`(btc/eth/xrp/sol 가격·거래량+fng 1년).
- 표 `trend` 셀은 fetch_us 가 기계 계산(한국 koTrend 스타일과 일관·정확). 군별 서술 코멘트는 기계 1줄, 더 풍부한 해석은 AnalysisAgent(9~12장).
- 美10년 헤드라인=`^TNX`. **전체 국채 커브(`us_treasury_curve`)·CAPEX·점도표는 USMacroExtras(FMP) 유지.** 환율 JPY/KRW ×100·CNY 크로스, 분배금 ETF(SCHD·JEPI·TLT·IEF) 캐비엇 보존. 멤버십/티커 변경 시 fetch_us.py 의 IDX/FX/COMM/ETF 맵 갱신.

## 4. CryptoAgent (정성 지표만 — 시계열은 fetch_us.py)

**임무**: 암호화폐 **정성 지표** → `nmr_crypto.json`. (1년 시계열 btc/eth/xrp/sol·fng 는 `scripts/fetch_us.py` 가 `nmr_crypto_series.json` 으로 산출.)
**도구**: CoinInfo MCP — `get_market_overview`·`get_fear_greed_index`·`get_kimchi_premium`(BTC/ETH/XRP/SOL)·`get_top_gainers`·`get_top_losers`·`get_coin_dominance`. gainers/losers/dominance 간헐 오류는 null/빈배열.
**반환 JSON**: market_overview·fear_greed·top_gainers·top_losers + **`kimchi_premium`(아래 구조 필수 — 빌더 6.3 렌더)**.
`kimchi_premium = {"rate_usd_krw": <USD/KRW 환율>, "coins": [{"symbol":"BTC","upbit_krw":<업비트 KRW가>,"binance_usd":<바이낸스 USD가>,"premium_pct":<김프%>,"status":"정상"}, ...ETH·XRP·SOL]}`
→ **4종(BTC/ETH/XRP/SOL) 모두** 채운다. `get_kimchi_premium` 이 김프%만 주면 **CoinDesk MCP `fetch_spot_tick`**(upbit `<SYM>-KRW`·binance `<SYM>-USDT`)로 `upbit_krw`·`binance_usd` 절대가를 직접 받아 채우고 `premium_pct=(upbit_krw/(binance_usd×rate)-1)×100`. SOL 누락 시 status="데이터부족". ⚠️ flat 구조({btc:..,eth:..}) 금지 — **coins[] 배열**로 반환(merge.py 가 flat 도 변환하지만 coins[] 가 표준).

## 5. SecuritiesAgent (한국 주요 10사 — 텔레그램 7 + Chrome 3)

**임무**: 한국 주요 증권사 10곳의 최신 리서치 시각을 `nmr_securities.json` 으로 작성. **핵심 6사는 풀(강점·채널·대표리포트·key_message·view), 기타 4사는 1줄 요약(key_message)**.

**소스 (v3.8 하이브리드)**:
| 구분 | 회사 | 소스 |
|------|------|------|
| 텔레그램 7 | 신한·키움·메리츠·하나·교보·유안타·현대차 | **`scripts/fetch_brokers_tele.py`**(curl, Chrome 불필요, 다른 fetch 와 bash 병렬 tool-call) → `nmr_brokers_tele.json`(firm별 최근 메시지). 메리츠 = `meritz_research`+`merITz_tech` 2채널 통합. |
| Chrome 3 | 삼성·미래에셋·한국투자 | **세 사이트 모두 정상 접속됨 — '로그인 전용/미확인'으로 단정 금지.** 메인세션 Claude in Chrome 으로 **`browser_batch` 로 3탭 navigate 를 묶고** `javascript_tool` 로 목록(제목·작성일·작성자) 추출(**단계별 screenshot 금지**·get_page_text 전체 덤프 금지 — 토큰 절감). **삼성**=`https://www.samsungpop.com/sscommon/jsp/search/research/research_pop.jsp#bm` — 로드 시 팝업이 뜨는 게 정상: 팝업을 닫으면('확인') '리서치 탐색기' 리스트로 진입한다(최초 로드 시 렌더러가 잠깐 멈출 수 있으니 재시도/대기). 진입 후 `table tr`/리스트 항목에서 날짜(YYYY-MM-DD)+제목+작성자 추출. **미래에셋**=`https://securities.miraeasset.com/bbs/board/message/list.do?categoryId=1521` — 리서치 게시판 행 추출. **한국투자**=`https://securities.koreainvestment.com/main/research/research/Strategy.jsp?jkGubun=99`(지수종합·시황) + `...Strategy.jsp?jkGubun=34`(AIR). ⚠️모닝브리프 목록은 단순 `table tr` 에 없다 — 페이지 앵커(`document.querySelectorAll('a')`)에서 **'한눈에 투데이'**(당일 시황 모닝브리프) 텍스트와 날짜 포함 앵커를 스캔해 본문·날짜를 추출한다(예: '한눈에 투데이 2026년 7월 2일 …' 전체 시황 코멘트 + 말미 '리서치본부 YYYY. MM. DD'; 시장데이터 위젯 table tr 과 구분). ⚠️`innerHTML`/`documentElement.innerHTML` 덤프 금지 — 쿠키·쿼리스트링 감지로 `[BLOCKED]` 반환. ⚠️`javascript_tool` 은 **top-level await 폴링**(스캔 함수 반복 + `await sleep(800)`, 최대 ~8회)으로 작성 — async IIFE(`(async()=>{})()`)로 감싸면 반환이 빈 `{}`. 봇탐지 iframe(`sessionTimer.jsp`) 존재는 정상. 직전 거래일 필요시 `&fromDate=YYYY-MM-DD`. |

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

## 7. AnalysisAgent (마지막 단독 호출 · model:"opus")

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
**저장**: `markets.index_rebalance` = {sp500:{schedule[], events[], criteria[], criteria_note}, nasdaq100:{schedule[], events[], rule_change{rows[]}, candidates[]}, comment, asof}. 각 편입/편출 항목 `{ticker, name, biz(사업 한 줄), reason(편입/편출 사유)}`. 스키마 상세는 **필요시** `data-schema.md` 참조(매 실행 로딩 불필요). 별도 `nmr_rebalance.json` 저장 후 Phase 3 병합. 날짜·종목은 1차 출처로 grounding, 미확정은 `미확인` 표기. **(v3.8.1) 빌더 견고화: `schedule`/`criteria` 는 문자열배열(불릿) 또는 객체배열(표) 모두 허용, `rule_change.rows` 는 `{item,detail}` 또는 `{rule,before,after}` 모두 허용, `candidates` 는 `{name,note}` 또는 `{name,biz,valuation,status}` 모두 허용 — 어느 형태든 3.2.5 가 '-' 없이 렌더된다.**

### KoreaTechAgent / 수급 (3.2.1·3.2.2 — 1년 일별)
- `nmr_kr_ohlcv.json` 의 `kospi_flows_daily`·`kosdaq_flows_daily` 는 **1년치 일별** 투자자 순매수 `[["YYYY-MM-DD", 외국인억원, 기관억원, 개인억원]..]` (1일치만 넣으면 누적순매수 차트가 평평해짐 — 반드시 1년).
  - 네이버금융 레거시 페이지는 SPA 개편으로 404. **다음금융 `finance.daum.net/api/market_index/days`**(market=KOSPI/KOSDAQ, `foreign/institution/individualStraightPurchasePrice` 원→억원 환산)로 1년 일별 수집.
  - **KOSDAQ 거래량**: 야후 `^KQ11` 지수 거래량이 손상(중앙값 1000)되므로 다음금융 `accTradeVolume` 로 교체. KOSPI 거래량은 야후 정상.
- `markets.korea_investor_stocks` = `{asof, kospi_buy[], kospi_sell[], kosdaq_buy[], kosdaq_sell[], note}` — 각 리스트 `{name, detail}` 약 10종(코스피 순매수/순매도·코스닥 순매수/순매도). 빌더가 **4개 리스트**로 렌더. 순매도 일간 종목 랭킹이 비공개/차단이면 빈배열로 두고 `note` 에 사유 명시. (구 `kospi_foreign_buy/kosdaq_strong/aggregate` 폐기)

### 3.1.5 경기선행지수 (markets.korea_leading)
- 각 항목 `{period(YYYY.MM), value(순환변동치 숫자), mom(+x.xp), note}` — **통계청(국가데이터처) 산업활동동향 확정치**를 직접 확인. 배열은 **최신이 맨 앞(내림차순)**. 빌더가 "선행지수↔KOSPI 정비례·약 2개월 선행", "100 이상=확장 / 100 이하=침체" 설명을 자동 표기.

### 3.2.3 테마 (AI·원자력 포함, 순서 고정)
- `markets.korea_themes` 순서: **반도체 · AI · 전력기기 · 조선 · 방산 · 원자력 · 증권 · 로봇 · 우주**. 각 `{theme, direction(▲/▼/■), comment}`.
- 각 테마 대표 ETF 1년 주봉 series 를 `nmr_themeseries1y.json[테마명]` 에 넣으면 `gen_rest_charts.py`(데이터 주도)가 `charts/theme_<테마명>.png` 자동 생성. `markets.korea_theme_etfs[테마]=ETF명`, `markets.korea_theme_charts[테마]="charts/theme_<테마>.png"` 설정. (AI 예: KODEX AI반도체핵심장비 471990.KS / 원자력 예: ACE 원자력테마딥서치 433500.KS)

### 2.3 빅테크 이벤트 (2.1/2.2 와 중복 금지)
- `events_calendar`(2.1)·`events_calendar_longterm`(2.2) 에 들어온 **빅테크 신제품·신기술·빅테크 실적** 이벤트(애플·삼성 언팩·엔비디아 실적/GTC·구글 I/O·메타 커넥트·MS·AWS·테슬라·OpenAI·CES·MWC 등)는 **2.3(`bigtech_events`)에만** 싣고 2.1/2.2 에서는 제외한다(매크로·정책·지표·IPO 만 2.1/2.2). 2.3 는 **날짜 오름차순**, 구체 일자가 캘린더에 있으면 그 일자를 사용(예: 애플 2026-09-08).

### 원자재 섹션별 추세평가 코멘트 / 환율 / 부록A
- `commodities.energy_comment` · `commodities.metals_comment` · `commodities.agri_comment` (4.1/4.2/4.3 각 표 아래 "추세 평가:" 로 렌더). **키명은 `agri_comment`** (agriculture_comment 아님). 4.3 농산물은 `renderAgriculture()` 가 소그룹(핵심곡물 corn·soybean·wheat / 기후충격 sugar·coffee·orange / 비용·종합 crb·bdi[프록시 ^TRCCRB·BDRY] / 농업ETF dba / 대장주 de·ntr)으로 렌더 — fetch_us.py COMM·agri 블록이 11키 모두 수집.
- `markets.fx_usd.usd_eur` = **USD/EUR (=1/EURUSD)** 로 저장(EUR/USD 아님).
- 부록A 버크셔 13F (`berkshire`) — 빌더 스키마 **정확히**: `{quarter, filing_date, summary, cash, new_buys[], added[], reduced[], exited[] (각 {name,ticker,detail}), top_holdings[] ({name,ticker,weight_or_value,note}), sources[]}`. `recent_buys/recent_sells` 나 `top_holdings.detail` 로 주면 부록A 가 비므로 금지 — `new_buys/exited`·`weight_or_value/note` 사용.

## (v3.6.7) 3.2.3 반도체/AI 상세표·테마 확장

- `markets.semi_ai_breakdown`: [{name, aum(시총 억원, 문자열 가능), note(간단 설명), chart("charts/semi_<i>.png" 또는 "")}] — 빌더가 [종목·ETF|시총|간단설명|추세(1Y)] 표로 렌더. chart 가 "" 면 추세 셀은 "-". 미존재 ETF 는 넣지 말 것. `markets.semi_ai_comment` 는 표 아래 현황·코멘트.
  - 차트: 각 종목/ETF 1년 주봉 series 로 미니차트(`charts/semi_<i>.png`) 생성(인덱스 = breakdown 행 순서, 시총순). series 가 없거나 매칭 ETF 가 모호하면 chart="".
- `markets.korea_themes` 의 반도체·AI 는 "반도체/AI" 한 행으로 통합하고 `korea_theme_etfs["반도체/AI"]` 는 대표 ETF 하나만. 테마는 자유 확장(신재생에너지·K화장품·K-푸드 등) — 각 테마 1년 series 를 `nmr_themeseries1y.json[테마명]` 에 넣고 `korea_theme_charts[테마]="charts/theme_<테마>.png"`.
- 3.2.2 `kospi_buy/sell`·`kosdaq_buy/sell` detail 은 풍부한 형식(금액·순위·주가±%·외국인지분율). 마감 공개 출처에 확정된 종목만 수록(추정·비교불가 데이터 패딩 금지), 한계는 `note`.

## (v3.10.0→v3.49) 3.1.9 HBMAgent — 메모리+HBM 지표 대시보드 (`nmr_hbm.json`)

**목적**: 3.1.9 메모리+HBM 대시보드(`gen_hbm_dashboard.py`)에 들어갈 분기 추정치를 수집한다. HBM 스팟가격·ASP·출하량·점유율·EPS/PER 은 **무료 실시간 API 가 없으므로 전부 추정치**다 — **뉴스 단독 출처 금지: 3사 EPS/PER 은 FnGuide·SimplyWallSt·MarketScreener 등 데이터벤더 컨센서스로, 점유율은 TrendForce·Counterpoint 로 수집**한다(가이던스·실적은 각사 IR). 모든 칸에 `source`·`asof` 명시, 뉴스기사 수치 패딩 금지.

- **호출**: Phase 1 병렬 배치에 포함(선택). **[v3.17] 저렴한 마커가 없으므로 `nmr_cache.py gate <오늘>` 의 hbm 이 verify/due(분기 창: 1·4·7·10월 초)일 때만 HBMAgent 발행, skip(창 밖)이면 미발행**(생성기가 내장/직전 nmr_hbm 으로 비차단 렌더). 결과는 `nmr_hbm.json` 으로 bash 저장하고 1줄 요약만 반환. **미수집/실패해도 무방** — 생성기가 내장 예시·추정값으로 차트를 만들고 '예시·추정' 으로 표기한다(비차단).
- **소스**: TrendForce/DRAMeXchange 보도·블로그, SK하이닉스·삼성전자·Micron 실적발표/IR/가이던스, 증권사·언론. **원문 유료 데이터 복제 금지** — 공개 보도된 수치/레인지만.
- **추정 명시 규칙(필수)**: 모든 값은 추정. **확인 불가 분기는 빈값(미표기)**, 절대 기억·임의값으로 패딩하지 말 것. `source`·`asof` 명시. 확신 없으면 해당 키 생략(생성기가 내장값 사용).
- **반환 스키마** = `references/data-schema.md` 의 `markets.hbm`(= `nmr_hbm.json`). 키: `spot_index, ddr5_16gb, ddr4_8gb, nand_mlc_64gb, hbm_shipment, hbm_market, hbm3e_price, hbm4_price, share[](samsung/sk_hynix/micron/others 합계 100%·예상 E), gap_ratio, eps_per[], year_cur, year_next, asof, source`.
- **점유율 others**: 삼성·SK하이닉스·마이크론 외 잔여분(중국 CXMT 등)을 `others` 로 채워 **합계 100%**.


## MacroAgent (3.1 주요지표) — v3.11.0

Phase 1 배치에 합류(general-purpose). ToolSearch 로 FMP `economics` 도구 로드 후 수집 → outputs `nmr_macro.json` 저장, **경로+1줄 요약만** 반환(긴 JSON 재타이핑 금지). UUID 하드코딩 금지.

**수집**
- **FMP `economics-indicators`**(name=): `federalFunds`(현재 기준금리)·`CPI`(지수→YoY/MoM)·`unemploymentRate`·`totalNonfarmPayroll`(전월차→신규고용)·`retailSales`(MoM)·`realGDP`(전기比 연율)·(보너스 `consumerSentiment`). **FMP `treasury-rates`** 최근일 `year2`·`year10` → `yield_curve`(10Y-2Y)·`us10y`.
- **FRED CSV**(Chrome 동일출처 `fredgraph.csv` — 3.3.3 HY OAS 와 동일 패턴): Core CPI=`CPILFESL`·PCE=`PCEPI`·Core PCE=`PCEPILFE`·PPI=`PPIFIS`·10Y 기대인플레=`T10YIE`(월별 12개+YoY/현재값).
- **ISM 제조/서비스 PMI = 공식 보도자료 실측**(WebSearch로 ISM/PRNewswire·Morningstar 등 ISM® Report On Business 헤드라인 수치 확보 — 예 'Manufacturing PMI at 53.3'). **'추정' 라벨 금지**(공식 발표치이므로 실측). 미발표월(휴일 지연 등)은 직전 실측월 유지·release 날짜 정확히. **한·중 정책금리만** 무료 실시간 API 부재로 WebSearch 추정('추정' 표기). **(v3.22) KSVKOSPI(코스피 변동성지수)는 추정 금지. ★중요: investing.com 페이지는 샌드박스 urllib·Claude-in-Chrome 에서 403/차단되므로 `fetch_us.py` 직접파싱이 깨진다 → MacroAgent 가 `web_fetch`(차단 안 됨)로 `https://kr.investing.com/indices/kospi-volatility`(현재/전일/1일/1년)와 `.../kospi-volatility-historical-data`(일별 종가표→스파크·1주~6개월)를 받아 `nmr_markets.json` 의 vkospi(current·prev_close·chg·1d_pct·1y_pct·anchors)에 주입한다. web_fetch 도 실패 시 `fetch_us.py` 의 CNBC `.KSVKOSPI` + 일별캐시(`nmr_vkospi_history.json`) 폴백. merge 가 'KSVKOSPI (KOSPI Volatility)' 행에 주입.**
- **재사용(수집 금지)**: VIX·DXY·원/달러·WTI·美10년물·**KSVKOSPI(CNBC .KSVKOSPI)** = `fetch_us.py` 산출 → `merge.py` 가 주입.

**반환 스키마** = `references/data-schema.md` 의 `markets.macro`. 차트용 시계열은 `nmr_macro.json` 의 `macro.series.*`(fed_funds_5y·curve_10_2·inflation·infl_exp·employment·sentiment) 로 저장하면 `gen_macro_charts.py` 가 라이브 차트 생성(없으면 내장 예시·추정). 미수집이어도 `merge.py` `MACRO_DEFAULT` 로 3.1 은 항상 렌더(비차단).

## (v3.46.0) M7OutlookAgent — 3.1.7 미국 빅테크(M7) 실적 전망 (`nmr_m7.json`, 매일)
**목적**: 3.1.7 표(가이던스·애널리스트 추정치 변화 시장 신호)를 매일 갱신. 대상 7종목 = AAPL·MSFT·NVDA·GOOGL·AMZN·META·TSLA.
**수집(매 실행·매일)**: 종목별 ① 현재가·52주 변화 ② 컨센서스 투자의견 분포·평균 목표주가(FMP `analyst` grades-summary·price-target-consensus/summary — 무료플랜 미국 대형주 가용) ③ 최근 1개월/1분기/1년 평균 목표주가 흐름 = 목표주가 리비전 추세(price-target-summary) ④ 최근 등급 변경(upgrades/downgrades). 가이던스·연간 추정치 변화와 최신 증권사 리포트는 WebSearch(회사 실적발표·FactSet·언론). **추정 금지·확인값만**, 뉴스 단독 수치 패딩 금지.
**신호 판정**: 추정치·목표주가 상향=긍정 / 실적 호조에도 목표주가 하향·디레이팅=경계 / 이익 모멘텀·의견 악화=위험 / 안정=중립.
**출력** `$WORK/nmr_m7.json` = `{as_of, rows:[{name,ticker,price,chg52,consensus,consensus_detail,target,upside,revision,revision_detail,guidance,signal}]}` → merge 가 `markets.m7_outlook` 로 주입(빌더 `renderM7Outlook`, 3.1.10 뒤). **미수집이어도 비차단** — 빌더 내장 스냅샷(M7_OUTLOOK_DEFAULT)으로 렌더. **호출**: Phase 1 병렬 배치 포함, `model:"sonnet"`.


## DerivPositioningAgent — 3.1.13 파생시장 포지셔닝 (v3.47, Phase 1, model:sonnet)

역할: 파생·수급 포지셔닝 z-score 스냅샷을 매일 산출.

1) `deriv_signals/` 에서 `python daily_update.py` 실행 — 무료 소스(yfinance 현물·선물·VIX·옵션, CFTC COT, 네이버 투자자별 매매동향, data.go.kr 파생상품·지수시세)로 `deriv_signals.db` 갱신. data.go.kr 키는 `deriv_signals/secrets.env` 의 `DATA_GO_KR_KEY`(gitignore).
2) `python export_snapshot.py <실행폴더>/nmr_deriv_positioning.json` — DB에서 지수현황·z매트릭스·활성신호·해석 산출.
3) merge 가 `markets.deriv_positioning` 로 로드 → 빌더 `renderDerivPositioning`. 미수집 시 내장 스냅샷(DERIV_POS_DEFAULT)으로 비차단.
※ COT는 주간(화요일 기준·금요일 공표)이라 미국 순포지션만 주간, 나머지(현물·베이시스·수급·옵션)는 일별.
