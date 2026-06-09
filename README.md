# namoobi-market-report (Claude Cowork / Claude Code 마켓플레이스)

글로벌 금융시장 종합 시황 보고서를 자동 생성·발송하는 플러그인 마켓플레이스.
`global-market-report` v0.3.0(SKILL v2.1)의 운영 학습을 전부 반영해 리빌드한 플러그인을 포함한다.

- 로컬 유지관리: `D:\claudeCowork\namoobi-market-report`
- 원격 저장소: https://github.com/namoobi-code/namoobi-market-report

## v3 주요 개선점 (구 global-market-report 대비)

1. **서브에이전트 프롬프트 완전 수록** — 구버전은 "기존 v2와 동일" 참조만 있고 실제 내용이 없었음 → `references/agents.md` 에 7개 에이전트 프롬프트·티커맵·반환 스키마 완비
2. **Progressive disclosure** — SKILL.md 는 오케스트레이터만, Gmail 발송 함정·절차는 `references/email-sending.md` 로 분리
3. **MCP 도구 탐색 견고화** — UUID 하드코딩 제거, ToolSearch 키워드 검색 방식
4. **build_report.js v3** — `--validate` 모드(품질기준 사전 검증), null 안전 처리, Executive Summary 섹션, 포트폴리오 비중 합계 검증, 표 개수 출력
5. **sample_data.json 픽스처** — 데이터 수집 없이 빌더 단독 테스트 가능
6. **SMTP 잔재 제거** — send_report.py / 네이버 앱 비밀번호 설정 삭제 (샌드박스에서 동작하지 않아 혼란만 유발)
7. **v1.1**: 이벤트 캘린더 + 희토류(REMX) + 환율·DXY 단·중·장기 추세 / **v1.2**: 글로벌 IB 5사 리서치 (UBS·GS·JPM·MS·BlackRock)
8. **v1.2.4**: 샌드박스 마운트 잘림 **자가복구**(`build_report.js.b64` 동봉, Phase 0 자동 복원) + **실행 시작/완료/소요시간 보고** + **D:\claudeCowork 작업폴더 자동 연결 요청**. ⚠️ 잘림의 원인은 호스트 파일이 아니라 마운트 host→VM 동기화 — 파일 복사·.plugin 패키징 후 반드시 크기·EOF 마커 검증.
9. **v1.2.5**: 수신자 정책 — 받는사람(To)은 namoobi@gmail.com 단독, 그 외 수신자는 저장소 밖 `D:\claudeCowork\SECURITY\메일수신자.txt` 에서 읽어 **숨은참조(BCC)** 로 발송. 주소는 비공개로 다루며 SECURITY 폴더는 절대 커밋하지 않는다.
10. **v1.2.6**: `build_report.js.b64` 동봉 제거 — 비표준 백업 파일이 Cowork 플러그인 설치 검증을 막아 삭제. 잘림 복구는 Phase 0 의 git 원본 재복사로 대체.
11. **v1.2.7**: BCC 수신자 **주석 처리** — `메일수신자.txt` 에서 라인 맨 앞(공백 허용)이 `//` 인 줄은 발송 대상에서 제외(주소 보존). 읽기 시 `grep -vE '^[[:space:]]*//'` 로 주석 라인을 거른 뒤 이메일 추출. 유효 주소 0개면 To 만 발송.

## 구조

```
namoobi-market-report/
├── .claude-plugin/
│   └── marketplace.json                  # 마켓플레이스 정의
└── plugins/
    └── namoobi-market-report/
        ├── .claude-plugin/plugin.json    # version 으로 업데이트 판단 (semver)
        ├── README.md
        └── skills/namoobi-market-report/
            ├── SKILL.md                  # 오케스트레이터 (v3.2.7)
            ├── scripts/
            │   ├── build_report.js       # JSON → DOCX (--validate 지원)
            │   ├── sample_data.json      # 테스트 픽스처
            │   └── package.json
            └── references/
                ├── agents.md             # 7개 서브에이전트 프롬프트·스키마
                ├── data-schema.md        # 통합 JSON 스키마
                └── email-sending.md      # Chrome Gmail 발송 절차·함정
```

## 등록 + 설치

**Cowork (데스크톱 앱)** — `/plugin` 명령 없음, UI 사용:
1. Cowork 탭 → 사이드바 **Customize** → **Plugins** 탭
2. **Personal plugins** 섹션 → **"+"** → **Add marketplace**
3. **Add from a repository** → `namoobi-code/namoobi-market-report` 입력
4. 목록에서 **namoobi-market-report** → **Install**

**Claude Code (CLI)**:
```
/plugin marketplace add namoobi-code/namoobi-market-report
/plugin install namoobi-market-report@namoobi-market-report
```

## 유지관리 루틴 (수정 → 커밋 → 푸시 → 업데이트)

```bash
# (1) SKILL.md / scripts / references 수정
# (2) plugin.json + marketplace.json 의 version 을 함께 올린다  예: 1.2.6 → 1.2.7   ← 업데이트 트리거 (필수!)
# (3) (잘림 주의) 커밋 전 git status/diff 를 네이티브 터미널에서 확인 — 샌드박스 bash 는 호스트 파일을 잘라 읽을 수 있음
git add . && git commit -m "fix: ..." && git push
```
이후 Cowork 는 Plugins 메뉴에서 마켓플레이스 갱신, Claude Code 는 `/plugin marketplace update`

## 빌더 단독 테스트

```bash
cd plugins/namoobi-market-report/skills/namoobi-market-report/scripts
npm install docx
node build_report.js --validate sample_data.json   # 데이터 검증
node build_report.js sample_data.json out.docx     # 샘플 docx 생성
```

## 메모

- `version` 을 안 올리면 업데이트로 인식되지 않는다 — 변경 시 항상 semver 로 올릴 것
- `node_modules`, 생성된 `*.docx`, `_market_report_data/`, `nmr_build/` 는 .gitignore 로 제외
- 기존 `namoobi-plugins`(global-market-report v0.3.0)는 별도 저장소로 그대로 두고, 이 저장소가 후속 버전
- **샌드박스(bash) 에서 이 저장소 파일을 읽을 때 잘려 보일 수 있다** — 호스트 원본은 정상이며, Read 도구(호스트 직접 읽기)가 신뢰 기준. 패키징·복사 작업은 반드시 검증 동반.
