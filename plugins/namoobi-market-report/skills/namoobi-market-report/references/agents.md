# 서브에이전트 상세 프롬프트 및 반환 스키마 (v3)

6개 에이전트 전부 **general-purpose** 타입으로 호출한다.
Phase 1 = News/Markets/Commodities/Crypto/Securities 5개를 **단일 메시지에 동시 발행**.
Phase 2 = AnalysisAgent 를 5개 결과와 함께 **단독 호출**.

모든 에이전트 프롬프트에 공통으로 포함할 문구:

> MCP 도구는 deferred 상태일 수 있다. 사용 전 반드시 `ToolSearch` 로 키워드 검색해 로드하라
> (예: `+UsStockInfo historical`, `+CoinInfo kimchi`). UUID 포함 도구명을 하드코딩하지 말 것.
> 실패한 항목은 null 또는 빈 배열로 반환하고 멈추지 말 것.
> 최종 출력은 지정된 JSON 만 반환할 것 (설명 문장 금지).

---

## 1. NewsAgent

**임무**: 글로벌 금융시장 Top News 10 + 환율 스냅샷.

**도구**: NaverSearch MCP(있으면), web_fetch(한국경제 등), WebSearch, Claude in Chrome(가능하면 한국경제 https://www.hankyung.com/finance).
naver.com 도메인은 Chrome 에서 차단될 수 있음 → NaverSearch MCP 또는 web_fetch 로 대체.

**프롬프트 골자**:
- 오늘(KST) 기준 글로벌 금융시장에 영향이 큰 뉴스 10개를 선별 (미국·한국·중국·유럽·중동·원자재·코인 균형 있게)
- 각 뉴스: rank / headline / 2~4문장 summary / impact 라벨
- impact 값: `★ 강세` / `▲ 양면` / `▼ 부정` / `■ 중립` (필요시 `★ 매우 강세 (단기)` 처럼 보강 가능)
- 환율 스냅샷: USD/EUR/JPY(100엔)/CNY/HKD 대 KRW + 원화 추세 1줄

**반환 JSON**:
```json
{
  "top_news": [
    {"rank": 1, "headline": "...", "summary": "...", "impact": "★ 강세"}
  ],
  "fx_snapshot": {
    "USD_KRW": "1495.25", "EUR_KRW": "1743", "JPY_KRW": "938.46",
    "CNY_KRW": "220.34", "HKD_KRW": "190.87",
    "krw_trend": "원화 약세 지속", "krw_comment": "..."
  }
}
```

---

## 2. MarketsAgent

**임무**: 글로벌 증시 + 매크로 지표의 현재치와 단·중·장기 변화율.

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

**계산**: 1y 일봉을 받아 현재가 대비 1주/1개월/3개월/6개월/1년 변화율(%)을 계산. 각 항목에 `trend` 평가 1줄 (예: "단기 조정, 장기 상승").

**반환 JSON** (`data-schema.md` 의 markets 섹션):
```json
{
  "korea":          {"kospi": {"current": 0, "1w_pct": 0, "1mo_pct": 0, "3mo_pct": 0, "6mo_pct": 0, "1y_pct": 0, "trend": "..."}, "kosdaq": {}},
  "us_markets":     {"sp500": {}, "nasdaq": {}, "dow": {}, "vix": {}, "dxy": {}, "us10y": {}},
  "asia_markets":   {"nikkei": {}, "shanghai": {}, "hsi": {}, "sensex": {}, "vietnam": {}},
  "europe_markets": {"stoxx50": {}, "dax": {}, "ftse": {}}
}
```

---

## 3. CommoditiesAgent

**임무**: 에너지·금속·농산물 원자재 추세.

**도구**: UsStockInfo MCP (선물 티커).

**티커 맵**: WTI `CL=F` / Brent `BZ=F` / 천연가스 `NG=F` / 금 `GC=F` / 은 `SI=F` / 구리 `HG=F` / 백금 `PL=F` / 옥수수 `ZC=F` / 대두 `ZS=F` / 밀 `ZW=F`.
선물 티커는 간헐 실패함 → 실패 시 `current: null` 로 두고 진행.

**반환 JSON**:
```json
{
  "energy":      {"wti": {"current": 0, "1w_pct": 0, "1mo_pct": 0, "3mo_pct": 0, "6mo_pct": 0, "1y_pct": 0, "trend": "..."}, "brent": {}, "natgas": {}},
  "metals":      {"gold": {}, "silver": {}, "copper": {}, "platinum": {}},
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

## 6. AnalysisAgent (마지막 단독 호출)

**임무**: Phase 1 의 5개 JSON 전체를 입력으로 받아 종합 분석과 포트폴리오를 도출. 외부 도구 불필요(입력 데이터만으로 추론).

**프롬프트에 5개 결과 JSON 을 그대로 첨부**하고 아래를 요구:
- `summary`: 3~5문장 Executive Summary (보고서 맨 앞에 들어감)
- `macro_view`: 매크로 톤 1문단
- `key_themes`: 3~6개 {theme, direction(▲/▼/■), comment}
- `key_risks`: 3~5개 리스크 문장
- `asset_view`: 자산군별(미국/한국/중국/일본/신흥/유럽 주식, 한·미 국채, 금, 원유, BTC) 단·중·장기 견해 1줄씩
- `portfolios`: aggressive/balanced/conservative — label, expected_return, max_drawdown, rebalance, allocation[{asset, weight_pct, vehicle}] (비중 합계 100%)
- `action_items`: 단기·중기·장기 체크리스트 5~8개

**반환 JSON**: `data-schema.md` 의 analysis 섹션과 동일.
