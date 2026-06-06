# 통합 데이터 JSON 스키마 (v3)

build_report.js v3 가 기대하는 통합 JSON 구조. 각 섹션은 해당 에이전트의 반환값을 그대로 넣는다.
누락 필드는 빌더가 `-` 로 렌더링하므로, 실패 항목은 null/빈배열로 두면 된다.

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
  "securities":  { "...": "SecuritiesAgent 반환 (5사 + common_themes + investor_type_recommendation)" },
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
    {"rank": 1, "headline": "코스피 사상 첫 8000 돌파", "summary": "2~4문장", "impact": "★ 강세"}
  ],
  "fx_snapshot": {
    "USD_KRW": "1495.25", "EUR_KRW": "1743", "JPY_KRW": "938.46",
    "CNY_KRW": "220.34", "HKD_KRW": "190.87",
    "krw_trend": "원화 약세", "krw_comment": "..."
  }
}
```

impact 값: `★ 강세` / `▲ 양면` / `▼ 부정` / `■ 중립` (보강 표기 허용).

## markets

```json
{
  "korea":          {"kospi": {}, "kosdaq": {}},
  "us_markets":     {"sp500": {}, "nasdaq": {}, "dow": {}, "vix": {}, "dxy": {}, "us10y": {}},
  "asia_markets":   {"nikkei": {}, "shanghai": {}, "hsi": {}, "sensex": {}, "vietnam": {}},
  "europe_markets": {"stoxx50": {}, "dax": {}, "ftse": {}}
}
```

## commodities

```json
{
  "energy":      {"wti": {}, "brent": {}, "natgas": {}},
  "metals":      {"gold": {}, "silver": {}, "copper": {}, "platinum": {}},
  "agriculture": {"corn": {}, "soybean": {}, "wheat": {}},
  "commentary":  "원자재 종합 코멘트"
}
```

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

## analysis

```json
{
  "summary": "Executive Summary 3~5문장 (보고서 맨 앞 1페이지)",
  "macro_view": "매크로 톤 1문단",
  "key_themes": [{"theme": "AI 반도체", "direction": "▲", "comment": "..."}],
  "key_risks": ["..."],
  "asset_view": {
    "us_equity": "...", "kr_equity": "...", "china_equity": "...", "japan_equity": "...",
    "em_equity": "...", "europe_equity": "...", "kr_treasury": "...", "us_treasury": "...",
    "gold": "...", "oil": "...", "btc": "..."
  },
  "portfolios": {
    "aggressive":   {"label": "공격형", "expected_return": "연 15~25%", "max_drawdown": "-30%", "rebalance": "월 1회",
                     "allocation": [{"asset": "미국 기술주", "weight_pct": 40, "vehicle": "QQQ, SMH"}]},
    "balanced":     {"label": "중립형", "expected_return": "...", "max_drawdown": "...", "rebalance": "...", "allocation": []},
    "conservative": {"label": "안정형", "expected_return": "...", "max_drawdown": "...", "rebalance": "...", "allocation": []}
  },
  "action_items": ["[단기] ...", "[중기] ...", "[장기] ..."]
}
```

각 포트폴리오 allocation 의 weight_pct 합계는 100 이어야 한다.
