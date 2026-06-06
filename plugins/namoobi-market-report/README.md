# namoobi-market-report (Cowork Plugin) v1.0.0

한 마디만 입력하면 6개 서브에이전트가 병렬로 글로벌 시장 데이터를 수집해
종합 시황 보고서(DOCX)를 만들고, Claude in Chrome 가 로그인된 Gmail 에서 직접 발송하는 플러그인.
(global-market-report v0.3.0 의 후속 — 운영 학습 반영 리빌드)

## ✨ 주요 기능

- **6개 서브에이전트 병렬 수집** (프롬프트 전문: `skills/namoobi-market-report/references/agents.md`)
  - NewsAgent: 글로벌 Top 10 뉴스 + 환율 스냅샷
  - MarketsAgent: 한·미·아시아·유럽 증시 + VIX/DXY/美10년 — 1주~1년 추세
  - CommoditiesAgent: 에너지·금속·농산물 (옥수수·대두·밀 포함)
  - CryptoAgent: 시장 개요 + 공포·탐욕 + 김치프리미엄(BTC/ETH/XRP/SOL)
  - SecuritiesAgent: 한국 5대 증권사 리서치 (Chrome)
  - AnalysisAgent: 종합 분석 + 공격/중립/안정형 포트폴리오 + 액션 아이템
- **DOCX 자동 생성**: Executive Summary·표·헤더·페이지 번호·한글 폰트, `--validate` 사전 검증
- **Gmail 직접 발송**: Claude in Chrome 가 로그인된 Gmail 작성창에서 작성·첨부·발송 (SMTP 불필요)
- 기본 수신자: namoobi@gmail.com, jaewoo.seo@mobis.com

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
- v1.0.0 — 2026-06-06 (global-market-report v0.3.0 → 리빌드)
