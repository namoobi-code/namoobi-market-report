# 이메일 발송 가이드 — Claude in Chrome 직접 발송 (v3.68)

> **★ v3.68 표준 경로 = "초안 경유 발송" (2026-07-17/18 3회 실측으로 확정 — 전면 작성창 직발송 금지)**
> 전면 작성창(`?view=cm&fs=1&…` 또는 #inbox?compose=new)은 ① 보내기 클릭이 조용히 무시되고(3회 중 3회 — 특히 첨부 업로드 직후) ② 첨부 대기 중 렌더러가 45초+ 프리즈되는 재발성 결함이 있다. 발송 소요가 8~12분까지 늘어난 원인. 아래 순서가 표준:
> 1. **prefill URL 로 초안 생성만**: `?view=cm&fs=1&to=…&bcc=…&su=…` navigate → 본문 DOM 주입(createElement/createTextNode — innerHTML 은 TrustedHTML 차단) → **보내기 누르지 말고** `#drafts` 로 이동(자동 초안 저장).
> 2. **초안 목록에서 해당 제목 행 클릭** → 하단 미니 작성창이 열리면 **제목 바 클릭으로 펼침**(최소화 40px 바 함정).
> 3. **첨부는 이 미니 작성창에서**: `find("file input")` ref → `file_upload`(연결 폴더 Windows 경로) → **업로드 완료 폴링**: `[role="progressbar"]` 소멸 + "첨부파일을 추가했습니다" 텍스트 확인(6MB급 ~30초). ⚠️ 본문 % 문구("-6.37%)") 가 진행률로 오탐되므로 % 매칭으로 판정 금지.
> 4. **본문 유실 점검**: 초안 재열기 시 본문이 비어 있으면(전면창 프리즈로 저장 유실) DOM 주입으로 재작성. `innerHTML=''` 대신 `while(firstChild) removeChild`.
> 5. **보내기 클릭 → "메시지 전송됨" 토스트 확인**(미니 작성창의 보내기는 신뢰됨). 토스트 미확인이면 `#sent` 최상단에서 제목 실측 — **보낸편지함에 없으면 미발송**이다(전면창 클릭 무시 사례).
> 6. **렌더러 프리즈(스크린샷/JS 타임아웃) 발생 시**: 즉시 해당 탭 `tabs_close_mcp` → 새 탭 → #drafts 재개. 대기 반복은 시간만 소모(실측 6분 낭비).

> v3.6.1: Gmail 이 안 켜져 있어도 Claude in Chrome 으로 `https://mail.google.com/mail/u/0/?ogbl#inbox` 로 navigate 하면 바로 받은편지함이 열린다 (로그인 상시 유지 — 비밀번호 단계 불필요). 발송 전제 #2·발송 절차 #2 참조.

> ⚠️ SMTP 는 샌드박스 네트워크 차단으로 동작하지 않는다. 사용 금지.
> Gmail MCP 초안 방식도 첨부 미지원 + 계정 불일치로 부적합.
> **아래 Chrome 직접 발송만 사용한다.**

## 수신자 정책 (v3.4.3 — 실행 모드별 수신자 파일 분기)

- **받는사람(To)**: `namoobi@gmail.com` **단 한 명만**. (사용자가 다른 To 를 지정하면 대체)
- **숨은참조(BCC)**: 실행 모드에 따라 **수신자 목록 파일이 달라진다** (Phase 0 에서 확정한 `$NMR_MODE` 사용):
  - **예약(scheduled) 실행** → `D:\claudeCowork\SECURITY\예약메일수신자.txt`
  - **일반(normal/direct) 실행** → `D:\claudeCowork\SECURITY\메일수신자.txt`
  - 모드 판정: 스킬 인자(ARGUMENTS)에 `scheduled`/`schedule`/`예약` 이 있거나, 예약 작업 프롬프트가 예약 실행임을 명시하면 **예약 모드**. 그 외에는 **일반 모드**. (상세는 SKILL.md Phase 0 참조)
  - **주석 처리 규칙**: 두 파일 모두, 라인 맨 앞(공백 허용)이 `//` 로 시작하면 그 줄의 수신자는 **발송 대상에서 제외**한다 (주소를 지우지 않고 `//` 만 붙여 일시 제외).
  - bash 로 읽기 (`//` 주석 라인 제외 후 이메일 추출) — 모드에 맞는 파일을 지정:
    - 예약: `grep -vE '^[[:space:]]*//' /sessions/*/mnt/claudeCowork/SECURITY/예약메일수신자.txt | grep -oE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'`
    - 일반: `grep -vE '^[[:space:]]*//' /sessions/*/mnt/claudeCowork/SECURITY/메일수신자.txt | grep -oE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'`
  - 해당 파일이 없거나, 비어 있거나, **유효 주소가 0개(전부 `//` 주석)** 이면 BCC 없이 To(namoobi) 에게만 발송하고, 그 사실을 결과 보고에 명시한다.
  - **이 주소들은 비공개 정보다 — 채팅·로그·보고서·커밋에 평문으로 노출하지 말 것.** BCC 인원 수만 보고한다 (예: "BCC 2명").
  - SECURITY 폴더와 그 내용은 절대 git 에 커밋하지 않는다 (저장소 밖 경로이며 .gitignore 로도 차단).

## 발송 전제 조건

1. Claude in Chrome 확장 연결 + **일반(normal) 브라우저 창** 존재
   (`mcp__Claude_in_Chrome__list_connected_browsers` 로 확인)
   - **(v3.53) 미연결(`[]`)이면 직접 실행 루틴** (사용자에게 떠넘기지 말 것):
     ① `mcp__computer-use__request_access(apps=["Google Chrome"], reason="크롬 실행해 Claude 확장 연결·시황 보고서 Gmail 발송")` — 브라우저는 tier "read" 라 "It is rare for this to be required…" 경고가 나오면 **같은 턴에서 즉시 한 번 더** `request_access` 호출(권한창은 재시도가 띄움). read 권한은 `open_application` 으로 크롬을 띄우는 용도이고 웹 조작은 전부 확장으로 한다.
     ② `mcp__computer-use__open_application(app="Google Chrome")` → `mcp__computer-use__wait(3)` → `list_connected_browsers` 재확인.
     ③ **프로필 선택 화면("Chrome 사용자 선택")** 이 뜨면(computer-use `screenshot` 확인) 브라우저 read 전용이라 Claude 가 클릭 못 함 → 사용자에게 **namoobi 프로필 1회 클릭** 요청. (피커 끄려면 크롬 프로필 설정에서 "시작 시 표시" 해제 안내.)
     ④ 확장이 붙어 기기가 반환되면 진행. 재실행·클릭 후에도 `[]` 면 Phase 6 에 "Chrome 미연결 — 메일 미발송(docx 는 연결 폴더 저장 완료)"으로 보고·발송 보류.
2. 해당 브라우저에 발송 계정 로그인 (https://mail.google.com/mail/u/0/)
   — 로그인 안 돼 있으면 비밀번호 입력은 정책상 Claude 가 대신 못 함 → 사용자에게 요청
   — **Gmail 이 아직 안 켜져 있어도 됨**: Claude in Chrome 으로 `https://mail.google.com/mail/u/0/?ogbl#inbox` 로 바로 `navigate` 하면 받은편지함이 열린다. **로그인은 항상 유지돼 있으므로** 별도 로그인 절차 없이 그대로 작성·발송하면 된다.
3. **첨부할 docx** 가 **연결 폴더(D:\claudeCowork)** 에 있을 것. ⚠️ file_upload 는 사용자 PC 경로만 받는다 — outputs 의 VM 경로(`/sessions/...`)는 거부되므로, 첨부는 반드시 **연결 폴더의 Windows 경로**(예: `D:\claudeCowork\global_market_report_YYYYMMDD_HHMM.docx`)로 지정한다. (v3.4.3 실측: outputs 경로·VM 경로 모두 업로드 거부, `D:\claudeCowork\...` 만 성공)

## 발송 절차 (docx 생성 후 추가 입력 없이 자동 수행)

사용자가 자동발송을 승인한 세션에서는 발송 직전 재확인도 생략한다.

> **⚠️ 작성창 하이드레이션 대기 — 리렌더 입력 유실 방지 (v3.6.2 · 2026-07-11 3회 실측)**
> `#inbox?compose=new` 로 navigate 하면 Gmail 앱 전체가 리로드되고, 작성창은 **껍데기(shell)가 먼저 뜬 뒤 편집기가 나중에 붙는다**("로드 중...", "리치 텍스트 로드 중..." 표시). 이 미완성 상태에서 입력한 **숨은참조·본문은 편집기 교체 시점에 유실**된다 — To·제목·첨부는 서버 초안에 먼저 커밋돼 살아남으므로 "부분만 남는" 위험한 상태가 된다.
> 규칙(순서 준수):
> 1. 가급적 URL 파라미터 대신 **받은편지함 로드 완료 후 `편지쓰기` 버튼 클릭**으로 작성창을 연다(앱 리로드 없음). URL 방식이 불가피하면 2번 대기를 반드시 지킨다.
> 2. **입력 시작 전 하이드레이션 완료를 폴링**: dialog `textContent` 에 `로드 중` 이 없고 `div[g_editable=true]` 가 존재할 때까지 대기(1초 간격, 최대 ~15초).
> 3. **입력 직후 반영 확인**: dialog `textContent` 로 BCC 주소·본문 첫 줄이 실제 들어갔는지 읽는다. 비어 있으면 ref 재클릭이 아니라 **screenshot 으로 실제 레이아웃 확인 후 화면 좌표로 재입력**한다(stale ref 클릭은 유실 상태에 다시 떨어진다).
> 4. 메일함이 큰 계정은 렌더러가 무거워 `innerText` 가 CDP 타임아웃/빈값을 자주 낸다 — **DOM 읽기는 `textContent`**, 렌더러 프리즈 반복 시 해당 탭을 닫고 새 탭에서 재시도.
> 5. 발송 성공 판정: "메시지 전송됨" 토스트 또는 (작성창 닫힘 + URL `#inbox` 복귀 + 받은편지함 카운트 증가·최상단 새 메일 도착) — screenshot 1장으로 최종 확인.


> **⚡ 토큰 절약 (v3.18 — 발송 방식·신뢰성 불변, 스크린샷 비용만 절감):** 메일 작성은 가급적 **`browser_batch` 로 여러 단계를 한 번에** 묶는다(작성창 열기·받는사람·숨은참조·제목·본문 입력). **단계마다 screenshot 을 찍지 말 것** — 화면 확인이 필요하면 **`get_page_text` 로 패시브 읽기**(클릭 없음 → 작성창 안 닫힘 + 이미지보다 토큰 저렴). **발송 직전 단 1회만** 전체 검증(아래 8단계)하고, 그때도 우선 `get_page_text` 로 받는사람/숨은참조 칩·제목·첨부 파일명을 확인하며, 애매할 때만 screenshot 1장. 첨부(file_upload)·발송(보내기) 메커니즘은 그대로다.

1. **docx 절대경로 확보** — **연결 폴더 Windows 경로** 기준 (예: `D:\claudeCowork\global_market_report_YYYYMMDD_HHMM.docx`). 같은 날짜 파일이 있어 `_HHMM` 접미사로 저장됐다면 그 실제 파일명을 사용.
2. **탭 준비** — `tabs_context_mcp(createIfEmpty=true)`
   - "Tabs can only be moved to and from normal windows" 오류 → 일반 크롬 창 없음.
     사용자에게 일반 창을 열어달라 요청 후 **재시도** (열리면 보통 즉시 성공)
   - 성공하면 tabId 로 `navigate` → `https://mail.google.com/mail/u/0/?ogbl#inbox` → screenshot 으로 로그인 확인.
     **Gmail 탭이 열려 있지 않아도 이 URL 로 navigate 하면 바로 받은편지함이 뜬다** (로그인 상시 유지 — 비밀번호 단계 불필요).
3. **작성창 열기** — 좌상단 `편지쓰기` 클릭 (작성창이 최소화돼 하단 "새 메일" 바만 보이면 그 바 클릭)
4. **받는사람(To) 입력** — 받는사람 칸 클릭 → `namoobi@gmail.com` 입력 → **Enter(칩 확정)**. To 는 이 한 명만.
4-1. **숨은참조(BCC) 입력** — 받는사람 칸 우측의 **`숨은참조`** 링크 클릭해 BCC 칸을 연 뒤,
   SECURITY 파일에서 읽은 주소(**`//` 주석 라인 제외**)를 **하나씩 입력 → Enter** 로 칩 확정 (주소마다 Enter 필수).
   BCC 주소가 화면·스크린샷에 보이더라도 채팅 응답에는 옮겨 적지 말 것 (인원 수만 보고).
   파일이 비어 있거나 유효 주소가 0개(전부 `//` 주석)이면 이 단계를 건너뛴다.
5. **제목 입력** — 반드시 **제목 칸을 새로 클릭한 뒤** 입력.
   형식: `[글로벌 시황 보고서] {YYYY년 M월 D일} 종합 보고서 송부`
6. **본문 입력** — 본문 영역 클릭 후: 핵심 헤드라인 3개 + 포트폴리오 톤 1줄 + "자세한 내용은 첨부 docx 참고"
7. **docx 첨부** — 첨부 버튼 클릭 금지(네이티브 파일창은 제어 불가).
   `find("file attachment input (type=file)")` 로 숨은 input 의 ref 획득 →
   `file_upload(paths=["D:\\claudeCowork\\...docx"], ref=..., tabId=...)` 로 직접 첨부 (연결 폴더 Windows 경로 사용 — outputs/VM 경로는 거부됨).
8. **검증 (발송 직전 1회)** — 우선 **`get_page_text` 로** 받는사람(To)·숨은참조(BCC) 칩 개수·제목·본문·첨부(docx 파일명/용량)를 읽어 확인(클릭 금지·작성창 유지). 텍스트로 불명확할 때만 **screenshot/zoom 1장** 보강. (단계마다 screenshot 금지 — 위 ⚡ 참조)
9. **발송** — `보내기` 클릭 → "메시지 전송됨" 토스트 확인 (#sent URL 전환, 임시보관함 비워짐도 신호)

## ⚠️ 흔한 함정 (반드시 회피)

- **수신자 칩 클릭 금지**: 칩/작성창 내부를 클릭해 검증하면 작성창이 닫히고 초안만 임시보관함에 남거나,
  아래 메일 목록 행을 잘못 클릭한다. 검증은 screenshot/zoom 으로만.
- **초안 재개**: 작성창이 닫혔으면 `navigate #drafts` → 초안(보통 "(제목 없음)") 클릭 → 수신자는 보존돼
  있으니 제목/본문/첨부만 이어서 넣고 발송.
- **제목이 받는사람 칸으로 들어감**: 수신자 입력 직후 좌표로 제목 칸을 누르면 레이아웃이 밀려 제목이
  받는사람 칸에 "외 N명" 으로 들어간다 → 수신자는 Enter 로 칩 확정 후, **제목 칸을 새로 클릭**해 입력.
- **연락처 표시명 함정**: 입력한 이메일이 주소록에 있으면 칩이 이메일 대신 **저장된 연락처 이름**으로
  표시된다 (예: namoobi@gmail.com → "JAEWOO SEO (gmail.com)"). 도메인/주소로 동일인 확인. 불확실하면 zoom.
- **포커스 유실**: screenshot/zoom 후 키 입력이 안 먹으면 대상 칸을 다시 클릭하고 진행.
- **백스페이스 과다 삭제**: 받는사람 칸에서 백스페이스로 칩까지 지워질 수 있음 → 사라졌으면 재입력 + Enter.

## 트러블슈팅

| 증상 | 대처 |
|------|------|
| "normal windows" 탭 오류 | 일반 크롬 창 열기 요청 → `tabs_context_mcp(createIfEmpty=true)` 재시도 |
| Chrome 미연결 | `list_connected_browsers` 확인, 확장 켜고 재시도 |
| Gmail 탭이 안 열려 있음 | Claude in Chrome 으로 `https://mail.google.com/mail/u/0/?ogbl#inbox` navigate — 로그인 상시 유지라 바로 받은편지함 |
| Gmail 미로그인 (드묾) | 보통은 로그인 상시 유지. 그래도 로그인 화면이면 비밀번호 대리 입력 불가 → 사용자가 직접 로그인 후 재시도 |
| 작성창 닫힘/초안만 남음 | #drafts 에서 초안 재개 |
| 칩이 사람 이름으로 표시 | 주소록 매칭 — 도메인/주소로 확인, 정상일 수 있음 |
| 첨부 실패 / "only files the user has shared" | docx 를 **연결 폴더(D:\claudeCowork) Windows 경로**로 첨부 (outputs·`/sessions/...` VM 경로는 업로드 거부됨) |
| 숨은참조 칸이 안 보임 | 받는사람 칸 우측 `숨은참조` 링크 클릭해 BCC 칸 펼치기 |
| 수신자 파일 없음 | 예약 모드는 예약메일수신자.txt, 일반 모드는 메일수신자.txt. 해당 파일 없으면 BCC 없이 To(namoobi)만 발송 + 결과 보고에 "BCC 파일 없음" 명시 |
| 특정 수신자만 일시 제외하고 싶음 | 해당 줄 맨 앞에 `//` 추가 (주소 보존). 빌더가 `//` 라인을 BCC 대상에서 제외 |
| 전부 `//` 주석이라 유효 주소 0개 | To(namoobi)만 발송 + 결과 보고에 "BCC 0명(전부 주석)" 명시 |
| 작성창에 입력한 BCC·본문이 사라짐("로드 중..." 리렌더) | 하이드레이션 전 입력 유실 — v3.6.2 규칙(입력 전 g_editable+로드중 소멸 대기 → 입력 후 textContent 재확인 → 유실 시 screenshot 기반 좌표 재입력) |
| 전면 작성창(view=cm)에서 보내기 클릭이 무반응(초안만 남음) | **재발성 결함 — v3.68 표준(초안 경유)로 전환**: #drafts → 초안 열기 → 미니 작성창 펼침 → 첨부·발송. 보낸편지함 실측으로만 발송 판정 |
| 첨부 업로드 중 보내기 클릭됨 → 미발송 | 업로드 완료 폴링 필수: [role=progressbar] 소멸 + "첨부파일을 추가했습니다" 확인 후 발송 (본문 % 문구를 진행률로 오탐 금지) |
| Gmail 탭 렌더러 프리즈(스크린샷·JS 45초 타임아웃 반복) | 대기하지 말고 탭 폐기→새 탭→#drafts 재개 (대형 메일함 계정의 재발성 증상) |
