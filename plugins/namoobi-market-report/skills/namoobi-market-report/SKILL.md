---
name: namoobi-market-report
description: |
  글로벌 금융시장 종합 시황 보고서를 자동 생성·발송하는 워크플로우. 사용자가
  "글로벌 시황 보고서", "오늘 시장 보고서 보내줘", "global market report",
  "daily market briefing", "매일 시황 발송", "코스피 미국증시 보고서 만들어줘",
  "namoobi 시황 보고서" 등으로 요청할 때 트리거된다. 6개의 서브에이전트
  (뉴스/시장데이터/원자재/암호화폐/증권사/종합분석)를 병렬로 호출해 자료를 수집하고,
  종합 데이터를 JSON으로 정리한 뒤 DOCX 보고서를 생성하고, Claude in Chrome 가
  로그인된 Gmail 작성창에서 직접 메일을 작성·docx 첨부·발송한다
  (기본 수신자: namoobi@gmail.com, jaewoo.seo@mobis.com, hyun.jiyoun@gmail.com).
---

# Namoobi Market Report (v3.1)

> v3.1 (plugin 1.1.0) 변경점:
> - **글로벌 주요 이벤트 캘린더** 섹션 추가 (NewsAgent가 향후 2주 이벤트 수집)
> - **희토류(REMX ETF)** 를 금속 테이블에 추가 (단·중·장기 추세 전 컬럼)
> - **환율 단·중·장기 추세 테이블** 추가 (MarketsAgent가 KRW=X 등 수집) + 환율 섹션에 **달러인덱스(DXY)** 병기
> - 기본 수신자 3명으로 확대
>
> v3.0 = global-market-report v2.1 의 운영 학습을 전부 반영한 리빌드.
> - 서브에이전트 프롬프트·반환 스키마를 `references/agents.md` 에 **완전 수록**
> - Gmail 발송 절차·함정 회피를 `references/email-sending.md` 로 분리 (progressive disclosure)
> - MCP 도구명을 UUID 하드코딩 대신 **ToolSearch 키워드 탐색**으로 변경
> - build_report.js: 입력 데이터 사전 검증(--validate), null 안전 처리, Executive Summary

## 보고서 품질 기준 (반드시 충족)

생성되는 docx 는 다음 9개 항목을 모두 포함해야 한다. 하나라도 누락되면 재작업 대상.

1. **글로벌 Top News 10** — 헤드라인 + 2~4문장 요약 + 임팩트 라벨
2. **글로벌 주요 이벤트 캘린더** — 향후 2주 핵심 이벤트 (날짜·지역·이벤트·중요도·예상 영향)
3. **단·중·장기 추세** — 모든 자산을 1주/1개월/3개월/6개월/1년 변화율로 제시
4. **글로벌 증시 풀커버리지** — 한국(코스피·코스닥)·미국·홍콩·중국·일본·인도·베트남·유럽
5. **매크로 지표** — 달러지수(DXY), VIX, 美 10년 국채금리
6. **원자재 풀커버리지** — 에너지(WTI·천연가스) + 금속(금·은·구리·**희토류 REMX**) + 농산물(옥수수·대두·밀)
7. **주요 환율 추세** — USD/EUR/JPY/CNY/HKD vs KRW 단·중·장기 추세 + **달러인덱스(DXY)** 병기 + 원화 톤
8. **암호화폐** — 시장 개요 + 공포·탐욕 지수(현재/1일/1주/1개월) + 김치프리미엄(BTC/ETH/XRP/SOL)
9. **종합 분석 + 포트폴리오** — 매크로 톤·테마·리스크 + 공격형/중립형/안정형 3개 모델 + 액션 아이템

## 워크플로우 개요

```
[Phase 0: 사전 점검]  스크립트 경로 자동탐색 / node_modules / 오늘 날짜 / Chrome 연결
        ↓
[Phase 1: 병렬 수집 — 5개 서브에이전트를 단일 메시지로 동시 발행]
  ├─ NewsAgent / MarketsAgent / CommoditiesAgent / CryptoAgent / SecuritiesAgent
        ↓
[Phase 2: AnalysisAgent 단독 호출]  Phase 1 결과를 입력으로 종합·포트폴리오 도출
        ↓
[Phase 3: 데이터 종합 → JSON 저장 + 유효성 검증]
        ↓
[Phase 4: DOCX 생성]  node build_report.js <json> <out.docx>
        ↓
[Phase 5: 이메일 발송]  Claude in Chrome → 로그인된 Gmail 직접 발송 (references/email-sending.md)
        ↓
[Phase 6: 결과 보고]  핵심 헤드라인 3개 + 포트폴리오 톤 요약
```

## Phase 0: 사전 점검

1. **날짜**: `TZ=Asia/Seoul date '+%Y-%m-%d'` 로 오늘(KST) 확정. `YYYYMMDD` 압축형도 함께 만든다.
2. **Chrome**: `mcp__Claude_in_Chrome__list_connected_browsers` 로 연결 확인. **일반(normal) 브라우저 창**이 있어야 한다. 없으면 사용자에게 일반 크롬 창을 열어달라고 요청. (발송 직전이 아니라 지금 미리 확인해 두면 Phase 5 실패를 줄인다.)
3. **빌드 환경 준비** — 플러그인 마운트는 읽기 전용이므로 쓰기 가능한 outputs 에 복사해 빌드한다:

```bash
SRC="$(dirname "$(find /sessions/*/mnt -path '*namoobi-market-report/scripts/build_report.js' 2>/dev/null | head -1)")"
WORK="$(ls -d /sessions/*/mnt/outputs 2>/dev/null | head -1)/nmr_build"
rm -rf "$WORK"; mkdir -p "$WORK"
cp "$SRC/build_report.js" "$SRC/package.json" "$WORK/"
cd "$WORK"
[ -d "$WORK/node_modules/docx" ] || npm install docx --no-fund --no-audit
node -e "require('$WORK/node_modules/docx'); console.log('docx OK')"
```

> ⚠️ `/tmp` 는 이전 세션 잔존물로 권한 오류가 날 수 있으니 사용하지 말 것. 항상 outputs 하위에서 빌드.

## Phase 1–2: 서브에이전트 호출

상세 프롬프트와 각 에이전트의 반환 JSON 스키마는 **`references/agents.md`** 를 읽고 그대로 사용한다.

핵심 규칙:
- Phase 1의 5개 에이전트(News/Markets/Commodities/Crypto/Securities)는 **반드시 단일 메시지에서 동시 발행** (general-purpose 타입).
- AnalysisAgent 는 5개 결과를 모두 받은 뒤 **마지막에 단독 호출**.
- MCP 도구는 deferred 상태일 수 있으므로 각 에이전트 프롬프트에 "먼저 `ToolSearch` 키워드 검색(예: `+UsStockInfo historical`, `+CoinInfo fear greed`)으로 도구를 로드한 뒤 사용하라"고 명시한다. **UUID 가 포함된 도구명을 하드코딩하지 말 것** — 서버 ID는 세션마다 다를 수 있다.
- 실패한 데이터는 null / 빈 배열로 두고 진행한다. 빌더가 "-" 로 렌더링한다.

## Phase 3: 데이터 종합 및 저장

6개 에이전트 결과를 `references/data-schema.md` 의 통합 스키마로 합쳐
outputs 하위 `_market_report_data/report_data_YYYYMMDD.json` 으로 저장한다.

> ⚠️ Write/Edit 파일도구가 outputs 에 직접 못 쓰는 경우("outside connected folders")
> bash heredoc 으로 저장한다. 한글 JSON 은 단일 인용 heredoc(`<<'JSONEOF'`)으로 변수확장을 막을 것.

저장 후 반드시 검증:
```bash
cd "$WORK" && node build_report.js --validate <outputs>/_market_report_data/report_data_YYYYMMDD.json
```
누락 섹션이 보고되면 해당 에이전트를 재실행하거나 null 처리 사유를 확인한 뒤 진행.

## Phase 4: DOCX 생성

```bash
cd "$WORK"
node build_report.js \
  <outputs>/_market_report_data/report_data_YYYYMMDD.json \
  <outputs>/글로벌금융시장_종합시황보고서_YYYYMMDD.docx
```
빌드 후 파일 크기와 `unzip -l` 무결성, 표 개수(`<w:tbl>`)를 점검한다.
docx 는 반드시 **연결된 폴더 또는 outputs 최상위**에 있어야 Chrome file_upload 첨부가 가능하다.

## Phase 5: 이메일 발송

**`references/email-sending.md` 를 읽고 절차를 그대로 따른다.** 요점:
- SMTP·Gmail MCP 초안 방식 금지. **Claude in Chrome 로그인된 Gmail 직접 발송만** 사용.
- 기본 수신자: `namoobi@gmail.com`, `jaewoo.seo@mobis.com`, `hyun.jiyoun@gmail.com` (사용자 지정 시 대체)
- 사용자가 자동발송을 승인한 세션에서는 추가 확인 없이 발송. 단, 로그인(비밀번호 입력)은 정책상 대신 수행 불가.
- 수신자 칩 클릭 금지, 검증은 screenshot/zoom 으로만 — 상세 함정 목록은 reference 참조.

## Phase 6: 결과 보고

```
📋 글로벌 시황 보고서 발송 완료
생성: 글로벌금융시장_종합시황보고서_YYYYMMDD.docx (NN KB)
수신: <recipients>
수집: 뉴스 N / 증시 N / 원자재 N / 코인 N / 증권사 N
[핵심 헤드라인 3개]
1~3. (top_news 상위 3개)
[추천 포트폴리오 톤]
- 공격형/중립형/안정형 1줄씩
```

## 트러블슈팅 (요약)

| 증상 | 대처 |
|------|------|
| Chrome "Tabs can only be moved to and from normal windows" | 일반 크롬 창 없음 → 사용자에게 열어달라 요청 후 `tabs_context_mcp(createIfEmpty=true)` 재시도 |
| Gmail 로그인 안 됨 | 비밀번호 대리 입력 불가 → 사용자가 직접 로그인 후 재시도 |
| 작성창이 닫히고 초안만 남음 | `#drafts` 에서 초안 다시 열어 이어서 작성·발송 (email-sending.md) |
| Write/Edit "outside connected folders" | bash heredoc 으로 저장 |
| npm/cp 권한 오류 | /tmp 금지, outputs/nmr_build 에서 빌드 |
| Chrome 차단 도메인(naver.com 등) | NaverSearch MCP / web_fetch 로 대체 |
| VNINDEX 데이터 부재 | VNM ETF (VanEck Vietnam) 로 대체 |
| 선물 티커 실패(PL=F 등) | current:null → 빌더가 "-" 렌더 |
| CoinInfo gainers/losers 간헐 오류 | null/빈배열로 두고 진행 |
| 한글 폰트 깨짐 | 시스템에 맑은 고딕 설치 확인 |

## 부록 A: 5대 증권사 강점 사전 정의

| 증권사 | 핵심 강점 | 대표 채널 | 추천 투자자 |
|--------|-----------|-----------|-------------|
| 신한투자증권 | 자산배분 통합 (주식·채권·원자재·대안), 매크로 일관성 | 카카오채널 '쏠쏠한 리포트', 신한 알파 앱 | 장기 자산배분형 |
| 미래에셋증권 | 12개국 현지법인, ETF 특화, 신흥국(베트남·인도·인니) | m.Global 앱, 디지털리서치 숏폼 | 해외주식·ETF·신흥국 |
| 삼성증권 | SGR 독립 싱크탱크, 파생·선