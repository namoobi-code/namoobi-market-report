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
- `markets.bigtech_capex`: {rows:[{company:str, y2025:str, y2026:str, comment:str}], comment:str}.
- `commodities.strategic_metals`: {etf:[{name:str, current:num, "1w_pct"~"1y_pct":num, trend:str}], etf_comment:str, spot:[{item:str, price:str, comment:str}], comment:str}.
