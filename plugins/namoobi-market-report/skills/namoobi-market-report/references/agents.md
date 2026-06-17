# 서브에이전트 상세 프롬프트 및 반환 스키마 (v3.3.0)

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
> - **3.2.2 주요 미국 ETF (신설, v3.6.8)**: `markets.us_etfs` (지수추종·11개 섹터·테마/특화·방어형 29종) + `nmr_etfseries.json` 1년 주봉. 아래 UsEtfAgent 참조.
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

7개 에이전트 전부 **general-purpose** 타입으로 호출한다.
Phase 1 = News/Markets/Commodities/Crypto/Securities/GlobalSecurities 6개를 **단일 메시지에 동시 발행**.
Phase 2 = AnalysisAgent 를 6개 결과와 함께 **단독 호출**.

## 공통 반환각(Hallucination) 방지 규칙 — 모든 에이전트 프롬프트에 그대로 포함 (v3.3.0)

아래 블록을 **모든** 서브에이전트 프롬프트 맨 앞에 붙인다.

> **[필수 준수 — 사실성 규칙]**
> 1. **추정 금지 (Grounding)**: 모든 수치·날짜·사실은 반드시 도구 호출 결과 또는 검색으로 직접 확인한 값만 사용한다. 도구/검색으로 확인되지 않은 값은 **절대 기억(학습데이터)으로 채우지 말고** `null`(또는 빈 문자열/빈 배열)로 둔다. "아마", "약", "대략", "추정컨대" 같은 추측성 수치 생성을 금지한다.
> 2. **출처 의무 (RAG)**: 뉴스·이벤트·리서치 등 정성 정보는 **출처(source)와 가능하면 URL·발행일**을 함께 반환한다. 출처를 댈 수 없는 항목은 보고서에 넣지 말고 제외한다.
> 3. **사실 vs 의견 구분**: 확인된 사실과 본인의 해석·전망을 섞지 않는다. 해석은 별도 필드(trend/comment/view)에만 적는다.
> 4. **결정적 출력 (낮은 Temperature 지향)**: 창작·과장·미사여구를 배제하고 사실 기반으로 간결하게. 동일 입력에는 동일 결론이 나오도록 보수적으로 답한다. 확신이 없으면 단정하지 말고 불확실성을 명시한다.
> 5. **도구 로딩**: MCP 도구는 deferred 상태일 수 있다. 사용 전 반드시 `ToolSearch` 키워드 검색으로 로드하라 (예: `+UsStockInfo historical`, `+CoinInfo kimchi`). **UUID 포함 도구명을 하드코딩하지 말 것** (서버 ID는 세션마다 다름).
> 6. **중단 금지**: 실패한 항목은 null/빈 배열로 두고 다음으로 진행한다. 실패를 추측으로 메우지 않는다.
> 7. **저장 규칙**: 최종 JSON 은 outputs 하위 `nmr_<에이전트이름>.json` 파일로 bash heredoc(`<<'EOF'`) 저장하고, 응답으로는 **저장한 파일 경로와 1줄 요약만** 반환할 것 (긴 JSON 본문 출력 금지 — v3.2.3 속도 규칙).

---

## 공통 데이터 소스 폴백 (v3.4.0) — MCP 부재 시 적용

지정 MCP 가 세션에 없으면 추정으로 채우지 말고 아래 폴백을 쓴다. 폴백도 안 되는 칸만 null.

- **증시·환율·원자재 (UsStockInfo MCP 부재 시)** → **Claude in Chrome 으로 Yahoo chart API 직접 호출**.
  절차: `navigate https://finance.yahoo.com` 후 `javascript_tool` 로 async IIFE 안에서
  `await fetch("https://query1.finance.yahoo.com/v8/finance/chart/<TICKER>?range=1y&interval=1wk")` (CORS 허용, **top-level await 금지 → `(async()=>{...})()` 로 감쌀 것**).
  주봉 close 배열 + `meta.regularMarketPrice` 로 1주(7d)/1개월(30d)/3개월(91d)/6개월(182d)/1년(365d) 변화율 계산(타깃일에 가장 가까운 주봉, 허용오차 ~11일).
  결과 JSON 이 길면 `window.__x=obj` 저장 후 8개 키씩 나눠 반환(출력 잘림 회피). **JPYKRW=X 는 100엔 환산이라 current 보존·pct 만 갱신**. CNYKRW 희박 시 USD/KRW ÷ USD/CNY(CNY=X). `web_fetch`·stooq 는 본문 빈값이라 사용 금지(Chrome 만).
- **암호화폐 (CryptoAgent)** → CoinInfo MCP 우선. `get_kimchi_premium` 이 "데이터 부족" 이면 **CoinDesk MCP `fetch_spot_tick`**(market=`upbit`, instruments=`BTC-KRW,ETH-KRW,XRP-KRW,SOL-KRW`)로 업비트 KRW + (market=`binance`, `BTC-USDT,...`) 로 USD 받아 김프=(업비트KRW/(USD×환율)−1)×100. 환율=Yahoo USD/KRW.
  공포·탐욕은 **7개 시점**: `api.alternative.me/fng/?limit=400` (Chrome navigate→get_page_text, body 를 JSON.parse) 에서 현재·1일·1주·1개월·3개월(idx 90)·6개월(idx 182)·1년(idx 365) 값+분류 수집 → `last_3month(_cls)`/`last_6month(_cls)`/`last_year(_cls)` 로 저장. CoinGecko 429 면 ~20초 후 재시도, 실패 시 Crypto.com Exchange MCP/직전값 유지. **한국 거래소 API(업비트·빗썸)는 Chrome 이 차단** → CoinDesk MCP 로만.
- **대형 IPO (NewsAgent)** → SpaceX·OpenAI·Anthropic·Databricks 등 대형 IPO 를 이벤트 캘린더에 포함. 상장일 확정은 `events_calendar`(1개월), 미확정/전망은 `events_calendar_longterm` 에 `(미확정/전망)`·출처와 함께, 날짜 칸엔 `expected_timing` 텍스트.
- **추세 텍스트는 한글로** (trend 필드 영문 금지).

---

## 1. NewsAgent

**임무**: 글로벌 금융시장 Top News 10 + 향후 2주 주요 이벤트 캘린더 + 원화 톤 코멘트.

**도구**: NaverSearch MCP(있으면), web_fetch(한국경제 등), WebSearch, Claude in Chrome(가능하면 한국경제 https://www.hankyung.com/finance).
naver.com 도메인은 Chrome 에서 차단될 수 있음 → NaverSearch MCP 또는 web_fetch 로 대체.

**프롬프트 골자**:
- 오늘(KST) 기준 글로벌 금융시장에 영향이 큰 뉴스 10개를 선별 (미국·한국·중국·유럽·중동·원자재·코인 균형 있게)
- 각 뉴스: rank / headline / 2~4문장 summary / impact 라벨 / **source(매체명) / source_url(원문 링크) / published_date(YYYY-MM-DD)**
- **(v3.3.0 출처 의무)** 모든 뉴스는 실제 검색·fetch 로 확인한 **출처와 URL**을 반드시 포함한다. URL 을 확보하지 못한 헤드라인은 **목록에서 제외**한다 (출처 없는 뉴스 생성 금지). headline·summary 는 원문 내용에 충실하게 쓰고, 원문에 없는 수치·인용을 지어내지 않는다.
- impact 값 (v3.4.3 — 빌더가 기호별 색으로 렌더): `▲ 강세` (호재·상승 요인) / `▼ 부정` (악재·하락 요인) / `■ 양면` (방향 불확실·혼재). 반드시 이 세 가지 중 하나로 쓰고 맨 앞에 기호(▲/▼/■)를 둔다. 필요시 `▲ 매우 강세 (단기)` 처럼 보강 가능하나 선두 기호는 유지. (구버전 `★`/`중립` 표기 금지)
- **이벤트 캘린더 (2단 수집)**:
  ① `events_calendar` — 향후 1개월(오늘 포함) 시장 영향이 큰 이벤트 7~12건, 전체 중요도(★~★★★), 날짜순.
  ② `events_calendar_longterm` — 1개월 이후 ~ 1년, **중요도 ★★★만** 6~10건, 날짜순. 일정 미확정은 "7월 말 (예정)" 식 표기.
  대상: 중앙은행 회의(FOMC/ECB/BOJ/한은), 주요 경제지표(CPI/PCE/고용/GDP), 선물옵션 만기,
  대형 IPO·실적시즌, 선거·정치, 잭슨홀, MSCI 리뷰, 중국 정책회의,
  **빅테크 신기술·신제품 발표 (v3.4.3 — 필수 수집, 누락 금지)**: 애플 아이폰/WWDC 이벤트·삼성 갤럭시 언팩·엔비디아 GTC/CES 키노트·OpenAI 신모델 발표·구글 I/O·메타 커넥트·MS Build/Ignite·테슬라 이벤트·MWC 등.
  - **(중요)** 빅테크 이벤트는 다른 일정에 묻혀 빠지기 쉬우므로, 캘린더를 채우기 전에 **반드시 별도 WebSearch 를 1회 이상 수행**한다 (예: "big tech product launch events June 2026", "엔비디아 GTC 2026 일정", "애플 이벤트 2026"). 향후 1개월 내 매우 중요한 빅테크 이벤트가 **확인되면 1건이라도 반드시 events_calendar 에 포함**하고, 1개월~1년 내 ★★★급(아이폰 이벤트·GTC·CES·OpenAI 플래그십 발표 등)은 events_calendar_longterm 에 포함한다. 해당 기간에 시장영향이 큰 빅테크 이벤트가 정말 없다고 출처로 확인한 경우에만 생략한다.
  - 빅테크 이벤트의 expected_impact 에는 **관련 종목·섹터 영향**을 적는다 (예: "NVDA·HBM(SK하이닉스·삼성전자) AI 밸류체인 촉매").
  - 시장 영향이 큰 것만 선별 — 일반 개발자 세션·마이너 업데이트 행사는 제외.
  - 날짜 grounding 동일 적용: 공식 발표·언론 보도 출처 필수, 미확정은 "(예상)"/"9월 (예상)" 표기.
  - **(v3.3.0 날짜 grounding)** 이벤트 날짜는 **반드시 공식·1차 출처에서 확인**한다 (중앙은행 IR/통계청·노동부 발표 일정, 거래소 만기 공지, 선거관리 일정 등). `events_calendar` 도구가 있으면 그 결과를 우선 사용한다. **기억에 의존해 날짜를 지어내지 말 것** — 확인되지 않은 일정은 날짜 칸에 `(미확정)` 으로 두고, 가능하면 `source` 에 근거 링크를 적는다. 과거에 지나간 날짜를 향후 일정으로 넣지 않도록 오늘(KST) 기준으로 검증한다.
- 원화 톤: krw_trend 1줄 + krw_comment (환율 수치 추세는 MarketsAgent 가 수집하므로 코멘트만)

**반환 JSON**:
```json
{
  "top_news": [
    {"rank": 1, "headline": "...", "summary": "...", "impact": "▲ 강세",
     "source": "한국경제", "source_url": "https://www.hankyung.com/article/...", "published_date": "2026-06-09"}
  ],
  "events_calendar": [
    {"date": "2026-06-11", "region": "한국", "event": "선물옵션 동시만기", "importance": "★★★",
     "expected_impact": "헤지 청산 시 변동성 급확대", "source": "한국거래소 일정", "source_url": "https://..."}
  ],
  "events_calendar_longterm": [
    {"date": "2026-11-03", "region": "미국", "event": "중간선거", "importance": "★★★",
     "expected_impact": "정책 불확실성·재정 방향 분기점", "source": "...", "source_url": "https://..."}
  ],
  "fx_snapshot": {
    "krw_trend": "원화 약세 지속", "krw_comment": "..."
  }
}
```
> `source_url`·`published_date` 가 없으면 빈 문자열로 둔다 (빌더가 출처 칸을 "-" 로 렌더). 단, top_news 는 출처 없는 항목을 **애초에 넣지 않는 것**이 원칙.

---

## 2. MarketsAgent

**임무**: 글로벌 증시 + 매크로 지표 + **주요 환율**의 현재치와 단·중·장기 변화율.

**도구**: UsStockInfo MCP `get_historical_stock_prices`, `get_stock_info` (Yahoo Finance 기반).

**티커 맵**:
| 항목 | 티커 | 항목 | 티커 |
|------|------|------|------|
| 코스피 | ^KS11 | 닛케이 | ^N225 |
| 코스닥 | ^KQ11 | 상하이 | 000001.SS |
| S&P500 | ^GSPC | 항셍 | ^HSI |
| 나스닥 | ^IXIC | 센섹스 | ^BSESN |
| 다우 | ^DJI | 베트남 | VNM (ETF 대체) |
| 대만 가권 | ^TWII | 유로스톡스50 | ^STOXX50E |
| VIX | ^VIX | DAX | ^GDAXI |
| DXY | DX-Y.NYB | FTSE100 | ^FTSE |
| 美10년 | ^TNX |  |  |

**환율 티커 맵** (v3.1 신규):
| 통화쌍 | 티커 | 비고 |
|--------|------|------|
| USD/KRW | KRW=X | |
| EUR/KRW | EURKRW=X | |
| JPY/KRW | JPYKRW=X | **×100 (100엔 기준) 환산** |
| CNY/KRW | CNYKRW=X | |
| HKD/KRW | HKDKRW=X | |

**계산**: `get_historical_stock_prices(period="1y", interval="1wk")` **주봉**을 받아 (일봉 금지 — 토큰 5배·시간 2배 낭비, v3.2.3 속도 규칙) 현재가 대비 1주(직전 주봉)/1개월(~4주)/3개월(~13주)/6개월(~26주)/1년(최초 데이터) 변화율(%)을 계산. 각 항목에 `trend` 평가 1줄 (예: "단기 조정, 장기 상승"). 환율은 원화 관점 평가(상승=원화 약세).

**반환 JSON** (`data-schema.md` 의 markets 섹션):
```json
{
  "korea":          {"kospi": {"current": 0, "1w_pct": 0, "1mo_pct": 0, "3mo_pct": 0, "6mo_pct": 0, "1y_pct": 0, "trend": "..."}, "kosdaq": {}},
  "us_markets":     {"sp500": {}, "nasdaq": {}, "dow": {}, "vix": {}, "dxy": {}, "us10y": {}},
  "asia_markets":   {"nikkei": {}, "shanghai": {}, "hsi": {}, "taiwan": {}, "sensex": {}, "vietnam": {}},
  "europe_markets": {"stoxx50": {}, "dax": {}, "ftse": {}},
  "fx_markets":     {"usd_krw": {}, "eur_krw": {}, "jpy_krw": {}, "cny_krw": {}, "hkd_krw": {}}
}
```

---

## 3. CommoditiesAgent

**임무**: 에너지·금속·농산물 원자재 추세.

**도구**: UsStockInfo MCP (선물 티커). `get_historical_stock_prices(period="1y", interval="1wk")` **주봉** 사용 (일봉 금지 — v3.2.3 속도 규칙). 변화율 계산은 MarketsAgent 와 동일(1주=직전 주봉).

**티커 맵**: WTI `CL=F` / Brent `BZ=F` / 천연가스 `NG=F` / 금 `GC=F` / 은 `SI=F` / 구리 `HG=F` / 백금 `PL=F` / **희토류 `REMX`** (VanEck Rare Earth ETF — 희토류는 선물 티커가 없어 ETF 프록시 사용) / 옥수수 `ZC=F` / 대두 `ZS=F` / 밀 `ZW=F`.
선물 티커는 간헐 실패함 → 실패 시 `current: null` 로 두고 진행.

**반환 JSON**:
```json
{
  "energy":      {"wti": {"current": 0, "1w_pct": 0, "1mo_pct": 0, "3mo_pct": 0, "6mo_pct": 0, "1y_pct": 0, "trend": "..."}, "brent": {}, "natgas": {}},
  "metals":      {"gold": {}, "silver": {}, "copper": {}, "platinum": {}, "rare_earth": {}},
  "agriculture": {"corn": {}, "soybean": {}, "wheat": {}},
  "energy_comment": "(v3.6.4) 에너지 군 단·중·장 추세 평가 1~2문장",
  "metals_comment": "(v3.6.4) 금속 군 추세 평가 1~2문장",
  "agri_comment":   "(v3.6.4) 농산물 군 추세 평가 1~2문장",
  "commentary":  "원자재 종합 코멘트 2~3문장"
}
```
> (v3.6.4) `energy_comment`/`metals_comment`/`agri_comment` 는 4.1/4.2/4.3 표 바로 아래에 "추세 평가:" 로 렌더된다. 각 군의 수치 추세(상승/하락·과열/조정)를 해석하는 코멘트 느낌으로 작성.

---

## 4. CryptoAgent

**임무**: 암호화폐 시장 개요 + 공포·탐욕 + 김치프리미엄 + 등락 상위.

**도구**: CoinInfo MCP — `get_market_overview`, `get_fear_greed_index`, `get_kimchi_premium`(BTC/ETH/XRP/SOL), `get_top_gainers`, `get_top_losers`, `get_coin_dominance`.
gainers/losers/dominance 는 간헐 오류(429 등) → null/빈배열로 두고 진행.

**반환 JSON**:
```json
{
  "market_overview": {"total_volume_24h_usd": 0, "avg_change_pct": 0, "coins_up": 0, "coins_down": 0, "btc_dominance": 0},
  "fear_greed": {"current": 0, "classification": "공포", "yesterday": 0, "last_week": 0, "last_month": 0},
  "kimchi_premium": {
    "rate_usd_krw": 0,
    "coins": [{"symbol": "BTC", "upbit_krw": 0, "binance_usd": 0, "premium_pct": 0, "status": "프리미엄|디스카운트"}]
  },
  "top_gainers": [{"symbol": "...", "change_pct": 0}],
  "top_losers":  [{"symbol": "...", "change_pct": 0}]
}
```

---

## 5. SecuritiesAgent

**임무**: 한국 5대 증권사 **공식 리서치 채널의 최신(발행일 D-1 이내) 리포트**를 수집. SKILL.md 부록 A 의 강점표를 프롬프트에 포함해 각 사의 강점 영역 시각을 우선 수집한다.

**(v3.6.4) 공식 리서치 목록 URL — 여기서 최신 리포트를 먼저 찾는다**:
| 증권사 | URL | 비고 |
|--------|-----|------|
| 신한투자증권 | https://www.shinhansec.com/siw/insights/research/list/view-popup.do | 리서치 목록 팝업 |
| 미래에셋증권 | https://securities.miraeasset.com/bbs/board/message/list.do?categoryId=1521 | 리서치 게시판 |
| 삼성증권 | https://www.samsungpop.com/sscommon/jsp/search/research/research_pop.jsp#bm | 팝업 뜨면 '확인' 눌러 진입 |
| 한국투자증권 | https://securities.koreainvestment.com/main/research/research/Strategy.jsp?jkGubun=99 (시황) · …?jkGubun=34 (전략) | 전략·시황 2개 탭 |
| 키움증권 | https://www3.kiwoom.com/h/invest/research/VMarketSDView · …/VMarketMLView · …/VAnalTPView | 시황·모닝·종목 |

**수집 방법 (v3.6.4)**: 위 페이지들은 대부분 **JS 렌더**라 서브에이전트의 web_fetch 로는 본문이 안 나온다. 따라서 **메인 세션이 Claude in Chrome 으로** 각 URL 을 `navigate` → `get_page_text` 해서 **목록에서 발행일이 가장 최신(오늘/전일)인 리포트의 제목·발행일·핵심 요약**을 뽑는다. 발행일이 D-1 보다 오래된 것만 있으면 그중 최신 1~2건을 쓰되 `key_message` 에 발행일을 명시한다.
- **뉴스는 폴백**: 공식 페이지에서 최신 리포트를 끝내 못 구한 사(社)에 한해서만 WebSearch/네이버 뉴스로 보강하고, 그 항목 `key_message` 말미에 `(뉴스 기반)` 을 붙인다. (구버전처럼 모든 사를 뉴스로 채우지 말 것.)
- 키움 텔레그램(https://t.me/s/KiwoomResearch)은 web_fetch 로도 직접 읽을 수 있어 보조로 활용 가능.
- 접속 실패 사이트는 `key_reports: []`, `key_message: ""` 로 둘 것 — 빌더가 "(리포트 수집 실패)" 로 렌더링.
**(v3.3.0 출처 의무)** `key_message` 와 각 `view` 는 **실제로 읽은 공개 리포트·기사 근거에서만** 작성한다. 접근하지 못한 증권사의 시각을 기억으로 지어내지 말 것 — 못 읽었으면 빈 값으로 둔다. `key_reports` 항목은 가능하면 `{"title","url","date"}` 객체로 출처 링크를 함께 담는다(문자열도 하위호환 허용).

**반환 JSON**:
```json
{
  "shinhan":    {"strength": "자산배분 통합", "channels": ["쏠쏠한 리포트"],
                 "key_reports": [{"title": "6월 자산배분 전략", "url": "https://...", "date": "2026-06-09"}],
                 "key_message": "...", "asset_allocation_view": "..."},
  "miraeasset": {"strength": "...", "channels": [], "key_reports": [], "key_message": "", "etf_emerging_view": "..."},
  "samsung":    {"strength": "...", "channels": [], "key_reports": [], "key_message": "", "derivatives_view": "..."},
  "korea_inv":  {"strength": "...", "channels": [], "key_reports": [], "key_message": "", "ib_china_view": "..."},
  "kiwoom":     {"strength": "...", "channels": [], "key_reports": [], "key_message": "", "global_etf_view": "..."},
  "common_themes": ["..."],
  "investor_type_recommendation": {
    "long_term_allocator": "...", "overseas_stock_picker": "...",
    "short_term_trader": "...", "etf_passive": "...", "china_focused": "..."
  }
}
```
> `key_reports` 는 문자열 배열 `["..."]` 또는 객체 배열 `[{"title","url","date"}]` 둘 다 허용한다 (빌더가 양쪽 렌더).

---

## 6. GlobalSecuritiesAgent (v3.2 신규)

**임무**: 해외 주요 IB 5사(UBS·Goldman Sachs·J.P. Morgan·Morgan Stanley·BlackRock)의 최신 하우스 뷰 수집. SKILL.md 부록 B 의 강점표를 프롬프트에 포함해 각 사의 강점 영역 시각을 우선 수집한다.

**도구**: WebSearch 주력 (예: "UBS CIO daily view", "Goldman Sachs S&P 500 target", "Morgan Stanley Mike Wilson outlook", "BlackRock weekly commentary"), mcp__workspace__web_fetch 로 공개 Insights 페이지 보강. Bigdata.com MCP `bigdata_search` 가 있으면 활용.
Chrome 브라우저 도구는 사용하지 말 것 (메인 세션/SecuritiesAgent 와 충돌).

**주의**:
- **(v3.6.4) 최신만**: 각 IB 의 **발행일 D-1(전일) 이내 최신 하우스 뷰/코멘트만** 수집한다. 며칠~몇 주 지난 오래된 코멘트는 배제. 공식 Insights/CIO 페이지(부록 B URL)를 우선 확인하고, 최신을 못 구한 기관에 한해 뉴스(Reuters/CNBC 등)로 보강하며 그 사실을 표기.
- 원문 리포트(목표주가 PDF)는 고객 전용 → 공개 채널·언론 보도로 핵심 메시지만 수집.
- 보조: UsStockInfo MCP `get_recommendations` 로 주요 종목 월가 컨센서스 확인 가능.
- 수집 실패한 기관은 key_reports: [], key_message: "" 로 두고 진행.
- **(v3.3.0 출처 의무)** house_view·key_message 는 **실제 읽은 공개 Insights/언론 보도 근거에서만** 작성한다. 확인 못 한 기관의 뷰를 기억으로 지어내지 말 것. 특히 `wall_street_consensus` 의 S&P500 목표지수 등 **구체 수치는 출처(매체·날짜)를 확인한 경우에만** 적고, 확인 불가 시 비워 둔다. `key_reports` 는 가능하면 `{"title","url","date"}` 객체로 출처 링크를 담는다.

**반환 JSON**:
```json
{
  "ubs":            {"strength": "CIO House View 자산배분·일일 시황", "channels": ["UBS CIO Daily"], "key_reports": [{"title": "CIO Daily 2026-06-09", "url": "https://...", "date": "2026-06-09"}], "key_message": "...", "house_view": "..."},
  "goldman":        {"strength": "매크로·원자재·경제전망", "channels": ["GS Insights"], "key_reports": [], "key_message": "", "macro_commodity_view": "..."},
  "jpmorgan":       {"strength": "글로벌 전략·시장 전망", "channels": ["JPM Global Research"], "key_reports": [], "key_message": "", "global_strategy_view": "..."},
  "morgan_stanley": {"strength": "미국주식 전략", "channels": ["Thoughts on the Market"], "key_reports": [], "key_message": "", "us_equity_view": "..."},
  "blackrock":      {"strength": "ETF·자산배분", "channels": ["BII Weekly Commentary"], "key_reports": [], "key_message": "", "etf_allocation_view": "..."},
  "common_themes": ["..."],
  "wall_street_consensus": "S&P500 목표지수 등 월가 컨센서스 1~2문장 (확보 시)"
}
```

---

## 7. AnalysisAgent (마지막 단독 호출)

**임무**: Phase 1 의 6개 JSON 전체를 입력으로 받아 종합 분석과 포트폴리오를 도출. **분석은 의견(opinion)이며, 반드시 Phase 1 에서 수집된 실제 데이터에 근거**해야 한다 — 입력 JSON 에 없는 수치·사실을 새로 만들어내지 말 것.

**프롬프트에 "outputs 의 nmr_*.json 6개 파일을 bash(cat) 로 읽으라"고 지시**하고 (긴 JSON 첨부 불필요 — v3.2.4) 아래를 요구:
- `summary`: 3~5문장 Executive Summary (보고서 맨 앞에 들어감). 입력 데이터에서 드러난 사실만 요약.
- `macro_view`: 매크로 톤 1문단
- `key_themes`: 3~6개 {theme, direction, comment}. **direction 은 반드시 `▲`(강세·상승) / `▼`(부정·하락) / `■`(양면·혼재) 중 하나**로 표기 (빌더가 기호별 색으로 렌더 — ▲ 초록·▼ 빨강·■ 앰버)
- `key_risks`: 3~5개 리스크 문장
- `asset_view`: 자산군별 단·중·장기 견해 1줄씩. **키명은 정확히 다음을 사용**:
  `us_equity, kr_equity, china_equity, japan_equity, em_equity, europe_equity, kr_treasury, us_treasury, gold, oil, btc`
  (빌더 v1.2.2 부터는 `cn_equity/jp_equity/eu_equity/kr_bond/us_bond` 축약 별칭도 수용하지만 위 정식 키를 우선 사용할 것)
- `portfolios`: aggressive/balanced/conservative — label, expected_return, max_drawdown, rebalance, **basis**, allocation[{asset, weight_pct, vehicle}] (비중 합계 100%)
  - **(v3.3.0 수치 환각 방지 — 가장 중요)** `expected_return`·`max_drawdown` 은 **근거 없는 단일 숫자를 지어내지 말 것**. 두 가지 방식만 허용한다:
    ① **계산 근거**: MarketsAgent/CommoditiesAgent 가 수집한 1년 주봉 변화율·구성자산 비중으로 과거 변동성/낙폭을 **계산**해 도출하고, 그 방법을 `basis` 에 명시 (예: "구성자산 1년 실적 변동성 가중평균 기반 추정").
    ② **시나리오 라벨**: 계산이 어려우면 구체 %대신 **범위 + 가정**으로만 표기하고(예: "연 +8~14% (강세 지속 가정)"), `basis` 에 "정성 시나리오 가정치 — 과거 수익률이며 미래 보장 아님" 을 적는다.
    - 어느 경우든 false precision(예: "연 13.7%") 금지. `basis` 필드는 **필수**.
- `action_items`: 단기·중기·장기 체크리스트 5~8개
- 저장 후 node 로 JSON.parse 검증까지 수행하도록 지시.

**반환 JSON**: `data-schema.md` 의 analysis 섹션과 동일.


## (v3.5.0) 신규 섹션 데이터 수집 — 추가 필드

아래 필드를 담당 에이전트가 수집해 JSON 에 포함한다. 수집 실패 시 해당 키를 생략하면 빌더가 섹션을 자동 생략한다(오류 아님). 모든 수치는 공통 반환각 규칙(추정 금지·출처 의무)을 따른다.

### NewsAgent 추가
- `news.bigtech_events`: [{date, event, importance(★~★★★), expected_impact}] — **매우 중요한 빅테크 신제품·신기술 이벤트만**(삼성 갤럭시 언팩, 애플 9월/폴더블, OpenAI 신모델, NVIDIA GTC·CES 키노트 등). WebSearch 로 공식 일정 확인, 미확정은 날짜에 `(예정)`. `news.bigtech_events_comment` 선택.

### MarketsAgent 추가
- `markets.korea_flows`: [{market(코스피/코스닥/수급 구도), trend(▲/▼ 포함 가능), comment}] — 외국인 순매수 동향(필요시 기관/개인). 출처: 한국거래소·언론. `markets.korea_flows_comment` 선택.
- `markets.korea_leading`: [{period(YYYY.MM), mom(전월비 +x.xp), note}] — 통계청 산업활동동향 경기선행지수 순환변동치 최근 3~4개월(기준선 100 상회=확장). `markets.korea_leading_comment` 선택.
- `markets.korea_themes`: [{theme, direction(▲ 강세/▼ 부정/■ 양면), comment}] — 순환매 관점 주요 테마(반도체·조선·방산·전력[전력기기·송배전·ESS·원전]·증권·로봇[피지컬AI]·우주). 방향은 정성 평가. `markets.korea_themes_intro`/`korea_themes_comment` 선택.
- `markets.us_credit`: {hy_oas, hy_yield, implied_ust, comment} — 美 하이일드. FRED ICE BofA OAS=`BAMLH0A0HYM2`, 유효수익률=`BAMLH0A0HYM2EY` (fred.stlouisfed.org/series/... 를 Chrome get_page_text 로 현재값 확인). 내재국채=유효수익률−OAS. ICE 저작권상 **현재값·요약통계만** 표기.
- `markets.bigtech_capex`: {rows:[{company, y2025, y2026, **y2027, y2028**, comment}], comment} — MSFT·Alphabet·Amazon·Meta 연간 CAPEX(전년 실적 + 당해 가이던스). **(v3.6.4)** `y2027`·`y2028` 은 가이던스·증권가 컨센서스 전망치를 **확인된 경우에만** 채우고(출처 필수), 미확인은 빈 문자열. 출처: 실적발표/언론/IB 전망.

### CommoditiesAgent 추가
- `commodities.strategic_metals`: {etf:[{name, current, "1w_pct".."1y_pct", trend}], etf_comment, spot:[{item, price, comment}], comment} — ETF 프록시 LIT(리튬)·REMX(희토류)·URA·URNM(우라늄) 주봉 변화율(MarketsAgent 방식) + 현물(탄산리튬·니켈 LME·코발트 LME·우라늄 U3O8·흑연)은 WebSearch.
- `commodities.metals.rare_earth` 는 4.2 표에서 제거됨 — 희토류는 strategic_metals 로 일원화(수집은 계속, 4.2 미표시).

## (v3.6.5) 추가/변경 — 수집 요구 (2026-06-14 사용자 피드백 반영)

아래는 v3.6.5 빌더가 기대하는 필드/시계열이다. 누락 시 해당 섹션·차트는 자동 생략된다.

### IndexSeriesAgent (지수 1년 시계열 — 3.2/3.3/3.4 추세 스파크라인)
- `nmr_indexseries.json`: 17개 지수 1년 **주봉 종가** `{kospi,kosdaq,sp500,nasdaq,dow,vix,dxy,us10y,nikkei,shanghai,hsi,taiwan,sensex,vietnam,stoxx50,dax,ftse}` 각 `[["YYYY-MM-DD",close]..]`. `gen_rest_charts.py` 가 이 파일로 `charts/spark_<key>.png` 를 생성해 3.2/3.3/3.4 표 추세열을 채운다. (없으면 추세열 비어 보임 → 반드시 수집)

### UsEtfAgent (3.2.2 주요 미국 ETF — 지수·섹터·테마·방어형, v3.6.8)
**임무**: 미국 주요 ETF 29종의 현재가·1주~1년 수익률·1년 주봉 시계열 수집.
**도구**: UsStockInfo MCP `get_historical_stock_prices(period="1y", interval="1wk")` (주봉). **FMP MCP 는 플랜 제한으로 quote-change/chart 가 막힐 수 있으니 Yahoo(UsStockInfo) 를 기본으로 한다.** 먼저 `ToolSearch`(예: `+UsStockInfo historical`)로 도구 로드.
**대상 (그룹 · 티커 · 설명 · 섹터비중)**:
- **index**: SPY(SPDR S&P 500 ETF Trust·S&P500 최대 유동성), VOO(Vanguard S&P 500·저비용), SPYM(SPDR Portfolio S&P 500·초저보수), QQQ(Invesco QQQ·나스닥100 대형기술), QQQM(QQQ 저보수판), DIA(다우존스30 우량주)
- **sector** (11개, S&P500 비중 weight): XLK 기술 27.69%(반도체·SW·AI), XLV 의료 13.48%, XLC 통신 11.22%, XLY 임의소비재 11.81%, XLF 금융 11.32%, XLI 산업 8.41%, XLP 필수소비재 5.87%, XLB 재료 2.60%, XLRE 부동산 2.61%, XLE 에너지 2.44%, XLU 유틸리티 2.55%
- **theme**: SOXX 반도체(인텔·엔비디아·AMD), SMH 반도체 집적(TSMC·엔비디아·삼성), BOTZ AI/로봇, ARKK 혁신기술(액티브), SCHD 배당성장주, JEPI 커버드콜 현금흐름(월배당), QTUM 양자컴퓨터, NASA 우주항공(Tema Space Innovators·2026 상장 신생), ICLN 글로벌 클린에너지
- **defensive**: GLD 금(현물·헷지), TLT 미국 장기채(20Y+), IEF 미국 중기채(7-10Y)
**계산**: MarketsAgent 와 동일 — 현재가=최신 주봉 종가, 1주=직전 주봉, 1개월≈4주 전, 3개월≈13주 전, 6개월≈26주 전, 1년=최초 데이터 대비 변화율(%). 각 ETF `trend` 1줄(한글, 1년/3개월/1개월 모멘텀+가격위치 종합). 신생 ETF(NASA 등)는 이력이 짧아 3·6개월이 비면 null, 미존재 티커는 수록 금지.
**저장**:
- `markets.us_etfs` = {index:[], sector:[](각 항목 `weight`), theme:[], defensive:[], comment, asof}. 각 항목 `{symbol, name, desc, current, "1w_pct","1mo_pct","3mo_pct","6mo_pct","1y_pct", trend, weight?}`. 별도 `nmr_usetf.json` 으로 저장 후 Phase 3 병합 시 `markets.us_etfs` 에 넣는다.
- `nmr_etfseries.json` = {SYMBOL:[["YYYY-MM-DD",close]..]} (29종 1년 주봉 종가). `gen_rest_charts.py` 가 `charts/spark_etf_<SYMBOL>.png` 생성 → 빌더 추세(1년) 셀.
**주의**: 분배금 큰 ETF(SCHD·JEPI·TLT·IEF)는 가격수익률 기준이라 총수익률보다 낮게 나옴 — `comment` 에 명시.

### IndexRebalanceAgent (3.2.3 미국 지수 정기 리밸런싱 — S&P 500·나스닥 100, v3.6.9)
**임무**: S&P 500·나스닥 100 정기 리밸런싱의 편입/편출 종목·사업내용·사유, 적용 일정, 편입 기준, 나스닥 패스트엔트리 룰 변경을 수집.
**도구**: WebSearch + web_fetch (먼저 `ToolSearch` 로 `select:WebSearch` 로드). **반드시 1차 출처 우선** — S&P 는 `press.spglobal.com` 보도자료, 나스닥은 `ir.nasdaq.com`·`indexes.nasdaq.com` 방법론 FAQ. 보조로 Reuters·CNBC·Bloomberg. **구성종목을 기억으로 생성 금지** — 확인 안 되면 빈 배열/`미확인`.
**수집 범위**:
- S&P 500: 분기 리밸런싱 일정(발표=둘째 금요일경, 발효=셋째 금요일 마감 후 다음 영업일 개장 전), 최근 2개 분기(직전·당분기) 편입/편출 + 그 사이 비정기(M&A) 변경, 편입 기준(시총 ~$20.5B·흑자·유동성·float·12개월 경과·섹터 대표성), 최신 기준 변경(예: MegaCap 컨설팅 결과).
- 나스닥 100: 연례 재구성(12월)·분기 리뷰·임시 변경의 편입/편출, 2026-05-01 패스트엔트리 룰 변경(상위 ~40위·15거래일 조기편입 / 10% float 폐지→3x cap / 10bp 중간편출 폐지→125위 밖 순위기반 정례편출), 패스트엔트리 후보 대형 IPO(SpaceX·OpenAI·Anthropic 등 시총·상장상태).
**검색 예**: `"S&P 500 index changes <month> 2026 spglobal"`, `"Nasdaq-100 annual reconstitution December 2025"`, `"Nasdaq 100 quarterly changes June 2026"`, `"Nasdaq 100 fast entry rule 2026"`, `"SpaceX OpenAI Anthropic IPO 2026 valuation"`.
**저장**: `markets.index_rebalance` = {sp500:{schedule[], events[], criteria[], criteria_note}, nasdaq100:{schedule[], events[], rule_change{rows[]}, candidates[]}, comment, asof}. 각 편입/편출 항목 `{ticker, name, biz(사업 한 줄), reason(편입/편출 사유)}`. 스키마 상세는 `data-schema.md` (v3.6.9) 참조. 별도 `nmr_rebalance.json` 저장 후 Phase 3 병합. 날짜·종목은 1차 출처로 grounding, 미확정은 `미확인` 표기.

### KoreaTechAgent / 수급 (3.1.1·3.1.2 — 1년 일별)
- `nmr_kr_ohlcv.json` 의 `kospi_flows_daily`·`kosdaq_flows_daily` 는 **1년치 일별** 투자자 순매수 `[["YYYY-MM-DD", 외국인억원, 기관억원, 개인억원]..]` (1일치만 넣으면 누적순매수 차트가 평평해짐 — 반드시 1년).
  - 네이버금융 레거시 페이지는 SPA 개편으로 404. **다음금융 `finance.daum.net/api/market_index/days`**(market=KOSPI/KOSDAQ, `foreign/institution/individualStraightPurchasePrice` 원→억원 환산)로 1년 일별 수집.
  - **KOSDAQ 거래량**: 야후 `^KQ11` 지수 거래량이 손상(중앙값 1000)되므로 다음금융 `accTradeVolume` 로 교체. KOSPI 거래량은 야후 정상.
- `markets.korea_investor_stocks` = `{asof, kospi_buy[], kospi_sell[], kosdaq_buy[], kosdaq_sell[], note}` — 각 리스트 `{name, detail}` 약 10종(코스피 순매수/순매도·코스닥 순매수/순매도). 빌더가 **4개 리스트**로 렌더. 순매도 일간 종목 랭킹이 비공개/차단이면 빈배열로 두고 `note` 에 사유 명시. (구 `kospi_foreign_buy/kosdaq_strong/aggregate` 폐기)

### 3.1.3 경기선행지수 (markets.korea_leading)
- 각 항목 `{period(YYYY.MM), value(순환변동치 숫자), mom(+x.xp), note}` — **통계청(국가데이터처) 산업활동동향 확정치**를 직접 확인. 배열은 **최신이 맨 앞(내림차순)**. 빌더가 "선행지수↔KOSPI 정비례·약 2개월 선행", "100 이상=확장 / 100 이하=침체" 설명을 자동 표기.

### 3.1.4 테마 (AI·원자력 포함, 순서 고정)
- `markets.korea_themes` 순서: **반도체 · AI · 전력기기 · 조선 · 방산 · 원자력 · 증권 · 로봇 · 우주**. 각 `{theme, direction(▲/▼/■), comment}`.
- 각 테마 대표 ETF 1년 주봉 series 를 `nmr_themeseries1y.json[테마명]` 에 넣으면 `gen_rest_charts.py`(데이터 주도)가 `charts/theme_<테마명>.png` 자동 생성. `markets.korea_theme_etfs[테마]=ETF명`, `markets.korea_theme_charts[테마]="charts/theme_<테마>.png"` 설정. (AI 예: KODEX AI반도체핵심장비 471990.KS / 원자력 예: ACE 원자력테마딥서치 433500.KS)

### 2.3 빅테크 이벤트 (2.1/2.2 와 중복 금지)
- `events_calendar`(2.1)·`events_calendar_longterm`(2.2) 에 들어온 **빅테크 신제품·신기술·빅테크 실적** 이벤트(애플·삼성 언팩·엔비디아 실적/GTC·구글 I/O·메타 커넥트·MS·AWS·테슬라·OpenAI·CES·MWC 등)는 **2.3(`bigtech_events`)에만** 싣고 2.1/2.2 에서는 제외한다(매크로·정책·지표·IPO 만 2.1/2.2). 2.3 는 **날짜 오름차순**, 구체 일자가 캘린더에 있으면 그 일자를 사용(예: 애플 2026-09-08).

### 원자재 섹션별 추세평가 코멘트 / 환율 / 부록A
- `commodities.energy_comment` · `commodities.metals_comment` · `commodities.agri_comment` (4.1/4.2/4.3 각 표 아래 "추세 평가:" 로 렌더). **키명은 `agri_comment`** (agriculture_comment 아님).
- `markets.fx_usd.usd_eur` = **USD/EUR (=1/EURUSD)** 로 저장(EUR/USD 아님).
- 부록A 버크셔 13F (`berkshire`) — 빌더 스키마 **정확히**: `{quarter, filing_date, summary, cash, new_buys[], added[], reduced[], exited[] (각 {name,ticker,detail}), top_holdings[] ({name,ticker,weight_or_value,note}), sources[]}`. `recent_buys/recent_sells` 나 `top_holdings.detail` 로 주면 부록A 가 비므로 금지 — `new_buys/exited`·`weight_or_value/note` 사용.

## (v3.6.7) 3.1.4 반도체/AI 상세표·테마 확장

- `markets.semi_ai_breakdown`: [{name, aum(시총 억원, 문자열 가능), note(간단 설명), chart("charts/semi_<i>.png" 또는 "")}] — 빌더가 [종목·ETF|시총|간단설명|추세(1Y)] 표로 렌더. chart 가 "" 면 추세 셀은 "-". 미존재 ETF 는 넣지 말 것. `markets.semi_ai_comment` 는 표 아래 현황·코멘트.
  - 차트: 각 종목/ETF 1년 주봉 series 로 미니차트(`charts/semi_<i>.png`) 생성(인덱스 = breakdown 행 순서, 시총순). series 가 없거나 매칭 ETF 가 모호하면 chart="".
- `markets.korea_themes` 의 반도체·AI 는 "반도체/AI" 한 행으로 통합하고 `korea_theme_etfs["반도체/AI"]` 는 대표 ETF 하나만. 테마는 자유 확장(신재생에너지·K화장품·K-푸드 등) — 각 테마 1년 series 를 `nmr_themeseries1y.json[테마명]` 에 넣고 `korea_theme_charts[테마]="charts/theme_<테마>.png"`.
- 3.1.2 `kospi_buy/sell`·`kosdaq_buy/sell` detail 은 풍부한 형식(금액·순위·주가±%·외국인지분율). 마감 공개 출처에 확정된 종목만 수록(추정·비교불가 데이터 패딩 금지), 한계는 `note`.
