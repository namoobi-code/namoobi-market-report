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
12. **미국 신용·ETF·리밸런싱·CAPEX** — 하이일드(HY) 신용 스프레드(OAS·유효수익률·국채분해) + 주요 미국 ETF(지수·섹터·테마·방어형 29종, 1년 추세) + 지수 정기 리밸런싱(S&P 500·나스닥 100 편입/편출·일정·룰변경) + AI 빅테크 자본지출(CAPEX)
13. **전략광물·배터리 금속** — 리튬·니켈·코발트·우라늄·희토류·흑연(ETF 프록시+현물) + 빅테크 신제품·신기술 핵심 이벤트

추가 품질 기준 (v3.3.0 반환각 보완):
- **출처(grounding)**: Top News 와 증권사/IB 대표 리포트는 원문 링크(source_url)를 포함한다. 출처를 댈 수 없는 항목은 수록하지 않는다.
- **수치 근거**: 포트폴리오 기대수익·MDD 는 단일 false-precision 숫자가 아니라 계산근거 또는 범위+가정으로 표기하고 `basis` 를 명시한다.
- **디스클레이머**: 표지 AI·환각 경고 배너와 14장 출처·면책 고지가 반드시 포함된다.

## 워크플로우 개요

```
[Phase 0: 사전 점검]  실행 모드 판정(예약/일반) / 날짜·시작시각 기록 / 연결 폴더(D:\claudeCowork) / Chrome / 빌드환경·무결성(자동복구)
        ↓
[Phase 1: 병렬 수집 — 서브에이전트를 단일 메시지로 동시 발행]
  ├─ NewsAgent / MarketsAgent / CommoditiesAgent / CryptoAgent
  ├─ SecuritiesAgent (한국 5대 — 메인세션 Chrome) / GlobalSecuritiesAgent (해외 IB 5사)
  ├─ IndexSeries / KoreaTech / CryptoSeries / Theme (시계열) · UsEtf (3.2.2) · IndexRebalance (3.2.3) · AINews · Berkshire
        ↓
[Phase 1.5: 차트 생성 (v3.6.4 — 분석 전)]  gen_tech_charts.py·gen_rest_charts.py·gen_hy_chart.py → charts/*.png
        ↓
[Phase 2: AnalysisAgent 단독 호출]  Phase 1 수집 데이터+차트를 입력으로 9~12장(종합분석·자산별견해·포트폴리오·액션) 도출
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
- **Gmail 이 안 켜져 있으면** Claude in Chrome 으로 `https://mail.google.com/mail/u/0/?ogbl#inbox` 로 navigate (로그인 상시 유지 — 비밀번호 단계 불필요).
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
| soffice 변환이 즉시 강제종료(SIGKILL/exit 137) — `--version` 은 되는데 `--convert-to` 만 죽음 | VM 손상(주로 장애·복구 직후) — 프로필 분리·setsid 로도 회피 불가. ① 새 세션/VM 에서 재시도(연결폴더 docx·JSON 백업으로 이어가기) ② 또는 사용자 PC 의 Word/LibreOffice 로 docx→PDF 내보내기(=soffice 동일 레이아웃). 비상 시에만 pandoc+weasyprint(docx→html→pdf, Noto Sans CJK KR) 폴백 — 기본 워크플로는 soffice 유지 |

## 플러그인 유지보수·배포 (git push)

플러그인 파일(SKILL.md·references·scripts·plugin.json 등)을 수정한 뒤 GitHub(origin main)에 반영할 때 따른다.

1. **토큰 자동 사용 — 추가 질문 없이 push**: `D:\claudeCowork\SECURITY\githubtoken.txt` 가 있고 그 안에 GitHub 토큰(`ghp_…`/`github_pat_…`)이 있으면, 사용자에게 다시 묻지 말고 그 토큰으로 `git push origin main` 한다. 파일이 없거나 비어 있을 때만 사용자에게 토큰을 요청하거나 사용자가 직접 푸시하도록 안내한다.
2. **토큰 취급 (비공개)**: 토큰은 채팅·로그·커밋·remote URL 어디에도 평문 노출 금지. URL 에 토큰을 박지 말고 일회성 credential helper(환경변수)로만 전달한다:

    ```bash
    # ⚠️ 토큰은 Read 도구(호스트 직접)로 전체값을 확인해 쓴다 — 마운트 bash 의 grep 은 긴 fine-grained 토큰을 잘라 읽는다.
    # ⚠️ credential helper 는 별도 프로세스라 GH_TOKEN 을 반드시 export 해야 보인다 (export 안 하면 빈 값 → "Invalid username or token").
    export GH_TOKEN='<githubtoken.txt 의 전체 토큰값>'
    git -c credential.helper='!f(){ echo username=namoobi-code; echo "password=$GH_TOKEN"; };f' push origin main 2>&1 | sed "s/$GH_TOKEN/***REDACTED***/g"
    unset GH_TOKEN
    # (검증된 one-shot 대안) git push "https://namoobi-code:<토큰>@github.com/namoobi-code/namoobi-market-report.git" main   # 토큰이 명령행에 남으니 마스킹 필수
    ```

    (push 출력에 토큰이 섞일 수 있으면 `| sed "s/$GH_TOKEN/***REDACTED***/g"` 로 마스킹한다.)
3. **SECURITY 폴더 커밋 금지**: `D:\claudeCowork\SECURITY` 는 레포(`D:\claudeCowork\namoobi-market-report`) 밖이고 `.gitignore` 에도 `SECURITY/` 가 있다. 토큰·수신자 파일은 절대 커밋하지 않는다.
4. **마운트 잘림 회피 커밋 절차**: 샌드박스 D: 마운트가 큰 파일(SKILL.md·build_report.js 등)을 간헐적으로 잘라 읽고/쓴다. 워킹트리에서 바로 `git add` 하면 잘린 blob 이 커밋될 수 있으니 금지. 대신 ① 편집은 Read/Write/Edit(호스트 직접) 도구로 하고, ② 커밋은 `git show HEAD:<path>` 로 원본을 받아(객체는 git 이 완전히 읽음) 메모리에서 동일 편집을 적용한 뒤 `git hash-object -w --stdin` 으로 blob 을 만들고 `git cat-file` 로 무결성(끝부분 마커·바이트수)을 검증한다. ③ 인덱스는 마운트가 아닌 tmpfs(`GIT_INDEX_FILE=/dev/shm/idx`)에 두고 `read-tree HEAD` → `update-index --cacheinfo` → `write-tree` → `commit-tree -p HEAD` → `update-ref refs/heads/main` 순으로 커밋한 뒤 push 한다.
5. **`.git/index.lock` 이 안 지워질 때**: 마운트 캐시 때문에 `rm` 이 'Operation not permitted' 가 나면 `mcp__cowork__allow_cowork_file_delete` 로 삭제 권한을 받은 뒤 제거한다.
6. **로컬 인덱스 복구 (자동)**: 작업 후 `.git/index` 가 손상돼 `git status` 가 "index file corrupt"/"bad signature" 를 띄우면, 사용자에게 미루지 말고 직접 `git read-tree HEAD`(또는 `git reset`)로 HEAD 기준 깨끗한 인덱스를 재생성한다. 푸시에는 영향 없다.

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
