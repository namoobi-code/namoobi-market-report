# 비매일 지표 DB화 아키텍처 (Big Architecture) — v1.0

> 사용자 확정 스펙(2026-06). 본 문서가 3.1 매크로 대시보드의 **갱신·저장 정책의 단일 권위**다.
> SKILL.md '핵심 수집 규칙'·agents.md·merge.py·build_report.js 는 본 문서를 따른다.

## ※ UPDATE 원칙 (대원칙)

- **모든 지표는 매일 최신값을 조사·반영**하는 것이 대원칙.
- **단, 발표주기가 매일이 아닌 '모든 지표'는 [DB화]**:
  1. 보고서에 **"업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지"** 캡션을 명시한다.
  2. DATA를 **별도 DB(파일)** 에 저장한다.
  3. 매 실행 **변동 여부만** 조사한다(저렴한 마커 1회 관측).
  4. **변동이 없으면 DB(파일)에 저장된 값을 그대로 사용**한다(무거운 재조사 스킵).
- 변동 판정이 **불확실/확인 불가**면 stale 금지 — 조사 후 DB 갱신(as_of 명시).

## DB 저장 규약

- 위치: 연결폴더 `D:\claudeCowork\_market_report_data\db\<item>.json` (없으면 outputs 폴백).
- 스키마: `{ "marker": <변동감지 마커>, "as_of": "YYYY-MM-DD", "data": <섹션 데이터> }`.
- 인터페이스(`scripts/nmr_db.py`): `check <item> <observed_marker>` → `reuse|due`,
  `get <item>` → data, `set <item> <as_of> <marker>` (stdin=data JSON).
- merge.py: DB화 섹션은 이번 런 신규조사분이 있으면 그것으로 `set`, 없으면 `get` 으로 주입.
- **누적형(accumulate) DB**(Forward EPS/PER·CAPEX·HBM): 덮어쓰지 말고 신규 관측치를 키로 upsert 하여 시계열을 계속 쌓는다(매 실행 DB 업그레이드).

## 섹션별 DB화 맵 (3.1 매크로 대시보드)

| 섹션 | 항목 | 정책 | 마커(변동감지) | DB 파일 |
|------|------|------|----------------|---------|
| 3.1.1 | 美 국채금리(10Y·2Y) | **매일 실측** | — | (DB 아님) |
| 3.1.1 | 미국 장단기 금리차(10Y-2Y)+그래프 | **매일 실측** | — | (DB 아님) |
| 3.1.1 | 하이일드(HY) 스프레드+그래프 | **매일 실측** | — | (DB 아님) |
| 3.1.1 | **FOMC 기준금리 + 6개국 정책금리(표·그래프)** | **[DB화]** | 각국 정책금리 변경일/최근 결정일 | `db/policy_rates.json` |
| 3.1.1 | **FOMC 회의 일정·정책방향(표)** | **[DB화]** | 최신 FOMC 개최일 | `db/fomc_meetings.json` |
| 3.1.1 | **FOMC 점도표(표)** | **[DB화]** | 최신 SEP(3·6·9·12월) 발표일 | `db/dot_plot.json` (기존 nmr_cache dot_plot 승계) |
| 3.1.2 | **CPI·Core CPI·PCE·Core PCE·PPI(표)+통합차트** | **[DB화]** | 각 지표 최신 발표일(월별) | `db/inflation.json` |
| 3.1.2 | 기대인플레이션(10년 BEI) 표·차트 | **매번 조사**(실시간) | — | (DB 아님) |
| 3.1.3 | **고용·경기 6종(NFP·실업률·소매판매·ISM제조·ISM서비스·GDP)+통합차트** | **[DB화]** | 각 지표 최신 발표일 | `db/employment.json` |
| 3.1.4 | 심리(VIX·KSVKOSPI·DXY·원/달러·WTI·美10Y) | **매일 실측** | — | (지표\|의미\|시장영향 텍스트만 canonical 재사용) |
| 3.1.5 | **지수·Forward EPS·PER(표·그래프·최신5건)** | **[DB화]+누적 업그레이드** | 신규 조사일(월키 upsert) | `nmr_fwd_history.json` (기존 승계) |
| 3.1.6 | **AI 빅테크 CAPEX(MSFT·GOOGL·AMZN·META·ORCL)+2그래프** | **[DB화]+누적 업그레이드** | 실적/가이던스 분기 | `nmr_capex.json` (기존 승계) |
| 3.1.7 | **메모리+HBM(그래프 6종·HBM 3사 EPS/PER·대시보드)** | **[DB화]+누적 업그레이드** | 분기 컨센서스/실적 | `nmr_hbm.json` (기존 승계) |
| 3.1.8 | **경기선행지수 순환변동치(표·그래프)** | **[DB화]** | 통계청 최신 발표월 | `db/leading.json` (fetch_leading 실측→DB) |

## 표준 캡션 (DB화 섹션 공통)

`업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지`

- 3.1.2 물가는 위 캡션 + `, BEI는 실시간`.
- build_report.js 가 각 DB화 섹션 헤더 직하에 본 캡션을 렌더(매일 실측 섹션엔 미표기).

## 3.1.4 지표·의미·시장영향 canonical 재사용

심리 보조지표 표의 `의미`·`시장영향` 텍스트는 매번 생성하지 말고 빌더 내 canonical 사전을 재사용한다(값만 매일 실측).

## 캐시→DB 마이그레이션 노트

기존 `nmr_cache.py`(dot_plot·berkshire·index_rebalance·hy_spread·cautions·leading)는 본 DB화의 부분집합이다.
`nmr_db.py` 는 이를 일반화(섹션 무관 store/check/reuse)하며, 신규 항목(policy_rates·fomc_meetings·inflation·employment)을 추가한다.
berkshire·index_rebalance 는 3.1 외 섹션이나 동일 메커니즘(변동감지·DB재사용)을 공유한다.

## 구현 상태 (v1.1 — 완료)

- **`scripts/nmr_db.py`**: 범용 DB 모듈 — `check <item> <marker>`(reuse/due) · `get` · `set`(stdin=data) · `upsert`(누적형, keyfield 병합) · `list`. DB=`_market_report_data/db/<item>.json`={marker,as_of,data}.
- **`scripts/merge.py`**: 매 실행 6개 비매일 섹션(**inflation·employment·policy_rates·fomc_meetings·dot_plot·leading**)을 자동 DB 동기화 — 신규조사분 있으면 `set`(marker=섹션 최신 발표/결정일), **비면 `get` 으로 DB값 재사용**(라이브 실패에도 stale/'-' 금지). 누적형(fwd EPS/PER·CAPEX·HBM)은 기존 전용 DB(nmr_fwd_history·nmr_capex·nmr_hbm) 유지.
- **에이전트 마커체크(조사 스킵·선택적 최적화)**: 수집 에이전트는 각 섹션의 저렴한 마커(예: 최신 CPI 발표월·FOMC 결정일·통계청 발표월)를 1회 관측해 `nmr_db.py check <item> <marker>` → **reuse 면 그 섹션 수집을 건너뛴다**(merge 가 DB값 사용); due(변경·확인불가)면 조사. 마커 관측 실패=불확실이면 무조건 조사(stale 금지).
