# namoobi-market-report (Cowork Plugin) v1.2.6

한 마디만 입력하면 7개 서브에이전트가 병렬로 글로벌 시장 데이터를 수집해
종합 시황 보고서(DOCX)를 만들고, Claude in Chrome 가 로그인된 Gmail 에서 직접 발송하는 플러그인.
(global-market-report v0.3.0 의 후속 — 운영 학습 반영 리빌드)

## ✨ 주요 기능

- **7개 서브에이전트 병렬 수집** (프롬프트 전문: `skills/namoobi-market-report/references/agents.md`)
  - NewsAgent: 글로벌 Top 10 뉴스 + **이벤트 캘린더(향후 2주)** + 원화 톤
  - MarketsAgent: 한·미·아시아·유럽 증시 + VIX/DXY/美10년 + **주요 환율 추세** — 1주~1년
  - CommoditiesAgent: 에너지·금속(**희토류 REMX 포함**)·농산물
  - CryptoAgent: 시장 개요 + 공포·탐욕 + 김치프리미엄(BTC/ETH/XRP/SOL)
  - SecuritiesAgent: 한국 5대 증권사 리서치 (WebSearch)
  - **GlobalSecuritiesAgent: 해외 IB 5사(UBS·GS·JPM·MS·BlackRock) 하우스 뷰** (공개 채널·WebSearch)
  - AnalysisAgent: 종합 분석 + 공격/중립/안정형 포트폴리오 + 액션 아이템
- **DOCX 자동 생성**: Executive Summary·표·헤더·페이지 번호·한글 폰트, `--validate` 사전 검증
- **Gmail 직접 발송**: Claude in Chrome 가 로그인된 Gmail 작성창에서 작성·첨부·발송 (SMTP 불필요)
- 받는사람(To): **namoobi@gmail.com 단독** / 숨은참조(BCC): `D:\claudeCowork\SECURITY\메일수신자.txt` 의 주소 (비공개, 인원 수만 보고)

### v1.2.6 변경점 (2026-06-08)
- build_report.js.b64 동봉 제거 — 비표준 백업 파일이 Cowork 플러그인 설치 검증을 막아 삭제. 마운트 잘림 복구는 Phase 0 의 git 원본 재복사로 대체.

### v1.2.5 변경점 (2026-06-08)
- 수신자 정책 변경: To 는 namoobi@gmail.com 단독, 그 외 수신자는 `D:\claudeCowork\SECURITY\메일수신자.txt` 에서 읽어 **숨은참조(BCC)** 로 발송 (서로의 주소 비노출). BCC 주소는 비공개로 다루며 SECURITY 폴더는 git 커밋 제외.

### v1.2.4 변경점 (2026-06-07 검증 운영 학습)
- **잘림 자가복구**: 샌드박스 마운트가 큰 파일을 잘라 읽는 문제 대응 — `build_report.js.b64`(gzip+base64 백업) 동봉, Phase 0 에서 EOF 마커 실패 시 자동 복원
- **실행 시간 보고**: Phase 6 결과 보고에 시작·완료(메일 발송 확인)·소요시간 표기
- **작업 폴더 보장**: D:\claudeCowork 미연결 시 자동 연결 요청, 결과물 사본 보장

### v1.2.3 변경점
- 속도 개선: 주봉(1y/1wk) 수집, 에이전트별 JSON 파일 직접 저장(메인 세션 재타이핑 제거)
- 결과물 위치 고정: 최종 docx·JSON 을 연결 폴더(D:\claudeCowork)에도 저장

### v1.2.2 변경점
- Phase 0 스크립트 무결성 검사(EOF 마커) + asset_view 키 별칭 수용

### v1.2.1 변경점
- 이벤트 캘린더 2단 구성: 2.1 향후 1개월(전체 중요도) + 2.2 중장기 1개월~1년(★★★만)

### v1.2.0 변경점
- 글로벌 주요 IB 리서치 섹션 추가 — UBS(CIO Daily)·Goldman Sachs(Insights)·J.P. Morgan(Global Research)·Morgan Stanley(Thoughts on the Market)·BlackRock(BII Weekly) 무료 공개 채널 기반 하우스 뷰. 원문 리포트는 고객 전용이라 핵심 메시지만 수집.

### v1.1.0 변경점
- 글로벌 주요 이벤트 캘린더 섹션 추가 (날짜·지역·이벤트·중요도·예상 영향)
- 희토류(REMX ETF) 단·중·장기 추세를 금속 테이블에 추가
- 환율 5종(USD/EUR/JPY/CNY/HKD vs KRW) 단·중·장기 추세 테이블 + 달러인덱스(DXY) 병기
- 기본 수신자 확대 (※ v1.2.5 에서 To 단독 + BCC 정책으로 변경됨)

## 🚀 트리거 문구

- "글로벌 시황 보고서 만들어줘" / "오늘 시장 보고서 작성하고 메일 발송"
- "global market report" / "daily market briefing"
- "코스피 미국증시 보고서 보내줘" / "namoobi 시황 보고서"

## 📋 의존성

- Node.js 18+ / `docx` npm 패키지 (DOCX 빌더)
- MCP: UsStockInfo, CoinInfo, NaverSearch(선택), Claude in Chrome (발송 필수)
- Gmail 에 발송 계정이 **미리 로그인**돼 있어야 함 (비밀번호 대리 입력 불가)

## 발송 전 체크 3가지

1. Claude in Chrome 연결 + **일반 크롬 창** 1개 이상
2. mail.google.com 로그인 상태
3. docx 가 연결된 폴더/outputs 에 존재

상세 절차·함정 회피: `skills/namoobi-market-report/references/email-sending.md`

## 📝 라이선스 / 만든 사람

MIT — namoobi (with Claude AI Research via Cowork)
- v1.2.5 — 2026-06-08 (수신자 정책: To 단독 + SECURITY 파일 BCC)
- v1.2.4 — 2026-06-07 (잘림 자가복구 + 실행시간 보고 + 작업폴더 보장)
- v1.2.0 — 2026-06-06 (글로벌 IB 리서치 추가)
- v1.0.0 — 2026-06-06 (global-market-report v0.3.0 → 리빌드)
