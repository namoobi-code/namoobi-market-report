# 이메일 발송 가이드 — Claude in Chrome 직접 발송 (v3)

> ⚠️ SMTP 는 샌드박스 네트워크 차단으로 동작하지 않는다. 사용 금지.
> Gmail MCP 초안 방식도 첨부 미지원 + 계정 불일치로 부적합.
> **아래 Chrome 직접 발송만 사용한다.**

**기본 수신자**: `namoobi@gmail.com`, `jaewoo.seo@mobis.com` (사용자가 다른 수신자를 지정하면 대체)

## 발송 전제 조건

1. Claude in Chrome 확장 연결 + **일반(normal) 브라우저 창** 존재
   (`mcp__Claude_in_Chrome__list_connected_browsers` 로 확인)
2. 해당 브라우저에 발송 계정 로그인 (https://mail.google.com/mail/u/0/)
   — 로그인 안 돼 있으면 비밀번호 입력은 정책상 Claude 가 대신 못 함 → 사용자에게 요청
3. docx 가 **연결된 폴더 또는 outputs** 에 있을 것 (file_upload 는 세션 공유 폴더 파일만 첨부 가능)

## 발송 절차 (docx 생성 후 추가 입력 없이 자동 수행)

사용자가 자동발송을 승인한 세션에서는 발송 직전 재확인도 생략한다.

1. **docx 절대경로 확보** — 사용자 PC 경로 기준 (예: `C:\...\outputs\글로벌금융시장_종합시황보고서_YYYYMMDD.docx`)
2. **탭 준비** — `tabs_context_mcp(createIfEmpty=true)`
   - "Tabs can only be moved to and from normal windows" 오류 → 일반 크롬 창 없음.
     사용자에게 일반 창을 열어달라 요청 후 **재시도** (열리면 보통 즉시 성공)
   - 성공하면 tabId 로 `navigate` → `https://mail.google.com/mail/u/0/` → screenshot 으로 로그인 확인
3. **작성창 열기** — 좌상단 `편지쓰기` 클릭 (작성창이 최소화돼 하단 "새 메일" 바만 보이면 그 바 클릭)
4. **받는사람 입력** — 받는사람 칸 클릭 → 첫 주소 입력 → **Enter(칩 확정)** → 다음 주소 입력 → **Enter**.
   (수신자마다 Enter 필수)
5. **제목 입력** — 반드시 **제목 칸을 새로 클릭한 뒤** 입력.
   형식: `[글로벌 시황 보고서] {YYYY년 M월 D일} 종합 보고서 송부`
6. **본문 입력** — 본문 영역 클릭 후: 핵심 헤드라인 3개 + 포트폴리오 톤 1줄 + "자세한 내용은 첨부 docx 참고"
7. **docx 첨부** — 첨부 버튼 클릭 금지(네이티브 파일창은 제어 불가).
   `find("file attachment input (type=file)")` 로 숨은 input 의 ref 획득 →
   `file_upload(paths=[docx 절대경로], ref=..., tabId=...)` 로 직접 첨부
8. **검증** — **screenshot/zoom 으로만** 수신자·제목·본문·첨부(파일명/용량) 확인
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
| Gmail 미로그인 | 사용자가 직접 로그인 후 재시도 |
| 작성창 닫힘/초안만 남음 | #drafts 에서 초안 재개 |
| 칩이 사람 이름으로 표시 | 주소록 매칭 — 도메인/주소로 확인, 정상일 수 있음 |
| 첨부 실패 | docx 가 연결 폴더/outputs 에 있는지 경로 확인 |
