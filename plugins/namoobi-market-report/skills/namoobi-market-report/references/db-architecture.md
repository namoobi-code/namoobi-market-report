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
- **누적형(accumulate) DB**(CAPEX·HBM): 덮어쓰지 말고 신규 관측치를 키로 upsert 하여 시계열을 계속 쌓는다(매 실행 DB 업그레이드).

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
| 3.1.6 | **AI 빅테크 CAPEX(MSFT·GOOGL·AMZN·META·ORCL)+2그래프** | **[DB화]+누적 업그레이드** | 실적/가이던스 분기 | `nmr_capex.json` (기존 승계) |
| 3.1.7 | **메모리+HBM(그래프 6종·HBM 3사 EPS/PER·대시보드)** | **[DB화]+누적 업그레이드** | 분기 컨센서스/실적 | `nmr_hbm.json` (기존 승계) |
| 3.1.8 | **경기선행지수 순환변동치(표·그래프)** | **[DB화]** | 통계청 최신 발표월 | `db/leading.json` (fetch_leading 실측→DB) |
| 3.1.10 | **관세청 수출 주요품목별 10일 단위 잠정치(2년치 그래프 2종)** | **[DB화]** | 최근 4개월 해시(신규 순보·현행화 감지) | `db/customs.json` (fetch_customs 실측→DB) |

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
- **`scripts/merge.py`**: 매 실행 6개 비매일 섹션(**inflation·employment·policy_rates·fomc_meetings·dot_plot·leading**)을 자동 DB 동기화 — 신규조사분 있으면 `set`(marker=섹션 최신 발표/결정일), **비면 `get` 으로 DB값 재사용**(라이브 실패에도 stale/'-' 금지). 누적형(CAPEX·HBM)은 기존 전용 DB(nmr_capex·nmr_hbm) 유지.
- **에이전트 마커체크(조사 스킵·선택적 최적화)**: 수집 에이전트는 각 섹션의 저렴한 마커(예: 최신 CPI 발표월·FOMC 결정일·통계청 발표월)를 1회 관측해 `nmr_db.py check <item> <marker>` → **reuse 면 그 섹션 수집을 건너뛴다**(merge 가 DB값 사용); due(변경·확인불가)면 조사. 마커 관측 실패=불확실이면 무조건 조사(stale 금지).

## [DB화 v2] 차트 시계열 누적 DB + 마커체크 폐지 (2026-06)

- **대원칙**: 모든 지표는 매 실행 최신값 조사·반영. 발표주기가 매일이 아닌 지표는 변동 시에만 DB 갱신, 미변동이면 DB값 그대로 사용 + 캡션 "업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지".
- **차트 시계열 DB(신규)**: `nmr_db.dbseries(item, fresh, dbdir[, prefer_fresh])` — 표 rows 뿐 아니라 차트용 시계열을 `db/series_<item>.json` 에 저장·누적. 날짜쌍 `[["YYYY-MM(-DD)",v]..]` 은 날짜 union 누적(부실 수집 회차를 과거 DB가 메움), 평면 배열은 더 긴 쪽 채택. `gen_macro_charts.py` 가 매 실행 기준금리(fed_funds_5y)·곡선(curve_10_2)·us2y/us10y 일별·물가 5라인·BEI(infl_exp)·고용 6패널을 dbseries 로 누적 → **부실 수집이어도 차트 항상 완전**. (BEI 는 prefer_fresh=True: 매번 조사, DB는 폴백.) us2y/vkospi 일별은 nmr_indexseries 에 주입돼 spark_us2y/spark_vkospi 생성.
- **CAPEX 풀매트릭스**: `merge.py` 가 표(`bigtech_capex.rows`)를 2024~2029 전 연도 capex·매출·FCF·비율로 보강(표 actuals 우선·결측은 컨센서스) → `nmr_capex.json` DB 누적 → **표와 차트(gen_capex_chart)가 항상 일치**.
- **마커체크(구 nmr_cache.py·Phase 1.0) 폐지**: 별도 마커 관측·조사 스킵 최적화를 제거. 통합 DB(merge.py + nmr_db)가 변동체크·미변동 재사용·시계열 누적을 일원 담당.

## [DB화 v3] 변경감지 마커 복원 + 셀단위 백필 + 실패 플래그 (2026-06)

- **문제**: '조사 실패(null)'를 '변경없음'으로 둔갑시켜 DB를 조용히 쓰면 실제 변경을 놓친다(사용자 지적).
- **dbseries(시계열)**: 마커(시계열 최신시점) 비교 → status = `updated`(마커 변경=신규 데이터) / `reused`(동일=변경없음) / **`unverified`(fresh null=조사 실패)**. unverified 는 조용히 DB 쓰지 않고 플래그한다.
- **dbrows(표 행)**: 셀 단위 병합 — fresh 셀에 값 있으면 fresh(변경 반영), null/'-' 이면 DB 셀 백필(조용한 '-' 방지). DB는 null 로 덮지 않음. 백필된 셀 목록 = '변경 미확인'.
- **표면화(조용히 통과 금지)**: merge 가 `macro._db_unverified`={rows_backfilled, series_unverified} 기록 → build_report 빨간 캡션('⚠ 변경 미확인 …'), verify_report req13 경고. 다음 실행에서 재조사로 갱신.
- **적용**: 3.1.2 물가·3.1.3 고용 표(dbrows), 3.1 매크로 차트 시계열(dbseries). (구 '조사-스킵 마커체크'는 여전히 폐지 — 매일 조사는 항상 수행하고, 마커는 변경/실패 판정용.)
