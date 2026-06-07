# 서브에이전트 상세 프롬프트 및 반환 스키마 (v3.2)

7개 에이전트 전부 **general-purpose** 타입으로 호출한다.
Phase 1 = News/Markets/Commodities/Crypto/Securities/GlobalSecurities 6개를 **단일 메시지에 동시 발행**.
Phase 2 = AnalysisAgent 를 6개 결과와 함께 **단독 호출**.

모든 에이전트 프롬프트에 공통으로 포함할 문구:

> MCP 도구는 deferred 상태일 수 있다. 사용 전 반드시 `ToolSearch` 로 키워드 검색해 로드하라
> (예: `+UsStockInfo historical`, `+CoinInfo kimchi`). UUID 포함 도구명을 하드코딩하지 말 것.
> 실패한 항목은 null 또는 빈 배열로 반환하고 멈추지 말 것.
> 최종 출력은 지정된 JSON 만 반환할 것 (설명 문장 금지).

---

## 1. NewsAgent

**임무**: 글로벌 금융시장 Top News 10 + 향후 2주 주요 이벤트 캘린더 + 원화 톤 코멘트.

**도구**: NaverSearch MCP(있으면), web_fetch(한국경제 등), WebSearch, Claude in Chrome(가능하면 한국경제 https://www.hankyung.com/finance).
naver.com 도메인은 Chrome 에서 차단될 수 있음 → NaverSearch MCP 또는 web_fetch 로 대체.

**프롬프트 골자**:
- 오늘(KST) 기준 글로벌 금융시장에 영향이 큰 뉴스 10개를 선별 (미국·한국·중국·유럽·중동·원자재·코인 균형 있게)
- 각 뉴스: rank / headline / 2~4문장 summary / impact 라벨
- impact 값: `★ 강세` / `▲ 양면` / `▼ 부정` / `■ 중립` (필요시 `★ 매우 강세 (단기)` 처럼 보강 가능)
- **이벤트 캘린더 (2단 수집)**:
  ① `events_calendar` — 향후 1개월(오늘 포함) 시장 영향이 큰 이벤트 7~12건, 전체 중요도(★~★★★), 날짜순.
  ② `events_calendar_longterm` — 1개월 이후 ~ 1년, **중요도 ★★★만** 6~10건, 날짜순. 일정 미확정은 "7월 말 (예정)" 식 표기.
  대상: 중앙은행 회의(FOMC/ECB/BOJ/한은), 주요 경제지표(CPI/PCE/고용/GDP), 선물옵션 만기,
  대형 IPO·실적시즌, 선거·정치, 잭슨홀, MSCI 리뷰, 중국 정책회의 등.
- 원화 톤: krw_trend 1줄 + krw_comment (환율 수치 추세는 MarketsAgent 가 수집하므로 코멘트만)

**반환 JSON**:
```json
{
  "top_news": [
    {"rank": 1, "headline": "...", "summary": "...", "impact": "★ 강세"}
  ],
  "events_calendar": [
    {"date": "2026-06-11", "region": "한국", "event": "선물옵션 동시만기", "importance": "★★★", "expected_impact": "헤지 청산 시 변동성 급확대"}
  ],
  "events_calendar_longterm": [
    {"date": "2026-11-03", "region": "미국", "event": "중간선거", "importance": "★★★", "expected_impact": "정책 불확실성·재정 방향 분기점"}
  ],
  "fx_snapshot": {
    "krw_trend": "원화 약세 지속", "krw_comment": "..."
  }
}
```

---

## 2. MarketsAgent

**임무**: 글로벌 증시 + 매크로 지표 + **주요 환율**의 현재치와 단·중·장기 변화율.

**도구**: UsStockInfo MCP `get_historical_stock_prices`, `get_stock_info` (Yahoo Finance 기반).

**티커 맵**:
| 항목 | 티커 | 항목 | 티커 |
|------|------|------|------|
| 코스피 | ^KS11 | 닛케이 | ^N225 |
| 코스닥 | ^KQ11 | 상하이 | 000001.SS |
| S&P500 | ^GSPC | 항셍 | ^HSI |
| 나스닥 | ^IXIC | 센섹스 | ^BSESN |
| 다우 | ^DJI | 베트남 | VNM (ETF 대체) |
| VIX | ^VIX | 유로스톡스50 | ^STOXX50E |
| DXY | DX-Y.NYB | DAX | ^GDAXI |
| 美10년 | ^TNX | FTSE100 | ^FTSE |

**환율 티커 맵** (v3.1 신규):
| 통화쌍 | 티커 | 비고 |
|--------|------|------|
| USD/KRW | KRW=X | |
| EUR/KRW | EURKRW=X | |
| JPY/KRW | JPYKRW=X | **×100 (100엔 기준) 환산** |
| CNY/KRW | CNYKRW=X | |
| HKD/KRW | HKDKRW=X | |

**계산**: 1y 일봉을 받아 현재가 대비 1주/1개월/3개월/6개월/1년 변화율(%)을 계산. 각 항목에 `trend` 평가 1줄 (예: "단기 조정, 장기 상승"). 환율은 원화 관점 평가(상승=원화 약세).

**반환 JSON** (`data-schema.md` 의 markets 섹션):
```json
{
  "korea":          {"kospi": {"current": 0, "1w_pct": 0, "1mo_pct": 0, "3mo_pct": 0, "6mo_pct": 0, "1y_pct": 0, "trend": "..."}, "kosdaq": {}},
  "us_markets":     {"sp500": {}, "nasdaq": {}, "dow": {}, "vix": {}, "dxy": {}, "us10y": {}},
  "asia_markets":   {"nikkei": {}, "shanghai": {}, "hsi": {}, "sensex": {}, "vietnam": {}},
  "europe_markets": {"stoxx50": {}, "dax": {}, "ftse": {}},
  "fx_markets":     {"usd_krw": {}, "eur_krw": {}, "jpy_krw": {}, "cny_krw": {}, "hkd_krw": {}}
}
```

---

## 3. CommoditiesAgent

**임무**: 에너지·금속·농산물 원자재 추세.

**도구**: UsStockInfo MCP (선물 티커).

**티커 맵**: WTI `CL=F` / Brent `BZ=F` / 천연가스 `NG=F` / 금 `GC=F` / 은 `SI=F` / 구리 `HG=F` / 백금 `PL=F` / **희토류 `REMX`** (VanEck Rare Earth ETF — 희토류는 선물 티커가 없어 ETF 프록시 사용) / 옥수수 `ZC=F` / 대두 `ZS=F` / 밀 `ZW=F`.
선물 티커는 간헐 실패함 → 실패 시 `current: null` 로 두고 진행.

**반환 JSON**:
```json
{
  "energy":      {"wti": {"current": 0, "1w_pct": 0, "1mo_pct": 0, "3mo_pct": 0, "6mo_pct": 0, "1y_pct": 0, "trend": "..."}, "brent": {}, "natgas": {}},
  "metals":      {"gold": {}, "silver": {}, "copper": {}, "platinum": {}, "rare_earth": {}},
  "agriculture": {"corn": {}, "soybean": {}, "wheat": {}},
  "commentary":  "원자재 종합 코멘트 2~3문장"
}
```

---

## 4. CryptoAgent

**임무**: 암호화폐 시장 개요 + 공포·탐욕 + 김치프리미엄 + 등락 상위.

**도구**: CoinInfo MCP — `get_market_overview`, `get_fear_greed_index`, `get_kimchi_premium`(BTC/ETH/XRP/SOL), `get_top_gainers`, `get_top_losers`, `get_coin_dominance`.
gainers/losers/dominance 는 간헐 오류 → null/빈배열로 두고 진행.

**반환 JSON**:
```json
{
  "market_overview": {"total_volume_24h_usd": 0, "avg_change_pct": 0, "coins_up": 0, "coins_down": 0, "btc_dominance": 0},
  "fear_greed": {"current": 0, "classification": "공포", "yesterday": 0, "last_week": 0, "last_month": 0},
  "kimchi_premium": {
    "rate_usd_krw": 0,
    "coins": [{"symbol": "BTC", "upbit_krw": 0, "binance_usd": 0, "premium_pct": 0, "status": "프리미엄|디스카운트"}]
  },
  "top_gainers": [{"symbol": "...", "change_pct": 0}],
  "top_losers":  [{"symbol": "...", "change_pct": 0}]
}
```

---

## 5. SecuritiesAgent

**임무**: 한국 5대 증권사 리서치 핵심 메시지 수집. SKILL.md 부록 A 의 강점표를 프롬프트에 포함해 각 사의 강점 영역 시각을 우선 수집한다.

**도구**: Claude in Chrome (사이트 접속), WebSearch 보조.
접속 실패 사이트는 `key_reports: []`, `key_message: ""` 로 둘 것 — 빌더가 "(리포트 수집 실패)" 로 렌더링.

**반환 JSON**:
```json
{
  "shinhan":    {"strength": "자산배분 통합", "channels": ["쏠쏠한 리포트"], "key_reports": ["..."], "key_message": "...", "asset_allocation_view": "..."},
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

---

## 6. GlobalSecuritiesAgent (v3.2 신규)

**임무**: 해외 주요 IB 5사(UBS·Goldman Sachs·J.P. Morgan·Morgan Stanley·BlackRock)의 최신 하우스 뷰 수집. SKILL.md 부록 B 의 강점표를 프롬프트에 포함해 각 사의 강점 영역 시각을 우선 수집한다.

**도구**: WebSearch 주력 (예: "UBS CIO daily view", "Goldman Sachs S&P 500 target", "Morgan Stanley Mike Wilson outlook", "BlackRock weekly commentary"), mcp__workspace__web_fetch 로 공개 Insights 페이지 보강. Bigdata.com MCP `bigdata_search` 가 있으면 활용.
Chrome 브라우저 도구는 사용하지 말 것 (메인 세션/SecuritiesAgent 와 충돌).

**주의**:
- 원문 리포트(목표주가 PDF)는 고객 전용 → 공개 채널·언론 보도로 핵심 메시지만 수집.
- 보조: UsStockInfo MCP `get_recommendations` 로 주요 종목 월가 컨센서스 확인 가능.
- 수집 실패한 기관은 key_reports: [], key_message: "" 로 두고 진행.

**반환 JSON**:
```json
{
  "ubs":            {"strength": "CIO House View 자산배분·일일 시황", "channels": ["UBS CIO Daily"], "key_reports": ["..."], "key_message": "...", "house_view": "..."},
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

**임무**: Phase 1 의 6개 JSON 전체를 입력으로 받아 종합 분석과 포트폴리오를 도출. 외부 도구 불필요(입력 데이터만으로 추론).

**프롬프트에 6개 결과 JSON 을 그대로 첨부**하고 아래를 요구:
- `summary`: 3~5문장 Executive Summary (보고서 맨 앞에 들어감)
- `macro_view`: 매크로 톤 1문단
- `key_themes`: 3~6개 {theme, direction(▲/▼/■), comment}
- `key_risks`: 3~5개 리스크 문장
- `asset_view`: 자산군별 단·중·장기 견해 1줄씩. **키명은 정확히 다음을 사용**:
  `us_equity, kr_equity, china_equity, japan_equity, em_equity, europe_equity, kr_treasury, us_treasury, gold, oil, btc`
  (빌더 v1.2.2 부터는 `cn_equity/jp_equity/eu_equity/kr_bond/us_bond` 축약 별칭도 수용하지만 위 정식 키를 우선 사용할 것)
- `portfolios`: aggressive/balanced/conservative — label, expected_return, max_drawdown, rebalance, allocation[{asset, weight_pct, vehicle}] (비중 합계 100%)
- `action_items`: 단기·중기·장기 체크리스트 5~8개

**반환 JSON**: `data-schema.md` 의 analysis 섹션과 동일.
