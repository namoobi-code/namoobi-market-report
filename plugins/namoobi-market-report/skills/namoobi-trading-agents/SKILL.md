---
name: namoobi-trading-agents
description: |
  서버가 매일 06시(KST)에 자동 생성한 종목 스크리닝 후보(ta_stage3 번들)로
  Bull/Bear 에이전트 토론(3단계)과 리스크 심사(4단계)를 수행해 최종 채택 종목을
  판정·기록하는 워크플로우. 사용자가 "트레이딩 에이전트", "종목 토론",
  "오늘 후보 토론 돌려줘", "trading agents 실행", "매수 후보 심사",
  "스크리닝 판정해줘", "종목 스크리닝 토론", "/namoobi-trading-agents" 등으로
  요청하면 반드시 이 스킬을 사용한다. 스크리닝 후보의 채택/탈락 판정, 종목 토론,
  리스크 심사와 관련된 요청이면 스킬명을 명시하지 않아도 트리거한다.
---

# namoobi-trading-agents (v1.0)

TauricResearch/TradingAgents의 멀티 에이전트 토론 구조를 번안한 종목 판정 워크플로우.
서버(무-LLM)가 1~3단계(유니버스→정량필터→번들)를 매일 자동 실행해 두고,
이 스킬은 LLM이 필요한 **3단계-C(토론)와 4단계(리스크 심사)만** 수행한다.

핵심 원칙 (원본 소스 분석에서 검증된 것):
- **사전 수집 → 주입**: 토론 에이전트는 도구를 쓰지 않는다. 데이터는 서버 번들에 이미 있다.
  툴 압박에 의한 지어내기(TradingAgents issue #557)를 원천 차단하는 설계다.
- **결측은 결측으로**: 번들에 없는 수치는 "자료 없음"으로 쓰게 한다. 지어내기 금지.
- **차별화 강제**: "전부 채택 금지" — 판정이 갈려야 토론의 의미가 있다.
- **기록 우선**: 판정은 반드시 서버 DB에 스냅샷으로 남긴다(5단계 성과추적의 원료).
  탈락 종목도 기록한다 — 생존편향 방지.

## 워크플로우

```
[Phase 0] 번들 다운로드·신선도 확인 (scripts/fetch_bundles.py)
[Phase 1] 토론 — 서브에이전트 4개 병렬 (그룹당 5종목, model: sonnet)
[Phase 2] 리스크 심사 — 메인 세션이 채택·관망 종목 대상 포트폴리오 관점 심사
[Phase 3] 산출 — 보고서 md + ta_verdict.json (scripts/save_verdict.py) → 연결폴더 저장 + 서버 업로드
[Phase 4] 결과 보고 — 최종 승인 종목 + 판정 분포 요약
```

## Phase 0 — 준비

작업 폴더를 만들고 번들을 내려받는다:

```bash
# 작업 폴더는 회차별로 분리한다 — 옛 회차의 grp_*/verdict_* 가 남아 섞이는 사고를 막는다
WORK="$(ls -d /sessions/*/mnt/outputs 2>/dev/null | head -1)/nta_$(date +%y%m%d_%H%M)"
mkdir -p "$WORK"
SKILL_DIR="$(dirname "$(find /sessions/*/mnt -path '*namoobi-trading-agents/scripts/fetch_bundles.py' 2>/dev/null | head -1)")/.."
python3 "$SKILL_DIR/scripts/fetch_bundles.py" "$WORK"
```

⚠️ **`trade_date` 는 가격 날짜가 아니다** — KRX 기본정보 API 가 1영업일 지연되므로 `trade_date`(예 20260710)와
실제 가격일(`price_date`, 예 2026-07-13)이 다르다. **성과추적·기준가는 반드시 `price_date` 를 쓴다.**
번들이 오늘 재생성됐는지는 `trade_date` 가 아니라 `as_of`·`price_date` 로 판단하라.

fetch_bundles.py는 서버(`http://141.147.160.13/api/db/`)에서 ta_stage3(번들)·ta_stage2(랭킹 컨텍스트)를
내려받아 `$WORK/grp_KR1.json`·`grp_KR2.json`·`grp_US1.json`·`grp_US2.json`(그룹당 5종목)으로 분할하고
기준 거래일을 stdout에 출력한다.

**대기 게이트 (서버 생성 중 보호)**: 스크립트 첫 토큰이 `RUNNING`이면 서버가 지금 스크리닝을 생성하는 중이다
(새벽 6시 전후 실행 시 흔함). **잘못된 데이터를 쓰지 않도록 스크립트가 다운로드 자체를 거부한다.**
이때는 완료까지 폴링 대기하라: `sleep 40` 후 재실행을 반복(약 60초 간격, 최대 30회 ≈ 20분).
매 5회마다 사용자에게 진행 상황을 한 줄 알리고, 30회 후에도 `RUNNING`이면 중단하고 사용자에게 알린다.
`PIPELINE_FAILED`(서버 파이프라인 실패)나 `INCONSISTENT`(stage2/stage3 거래일 불일치 — 부분 실행 잔재)가
나오면 대기하지 말고 즉시 사용자에게 알리고 중단한다.

**실시간 급변 게이트 (ALERT)**: 번들은 서버가 새벽 6시에 만든 확정 일봉 기준이라 당일 장중 급등락을 모른다.
그래서 fetch_bundles.py가 후보 20종목의 **현재가를 실시간 대조**(KR=네이버, US=야후)해 각 번들에
`실시간체크`(현재가·번들종가·번들대비 괴리·당일등락률)를 주입하고, 괴리 ±5% 이상이면 `ALERT`를 붙인 뒤
마지막 줄에 `ALERTS [...]`로 요약한다. ALERT 종목 규칙:
- 토론(Phase 1)에서 해당 종목은 급변 사실과 원인(뉴스 헤드라인으로 설명 가능한지)을 반드시 다룬다.
- **원인 불명의 급락은 채택 금지(최대 관망)** — "싸졌다"는 Bull 논거로 쓰지 마라.
- 리스크 심사(Phase 2)에서 ALERT 종목을 승인하려면 사유에 급변 원인과 그 유효성 판단을 명시해야 한다.
- 실시간 조회 실패(`오류` 필드) 종목은 확정 일봉 기준으로 판단하되 확신도를 낮춘다.

**완료 flag 게이트**: 출력 마지막 토큰은 서버 파이프라인(3B) 완료 flag다 — 서버가 stage3까지 성공하면
최상위 폴더에 `screening_completed_YYMMDD_HHMM.txt`를 남기고 같은 내용을 `/api/db/ta_flag`로 서빙한다.
`FLAG_MISSING`(flag 자체가 없음)이거나 `MISMATCH`(flag의 거래일과 번들 거래일 불일치), 또는 completed
시각이 실행일 06시 이전이면 서버 cron이 오늘 완주하지 못한 것이다 — STALE과 동일하게 사용자에게 확인받아라.

**신선도 게이트**: 스크립트가 `STALE`(기준 거래일이 5일 초과 과거)을 출력하면 그대로 진행하지 말고
사용자에게 "서버 데이터가 오래됐다(기준일 표시). 그대로 진행할까, 중단할까"를 물어라.
서버 cron(06:00 KST)이 실패했을 가능성이 높다.

**서버 접속 실패 시**: 비차단으로 넘기지 말고 사용자에게 알리고 중단한다 — 이 스킬은 번들 없이는 의미가 없다.

## Phase 1 — 토론 (서브에이전트 4개, 단일 메시지로 병렬 발행)

그룹 파일(grp_KR1/KR2/US1/US2) 각각에 대해 서브에이전트(model: sonnet)를 **한 메시지에 4개 모두** 발행한다.
프롬프트 템플릿은 `references/debate-prompt.md`를 읽고 그대로 사용한다(그룹 파일 경로·저장 경로·
시장 유의사항만 치환). 각 에이전트는 `$WORK/verdict_<그룹>.json`을 저장한다.

핵심 규칙(템플릿에 포함 — 임의로 빼지 말 것):
- 번들 데이터만 근거로, 구체 수치 인용 의무. 번들에 없으면 "자료 없음".
- 4분석가(기본·기술·심리·뉴스) 의견 → Bull 논거 3 → Bear 조목 반박 → 판정.
- 판정 = 채택/관망/탈락 + 확신도 1~10. **그룹 내 전부 채택 금지.**
- RSI 30~40대(조정권)와 1개월 음수 수익률은 Bear가 반드시 지적.

서브에이전트를 쓸 수 없는 환경이면 같은 템플릿으로 그룹별 인라인 처리해도 된다(품질 동일, 시간만 증가).

## Phase 2 — 리스크 심사 (메인 세션 인라인)

4개 verdict 파일을 읽고, **채택 전부 + 확신도 7 이상 관망** 종목을 심사 대상으로 올린다.
포트폴리오 매니저 관점으로 아래 4개 항목을 심사해 `$WORK/risk_review.json`에 저장한다:

1. **밸류체인 중복**: 사실상 같은 베팅인 종목 쌍(예: SK하이닉스와 SK스퀘어 — 사업회사·지주)은
   확신도 높은 쪽만 승인, 나머지는 "중복 반려".
2. **섹터 집중**: 같은 섹터 승인은 시장별 최대 2종목. 초과분은 확신도 순으로 반려하고 사유 명시.
3. **변동성 사이징**: 번들 ATR% 기준 비중 가이드 — 2% 이하 "표준", 2~4% "축소", 4% 초과 "최소 또는 반려".
4. **손절선·무효화 조건 (승인 종목 필수)**: 승인하는 모든 종목에
   - `손절선` = 기준가(실시간체크의 현재가, 없으면 번들종가) × (1 − 1.5 × ATR%/100) — 원 단위/달러 반올림.
   - `무효화` = 판정을 무효로 만드는 조건 한 줄 (예: "종가 기준 손절선 이탈", "다음 실적에서 HBM 가이던스 하향",
     "급락 원인 뉴스가 구조적 악재로 확인될 때"). 손절선은 기계적 하한, 무효화는 논리적 하한 — 둘 다 쓴다.
   판정은 "누구를"까지만 답하므로, 이 두 필드가 "언제 나올지"의 최소 안전장치다.
5. **최종 판정**: 종목별 승인/반려 + 한 줄 사유. 승인 0종목이어도 된다 — 억지로 승인하지 말 것.

risk_review.json 스키마:
```json
{"심사대상":[{"종목":"...","시장":"KR|US","토론판정":"채택","확신도":7,
  "승인":true,"사유":"...","비중가이드":"표준|축소|최소",
  "손절선":1700000,"무효화":"종가 기준 손절선 이탈 또는 ..."}],
 "총평":"섹터 분포·시장 국면 관점 2~3문장"}
```

## Phase 3 — 산출·기록

```bash
python3 "$SKILL_DIR/scripts/save_verdict.py" "$WORK"
```

save_verdict.py가 verdict_*.json + risk_review.json을 병합해
`$WORK/ta_verdict.json`(서버 업로드용: 판정 전체 + 승인 리스트 + 기준가 스냅샷)과
`$WORK/트레이딩에이전트_판정_YYYYMMDD.md`(보고서)를 생성한다. 이후:

1. 보고서 md를 **연결 폴더 `D:\claudeCowork` 에 복사**하고 present_files 로 제시한다.
   ⚠️ **폴더 선택 다이얼로그를 띄우지 말 것** — `request_cowork_directory` 를 호출하지 않는다.
   이 스킬의 산출물 저장 위치는 **항상 `D:\claudeCowork`** 로 고정이며, 샌드박스 경로는
   `/sessions/*/mnt/claudeCowork` 로 이미 마운트돼 있으므로 별도 권한 요청이 필요 없다:

   ```bash
   CW=$(ls -d /sessions/*/mnt/claudeCowork | head -1)
   cp "$WORK"/트레이딩에이전트_판정_*.md "$CW"/
   ```
   present_files 에는 위 `$CW` 경로의 파일을 넘긴다(연결 폴더 안이므로 선택 창이 뜨지 않는다).
   만약 `claudeCowork` 마운트가 없으면 그때만 사용자에게 알리고 중단한다 — 임의 폴더를 요청하지 않는다.
2. **서버 업로드** — 연결폴더 `SECURITY/ssh-key-2026-07-11.key` 존재 시(없으면 스킵하고 Phase 4에 명시):

```bash
cp /sessions/*/mnt/claudeCowork/SECURITY/ssh-key-2026-07-11.key /tmp/nta.key && chmod 600 /tmp/nta.key
scp -i /tmp/nta.key -o StrictHostKeyChecking=no "$WORK/ta_verdict.json" ubuntu@141.147.160.13:/home/ubuntu/namoobi/data/db/ta_verdict.json
ssh -i /tmp/nta.key ubuntu@141.147.160.13 "cd /home/ubuntu/namoobi && python3 - <<'PY'
import json,os
p='data/db/ta_calls.json'
hist=json.load(open(p)) if os.path.exists(p) else {'calls':[]}
v=json.load(open('data/db/ta_verdict.json'))
hist['calls']=[c for c in hist['calls'] if c.get('trade_date')!=v.get('trade_date')]+[v]
hist['as_of']=v.get('as_of','')
json.dump(hist,open(p,'w'),ensure_ascii=False)
print('ta_calls:',len(hist['calls']),'runs')
PY"
```

(ta_calls.json은 5단계 성과추적용 누적 이력 — 같은 거래일 재실행은 교체, 과거 이력은 보존.)

## Phase 4 — 결과 보고

요약만 간결하게: 기준 거래일 / 판정 분포(채택·관망·탈락 수) / 리스크 심사 결과(승인 종목 + 비중 가이드,
반려 사유) / 서버 업로드 여부. 마지막에 반드시:
**"투자 자문이 아니며 판정은 참고용. 매매 판단과 책임은 사용자에게 있다."**

## 참고

- `references/debate-prompt.md` — Phase 1 토론 프롬프트 템플릿 (수정 없이 치환만)
- 서버 파이프라인(1~3단계 수집): `/home/ubuntu/namoobi/scripts/ta_screen.py`, cron 06:00 KST
- 대시보드: http://141.147.160.13/ → TradingAgents 탭 (0~5 Step 버튼)
