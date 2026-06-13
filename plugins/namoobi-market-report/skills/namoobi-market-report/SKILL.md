---
name: namoobi-market-report
description: |
  글로벌 금융시장 종합 시황 보고서를 자동 생성·발송하는 워크플로우. 사용자가
  "글로벌 시황 보고서", "오늘 시장 보고서 보내줘", "global market report",
  "daily market briefing", "매일 시황 발송", "코스피 미국증시 보고서 만들어줘",
  "namoobi 시황 보고서" 등으로 요청할 때 트리거된다. 7개의 서브에이전트
  (뉴스/시장데이터/원자재/암호화폐/한국증권사/글로벌IB/종합분석)를 병렬로 호출해 자료를 수집하고,
  종합 데이터를 JSON으로 정리한 뒤 PDF 보고서를 생성하고, Claude in Chrome 가
  로그인된 Gmail 작성창에서 직접 메일을 작성·PDF 첨부·발송한다
  (받는사람: namoobi@gmail.com 단독, 숨은참조: 연결폴더 SECURITY 폴더의 수신자 목록 파일에 적힌 주소 —
  예약 실행이면 예약메일수신자.txt, 일반 실행이면 메일수신자.txt).
---

# Namoobi Market Report (v3.5.0)

> v3.5.0 (plugin 1.6.0) 변경점 — 섹션 확장·작성주체 익명화 (2026-06-13 사용자 피드백):
> - **3.1 한국 증시 확장** — 3.1.1 외국인 순매수 동향 · 3.1.2 경기선행지수 순환변동치 · 3.1.3 순환매 대비 테마별 현황(반도체·조선·방산·전력[전력기기·송배전·ESS·원전]·증권·로봇[피지컬AI]·우주) 추가. MarketsAgent 가 `markets.korea_flows`/`korea_leading`/`korea_themes` 수집.
> - **3.2 미국 증시 확장** — 3.2.1 미국 하이일드(HY) 신용 스프레드(FRED ICE BofA OAS·유효수익률·내재국채 분해) · 3.2.2 AI 빅테크 자본지출(CAPEX) 추가. `markets.us_credit`/`markets.bigtech_capex`.
> - **2.3 빅테크 주요 이벤트(신제품·신기술)** — 매우 중요한 것만 별도 표. NewsAgent 가 `news.bigtech_events` 수집(삼성 언팩·애플 이벤트·OpenAI 신모델 등, ★ 중요도).
> - **4.5 전략광물·배터리 금속** — 리튬·니켈·코발트·우라늄·희토류·흑연. ETF 프록시(LIT·REMX·URA·URNM) 추세 + 현물 표. CommoditiesAgent 가 `commodities.strategic_metals` 수집. **4.2 금속에서 희토류(REMX) 행 제거**(전략광물로 이전).
> - **작성주체 익명화** — 표지·면책·13장에서 'Claude' 표기 전부 제거('AI Research'/'AI'로 표기).
>
> v3.4.3 변경점 — 수신자 분기·PDF 발송·가독성 (2026-06-12 사용자 피드백):
> - **실행 모드별 수신자 분기** — 예약(Schedule) 실행이면 `SECURITY\예약메일수신자.txt`, 일반 실행이면 `SECURITY\메일수신자.txt` 의 주소를 BCC 로 보낸다. 두 파일 모두 `//` 주석 라인은 제외. 모드 판정은 Phase 0 에서 스킬 인자(`scheduled`/`예약`)·예약 작업 프롬프트 명시로 한다. (예약 작업 SKILL.md 프롬프트에 `/namoobi-market-report:namoobi-market-report scheduled` 로 인자를 전달할 것.)
> - **PDF 만 생성·발송** — 이제 메일 첨부는 **PDF** 다. docx 는 빌더 산출용 중간 파일로만 outputs 에 두고, **연결 폴더에는 PDF 만 저장**하고 메일에도 PDF 를 첨부한다. (⚠️ file_upload 는 `D:\claudeCowork\...` Windows 경로만 받는다 — outputs·VM 경로는 거부. 그래서 PDF 를 반드시 연결 폴더에 둔다.)
> - **임팩트·핵심테마 색상 마커** — 1장 Top News 임팩트와 9.2 핵심테마 방향을 `▲ 강세(초록)`/`▼ 부정(빨강)`/`■ 양면(앰버)` 로 기호+색 구분. Top News 표 하단에 색상 범례 추가. (구버전 `★`/`중립` 표기 폐기 → NewsAgent 임팩트 라벨 변경.)
> - **아시아 증시에 대만(가권 ^TWII) 추가** — MarketsAgent 티커맵·스키마(`asia_markets.taiwan`)·빌더 3.3 표에 반영.
> - **빅테크 주요 이벤트 누락 방지** — NewsAgent 가 캘린더 작성 전 빅테크 이벤트(아이폰·갤럭시 언팩·GTC·CES·OpenAI 신모델 등)를 **별도 WebSearch 로 필수 확인**하고, 향후 일정에 있으면 누락하지 않는다 (`references/agents.md` NewsAgent).
>
> v3.4.1~v3.4.2 변경점 — 보고서 구조·가독성·미리보기 (2026-06-11 사용자 피드백):
> - **(v3.4.1) 매크로 4장 삭제·번호 재조정** — VIX·DXY·美10년이 3.2 미국 증시 표와 중복이라 별도 4장을 삭제, 이후 장 번호를 한 칸씩 당김 (총 13장). 목차·"AI 의견 9~12장" 문구도 갱신.
> - **(v3.4.1) 김치 프리미엄 키 별칭** — CryptoAgent 가 `upbit_price_krw`/`global_price_usd`/`premium_percent` 로 저장해도 빌더가 렌더 (정식 키는 `upbit_krw`/`binance_usd`/`premium_pct`).
> - **(v3.4.2) 공포·탐욕 표 개선** — 컬럼을 [시점|지수|분류(단계)|현재 대비]로 분리. 모든 행에 분류를 표기(값으로 5단계 자동 도출)하고 분류 칸을 단계별 배경색(빨강~초록)으로 구분. 변화는 "+3p ▲ 공포 완화 (탐욕 쪽으로)" 식으로 설명. 범위 범례 추가.
> - **(v3.4.2) 한글 폰트 임베드 — 미리보기 깨짐 방지** — `scripts/fonts/nmr_kr.ttf`(나눔바른고딕 서브셋 2.2MB, OFL)를 빌더가 자동 임베드(폰트명 `NanumBarunGothic`). Phase 0 에서 fonts 폴더도 WORK 에 복사할 것. docx 크기 ~830KB→정상. **LibreOffice 계열 뷰어는 docx 임베드 폰트를 무시**하므로, 확실한 미리보기용으로 Phase 4 에서 PDF 사본도 생성한다: `mkdir -p ~/.fonts && cp fonts/nmr_kr.ttf ~/.fonts/ && fc-cache -f` 후 `soffice --headless --convert-to pdf`.
> - **(v3.4.2) 작성자 익명화** — 문서 내 "(Cowork)"·"namoobi" 표기 전부 제거 (표지 "작성: Claude AI Research — v3.4.2", 푸터 "v3.4.2", 13장 문구). 메일 본문 서명도 "— Claude AI Research 자동 생성·발송" 으로 쓸 것.
> - **(v3.4.2) 빅테크 신기술·신제품 이벤트 수록** — NewsAgent 이벤트 캘린더에 빅테크 발표(아이폰 이벤트·갤럭시 언팩·GTC·CES 키노트·OpenAI 신모델 등) 추가. 꼭 알아야 할 빅 이벤트만, expected_impact 에 관련 종목·섹터 명시, 중장기는 ★★★급만 (상세 `references/agents.md` NewsAgent 대상 목록).
>
> v3.4.0 (plugin 1.4.0) 변경점 — 데이터 소스 폴백·표 보강 (2026-06-09 운영 학습):
> - **시세 MCP 부재 시 Yahoo chart API 폴백 (가장 중요)** — UsStockInfo MCP 가 세션에 없으면 증시·환율·원자재의 1주~1년 변화율이 전부 "-" 가 된다. 이때 **Claude in Chrome 로 Yahoo chart API 를 직접 호출**해 주봉 1년 시계열을 받아 정밀 계산한다. 절차: `navigate https://finance.yahoo.com` → `javascript_tool` 로 `(async()=>{ ... await fetch("https://query1.finance.yahoo.com/v8/finance/chart/<TICKER>?range=1y&interval=1wk") ... })()` (CORS 허용됨, top-level await 금지 → async IIFE 로 감쌀 것). 각 티커의 주봉 close 와 `meta.regularMarketPrice` 로 1주(7d)/1개월(30d)/3개월(91d)/6개월(182d)/1년(365d) 변화율을 계산. **엔화(JPYKRW=X)는 100엔 환산이라 current 보존·변화율만 갱신**. CNY/KRW 데이터 희박 시 USD/KRW ÷ USD/CNY(CNY=X)로 도출. web_fetch·stooq 는 본문이 비어 못 쓰니 반드시 Chrome 사용.
> - **암호화폐 폴백 체계** — CoinInfo MCP 우선. 단 `get_kimchi_premium` 이 "데이터 부족" 으로 실패하면 **CoinDesk MCP `fetch_spot_tick`**(market=upbit, instruments=BTC-KRW,ETH-KRW,XRP-KRW,SOL-KRW + market=binance USDT)로 업비트·바이낸스 실시세를 받아 김프=(업비트KRW/(바이낸스USD×환율)−1)×100 로 계산. 환율은 Yahoo USD/KRW. CoinGecko 429(레이트리밋)로 market_overview/gainers/dominance 가 막히면 ~20초 후 재시도, 그래도 실패면 Crypto.com Exchange MCP 값/직전값 유지. 한국 거래소 API(업비트·빗썸)는 Chrome navigate 가 안전정책으로 차단하니 직접 띄우지 말 것 — CoinDesk MCP 사용.
> - **공포·탐욕 7개 시점 확장(증시처럼)** — alternative.me(`api.alternative.me/fng/?limit=400`, Chrome navigate→get_page_text 또는 JSON.parse(body))에서 현재·1일·1주·1개월·3개월(90d)·6개월(182d)·1년(365d) 전 값+분류를 수집. 빌더 7.2 표가 7행을 렌더(`last_3month(_cls)`/`last_6month(_cls)`/`last_year(_cls)`).
> - **매크로 지표 추세표화** — 4장(VIX·DXY·美10년)을 "단기 시그널/장기 추세" 텍스트에서 **증시와 동일한 1주~1년 변화율 추세표**로 변경.
> - **대형 IPO 일정 수록** — NewsAgent 가 SpaceX·OpenAI·Anthropic 등 대형 IPO 를 이벤트 캘린더에 넣는다. 상장일 확정 건은 1개월 캘린더, 미확정/전망 건은 중장기 캘린더에 `(미확정/전망)` 문구·출처와 함께. 날짜 미상은 expected_timing 텍스트(예: "2026년 4분기(전망)")를 날짜 칸에.
> - **추세 평가 한글화** — 모든 추세(trend) 텍스트는 한글로 작성/생성한다(영문 금지).
> - ⚠️ **git·패키징 주의(재강조)** — 샌드박스 bash 마운트가 build_report.js 등 큰 파일을 간헐적으로 잘라 읽는다(예: 933행을 842행으로). 파일 수정·검증은 **Read/Write/Edit 도구(호스트 직접)** 로만 신뢰하고, **bash 에서 `git add/commit` 하지 말 것**(잘린 blob 이 커밋돼 저장소 손상). 커밋은 잘림 없는 **사용자 터미널**에서 수행한다.
>
> v3.3.0 (plugin 1.3.0) 변경점 — 반환각(Hallucination) 보완 (2026-06-09):
> - **공통 사실성 규칙** — 모든 서브에이전트 프롬프트에 "추정 금지·출처 의무·사실/의견 구분·결정적 출력" 7개 규칙을 붙인다 (`references/agents.md` 상단). 도구/검색으로 확인 안 된 값은 절대 기억으로 채우지 말고 null.
> - **RAG 출처 grounding** — 뉴스·이벤트·증권사/IB 리포트에 `source`/`source_url`/`published_date` 수집. 뉴스 표에 '출처' 컬럼(하이퍼링크) 추가. 출처 없는 뉴스는 애초에 수록 금지.
> - **이벤트 날짜 grounding** — FOMC·CPI·만기 등 미래 일정 날짜는 공식·1차 출처에서만 확인, 미확정은 `(미확정)`. 기억 기반 날짜 생성 금지.
> - **포트폴리오 수치 환각 방지** — `expected_return`/`max_drawdown` 은 계산 근거 또는 범위+가정으로만. `basis` 필드 필수, false precision 금지. 빌더가 산출근거를 표기·검증.
> - **디스클레이머 강화** — 표지 AI·환각 경고 배너, 10~13장 'AI 의견' 마커, 14장 출처·생성시각 보강.
> - **Phase 3.5 교차검증 추가** — DOCX 생성 전, 서브에이전트 1개로 환각·출처 누락·데이터 모순을 점검(아래 Phase 3.5).
>
> v3.2.7 (plugin 1.2.7) 변경점 — BCC 수신자 주석 처리 (2026-06-08):
> - **`//` 주석 수신자 제외** — `D:\claudeCowork\SECURITY\메일수신자.txt` 에서 라인 맨 앞(공백 허용)이 `//` 로 시작하면 그 수신자는 BCC 발송 대상에서 **제외**한다. 주소를 지우지 않고 일시적으로 빼두고 싶을 때 `//` 만 붙이면 된다.
> - 읽기 명령: `grep -vE '^[[:space:]]*//' …메일수신자.txt | grep -oE '<email>'` (주석 라인 제외 후 추출). 유효 주소가 0개(전부 주석)면 To(namoobi)에게만 발송하고 보고에 "BCC 0명(전부 주석)" 명시.
> - 상세는 `references/email-sending.md` 수신자 정책 참조.
>
> v3.2.6 (plugin 1.2.6) 변경점 — 설치 호환성 (2026-06-08):
> - **build_report.js.b64 동봉 제거** — 비표준 백업 파일이 Cowork 플러그인 설치 검증을 막던 원인이라 삭제. 마운트 잘림 복구는 Phase 0 의 EOF 검사 후 git 원본 재복사로 대체(아래).
> - SKILL 프론트매터에서 Windows 백슬래시 경로 제거(YAML 안전).
>
> v3.2.5 (plugin 1.2.5) 변경점 — 수신자 정책 변경 (2026-06-08):
> - **받는사람(To)** 는 `namoobi@gmail.com` **단 한 명만**.
> - **숨은참조(BCC)** 는 `D:\claudeCowork\SECURITY\메일수신자.txt` 의 각 줄 이메일을 읽어 넣는다 (다른 수신자가 서로의 주소를 보지 못하게).
> - BCC 주소는 **비공개 정보** — 채팅·보고·커밋에 평문 노출 금지, 인원 수만 보고. SECURITY 폴더는 git 커밋 금지.
> - 파일이 없거나 비면 To(namoobi)에게만 발송하고 보고에 명시.
>
> v3.2.4 (plugin 1.2.4) 변경점 — 신뢰성·가시성 개선 (2026-06-07 검증 운영 학습):
> - **잘림 원인 규명 + 자가복구** — 잘림의 원인은 설치 캐시 파일이 아니라 **샌드박스 마운트의 host→VM 동기화가 큰 파일을 간헐적으로 잘라 읽는 것** (호스트 원본은 정상. 같은 파일이 Read 도구로는 857행, bash 마운트로는 713행으로 보인 사례). 대응:
>   ① `scripts/build_report.js.b64` (gzip+base64 백업, ~15KB) 동봉 — Phase 0 에서 EOF 마커 검사 실패 시 b64 를 디코드해 **자동 복구**.
>   ② 파일 복사·패키징(.plugin 생성 포함) 후에는 **반드시 크기·EOF 마커 검증**. 잘린 파일로 .plugin 을 만들면 잘린 채 설치된다 (v123 .plugin 실제 사례).
>   ③ 호스트 파일의 신뢰 기준은 Read 도구 (호스트 직접 읽기). bash 마운트 읽기와 결과가 다르면 Read 쪽이 맞다.
> - **실행 시간 보고** — Phase 0 에서 시작시각 기록(`$WORK/nmr_start_epoch.txt`), Phase 6 결과 보고에 시작·완료(메일 발송 확인)·소요시간 표기.
> - **작업 폴더 보장** — Phase 0 에서 연결 폴더(D:\claudeCowork) 확인, 미연결이면 `mcp__cowork__request_cowork_directory`(path="D:\claudeCowork") 로 연결 요청. 거부/실패 시 outputs 에서 진행하되 Phase 6 보고에 "연결 폴더 미연결 — docx 사본 미생성"을 명시.
>
> v3.2.3 (plugin 1.2.3) 변경점 — 속도·결과물 위치 개선 (2026-06-07 운영 학습):
> - **결과물 위치 고정** — 최종 docx 는 반드시 **연결 폴더(D:\claudeCowork) 최상위에도 저장**. 연결 폴더는 기존 파일 덮어쓰기가 차단될 수 있으므로 동일 파일명 존재 시 `_HHMM` 시각 접미사를 붙여 새 파일로 저장. 보고서 JSON 도 연결 폴더 `_market_report_data` 에 복사.
> - **수집 속도 개선** — MarketsAgent·CommoditiesAgent 는 `get_historical_stock_prices` 를 `period="1y", interval="1wk"`(주봉)로 호출 (일봉 대비 토큰 1/5, 최장 에이전트 소요 절반 이하). 1주 변화율은 직전 주봉 종가로 계산.
> - **Phase 3 재조립 제거** — Phase 1/2 각 에이전트가 결과 JSON 을 outputs 파일(nmr_news.json 등)로 직접 저장하고, 메인 세션은 node 로 병합만 수행 (메인 세션 재타이핑 ~5분 절감).
>
> v3.2.2 (plugin 1.2.2) 변경점:
> - **Phase 0 스크립트 무결성 검사 추가** — build_report.js 가 잘려(713행) docx 가 생성되지 않는 사례 발생(2026-06-07). EOF 마커 검사로 사전 감지.
> - **asset_view 키 별칭 수용** — 빌더가 `cn_equity/jp_equity/eu_equity/kr_bond/us_bond` 축약 키도 렌더링. agents.md 에 정식 키명 명시.
>
> v3.2.1 (plugin 1.2.1) 변경점:
> - 이벤트 캘린더 2단 구성 — **2.1 향후 1개월(전체 중요도)** + **2.2 중장기 1개월~1년(★★★만)**. NewsAgent 가 events_calendar / events_calendar_longterm 분리 수집.
>
> v3.2 (plugin 1.2.0) 변경점:
> - **GlobalSecuritiesAgent 추가** — 해외 주요 IB 5사(UBS·Goldman Sachs·J.P. Morgan·Morgan Stanley·BlackRock)의 무료 공개 하우스 뷰 수집, 보고서 새 섹션 "글로벌 주요 IB 리서치". 원문 리포트는 고객 전용이므로 공개 채널(Insights/CIO View/언론 보도)·WebSearch 로 핵심 메시지만 수집. 부록 B 강점표 참조.
>
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

생성되는 docx 는 다음 10개 항목을 모두 포함해야 한다. 하나라도 누락되면 재작업 대상.

1. **글로벌 Top News 10** — 헤드라인 + 2~4문장 요약 + 임팩트 라벨(`▲ 강세`/`▼ 부정`/`■ 양면` — 기호+색 구분)
2. **글로벌 주요 이벤트 캘린더** — ① 향후 1개월 전체 중요도(★~★★★) ② 1개월~1년 중장기는 ★★★만 (날짜·지역·이벤트·예상 영향). **빅테크 주요 이벤트(아이폰·갤럭시 언팩·GTC·CES·OpenAI 신모델 등)가 향후 일정에 있으면 누락 금지** (NewsAgent 가 별도 검색으로 확인)
3. **단·중·장기 추세** — 모든 자산을 1주/1개월/3개월/6개월/1년 변화율로 제시
4. **글로벌 증시 풀커버리지** — 한국(코스피·코스닥)·미국·홍콩·중국·일본·**대만**·인도·베트남·유럽
5. **매크로 지표** — 달러지수(DXY), VIX, 美 10년 국채금리
6. **원자재 풀커버리지** — 에너지(WTI·천연가스) + 금속(금·은·구리) + 농산물(옥수수·대두·밀)
7. **주요 환율 추세** — USD/EUR/JPY/CNY/HKD vs KRW 단·중·장기 추세 + **달러인덱스(DXY)** 병기 + 원화 톤
8. **암호화폐** — 시장 개요 + 공포·탐욕 지수(현재/1일/1주/1개월) + 김치프리미엄(BTC/ETH/XRP/SOL)
9. **글로벌 주요 IB 리서치** — UBS·Goldman Sachs·J.P. Morgan·Morgan Stanley·BlackRock 하우스 뷰 (한국 5대 증권사와 동일 구조)
10. **종합 분석 + 포트폴리오** — 매크로 톤·테마·리스크 + 공격형/중립형/안정형 3개 모델 + 액션 아이템 (각 포트폴리오 `basis` 산출근거 포함)

11. **국내 순환매 테마·수급** — 외국인 순매수(코스피/코스닥) + 경기선행지수 순환변동치 + 순환매 테마별 현황(반도체·조선·방산·전력·증권·로봇·우주)
12. **미국 신용·CAPEX** — 하이일드(HY) 신용 스프레드(OAS·유효수익률·국채분해) + AI 빅테크 자본지출(CAPEX)
13. **전략광물·배터리 금속** — 리튬·니켈·코발트·우라늄·희토류·흑연(ETF 프록시+현물) + 빅테크 신제품·신기술 핵심 이벤트

추가 품질 기준 (v3.3.0 반환각 보완):
- **출처(grounding)**: Top News 와 증권사/IB 대표 리포트는 원문 링크(source_url)를 포함한다. 출처를 댈 수 없는 항목은 수록하지 않는다.
- **수치 근거**: 포트폴리오 기대수익·MDD 는 단일 false-precision 숫자가 아니라 계산근거 또는 범위+가정으로 표기하고 `basis` 를 명시한다.
- **디스클레이머**: 표지 AI·환각 경고 배너와 14장 출처·면책 고지가 반드시 포함된다.

## 워크플로우 개요

```
[Phase 0: 사전 점검]  실행 모드 판정(예약/일반) / 날짜·시작시각 기록 / 연결 폴더(D:\claudeCowork) / Chrome / 빌드환경·무결성(자동복구)
        ↓
[Phase 1: 병렬 수집 — 6개 서브에이전트를 단일 메시지로 동시 발행]
  ├─ NewsAgent / MarketsAgent / CommoditiesAgent / CryptoAgent
  ├─ SecuritiesAgent (한국 5대) / GlobalSecuritiesAgent (해외 IB 5사)
        ↓
[Phase 2: AnalysisAgent 단독 호출]  Phase 1 결과를 입력으로 종합·포트폴리오 도출
        ↓
[Phase 3: 데이터 종합 → JSON 저장 + 유효성 검증]
        ↓
[Phase 3.5: 반환각 교차검증]  서브에이전트 1개로 출처 누락·수치 모순·환각 점검 (v3.3.0)
        ↓
[Phase 4: 보고서 생성]  node build_report.js <json> <out.docx>(중간) → soffice 로 PDF 변환 → 연결 폴더에 PDF 저장
        ↓
[Phase 5: 이메일 발송]  Claude in Chrome → 로그인된 Gmail 직접 발송(PDF 첨부) + 모드별 수신자 파일 (references/email-sending.md)
        ↓
[Phase 6: 결과 보고]  헤드라인 3개 + 포트폴리오 톤 + 시작/완료/소요시간
```

## Phase 0: 사전 점검

0. **실행 모드 판정 (v3.4.3 — Phase 5 수신자 결정)**: 이번 실행이 **예약(scheduled)** 인지 **일반(normal)** 인지 먼저 판정한다.
   - **예약 모드 조건** (하나라도 해당): 스킬 인자(ARGUMENTS)에 `scheduled`/`schedule`/`예약` 포함 / 예약 작업 프롬프트가 예약 실행임을 명시(예: "이 실행은 예약 실행") / 세션이 사용자 입력 없이 스케줄러로 자동 시작됨.
   - **일반 모드**: 그 외 모두 (사용자가 채팅에서 직접 `/namoobi-market-report` 실행, 인자 `direct` 등).
   - 판정 결과를 메모해 두고(예: `$WORK/nmr_mode.txt` 에 `scheduled` 또는 `normal` 기록) Phase 5 에서 수신자 파일을 고른다:
     예약 → `SECURITY\예약메일수신자.txt`, 일반 → `SECURITY\메일수신자.txt`. (애매하면 **일반 모드**로 처리하고 Phase 6 에 모드를 명시한다.)
1. **날짜·시작시각**: `TZ=Asia/Seoul date '+%Y-%m-%d %H:%M:%S'` 로 오늘(KST)과 **워크플로우 시작시각**을 확정. `YYYYMMDD` 압축형도 함께 만든다. 시작시각(사람이 읽는 형식 + epoch)은 Phase 6 소요시간 계산에 쓰므로 아래 3번에서 `$WORK/nmr_start_epoch.txt` 로 기록한다.
2. **연결 폴더 확인** (v3.2.4): D:\claudeCowork 가 세션에 연결돼 있는지 확인. 미연결이면 `mcp__cowork__request_cowork_directory`(path="D:\claudeCowork") 로 연결을 요청한다 (ToolSearch 로 로드). 사용자가 거부하거나 연결 불가면 outputs 에서 진행하되, Phase 6 보고에 "연결 폴더 미연결 — docx 사본 미생성"을 명시한다.
3. **Chrome**: `mcp__Claude_in_Chrome__list_connected_browsers` 로 연결 확인. **일반(normal) 브라우저 창**이 있어야 한다. 없으면 사용자에게 일반 크롬 창을 열어달라고 요청. (발송 직전이 아니라 지금 미리 확인해 두면 Phase 5 실패를 줄인다.)
4. **빌드 환경 준비 + 무결성 검사·자동복구** — 플러그인 마운트는 읽기 전용이므로 쓰기 가능한 outputs 에 복사해 빌드한다:

```bash
SRC="$(dirname "$(find /sessions/*/mnt -path '*namoobi-market-report/scripts/build_report.js' 2>/dev/null | head -1)")"
WORK="$(ls -d /sessions/*/mnt/outputs 2>/dev/null | head -1)/nmr_build"
rm -rf "$WORK"; mkdir -p "$WORK"
date +%s > "$WORK/nmr_start_epoch.txt"   # v3.2.4 시작시각 기록
TZ=Asia/Seoul date '+%Y-%m-%d %H:%M:%S' > "$WORK/nmr_start_human.txt"
cp "$SRC/build_report.js" "$SRC/package.json" "$WORK/"
cp -r "$SRC/fonts" "$WORK/fonts" 2>/dev/null && echo "폰트 OK ($(wc -c < "$WORK/fonts/nmr_kr.ttf")B)"  # v3.4.2 한글 임베드 폰트
cd "$WORK"
[ -d "$WORK/node_modules/docx" ] || npm install docx --no-fund --no-audit
node -e "require('$WORK/node_modules/docx'); console.log('docx OK')"
# 무결성 검사 (v3.2.6) — 샌드박스 마운트가 큰 파일을 잘라 읽는 사례가 있음 (호스트 원본은 정상)
if ! tail -1 "$WORK/build_report.js" | grep -q "EOF — namoobi-market-report"; then
  echo "⚠️ 잘림 감지 → git 원본에서 재복사"
  cp "$SRC/build_report.js" "$WORK/build_report.js"
fi
tail -1 "$WORK/build_report.js" | grep -q "EOF — namoobi-market-report" \
  && node --check "$WORK/build_report.js" && echo "script OK" \
  || echo "❌ 여전히 잘림 — 호스트 git 원본을 Read 도구로 읽어(마운트 bash 금지) WORK 에 재구성할 것"
```

> ⚠️ `/tmp` 는 이전 세션 잔존물로 권한 오류가 날 수 있으니 사용하지 말 것. 항상 outputs 하위에서 빌드.
> ⚠️ 마운트 읽기 잘림은 b64(~15KB, 작아서 안전) 디코드로 복구된다. b64 마저 잘렸으면 호스트 경로를 **Read 도구**로 읽어 재구성한다 — Read 는 호스트를 직접 읽으므로 항상 완전하다.

## Phase 1–2: 서브에이전트 호출

상세 프롬프트와 각 에이전트의 반환 JSON 스키마는 **`references/agents.md`** 를 읽고 그대로 사용한다.

핵심 규칙:
- Phase 1의 6개 에이전트(News/Markets/Commodities/Crypto/Securities/GlobalSecurities)는 **반드시 단일 메시지에서 동시 발행** (general-purpose 타입).
- AnalysisAgent 는 6개 결과를 모두 받은 뒤 **마지막에 단독 호출**. 6개 JSON 을 프롬프트에 붙이는 대신 "outputs 의 nmr_*.json 6개를 bash 로 읽으라"고 지시해도 된다 (재타이핑 절감).
- **(v3.2.3 속도)** MarketsAgent·CommoditiesAgent 프롬프트에 `period="1y", interval="1wk"`(주봉) 사용을 명시한다 — 일봉 금지. 1주 변화율은 직전 주봉 종가 기준.
- **(v3.2.3 속도)** 각 에이전트 프롬프트에 "최종 JSON 을 outputs 하위 `nmr_<이름>.json` 파일로 bash heredoc 저장하고, 응답으로는 저장 경로와 1줄 요약만 반환하라"를 명시한다. 메인 세션이 긴 JSON 을 받아 재타이핑하는 것을 금지.
- MCP 도구는 deferred 상태일 수 있으므로 각 에이전트 프롬프트에 "먼저 `ToolSearch` 키워드 검색(예: `+UsStockInfo historical`, `+CoinInfo fear greed`)으로 도구를 로드한 뒤 사용하라"고 명시한다. **UUID 가 포함된 도구명을 하드코딩하지 말 것** — 서버 ID는 세션마다 다를 수 있다.
- 서브에이전트가 API 오류(소켓 끊김 등)로 결과 파일을 저장하지 못했으면 해당 에이전트만 재실행한다 (파일 존재 여부로 판단).
- 실패한 데이터는 null / 빈 배열로 두고 진행한다. 빌더가 "-" 로 렌더링한다.

## Phase 3: 데이터 종합 및 저장

에이전트들이 저장해 둔 `nmr_*.json` 파일을 **node 스크립트로 병합**해 (메인 세션 재타이핑 금지)
outputs 하위 `_market_report_data/report_data_YYYYMMDD.json` 으로 저장한다. metadata 는 병합 시 추가.

> ⚠️ 직접 heredoc 작성이 불가피한 경우: 한글 JSON 은 단일 인용 heredoc(`<<'JSONEOF'`)으로 변수확장을 막을 것.
> 병합 후 JSON 사본을 연결 폴더 `D:\claudeCowork\_market_report_data\` 에도 복사한다 (새 파일 생성은 허용됨).

저장 후 반드시 검증:
```bash
cd "$WORK" && node build_report.js --validate <outputs>/_market_report_data/report_data_YYYYMMDD.json
```
누락 섹션이 보고되면 해당 에이전트를 재실행하거나 null 처리 사유를 확인한 뒤 진행.
`--validate` 가 v3.3.0 부터 **출처 없는 뉴스·basis 누락 포트폴리오**도 경고로 보고하므로, 경고가 나오면 Phase 3.5 에서 함께 점검한다.

## Phase 3.5: 반환각(Hallucination) 교차검증 (v3.3.0)

DOCX 생성 직전, **general-purpose 서브에이전트 1개**를 띄워 종합 JSON(`report_data_YYYYMMDD.json`)을 입력으로 아래를 점검하게 한다. 고위험(외부 메일 발송) 작업이므로 메인 세션이 아닌 별도 에이전트로 검증한다.

서브에이전트 프롬프트 골자:
- **출처 점검**: `news.top_news` 각 항목에 `source_url` 이 있는지, 증권사/IB `key_reports` 가 비어있지 않은 곳은 링크가 있는지 확인. 출처 없는 정성 항목을 표시.
- **수치 정합성**: `analysis.asset_view`·포트폴리오의 방향성이 실제 수집된 `markets`/`commodities`/`crypto` 수치와 모순되지 않는지(예: "증시 강세" 서술인데 주요 지수 1개월 변화율이 일제히 음수) 점검.
- **포트폴리오 근거**: 각 portfolio 에 `basis` 가 있고, 기대수익·MDD 가 단일 false-precision 숫자가 아닌지 확인.
- **날짜 sanity**: `events_calendar` 날짜가 오늘(KST) 이후인지, `events_calendar_longterm` 이 1개월~1년 범위인지, 명백히 틀린(과거) 날짜가 향후 일정에 없는지 확인.
- **환각 의심 표현**: 확인 불가한 구체 수치·고유명사(목표주가, 특정 인용문 등)가 출처 없이 단정적으로 적혔는지 표시.
- 산출물: `{ "ok": true|false, "blocking": [...심각 문제...], "warnings": [...경미...] }` 를 outputs 에 `nmr_verify.json` 으로 저장하고 1줄 요약만 반환.

대응: `blocking` 이 있으면 해당 에이전트를 재실행하거나 문제 필드를 null/수정 후 재검증한다. `warnings` 만 있으면 진행하되 Phase 6 보고에 건수를 명시한다. (검증 실패가 반복되면 그 항목을 비우고 진행 — 환각을 남기느니 비우는 것이 낫다.)

## Phase 4: 보고서 생성 (PDF 만 — v3.4.3)

> **이제 메일 첨부·연결 폴더 산출물은 PDF 다.** docx 는 빌더(build_report.js)가 만드는 **중간 파일**로 outputs 에만 두고, 연결 폴더에는 복사하지 않는다. 최종 산출물은 PDF.

1. **docx 생성 (중간 파일)** — outputs 에 생성:
```bash
cd "$WORK"
node build_report.js \
  <outputs>/_market_report_data/report_data_YYYYMMDD.json \
  <outputs>/글로벌금융시장_종합시황보고서_YYYYMMDD.docx
```
빌드 후 파일 크기와 `unzip -l` 무결성, 표 개수(`<w:tbl>`)를 점검한다.

2. **PDF 변환** — 한글 임베드 폰트를 시스템에 설치한 뒤 soffice 로 변환:
```bash
mkdir -p ~/.fonts && cp "$WORK/fonts/nmr_kr.ttf" ~/.fonts/ && fc-cache -f >/dev/null 2>&1
timeout 60 soffice --headless --convert-to pdf --outdir "<outputs>" "<outputs>/글로벌금융시장_종합시황보고서_YYYYMMDD.docx"
pdffonts "<outputs>/글로벌금융시장_종합시황보고서_YYYYMMDD.pdf" | grep -qi nanum && echo "PDF 한글 OK"
```

3. **(필수) PDF 를 연결 폴더 `D:\claudeCowork` 최상위에 저장한다.** ⚠️ file_upload 는 `D:\claudeCowork\...` Windows 경로만 받으므로(outputs·VM 경로 거부) **메일 첨부를 하려면 PDF 가 연결 폴더에 반드시 있어야 한다.**
   연결 폴더는 기존 파일 덮어쓰기가 차단될 수 있으므로, 동일 파일명이 이미 있으면 `글로벌금융시장_종합시황보고서_YYYYMMDD_HHMM.pdf` 처럼 실행 시각 접미사를 붙여 **새 파일**로 저장하고, 그 실제 파일명을 Phase 5 첨부에 사용한다.
   복사 후 **반드시 크기를 비교 검증**한다 (`wc -c` 원본=사본). 연결 폴더가 없으면 첨부가 불가하므로 Phase 6 에 "연결 폴더 미연결 — PDF 첨부 불가"를 명시한다.
   (docx 중간 파일은 연결 폴더로 복사하지 않는다.)

## Phase 5: 이메일 발송

**`references/email-sending.md` 를 읽고 절차를 그대로 따른다.** 요점:
- SMTP·Gmail MCP 초안 방식 금지. **Claude in Chrome 로그인된 Gmail 직접 발송만** 사용.
- **첨부는 PDF** — 연결 폴더(`D:\claudeCowork\...pdf`) Windows 경로로 첨부 (outputs·VM 경로는 거부됨).
- **받는사람(To)**: `namoobi@gmail.com` 단독.
- **숨은참조(BCC) — 실행 모드별 파일 (v3.4.3)**: Phase 0 에서 판정한 모드에 따라
  **예약** → `D:\claudeCowork\SECURITY\예약메일수신자.txt`, **일반** → `D:\claudeCowork\SECURITY\메일수신자.txt` 의 주소를 읽어 넣는다 (해당 파일 없으면 BCC 생략·보고에 명시).
- **`//` 주석 제외**: 라인 맨 앞(공백 허용)이 `//` 인 줄은 BCC 대상에서 제외. 읽기: `grep -vE '^[[:space:]]*//' <모드별 파일> | grep -oE '<email>'`. 유효 주소 0개면 To 만 발송·"BCC 0명(전부 주석)" 보고.
- BCC 주소는 비공개 정보 — 채팅·보고에 평문 노출 금지, **인원 수만** 보고 (예: "BCC 2명").
- 사용자가 자동발송을 승인한 세션에서는 추가 확인 없이 발송. 단, 로그인(비밀번호 입력)은 정책상 대신 수행 불가.
- 수신자 칩 클릭 금지, 검증은 screenshot/zoom 으로만 — 상세 함정 목록은 reference 참조.
- "메시지 전송됨" 확인 직후 완료시각을 기록한다: `TZ=Asia/Seoul date '+%Y-%m-%d %H:%M:%S'` + `date +%s`

## Phase 6: 결과 보고

소요시간 계산: `END=$(date +%s); START=$(cat "$WORK/nmr_start_epoch.txt"); echo $(( (END-START)/60 ))분 $(( (END-START)%60 ))초`

```
📋 글로벌 시황 보고서 발송 완료
실행 모드: 예약 / 일반  (수신자 파일: 예약메일수신자.txt / 메일수신자.txt)
생성: 글로벌금융시장_종합시황보고서_YYYYMMDD.pdf (NN KB)
수신: namoobi@gmail.com (To) + 숨은참조 N명 (주소 비공개)
수집: 뉴스 N / 증시 N / 원자재 N / 코인 N / 증권사 N+IB N
검증(Phase 3.5): blocking N건 / warnings N건  (v3.3.0)
[실행 시간]
- 시작: YYYY-MM-DD HH:MM:SS (KST)
- 완료(메일 발송 확인): YYYY-MM-DD HH:MM:SS (KST)
- 소요: M분 S초
[핵심 헤드라인 3개]
1~3. (top_news 상위 3개)
[추천 포트폴리오 톤]
- 공격형/중립형/안정형 1줄씩
```
연결 폴더 미연결로 PDF 를 연결 폴더에 두지 못해 첨부할 수 없었으면 그 사실도 함께 보고한다.

## 트러블슈팅 (요약)

| 증상 | 대처 |
|------|------|
| Chrome "Tabs can only be moved to and from normal windows" | 일반 크롬 창 없음 → 사용자에게 열어달라 요청 후 `tabs_context_mcp(createIfEmpty=true)` 재시도 |
| Gmail 로그인 안 됨 | 비밀번호 대리 입력 불가 → 사용자가 직접 로그인 후 재시도 |
| 작성창이 닫히고 초안만 남음 | `#drafts` 에서 초안 다시 열어 이어서 작성·발송 (email-sending.md) |
| 작성창이 최소화돼 "새 메일" 바만 보임 | 하단 "새 메일" 바 클릭해 펼친 뒤 진행 |
| 제목 입력이 누락됨 | 발송 전 screenshot 검증에서 제목 칸 확인, 비었으면 제목 칸 다시 클릭 후 입력 |
| Write/Edit "outside connected folders" | bash heredoc 으로 저장 |
| npm/cp 권한 오류 | /tmp 금지, outputs/nmr_build 에서 빌드 |
| 파일이 중간에 잘려 보임 (마운트 잘림) | 호스트 원본은 정상 — Read 도구로 읽으면 완전하다. build_report.js 는 Phase 0 자동복구(b64). 복사·패키징 후 크기·EOF 검증 필수 |
| 빌드 exit 0 인데 docx 미생성 | 스크립트 잘림 — Phase 0 EOF 검사·자동복구 수행 여부 확인 |
| 연결 폴더 미연결 | `request_cowork_directory`(D:\claudeCowork) 요청, 거부 시 outputs 진행 + Phase 6 에 명시 |
| 연결 폴더 cp "Permission denied" | 동일 파일명 존재 (덮어쓰기 차단) → `_HHMM` 접미사 새 파일명으로 저장 |
| 첨부 시 "only files the user has shared" | file_upload 는 `D:\claudeCowork\...pdf` Windows 경로만 허용 — outputs·`/sessions/...` VM 경로는 거부. PDF 를 연결 폴더에 두고 그 경로로 첨부 |
| 예약/일반 수신자 혼동 | Phase 0 모드 판정 결과로 결정 — 예약=예약메일수신자.txt, 일반=메일수신자.txt. 예약 작업 프롬프트에 `scheduled` 인자 전달 확인 |
| 서브에이전트 API 오류로 결과 누락 | nmr_*.json 존재 여부 확인 후 해당 에이전트만 재실행 |
| Chrome 차단 도메인(naver.com 등) | NaverSearch MCP / web_fetch 로 대체 |
| VNINDEX 데이터 부재 | VNM ETF (VanEck Vietnam) 로 대체 |
| 선물 티커 실패(PL=F 등) | current:null → 빌더가 "-" 렌더 |
| CoinInfo gainers/losers 간헐 오류 (429 등) | null/빈배열로 두고 진행 |
| 한글 폰트 깨짐 | 시스템에 맑은 고딕 설치 확인 |

## 부록 A: 5대 증권사 강점 사전 정의

| 증권사 | 핵심 강점 | 대표 채널 | 추천 투자자 |
|--------|-----------|-----------|-------------|
| 신한투자증권 | 자산배분 통합 (주식·채권·원자재·대안), 매크로 일관성 | 카카오채널 '쏠쏠한 리포트', 신한 알파 앱 | 장기 자산배분형 |
| 미래에셋증권 | 12개국 현지법인, ETF 특화, 신흥국(베트남·인도·인니) | m.Global 앱, 디지털리서치 숏폼 | 해외주식·ETF·신흥국 |
| 삼성증권 | SGR 독립 싱크탱크, 파생·선물, SPOT 코멘트, POP TV | mPOP 앱, 유튜브 '글로벌 마켓토크' | 단기 트레이더·매크로 |
| 한국투자증권 | JP모간·골드만삭스 IB 리포트 독점, 중국 국태해통 | 한투 앱 '독점 글로벌 리서치' | 기관 수준 분석 선호·중국 |
| 키움증권 | 텔레그램 실시간, 글로벌 ETF 전략, 중국·신흥국 섹션 | 텔레그램 t.me/s/KiwoomResearch | ETF·속보성 중시 |

복수 구독 전략: 자산배분 큰 그림(신한) + 해외 종목(한투 IB) + ETF(키움) + 신흥국(미래에셋) 조합.

## 부록 B: 해외 주요 IB 5사 강점 사전 정의 (무료 공개 채널)

| 기관 | 핵심 강점 | 무료 공개 채널 | 갱신 주기 |
|------|-----------|----------------|-----------|
| UBS | CIO House View — 자산배분·일일 시황 (시황보고서에 최적) | ubs.com/global/en/wealthmanagement/insights (CIO Daily) | 매일 |
| Goldman Sachs | 매크로·원자재·경제전망 | goldmansachs.com/insights | 수시 |
| J.P. Morgan | 글로벌 전략·시장 전망 | jpmorgan.com/insights/global-research | 수시 |
| Morgan Stanley | 미국주식 전략 (Thoughts on the Market) | morganstanley.com/insights | 주간 |
| BlackRock | ETF·자산배분 (BII Weekly Commentary, 매주 월요일) | blackrock.com/corporate/insights/blackrock-investment-institute | 주간 |

수집 시 주의:
- **원문 리포트(목표주가·종목분석 PDF)는 고객 전용** — 공개 Insights 페이지와 언론 보도(Reuters/CNBC 등, 예: "Goldman S&P target" 검색)로 하우스 뷰 핵심 메시지만 수집한다.
- 보조 수단: UsStockInfo MCP `get_recommendations`(종목별 월가 컨센서스), Bigdata.com MCP `bigdata_search`(있으면).
