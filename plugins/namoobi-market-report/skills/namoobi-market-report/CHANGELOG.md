# Namoobi Market Report — 변경이력 (CHANGELOG)

## v3.55.0 (plugin 1.22.0, 2026-07-11) — KRX OPEN API 도입: 3.1.13 KOSPI200 대폭 보강 + 국내 시장데이터 웹서치 대체
**배경** — 3.1.13(파생 포지셔닝 선행신호)에서 KOSPI200만 지표가 빈약했다(현물=KODEX ETF 대용, 옵션 PCR/IV스큐/GEX는 값 붕괴). KRX OPEN API(openapi.krx.co.kr) 승인으로 25개 엔드포인트를 전수 검증(전부 정상, 1년 백필 가능)하고 소스를 개편했다.

### 신규 모듈 (`deriv_signals/`)
- **`krx_openapi.py`** — KRX OPEN API 공용 클라이언트. `http://data-dbg.krx.co.kr/svc/apis/{cat}/{api}?basDd=YYYYMMDD`, 헤더 `AUTH_KEY`, 응답 루트 `OutBlock_1`. 인증키는 `KRX_API_KEY` → 연결폴더 `SECURITY/openapi.krx.co.kr.txt` → `secrets.env` 순 자동탐색(**값 미출력**). 일자별 gzip 디스크 캐시 → 1년 백필은 최초 1회만 네트워크, 이후 신규 영업일만 조회.
- **`ingest_krx_open.py`** — 【1차·무로그인】 KOSPI200 수집: ① 현물=`idx/kospi_dd_trd` '코스피 200' 공식 종가 ② 베이시스=`drv/fut_bydd_trd` 최근월물(코스피200/미니코스피 중 만기 최근·OI 최대, `SPOT_PRC` 대비 bp) ③ 미결제=`ACC_OPNINT_QTY` 합계 ④ **VKOSPI**=`idx/drvprod_dd_trd` '코스피 200 변동성지수'.
- **`ingest_krx_web.py`** — 【2차·선택】 data.krx.co.kr `getJsonData.cmd`(bld `dbms/MDC/STAT/standard/MDCSTAT134xx`)에서 **괴리율(시장−이론 베이시스 → 캐리 왜곡 제거)·공식 IV·공식 P/C Ratio** 보강. **로그인 세션 쿠키가 있을 때만** 동작(`KRX_COOKIE` 또는 `SECURITY/krx_cookie.txt`), 없거나 만료면 **조용히 skip**(완전 비차단). **비밀번호는 취급하지 않는다.**
- **`krx_market_snapshot.py`** — 【웹서치 대체】 `nmr_krx_market.json` 생성: 코스피·코스닥·코스피200 종가/등락률, VKOSPI, 코스피200 섹터 등락 상·하위, 국고채 종가수익률, KRX 금현물, ETF 거래대금 상위+괴리율(NAV 대비).

### 지표 추가 — VKOSPI
- `INDICATOR_META.vkospi`(expected=**−1**, 컨트라리안: 공포 극단 → 반등), `IND_COLS`·`indicators_daily.vkospi`·`zscores_daily.z_vkospi`·`kr_derivatives_daily.vkospi` 추가. export_snapshot 에 "VKOSPI (변동성지수)" 행 + 활성신호 태그 추가.
- ⚠️ **KOSPI200 옵션체인은 KRX 공식 데이터에서도 붕괴** — 최근월 행사가 사다리(545~997.5)가 현물(1,219.62)을 커버하지 못해 PCR 100 초과 등 비정상값 발생(2026-07-02 실측). **PCR·IV스큐·GEX 를 KOSPI200에서 산출하지 않고 VKOSPI 로 대체**한다(소스를 바꿔도 해결 불가한 데이터 특성).
- 1년 백필 실측(281 영업일): VKOSPI z≤−1.5 신호 9건 → **5일 후 평균 +3.04%, 적중률 89%**. 베이시스 z≥+1.5 29건 → +1.52%, 68%.

### 소스 전략 (3단)
1차 KRX OPEN API(무로그인·안정) → 2차 data.krx(세션 있을 때만 정밀도 보강) → 폴백 네이버/data.go.kr(1차 실패 시). `ingest_krx.py` 가 디스패처. 외국인·기관 **투자자별 매매동향은 KRX OPEN API 미제공** → 네이버 유지.

### 버그 수정
- **`db.migrate()` 신설** — 구버전 DB에 `options_daily.gex`/`indicators_daily.gex`/`z_gex` 등이 없어 `KeyError: 'gex'`·`no column named gex` 로 죽던 문제 수정(ALTER TABLE 멱등 마이그레이션). `analyze.build_indicators` 도 컬럼 부재 방어.

### 문서
- SKILL.md: 3.1.13 소스 개편 명세, **국내 데이터 우선순위 규칙**(KRX 공식값 > MCP/스크래핑 > 웹서치; 글로벌 지표·투자자별 수급은 KRX 범위 밖), Phase 1 런처가 `nmr_krx_market.json` 도 생성.

## v3.54.0 (plugin 1.21.0, 2026-07-09) — 3.2.4/3.2.5 KRX 증시 Brief·공매도 데일리 브리프 신설 (DB화)
- **신규 `scripts/fetch_krx_brief.py`**: open.krx.co.kr 시장동향>종합시황 게시판에서 최신 'KRX 증시 Brief'·'공매도 데일리 브리프' PDF를 OTP 체인(GenerateOTP→OPN99000001→file.krx.co.kr/download.jspx)으로 다운로드(쿠키·Chrome 불필요, 2026-07-09 실측) → pdftocairo 페이지별 PNG 캡쳐(-r110).
- **DB화(회차 마커=게시글 att_seq)**: `_market_report_data/krx_brief/<key>_<att_seq>/`(pdf+PNG 영구 저장, 항목별 최근 5회차 유지)+`db/krx_brief.json`. **동일 회차면 다운로드·캡쳐 생략·저장본 재사용**, 수집 실패 시 직전 회차 폴백(stale_note 표기).
- 빌더 `renderKoreaExtras` 끝에 3.2.4/3.2.5 렌더(표준캡션+제목·등록일+페이지 캡쳐+출처, 항목 데이터 없으면 자동 생략·비차단) — 문서번호 충돌 없음(테마=3.2.3, HBM=3.1.9). merge `m['krx_brief']`(LCF→DB 폴백).
- 게이트: builder validate [차트누락] + verify **req22**(데이터 있는데 캡쳐 PNG 없으면 발송 차단 / 데이터 없으면 warning / DB 폴백 사용 시 warning).
- SKILL.md: 핵심 수집 규칙에 3.2.4/3.2.5 블록 추가, Phase 1 bash 병렬 목록에 fetch_krx_brief.py 추가, 구번호 라벨 정리(3.2.4 테마→3.2.3, 3.2.5 HBM→3.1.9 — 문서 실번호와 일치화).

## v3.53.0 (plugin 1.20.0, 2026-07-07) — FRED 수집 API 키 직접 호출로 전환
- **신규 `scripts/nmr_fred.py`**(공용 헬퍼): FRED API(`api.stlouisfed.org`) 키 직접 호출 우선 → `fredgraph.csv` 폴백. 키=연결폴더 `SECURITY/secrets.env` 의 `FRED_API_KEY`(환경변수 우선). sandbox curl 도달 실측 확인(단건 ~0.4s, CSV ~0.6s).
- `fetch_macro.py`(물가·금리·고용 15개 시리즈)·`fetch_kr.py`(HY OAS — API→equibles→영구캐시 순)·`gen_curve_1y.py`(T10Y2Y) 가 헬퍼 사용. Chrome 동일출처 CSV·미러 의존 제거(폴백으로만 유지).
- ⚠️ **BAMLH0A0HYM2 등 ICE BofA 시리즈의 약 3년 상한은 CSV 방식이 아니라 FRED 라이선스 제한 — API 키로도 동일**(2026-07-07 실측: observation_start=1996 지정에도 시작일 3년 전·793개). 전환 목적은 구간 확대가 아닌 속도·안정성.
- SKILL.md(3.1·3.3.3·Phase1)·references/agents.md(출처·샌드박스 도달 규칙) 갱신 — "샌드박스 FRED 불가" 문구를 실측 결과로 교체.

## v3.52.1 (plugin 1.19.1, 2026-07-05) — [부록C] 43→46종 확장 (부록D 관계도와 동기화)
- fetch_appc.py ROWS +3: ORCL(빅테크 수요처)·이수페타시스 007660.KS(후공정/패키징)·AMKR(후공정/패키징) → 46종(미 31·일 4·한 11), ①빅테크5 ⑦후공정8.
- verify [AppC] 게이트 43→46, SKILL.md 부록C 블록 갱신. 부록D 관계도(46종)와 구성 일치.
- 미리보기=global_market_report_20260705_부록C46종_부록D_재빌드.docx (report_data_20260705.json 재빌드).

## v3.52.0 (plugin 1.19.0, 2026-07-05) — [부록D] AI 반도체 밸류체인 관계도(해자 지도) 신설
- **[부록D] 신설**(부록C 뒤): 부록C 종목이 '왜 중요한지'를 6단 흐름(수요 빅테크→설계 팹리스·EDA·인터커넥트→장비·소재→제조 파운드리·메모리→후공정→전력 인프라)으로 잇고 종목별 해자 한 줄 + 배지(파랑=독점·준독점 / 황색=과점·복점·양강)를 단 관계도 이미지 3장. 페이지당 1장 삽입.
- **구성 46종** = 부록C 43종 + 확장 3종(ORCL·이수페타시스 007660·AMKR — 사용자 지정). Advantest·Disco 는 표(부록C)에선 후공정, 관계도에선 '장비·소재' 층에 배치(공급자 관점).
- **구현**: 정적 자산 방식 — `assets/gen_appd_valuechain.py`(weasyprint+pdftocairo+Noto Sans CJK, 종목 변경 시에만 재실행)가 `assets/appd_valuechain.html`(미리보기)+`appd_valuechain_{1..3}.png`(1680px 폭, 2x) 생성. 빌더 `renderAppendixD`: assets find→IEND 무결성 검증→마운트 잘림 시 `git show` 폴백→charts/ 복사→삽입, TOC에 부록D 추가. 이미지 없으면 자동 생략(비차단). 매일 실행 비용 0(수집·차트·verify 변경 없음).
- 미리보기=global_market_report_20260705_1637_추가미리보기4_부록D_관계도.docx.

## v3.51.0 (plugin 1.18.0, 2026-07-05) — [부록C] AI 반도체 밸류체인 43종 신설 (글로벌 개별종목)
- **[부록C] 신설**(부록B 뒤): AI 반도체 흐름을 수요→설계→제조→소재·장비→후공정→전력 인프라로 잇는 글로벌 개별종목 43종(미 29·일 4·한 10) 추세표 — ①빅테크 수요처(GOOGL·MSFT·AMZN·META) ②팹리스/가속기(NVDA·AMD·AVGO·MRVL·ARM·ANET·CRDO·ALAB) ③파운드리/제조(TSM·삼성전자·INTC) ④메모리(MU·SK하이닉스) ⑤소재/부품(신에츠·SUMCO) ⑥전공정 장비(ASML·AMAT·LRCX·KLAC·TEL·SNPS·CDNS) ⑦후공정/패키징(Advantest·Disco·한미반도체·ISC·리노공업·대덕전자) ⑧데이터센터 전력·인프라(VRT·ETN·GEV·CEG·PWR·NVT·VST·LS일렉·효성중공업·HD현대일렉·두산에너빌리티).
- **구현**: `scripts/fetch_appc.py` 신설(Phase 1 bash 병렬, 야후 일봉 2y→nmr_appc.json/nmr_appc_series.json) → merge `m['appendix_c']` → 빌더 `renderAppendixC`(TOC 부록C 추가, 통화 접두 $/¥/₩, 데이터 없으면 자동 생략) → gen_rest_charts `spark_c_*` 스파크.
- **게이트**: verify [AppC] — 43종 미달·스파크 커버리지·데이터 부재 warning.
- **헤지 검토 반영**(사용자 승인): 테스트·그라인더 공백=Advantest(6857.T)·Disco(6146.T), 인터커넥트 짝=ALAB, 웨이퍼 짝=SUMCO(3436.T) 추가(39→43종). 미리보기=global_market_report_20260705_1637_추가미리보기3_부록C_43종.docx.

## v3.50.1 (plugin 1.17.1, 2026-07-05) — 3.2.3 테마 3종 추가: 건설기계·항공·정유 (종전 수혜 트리오, 12종)
- THEME_ORDER 12종: 기존 9종 + 건설기계(KODEX 기계장비 102960 프록시 — HD현대건설기계·두산밥캣 등 기계/장비) · 항공(TIGER 여행레저 228800 프록시 — 대한항공 등 항공+여행/레저) · 정유(KODEX 에너지화학 117460 프록시 — S-Oil·SK이노베이션 등 에너지/화학). 전용 ETF 부재로 섹터 프록시 사용(desc 명시).
- fetch_semi.py themes_etf 3종 추가(10년 월봉+일봉 자동 수집·theme_건설기계/항공/정유.png 차트 자동 생성) — 에이전트 미제공 시 merge.py 폴백(수익률 기반 방향)으로 행 보장.
- 게이트: verify_report.js req3 테마 <12 차단으로 상향.

## v3.50.0 (plugin 1.17.0, 2026-07-05) — 3.2.3 건설 테마 + 3.4.1 미국상장 아시아 ETF 15종 국가병합 + 3.6/3.7 북미&중남미·호주&중동 신설
- **3.2.3 건설 테마 추가(9종)**: THEME_ORDER 에 '건설'(대표 ETF KODEX 건설 117700) — fetch_semi.py 시계열(10년 월봉+일봉), 에이전트 미제공 시 merge.py 가 수익률 기반 방향(▲/▼/■) 폴백 행 생성(조용한 누락 방지).
- **3.4.1 국가병합**: 미국거래소 상장 아시아 ETF 15종(MCHI·FXI·KWEB·EWH / EWJ·DXJ / EWT / INDA / VNM·VNAM / EIDO·EPHE·EWM·THD·EWS)을 같은 나라 그룹에 병합(국내상장 뒤·달러 $ 표기·ccy 필드), ⑦ 동남아(sea) 그룹 신설 — 총 29종(한국 14+미국 15). fetch_asia_etf.py 미국 티커 직수집(Daum 폴백 없음)·한국/미국 분리 평균 comment.
- **3.6/3.7 신설**: 3.6 북미&중남미(EWW·EWZ·EWC) / 3.7 호주&중동(EWA·KSA·UAE·QAT) — fetch_us.py AMER_ETF/AUME_ETF(EUETF 패턴) → nmr_amer_etf.json/nmr_aume_etf.json → merge americas_etfs/aume_etfs → 빌더 renderAmericasEtfs/renderAumeEtfs(3.5.1 뒤, 데이터 없으면 자동 생략).
- **게이트(verify_report.js)**: req3 테마 9행(<9 차단) · 3.4.1 sea 그룹 포함 스파크 커버리지 + 29종 미달 warning · 3.6/3.7 항목수(3/4)·스파크 커버리지 warning.
- **미리보기**: global_market_report_20260705_1637_추가미리보기2.docx (사용자 승인).

## v3.49.0 — 3.1 주요지표 재배열: ①~④ 그룹 소제목(번호 없는 소제목, 방법 B) + 순차 번호 3.1.1~3.1.13 (2026-07-05)
- **구조**: 거시→실적→섹터→수급·심리 흐름으로 재배열. ① 매크로(정책·경기)=3.1.1 금리 / 3.1.2 물가 / 3.1.3 고용 / 3.1.4 OECD CLI / 3.1.5 순환변동치 · ② 기업 실적=3.1.6 FactSet / 3.1.7 M7 실적 전망 / 3.1.8 CAPEX · ③ 반도체·한국 연결고리=3.1.9 메모리+HBM / 3.1.10 관세청 수출 / 3.1.11 반도체 사이클→코스피 · ④ 수급·심리(선행신호)=3.1.12 심리·자금흐름 / 3.1.13 파생 포지셔닝.
- **구번호 대응**: 舊3.1.4심리→3.1.12 · 舊3.1.5FactSet→3.1.6 · 舊3.1.6CAPEX→3.1.8 · 舊3.1.7A→3.1.9 · 舊3.1.7B→3.1.11 · 舊3.1.8CLI→3.1.4 · 舊3.1.9순환→3.1.5 · 舊3.1.20M7→3.1.7 · 舊3.1.21파생→3.1.13. (3.1.1~3.1.3·3.1.10 불변)
- **빌더**: `build_report.js` — `gh()` 그룹 소제목 헬퍼 신설(좌측 파란 바+연한 음영, 개요 번호 밖·목차 미포함), `renderMacroIndicators` 렌더 순서 재배치(심리 블록을 ④로 이동, OECD CLI·순환변동치를 고용 뒤로).
- **게이트**: `verify_report.js` v3.6.33 — 섹션 라벨 신번호로 정정(req19 CLI=3.1.4, req20 FactSet=3.1.6, req21 M7=3.1.7, req2 순환변동치=3.1.5) + 종전 구버전 잔존 라벨 정정(req1=3.2.1 코스피 캔들, req3~5=3.2.3 테마·반도체, req6=3.1.8 CAPEX, req7=3.1.1 점도표, req15=3.1.1 HY). 차단/경고 로직 자체는 불변(번호 라벨만 정정).
- **문서**: SKILL.md에 3.1 구성 정의(그룹 구조+구번호 대응표) 추가, references/agents.md·data-schema.md·db-architecture.md·merge.py·gen_cli_chart.py·gen_hbm_dashboard.py·gen_leading_chart.py 주석 라벨 동기화.

## v3.47.0 (plugin 1.16.0) — 3.1.21 파생시장 포지셔닝 기반 현물 선행신호 분석 신설 (매일)
- **신설 3.1.21**: 3.1.20 뒤. KOSPI200·S&P500·Nasdaq100의 선물 베이시스·순포지션/수급(美 COT / 韓 외국인·기관)·풋콜비율·IV스큐·딜러감마(GEX)를 z-score(60거래일)로 표준화한 스냅샷(① 지수현황 ② 값·z 매트릭스 ③ 활성신호 ④ 시장해석 ⑤ 종합).
- **파이프라인**: `deriv_signals/`(daily_update.py→DB, export_snapshot.py→nmr_deriv_positioning.json) → merge `markets.deriv_positioning` → 빌더 `renderDerivPositioning`. 미수집 시 내장 DERIV_POS_DEFAULT 비차단. 데이터=yfinance·CFTC COT·네이버 수급·data.go.kr(파생·지수).
- **선행성 검증**: 신호일→1/3/5일 현물수익률 hit·IC (예: 외국인 순매수 z≥+1.5 → 5일 +5.83%·적중 87%, KOSPI200 베이시스 z≥+1.5 → +3.77%·78%).

## v3.46.0 (plugin 1.15.0, 2026-07-04) — 3.1.20 미국 빅테크(M7) 실적 전망 신설 (가이던스·애널리스트 추정치 변화 시장 신호, 매일)
- **신설 3.1.20**: 3.1.10 뒤에 미국 빅테크 7종목(AAPL·MSFT·NVDA·GOOGL·AMZN·META·TSLA) 실적 전망 표. 컬럼=기업·현재가/52주·컨센서스·평균목표주가/여력·목표주가 리비전(1M/1Q/1Y)·최근 가이던스·신호. 신호 색=긍정(초록)/경계(주황)/위험(빨강)/중립(회색).
- **관점**: 가이던스·이익 추정치/목표주가 리비전을 섹터·시장 하락의 선행·직접 신호로 읽음(추정치 하향·목표주가 컷=경계/위험). 데이터 소스=회사 실적발표·Refinitiv/LSEG I/B/E/S·Bloomberg·FactSet·증권사 리포트.
- **매일 갱신**: 시세·평균목표주가·투자의견 분포·목표주가 리비전·등급변경은 매 실행 실측(FMP `analyst`), 가이던스·연간 추정치는 실적 발표 시 WebSearch.
- **구현**: `build_report.js renderM7Outlook`(3.1.10 뒤) + 내장 스냅샷(M7_OUTLOOK_DEFAULT, 미수집 시 비차단) / `M7OutlookAgent`→`nmr_m7.json`→`merge.py markets.m7_outlook` 라이브 오버라이드 / `references/agents.md`·`data-schema.md` 스펙.

## v3.45.0 (plugin 1.14.0, 2026-07-04) — 3.1.7B 반도체 사이클→코스피 점검판 신설 (DB화) · 3.1.7→3.1.7A 개명
- **개명**: 기존 **3.1.7 반도체 주가 체크용 메모리+HBM 지표** → **3.1.7A** (내용·차트·데이터 불변, `renderHBM` 헤딩만 변경).
- **신설**: **3.1.7B 반도체 사이클 → 코스피 점검판**(본문+신호표, **차트 없음**·비차단). 목표=반도체 업황(메모리 가격·재고·주문·CAPEX)/업종 사이클(재고·ASP→업체 실적 선행)/반도체 사이클 하강의 코스피 핵심 대형주(삼성전자·SK하이닉스) 압박/확인법(메모리업체 발표·시장조사 보고서)을 한 화면에 점검.
- **구성**: 핵심 한 줄 · 읽는 방법 · 지금 봐야 할 조기 경보 신호 · 메모리 사이클 조기경보 점검(3신호표=① 재고주수 ② DRAM 계약가 상승률 QoQ ③ SK하이닉스 CAPEX 증가율 YoY; 현재값·판정·경보 임계선·비고) · 읽는 방법 · 출처. 판정 색=안전(초록)/주의·둔화(주황)/경보·하강(빨강). **2개 이상 경보면 고점·하강 신호**.
- **DB화**: `db/semi_cycle.json` 시드(2026-07-04). 매 실행(매일) 저렴한 변동체크 — 변동 시에만 `nmr_semi_cycle.json` 생성, 없으면 DB 재사용(표준캡션). merge `_ndb.sync('semi_cycle')`(marker=asof) → `m.semi_cycle` → build `renderSemiCycle`(3.1.7A 뒤·3.1.8 앞). 데이터 없으면 자동 생략.
- 파일: `build_report.js`(renderSemiCycle 신설·3.1.7A 개명), `merge.py`(semi_cycle DB 동기화), `SKILL.md`·`references/{db-architecture,data-schema,agents}.md` 갱신. verify 게이트 영향 없음(신규 섹션은 차트 비의존).

## v3.44.0 (plugin 1.13.0, 2026-07-04) — 3.1.10 관세청 수출 주요품목별 10일 단위 잠정치 통계 신설 (DB화)
- **신설**: data.go.kr 관세청 오픈API(15157908, `prlstMmUtPrviExpAcrs`)로 2016-01~ 전 기간 10일 누계(1~10/1~20/1~말일) 수출액(11개 품목, 천 달러)을 `db/customs.json` 로 DB화(378행 시드).
- **매일 변경체크**(최근 4개월 해시 마커): 신규 순보/현행화 시에만 전체 백필·갱신, 변경없으면 DB·차트 그대로 재사용(표준캡션). 공표 11/21/익월1.
- 파이프라인: `fetch_customs.py`(stdlib, Phase 1 bash 병렬) → `nmr_customs.json`(변경시) → merge `_ndb.sync('customs')` → build_report `renderCustoms`(최근월 요약표+차트 2종). 차트 `gen_customs_chart.py` → `charts/수출_전체_24개월.png`·`charts/수출_반도체_24개월.png`. verify 게이트 추가.

## v3.43.1 (plugin 1.12.1, 2026-07-03) — 3.1.8↔3.1.9 순서 스왑
- **3.1.8 = OECD 경기선행지수(CLI)** (더 앞단의 "방향 신호") → **3.1.9 = 통계청 선행종합지수 순환변동치** ("확인 신호") 순으로 변경. 제목 번호·상호참조·validate/verify 문구 일괄 갱신 (기능·DB·차트 불변).

## v3.43.0 (plugin 1.12.0, 2026-07-03) — 3.1.9 OECD 경기선행지수(CLI) 신설 + 3.1.8 구성항목·주식선행 관점 명시
- **3.1.9 신설**: OECD CLI(KOSIS DT_2STES045) 통합 DB화(`db/oecd_cli.json`, 시드 2022.01~2026.04 × 17개국). 매 실행 메인세션 Chrome 배치에 KOSIS 자료갱신일 체크 1탭 추가(`nmr_db.py check oecd_cli`) — reuse면 DB 재사용, due면 전체기간 시계열 재추출(`nmr_oecd_cli.json`)→merge 가 DB 갱신.
- **차트**: `gen_cli_chart.py`(신규, Phase 1.5 8종) → `charts/oecd_cli.png` — 전 국가 통합 1장(X축=월별 총기간, Y축=지수(진폭조정), 기준선 100, 대한민국 굵은 선, 우측 국가명·최신값 라벨). 입력=신규 스크랩 또는 DB 폴백(항상 생성 가능).
- **빌더**: `renderOecdCli`(3.1.8 뒤) — 표준캡션+통합차트+고정 설명블록(정의/구성요소/해석방법(기준점100)/한계). merge.py `_ndb.sync('oecd_cli')` 연동.
- **게이트**: verify_report.js req19(데이터 있는데 차트 없으면 차단·데이터 없으면 warning), build validate 경고 추가.
- **3.1.8 보강**: ① 구성항목(재고순환지표(제조업)·기계류내수출하지수·건설수주액(실질)·소비자기대지수·구인구직비율·장단기금리차·코스피지수·수출입물가비율·순상품교역조건 등) ② 주식 선행 관점 — OECD CLI(3.1.9)=더 앞단의 "방향 신호", 통계청 선행종합지수 순환변동치=국내 경기 데이터로 다듬은 "확인 신호" 문구 추가.

## v3.42.0 (plugin 1.11.0, 2026-07-02) — req1~4 근본수정: 2.3 빅테크이벤트 hoist·물가/고용 발표날짜 날짜화·release 기관명 정화·HBM EPS/PER 필드단위 carry-forward
- **req1**: NewsAgent 가 bigtech_events 를 중첩 `news` 키 아래 저장 → merge 가 상위로 hoist(2.3 섹션 누락 재발방지).
- **req2/req3**: 물가·고용 발표날짜에 기관명(BLS·BEA 등)이 들어차 nmr_reasons(빈값만 채움)를 우회하던 문제 → `_bad_release` 로 기관명도 교체 + merge 가 DB 저장 전 정화. 물가표는 INFL_REL 로 실제 발표일(CPI 06-10·PPI 06-11·PCE 06-26) 표기.
- **req4**: HBMAgent 불완전 수집이 영구본을 통째 덮어써 2027E/2028E/PER 유실 → merge 에 필드단위 carry-forward(순수숫자만 채택·결측은 db/hbm_eps.json 보완).


## v3.40.0 (plugin 1.10.0, 2026-06-28) — 유지보수: 버전 unfreeze·SKILL.md 구조 정상화·release 자동화
- **버전 unfreeze (핵심)**: plugin.json 1.9.0→**1.10.0**, marketplace.json 1.7.19→**1.10.0** 동시 bump. v3.39.x 의 `nmr_selfcheck` 가 '설치본 STALE' 를 감지해도 advertised 버전이 안 올라가 '플러그인 업데이트'가 no-op 이던 마지막 고리를 해소(설치본이 계속 1.9.0 으로 실행되던 근본원인).
- **SKILL.md frontmatter 최상단 복원**: 매 릴리스마다 누적되어 YAML frontmatter 를 24행 아래로 밀어내던 `> **vX**` 배너 전량(v3.39.0~v3.16.0)을 CHANGELOG 로 이전(런타임 미로딩) → 트리거 메타데이터 정상화 + 매 실행 토큰↓.
- **plugin.json·marketplace.json description 슬림화**: changelog 박제 → 한 줄 + CHANGELOG 포인터.
- **release.sh 추가**: plugin.json·marketplace.json·SKILL.md 헤더 버전을 한 번에 bump + CHANGELOG 항목 + commit + `reset --hard` + push → 버전 freeze 재발 방지.
- (동작·데이터 스키마·빌더·nmr_selfcheck 로직 불변 — 배포 파이프라인·문서 구조 정비만.)

### (SKILL.md 배너 보관 — v3.39.0 ~ v3.16.0; v3.40.0 에서 이전)

> **v3.39.0 (2026-06-26) — 재발방지 3종(수정이 새 실행에 반영되도록).** ① **설치본 자가점검** `scripts/nmr_selfcheck.py` 를 Phase 0 에서 실행: 설치본 스크립트가 GitHub HEAD 와 다르면(플러그인 미업데이트) 중단·사용자 안내. ② **커밋 후 작업트리 동기화**(`git reset --hard HEAD`) 규칙 명문화: mount-safe 커밋이 디스크를 옛 파일로 남겨 플러그인이 stale 설치되던 근본원인 차단. ③ **휘발 데이터 carry-forward**: merge.py `LCF()` 가 nmr_hbm/nmr_capex 를 WORK 없으면 연결폴더 `_market_report_data/` 영구본에서 로드하고 사용분을 저장 → 수집 실패해도 내장 예시로 떨어지지 않고 직전 조사값 유지(HBMAgent·CapexAgent 도 영구본을 베이스로 갱신).
> **v3.38.0 (2026-06-26) — fetch_us.py glob import 버그픽스.** 미국 시세 수집기가 glob.glob 사용하면서 import 누락(NameError) → `import glob` 추가. (이번 세션 누적 반영 동기화)
> **v3.37.0 (2026-06-26) — 3.1.7 HBM 대시보드 주기·갱신일 명시 + 최신화.** 6개 차트 캡션에 "월별/분기 추정 · 최종 갱신일(출처)" 라벨 추가. nmr_hbm.json 최신 웹리서치 반영: HBM 점유율(2025 SK57/삼성22/마이크론20%)·HBM3E/HBM4 단가(36GB →360, 48GB ; TrendForce/Counterpoint/Digitimes). 가격·출하·시장규모는 무료 실시간 부재로 월별/분기 추정 유지(라벨 표기). 3사 EPS/PER 표는 FMP+컨센서스 실측.
> **v3.36.0 (2026-06-26) — 3.1.6 차트 가독성.** CAPEX 스택·FCF 차트 범례(회사명)를 플롯 밖 상단 행으로 이동(선과 겹침 제거), 제목 pad 확대, FCF 세로 여백·높이 확대, 선 위를 덮던 빨간 주석 제거.
> **v3.35.0 (2026-06-26) — 3.1.6 CAPEX 표·차트 완전 데이터연동.** 표를 기업별 **4행**(CAPEX / 매출 / Capex·매출 비율 / FCF)으로 확장하고, 두 차트(스택+비율선, FCF)를 모두 이 표값(`bigtech_capex.rows`)으로 구동(하드코딩 매출/FCF 제거). 매출=FMP income(실측 2024~25)+애널리스트 컨센서스(2026~29E), FCF=FMP cashflow freeCashFlow(실측)+(직전 영업CF×매출성장−CAPEX) 추정, Capex/매출=CAPEX÷매출. ORCL 은 FMP 플랜 제한 시 공개치·추정.
> **v3.34.0 (2026-06-26) — 3.1.6 CAPEX 표·차트 일치.** gen_capex_chart.py 가 표(bigtech_capex.rows, y2024~y2029)를 막대 CAPEX 로 직접 사용(2023만 내장 유지) → 표와 그래프 수치 완전 일치(예: 2026E MSFT=GOOGL=190 이면 막대 높이 동일). 기존엔 내장 기본값으로 그려 표와 달랐음. 차트 제목 비중%는 ratio 최대값으로 동적 표기.
> **v3.33.0 (2026-06-26) — 3.1.5 검증된 출처 링크 + 풀날짜.** 표의 '조사 출처·링크'는 실제 데이터가 보이는 1차 출처로 연결한다. **S&P500=FactSet Earnings Insight 주간 PDF**(URL=`EarningsInsight_MMDDYY.pdf`, eps_date에서 자동 구성 — 해당 PDF에 그 날짜의 forward 12M P/E·지수 수록, 검증됨; 041026만 'A' 접미사). **KOSPI=출처 증권사 리포트 PDF**(대신 이경민 주간전략 등 — 선행EPS·PER 수치 명시). DB는 풀날짜(eps_date) 키로 dedup(월 단위 금지 — 같은 달 복수 시점 허용). EPS·PER 둘 다 조사되면 지수=EPS×PER(출처와 일치), 한쪽만이면 해당일 일일지수로 보정. MacroAgent 는 spx_fwd/kospi_fwd 에 **asof=풀날짜(YYYY-MM-DD)·link=출처 URL** 을 반드시 담는다(월만 있으면 누적 제외).
> **v3.32.0 (2026-06-26) — 3.1.5 DB schema2 + 일일지수 통합차트 + 최신5 표.** DB 점 스키마: `{eps,eps_date,per,per_date,idx,idx_date,src,link}` (날짜시점 지수=실측 일일종가). `fetch_idx_daily.py` 가 ^GSPC·^KS11 2년 일봉을 `nmr_idx_daily.json` 으로 수집. `nmr_fwd_accum.py` 는 매 실행 MacroAgent 스냅샷을 월키로 upsert하며 **EPS or PER 한쪽만 조사되면 해당일 일일지수로 보정(EPS×PER=지수)**. `gen_fwd3.py` 통합차트=**지수 일일선(실측)+선행EPS·PER 조사시점 포인트**(3중 Y축). 빌더는 각 지수마다 **최신 5건 표**(선행EPS·날짜 | 선행PER·날짜 | 날짜시점 지수 | 조사 출처·링크 ExternalHyperlink) 렌더.
> **v3.31.0 (2026-06-26) — 섹션 재배치.** 3.2.3 경기선행지수 순환변동치 → **3.1.8**(매크로 대시보드 말미, renderKoreaLeading)로 이동. 기존 3.2.4 순환매 테마별 현황 → **3.2.3**으로 번호 변경. 3.1.5 캡션을 단일 통합차트(3중 Y축)에 맞게 수정.
> **v3.30.0 (2026-06-26) — 3.1.5 선행EPS/PER DB 누적 + 단일 통합차트.** 조사된 12M 선행EPS·PER 을 `_market_report_data/nmr_fwd_history.json`(DB)에 월(YYYY-MM) 키로 저장, 매 실행 신규 검색분을 병합(`nmr_fwd_accum.py` = 시리즈 파일 + MacroAgent 스냅샷 harvest) → 시계열이 매일 향상. 차트(`gen_fwd3.py`)는 DB 를 읽어 **지수/12M선행EPS/선행PER 를 하나의 그래프(3중 Y축)** 로 표시(지수=선행EPS×선행PER 복원 → 전구간 가시, Y축 패딩). S&P500=FactSet · KOSPI=FnGuide. 판단기준 박스 포함. (구 `gen_fwd_eps.py`·3단 분리 폐기.)
> **v3.29.0 (2026-06-26) — 3.1.5 3단 시계열.** 지수/12M 선행EPS/선행PER 3단 공유축 차트(gen_fwd3.py): S&P500=FactSet 14포인트(월말, 동일 산식), KOSPI=FnGuide 컨센서스 6포인트(증권사 리포트 인용). 매 실행 월말 스냅샷 nmr_fwd_history.json 누적(12+ 자동 충족). 판단 기준 박스(EPS·PER 4국면) 추가.
> **v3.28.0 (2026-06-26) — 3.1.5 선행EPS 오버레이.** S&P500=FactSet(지수+12M 선행EPS 앵커+선행P/E), KOSPI=FnGuide/연합인포맥스 컨센서스(지수+선행EPS+선행P/E, 최신시점 위주). 뉴스 출처 금지·공인자료만. nmr_fwd.json → gen_macro2 오버레이 차트.
> **v3.27.0 (2026-06-26) — 3.1.3 고용 주식관점 중요도순 재정렬.** 표·6패널 차트 순서 = NFP·실업률 > 소매판매 > ISM제조 > ISM서비스 > GDP. 의미·시장영향 보완(연준경로·소비·경기민감주 등). GDP 실질성장률을 6패널에 재통합(별도차트 제거).
> **v3.26.0 (2026-06-26) — 변동이력·표 정비.** 비일간 지표(정책금리·물가·고용·CAPEX) 최종값 캐시 후 매일 비교→**변경분 표 위 빨간색**(nmr_changelog.py). 3.1.4 '활용'→'시장 영향'. KSVKOSPI investing 1년 일별 채움. 3.1.5 SPX 선행EPS·지수·선행PER 오버레이(+KOSPI 지수). 3.1.6 CAPEX 변동이력 표 위. 3.1.7 대시보드 EPS패널 제거→3사 연도별 EPS/PER 표. 3.1.3 GDP 분기 별도 차트.
> **v3.25.0 (2026-06-26) — 3.1.2/3.1.3 표 재정비.** 3.1.2 물가표에 **발표날짜 컬럼** 추가 + **10Y BEI 를 표 행으로 통합**(6행: CPI·Core CPI·PCE·Core PCE·PPI·BEI), 통합 추이 그래프. 3.1.3 고용표에 **발표일자 컬럼** 추가(지표·최신수치·기준·발표일자·의미·시장영향). yoy/mom 문자열 허용.
> **v3.24.0 (2026-06-26) — 3.1 실측 확장·GOOD REPORT 정합.** (r1) 美 국채금리 블록 **2년물 추가**(10Y+2Y). (r2/r4) 물가5·고용6 월별 **FMP historical 24개월**로 확장(차트 정상화). (r3) BEI 24개월. (r6) SPX 선행지수 추이+선행PER. (r7) **CAPEX 표 2024~2029(E)+기업별 추세 스파크+일별 차트2종**. (r8) **HBM 대시보드 복원**. (r0) 갱신주기 명시. 신규 **gen_macro2.py**(측정 매크로 차트 생성기).
> **v3.23.0 (2026-06-26) — 매크로 전면 실측화(추정 제거, req0).** (1) gen_macro_charts 측정전용: 기준금리=미국 실효(FRED/FMP)만·추정 국가선/ISM/추정 스파크 제거·BEI 무측정시 '미표시'·고용=실측 패널만(실업률·소매·GDP)·물가=CPI 실측(동적 x). (2) 장단기 금리차 차트 **최대기간**(FMP daily). (3) 美10년물 **현재가에 당일변동 복원**·'1일'=직전거래일(prev_pct). (4) 정책금리·**CAPEX(FMP cash-flow)**·**HBM 3사 EPS/PER** 실측, HBM 스팟/점유율 미수록. (5) **KSVKOSPI=investing.com 실측**. (6) MacroAgent series 는 gen_macro_charts 평면배열 스키마. (build_report·gen_macro_charts·merge·agents 갱신.)
> **v3.22.0 (2026-06-26) — 사용자 피드백 8건 반영.** (1) **3.1.1 순서 재정렬**: 美10년물 → 장단기 금리차(10Y-2Y) → HY 스프레드 → FOMC 기준금리 → FOMC 회의 → 점도표. (2) 각 항목 **업데이트 주기/방법 캡션**(매일·변동 시 갱신 등). (3) **6개국 정책금리 실측화** — `PolicyRatesAgent → nmr_policyrates.json`, merge 가 MACRO_DEFAULT 추정 대체. (4) **美10년물 '1일'** = 직전 거래일 대비 1일 변동률(현재가와 분리). (5) **장단기 금리차 1년 차트** `gen_curve_1y.py`(FRED T10Y2Y→FMP curve_10_2 폴백). (6) **Top News 최근 3일 이내만**. Phase 1.5 차트 목록에 `gen_curve_1y.py` 추가.

> **v3.21.0 (2026-06-22) — Phase별 계측(병목 가시화).** 신규 `scripts/nmr_timer.py` 로 각 Phase 시작 시 벽시계를 1줄 마킹하고 Phase 6 에서 Phase별 소요·합계를 출력해 결과 보고에 포함 → 어느 단계(수집/발송/게이트 재작업)에 시간이 쏠리는지 매 실행 수치로 확인. 저비용·비차단(마킹 누락돼도 무방). 동작·산출물 불변.
> **v3.20.0 (2026-06-22) — 증권사 3사(삼성·미래에셋·한투) 메인세션 Chrome 경량화.** 비-Chrome 엔드포인트가 없는(JS 렌더 → web_fetch 는 껍데기) 3사는 메인세션 Chrome 유지가 불가피하나(Chrome 은 메인세션 싱글톤 → 서브에이전트 이전 시 충돌), 토큰을 줄인다: **`browser_batch` 로 3탭 navigate 를 한 번에 묶고 `javascript_tool` 타깃추출만, 단계별 screenshot 금지·get_page_text 덤프 금지.** 텔레그램 7사는 종전대로 `fetch_brokers_tele.py`(curl, Chrome 불필요).
> **v3.19.0 (2026-06-22) — 고정 컨텍스트 다이어트(매 실행 로딩 토큰↓).** SKILL.md 상단 구버전 변경배너(v3.13.2~v3.7.0)를 `CHANGELOG.md` 로 이전(런타임 미로딩) — 최근 배너(v3.16~v3.19)만 유지. 동작·규칙 불변(현행 규칙은 아래 '핵심 수집 규칙'·각 Phase 본문에 이미 반영).
> **v3.18.0 (2026-06-22) — Phase 5 발송 Chrome 경량화(발송 방식 불변).** Gmail MCP 는 발송(send) 도구가 없고 첨부도 미지원 확인 → **Claude in Chrome 직접 발송 유지**하되 토큰 절감: 메일 작성 입력을 `browser_batch` 로 묶고 **단계마다 screenshot 금지**, 발송 직전 1회만 검증(우선 `get_page_text` 패시브 읽기 → To/BCC 칩·제목·첨부 확인, 애매할 때만 screenshot 1장). 첨부(file_upload)·발송 메커니즘·수신자 정책 불변. (상세 `references/email-sending.md`.)
> **v3.17.0 (2026-06-22) — 슬로우데이터 변경감지 보장 + 무거운 에이전트 조건부 발행(토큰·시간↓).** 점도표·버핏13F·지수리밸런싱은 **매 실행 저렴한 마커 1회 관측 → `scripts/nmr_cache.py check`** 로 변경 여부를 확인하고, **마커가 바뀐 경우에만** 해당 무거운 조사 에이전트(USMacroExtras·IndexRebalance·NewsBerk 13F)를 발행한다(변경 없으면 `get` 캐시 재사용=조사 스킵). 빅테크 CAPEX·HBM 은 저렴한 마커가 없어 **실적/분기 창**(`nmr_cache.py gate <오늘>`)으로 판정 — 창 안에서만 조사, 밖이면 carry-forward/내장값. **변경은 매 실행 재관측으로 즉시 포착(보장)** 하되 안 바뀐 날엔 무거운 검색 에이전트가 안 떠 비용이 크게 준다. 캐시 비면 무조건 조사(silent "-" 금지). 게이트는 요일 무관·이벤트창만 본다.
> **v3.16.0 (2026-06-22) — 서브에이전트 모델 티어링(비용·속도 최적화).** Phase 1 수집 에이전트 9종(News·Crypto·Macro·KoreaSemiTheme·GlobalSecurities·USMacroExtras·IndexRebalance·NewsBerk·HBM)을 Agent/Task 호출 시 **`model:"sonnet"`** 으로 발행한다(검색→추출→JSON 저장 작업이라 Opus 불필요 — 토큰·지연 大폭 절감, "추정 금지·도구값만" 그라운딩 규칙으로 품질 유지). **종합·추론이 필요한 Phase 2 AnalysisAgent만 `model:"opus"`** 유지. 메인 오케스트레이터 세션·bash fetch 스크립트는 불변. `model` 미지정 시 부모(Opus) 상속이므로 **반드시 명시**한다(Crypto 등 순수 MCP 호출 에이전트는 검증 후 `haiku` 로 추가 강등 가능).
> **이전 변경이력(v3.13.2 ~ v3.7.0)은 `CHANGELOG.md` 로 이전(런타임 미로딩).** 현행 규칙은 아래 '핵심 수집 규칙'과 각 Phase 본문에 반영돼 있다.


## (SKILL.md 배너 보관 — v3.13.2 ~ v3.7.0)

> **v3.13.2 (2026-06-22) — 3.1 매크로 빈표 재발방지 + docx 전용 확정.** (1) **merge.py 매크로 구조 가드(`_macro_ok`)**: 에이전트 `nmr_macro.json` 의 `macro` 가 빌더 기대 구조(MACRO_DEFAULT: `rates.fed_funds`=dict·`rates.fomc_meetings[]`·`inflation/employment/sentiment.rows[]`)를 못 맞추고 **평면 구조**(`rates.fed_funds`=숫자·`inflation.cpi_yoy` 등)면 그 결과를 **무시하고 `MACRO_DEFAULT` 로 폴백**한다 → 평면 구조가 정상 기본값을 덮어써 3.1.1~3.1.5 표가 통째로 비던 사고를 코드 차원에서 차단. 실측값은 MACRO_DEFAULT 구조 위에 덮어쓰는 방식 권장. (2) **PDF 변환 영구 폐지 재확인**: 최종 산출물은 **docx 전용**(soffice/LibreOffice 변환·PDF 생성·PDF 첨부 금지) — 예약작업 추가지시도 docx 로 통일.

> **v3.13.1 (2026-06-21) — 보고서 품질 3종 상시 보정.** (1) **뉴스 한글 강제**: NewsAgent 가 `headline`·`summary`(1장 핵심 헤드라인·1.글로벌 Top News 10)를 **반드시 한글**로 작성(외신 영어·중국어는 한글 번역, source·source_url 만 원문). 영어 헤드라인 그대로 두기 금지. (2) **AI Trends 항상 10개**: NewsBerkAgent `ai_trends.items` 를 5~8개→**정확히 10개**(부족 시 추가 WebSearch·출처 URL 확인 항목만). (3) **HY 스프레드 차트 상시 렌더**: `gen_hy_chart.py` 폴백이 연결폴더 `_market_report_data` 의 직전 report_data `hy_spread`(6점)도 탐색 → FRED(sandbox 차단) 실패·merge 전 실행이어도 `charts/hy_oas.png` 항상 생성.

> **v3.13.0 (2026-06-21) — 경기선행 순환변동치 차트 자동화(Chrome 불필요·sandbox 실측).** 신규 `scripts/fetch_leading.py` 가 e-나라지표 통계표 AJAX 엔드포인트(`showStblGams3.do?stts_cd=105701&idx_cd=1057&freq=M`, UA+Referer+X-Requested-With 헤더 → 200)에서 **선행종합지수 순환변동치 월별 실측(~29개월)을 sandbox 에서 직접 수집**해 `nmr_leading_series.json`(≥12)+`nmr_leading.json`(최신 4개월 desc·mom)을 생성한다. Phase 1 bash 병렬 배치에 합류(fetch_us·kr·semi·brokers_tele 와 함께) → `gen_leading_chart.py` 가 매 실행 `charts/leading_cycle.png`(3.2.3) 를 항상 채운다. 기존 "Chrome/INDEXerGO echarts(curl 403)·P2 캐시" 경로는 폐기. 실패 시 비차단(파일 미생성 → merge 가 캐시/직전 report_data 폴백).

> **v3.12.0 (2026-06-21) — 3.1 매크로 대시보드 구조 개편 + 선행EPS 차트·경기선행 실측.** (1) **3.1.4 심리에서 선행EPS 분리 → 신규 3.1.5 「지수·Forward EPS·PER」**(S&P500·KOSPI 12M 선행EPS·PER + 지수 차트). (2) **3.3.2 FOMC 점도표·3.3.3 HY 스프레드 → 3.1.1 금리·통화정책에 통합**(하위 블록). (3) **3.3.1 빅테크 CAPEX → 3.1.6**(차트 풀폭 660), **3.2.5 메모리+HBM → 3.1.7** 이동. 미국 증시(3.3)는 ETF(3.3.1)·리밸런싱(3.3.2)만. (4) 신규 `scripts/gen_fwd_eps.py`(S&P500·KOSPI 12M 선행EPS·선행PER 차트 — 지수=실측 nmr_indexseries, EPS=컨센서스 앵커 보간) — **Phase 1.5 차트 7종→8종.** (5) **3.1.1 ● 마커 → ■ + 파란색(1E40AF) 통일**, 장단기 금리차 라벨/값 2줄 분리, 기대인플레 현재값 ■ 제거. (6) **3.2.3 경기선행 순환변동치 = e-나라지표 통계표(index.go.kr idx_cd=1057 → 통계표 탭, 국가데이터처 산업활동동향)에서 12개월 실측 수집** → `nmr_leading_series.json`(INDEXerGO echarts 기계추출 곤란 시 통계표 우선). (7) **MacroAgent VKOSPI 수집값을 임의로 덮어쓰지 말 것**(중동발 급등 실측 반영). (8) **글로벌 IB 신선도 엄격**: 발행일 D-3 초과(예: 월간 House View 3주 전) 자료는 key_reports 에서 제외, 없으면 WebSearch 폴백.

> **v3.11.0 (2026-06-21) — 3장 맨 앞에 「3.1 주요지표」(매크로 대시보드) 신설 + 3장 번호 재배치.** (1) 신규 `build_report.js renderMacroIndicators` 가 **3.1.1 금리·통화정책**(FOMC 기준금리·6개국 정책금리 5년·FOMC 회의 1년 리스트[최신순]·美10년물·장단기 금리차[10Y-2Y])·**3.1.2 물가**(CPI·CoreCPI·PCE·CorePCE·PPI 의미/시장영향 + 통합 YoY 그래프 + 기대인플레 10Y)·**3.1.3 고용**(NFP·실업률·GDP·ISM·소매판매 + 통합 6패널)·**3.1.4 심리**(VIX·VKOSPI·DXY·원달러·WTI 1주~1년 + 의미/활용 + S&P500/KOSPI 선행EPS·PER)를 렌더. (2) 기존 증시 블록 재배치: **한국 3.1→3.2(하위 3.1.1~3.1.5→3.2.1~3.2.5), 미국 3.2→3.3(하위 3.2.1~3.2.5→3.3.1~3.3.5), 아시아 3.3→3.4, 유럽 3.4→3.5.** **3.3 미국 증시 표에서 VIX·DXY·美10년물 제거**(주요지표와 중복 → 일원화). (3) 신규 `scripts/gen_macro_charts.py`(차트 13종) — **Phase 1.5 차트 6종→7종.** (4) 신규 **MacroAgent**(FMP economics/treasury + FRED CSV)가 `nmr_macro.json` 저장, `merge.py`가 `markets.macro`로 전달(없으면 내장 예시·추정값 `MACRO_DEFAULT`). VIX·DXY·원달러·WTI·美10년물은 `fetch_us.py` 시세 **재사용**(중복수집 금지). **확보 어려운 항목(Core CPI·PCE·PPI·ISM·VKOSPI·선행EPS·한중정책금리)은 '추정' 표기**, 미확보 시 빈값.

> **v3.10.0 (2026-06-21) — 3.1.5 반도체 주가 체크용 메모리+HBM 지표 대시보드 추가.** (1) 신규 `scripts/gen_hbm_dashboard.py` 가 6패널(메모리 스팟 종합지수·DDR4/DDR5/NAND 가격·HBM 출하량/시장규모·HBM3E/HBM4 ASP·HBM 점유율[기타 포함 합계 100%·2027E]·HBM:DDR5 격차) + HBM 3사 EPS/PER(당해·차년) 표를 `charts/hbm_dashboard.png` 로 생성(각 패널 내부 범례·하단 해석 코멘트 포함). (2) `build_report.js renderKoreaExtras` 가 **3.1.5** 섹션에 이미지+6개 해설을 `imagePara` 로 임베드(파일 없으면 자동 생략·비차단). (3) **Phase 1.5 차트 생성기 5종→6종.** (4) `merge.py` 가 `nmr_hbm.json`→`markets.hbm` 전달. **모든 수치는 추정치** — `nmr_hbm.json`(HBMAgent 웹리서치) 있으면 라이브 오버라이드, 없으면 내장 예시·추정값. 확인 불가 항목은 미표기·'추정' 표기.

> **v3.9.0 (2026-06-21) — 3.2.1 빅테크 CAPEX 차트 2종 추가.** 신문형 시각자료 요청 반영: (1) 신규 `scripts/gen_capex_chart.py` 가 5개사(MS·아마존·알파벳·메타·오라클) **CAPEX 스택바 + Capex/매출 비율선**(`charts/capex_stack_ratio.png`)과 **FCF 추이선**(`charts/capex_fcf.png`)을 생성 — 2023~2025 실적(각사 10-K/FMP)·2026 가이던스·2027~2029 전망(E). (2) `build_report.js` 가 **3.2.1 표 맨 아래**에 두 차트를 `imagePara` 로 임베드(파일 없으면 자동 생략 — 비차단). (3) **Phase 1.5 차트 생성기 4종→5종**. 데이터는 내장 기본값 우선, `markets.bigtech_capex.{capex,rev,fcf}_series` 가 있으면 라이브 오버라이드.

>

> **v3.8.0 (2026-06-21) — 보고서 "-"/누락 근본 수정.** 사용자 피드백(대량 "-")에 따라: (1) `fetch_us.py` 가 아시아·유럽 지수(3.3/3.4)·금속/농산물(4.2/4.3) 시계열을 `nmr_indexseries`/`series2` 에 포함해 추세 스파크라인 생성, CNY/KRW 크로스(=USD_KRW/USD_CNY) 폴백으로 5장 환율 채움. (2) `merge.py` 가 HY 1주~1년 OAS 히스토리(3.2.3)·FOMC 점도표 "변화" 열(3.2.2, jun−mar)·김치프리미엄 `coins[]`(6.3, upbit_krw/binance_usd/premium_pct) 를 구성. (3) `build_report.js` 에서 7.9 투자자 유형별 추천 조합 **삭제**, 글로벌 IB(8장) "수집 실패" 문구는 key_message/뷰가 없을 때만 표기. (4) `agents.md` — CryptoAgent 김프 coins[] 스키마·SecuritiesAgent 삼성/미래에셋/한투 정확 URL·NewsBerk `ai_trends.items[]`(summary/title_en/summary_en) 명시. **빌더·merge 스키마 일부 확장.**

>

> **v3.7.0 (2026-06-20) — 문서 구조 개편(동작 불변).** 과거 변경이력(v3.0~v3.6.35)은 `CHANGELOG.md` 로 분리(런타임 미로딩)하고, 거기 흩어져 있던 현행 규칙은 아래 **핵심 수집 규칙**과 각 Phase 본문으로 통합했다. **데이터 스키마·서브에이전트·빌더(build_report.js) 로직은 그대로다 — 문서 정리만.** 모순 일원화: 최종 산출물 = **docx 전용**(soffice/PDF 변환 폐지), `request_cowork_directory` **호출 안 함**, 차트 생성기 = 현행 4종만. 에이전트별 상세 프롬프트·반환 스키마는 `references/agents.md`, 발송 절차는 `references/email-sending.md`.


## v3.11.0 (2026-06-21)
- **3장 맨 앞에 「3.1 주요지표」(매크로 대시보드) 신설** — `renderMacroIndicators`: 3.1.1 금리·통화정책(기준금리·6개국 정책금리·FOMC 회의 1년 리스트[최신순]·美10년물·장단기 금리차 10Y-2Y), 3.1.2 물가(CPI~PPI 의미/시장영향 + 통합 YoY 그래프 + 기대인플레 10Y), 3.1.3 고용(NFP·실업·GDP·ISM·소매 + 통합 6패널), 3.1.4 심리(VIX·VKOSPI·DXY·원달러·WTI + 의미/활용 + S&P500/KOSPI 선행EPS·PER).
- **3장 번호 재배치**: 한국 3.1→3.2(하위 3.1.1~3.1.5→3.2.1~3.2.5), 미국 3.2→3.3(하위 3.2.1~3.2.5→3.3.1~3.3.5), 아시아 3.3→3.4, 유럽 3.4→3.5.
- **3.3 미국 증시 표에서 VIX·DXY·美10년물 제거**(3.1 주요지표와 중복 → 일원화).
- 신규 `scripts/gen_macro_charts.py`(차트 13종) — Phase 1.5 차트 6종→7종.
- 신규 **MacroAgent**(FMP economics/treasury + FRED CSV) → `nmr_macro.json`, `merge.py` 가 `markets.macro` 전달(없으면 내장 `MACRO_DEFAULT`). VIX·DXY·원달러·WTI·美10년물은 `fetch_us.py` 시세 재사용. Core CPI·PCE·PPI·ISM·VKOSPI·선행EPS·한중정책금리는 '추정' 표기.


> 이 파일은 과거 운영 학습·변경 내역의 **보관용 기록**이다. 런타임(스킬 실행)에는 로딩되지 않는다.
> 현행 규칙은 `SKILL.md` 의 '핵심 수집 규칙' 및 각 Phase 본문을 따른다. (v3.7.0, 2026-06-20 에 SKILL.md 에서 분리)

---

# Namoobi Market Report (v3.9.0)

> v3.9.0 (2026-06-21 — 3.2.1 빅테크 CAPEX 차트 2종 추가): 신규 `scripts/gen_capex_chart.py` 가 5개사(MS·아마존·알파벳·메타·오라클) **CAPEX 스택바+Capex/매출 비율선**(`charts/capex_stack_ratio.png`)·**FCF 추이선**(`charts/capex_fcf.png`)을 생성(2023~2025 실적[각사 10-K/FMP]·2026 가이던스·2027~2029 전망E). `build_report.js` 가 3.2.1 표 맨 아래에 `imagePara` 로 임베드(없으면 비차단 생략). Phase 1.5 차트 생성기 4종→5종. 데이터 내장 기본값 + `markets.bigtech_capex.{capex,rev,fcf}_series` 라이브 오버라이드.

# Namoobi Market Report (v3.6.35)

> v3.6.35 (2026-06-20 운영 학습 — 12장 액션아이템 렌더·증권사 수집방식): **이 블록은 이전 모든 규칙에 우선한다.**
> - **12장 액션아이템 [object Object] 근본수정**: `build_report.js` 가 `action_items.forEach(it=>children.push(bullet(it)))` 로 각 항목을 **문자열로** 출력하는데, AnalysisAgent 가 `{horizon,item}` **객체**로 주면 "[object Object]" 로 렌더됐다(실측). 빌더가 항목이 객체(`{horizon, item|text|action}`)이든 문자열이든 모두 `"[horizon] item"` 문자열로 정규화해 출력하도록 수정 — 스키마 불문 안전. 병합 단계에서도 동일 정규화를 권장(`action_items=action_items.map(it=>typeof it==='object'?('['+(it.horizon||'')+'] '+(it.item||'')):String(it))`).
> - **7 한국 5대 증권사 = 메인세션 Claude in Chrome 직접 navigate 필수(재강조)**: 키움이 koscom iframe 이라 본문이 안 보인다고 **5개사를 전부 WebSearch 로 일괄 우회하면 안 된다.** 미래에셋·삼성 등은 JS 렌더 리서치 목록이라 WebSearch 에 안 잡혀, **접근 가능한데도 "기준일 미확인" 으로 잘못 비는 사고**가 난다(실측: `securities.miraeasset.com/bbs/board/message/list.do?categoryId=1521` 정상 접근·6/19자 '한국&중국 마켓 클로징'·'월스트리트파인더' 등 노출). 각 사 공식 목록을 **개별로 navigate→get_page_text** 하고, 키움만 iframe 이면 키움만 보조수단(텔레그램 t.me/s/KiwoomResearch)을 쓴다. WebSearch 일괄 우회 금지.

> v3.6.34 (2026-06-19 사용자 추가 피드백 — KOSDAQ 거래량·CAPEX 2027·DRAM ETF):
> - **3.1.1 KOSDAQ(·KOSPI) 일봉 거래량 (반복 이슈)**: 야후 `^KQ11` 거래량은 ① 값 자체가 손상(중앙값~1000)되고 ② **비거래일 유령행**(일요일 등, vol≈1000)이 섞여 있다. → 캔들 입력(`nmr_kr_ohlcv.json`) 구성 시 **다음 `market_index/days` accTradeVolume 으로 거래량을 교체하고, 다음(KRX 거래일)에 없는 날짜(유령행)는 제거**한다(거래일 캘린더=다음 기준). KOSPI 도 동일 적용해 일관화. (이 단계 누락이 '거래량 이상' 반복의 원인.)
> - **3.2.1 CAPEX 2027(E) 항상 수집·표 전체폭 (req)**: `bigtech_capex.rows[].y2027` 을 매 실행 웹조사로 채운다(개별 2027 공식 가이던스 미제시 시 컨센서스/하우스 추정·정성 표기, 출처 명시 — 예 알파벳 모건스탠리 ~$250B, 4사 합산 RBC $637B~Evercore/BofA $1T+). 빈칸 금지(채우면 yrHas 로 열 표시). 표는 연도 열 수에 맞춰 **코멘트 열이 남는 폭을 흡수해 오른쪽 끝까지**(`build_report.js` v3.6.34, Wt≈9740 twips). 2028(E) 는 전부 미공개면 자동 제거 유지.
> - **3.2.4 ③ 테마/특화 ETF 에 DRAM 포함**: `markets.us_etfs.theme` 에 **DRAM(Roundhill Memory ETF — D램·HBM 메모리)** 항상 포함(신생 ETF 라 6개월·1년은 null, 상장후 기간 표기). UsEtfAgent 대상에 DRAM 추가됨.



> v3.6.33 (2026-06-19 사용자 피드백 — req1~7 차트 근본수정 + "조용히 미표시 금지" 정책 + GOODREPORT 비교 게이트):
> **반복 원인 2가지: ① 설치본이 repo 보다 구버전(수정이 production 에 반영 안 됨) ② 데이터 미수집 시 스크립트가 조용히 열화(주봉선 폴백)하거나 빌더가 "-"로 넘김.** 아래로 영구 차단한다.
> - **데이터 소스 교체 (가장 중요 — req3/4/5 근본원인)**: 다음금융 차트 API `finance.daum.net/api/charts/A{code}/days` 는 현재 **403**(한국 ETF/종목 시계열 수집 불가의 진짜 원인). → **Yahoo `<code>.KS`/`.KQ` 로 교체**(확인됨: 091160.KS=121개월, 신규상장 ETF 도 상장이후 가용분 반환). 코드 해석은 다음 검색 API `api/search/quotes?q=<이름>`(정상 작동)로, 시계열은 Yahoo(UsStockInfo MCP `get_historical_stock_prices(period="10y",interval="1mo")` 또는 메인세션 Chrome `query1.finance.yahoo.com/v8/finance/chart`)로 받는다. **수집 결과 `_failed` 배열로 실패 티커를 명시**해 "신규상장이라 짧은 것"과 "수집 버그로 빈 것"을 구분한다(빈 것은 사용자에게 보고).
> - **3.1.1 코스피/코스닥 일봉 캔들 (req1)**: `nmr_kr_ohlcv.json` 에 **일봉 OHLCV**(Yahoo `^KS11`/`^KQ11` interval=1d, ~245행)+**일별 수급**(`kospi_flows_daily`/`kosdaq_flows_daily`=[date,F,I,P] 다음 `market_index/days` perPage=250, 오름차순)을 채운다 → `gen_kr_candle.py`(mplfinance 필요)가 캔들+MA(5/20/60/120)+볼린저/거래량/RSI/누적순매수 4패널 생성. **주봉선 폴백은 데이터 미수집 시에만**(정상 경로 아님).
> - **3.1.3 경기선행지수 10년 (req2)**: `nmr_leading_series.json` 에 INDEXerGO echarts 전체 시계열([["YYYY-MM",값]] 2016~현재, 119점). 메인세션 Chrome `navigate indexergo.com/series/?detailId=11601&frq=M` → `window.echarts.getInstanceByDom(node).getOption().series` 에서 name='선행종합지수 순환변동치' data 추출(날짜 구분자 정규화). `gen_leading_chart.py` 가 연축 10년 라인.
> - **3.1.4 테마 10년 월별 (req3) + 반도체 종목/ETF 추세 (req4/5)**: `nmr_kr_series.json={stocks,themes,etfs}`(각 10년 월별 종가, Yahoo). `gen_rest_charts.py` v3.6.33 가 **신스키마**(report_data `markets.semi_ai_stocks`/`semi_ai_etfs` 순서)로 `charts/semi_s_<i>.png`·`semi_e_<i>.png` 와 `theme_<sani>.png`(10년) 생성 — **구버전은 nmr_semi_series.json+semi_ai_breakdown(구스키마)라 신스키마와 불일치→항상 "-" 였음(수정)**. 추세 라벨은 실제 보유기간(N Y/N M). ETF 는 **항상 상위 20**(미달이면 빌더가 blocking).
> - **3.2.1 CAPEX 2028 (req6)**: `build_report.js` `yrHas()` 가 전부 빈 연도 열을 제거(이미 적용). 2027·2028 전부 미공개면 그 열 통째 삭제.
> - **3.2.3 HY 월별 (req7)**: `nmr_hy_series.json` 에 FRED `BAMLH0A0HYM2` **월별** 시계열(메인세션 Chrome `fred.stlouisfed.org` 동일출처 `graph/fredgraph.csv?id=...`; **무료 CSV 는 약 3년 상한** — 그 이상은 FRED API 키 필요, 미보유 시 가용 최대(약 3년)로 월별 렌더하고 보고에 한계 명시). `gen_hy_chart.py` v3.6.33 가 월별(연/반기 눈금) 라인.
> - **(정책) 조용히 미표시·"-" 금지 → 차단형 게이트 + 사용자 질문**: `build_report.js` validate() v3.6.33 가 **데이터는 있는데 차트 파일이 없으면 issues(blocking)** 로 처리(kospi/kosdaq_tech, leading_cycle, hy_oas, semi_s/semi_e 전수, ETF<20). **Phase 3.6**(아래)에서 `--validate` 가 exit≠0 이면 워크플로를 멈추고 **사용자에게 어찌할지 묻는다**(임의로 비우거나 진행 금지).
> - **(정책) GOODREPORT 비교 게이트 (Phase 4.5)**: 최종 docx 를 연결폴더 `GOODREPORT` 기준본과 `scripts/gen_goodreport_compare.py` 로 비교(이미지/표/용량/섹션). 이상부(이미지·용량 부족, 섹션 누락) 검출 시 보고서 발송/공유 전에 **사용자에게 보고**하고 보완한다.
> - **반복 방지(설치본 stale)**: repo 를 고친 뒤 **반드시 재설치**해야 production(설치본)에 반영된다. 수정 후 Phase 0 에서 설치본 build_report.js footer 버전이 repo 와 다르면 경고.



> v3.6.32 (2026-06-19 사용자 피드백 — 반복 결함 근본차단) — **이 블록은 이전 모든 규칙에 우선한다.**
>
> **핵심 원칙: "조용히 미표시(-)·carry-forward·stale 로 넘어가지 말 것. 결함이 있으면 발송하지 말고 사용자에게 물어라."**
> v3.6.31 까지의 "폴백으로 항상 채운다"는 접근이 오히려 *열등한 차트·빈칸·낡은 자료*를 조용히 통과시켜 매 회차 같은 섹션이 깨졌다. 이제는 폴백으로 때우지 말고, **정상 예제(`D:\claudeCowork\GOODREPORT`) 수준을 못 맞추면 멈추고 묻는다.**
>
> ## 1. 발송 전 품질 게이트 = Phase 4.5 (필수·차단)
> docx 빌드 직후 **반드시** `node scripts/verify_report.js <report_data.json> <WORK>` 를 실행한다. problems 가 하나라도 있으면 **exit 1** 이며 다음을 코드로 검사한다:
> - req1) 3.1.1 코스피·코스닥 차트 = **일봉 캔들**(`charts/kospi_tech.png`·`kosdaq_tech.png`) 존재 — `*_flows.png` 폴백이면 실패.
> - req2) 3.1.3 경기선행지수 **장기 series(`nmr_leading_series.json` ≥12개월)** + 차트 존재.
> - req3) 3.1.4 테마 8종 추세차트(`charts/theme_*.png`) 모두 존재.
> - req4) 반도체/AI 종목 ≥10 + 각 추세차트(`semi_s_*.png`).
> - req5) 반도체/AI ETF **정확히 20종** + 각 추세차트(`semi_e_*.png`).
> - req7) FOMC 점도표 rows 의 jun·mar 값에 **빈칸 없음**.
> - req8) 증권사·IB `key_reports` 날짜 **신선도(Daily≤1·Weekly/Monthly≤3일; 월요일·주말은 금요일까지)** 이내 — stale 이면 실패.
>
> **게이트 실패 시 절대 자동 발송 금지.** problems 목록을 사용자에게 그대로 보고하고 어떻게 할지 물어라(해당 섹션 재수집 / 그대로 발송 / 보류). **예약(scheduled) 실행도 동일** — 결함이 있으면 발송을 보류하고 결함 목록을 결과 보고에 남긴 뒤 사용자 확인을 기다린다(낡은·깨진 보고서를 자동 발송하지 않는다).
>
> ## 2. GOODREPORT 최종 비교 (Phase 4.5)
> `D:\claudeCowork\GOODREPORT\` 골든 리포트와 새 docx 를 비교: `unzip -l` 임베드 미디어(차트) 개수가 골든의 90% 미만이거나 핵심 섹션 머리말이 누락되면 결함으로 보고 위와 동일하게 사용자에게 묻는다. (골든 폴더가 비었거나 깨진 회차 파일이 들어 있으면 사용자에게 기준 파일을 확인 요청 — 임의 진행 금지.)
>
> ## 3. 수집 강제 (carry-forward·열등 폴백 금지 — 게이트가 잡는다)
> - **3.1.1 일봉 OHLC**: 야후 `^KS11`/`^KQ11` `interval=1d`(Chrome 동일출처 fetch) → `nmr_kr_ohlcv.json`(`kospi_ohlcv`/`kosdaq_ohlcv`=[[date,o,h,l,c,v]]), 거래량=다음 `accTradeVolume`, 수급=다음 일별 → **`gen_kr_candle.py` 로 `kospi_tech.png`·`kosdaq_tech.png` 생성**(flows 차트로 대체 금지).
> - **3.1.3 선행지수 장기 series**: INDEXerGO `series/?detailId=11601&frq=M` echarts 에서 2016~현재 월별 순환변동치 추출 → `nmr_leading_series.json`(≥12) → `gen_leading_chart.py`.
> - **3.1.4 테마·반도체 series**: 8테마 대표 ETF + 종목10·ETF20 의 1년 주봉을 `nmr_themeseries1y.json`·`nmr_semi_series_v3.json` 에 채워 `gen_rest_charts.py`(theme_*/semi_s_*/semi_e_*). **ETF 는 항상 AUM 상위 20**(다음금융 검색+marketCap 정렬, 단일종목 레버리지 포함).
> - **3.2.2 점도표**: 2026·2027·2028말·장기중립 **jun·mar 중간값 모두** 확보(빈칸이면 게이트가 막음 → 추가 검색).
> - **7 증권사 = Chrome-first**: 신한·미래에셋·삼성·한국투자·키움 공식 페이지를 **메인세션 Claude in Chrome navigate→get_page_text/screenshot** 로 직접 읽어 신선도 충족 최신만 수집. 못 구하면 빈값으로 두되 **stale 로 채우지 말 것**. 키움은 `?dummyVal=0`.
>
> ## 4. 빌더(이미 반영)
> - req6) 3.2.1 CAPEX: 2027(E)·2028(E) 열은 **값이 하나라도 있을 때만** 표시(전부 미공개면 열 통째 제거) — `build_report.js` 적용 완료.

# Namoobi Market Report (v3.6.31)

> v3.6.31 (plugin 1.7.30) 변경점 — 7개 재발 이슈 근본수정 (2026-06-19 사용자 피드백: 3.1.1 수급차트·3.1.3 선행지수·3.2.1 CAPEX·3.2.2 점도표·3.2.3 HY그래프·6.3 SOL·8 IB최신성이 새 세션마다 깨짐):
> 근본원인 = **빌더는 정상이나 데이터/차트 입력이 불안정하면 빌더가 해당 섹션을 조용히 생략**(빈 데이터=미표시). 차트는 스크립트 폴백, 데이터는 수집 강제+carry-forward 로 항상 채워 영구 차단한다.
> - **차트 스크립트 robust화 (입력 불안정해도 항상 생성) — Phase 1.5 에서 셋을 반드시 실행하고 인자로 report_data 경로를 넘긴다**:
>   - `gen_hy_chart.py` (3.2.3): **출력 파일명을 `charts/hy_oas.png` 로 수정**(구버전은 `hy_oas_chart.png` 로 저장 → 빌더(charts/hy_oas.png)와 불일치 → 그래프 미표시가 근본원인). FRED 1년 series(`nmr_hy_series.json`) 없으면 **report_data `markets.hy_spread` 6레벨(current/w1/m1/m3/m6/y1)로 추이선** 폴백.
>   - `gen_leading_chart.py` (3.1.3): 장기 series(`nmr_leading_series.json`) 없으면 **`markets.korea_leading[].value` 월별 점으로** 폴백(구버전은 파일 없으면 FileNotFoundError 크래시 → 그래프 없음/이상).
>   - `gen_kr_candle.py` (3.1.1): 일봉 OHLCV(`nmr_kr_ohlcv.json`)를 **검증·세정**(0/음수/High<Low/±40% 급변/중복일/NaN 제거)해 깨진 캔들('차트 이상') 차단. 일봉 없거나 유효행<30이면 **`nmr_indexseries.json` 주봉 종가로 종가선+이동평균** 폴백(크래시 금지).
>   - 실행: `python3 <script> <report_data.json>`(또는 NMR_OUT 자동탐색). 입력 미수집이어도 폴백으로 그래프 생성.
> - **3.2.1 CAPEX·3.2.2 FOMC 점도표 — Phase 1 에 USMacroExtras 수집 추가**: `markets.bigtech_capex`(MSFT/GOOGL/AMZN/META 연간 CAPEX) + `markets.fomc_dotplot`(최신 점도표). 미수집 시 빌더가 섹션 생략하므로 매 실행 WebSearch 수집(`references/agents.md` USMacroExtrasAgent). 저장 `nmr_usmacro.json` → 병합 시 주입.
> - **병합 carry-forward (slow-change last-known-good)**: 이번 런에서 `markets.bigtech_capex`·`markets.fomc_dotplot`·`markets.us_credit`/`markets.hy_spread` 가 비면 **직전 `_market_report_data/report_data_*.json` 에서 가져와 채운다**(분기/월 단위로만 변함). 병합 node 스크립트에 포함.
> - **6.3 김프 SOL 항상 채움**: CryptoAgent 가 SOL 포함 4종을 CoinInfo→실패 시 CoinDesk(upbit/binance)로 반드시 계산(`references/agents.md`).
> - **8 IB 최신성 엄격**: D-1/D-3 초과 자료 사용 금지, 미충족이면 "기준일(D-1/D-3) 충족 최신 공개 자료 미확인"으로 정직하게 비움.


# Namoobi Market Report (v3.6.28)

> v3.6.28 (plugin 1.7.29) 변경점 — 부록B 한/영·5장 환율 스파크라인·이미지 복구버그 (2026-06-18 사용자 피드백):
> - **이미지 type:"png" (Word 복구창 해결)**: build_report.js `imagePara`/`imgCellSpark` 의 `ImageRun` 에 `type:"png"` 추가. docx 라이브러리 9.x 는 type 미지정 시 이미지 파트를 `.undefined` 확장자로 저장 → `[Content_Types].xml` 에 png 만 있어 Word 가 "일부 콘텐츠를 읽을 수 없습니다(복구)" 를 띄운다(XML·폰트·링크는 정상이라 [예] 누르면 열림).
> - **[부록B] AI Trends 국문·영문 병기**: 기본=한글 본문, 그 아래 영어 번역본("EN ▸ ...") 2종. ai_trends.items[] 에 title/summary(한글) + title_en/summary_en(영어). 빌더 renderAITrends 가 한/영 렌더, 헤더 "(국문·영문 병기)".
> - **5장 환율 추세 스파크라인 항상**: USD/EUR/JPY/CNY/HKD 대 원화 5행의 추세(1년) 그래프가 "-" 로 비던 문제 — nmr_series2.json.fx 에 usd_krw/eur_krw/jpy_krw/cny_krw/hkd_krw 1년 주봉을 채워 gen_rest_charts.py 가 spark_*_krw.png 를 생성하도록 했다.

# Namoobi Market Report (v3.6.27)

> v3.6.27 (plugin 1.7.28) 변경점 — SECURITY 권한창 제거 (2026-06-18 사용자 피드백 "실행할 때마다 이거 물어보는데 묻지 마"):
> - **`mcp__cowork__request_cowork_directory` 를 절대 호출하지 않는다(이 호출이 매 실행 권한창의 원인).** Phase 0/Phase 5 에서 D:\claudeCowork 또는 그 하위 SECURITY 폴더 접근을 위해 이 도구를 호출하면 "D:\claudeCowork\SECURITY 에서 Cowork 하려고 합니다 — 허용/거부" 창이 떠서 사용자가 매번 눌러야 한다. 호출 자체를 제거한다.
> - **이미 연결된 경로로 직접 접근**: D:\claudeCowork 는 사용자가 세션 시작 시 연결해 둔다는 전제로, 연결 폴더·SECURITY 파일(수신자 목록·githubtoken)·docx 저장을 모두 **이미 마운트된 VM 경로 `/sessions/*/mnt/claudeCowork/...` 로 bash 에서 직접 읽고 쓴다**(권한 요청 없이). 전체 마운트가 `D:\claudeCowork\Scheduled` 보호로 막혀도 **SECURITY 하위폴더를 개별 request 하지 말 것**.
> - **접근 실패 시에도 권한창 금지**: SECURITY 파일을 못 읽으면(미연결) request_cowork_directory 를 부르지 말고, BCC 생략·outputs 진행 후 Phase 6 에 "연결 폴더 미연결" 만 보고한다. (Phase 0 의 기존 '미연결이면 request_cowork_directory 요청' 지시·트러블슈팅 표의 동일 항목은 본 v3.6.27 규칙으로 무효화한다 — 호출하지 않는다.)

# Namoobi Market Report (v3.6.26)

> v3.6.26 (plugin 1.7.27) 변경점 — 표 2행 레이아웃·반도체 ETF 다음금융·차트 보강·파일명/형식 (2026-06-18 사용자 피드백):
> - **최종 산출물 = docx (PDF 변환 폐지)**: soffice 변환이 이 환경에서 자주 hang/실패하므로 **docx 를 그대로 메일 첨부·공유**한다. Phase 4 의 docx→PDF(soffice) 변환 단계는 생략(원하면 사용자 PC 에서 변환).
> - **파일명 = `global_market_report_YYYYMMDD_HHMM.docx`** (영문, 연월일=기준일·시분=생성시각 KST). 기존 한글 파일명 폐기.
> - **표 전부 2행 레이아웃 통일**: 3.2 미국 ETF(①②③④)·3.3 아시아·3.4 유럽·4.1 에너지·4.2 금속·4.3 농산물·4.5① 전략광물 ETF·5 환율 을 3.1.4식 **2행**(1행=이름·설명 span / 2행=현재가·1주~1년·추세그래프·추세평가)으로 렌더. 빌더 신규 공통 함수 `trend2Rows`+`TR2`(renderMarketBlockC·5장 FX 블록·renderUSEtfs·renderStrategicMetals 모두 이걸 호출). 세로 길이 압축 목적.
> - **3.1.4 반도체/AI ETF = 다음금융 AUM 상위 20종(필수, 야후 금지)**: 야후엔 한국 ETF 가 없어 '상장전'/누락 발생했었다. **다음금융 API 직접 수집**(메인세션 Claude in Chrome, finance.daum.net/quotes/A091160 등에서 동일출처 fetch): ① 검색 `api/search/quotes?q=반도체|AI반도체|시스템반도체|반도체소부장|단일종목레버리지&limit=30` → ETF 후보 symbolCode 수집 ② 각 `api/quotes/{sym}?summary=false` 의 `marketCap`(AUM 프록시)로 내림차순 정렬해 상위 20 ③ 각 `api/charts/{sym}/days?limit=300&adjusted=false`(헤더 Referer=`finance.daum.net/quotes/{sym}`) — **응답은 오름차순(data[0]=과거, 마지막=현재, 마지막 tradePrice 가 실시세와 일치)**, 절대 reverse 금지, adjusted=true 금지(현재가 불일치). 현재가=마지막, 1주=−5·1개월=−21·3개월=−63·6개월=−126·1년=−248 영업일 종가 대비 수익률. 상장 1년 미만이라 없는 기간은 문자열 `"상장전"`(빌더 fmtPct 가 숫자 아니면 그대로 출력), trend=`"상장 N주"`. series(주봉 다운샘플)로 `charts/semi_e_<i>.png` 미니차트.
> - **3.1.3 경기선행지수 시계열 차트**: indexergo(`indexergo.com/series/?detailId=11601&frq=M`)의 **echarts 인스턴스**에서 전체 시계열 추출(`window.echarts.getInstanceByDom(node)`→`getOption().series` 중 name '선행종합지수 순환변동치'의 data = [[YYYY.MM,값]…] 2016~현재). 날짜 정규화 후 `nmr_leading_series.json` 저장 → `scripts/gen_leading_chart.py`(빨강 라인+100 기준선+최신값 라벨, `charts/leading_cycle.png`). 빌더가 `markets.korea_leading_chart` 로 3.1.3 표 아래 `imagePara` 임베드.
> - **3.2.1 HY 차트**: FRED `BAMLH0A0HYM2` 1년 일별 OAS(`nmr_hy_series.json`)로 `charts/hy_oas.png` 생성, `markets.hy_spread.chart` 임베드. `hy_spread` 에 current + w1/m1/m3/m6/y1(1주~1년 OAS 레벨) 모두 채워 표 '-' 방지(빌더 us_credit→hy_spread 정규화는 current 만 채우므로 hy_spread 를 직접 세팅).
> - **6.3 김치프리미엄 SOL**: CoinDesk MCP `fetch_spot_tick`(market=upbit SOL-KRW + market=binance SOL-USDT)로 김프=(업비트KRW/(바이낸스USD×환율)−1)×100. BTC·ETH·XRP·SOL 4종 모두 채움.
> - **7 키움 = `?dummyVal=0`**: 일간증시전망 목록은 `www3.kiwoom.com/h/invest/research/VMarketSDView?dummyVal=0`(모닝 `VMarketMLView?dummyVal=0`·종목 `VAnalTPView?dummyVal=0`)로 접근하면 **본문 DOM 에 목록(제목·작성일)이 렌더**된다. dummyVal 없으면 koscom iframe 위젯이라 텍스트가 안 보임(과거 '미확인' 오판 원인). screenshot 불필요.
> - **8 JPM 빈칸 정책**: jpmorgan.com·privatebank.jpmorgan.com 은 Claude in Chrome 안전정책 차단, web_fetch 는 JS 셸, WebSearch 는 연간 전망만 노출 → **D-1/D-3 충족 공개자료 확보 불가 시 다른 IB 와 동일 기준으로 "기준일(D-1/D-3) 충족 최신 공개 자료 미확인" 으로 비워둔다**(연간 전망 등 stale 로 채우지 말 것).

# Namoobi Market Report (v3.6.25)

> v3.6.25 (plugin 1.7.26) 변경점 — 반복 드리프트 근본차단·결정적 경로 고정 (2026-06-17 사용자 피드백 "며칠째 같은 게 깨진다"):
> 아래는 **매 실행 반드시 이 경로로만** 수행한다(다른 생성기/소스 선택 금지). "지시는 프롬프트에 있는데 코드로 강제 안 돼서" 매번 다르게 깨지던 문제의 해결책이다.
> - **3.1.1 차트 = 반드시 일봉 캔들(`gen_kr_candle.py`)**: `gen_kr_tech.py`(선차트·주봉)·`gen_kr_extra.py` 등 **다른 한국 지수 차트 생성기 사용 금지**. 입력 `nmr_kr_ohlcv.json` 의 `kospi_ohlcv`/`kosdaq_ohlcv` 는 **야후 `^KS11`/`^KQ11` interval="1d" 일봉 OHLC**(주봉·종가선 금지), 거래량은 **다음금융 `accTradeVolume`(야후 ^KQ11 거래량 손상)** 으로 ±1일 매칭 교체, `kospi_flows_daily`/`kosdaq_flows_daily` 는 다음금융 일별 순매수(`market_index/days`, Chrome 동일출처 fetch). 생성 후 PNG 를 **반드시 열어 캔들·일봉·거래량 정상인지 눈으로 확인**(연결폴더 복사 후 Read).
> - **3.1.3 경기선행지수 = WebSearch 절대 금지, indexergo 직접**: Claude in Chrome 으로 `https://www.indexergo.com/series/?detailId=11601&frq=M`(국가데이터처 선행종합지수 순환변동치) 를 `get_page_text` 해 **순환변동치 절대값(예 104.10)+전월차(+0.60p)+전년차**를 읽는다. `markets.korea_leading=[{period,value(숫자),mom,note}]` 의 value 를 비우지 말 것(잠정치면 note 명시). 비로그인은 최신월만 노출되므로 최신 1행+코멘트로 충분.
> - **3.2.1 HY 스프레드 = FRED 직접(null 금지)**: Chrome 으로 `https://fred.stlouisfed.org/series/BAMLH0A0HYM2` 진입 후 **동일출처** fetch `graph/fredgraph.csv?id=BAMLH0A0HYM2&cosd=...`(OAS)·`id=BAMLH0A0HYM2EY`(유효수익률). `markets.us_credit={hy_oas,hy_yield,implied_ust(=유효수익률-OAS),comment}` + 1주~1년 레벨. (CORS 때문에 반드시 fred.stlouisfed.org 도메인 위에서 fetch — 타 도메인에서 fetch 하면 Failed to fetch.)
> - **5 환율 HKD/KRW 항상 채움**: `HKD/KRW = USD/KRW ÷ USD/HKD`(HKD 는 USD 페그 7.75~7.85, 야후 `HKD=X`). null 금지.
> - **3.1.4 테마 수익률 = 시계열에서 계산**: `markets.korea_theme_rows` 각 테마 `current`/`1w_pct`~`1y_pct`/`trend` 를 `nmr_themeseries1y.json` 대표 ETF 1년 시계열로 계산해 채운다(빈칸"-" 금지). 빌더는 차트만 있고 값이 없으면 전부 "-" 로 렌더됨.
> - **7·8 신선도 게이트 = 코드로 강제**: 발행일 D-1(Daily)/D-3(Weekly·Monthly) 초과 자료는 **병합 단계 코드로 제거**(주말이면 금요일 허용). 프롬프트 지시만 믿지 말고 merge 스크립트에서 `key_reports` 날짜를 필터링한다.
> - **⚠️ PDF 변환 = 항상 새 파일명으로(절대 덮어쓰기 금지) — 이번 며칠째 PDF 깨짐의 근본원인**: 직전에 `present_files`/메일로 공유했거나 이미 존재하는 PDF 파일명으로 `soffice --convert-to` 하면 **하니스 file-lock 때문에 덮어쓰기가 `Io Abort(Error Area:Io Class:Abort Code:27)` 로 실패**하고, **깨진 옛 PDF(잘린 페이지·텍스트 추출 0)** 가 그대로 남아 "수정이 반영 안 됐다"고 오판하게 된다. → 변환 출력은 **반드시 한 번도 공유 안 한 새 파일명**(예 `rpt_build_HHMMSS.pdf`)으로 만들고, 그 다음 연결폴더의 최종 파일명으로 복사한다. soffice 는 **기본 프로파일**로 `setsid` detached 실행(`-env:UserInstallation` 새 프로파일은 느리거나 행). 변환 후 `pdftotext`로 텍스트 추출·`pdfinfo` 페이지수·`pdffonts` nanum 임베드를 **반드시 검증**(텍스트 0 또는 페이지 급감이면 깨진 것 → 새 파일명으로 재변환). soffice 좀비는 `pkill -9 -f soffice` 로 정리(메모리 OOM 유발). **soffice 가 변환을 시작은 하는데 PDF 가 안 나오고 무한 대기(hang)하면, 기본 프로파일 락(`~/.config/libreoffice/.lock`)을 좀비가 쥐고 있는 경우가 많다 → `pkill -9 -f soffice; sleep 3; rm -rf ~/.config/libreoffice` 로 프로파일을 완전 초기화한 뒤 단일 변환하면 정상 동작**(이번 PDF hang 의 재현 원인·해결). 큰 캔들 PNG(>200KB)는 `convert <png> -resize 58% -strip <png>` 로 줄이면 변환이 빨라진다.

# Namoobi Market Report (v3.6.23)

> v3.6.23 (plugin 1.7.23) 변경점 — 코스닥 10·증권사 직접수집 (2026-06-17 사용자 피드백):
> - **3.1.2 코스닥도 상위 10**: 코스닥 순매수/순매도도 외국인·기관 각 상위 10 으로(코스피와 동일). 빌더 `invMerged(...,10)`.
> - **7 한국 5대 증권사 = Claude in Chrome 직접 수집(필수)**: 증권사 공식 리서치 페이지는 JS 렌더라 WebSearch/web_fetch 로는 목록이 안 보인다. **메인 세션이 Claude in Chrome 으로 각 사 페이지를 직접 navigate→get_page_text/screenshot** 해서 최신(D-1/D-3) 리포트를 읽는다(WebSearch 단독 금지 — 이래서 과거 "자료없음" 오판 발생). URL: 신한 `shinhansec.com/siw/insights/research/list/view-popup.do`, 미래에셋 `securities.miraeasset.com/bbs/board/message/list.do?categoryId=1521`, 삼성 `samsungpop.com/.../research_pop.jsp`(팝업 자동 로드), 한국투자 `securities.koreainvestment.com/main/research/research/Strategy.jsp?jkGubun=99`(모닝브리프 화면은 screenshot 로 읽기), 키움 `www3.kiwoom.com/h/invest/research/VMarketSDView`(일간증시전망, screenshot). 각 사 발행일 명시. (네이버 금융만 환경 차단이고 이 5개 증권사·다음금융은 모두 접근 가능.)

# Namoobi Market Report (v3.6.22)

> v3.6.22 (plugin 1.7.22) 변경점 — 3.1.2 표 병합·리서치 신선도 강화 (2026-06-17 사용자 피드백):
> - **3.1.2 외국인·기관 한 표 병합**: 8개 분리 표 대신 4개 병합 표로 렌더(빌더 `invMerged`, columnSpan 그룹헤더). 각 표 = `순위 | 외국인(종목·순매매규모) | 기관(종목·순매매규모)`. 코스피 순매수/순매도 상위 10, 코스닥 순매수/순매도 상위 5.
> - **7·8 리서치 신선도 — 웹검색에도 동일 적용**: 신선 자료가 없으면 WebSearch 로 찾되, **웹검색 결과도 D-1(Daily)/D-3(Weekly·Monthly) 기준을 넘으면 사용 금지**(주말이면 금요일 허용). 기준 충족 자료를 끝내 못 찾으면 그 사/IB 는 `key_message:"기준일(D-1/D-3) 충족 최신 공개 자료 미확인"` 으로 두고 **오래된 자료로 채우지 않는다**.

# Namoobi Market Report (v3.6.21)

> v3.6.21 (plugin 1.7.21) 변경점 — 3.1.2 실수집·3.2.0 이동·리서치 항상 채움 (2026-06-17 사용자 피드백):
> - **3.1.2 종목별 수급 — 다음금융 investor_purchase API 로 실수집**: 네이버 금융(finance.naver.com)은 본 실행 환경에서 web_fetch·Claude in Chrome 모두 **플랫폼 차단(blocklist)** 이라 접근 불가. 동일 데이터를 **다음금융**에서 받는다: Claude in Chrome 으로 `https://finance.daum.net/domestic/influential_investors` 진입 후 동일출처 fetch `https://finance.daum.net/api/trend/investor_purchase/?...&market={KOSPI|KOSDAQ}&investorType={FOREIGN|INSTITUTION}` (응답 `data.BUY[30]`·`data.SELL[30]`, 각 `{rank,name,straightPurchasePrice(원),changeRate}`). 4개 조합으로 코스피 외국인/기관 순매수·순매도 상위 10, 코스닥 상위 5 를 채워 `korea_investor_stocks.{kospi_foreign_buy,kospi_inst_buy,kospi_foreign_sell,kospi_inst_sell,kosdaq_*}`(각 `{name,detail}`, detail="순매수/순매도 X억원", `straightPurchasePrice/1e8`)로 저장. 기준일은 `toDate`.
> - **3.2.0 AI 빅테크 CAPEX 위치 이동**: 기존 3.2.4 → **3.2.0**(미국 증시 섹션 맨 앞, 3.2.1 HY 스프레드 앞)으로 이동. `renderUSExtras` 가 `bigtech_capex` 를 가장 먼저 렌더.
> - **7·8 리서치 — 신선자료 없으면 웹검색으로 항상 채움**: D-1(Daily)/D-3(Weekly·Monthly) 최신을 1순위로 하되, 기준 충족 자료가 없으면 **빈값으로 두지 말고 WebSearch 로 각 사/IB 의 가장 최근 공개 시각을 찾아** 핵심 메시지를 채운다(발행일 명시, 뉴스 기반이면 `(뉴스 기반)`). 5사·5IB 모두 `key_message` 비우지 않는다.

# Namoobi Market Report (v3.6.20)

> v3.6.20 (plugin 1.7.20) 변경점 — 3.1.x/4.5/6.2/7·8 보강·항상 표시 (2026-06-17 사용자 피드백):
> - **3.1.1 KOSDAQ 거래량 항상 정상 표시**: 야후 ^KQ11 거래량 손상분(중앙값~1000)을 다음금융 `accTradeVolume`(Claude in Chrome 동일출처 fetch, `market_index/days`)로 교체해 `nmr_kr_ohlcv.json` 의 `kosdaq`/`kosdaq_ohlcv` 거래량(6번째 컬럼)을 채운다. KOSPI 거래량은 야후 정상.
> - **3.1.2 외국인/기관 10·10·10·10 + 코스닥 5·5·5·5**: `korea_investor_stocks` 를 `kospi_foreign_buy`/`kospi_inst_buy`/`kospi_foreign_sell`/`kospi_inst_sell`(각 10)·`kosdaq_foreign_buy`/…/`kosdaq_inst_sell`(각 5)로 분리 수집한다. **NaverSearch(PLAY) MCP**·다음금융 우선, 확정 출처 없는 리스트는 빈배열+`note`(추정 금지). 빌더는 8개 리스트를 각각 렌더.
> - **3.1.4 수익률 2줄 표기**: 테마·반도체 종목·ETF 각 항목을 **2줄**(1행=설명[테마/종목·방향·대표ETF/시총·현황], 2행=현재가·1주·1개월·3개월·6개월·1년 수익률·추세(1Y) 그래프·추세 평가)로 렌더한다(`build_report.js` `retRows`, columnSpan 설명행). 데이터: `markets.korea_theme_rows`(8테마 고정순서)·`markets.semi_ai_stocks`(10)·`markets.semi_ai_etfs`(**항상 20**, 단일종목 레버리지 포함 AUM 상위 20) 각 항목에 `current`,`1w_pct`~`1y_pct`,`trend`,`chart` 포함. 수익률은 1년 주봉 시계열로 계산(부분봉 제거).
> - **4.5 ① 전략광물 ETF 추세그래프 항상 표시**: LIT·REMX·URA·URNM 1년 주봉 시계열(`nmr_strat_series.json`)로 `charts/spark_lit|remx|ura|urnm.png` 를 항상 생성하고 `commodities.strategic_metals.etf` 에 수익률을 채운다.
> - **6.2 코인 차트 항상 조사·표시**: CryptoSeriesAgent 가 BTC·ETH·XRP·SOL 1년(가격·거래량, CoinDesk MCP `fetch_spot_ohlcv` 우선)+공포탐욕 1년(alternative.me)을 `nmr_crypto_series.json` 으로 수집 → `charts/coin_*.png`·`fng_1y.png` 생성 후 `crypto.charts={btc,eth,xrp,sol,fng}` 에 매핑(없으면 6.2 누락).
> - **7 한국 5대 증권사·8 글로벌 IB — 최신자료 신선도 규칙(엄격)**: **Daily 자료는 D-1(전일) 이내, Weekly/Monthly 자료는 D-3 이내**만 사용한다. 주말이라 최신자료가 없으면 **금요일 자료**를 사용. 기준 초과한 오래된 자료(예: 5월·6월초·전년 12월·4월 목표주가)는 **사용 금지** — 미확보 시 빈값(`key_reports:[]`,`key_message:""`). 발행일을 `key_reports[].date` 와 `key_message` 에 명시.

# Namoobi Market Report (v3.6.17)

> v3.6.17 (plugin 1.7.17) 변경점 — 27개 항목 품질 보강·항상 표시 (2026-06-16 사용자 피드백):
> 빌더(build_report.js)·차트(scripts/gen_all2.py·gen_semi_etf.py·gen_kr_flows.py)·에이전트 스키마를 전면 보강해 **아래가 매 실행 항상 포함**되도록 했다. 상세는 `references/agents.md` v3.6.17.
> - **3.1.1 코스피·코스닥 = 대형 일봉 캔들차트** — `gen_all2.py`가 일봉 OHLC(야후 ^KS11/^KQ11 `interval=1d`) 캔들 + MA5/20/60/120 + **거래량 패널** + 투자자별 누적순매수(외국인 빨강·기관 파랑·개인 초록) 3패널을 `charts/kospi_candle.png`·`kosdaq_candle.png`로 생성. 빌더는 항상 폭 648×486(여백최소·최대 크기)로 임베드. `markets.korea_investors.tech=true`, `kospi_chart`/`kosdaq_chart`=candle 경로.
> - **3.1.2 8개 리스트 항상 표시** — `markets.korea_investor_stocks` 에 `kospi_foreign_buy/inst_buy/foreign_sell/inst_sell`(각 10), `kosdaq_*`(각 5). 빌더가 ◆코스피/◆코스닥별 4표씩, 비어도 헤더+"(자료 미수집)" 행 렌더. 수집은 KoreaTechFlowsAgent 가 다음금융+NaverSearch 뉴스로(부분이면 note).
> - **3.1.3 순환변동치 값** — `korea_leading[].value` 숫자 채움(통계청). 값 없으면 전월차만.
> - **3.1.4 테마 순서 고정·항상 8개** — 빌더 `THEME_ORDER=[반도체/AI,전력기기,조선,방산,원자력,증권,로봇,우주]` 고정 렌더. `korea_theme_etfs` 는 **문자열**(객체면 name 추출 → [object Object] 버그 해결). 추세차트는 `korea_theme_charts` 없으면 `charts/theme_<테마>.png` 자동(테마 series 로 생성, 항상).
> - **3.1.4 반도체/AI 종목 10·ETF 20** — 각 `aum`(시총/AUM) 채움, 추세차트 항상(종목 `semi_s_<i>.png`, ETF `semi_e_<i>.png`). ETF 20개·**KODEX 삼성전자/SK하이닉스 단일종목레버리지 포함**. 신규상장 ETF series 는 **다음금융 `/api/charts/A{code}/days`** (반드시 `finance.daum.net/quotes/A{code}` 페이지에서 동일출처 fetch — Referer 헤더 수동설정 불가, `/quotes/` 문서 referer 필요).
> - **3.2.2 미국ETF·3.3 아시아·3.4 유럽·4.x 원자재·5 환율 추세평가 상세화** — 에이전트가 2문장 한글 평가(예 "강한 상승추세 · 가속 국면, 3개월 +35%로 신고가 경신했으나 RSI 과열"). 4.1~4.5·5 추세 그래프 항상(원자재·전략광물 1년 series→`spark_<key>.png`, FX `usd_jpy`/`usd_cny` series 추가).
> - **3.2.3 나스닥100 리밸런싱** — 분기 "셋째 금요일" 행 제거, 연례 재구성만(결정시점 매년).
> - **[부록A] 버크셔** — 빈 섹션도 헤더+"(이번 분기 해당 종목 없음)" 항상 표시, `note` 필드 인식, top_holdings 최대 20.
> - **[부록B] AI Trends** — 빌더가 `ai_trends` 가 **배열이든 {items:[]}든** 렌더(과거 배열이면 미표시되던 버그 해결). 병합 시 `{as_of,sources_checked,items}`로 래핑.
>
> v3.6.16 (plugin 1.7.16) 변경점 — 3.1.x/6.x 1차출처 정밀화 (2026-06-15 사용자 피드백):
> - **3.1.1 한국 기술차트·수급** — 다음금융 `market_index/days`(perPage=250) **Claude in Chrome 동일출처 fetch**로 1년 일별 종가·거래량·외국인/기관/개인 순매수 수집. 지수 OHLC 캔들 API(`/api/charts/...`)는 403 → 캔들 대신 **종가선 멀티패널**(종가+MA5/20/60/120+볼린저 / 거래량 / RSI / 누적순매수)을 신규 `scripts/gen_kr_tech.py`로 생성(`charts/kospi_tech.png`·`kosdaq_tech.png`). `markets.korea_investors.level/순매수`는 최신 마감일 값.
> - **⚠️ 야후 주봉 current stale** — `^KS11`/`^KQ11` 주봉 current가 며칠 지연(예 8123 vs 다음 8546). 한국 지수 current·등락률은 **다음 일별 CSV로 산출**.
> - **3.1.2 종목별 수급** — 다음 메인(`finance.daum.net/domestic`) 외국인/기관 순매수 위젯 DOM 파싱(코스피/코스닥 교차행). 네이버 deal_rank는 web_fetch blocklist.
> - **3.1.3 경기선행지수 — 통계청 보도자료 직접(WebSearch 금지)** — KOSIS/e-나라지표 불안정 → `mods.go.kr` 산업활동동향 게시판(mid=a10301050100&bid=216) 최신 view에서 `(경기) … 선행종합지수 순환변동치 전월대비 X.Xp` 파싱(최근 3개월). 절대수준은 PDF 전용이라 전월차로 표기.
> - **3.1.4** Yahoo `get_stock_info` marketCap(시총)·공개보도 AUM. **6.2/6.3** CoinDesk `fetch_spot_ohlcv`(코인 1년 OHLCV)·`api.alternative.me/fng`(F&G 1년)·`fetch_spot_tick`(김프 4종).
> - 상세 절차·스키마는 `references/agents.md` v3.6.16 참조.
>
> v3.6.15 (plugin 1.7.15) 변경점 — 3.1.x 수급/일봉·3.2.x 재발방지 (2026-06-15 사용자 피드백):
> - **3.1.1 일봉 OHLC 필수** — 코스피·코스닥 기술적 차트는 반드시 **일봉(`interval="1d"`)**. 주봉/월봉처럼 보이던 문제 차단.
> - **3.1.1 외국인/기관/개인 누적순매수 차트·1일 순매수 표 재발방지** — 다음금융 투자자 API 는 web_fetch 가 `Referer` 헤더를 못 보내 항상 빈 응답 → **Claude in Chrome 동일출처 fetch** 로 1년 일별 수급(`*_flows_daily`)을 받는다(검증된 영구 해법). 투자자별 순매수 표는 `*_flows_daily` 최신일 값으로 항상 채운다(빈 객체 금지). 상세는 `references/agents.md` v3.6.15.
> - **3.1.2 장중 수집 / 3.1.3 경기선행지수 / 3.1.4 테마·반도체 추세차트** — 누락 시 섹션이 통째로 빠지므로 수집 의무·소스 명시.
> - **3.2/3.3/3.4 1주 +0.00% 버그** — 야후 '진행중 부분 주봉'이 직전 완성봉과 종가가 같아 1주가 0으로 왜곡됨 → MarketsAgent 가 부분봉 제거 후 1주 계산(UsEtfAgent 와 동일). 빌더는 정상 데이터를 렌더.
> - **3.2.1 미국 HY 스프레드** — FRED CSV 는 web_fetch 가 binary 로 반환해 실패 → Claude in Chrome 으로 `fredgraph.csv` navigate→get_page_text/fetch.
> - **3.2.3 분기 미표시** — 빌더가 S&P500 일정의 `s.q` 만 읽던 것을 `s.q??s.cycle??s.quarter` 로 수정(build_report.js).
>
> v3.6.14 (plugin 1.7.14) 변경점 — 신규 상장 ETF 차트 누락 방지 (2026-06-14 사용자 피드백):
> - **신규 상장 ETF 추세차트** — 야후에 데이터가 없는 최근 상장 ETF(예: 2026.6 상장 단일종목 레버리지)는 **다음금융 charts API**(`finance.daum.net/api/charts/A{코드}/days`, 심볼별 Referer 필수)로 상장 이후 일별 종가를 받아 `charts/semi_e_<i>.png` 생성. 1년 미만은 라벨 `(상장후)`, 한글 라벨용 `fonts/nmr_kr.ttf` matplotlib 등록. (단일종목 레버리지 ETF 차트가 비던 문제 해결.)
>
> v3.6.13 (plugin 1.7.13) 변경점 — 단일종목 레버리지 ETF 포함 (2026-06-14 사용자 피드백):
> - **3.1.4 반도체/AI ETF 유니버스 보강** — AUM 상위 20 선정 시 **삼성전자·SK하이닉스 단일종목 (2배) 레버리지 ETF**(KODEX/TIGER)를 반드시 후보에 포함(2026.6 상장 직후 각 ~2조원대로 AUM 5·6위인데 누락됐던 문제). 2026 신규 상장·레버리지/인버스도 반도체/AI 테마면 배제하지 말 것. 신규 상장 ETF 는 추세차트 미표시(`note` 에 상장월 명시).
>
> v3.6.12 (plugin 1.7.12) 변경점 — 반도체/AI 종목10+ETF20 2그룹 (2026-06-14 사용자 피드백):
> - **3.1.4 반도체/AI 2그룹 확대** — 국내 **종목 시총 상위 10개**(`markets.semi_ai_stocks`) + **ETF AUM 상위 20개**(`markets.semi_ai_etfs`)를 각각 별도 표로, **그룹별 현황 코멘트**(`semi_ai_stocks_comment`/`semi_ai_etfs_comment`)와 각 행 1Y 추세차트(`charts/semi_s_<i>.png`/`semi_e_<i>.png`)로 렌더. 빌더 `semiTbl` 신스키마 우선·구 `semi_ai_breakdown` 폴백. KoreaMacroAgent 가 30종 시총/AUM·series 수집.
>
> v3.6.11 (plugin 1.7.11) 변경점 — 반도체표·원자재추세·버크셔 (2026-06-14 사용자 피드백):
> - **3.1.4 반도체/AI 표 11행** — `semi_ai_breakdown` = 대표 종목 3(삼성전자·SK하이닉스·삼성전기) + 한국 반도체/AI ETF **AUM 상위 8개**(시총순 11행), 각 `aum`·1Y `charts/semi_<i>.png`, **`semi_ai_comment` 현황 코멘트 필수**(ETF 2개·코멘트 없음 문제 해결).
> - **4 원자재 추세열 한글화** — 각 행 `trend` 가 "up"/"down" 영문이면 빌더 `koTrend` 가 수익률 기반 한글("1년 +X% 강세, 3개월 -Y% 조정")로 자동 생성. CommoditiesAgent 도 한글 trend 의무화.
> - **[부록A] 버크셔 상위 보유 최대 20종** — BerkshireAgent `top_holdings` 5→최대 20.
>
> v3.6.10 (plugin 1.7.10) 변경점 — 보고서 정합·견고화 (2026-06-14 사용자 피드백):
> - **3.2.3 리밸런싱 정상화** — IndexRebalanceAgent 가 빌더 스키마(`events:[{title,effective,add[],remove[]}]`)로 출력하도록 강제(평면 `[{ticker,reason}]` 금지). 빌더도 평면 배열이 와도 add/remove 로 자동 정규화(`renderEvents`). 최근 2~3개 분기/연례+M&A·임시 변경 모두 수집. 사용자 `3.2.3_지수리밸런싱.html` 1차 정합.
> - **3.1.1/3.1.2 코스닥 수급** — KoreaTechAgent 가 다음금융 REST(`market_index/days`, 헤더 User-Agent·Referer 필수·perPage=250)로 코스피·코스닥 **1년 일별 외국인/기관/개인 순매수**와 **KOSDAQ 거래량(accTradeVolume)**을 수집(누적순매수 차트·거래량 정상화). KoreaMacroAgent 가 `korea_investor_stocks.kosdaq_buy/sell` 도 채움(누락 방지).
> - **3.1.4 반도체/AI 표** — `semi_ai_breakdown` 각 행 `aum`(시총) 필수 + 1Y series(`nmr_semi_series.json`)로 `charts/semi_<i>.png` 생성(`gen_rest_charts.py` 보강).
> - **3.2.1 HY 스프레드** — FRED `BAMLH0A0HYM2`/`…EY` 1년 일별 CSV 로 현재·1주~1년 레벨·`hy_oas_chart.png` 채움(현재값만 있던 문제 해결).
> - **3.2.2 미국 ETF** — 사용자 `3.2.2_미국ETF시황.html` 기준으로 수익률·추세평가 정합.
> - **3.2.4 CAPEX** — 미확인 칸은 "-" 대신 **"미공개"**(에이전트·빌더 양쪽).
> - **2.3 빅테크 이벤트** — ★★ 포함 8~12건으로 확대(★★★만 금지).
> - **5 환율** — CNY/KRW 시계열을 USD/KRW÷USD/CNY 로 도출해 추세차트 생성.
>
> v3.6.9 (plugin 1.7.9) 변경점 — 3.2.3 미국 지수 정기 리밸런싱 섹션 신설 (2026-06-14 사용자 피드백):
> - **3.2.3 미국 지수 정기 리밸런싱(신설)** — S&P 500·나스닥 100 의 **편입/편출 종목(사업 내용·사유 포함)**, 분기/연례 적용 일정, S&P 편입 기준, 나스닥 **2026-05-01 패스트엔트리 룰 변경**(상위 40위·15거래일 조기편입 / 10% float 폐지→3x cap / 10bp 중간편출 폐지), 패스트엔트리 후보 대형 IPO(SpaceX·OpenAI·Anthropic). 데이터 `markets.index_rebalance`(빌더 `renderIndexRebalance`), 편입=초록·편출=빨강. 신규 **IndexRebalanceAgent**(WebSearch·1차 출처 grounding) Phase 1 병렬 수집에 추가.
> - **기존 3.2.3 CAPEX → 3.2.4 로 이동** (3.2.1 HY → 3.2.2 ETF → 3.2.3 리밸런싱 → 3.2.4 CAPEX 순).
> - `references/agents.md` IndexRebalanceAgent·`data-schema.md` index_rebalance 참조. 구성종목·일정은 press.spglobal.com / ir.nasdaq.com 1차 출처로만 확인(기억 생성 금지, 미확정은 `미확인`).
>
> v3.6.8 (plugin 1.7.8) 변경점 — 3.2.2 주요 미국 ETF 섹션 신설 (2026-06-14 사용자 피드백):
> - **3.2.2 주요 미국 ETF(신설)** — 미국 대표 지수추종(SPY·VOO·SPYM·QQQ·QQQM·DIA), 11개 S&P 500 섹터(XLK~XLU, S&P500 비중 표기), 테마/특화(SOXX·SMH·BOTZ·ARKK·SCHD·JEPI·QTUM·NASA·ICLN·ROBO·AIQ·MAGS), 방어형(GLD·TLT·IEF) **32종**을 4개 그룹 표로. 각 행: 티커·ETF설명·현재가·1주·1개월·3개월·6개월·1년 수익률(±색)·**추세(1년) 스파크라인**·추세평가. 데이터 `markets.us_etfs`(빌더 `renderUSEtfs`), 1년 주봉은 `nmr_etfseries.json` → `gen_rest_charts.py` 가 `charts/spark_etf_<티커>.png` 생성.
> - **기존 3.2.2 CAPEX → 3.2.3 으로 이동** (3.2.1 HY 스프레드 → 3.2.2 ETF → 3.2.3 CAPEX 순).
> - **신규 UsEtfAgent** — Phase 1 병렬 배치에 추가(Yahoo `get_historical_stock_prices` 주봉 기본, FMP 는 플랜 제한 시 폴백). 수익률은 주봉 가격수익률이라 분배금 큰 ETF(SCHD·JEPI·채권형)는 총수익률보다 낮게 표기됨을 그룹 코멘트에 명시. 신생 ETF(NASA)는 3·6개월 null 허용. `references/agents.md` UsEtfAgent·`data-schema.md` us_etfs 참조.
>
> v3.6.7 (plugin 1.7.7) 변경점 — 3.1.4 반도체/AI 상세표·테마 확장 (2026-06-14 사용자 피드백):
> - **3.1.4 반도체/AI 대표 ETF·종목 시총순 상세표(신설)** — `markets.semi_ai_breakdown`: [{name, aum(시총 억원), note(간단 설명), chart("charts/semi_<i>.png" 또는 "")}] + `markets.semi_ai_comment`(현황·코멘트). 추세(1Y) 셀은 chart 가 비면 "-" 로 표시. 미존재 ETF(예: 삼성+하이닉스 50:50 단일 2배 레버리지)는 수록하지 말 것.
> - **3.1.4 반도체·AI 테마 통합** — 두 테마를 "반도체/AI" 한 행으로, 대표 ETF 는 **하나만** 표기(`korea_theme_etfs["반도체/AI"]`). 테마는 자유 확장 가능(예: 신재생에너지·K화장품·K-푸드) — 각 테마 1년 series 를 `nmr_themeseries1y.json[테마명]` 에 넣으면 `gen_rest_charts.py` 가 theme_<테마>.png 자동 생성.
> - **3.1.2 종목 — 풍부한 형식·정확성 우선** — `kospi_buy/sell` 등 detail 은 "외국인 순매수 X억원(N위, 주가 ±%, 외국인 지분율 Y%)" 형식. 당일 마감 공개 출처에 확정된 종목만 수록(예: 급등일 외국인 순매수 상위 6종만 공개되면 6종만, 7위↓ 보류) — 직전일 등 비교 불가 데이터로 채워 왜곡 금지, `note` 에 사유.
> - **PDF 는 soffice(LibreOffice) 유지** — 기본 변환은 Phase 4 soffice 그대로. (트러블슈팅에 VM 장애 시 대응 추가.)
>
> v3.6.6 (plugin 1.7.6) 변경점 — 2.1/2.2 빅테크 제외·표 가드 (2026-06-14 사용자 피드백):
> - **2.1/2.2 빅테크 이벤트 자동 제외** — 빌더가 `BIGTECH_EVENT_RE`(언팩·갤럭시·아이폰·WWDC·GTC·CES·MWC·메타 커넥트·구글 I/O·Ignite·re:Invent·키노트·신모델 등)로 `events_calendar`·`events_calendar_longterm` 을 필터링해 **빅테크 신제품·신기술 이벤트는 2.3 에만** 표시(에이전트가 캘린더에 넣어도 자동 제외). 2.1/2.2 는 매크로·정책·지표·IPO 만.
> - **표 비객체 행 가드** — `renderMarketBlockC` 가 섹션 딕셔너리의 비객체 값(잘못 중첩된 `energy_comment` 문자열 등)을 표 행으로 렌더하지 않도록 가드(빈 "ENERGY_COMMENT" 행 버그 수정). 섹션 코멘트는 top-level `commodities.energy_comment`/`metals_comment`/`agri_comment` 만 사용, 섹션 딕셔너리 안에 넣지 말 것.
> - **3.1.2 순매도 폴백** — 당일이 외국인·기관 동반 순매수(쌍끌이)면 종목별 순매도 랭킹이 공개 안 되므로, **직전 거래일 기준**(한국투자증권 공개 순위 등)으로 순매도 상위를 대체 표기하고 기준일·사유를 `note` 에 명시.
> - **원자재 변화율 보완** — 1주·1년만 있고 1·3·6개월이 비면 `nmr_series2.json` 1년 주봉으로 계산해 채움(4.1~4.3·4.5).
> - **CAPEX 미공개** — `bigtech_capex.rows[].y2027/y2028` 미확인 칸은 "-" 대신 "미공개" 표기.
>
> v3.6.5 (plugin 1.7.5) 변경점 — 한국 수급·테마·부록 정밀화 (2026-06-14 사용자 피드백):
> - **3.1.1/3.1.2 수급 1년 일별화** — 코스피·코스닥 외국인·기관·개인 누적순매수 차트를 1일치→**1년 일별**로(다음금융 `market_index/days`, 네이버 SPA 404 대체). **KOSDAQ 거래량**은 야후 ^KQ11 손상분을 다음금융 `accTradeVolume` 로 교체.
> - **3.1.2 4리스트** — 코스피/코스닥 **순매수·순매도 주요 종목** 각 ~10 (`kospi_buy/kospi_sell/kosdaq_buy/kosdaq_sell`, 각 {name,detail}). 빌더가 4개 리스트로 렌더(구 외국인순매수/기관강세 폐기). 순매도 비공개 시 빈배열+note.
> - **3.1.3 설명+최신상단** — 빌더가 "선행지수↔KOSPI 정비례·약 2개월 선행", "100 이상=확장/100 이하=침체" 설명을 자동 표기. `korea_leading` 은 통계청(국가데이터처) 확정치, **최신이 맨 위(내림차순)**.
> - **3.1.4 테마 AI·원자력 추가·순서조정** — 반도체·AI·전력기기·조선·방산·원자력·증권·로봇·우주. `gen_rest_charts.py` 가 `nmr_themeseries1y.json` 의 **모든 테마 키로 theme_<테마>.png 데이터 주도 생성**.
> - **3.2/3.3/3.4 지수 스파크라인** — `nmr_indexseries.json`(17개 지수 1년 주봉)으로 `gen_rest_charts.py` 가 `spark_<key>.png` 생성, 추세열을 채움.
> - **2.3 빅테크 이벤트 중복 제거** — 2.1/2.2 의 빅테크 신제품·신기술·실적 이벤트는 2.3 에만 표시(2.1/2.2 는 매크로·정책·IPO 만), 2.3 날짜 오름차순.
> - **부록A 13F 정밀화** — 빌더 스키마(new_buys/added/reduced/exited/top_holdings.weight_or_value 등)에 정확히 맞춰 수집(필드명 불일치로 비던 문제 해결).
> - **빌더 안정화** — 이미지셀 빈 경로/디렉터리 readFileSync(EISDIR) 가드, 3.1.1 기준일(asof) 동적 표기.
>
> v3.6.4 (plugin 1.7.4) 변경점 — 표지·섹션·수집 품질 개선 (2026-06-14 사용자 피드백):
> - **표지 배지줄 제거** — 표지의 "Top News · 이벤트 캘린더 · … · 포트폴리오" 한 줄 삭제(build_report.js 표지 영역).
> - **5 환율 USD/EUR** — 기존 EUR/USD(≈1.16) 대신 **USD/EUR**(=1/EURUSD≈0.86, 1달러당 유로)로 표기. MarketsAgent 가 `markets.fx_usd.usd_eur`(역수 시계열 기준 현재치·1주~1년 변화율) 수집, 시계열 `s2.fx.usd_eur`(spark_usd_eur.png).
> - **4 원자재 섹션별 추세 코멘트** — 4.1 에너지/4.2 금속/4.3 농산물 각 표 아래 "추세 평가:" 코멘트. CommoditiesAgent 가 `commodities.energy_comment`/`metals_comment`/`agri_comment` 수집.
> - **3.2.2 CAPEX 2027·2028 전망 열 추가** — `markets.bigtech_capex.rows[].y2027`·`y2028`(확인된 전망만, 출처 필수).
> - **7 한국 5대 증권사 — 공식 채널 최신 리포트 우선** — 각 사 공식 리서치 목록 URL(신한·미래에셋·삼성·한국·키움; `references/agents.md` SecuritiesAgent 표)에서 **발행일 D-1 이내 최신 리포트** 수집. JS 렌더가 많아 **메인 세션이 Claude in Chrome navigate→get_page_text** 로 직접 읽는다. **최신 공식 리포트를 못 구한 사만** 뉴스 폴백(말미 `(뉴스 기반)`). (기존: 키움만 리포트·나머지는 오래된 뉴스였던 문제 수정.)
> - **8 글로벌 IB — 최신만** — 발행일 D-1 이내 최신 하우스 뷰만, 오래된 코멘트 배제, 못 구할 때만 뉴스.
> - **차트 생성을 9~12 분석 전으로 이동** — Phase 1(수집) 직후 **Phase 1.5 차트 생성**, 그 다음 Phase 2 AnalysisAgent(9~12). 분석이 차트·시계열을 근거로 작성되도록.
> - **차트 스크립트 세션경로 자동탐지(버그픽스)** — `gen_tech_charts.py`·`gen_rest_charts.py` 의 하드코딩 세션경로(`/sessions/upbeat-elegant-allen/...`)를 `argv[1] > NMR_OUT > glob('/sessions/*/mnt/outputs')` 자동탐지로 교체. (구버전은 새 세션에서 nmr_*.json 을 못 찾아 차트가 통째로 누락 — 3.1.1/3.1.4/3.2.1/6.2 그래프 실종의 근본원인.)

> v3.6.3 (plugin 1.7.3) 변경점 — 자동 push 절차 버그픽스 (2026-06-13):
> - **credential helper 토큰 전달 수정** — helper 는 별도 프로세스로 실행되므로 `GH_TOKEN` 을 반드시 `export` 해야 인식한다 (export 누락 시 빈 값이 전달돼 GitHub 가 "Invalid username or token" 으로 거부 — 실제로 이 버그로 여러 번 실패함). 또한 샌드박스 bash 의 `grep … githubtoken.txt` 는 긴 fine-grained 토큰(약 93자)을 잘라 읽으니, 토큰은 Read 도구(호스트 직접)로 전체값을 확인해 사용한다. 검증된 one-shot 대안(token-in-URL)도 병기. '## 플러그인 유지보수·배포 (git push)' 2번 항목 참조.
>
> v3.6.2 (plugin 1.7.2) 변경점 — 플러그인 배포 자동화·인덱스 복구 (2026-06-13 사용자 피드백):
> - **플러그인 수정 후 git push 자동화** — `D:\claudeCowork\SECURITY\githubtoken.txt` 에 GitHub 토큰이 있으면 추가 질문 없이 그 토큰으로 `origin main` 에 push 한다 (토큰은 비공개·일회성 credential helper 로만 전달, URL/로그/커밋 노출 금지). 신설 '## 플러그인 유지보수·배포 (git push)' 섹션 참조.
> - **마운트 잘림 회피 커밋 절차 + 로컬 인덱스 자동 복구** 도 같은 섹션에 문서화 — 손상된 `.git/index`("index file corrupt")는 사용자에게 미루지 말고 직접 `git read-tree HEAD` 로 재생성한다 (푸시엔 영향 없음).
>
> v3.6.1 (plugin 1.7.1) 변경점 — Gmail 미기동 시 발송 폴백 (2026-06-13 사용자 피드백):
> - **메일 발송 시 Gmail 이 안 켜져 있어도 됨** — Claude in Chrome 으로 `https://mail.google.com/mail/u/0/?ogbl#inbox` 로 `navigate` 하면 바로 받은편지함이 열린다. **로그인은 항상 유지**되므로 비밀번호 단계 없이 그대로 작성·PDF 첨부·발송한다. (`references/email-sending.md` 발송 전제 #2·발송 절차 #2·트러블슈팅에 반영.) Phase 5 절차는 동일.
>
> v3.6.0 (plugin 1.7.0) 변경점 — 시각화 대폭 강화·섹션 재편 (2026-06-13 사용자 피드백):
> - **3.1.1 한국 증시 기술적 멀티패널 차트** — 코스피·코스닥 각각 1년 일봉 캔들 + 이동평균(5·20·60·120) + 볼린저밴드 / 거래량 / RSI / **외국인·기관·개인 누적순매수**(빨강·파랑·초록)를 한 장의 차트로. 차트 생성은 `scripts/gen_tech_charts.py`(mplfinance). 데이터: 새 KoreaTechAgent 가 `nmr_kr_ohlcv.json`(^KS11·^KQ11 1년 일봉 OHLCV + 네이버금융 일별 투자자 순매수 시계열) 수집 → 빌더 `markets.korea_investors.{kospi,kosdaq}_chart`·`tech:true`. 투자자별 순매수 표는 **최근 장 마감일 1일 기준**임을 명시.
> - **3.1 하위 섹션 재번호** — 3.1.1 외국인 수급(차트) / **3.1.2 투자자별 순매수·순매도 주요 종목(신설, `markets.korea_investor_stocks`)** / 3.1.3 경기선행지수 순환변동치(**최신순 정렬**, 통계청 `markets.korea_leading`+value) / 3.1.4 순환매 테마(대표 ETF + **1년** 미니차트, `markets.korea_theme_etfs`/`korea_theme_charts`).
> - **2.3 빅테크 이벤트** — 시기 순(날짜 오름차순) 정렬, '중요한 것만' 폭넓게 수록.
> - **1년 추세 스파크라인 전면 도입** — 3.2/3.3/3.4(지수)·4.1~4.3·4.5①ETF·5(환율)의 모든 행에 '추세(1년)' 그래프 열 추가(`renderMarketBlockC`/`trendRowC`, `charts/spark_<key>.png`). 차트는 `scripts/gen_rest_charts.py`. 지수·원자재·환율 1년 주봉 시계열은 IndexSeriesAgent(`nmr_series.json`/`nmr_series2.json`).
> - **3.2 변동값 강조** — `renderMarketBlockC(...,prev)`+`trendRowC(...,changed)`로 직전 보고서(`markets.us_prev`) 대비 현재치가 바뀐 행은 **빨간색·볼드**. (메인 세션이 직전 연결폴더 JSON 의 us_markets current 를 `us_prev` 로 주입.)
> - **5 환율 확장** — USD/JPY(JPY=X)·USD/CNY(CNY=X)·EUR/USD(EURUSD=X) 행 추가(`markets.fx_usd`), **HKD/KRW** 는 USD/KRW÷USD/HKD(약 7.8 페그)로 환산해 '-' 제거.
> - **6 암호화폐 재편** — 구 6.2 공포·탐욕 표 **삭제**, 6.5 코인 차트 섹션을 **6.2 로 이동**: BTC·ETH·XRP·SOL 각 1년 가격+거래량 + 공포·탐욕 1년 라인 차트(`crypto.charts`, `scripts/gen_rest_charts.py` 의 coin/fng). 코인 1년 일봉·F&G 1년은 CryptoSeriesAgent(`nmr_crypto_series.json`).
> - **부록 신설** — 기존 14장 → **[부록A] 워런 버핏·버크셔 13F**(BerkshireAgent `nmr_berkshire.json` → `data.berkshire`), **[부록B] 최신 AI Trends**(AINewsAgent: news.hada.io·/weekly·특이점 갤러리+웹검색, ≤10건, `data.ai_trends`). 목차도 반영.
> - **차트 파이프라인** — Phase 4 직전 '차트 생성' 단계 추가: 위 시계열 JSON 들을 입력으로 `gen_tech_charts.py`·`gen_rest_charts.py`·`gen_hy_chart.py` 를 실행해 `<WORK>/charts/*.png` 생성(빌더가 상대경로로 임베드, 파일 없으면 해당 차트만 생략). `pip install mplfinance matplotlib pandas`. PDF 변환 시 한글 폰트 임베드 동일.
>
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


---

## (참고) agents.md 변경이력 — v3.7.0 에서 분리

> **v3.6.32 (2026-06-19) — 수집 강제(게이트 통과 필수). `scripts/verify_report.js` 가 아래를 코드로 검사하며, 미달이면 발송이 차단되고 사용자에게 질문한다. carry-forward·열등 폴백·stale 로 때우지 말 것.**
> - **USMacroExtrasAgent — 점도표 완전수집(req7)**: `fomc_dotplot.rows` 의 2026·2027·2028말·장기중립 각 행에 **`jun` 과 `mar` 중간값을 모두** 채운다(빈칸·"-" 금지). FOMC SEP(연준/언론 표)에서 6월·3월 중간값 직접 확인.
> - **KoreaSemiThemeAgent — ETF 20 + series(req3-5)**: `semi_ai_etfs` 는 **항상 AUM 상위 20**(다음금융 `api/search/quotes`+`marketCap` 정렬, 단일종목 레버리지 포함). 8테마 대표 ETF·종목10·ETF20 의 1년 주봉 series 를 `nmr_themeseries1y.json`/`nmr_semi_series_v3.json` 에 채워야 `theme_*`·`semi_s_*`·`semi_e_*` 차트가 생성(빈 series=추세 '-'=게이트 실패).
> - **3.1.1 일봉 OHLC(req1)**: 메인세션이 야후 `^KS11`/`^KQ11` `interval=1d` 로 `nmr_kr_ohlcv.json` 일봉 OHLC 를 채워 `gen_kr_candle.py` 캔들(`kospi_tech.png`/`kosdaq_tech.png`) 생성. flows 라인차트 대체 금지.
> - **SecuritiesAgent·GlobalSecuritiesAgent — 신선도 코드강제(req8)**: `key_reports[].date` 가 Daily≤1·Weekly/Monthly≤3일(월요일·주말은 금요일까지) 초과면 게이트가 stale 로 막는다. **메인세션 Chrome 공식 페이지 직접 수집** 1순위, 못 구하면 빈값(stale 금지).


> **v3.6.31 변경점 (2026-06-19 사용자 피드백 — 7개 재발 이슈 근본수정)**
> "cowork 새 작업마다 같은 섹션이 깨진다"의 영구 수정. 근본원인 = **빌더는 정상이나 데이터/차트 입력이 불안정하면 빌더가 해당 섹션을 조용히 생략**한다는 것 → 차트는 스크립트 폴백, 데이터는 수집 강제+직전값 carry-forward 로 항상 채운다.
> - **6.3 김치프리미엄 SOL 항상 채움 (CryptoAgent 필수)**: `get_kimchi_premium` 결과의 BTC/ETH/XRP/SOL 중 **하나라도 null/"데이터 부족"이면 즉시 CoinDesk MCP `fetch_spot_tick`(market=upbit `<SYM>-KRW` + market=binance `<SYM>-USDT`)로 직접 계산**해 채운다(특히 SOL 이 자주 빔). 김프=(업비트KRW/(바이낸스USD×환율)−1)×100, 환율=Yahoo `KRW=X`. 4종 모두 `premium_pct`/`upbit_krw`/`binance_usd`/`status` 비우지 말 것. 그래도 못 구한 코인만 null+`note`.
> - **8 글로벌 IB 최신성 엄격 (GlobalSecuritiesAgent)**: UBS·GS·JPM·MS·BlackRock 각각 **발행일 D-1(Daily)/D-3(Weekly·Monthly) 이내 공개 자료만** 사용. 연간 전망·수주 지난 하우스뷰로 채우지 말 것. 기준 충족 자료가 없으면 `key_reports:[]`, `key_message:"기준일(D-1/D-3) 충족 최신 공개 자료 미확인"`. 검색에 주·날짜를 넣어 최신만 찾는다("UBS CIO house view June 2026 week", "<IB> outlook FOMC June 2026"). 각 항목 발행일(YYYY-MM-DD) 명시.
> - **3.2.1 CAPEX · 3.2.2 FOMC 점도표 신규 수집 (USMacroExtrasAgent — Phase 1 추가)**: 매 실행 WebSearch 로 수집해 빌더가 두 섹션을 항상 렌더하게 한다(미수집=빌더 자동생략=과거 "표시안됨"의 원인).
>   - `markets.bigtech_capex={rows:[{company,y2025,y2026,y2027,y2028,comment}],comment}` — MSFT·Alphabet·Amazon·Meta 연간 CAPEX(실적+가이던스). 미확인 칸은 ""(빌더가 "미공개").
>   - `markets.fomc_dotplot={summary,rows:[{item,jun,mar,change}],distribution:[{label,count}],policy_rate,next_meeting,background:[],market_impact,sources:[]}` — 최신 FOMC 점도표(직전 대비). 최소 summary·policy_rate·rows(2026/2027/2028말·장기중립 중간값)는 채울 것.
>   - 저장 `nmr_usmacro.json` → 병합 시 `markets.bigtech_capex`/`markets.fomc_dotplot` 로 주입.
> - **carry-forward (병합 단계 — slow-change last-known-good)**: 이번 런에서 `bigtech_capex`·`fomc_dotplot`·`us_credit`/`hy_spread` 가 비면 연결폴더 `_market_report_data/` 의 **직전 report_data_*.json 에서 가져와 채운다**(분기/월 단위로만 바뀌므로 직전값이 정확). 그래도 없으면 섹션 생략.
> - **3.1.1/3.1.3/3.2.3 차트는 스크립트 폴백으로 항상 생성** (scripts 변경 — SKILL Phase 1.5): gen_kr_candle.py(일봉 없으면 주봉 폴백)·gen_leading_chart.py(장기 series 없으면 korea_leading 값)·gen_hy_chart.py(FRED series 없으면 hy_spread 6레벨, **출력 charts/hy_oas.png**). 입력이 불안정해도 표에 있는 값으로 그래프를 만든다.


> **v3.6.28 변경점 (2026-06-18 사용자 피드백 — 부록B 한/영·5장 환율 스파크라인·이미지 복구버그)**
> - **[부록B] AI Trends 한/영 2종 병기**: AINews+Berkshire 에이전트의 `ai_trends.items[]` 각 항목은 **기본=한글**(`title`/`summary` 한국어) + **영어 번역본**(`title_en`/`summary_en`)을 함께 담는다. 원문이 영어라도 title/summary 는 반드시 한국어로 번역해 넣고, 영어 원문은 title_en/summary_en 에 둔다(영어 공부용). 빌더 renderAITrends 가 한글 본문 아래 "EN ▸ ..." 로 영문본을 렌더한다.
> - **5장 환율 스파크라인 항상**: IndexSeriesAgent(또는 MarketsAgent)가 `nmr_series2.json.fx` 에 **원화 5쌍** `usd_krw,eur_krw,jpy_krw,cny_krw,hkd_krw` 1년 주봉 시계열을 반드시 포함한다(야후 `KRW=X`/`EURKRW=X`/`JPYKRW=X`/`CNYKRW=X`, hkd_krw=usd_krw÷`HKD=X`; cny_krw 희박 시 usd_krw÷`CNY=X`). gen_rest_charts.py 가 s2.fx 키로 `charts/spark_<key>.png` 를 생성하므로 이 5쌍이 있어야 5장 추세열 "-" 가 사라진다. usd_jpy/usd_cny/usd_eur 도 함께.
> - **이미지 .undefined 복구버그**: build_report.js 의 `ImageRun` 2곳에 `type:"png"` 명시(docx 9.x 필수). 누락 시 이미지 파트가 `.undefined` 로 저장돼 Word "일부 콘텐츠를 읽을 수 없습니다" 복구창이 뜬다.

> **v3.6.23 변경점 (2026-06-17)**
> - **3.1.2 코스닥도 외국인/기관 각 상위 10** 수집(다음 investor_purchase 응답 BUY/SELL 상위 10).
> - **7 SecuritiesAgent → 메인세션 Chrome 직접 수집**: 5개 증권사 공식 리서치 페이지(신한·미래에셋·삼성·한국투자·키움)는 JS 렌더라 WebSearch/web_fetch 로 목록이 안 보인다. **메인 세션이 Claude in Chrome 으로 직접 navigate→get_page_text(또는 screenshot)** 해 최신(D-1/D-3) 리포트를 읽고 발행일을 명시한다. WebSearch 단독으로 "자료없음" 판정 금지. (네이버 금융만 환경 차단, 이 5사·다음은 접근 가능.)

> **v3.6.22 변경점 (2026-06-17 사용자 피드백)**
> - **3.1.2 표 병합**: `korea_investor_stocks` 데이터 구조는 동일(8개 리스트). 빌더가 외국인(좌)·기관(우)를 한 표로 병합 렌더하므로 4개 리스트 쌍(코스피 매수/매도, 코스닥 매수/매도)을 모두 채울 것.
> - **7·8 신선도 = 웹검색에도 적용**: SecuritiesAgent·GlobalSecuritiesAgent 는 WebSearch 결과라도 발행일이 D-1(Daily)/D-3(Weekly·Monthly) 기준을 넘으면 사용 금지(주말이면 금요일 허용). 기준 충족 자료가 없으면 `key_message:"기준일(D-1/D-3) 충족 최신 공개 자료 미확인"` 으로 두고 오래된 자료로 채우지 않는다(빈 stub 허용).

> **v3.6.21 변경점 (2026-06-17 사용자 피드백)**
> - **3.1.2 종목 수급 = 다음금융 investor_purchase API (네이버는 차단)**: finance.naver.com 은 실행 환경에서 web_fetch·Chrome 모두 플랫폼 차단이므로 사용 불가. 메인세션이 Claude in Chrome 으로 `https://finance.daum.net/domestic/influential_investors` 진입 후 동일출처 fetch `https://finance.daum.net/api/trend/investor_purchase/?market={KOSPI|KOSDAQ}&investorType={FOREIGN|INSTITUTION}&...`(나머지 buyFieldName/buyOrder/sellFieldName/sellOrder/limit 파라미터는 페이지가 보낸 값 그대로 재사용). 응답 `data.BUY`/`data.SELL` 각 `{name, straightPurchasePrice(원), changeRate}`. 4조합으로 `korea_investor_stocks`(코스피 10·코스닥 5, detail="순매수/순매도 X억원") 채운다.
> - **3.2.0 CAPEX**: `bigtech_capex` 는 미국 증시 섹션 맨 앞(3.2.0)에 렌더(빌더 `renderUSExtras` 최상단).
> - **7·8 항상 채움**: SecuritiesAgent·GlobalSecuritiesAgent 는 D-1/D-3 신선자료 1순위, 없으면 **WebSearch 로 최신 공개 시각을 찾아 반드시 채운다**(빈값 금지, 발행일 명시).

> **v3.6.20 변경점 (2026-06-17 사용자 피드백 — 매 실행 반드시 적용)**
> - **3.1.1 KOSDAQ 거래량**: KoreaTechAgent/메인세션이 다음금융 `accTradeVolume`(동일출처 fetch)로 `kosdaq`/`kosdaq_ohlcv` 거래량 컬럼을 교체(야후 ^KQ11 거래량은 손상). 거래량 패널이 항상 정상 표시되어야 한다.
> - **3.1.2 종목 수급**: `korea_investor_stocks = {asof, note, kospi_foreign_buy[10], kospi_inst_buy[10], kospi_foreign_sell[10], kospi_inst_sell[10], kosdaq_foreign_buy[5], kosdaq_inst_buy[5], kosdaq_foreign_sell[5], kosdaq_inst_sell[5]}` (각 `{name,detail}`). **NaverSearch(PLAY) MCP**·다음금융 우선. 확정 출처 없는 리스트는 빈배열+note(추정 금지).
> - **3.1.4 수익률**: `markets.korea_theme_rows`(8테마 `{theme,direction,comment,etf,current,"1w_pct".."1y_pct",trend,chart}`)·`markets.semi_ai_stocks`(10)·`markets.semi_ai_etfs`(**정확히 20**, 단일종목 레버리지 포함 AUM순) 각 항목에 current·1주~1년 수익률·trend·chart 채운다. 빌더가 2줄(설명행+수익률행)로 렌더.
> - **4.5 전략광물 ETF**: LIT·REMX·URA·URNM 1년 주봉 → `nmr_strat_series.json` 으로 `charts/spark_lit|remx|ura|urnm.png` 생성, `commodities.strategic_metals.etf[].{current,1w_pct..1y_pct,trend}`.
> - **6.2 코인 차트(CryptoSeriesAgent 필수)**: BTC·ETH·XRP·SOL 1년 `[date,price,volume]`(CoinDesk `fetch_spot_ohlcv`, market=binance, 폴백 야후 `*-USD`)+공포탐욕 1년 `[date,value]`(alternative.me `fng/?limit=400`) → `nmr_crypto_series.json` → `charts/coin_*.png`·`fng_1y.png` → `crypto.charts`.
> - **7 SecuritiesAgent·8 GlobalSecuritiesAgent — 신선도 규칙(엄격)**: Daily 자료는 발행일 **D-1 이내**, Weekly/Monthly 는 **D-3 이내**만 사용. 주말이면 **금요일 자료** 허용. 그 외 오래된 자료는 사용 금지(미확보 시 빈값). 발행일을 `key_reports[].date`·`key_message` 에 명시.

> **v3.6.17 변경점 (2026-06-16 사용자 피드백 — 27개 항목 항상 포함). 아래 데이터·시계열을 매 실행 반드시 수집한다.**
> Phase 1.5 차트는 `scripts/gen_all2.py`(코스피·코스닥 캔들+거래량+누적순매수, 원자재·전략광물·테마·반도체종목·FX 스파크라인) + `scripts/gen_semi_etf.py`(반도체 ETF 추세, 다음 charts API series) + `scripts/gen_kr_flows.py` 로 생성.
> - **KoreaTechFlowsAgent** → `nmr_korea_tech.json`: ① `kr_ohlcv`={kospi,kosdaq:[[date,o,h,l,c,v]…]} **1년 일봉**(야후 `^KS11`/`^KQ11` interval=1d, 캔들용) ② `korea_investor_stocks` **8리스트**(`kospi_foreign_buy/inst_buy/foreign_sell/inst_sell` 각 10, `kosdaq_*` 각 5; 각 {name,detail}; 다음금융+NaverSearch 뉴스, 부분이면 note) ③ `korea_leading` value(숫자)+mom.
> - **KoreaSemiThemeAgent** → `nmr_semi.json`: `semi_ai_stocks`(시총 상위 10, {name,ticker,aum,note}), `semi_ai_etfs`(**AUM 상위 20, KODEX 삼성전자·SK하이닉스 단일종목레버리지 필수 포함**, {name,ticker,aum,note}), `stock_series`/`etf_series`/`theme_series`(8테마 키=반도체/AI·전력기기·조선·방산·원자력·증권·로봇·우주) 1년 series, `theme_etfs`(테마→대표ETF **문자열**). 신규상장 ETF series 는 다음 `/api/charts/A{code}/days`(메인세션이 `finance.daum.net/quotes/A{code}` 페이지에서 동일출처 fetch — Referer 수동설정 불가).
> - **CommoditySeriesAgent** → `nmr_commod.json`: energy/metals/agriculture/strategic_metals + 각 행 **2문장 한글 trend** + `series`{wti,brent,natgas,gold,silver,copper,platinum,corn,soybean,wheat,lit,remx,ura,urnm} 1년 주봉(추세그래프용).
> - **MarketsTrendAgent** → `nmr_trendtext.json`: asia(6)/europe(3)/fx(9) **2문장 한글 추세평가** + `fx_series`{usd_jpy,usd_cny} 1년 주봉.
> - **UsEtfTrendAgent** → `nmr_usetf_trends.json`: 29 ETF별 2문장 한글 추세평가(예 "강한 상승추세·가속 국면…").
> - **NewsBerkAgent** → `nmr_news2.json`: `events_calendar_longterm` ★★★ **8~10건**(2.2 풍부화), `berkshire`(new_buys/added/reduced/exited + top_holdings **최대 20**, note 필드).
> - 병합(merge): asia/europe/fx/us_etf trend 텍스트를 각 항목 `.trend`에 주입, `ai_trends`는 `{as_of,sources_checked,items}`로 래핑, 나스닥100 schedule 은 연례행만 남김, korea_theme_etfs 는 nmr_semi 문자열 사용.
>
> **v3.6.16 변경점 (2026-06-15 사용자 피드백 — 3.1.x/6.x 1차출처 정밀화, 반복 누락 근본차단)**
> 아래 출처·절차를 그대로 따른다(WebSearch 폴백 최소화). 한국 수급/선행지수/코인 시계열이 비거나 부정확했던 문제의 영구 해법이다.
> - **3.1.1 한국 기술차트·수급 (다음금융 동일출처 fetch)**: Claude in Chrome 로 `navigate https://finance.daum.net/domestic` 후 `javascript_tool` 에서 동일출처 fetch:
>   `fetch('https://finance.daum.net/api/market_index/days?page=1&perPage=250&market=KOSPI&pagination=true',{headers:{Referer:'https://finance.daum.net/',Accept:'application/json'}})` (KOSDAQ 동일). 응답 `data[]` 의 `tradePrice`(종가)·`accTradeVolume`(거래량)·`foreign/institution/individualStraightPurchasePrice`(원→억원 ÷1e8) 를 **오름차순**으로 1년 일별 수집. 반환 잘림 회피: 결과를 `document.body.innerHTML='<pre>...</pre>'` 로 덤프 후 `get_page_text` 로 한 번에 회수(20KB 가능). ⚠️ **지수 OHLC 캔들 API(`/api/charts/...`)는 심볼 Referer 로도 403** 이므로 캔들 대신 **종가선 멀티패널** 차트를 쓴다 → `<O>/kospi_daily.csv`·`kosdaq_daily.csv`(행 `date,close,vol,F억,I억,P억`) 저장 후 `scripts/gen_kr_tech.py` 로 `charts/kospi_tech.png`·`kosdaq_tech.png` 생성(종가+MA5/20/60/120+볼린저 / 거래량 / RSI / 외국인·기관·개인 누적순매수). 빌더 데이터 `markets.korea_investors`={tech:true,asof,source,kospi:{level,foreign,institution,individual,comment},kospi_chart,kosdaq:{...},kosdaq_chart}; level·순매수 3종은 **최신 마감일** 값(예 `"+1.08조"`,`"-1.51조"`).
> - **⚠️ 야후 주봉 current stale 주의**: `^KS11`/`^KQ11` 주봉 current 가 며칠 지연될 수 있다(실측 KOSPI 8123(야후 06-12 부분주봉) vs 다음 8546(06-15)). **한국 지수 current·1주~1년 등락률은 다음 일별 CSV 로 산출**해 `markets.korea.{kospi,kosdaq}` 에 넣는다.
> - **3.1.2 종목별 수급 (다음 메인 위젯 DOM)**: `finance.daum.net/domestic` 렌더 후 외국인/기관 **순매수 상위** 위젯의 DOM 텍스트를 파싱(행이 `코스피종목 | 코스닥종목` 교차, 표기 %는 당일 주가등락률·순매수 금액순). `markets.korea_investor_stocks={asof,source,kospi_buy[],kospi_sell[],kosdaq_buy[],kosdaq_sell[],note}`(각 {name,detail}). 순매도 탭은 SPA 동작상 별도(미수집 시 note 명시). 네이버 sise_deal_rank 는 web_fetch 차단(blocklist)·Chrome 차단이라 사용 불가.
> - **3.1.3 경기선행지수 순환변동치 (통계청 보도자료 직접 — WebSearch 금지)**: KOSIS statHtml·e-나라지표(index.go.kr)는 iframe/AJAX 로 데이터 미노출·렌더 멈춤이 잦다 → **통계청(국가데이터처) 보도자료**로 직접 간다: `navigate https://mods.go.kr/board.es?mid=a10301050100&bid=216&act=list` (산업활동동향 게시판) → 최신 `2026년 N월 산업활동동향` view(`...&act=view&list_no=<번호>`)에서 `□ (경기) 동행종합지수 순환변동치는 전월대비 X.Xp …, 선행종합지수 순환변동치는 전월대비 Y.Yp …` 문장 파싱. 최근 3개월(직전 list_no 들)도 동일 수집. **절대 순환변동치 수준은 보도자료 HTML 엔 없고 PDF 전용** → 공식 헤드라인인 **전월차(±p)** 로 `markets.korea_leading=[{period,value:null,mom:"+0.6p",note:"통계청 산업활동동향 게시 YYYY-MM-DD"}]` 채우고 comment 에 3개월 추세·KOSPI 약 2개월 선행 관계 명시.
> - **3.1.4 반도체/AI 시총·AUM**: 종목 시총=Yahoo `get_stock_info` marketCap(.KS/.KQ), ETF AUM=공개보도(네이버금융 web_fetch 차단 주의). 표기 시 raw 숫자/괄호주석 제거(예 "약 2,213조원").
> - **6.2 코인 1년 / 6.3 김프 (CoinDesk MCP + alternative.me)**: `fetch_spot_ohlcv`(market=coinbase, instrument=BTC-USD 등, ~365 일봉)로 BTC/ETH/XRP/SOL 가격·거래량 → `nmr_crypto_series.json={btc,eth,xrp,sol:[[d,close,vol]],fng:[[d,val]]}`; F&G 1년=`api.alternative.me/fng/?limit=400`(web_fetch). 김프 4종=`fetch_spot_tick`(market=upbit BTC-KRW… + market=binance BTC-USDT…), 환율 Yahoo KRW=X. 빌더 `crypto.charts={btc,eth,xrp,sol,fng}` 로 1년 차트(gen_rest_charts.py coin/fng). `nmr_crypto_series.json` 가 비어도 gen_rest_charts.py 는 가드되어 안전.
>
> **v3.6.15 변경점 (2026-06-15 사용자 피드백 — 3.1.x 수급/일봉·3.2.x 재발방지)**
> 아래는 "자주 발생하는" 한국 수급/차트 누락을 **근본 차단**하기 위한 필수 규칙이다(반복 위반 금지).
> - **3.1.1 일봉 OHLC 필수**: KoreaTechAgent 는 코스피·코스닥 차트용 OHLC 를 **반드시 일봉(`interval="1d"`)**으로 받는다(주봉 금지 — 주봉/월봉처럼 보임). `nmr_kr_ohlcv.json` 의 `kospi`/`kosdaq` 와 `kospi_ohlcv`/`kosdaq_ohlcv`(동일값) 둘 다 일봉으로 채운다.
> - **3.1.1 외국인/기관/개인 누적순매수 차트가 평평/비정상인 근본원인 = `kospi_flows_daily`/`kosdaq_flows_daily` 가 비어서임.** 다음금융 투자자 API 는 web_fetch 가 헤더(`Referer`)를 못 보내 항상 빈 응답이다. **반드시 Claude in Chrome 동일출처 fetch 로 받는다(검증됨).** 절차: `navigate https://finance.daum.net/domestic` → `javascript_tool` 로
>   `fetch('https://finance.daum.net/api/market_index/days?page=1&perPage=250&market=KOSPI&pagination=true',{headers:{Referer:'https://finance.daum.net/',Accept:'application/json'}})` (KOSDAQ 동일). 응답 `data[]` 의 `foreignStraightPurchasePrice/institutionStraightPurchasePrice/individualStraightPurchasePrice`(÷1e8=억원)·`accTradeVolume`·`tradePrice`(종가)를 **오름차순**으로. javascript_tool 반환은 ~1.4KB 에서 잘리니 window 변수 저장 후 **≤900자 슬라이스**로 나눠 받아 파일 append 재조립(base64 반환은 차단되니 일반 텍스트만). 1년치(perPage=250)면 누적순매수 차트가 정상.
> - **3.1.1 투자자별 순매수 표(외국인/기관/개인) 항상 채움**: `korea_investors.kospi/kosdaq` 의 `foreign/institution/individual` 은 `*_flows_daily` **마지막 행(최신일)**에서 보기좋게(예 `"+9,859억"`,`"-1.49조"`) 반드시 채운다(빈 객체 `{}` 금지 — 표가 "-" 로 나옴).
> - **3.1.2 장중에도 수집**: 종목별 순매수/순매도는 다음금융/KRX 의 장중 잠정치라도 채우고 `note` 에 "장중 잠정"을 명시. 끝내 없으면 빈배열+사유.
> - **3.1.3 경기선행지수**: 통계청(국가데이터처) 순환변동치 최근 3~4개월, 최신 맨 앞. 비면 섹션이 통째로 빠지므로 WebSearch 로 반드시 시도.
> - **3.1.4 테마/반도체 추세차트**: 각 테마 대표 ETF·반도체 종목의 1년 주봉 series 를 `nmr_themeseries1y.json`/`nmr_semi_series.json` 에 채워야 미니차트가 생성됨(비면 "-").
> - **3.2/3.3/3.4 1주 변화율 = +0.00% 버그 차단**: 야후 주봉의 **마지막 '진행중(부분) 주봉'이 직전 완성봉과 종가가 같아** 1주 수익률이 0으로 왜곡된다. MarketsAgent 는 마지막 두 봉이 7일 미만 간격이면서 종가가 같으면 **부분봉을 버리고** 직전 완성봉 기준으로 1주를 계산한다(UsEtfAgent 와 동일 처리). 모든 기간(1w~1y)은 날짜 기준 룩백 권장.
> - **3.2.1 미국 HY 신용 스프레드**: FRED `BAMLH0A0HYM2`(OAS)·`BAMLH0A0HYM2EY`(유효수익률) — web_fetch 는 CSV 를 binary 로 반환해 실패하므로 **Claude in Chrome 으로 `fredgraph.csv?id=...&cosd=...&coed=...` 을 navigate→get_page_text** 또는 동일출처 fetch 로 받아 `markets.us_credit{hy_oas,hy_yield,implied_ust,comment}` 와 1년 일별 series(`hy_oas.json`)를 채운다(비면 3.2.1 섹션 누락).
> - **3.2.3 분기 표시**: IndexRebalanceAgent 의 `sp500.schedule` 항목 키는 `q`(분기) 권장이나 `cycle`/`quarter` 로 와도 빌더가 표시한다(빌더 v3.6.15 에서 `s.q??s.cycle??s.quarter` 로 수정). 에이전트는 가급적 `q` 에 "2026 Q2" 형식으로 채울 것.
>
> **v3.6.4 변경점 (2026-06-14 사용자 피드백)**
> - **7 한국 5대 증권사 — 공식 채널 최신 리포트 우선**: 각 사 공식 리서치 목록 페이지(아래 URL)에서 **발행일이 D-1(전일) 이내인 최신 리포트**의 제목·발행일·핵심메시지를 수집한다. 공식 페이지가 JS 렌더라 서브에이전트 web_fetch 로 본문이 안 나오면, **메인 세션이 Claude in Chrome 으로 navigate→get_page_text** 해서 수집한다(주: 키움만 리포트고 나머지는 뉴스에서 추출 + 오래된 자료였던 문제 수정). **최신 공식 리포트를 끝내 못 구한 사(社)만** WebSearch/네이버 뉴스로 보강하고 그 사실을 `key_message` 말미에 `(뉴스 기반)` 으로 표기.
> - **8 글로벌 IB — 최신만**: 발행일 D-1 이내의 최신 하우스 뷰만 수집. 오래된 코멘트는 배제. 못 구할 때만 뉴스 검색.
> - **5 환율 USD/EUR**: EUR/USD 대신 **USD/EUR**(=1/EURUSD, 1달러당 유로)를 `markets.fx_usd.usd_eur` 로 저장. 현재치·1주~1년 변화율 모두 역수 시계열(usd_eur_t = 1/eurusd_t) 기준으로 계산. 시계열 차트도 `s2.fx.usd_eur` 로 저장(스파크 spark_usd_eur.png).
> - **4 원자재 섹션별 추세 코멘트**: 4.1/4.2/4.3 각각에 추세 평가 코멘트 1~2문장을 `commodities.energy_comment`/`metals_comment`/`agri_comment` 로 수집(에너지·금속·농산물 각 군의 단·중·장 추세 해석).
> - **3.2.2 주요 미국 ETF (신설, v3.6.8)**: `markets.us_etfs` (지수추종·11개 섹터·테마/특화·방어형 32종) + `nmr_etfseries.json` 1년 주봉. 아래 UsEtfAgent 참조.
- **3.2.3 미국 지수 정기 리밸런싱 (신설, v3.6.9)**: `markets.index_rebalance` (S&P 500·나스닥 100 편입/편출·일정·기준·룰변경). 아래 IndexRebalanceAgent 참조. 기존 CAPEX 는 **3.2.4** 로 이동.
- **3.2.4 CAPEX 2027·2028 전망**: `markets.bigtech_capex.rows[]` 에 `y2027`·`y2028`(가이던스/컨센서스 전망, 확인된 경우만) 필드 추가.
> - **차트는 분석(9~12) 전에 생성** — 시계열 에이전트(IndexSeries/KoreaTech/CryptoSeries/Theme)는 Phase 1 에서 함께 수집하고, 차트 PNG 생성은 AnalysisAgent 호출 전에 끝낸다.

> **v3.6.10 변경점 (2026-06-14 사용자 피드백 — 보고서 정합·견고화)**
> - **IndexRebalanceAgent — 반드시 빌더 스키마**: `markets.index_rebalance.sp500/nasdaq100` 의 `events` 는 **`[{title, effective, note_top?, add:[{ticker,name,biz,reason}], remove:[{...}], note?}]`** 형식이어야 한다(편입=add·편출=remove). **평면 `[{ticker,name,biz,reason}]` 배열 금지** — 그러면 3.2.3 이 빈 표로 렌더된다(실측 버그). `schedule`=[{q 또는 cycle, announce, effective, note}], `criteria`=[{item,detail}], `rule_change`={effective, rows:[{rule,before,after}], note}, `candidates`=[{name,biz,valuation,status}]. **최근 2~3개 분기/연례 재구성 + M&A·임시 변경까지** 모두 수집(직전 분기 1건만 넣지 말 것). 사용자 연결폴더에 `3.2.3_지수리밸런싱.html` 가 있으면 그 내용을 1차 기준으로 정합.
> - **NewsAgent `bigtech_events` — ★★ 포함 8~12건**: ★★★만 넣지 말 것. 갤럭시 언팩·구글 I/O·메타 커넥트·MS Ignite·AWS re:Invent·테슬라/엔비디아/애플 실적·CES/Computex 등 ★★급도 충분히 포함, 날짜 오름차순.
> - **KoreaTechAgent — 일별 수급·거래량(다음금융 REST 직접)**: `kospi_flows_daily`·`kosdaq_flows_daily`(최근 ~250영업일)는 `https://finance.daum.net/api/market_index/days?page=N&perPage=250&market=KOSPI(또는 KOSDAQ)&pagination=true` 로 수집. **헤더 `User-Agent`(브라우저)·`Referer: https://finance.daum.net/` 필수** — 없으면 빈 응답(실측: web_fetch 가 헤더 미전송으로 빈값이면 메인 세션이 직접 받아 채운다). `data[].foreignStraightPurchasePrice/institutionStraightPurchasePrice/individualStraightPurchasePrice`(원→억원 ÷1e8), `accTradeVolume`. **KOSDAQ 거래량은 이 accTradeVolume 로 ^KQ11 손상분(중앙값 1000)을 교체**. 1일 기준 투자자 표(외국인/기관/개인)도 최신일 값으로 채운다.
> - **KoreaMacroAgent — 코스닥 종목·반도체 시총·차트 시리즈**: `korea_investor_stocks` 는 `kospi_buy/sell` **뿐 아니라 `kosdaq_buy/sell` 도 반드시** 채운다(각 6~10종 {name,detail}; 코스닥 일간 랭킹 비공개면 최근 확인일 기준+`note` 명시). `semi_ai_breakdown` 각 행 **`aum`(시총, 억원/조원) 필수**, 1Y 주봉 series 를 `nmr_semi_series.json[종목명]` 으로 저장하면 `gen_rest_charts.py` 가 `charts/semi_<i>.png`(시총순)를 만든다. `bigtech_capex` 미확인 연도칸은 빈칸이 아니라 **"미공개"**(빌더도 v3.6.10부터 빈칸을 "미공개"로 렌더).
> - **IndexSeriesAgent — CNY/KRW 시계열 도출**: `CNYKRW=X` 가 단일 포인트만 반환하면 `cny_krw` 시계열을 **`usd_krw / usd_cny`(동일자)** 로 계산해 `nmr_series2.json.fx.cny_krw` 에 넣는다(5장 환율 추세차트 누락 방지).
> - **UsEtfAgent — 사용자 참고 HTML 정합**: 연결폴더에 `3.2.2_미국ETF시황.html` 가 있으면 현재가·수익률·추세평가를 그 값으로 정합(HTML 우선).

> **v3.6.11 변경점 (2026-06-14 사용자 피드백 — 반도체표·원자재추세·버크셔)**
> - **CommoditiesAgent — trend 한글 필수**: 에너지·금속·농산물·전략광물 각 행의 `trend` 는 **반드시 한글 간략 평가**(예: `"1년 +26% 강세, 3개월 -16% 조정"`). **"up"/"down" 영문 단어 금지**(실측 위반). 섹션별 `energy_comment`/`metals_comment`/`agri_comment` 와 별개로 각 행 trend 도 채운다. (빌더도 v3.6.11 `koTrend` 로 영문/빈 trend 를 수익률 기반 한글로 자동 생성하지만, 에이전트가 우선 채울 것.)
> - **KoreaMacroAgent — 반도체/AI 표 11행**: `semi_ai_breakdown` 은 **대표 종목 3개(삼성전자·SK하이닉스·삼성전기) + 한국 상장 반도체/AI ETF 중 AUM 상위 8개 = 총 11행, 시총/AUM 내림차순**. 각 행 `aum`(억원/조원) 필수, `note`(1줄 설명). **`semi_ai_comment`(현황 2~3문장: 삼성·SK 시총·HBM·AI 슈퍼사이클·ETF 자금흐름) 필수**. 각 행 1Y 주봉 series 를 `nmr_semi_series.json[종목/ETF명]`(키는 breakdown name 과 정확히 일치)으로 저장 → `charts/semi_<i>.png`(시총순). ETF 2개만 넣지 말 것.
> - **BerkshireAgent — 상위 보유 최대 20**: `top_holdings` 는 포트폴리오 비중 **상위 최대 20종**(각 {name,ticker,weight_or_value,note}). 5종만 넣지 말 것. `new_buys/added/reduced/exited` 와 별개.

> **v3.6.12 변경점 (2026-06-14 사용자 피드백 — 반도체/AI 종목10+ETF20 2그룹)**
> - **KoreaMacroAgent — 반도체/AI 2그룹 대폭 확대**: 기존 `semi_ai_breakdown`(단일 11행) 대신 **두 그룹**을 수집한다. ① `markets.semi_ai_stocks` = 국내 반도체/AI 관련 **종목 시총 상위 10개**(삼성전자·SK하이닉스 포함, 한미반도체·삼성전기·주성엔지니어링·원익IPS·리노공업·이오테크닉스·DB하이텍·HPSP 등에서 시총순), 각 {name, aum(시총), note(현황 1줄), }. ② `markets.semi_ai_etfs` = 국내 상장 반도체/AI **ETF AUM 상위 20개**(KODEX/TIGER/SOL/ACE/RISE/PLUS 등), 각 {name, aum(AUM), note}. **그룹별 현황 코멘트** `markets.semi_ai_stocks_comment`·`markets.semi_ai_etfs_comment`(각 2~3문장) 필수. 각 종목·ETF(총 30) 1Y 주봉 series 를 `nmr_semi_series_v3.json[name]` 으로 → 메인세션이 `charts/semi_s_<i>.png`(종목)·`charts/semi_e_<i>.png`(ETF) 생성해 각 행 `chart` 에 매핑. 빌더는 신스키마(stocks/etfs) 우선 렌더, 없으면 구 `semi_ai_breakdown` 폴백. **ETF 2~8개만 넣지 말 것 — 종목 10·ETF 20 채울 것.**

> **v3.6.13 변경점 (2026-06-14 사용자 피드백 — 단일종목 레버리지 ETF 포함)**
> - **KoreaMacroAgent — `semi_ai_etfs` 에 단일종목 레버리지 ETF 포함**: 반도체/AI ETF AUM 상위 20 선정 시, **삼성전자·SK하이닉스 단일종목 (2배) 레버리지 ETF**(예: `KODEX 삼성전자단일종목레버리지`·`KODEX SK하이닉스단일종목레버리지`·동일 TIGER 시리즈)는 반도체 대형주 추종이며 AUM 이 매우 크므로(2026.6 상장 직후 각 ~2조원대) **반드시 후보에 포함**해 AUM 순위대로 넣는다. 2026년 상장 신규 ETF·레버리지/인버스도 반도체/AI 테마면 배제하지 말 것(누락 실측 — 단일종목 레버리지 2종이 AUM 5·6위인데 빠졌었음). 신규 상장이라 1Y series 가 짧거나 없으면 `note` 에 "20YY.M 상장" 명시하고 추세차트는 비워둔다.

> **v3.6.14 변경점 (2026-06-14 사용자 피드백 — 신규 상장 ETF 차트 누락 방지)**
> - **신규 상장 ETF 도 추세차트 생성(다음금융 charts API)**: 야후(`get_historical_stock_prices`)에 데이터가 없거나 1~2주뿐인 **최근 상장 ETF**(예: 2026.6 상장 단일종목 레버리지)는 시계열이 비어 차트가 누락된다. 이 경우 **다음금융 일별 차트 API** 로 상장 이후 일별 종가를 받아 시계열을 채운다:
>   `https://finance.daum.net/api/charts/A{6자리코드}/days?limit=40&adjusted=true` — 헤더 `User-Agent`(브라우저)·**`Referer: https://finance.daum.net/quotes/A{코드}`**(심볼별 Referer 필수, 일반 Referer 는 403)·`Accept: application/json`. 응답 `data[].tradePrice`·`date` 로 `[[date, close]..]` 구성(오름차순). 코드는 WebSearch 로 확인(예: KODEX 삼성전자단일종목레버리지=0193W0, SK하이닉스=0193T0). 이 시계열을 `nmr_semi_series_v3.json[ETF명]` 에 넣으면 메인세션이 `charts/semi_e_<i>.png` 를 생성한다. 상장 1년 미만이면 미니차트 라벨은 `(1Y)` 대신 **`(상장후)`** 로 표기하고, 차트에 한글 라벨을 쓸 땐 `fonts/nmr_kr.ttf` 를 matplotlib `font_manager.addfont` 로 등록(기본폰트는 한글 미렌더).

