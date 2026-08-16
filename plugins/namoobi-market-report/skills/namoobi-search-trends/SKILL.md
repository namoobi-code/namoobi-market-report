---
name: namoobi-search-trends
description: |
  주 1회(월요일) 트렌드 주간 LLM 리포트를 생성해 AI 터미널 홈피 Trends 탭에 게시하는
  워크플로우. 웹 리서치로 ① 인스타 주간 큐레이션(KR·글로벌) ② 구글 주간 해설(KR·US)
  ③ 유튜브 주간 해설(KR·US) ④ 네이버 쇼핑 5년 장기 해석 ⑤ 시즌·연간 리포트 발표
  체크를 수행하고 trends_weekly_llm.json 을 만들어 서버에 업로드한다.
  사용자가 "트렌드 리포트", "주간 트렌드", "인스타 트렌드 갱신", "search trends 실행",
  "/namoobi-search-trends" 등으로 요청하거나 예약 실행 시 이 스킬을 사용한다.
  ※ 일간 트렌드(구글 RSS·유튜브 API·네이버 쇼핑 랭킹)는 서버 cron(trends_collect.py,
  매일 05:50)이 무토큰으로 처리하므로 이 스킬의 대상이 아니다.
---

# namoobi-search-trends (v1.1)

## 모델 지정 (필수)

이 스킬의 실제 수행은 반드시 Agent 툴로 서브에이전트를 1개 생성해 전부 위임한다 —
`subagent_type: "general-purpose"`, `model: "sonnet"` (Claude Sonnet 5).
아래 워크플로우 전문(Phase 0~4)을 서브에이전트 프롬프트로 그대로 전달하고,
오케스트레이터는 직접 리서치·JSON 생성·업로드를 하지 말고 서브에이전트의 최종 보고만 요약한다.
(예약 실행·수동 실행 공통. 배포 키는 /tmp 권한 충돌 가능 → $HOME/nmr_deploy_key 로 복사해 사용)

'트렌드 조사 및 자동화 검토' 보고서(2026-08-06)의 하이브리드 설계 중 **LLM 담당분**:
무토큰 자동화가 불가한 인스타그램 + 해설·해석이 필요한 주간/장기 요약만 주 1회 LLM이 수행한다.

## 산출물

`data/db/trends_weekly_llm.json` 1개 — 홈피 Trends 탭의 "🤖 주간 LLM 리포트" 섹션이 이 파일을 렌더한다.
**스키마는 프론트(app.js)가 파싱하므로 절대 바꾸지 말 것** (필드 추가는 가능, 삭제·개명 금지):

```json
{
  "asof": "YYYY-MM-DD", "week": "YYYY년 M월 N주", "note": "...",
  "kr":     {"title": "🇰🇷 인스타 주간 트렌드 (한국)",   "items": [["제목","한줄 해설","링크URL"], ...최대10개]},
  "global": {"title": "🌎 인스타 주간 트렌드 (글로벌)",   "items": [[..., ..., ...], ...최대10개]},
  "google_wk":  {"title": "🔍 구글 주간 해설",
    "kr": {"head": "이번 주 한 줄 총평", "items": [["키워드(검색량)","왜 떴나 해설"], ...최대10개]},
    "us": {"head": "...", "items": [...최대10개]}},
  "youtube_wk": {"title": "▶️ 유튜브 주간 해설", "kr": {...}, "us": {...}},
  "naver_long": {"title": "🛒 네이버 쇼핑 장기 해석 (5년 클릭 추이)", "head": "...", "items": [...최대10개]},
  "season_check": {"checked": "YYYY-MM-DD", "found": "신규 없음 — ... / 또는 발견 내용"},
  "sources": [["출처명","URL"], ...]
}
```

**항목 수 원칙(v1.1)**: 각 섹션(인스타 KR·글로벌, 구글 KR·US, 유튜브 KR·US, 네이버 장기)은 **가능한 한 10개까지** 채운다.
서버 실데이터(구글·유튜브 랭킹은 상위 10위까지, 네이버는 11개 분야 전부)를 근거로 우선 채우고,
리서치로 확인 가능한 만큼 인스타·해설 항목을 확장한다. 단, **지어낸 항목으로 10개를 억지로 채우지 않는다** —
근거 있는 항목만 쓰고 부족하면 6~9개도 허용(품질 > 개수).

## 워크플로우

### Phase 0 — 서버 데이터 로드 (해설의 재료 — 지어내기 금지)

서버가 이미 수집한 실데이터를 먼저 읽는다:

```bash
curl -sk https://161.33.190.254/api/db/trends
```

- `weekly.g_kr / g_us` — 최근 7일 구글 급상승 등장일수 랭킹 (구글 주간 해설의 뼈대)
- `weekly.y_kr / y_us` + `y_kr / y_us`(오늘 일간) — 유튜브 주간 해설의 뼈대
- `nv_trend` — 네이버 쇼핑 11분야 5년 월간 클릭 추이. 해석 시 계산 팩트(최근 12M 평균 vs 3년 전,
  피크 월, 하락률)를 파이썬으로 직접 산출해 근거로 쓸 것.
  ※ 알려진 구조 팩트: 전 분야가 2023.02 피크 후 하락 = 네이버쇼핑 트래픽 자체 축소(플랫폼 요인)
  → 절대값이 아니라 **분야 간 상대 비교**가 정보라고 해석하는 것이 정확하다.

### Phase 1 — 웹 리서치 (WebSearch 6~10콜 — 항목 10개 채우려면 소스당 콜 수 확대)

1. 인스타 KR: `인스타그램 릴스 밈 트렌드 <이번달> 챌린지 유행` + 위픽/HSAD 밈 리포트 —
   HSAD 이달의 밈집 전체 항목 + 위픽 아카이브 + 최신 밈 뉴스를 모아 최대 10개 확보
2. 인스타 글로벌: `Instagram trends this week <month year> reels trending audio formats`
   (Lightreel·Newengen·HeyOrca·SocialPilot·Metricool 등 복수 소스를 조합해 최대 10개 확보 —
   한 리포트에서 6~7개, 나머지는 다른 소스에서 보강)
3. 구글·유튜브 주간 해설: 서버 랭킹(g_kr/g_us/y_kr/y_us)은 최대 10위까지 모두 사용 —
   맥락 불명인 키워드는 뉴스 검색으로 배경 확인 후 해설 작성
4. 시즌·연간 발표 체크: `Google Year in Search <올해>` / `Google Trends 시즌 리포트` /
   `YouTube Culture & Trends <올해>` — **새 리포트 발견 시** trends_annual.json 카드도 갱신
   (연간 카드 스키마: {icon,title,src,url,items[]} — 기존 파일 참조)

### Phase 2 — JSON 작성 원칙

- 인스타 항목엔 반드시 **바로가기 링크**: KR 밈 = 인스타 해시태그
  (`https://www.instagram.com/explore/tags/<URL인코딩>/`), 글로벌 = 리포트 원문 URL
- 해설은 투자 관점 연결을 우선(예: 지원금 검색 급등 → 유통·편의점 소비주 신호)
- 서버 데이터에 없는 수치는 쓰지 않는다. 리서치 출처의 수치는 출처 병기.
- 구글·유튜브 해설 head는 "이번 주를 한 줄로" — 나열이 아니라 관통하는 흐름을 뽑는다.

### Phase 3 — 업로드·검증

```bash
# 키 준비 (없으면): cp <연결폴더>/SECURITY/nmr_deploy_key /tmp/ && chmod 600 /tmp/nmr_deploy_key
scp -i /tmp/nmr_deploy_key -o StrictHostKeyChecking=no trends_weekly_llm.json \
    ubuntu@161.33.190.254:namoobi/data/db/
curl -sk https://161.33.190.254/api/db/trends_weekly_llm | head -c 200   # 서빙 확인
```

로컬 저장소(namoobi-market-report-server/data/db/)에도 같은 파일을 저장해 이력을 남긴다.
연간 카드를 갱신한 경우 trends_annual.json 도 동일하게 업로드.

### Phase 4 — 결과 보고

주간 하이라이트 3줄(인스타 1·구글 1·특이사항 1) + 시즌·연간 체크 결과 + 홈피 링크로 마무리.
