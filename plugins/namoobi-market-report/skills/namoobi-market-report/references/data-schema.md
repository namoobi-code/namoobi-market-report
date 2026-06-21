# 통합 데이터 JSON 스키마 (v3.3.0)

build_report.js 가 기대하는 통합 JSON 구조. 각 섹션은 해당 에이전트의 반환값을 그대로 넣는다.
누락 필드는 빌더가 `-` 로 렌더링하므로, 실패 항목은 null/빈배열로 두면 된다.

> **v3.3.0 반환각 방지 필드 (요약)** — 자세한 규칙은 `agents.md` 참조:
> - `news.top_news[]`·`events_calendar[]`: `source`/`source_url`/`published_date` 추가 (출처 grounding).
> - `securities.*.key_reports[]`·`global_securities.*.key_reports[]`: 문자열 또는 `{title,url,date}` 객체 허용.
> - `analysis.portfolios.*`: `basis` 필드 필수 (expected_return/max_drawdown 의 산출 근거).

```json
{
  "metadata": {
    "report_date":  "YYYY-MM-DD",
    "generated_at": "ISO-8601 timestamp (KST)",
    "generator":    "Claude AI Research (Cowork) v3"
  },
  "news":        { "...": "NewsAgent 반환 (top_news, fx_snapshot)" },
  "markets":     { "...": "MarketsAgent 반환 (korea, us_markets, asia_markets, europe_markets)" },
  "commodities": { "...": "CommoditiesAgent 반환 (energy, metals, agriculture, commentary)" },
  "crypto":      { "...": "CryptoAgent 반환 (market_overview, fear_greed, kimchi_premium, top_gainers, top_losers)" },
  "securities":  { "...": "SecuritiesAgent 반환 (한국 5사 + common_themes + investor_type_recommendation)" },
  "global_securities": { "...": "GlobalSecuritiesAgent 반환 (UBS/GS/JPM/MS/BlackRock + common_themes + wall_street_consensus)" },
  "analysis":    { "...": "AnalysisAgent 반환 (summary, macro_view, key_themes, key_risks, asset_view, portfolios, action_items)" }
}
```

## 추세 항목 공통 형식 (markets / commodities 의 모든 지수·원자재)

```json
{
  "current": 8228.70,
  "1w_pct":  1.2,
  "1mo_pct": 4.5,
  "3mo_pct": 31.8,
  "6mo_pct": 42.0,
  "1y_pct":  55.3,
  "trend":   "단기 과열, 장기 상승 추세 유지"
}
```

필수: `current` + 최소 1개 기간 변화율 + `trend`. 실패 시 `current: null`.

## news

```json
{
  "top_news": [
    {"rank": 1, "headline": "코스피 사상 첫 8000 돌파", "summary": "2~4문장", "impact": "★ 강세",
     "source": "한국경제", "source_url": "https://www.hankyung.com/article/...", "published_date": "2026-06-09"}
  ],
  "events_calendar": [
    {"date": "2026-06-11", "region": "한국", "event": "선물옵션 동시만기", "importance": "★★★",
     "expected_impact": "헤지 청산 시 변동성 급확대", "source": "한국거래소", "source_url": "https://..."}
  ],
  "events_calendar_longterm": [
    {"date": "2026-11-03", "region": "미국", "event": "중간선거", "importance": "★★★",
     "expected_impact": "정책 불확실성 분기점", "source": "...", "source_url": "https://..."}
  ],
  "fx_snapshot": {
    "krw_trend": "원화 약세", "krw_comment": "..."
  }
}
```

impact 값: `★ 강세` / `▲ 양면` / `▼ 부정` / `■ 중립` (보강 표기 허용).
(v3.3.0) `source`/`source_url`/`published_date` 는 출처 grounding 용. top_news 는 출처 확인된 항목만 수록. 날짜 미확정 이벤트는 `date: "(미확정)"`.
events_calendar 는 향후 1개월 전체 중요도(★~★★★) 7~12건, events_calendar_longterm 은 1개월~1년 ★★★만 6~10건 — 모두 날짜순.
(구버전 호환: fx_snapshot 에 USD_KRW 등 현재가 문자열이 있으면 빌더가 폴백 렌더링한다.)

## markets

```json
{
  "korea":          {"kospi": {}, "kosdaq": {}},
  "us_markets":     {"sp500": {}, "nasdaq": {}, "dow": {}, "vix": {}, "dxy": {}, "us10y": {}},
  "asia_markets":   {"nikkei": {}, "shanghai": {}, "hsi": {}, "sensex": {}, "vietnam": {}},
  "europe_markets": {"stoxx50": {}, "dax": {}, "ftse": {}},
  "fx_markets":     {"usd_krw": {}, "eur_krw": {}, "jpy_krw": {}, "cny_krw": {}, "hkd_krw": {}}
}
```

fx_markets 의 각 항목도 추세 공통 형식(current + 1w/1mo/3mo/6mo/1y + trend).
jpy_krw 는 100엔 기준으로 환산해 넣는다. 환율 섹션에는 us_markets.dxy 가 자동 병기된다.

## commodities

```json
{
  "energy":      {"wti": {}, "brent": {}, "natgas": {}},
  "metals":      {"gold": {}, "silver": {}, "copper": {}, "platinum": {}, "rare_earth": {}},
  "agriculture": {"corn": {}, "soybean": {}, "wheat": {}},
  "commentary":  "원자재 종합 코멘트"
}
```

rare_earth 는 REMX (VanEck Rare Earth/Strategic Metals ETF) 프록시.

## crypto

```json
{
  "market_overview": {"total_volume_24h_usd": 93598932897, "avg_change_pct": -0.32, "coins_up": 25, "coins_down": 69, "btc_dominance": 58.2},
  "fear_greed": {"current": 25, "classification": "공포", "yesterday": 34, "last_week": 27, "last_month": 33},
  "kimchi_premium": {
    "rate_usd_krw": 1495.39,
    "coins": [{"symbol": "BTC", "upbit_krw": 111900000, "binance_usd": 75823, "premium_pct": -1.31, "status": "디스카운트"}]
  },
  "top_gainers": [{"symbol": "XYZ", "change_pct": 12.3}],
  "top_losers":  [{"symbol": "ABC", "change_pct": -9.8}]
}
```

(v3.4.2) 빌더는 `kimchi_premium.coins[]` 의 키 별칭도 수용한다: `upbit_price_krw` / `global_price_usd`·`binance_price_usd` / `premium_percent`. 단 정식 키(`upbit_krw`/`binance_usd`/`premium_pct`) 사용을 권장.

## securities

```json
{
  "shinhan":    {"strength": "...", "channels": ["..."], "key_reports": ["..."], "key_message": "...", "asset_allocation_view": "..."},
  "miraeasset": {"strength": "...", "channels": [], "key_reports": [], "key_message": "", "etf_emerging_view": "..."},
  "samsung":    {"strength": "...", "channels": [], "key_reports": [], "key_message": "", "derivatives_view": "..."},
  "korea_inv":  {"strength": "...", "channels": [], "key_reports": [], "key_message": "", "ib_china_view": "..."},
  "kiwoom":     {"strength": "...", "channels": [], "key_reports": [], "key_message": "", "global_etf_view": "..."},
  "common_themes": ["..."],
  "investor_type_recommendation": {
    "long_term_allocator": "...", "overseas_stock_picker": "...",
    "short_term_trader": "...", "etf_passive": "...", "china_focused": "..."
  }
}
```

접속 실패: `key_reports: []`, `key_message: ""` → 빌더가 "(리포트 수집 실패)" 렌더링.
(v3.3.0) `key_reports` 항목은 문자열 `"제목"` 또는 객체 `{"title": "...", "url": "https://...", "date": "2026-06-09"}` 둘 다 허용 — 빌더가 객체면 제목+링크로 렌더.

## global_securities (v3.2)

```json
{
  "ubs":            {"strength": "...", "channels": ["UBS CIO Daily"], "key_reports": ["..."], "key_message": "...", "house_view": "..."},
  "goldman":        {"strength": "...", "channels": [], "key_reports": [], "key_message": "", "macro_commodity_view": "..."},
  "jpmorgan":       {"strength": "...", "channels": [], "key_reports": [], "key_message": "", "global_strategy_view": "..."},
  "morgan_stanley": {"strength": "...", "channels": [], "key_reports": [], "key_message": "", "us_equity_view": "..."},
  "blackrock":      {"strength": "...", "channels": [], "key_reports": [], "key_message": "", "etf_allocation_view": "..."},
  "common_themes": ["..."],
  "wall_street_consensus": "S&P500 목표지수 등 월가 컨센서스 (확보 시)"
}
```

수집 실패 기관: `key_reports: []`, `key_message: ""` → 빌더가 "(리포트 수집 실패)" 렌더링.

## analysis

```json
{
  "summary": "3~5문장 Executive Summary (보고서 맨 앞)",
  "macro_view": "매크로 톤 1문단",
  "key_themes": [{"theme": "...", "direction": "▲", "comment": "..."}],
  "key_risks": ["..."],
  "asset_view": {
    "us_equity": "단기 ... / 중기 ... / 장기 ...",
    "kr_equity": "...", "china_equity": "...", "japan_equity": "...", "em_equity": "...",
    "europe_equity": "...", "kr_treasury": "...", "us_treasury": "...",
    "gold": "...", "oil": "...", "btc": "..."
  },
  "portfolios": {
    "aggressive":   {"label": "공격형", "expected_return": "연 +8~14% (강세 지속 가정)", "max_drawdown": "-25~-35% (과거 변동성 기반)", "rebalance": "월 1회", "basis": "구성자산 1년 실적 변동성 가중평균 기반 추정 — 미래 보장 아님", "allocation": [{"asset": "...", "weight_pct": 0, "vehicle": "구체 종목·ETF"}]},
    "balanced":     {"label": "중립형", "expected_return": "...", "max_drawdown": "...", "rebalance": "...", "basis": "...", "allocation": []},
    "conservative": {"label": "안정형", "expected_return": "...", "max_drawdown": "...", "rebalance": "...", "basis": "...", "allocation": []}
  },
  "action_items": ["단기·중기·장기 체크리스트 5~8개"]
}
```

- `asset_view` 키명은 위 정식 키를 사용 (빌더 v1.2.2+ 는 `cn_equity/jp_equity/eu_equity/kr_bond/us_bond` 축약 별칭도 수용).
- `direction` 은 ▲/▼/■ 중 하나.
- 각 portfolio 의 `allocation` 비중(weight_pct) 합계는 **반드시 100** — 빌더가 합계를 검증해 경고를 출력한다.
- (v3.3.0) `basis` 는 `expected_return`/`max_drawdown` 산출 근거 — **필수**. 단일 false-precision 숫자(예: "연 13.7%") 금지, 범위+가정 또는 계산근거로 표기. 빌더가 포트폴리오 표 아래에 출력하고, `--validate` 가 누락 시 경고한다.


## (v3.5.0) 추가 필드 스키마 — 모두 선택(없으면 섹션 자동 생략)

- `news.bigtech_events`: [{date:str, event:str, importance:"★|★★|★★★", expected_impact:str}], `news.bigtech_events_comment`:str.
- `markets.korea_flows`: [{market:str, trend:str, comment:str}], `markets.korea_flows_comment`:str.
- `markets.korea_leading`: [{period:str, mom:str, note:str}], `markets.korea_leading_comment`:str.
- `markets.korea_themes`: [{theme:str, direction:"▲ 강세|▼ 부정|■ 양면", comment:str}], `markets.korea_themes_intro`/`korea_themes_comment`:str.
- `markets.us_credit`: {hy_oas:str, hy_yield:str, implied_ust:str, comment:str} (또는 {rows:[{label,value,note}], comment}).
- `markets.bigtech_capex`: {rows:[{company:str, y2025:str, y2026:str, comment:str}], comment:str}. (보고서 3.2.3)

## (v3.6.8) 추가 필드 — 3.2.2 주요 미국 ETF

- `markets.us_etfs`: {index:[], sector:[], theme:[], defensive:[], comment:str, asof:str} — 미국 ETF 29종(지수추종·11개 섹터·테마/특화·방어형). 각 그룹 배열 항목:
  ```json
  {"symbol":"XLK","name":"Technology Select Sector SPDR","desc":"반도체·소프트웨어·AI (엔비디아·MS·애플)","weight":"27.69%",
   "current":185.0,"1w_pct":2.5,"1mo_pct":11.6,"3mo_pct":35.1,"6mo_pct":28.2,"1y_pct":55.4,"trend":"강한 상승추세 · 신고가권"}
  ```
  `weight` 는 sector 그룹만(S&P500 비중). 빌더(renderUSEtfs)가 4개 그룹 표로 렌더하며 추세(1년) 셀은 `charts/spark_etf_<symbol>.png`. 신생 ETF 는 3·6개월 null 허용. 없으면 3.2.2 섹션 자동 생략(기존 CAPEX 는 3.2.3).
- `nmr_etfseries.json`: {SYMBOL:[["YYYY-MM-DD",close]..]} (또는 [close..]) — 29종 1년 주봉 종가. `gen_rest_charts.py` 가 `charts/spark_etf_<SYMBOL>.png` 생성.

## (v3.6.9) 추가 필드 — 3.2.3 미국 지수 정기 리밸런싱

- `markets.index_rebalance`: {sp500:{...}, nasdaq100:{...}, comment:str, asof:str} — 빌더(renderIndexRebalance)가 3.2.3 섹션 렌더. 없으면 자동 생략(기존 CAPEX 는 3.2.4).
  - `sp500` / `nasdaq100` 공통:
    - `schedule`: S&P=[{q, announce, effective, note}], 나스닥=[{cycle, announce, effective}] (결정 시점 표).
    - `events`: [{title, effective, note_top, add:[], remove:[], note}] — 각 편입/편출 이벤트. `add`/`remove` 항목은 `{ticker, name, biz(사업 내용 한 줄), reason(편입/편출 사유)}`. 빌더가 편입=초록·편출=빨강으로 렌더.
  - `sp500.criteria`: [{item, detail}] (편입 기준 표), `sp500.criteria_note`: str (예: MegaCap 컨설팅 결과).
  - `nasdaq100.rule_change`: {effective, rows:[{rule, before, after}], note} (패스트엔트리 룰 변경 전/후 표).
  - `nasdaq100.candidates`: [{name, biz, valuation, status}] (패스트엔트리 유력 대형 IPO 후보).
  ```json
  {"sp500":{"schedule":[{"q":"1분기","announce":"2026-03-06","effective":"2026-03-23(월) 개장 전","note":"셋째 금요일 마감 후"}],
            "events":[{"title":"2026년 1분기 편입/편출","effective":"3/23 적용",
                       "add":[{"ticker":"VRT","name":"Vertiv Holdings","biz":"데이터센터 전력·냉각 인프라","reason":"AI 수요로 시총 급증"}],
                       "remove":[{"ticker":"MTCH","name":"Match Group","biz":"데이팅 앱","reason":"순위 하락→SmallCap 강등"}],"note":"..."}],
            "criteria":[{"item":"시가총액","detail":"약 USD 20.5B 이상"}],"criteria_note":"2026-06-04 MegaCap 완화안 부결"},
   "nasdaq100":{"schedule":[{"cycle":"연례(연 1회)","announce":"12월 초","effective":"12월 셋째 금요일 마감 후"}],
                "events":[{"title":"2025년 12월 연례 재구성","effective":"12/22 적용","add":[],"remove":[]}],
                "rule_change":{"effective":"2026-05-01","rows":[{"rule":"대형 IPO 조기편입","before":"정례까지 대기","after":"상위 40위·15거래일 편입"}],"note":"..."},
                "candidates":[{"name":"SpaceX","biz":"발사체·위성통신","valuation":"약 $1.75조","status":"2026-06-12 상장(SPCX)"}]},
   "comment":"AI·반도체·우주 테마 편입 두드러짐","asof":"2026-06-14"}
  ```

## (v3.10.0) 추가 필드 — 3.1.5 반도체 주가 체크용 메모리+HBM 지표 대시보드

`gen_hbm_dashboard.py` 가 `charts/hbm_dashboard.png`(6패널 + EPS/PER 표)를 생성하고, `build_report.js renderKoreaExtras` 가 3.1.5 섹션에 임베드(파일 없으면 자동 생략·비차단). **모든 수치는 추정치** — HBMAgent 가 `nmr_hbm.json` 으로 저장하면 `merge.py` 가 `markets.hbm` 으로 전달(라이브 오버라이드). 미수집이면 생성기 내장 예시·추정값('예시·추정' 표기). 확인 불가 분기는 빈값.

- `markets.hbm` (= `nmr_hbm.json`). 시계열 키는 `[["YYYY-MM",값]…]`(월별) 또는 `[[연도,값]…]`(연도별):
  - `spot_index`: 메모리 종합 스팟 지수(월별, 기준 100). `ddr5_16gb`/`ddr4_8gb`/`nand_mlc_64gb`: 현물가(USD, 월별).
  - `hbm_shipment` `[[연도,십억Gb]…]`, `hbm_market` `[[연도,$B]…]`, `hbm3e_price`/`hbm4_price` `[[연도,USD]…]`.
  - `share`: [{year, samsung, sk_hynix, micron, others}] (others=기타·중국 CXMT 등, 합계 100%, 예상 E).
  - `gap_ratio` `[[연도,x]…]`. `eps_per`: [{name, eps_cur, eps_next, per_cur, per_next}]. `year_cur`/`year_next`, `asof`, `source`.


## (v3.11.0) 추가 필드 — 3.1 주요지표 (markets.macro)

`markets.macro` = {rates, inflation, employment, sentiment} — `build_report.js renderMacroIndicators` 가 **3.1 주요지표**(3.1.1 금리·통화정책 / 3.1.2 물가 / 3.1.3 고용 / 3.1.4 심리)를 렌더. 없으면 `merge.py` 내장 `MACRO_DEFAULT` 주입(비차단). `nmr_macro.json`(MacroAgent) 있으면 오버라이드.

- `rates`: `fed_funds{current,decision,bias,meaning,freq,impact}` · `policy_rates[{country,rate,asof,note}]`(6개국) · `policy_rates_chart` · `fomc_meetings[{date,stance,note}]`(빌더가 **최신순** 렌더, stance 에 '매파'=빨강/'비둘기'=초록) · `fomc_market_impact` · `us10y{current,1w_pct,1mo_pct,3mo_pct,6mo_pct,1y_pct,trend,spark}` · `yield_curve{label,spread,status,note,meaning,impact,chart}`(10Y-2Y).
- `inflation`: `chart`(통합 YoY) · `rows[{name,yoy,mom,asof,meaning,impact}]`(CPI·Core CPI·PCE·Core PCE·PPI) · `infl_exp_10y{current,trend,chart,meaning,freq,impact}`(표 없이 현재값+차트+해설).
- `employment`: `chart`(통합 6패널) · `rows[{name,value,asof,meaning,freq,impact}]`(NFP·실업률·GDP·ISM 제조/서비스·소매판매).
- `sentiment`: `rows[{name,current,1w_pct,1mo_pct,3mo_pct,6mo_pct,1y_pct,trend,spark,meaning,use}]`(VIX·VKOSPI·DXY·원/달러·WTI) · `spx_fwd{fwd_eps,fwd_per,asof,chart,note}` · `kospi_fwd{...}`.
- **재사용**: `merge.py` 가 `sentiment.rows` 의 VIX·DXY·원/달러·WTI 와 `rates.us10y` 를 `fetch_us.py` 시세(`us_markets`/`fx_markets`/`commodities.energy`)로 채움(중복수집 금지).
- **차트**: `gen_macro_charts.py` → `charts/macro_policy_rates.png`·`macro_curve.png`·`macro_inflation.png`·`macro_employment.png`·`macro_infl_exp.png`·`macro_spx_fwd.png`·`macro_kospi_fwd.png` + `charts/spark_{us10y,vix,vkospi,dxy,usdkrw,wti}.png`. 시계열 라이브 오버라이드는 `nmr_macro.json` 의 `macro.series.{fed_funds_5y,curve_10_2,inflation,infl_exp,employment,sentiment,spx_eps,spx_idx,kospi_eps,kospi_idx}`.

```json
{
  "rates": {
    "fed_funds": {"current": 3.63, "decision": "동결", "bias": "중립", "meaning": "연준 기준금리", "freq": "연 8회 회의", "impact": "금리↑ → 주식↓·달러↑·채권↓"},
    "policy_rates": [
      {"country": "미국", "rate": 3.63, "asof": "2026-05", "note": "FMP 실측(FedFunds)"},
      {"country": "한국", "rate": 2.50, "asof": "2026-05", "note": "BOK 기준금리(추정)"},
      {"country": "일본", "rate": 0.50, "asof": "2026-05", "note": "BOJ(추정)"},
      {"country": "중국", "rate": 3.00, "asof": "2026-05", "note": "1년 LPR(추정)"},
      {"country": "유로존", "rate": 2.15, "asof": "2026-05", "note": "ECB 예금금리(추정)"},
      {"country": "영국", "rate": 4.00, "asof": "2026-05", "note": "BOE(추정)"}
    ],
    "policy_rates_chart": "charts/macro_policy_rates.png",
    "fomc_meetings": [
      {"date": "2025-07-30", "stance": "동결(중립)", "note": "고금리 유지·인하 신중(추정)"},
      {"date": "2025-09-17", "stance": "인하(비둘기)", "note": "-25bp, 고용 둔화 반영(추정)"},
      {"date": "2025-10-29", "stance": "인하(비둘기)", "note": "-25bp 연속 인하(추정)"},
      {"date": "2025-12-10", "stance": "동결(중립)", "note": "인하 속도 조절 시사(추정)"},
      {"date": "2026-01-28", "stance": "동결(매파)", "note": "인플레 재반등 경계(추정)"},
      {"date": "2026-03-18", "stance": "동결(매파)", "note": "점도표 상향·인하 지연(추정)"},
      {"date": "2026-04-29", "stance": "동결(중립)", "note": "데이터 관망(추정)"},
      {"date": "2026-06-17", "stance": "동결(매파)", "note": "끈적한 물가에 매파 톤(추정)"}
    ],
    "fomc_market_impact": "매파(긴축)↑ → 금리↑ → 주식↓·달러↑   |   비둘기(완화)↑ → 금리↓ → 주식↑",
    "us10y": {"current": 4.46, "1w_pct": -0.7, "1mo_pct": 1.1, "3mo_pct": 2.0, "6mo_pct": -3.0, "1y_pct": 5.5, "trend": "고착·박스권", "spark": "charts/spark_us10y.png"},
    "yield_curve": {"label": "미국 장단기 금리차(수익률곡선)(10Y-2Y)", "spread": 0.27, "status": "정상(비역전)", "note": "2Y 4.19·10Y 4.46", "meaning": "단기-장기 금리차", "impact": "역전(단기>장기) → 경기침체 신호·주식↓", "chart": "charts/macro_curve.png"}
  },
  "inflation": {
    "chart": "charts/macro_inflation.png",
    "rows": [
      {"name": "CPI (소비자물가)", "yoy": 4.17, "mom": 0.47, "asof": "2026-05", "meaning": "일반 소비자 체감 물가", "impact": "CPI↑ → 금리↑ 기대 → 주식↓·달러↑·채권↓"},
      {"name": "Core CPI (식·에너지 제외)", "yoy": 3.1, "mom": 0.3, "asof": "2026-05", "meaning": "식·에너지 제외 물가(연준 가장 중시)", "impact": "Core CPI↑ → 금리↑ 방향 직접 결정"},
      {"name": "PCE (개인소비물가)", "yoy": 2.6, "mom": 0.2, "asof": "2026-04", "meaning": "연준 공식 인플레이션 목표 지표", "impact": "PCE↑ → 금리↑ 압력"},
      {"name": "Core PCE", "yoy": 2.8, "mom": 0.2, "asof": "2026-04", "meaning": "식·에너지 제외(연준 최우선)", "impact": "Core PCE↑ → 금리↑ 방향 직접 결정"},
      {"name": "PPI (생산자물가)", "yoy": 2.9, "mom": 0.1, "asof": "2026-05", "meaning": "기업 원가 변화", "impact": "PPI↑ → 금리↑ → 기업마진 압박·주식↓"}
    ],
    "infl_exp_10y": {"current": 2.35, "trend": "완만한 상승(추정)", "chart": "charts/macro_infl_exp.png", "meaning": "미래 인플레 기대수치", "freq": "매일", "impact": "10년 기대↑(2%대) + 실업률 4%대 → 테이퍼링·금리인상 언급"}
  },
  "employment": {
    "chart": "charts/macro_employment.png",
    "rows": [
      {"name": "NFP (비농업 신규고용)", "value": "+172K", "asof": "2026-05", "meaning": "신규 일자리 수", "freq": "매월 첫째 금요일", "impact": "NFP↑(강세) → 금리↑ → 주식↓·달러↑"},
      {"name": "실업률", "value": "4.3%", "asof": "2026-05", "meaning": "실직자 비율", "freq": "매월 첫째 금요일", "impact": "실업률↑ → 금리↓ 기대 → 주가↑"},
      {"name": "GDP (전기比 연율)", "value": "+1.6%", "asof": "26Q1", "meaning": "경제 전체 성장률", "freq": "분기별", "impact": "GDP↑ → 경기성장·실적 개선 가능성"},
      {"name": "ISM 제조업 PMI", "value": "48.7", "asof": "2026-05", "meaning": "기업 체감경기(제조)", "freq": "매월", "impact": "50↑ 경기확장 → 금리↑ 혼조"},
      {"name": "ISM 서비스 PMI", "value": "51.6", "asof": "2026-05", "meaning": "기업 체감경기(서비스)", "freq": "매월", "impact": "50↑ 경기확장 → 금리↑ 혼조"},
      {"name": "소매판매 (MoM)", "value": "+1.0%", "asof": "2026-05", "meaning": "소비 지표", "freq": "매월", "impact": "소매판매↑ → 경기과열 → 금리↑"}
    ]
  },
  "sentiment": {
    "rows": [
      {"name": "VIX (공포지수)", "current": 17.2, "1w_pct": -5.0, "1mo_pct": -8.0, "3mo_pct": -12.0, "6mo_pct": -6.0, "1y_pct": -10.0, "trend": "안정(추정)", "spark": "charts/spark_vix.png", "meaning": "변동성 예측", "use": "높을수록 등락 심화 → 현금 비중 늘려 관망"},
      {"name": "VKOSPI", "current": 18.0, "1w_pct": -3.0, "1mo_pct": -6.0, "3mo_pct": -9.0, "6mo_pct": -4.0, "1y_pct": -8.0, "trend": "안정(추정)", "spark": "charts/spark_vkospi.png", "meaning": "변동성 예측(코스피)", "use": "높을수록 등락 심화 → 현금 비중 늘려 관망"},
      {"name": "달러인덱스 DXY", "current": 98.1, "1w_pct": 0.3, "1mo_pct": -0.5, "3mo_pct": -1.8, "6mo_pct": -3.0, "1y_pct": -4.0, "trend": "약보합(추정)", "spark": "charts/spark_dxy.png", "meaning": "달러 가치", "use": "달러 강세 → 코스피 조정 역사"},
      {"name": "원/달러 환율", "current": 1380, "1w_pct": 0.2, "1mo_pct": 0.5, "3mo_pct": 1.0, "6mo_pct": 1.5, "1y_pct": 2.0, "trend": "원화 약세(추정)", "spark": "charts/spark_usdkrw.png", "meaning": "외국인 수급 영향", "use": "1,400원↑ → 외국인 이탈 가속"},
      {"name": "WTI 유가", "current": 71.5, "1w_pct": 1.5, "1mo_pct": -2.0, "3mo_pct": -5.0, "6mo_pct": -3.0, "1y_pct": -8.0, "trend": "박스권(추정)", "spark": "charts/spark_wti.png", "meaning": "인플레 압력", "use": "급등 → 인플레 → 금리상승 → 성장주 부담"}
    ],
    "spx_fwd": {"fwd_eps": 330, "fwd_per": 22.7, "asof": "2026-06", "chart": "charts/macro_spx_fwd.png", "note": "출처: LSEG/Yardeni 공개치(월간 캐시) — 추정. 지수 7,500 / EPS 330 → 선행PER 22.7배로 정합"},
    "kospi_fwd": {"fwd_eps": 918, "fwd_per": 9.8, "asof": "2026-06", "chart": "charts/macro_kospi_fwd.png", "note": "출처: 연합인포맥스/WISEfn(월간 캐시) — 추정. 지수 9,000 / EPS 918 → 선행PER 9.8배로 정합"}
  }
}

```
