# namoobi-market-report (Cowork Plugin) v1.2.0

한 마디만 입력하면 7개 서브에이전트가 병렬로 글로벌 시장 데이터를 수집해
종합 시황 보고서(DOCX)를 만들고, Claude in Chrome 가 로그인된 Gmail 에서 직접 발송하는 플러그인.
(global-market-report v0.3.0 의 후속 — 운영 학습 반영 리빌드)

## ✨ 주요 기능

- **7개 서브에이전트 병렬 수집** (프롬프트 전문: `skills/namoobi-market-report/references/agents.md`)
  - NewsAgent: 글로벌 Top 10 뉴스 + **이벤트 캘린더(향후 2주)** + 원화 톤
  - MarketsAgent: 한·미·아시아·유럽 증시 + VIX/DXY/美10년 + **주요 환율 추세** — 1주~1년
  - CommoditiesAgent: 에너지·금속(**희토류 REMX 포함**)·농산물
  - CryptoAgent: 시장 개요 + 공포·탐욕 + 김치프리미엄(BTC/ETH/XRP/SOL)
  - SecuritiesAgent: 한국 5대 증권사 리서치 (Chrome)
  - **GlobalSecuritiesAgent: 해외 IB 5사(UBS·GS·JPM·MS·BlackRock) 하우스 뷰** (공개 채널·WebSearch)
  - AnalysisAgent: 종합 분석 + 공격/중립/안정형 포트폴리오 + 액션 아이템
- **DOCX 자동 생성**: Executive Summary·표·헤더·페이지 번호·한글 폰트, `--validate` 사전 검증
- **Gmail 직접 발송**: Claude in Chrome 가 로그인된 Gmail 작성창에서 작성·첨부·발송 (SMTP 불필요)
- 기본 수신자: namoobi@gmail.com, jaewoo.seo@mobis.com, hyun.jiyoun@gmail.com

### v1.2.0 변경점
- 글로벌 주요 IB 리서치 섹션 추가 — UBS(CIO Daily)·Goldman Sachs(Insights)·J.P. Morgan(Global Research)·Morgan Stanley(Thoughts on the Market)·BlackRock(BII Weekly) 무료 공개 채널 기반 하우스 뷰. 원문 리포트는 고객 전용이라 핵심 메시지만 수집.

### v1.1.0 변경점
- 글로벌 주요 이벤트 캘린더 섹션 추가 (날짜·지역·이벤트·중요도·예상 영향)
- 희토류(REMX ETF) 단·중·장기 추세를 금속 테이블에 추가
- 환율 5종(USD/EUR/JPY/CNY/HKD vs KRW) 단·중·장기 추세 테이블 + 달러인덱스(DXY) 병기
- 기본 수신자 3명으로 확대

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
- v1.2.0 — 2026-06-06 (글로벌 IB 리서치 추가)
- v1.0.0 — 2026-06-06 (global-market-report v0.3.0 → 리빌드)
