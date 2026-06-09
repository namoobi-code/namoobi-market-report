# 서브에이전트 상세 프롬프트 및 반환 스키마 (v3.3.0)

7개 에이전트 전부 **general-purpose** 타입으로 호출한다.
Phase 1 = News/Markets/Commodities/Crypto/Securities/GlobalSecurities 6개를 **단일 메시지에 동시 발행**.
Phase 2 = AnalysisAgent 를 6개 결과와 함께 **단독 호출**.

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

## 1. NewsAgent

**임무**: 글로벌 금융시장 Top News 10 + 향후 2주 주요 이벤트 캘린더 + 원화 톤 코멘트.

**도구**: NaverSearch MCP(있으면), web_fetch(한국경제 등), WebSearch, Claude in Chrome(가능하면 한국경제 https://www.hankyung.com/finance).
naver.com 도메인은 Chrome 에서 차단될 수 있음 → NaverSearch MCP 또는 web_fetch 로 대체.

**프롬프트 골자**:
- 오늘(KST) 기준 글로벌 금융시장에 영향이 큰 뉴스 10개를 선별 (미국·한국·중국·유럽·중동·원자재·코인 균형 있게)
- 각 뉴스: rank / headline / 2~4문장 summary / impact 라벨 / **source(매체명) / source_url(원문 링크) / published_date(YYYY-MM-DD)**
- **(v3.3.0 출처 의무)** 모든 뉴스는 실제 검색·fetch 로 확인한 **출처와 URL**을 반드시 포함한다. URL 을 확보하지 못한 헤드라인은 **목록에서 제외**한다 (출처 없는 뉴스 생성 금지). headline·summary 는 원문 내용에 충실하게 쓰고, 원문에 없는 수치·인용을 지어내지 않는다.
- impact 값: `★ 강세` / `▲ 양면` / `▼ 부정` / `■ 중립` (필요시 `★ 매우 강세 (단기)` 처럼 보강 가능)
- **이벤트 캘린더 (2단 수집)**:
  ① `events_calendar` — 향후 1개월(오늘 포함) 시장 영향이 큰 이벤트 7~12건, 전체 중요도(★~★★★), 날짜순.
  ② `events_calendar_longterm` — 1개월 이후 ~ 1년, **중요도 ★★★만** 6~10건, 날짜순. 일정 미확정은 "7월 말 (예정)" 식 표기.
  대상: 중앙은행 회의(FOMC/ECB/BOJ/한은), 주요 경제지표(CPI/PCE/고용/GDP), 선물옵션 만기,
  대형 IPO·실적시즌, 선거·정치, 잭슨홀, MSCI 리뷰, 중국 정책회의 등.
  - **(v3.3.0 날짜 grounding)** 이벤트 날짜는 **반드시 공식·1차 출처에서 확인**한다 (중앙은행 IR/통계청·노동부 발표 일정, 거래소 만기 공지, 선거관리 일정 등). `events_calendar` 도구가 있으면 그 결과를 우선 사용한다. **기억에 의존해 날짜를 지어내지 말 것** — 확인되지 않은 일정은 날짜 칸에 `(미확정)` 으로 두고, 가능하면 `source` 에 근거 링크를 적는다. 과거에 지나간 날짜를 향후 일정으로 넣지 않도록 오늘(KST) 기준으로 검증한다.
- 원화 톤: krw_trend 1줄 + krw_comment (환율 수치 추세는 MarketsAgent 가 수집하므로 코멘트만)

**반환 JSON**:
```json
{
  "top_news": [
    {"rank": 1, "headline": "...", "summary": "...", "impact": "★ 강세",
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

**계산**: `get_historical_stock_prices(period="1y", interval="1wk")` **주봉**을 받아 (일봉 금지 — 토큰 5배·시간 2배 낭비, v3.2.3 속도 규칙) 현재가 대비 1주(직전 주봉)/1개월(~4주)/3개월(~13주)/6개월(~26주)/1년(최초 데이터) 변화율(%)을 계산. 각 항목에 `trend` 평가 1줄 (예: "단기 조정, 장기 상승"). 환율은 원화 관점 평가(상승=원화 약세).

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

**도구**: UsStockInfo MCP (선물 티커). `get_historical_stock_prices(period="1y", interval="1wk")` **주봉** 사용 (일봉 금지 — v3.2.3 속도 규칙). 변화율 계산은 MarketsAgent 와 동일(1주=직전 주봉).

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
gainers/losers/dominance 는 간헐 오류(429 등) → null/빈배열로 두고 진행.

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

**도구**: WebSearch / mcp__workspace__web_fetch / NaverSearch MCP(있으면). 키움 텔레그램(https://t.me/s/KiwoomResearch)은 web_fetch 로 직접 읽을 수 있다.
**Chrome 브라우저 도구는 사용하지 말 것** (메인 세션·다른 에이전트와 충돌 — v3.2.4 명시).
접속 실패 사이트는 `key_reports: []`, `key_message: ""` 로 둘 것 — 빌더가 "(리포트 수집 실패)" 로 렌더링.
**(v3.3.0 출처 의무)** `key_message` 와 각 `view` 는 **실제로 읽은 공개 리포트·기사 근거에서만** 작성한다. 접근하지 못한 증권사의 시각을 기억으로 지어내지 말 것 — 못 읽었으면 빈 값으로 둔다. `key_reports` 항목은 가능하면 `{"title","url","date"}` 객체로 출처 링크를 함께 담는다(문자열도 하위호환 허용).

**반환 JSON**:
```json
{
  "shinhan":    {"strength": "자산배분 통합", "channels": ["쏠쏠한 리포트"],
                 "key_reports": [{"title": "6월 자산배분 전략", "url": "https://...", "date": "2026-06-09"}],
                 "key_message": "...", "asset_allocation_view": "..."},
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
> `key_reports` 는 문자열 배열 `["..."]` 또는 객체 배열 `[{"title","url","date"}]` 둘 다 허용한다 (빌더가 양쪽 렌더).

---

## 6. GlobalSecuritiesAgent (v3.2 신규)

**임무**: 해외 주요 IB 5사(UBS·Goldman Sachs·J.P. Morgan·Morgan Stanley·BlackRock)의 최신 하우스 뷰 수집. SKILL.md 부록 B 의 강점표를 프롬프트에 포함해 각 사의 강점 영역 시각을 우선 수집한다.

**도구**: WebSearch 주력 (예: "UBS CIO daily view", "Goldman Sachs S&P 500 target", "Morgan Stanley Mike Wilson outlook", "BlackRock weekly commentary"), mcp__workspace__web_fetch 로 공개 Insights 페이지 보강. Bigdata.com MCP `bigdata_search` 가 있으면 활용.
Chrome 브라우저 도구는 사용하지 말 것 (메인 세션/SecuritiesAgent 와 충돌).

**주의**:
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
- `key_themes`: 3~6개 {theme, direction(▲/▼/■), comment}
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
- 저장 후 node 로 JSON.parse 검증까지 수행하도록 지시.

**반환 JSON**: `data-schema.md` 의 analysis 섹션과 동일.
