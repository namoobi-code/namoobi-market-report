#!/usr/bin/env python3
import glob
# fetch_us.py (v3.7) — 美/글로벌 시세 sandbox 수집 (Chrome 불필요, stdlib only, 스레드 병렬).
# MarketsAgent·CommoditiesAgent·UsEtfAgent + Crypto 시계열을 대체. 표의 trend 셀은 기계 계산
# (한국 koTrend 스타일과 일관). 그룹 서술 코멘트(에너지/금속/농산물/ETF)는 기계 요약 1줄.
# 산출: nmr_markets.json, nmr_indexseries.json, nmr_series2.json, nmr_commod.json,
#       nmr_usetf.json, nmr_etfseries.json, nmr_crypto_series.json
# 사용: python3 fetch_us.py [WORK_DIR]
import json, urllib.request, urllib.parse, datetime as dt, time, sys, os
from concurrent.futures import ThreadPoolExecutor
if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]): os.chdir(sys.argv[1])
H = {'User-Agent': 'Mozilla/5.0'}

def get(url, timeout=12, tries=2):
    last = None
    for i in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=timeout).read().decode('utf-8', 'replace')
        except Exception as e: last = e; time.sleep(0.6)
    raise last

# (fix v3.48) 한국상장 .KS ETF 는 Yahoo 가 이력을 최신 1점만 주는 경우가 많다 → finance.daum.net 일봉 폴백.
def _daum_daily_us(code):
    u = 'https://finance.daum.net/api/charts/A%s/days?limit=500&adjusted=true' % code
    req = urllib.request.Request(u, headers={'Referer': 'https://finance.daum.net/quotes/A%s' % code,
                                             'User-Agent': H['User-Agent'], 'X-Requested-With': 'XMLHttpRequest'})
    d = json.loads(urllib.request.urlopen(req, timeout=15).read().decode('utf-8', 'replace')).get('data', [])
    rows = []
    for p in d:
        tp = p.get('tradePrice')
        if not tp: continue
        try: ep = int(dt.datetime.strptime(str(p.get('date'))[:10], '%Y-%m-%d').replace(tzinfo=dt.timezone.utc).timestamp())
        except Exception: continue
        vol = p.get('accTradeVolume') or p.get('candleAccTradeVolume') or 0
        rows.append((ep, float(tp), int(vol or 0)))
    rows.sort()
    return rows

def _daum_res(code, weekly):
    try: rows = _daum_daily_us(code)
    except Exception: return None
    if len(rows) < 2: return None
    if weekly:
        wk = rows[::5]
        if wk and wk[-1] is not rows[-1]: wk.append(rows[-1])
        rows = wk
    return {'timestamp': [r[0] for r in rows],
            'indicators': {'quote': [{'close': [r[1] for r in rows], 'volume': [r[2] for r in rows]}]}}

def _kscode(tk):
    if isinstance(tk, str) and tk.endswith('.KS'):
        c = tk[:-3]
        if len(c) == 6: return c
    return None

def yfetch(ticker, rng='1y', interval='1wk'):
    tk = urllib.parse.quote(ticker)
    for host in ('query1', 'query2'):
        try:
            j = json.loads(get(f'https://{host}.finance.yahoo.com/v8/finance/chart/{tk}?range={rng}&interval={interval}'))
            r = j.get('chart', {}).get('result')
            if r: return r[0]
        except Exception: time.sleep(0.4)
    return None

def closes(res):
    if not res: return []
    ts = res.get('timestamp') or []; q = (res.get('indicators', {}).get('quote') or [{}])[0]; cl = q.get('close') or []
    return [[dt.datetime.utcfromtimestamp(t).strftime('%Y-%m-%d'), round(float(c), 4)] for t, c in zip(ts, cl) if c is not None]

def closevol(res):
    if not res: return []
    ts = res.get('timestamp') or []; q = (res.get('indicators', {}).get('quote') or [{}])[0]; cl = q.get('close') or []; vo = q.get('volume') or []
    out = []
    for t, c, v in zip(ts, cl, vo):
        if c is None: continue
        out.append([dt.datetime.utcfromtimestamp(t).strftime('%Y-%m-%d'), round(float(c), 2), int(v or 0)])
    return out

def ret(series, scale=1.0):
    pts = [(dt.date.fromisoformat(d), float(v) * scale) for d, v in series if v is not None]
    if len(pts) < 2: return {}
    pts.sort(); cur = pts[-1][1]; last = pts[-1][0]
    dec = 4 if abs(cur) < 10 else (3 if abs(cur) < 100 else 2)
    out = {'current': round(cur, dec)}
    for k, days in [('1w_pct', 7), ('1mo_pct', 30), ('3mo_pct', 91), ('6mo_pct', 182), ('1y_pct', 365)]:
        tgt = last - dt.timedelta(days=days); cand = [p for p in pts if p[0] <= tgt] or [pts[0]]; base = cand[-1][1]
        out[k] = round((cur / base - 1) * 100, 2) if base else None
    return out

def trend(r):
    if not r or r.get('1y_pct') is None: return ''
    y = r['1y_pct']; m3 = r.get('3mo_pct') or 0; m1 = r.get('1mo_pct') or 0
    if m3 > 5 and m1 >= 0: ph = '완만한 상승세'
    elif m3 < -5: ph = '조정 흐름'
    elif y > 0: ph = '완만한 상승세' if m3 > 0 else '횡보 흐름'
    else: ph = '약세 흐름'
    return f"{ph}(1년 {y:+.2f}%·3개월 {m3:+.2f}%·1개월 {m1:+.2f}%)"

# ===== 티커 정의 =====
IDX = {'kospi':'^KS11','kosdaq':'^KQ11','sp500':'^GSPC','nasdaq':'^IXIC','dow':'^DJI','vix':'^VIX',
       'dxy':'DX-Y.NYB','us10y':'^TNX','nikkei':'^N225','shanghai':'000001.SS','hsi':'^HSI',
       'taiwan':'^TWII','sensex':'^BSESN','vietnam':'VNM','stoxx50':'^STOXX50E','dax':'^GDAXI','ftse':'^FTSE'}
FX = {'usd_krw':'KRW=X','eur_krw':'EURKRW=X','jpy_krw':'JPYKRW=X','cny_krw':'CNYKRW=X','hkd_krw':'HKDKRW=X',
      'usd_eur':'EUR=X','usd_jpy':'JPY=X','usd_cny':'CNY=X'}
COMM = {'wti':'CL=F','brent':'BZ=F','natgas':'NG=F','gold':'GC=F','silver':'SI=F','copper':'HG=F',
        'platinum':'PL=F','rare_earth':'REMX','corn':'ZC=F','soybean':'ZS=F','wheat':'ZW=F',
        # (v3.46) 4.3 농산물 확장: 기후충격(설탕·커피·오렌지주스) + 비용/종합(CRB·BDI 프록시) + 농업ETF(DBA) + 비료/농기계 대장주(DE·NTR)
        'sugar':'SB=F','coffee':'KC=F','orange':'OJ=F',
        'crb':'^TRCCRB','bdi':'BDRY','dba':'DBA','de':'DE','ntr':'NTR'}
STRAT = {'lit':'LIT','remx':'REMX','ura':'URA','urnm':'URNM'}
# (v3.46) 4.4 비철금속 — 배터리/우라늄/전략광물 3개 테마 밸류체인. key=스파크키 → 야후 티커.
#  우라늄 선물 무료피드 부재→SRUUF(Sprott 실물 우라늄)로 근사, 탄산리튬 현물은 EastMoney GFEX 碳酸锂 主连 선물(fetch_lithium)로 추세 수집.
NF = {'lit':'LIT','tsla':'TSLA','kodex_batt':'305720.KS','sruuf':'SRUUF','ura':'URA','nlr':'NLR',
      'hanaro_nuke':'434730.KS','copper':'HG=F','copx':'COPX','remx':'REMX','kodex_copper':'138910.KS'}
# (사용자요청 v3.47) 4.1 에너지 — 국내 상장 에너지 관련 ETF: 전통 화석연료(KODEX 미국S&P500에너지 합성) · 넥스트에너지 전력망/인프라(KODEX 미국AI전력핵심인프라). key=스파크키 → 야후 티커(.KS)
ENERGY_ETF = {'kodex_energy':'218420.KS','kodex_aipower':'487230.KS'}
# US ETF: symbol -> (group, name, desc, weight)
ETF = {
 'SPY':('index','SPDR S&P 500 ETF','S&P500 추종 대표 ETF',None),'VOO':('index','Vanguard S&P 500','저비용 S&P500',None),
 'SPYM':('index','SPDR Portfolio S&P 500','초저보수 S&P500',None),'QQQ':('index','Invesco QQQ','나스닥100 대형기술',None),
 'QQQM':('index','Invesco QQQ M','QQQ 저보수판',None),'DIA':('index','SPDR Dow Jones','다우30 우량주',None),
 'XLK':('sector','Technology','기술·반도체·SW·AI',27.69),'XLV':('sector','Health Care','의료',13.48),
 'XLC':('sector','Communication','통신',11.22),'XLY':('sector','Consumer Discretionary','임의소비재',11.81),
 'XLF':('sector','Financials','금융',11.32),'XLI':('sector','Industrials','산업',8.41),
 'XLP':('sector','Consumer Staples','필수소비재',5.87),'XLB':('sector','Materials','재료',2.60),
 'XLRE':('sector','Real Estate','부동산',2.61),'XLE':('sector','Energy','에너지',2.44),'XLU':('sector','Utilities','유틸리티',2.55),
 'SOXX':('theme','iShares Semiconductor','반도체(엔비디아·AMD)',None),'SMH':('theme','VanEck Semiconductor','반도체 집적(TSMC·엔비디아)',None),
 'DRAM':('theme','Roundhill Memory','메모리/HBM/NAND(삼성·하이닉스·마이크론)',None),'BOTZ':('theme','Global X Robotics & AI','AI/로봇',None),
 'ARKK':('theme','ARK Innovation','혁신기술(액티브)',None),'SCHD':('theme','Schwab US Dividend','배당성장주',None),
 'JEPI':('theme','JPM Equity Premium','커버드콜 월배당',None),'QTUM':('theme','Defiance Quantum','양자컴퓨터',None),
 'NASA':('theme','Tema Space Innovators','우주항공',None),'ICLN':('theme','iShares Global Clean Energy','클린에너지',None),
 'ROBO':('theme','ROBO Global Robotics','로보틱스·자동화',None),'AIQ':('theme','Global X AI & Tech','AI·기술 전반',None),
 'MAGS':('theme','Roundhill Magnificent 7','매그니피센트7 동일가중',None),
 'GLD':('defensive','SPDR Gold','금 현물·헷지',None),'TLT':('defensive','iShares 20Y+ Treasury','미국 장기채',None),
 'IEF':('defensive','iShares 7-10Y Treasury','미국 중기채',None)}
# (v3.7.x) 3.5.1 유럽 주요 ETF: dispSym -> (yahoo_ticker, name, desc, region). 국내상장(.KS)+미국상장 병행 —
#   유럽 자금흐름을 국내물(원화·환헤지)과 미국물(달러) 양쪽으로 교차 확인. 한국물(코스피/K방산 등) 제외.
EUETF = {
 '195930':('195930.KS','TIGER 유로스탁스50(합성 H)','유로존 대형 50 (EURO STOXX 50, 환헤지)','국내'),
 '245350':('245350.KS','TIGER 유로스탁스배당30','유로존 고배당 30 (Select Dividend)','국내'),
 '411860':('411860.KS','KIWOOM 독일DAX','독일 DAX 40 (제조·수출·화학)','국내'),
 '456250':('456250.KS','KODEX 유럽명품TOP10 STOXX','유럽 명품 10 (에르메스·LVMH 등)','국내'),
 '400570':('400570.KS','KODEX 유럽탄소배출권선물ICE(H)','EU 탄소배출권 선물 (정책·대체자산)','국내'),
 '496770':('496770.KS','PLUS 글로벌방산','미국+유럽 방산 10 (재무장 수혜)','국내'),
 '0102X0':('0102X0.KS','ACE 유럽방산TOP10','유럽 방산 10 (라인메탈 등, 신규상장)','국내'),
 'VGK':('VGK','Vanguard FTSE Europe','광역 유럽(영국·스위스 포함) 대표','미국'),
 'EUFN':('EUFN','iShares MSCI Europe Financials','유럽 은행·금융 (자금흐름 핵심신호)','미국'),
 'EWG':('EWG','iShares MSCI Germany','독일 단일국','미국'),
 'EWQ':('EWQ','iShares MSCI France','프랑스 단일국','미국'),
 'EWU':('EWU','iShares MSCI United Kingdom','영국 단일국','미국'),
}
CRYPTO = {'btc':'BTC-USD','eth':'ETH-USD','xrp':'XRP-USD','sol':'SOL-USD'}

# ===== 병렬 fetch =====
wk_tickers = {}  # name->ticker for weekly
for d in (IDX, FX, COMM, STRAT, NF, ENERGY_ETF): wk_tickers.update({v: v for v in d.values()})
for s in ETF: wk_tickers[s] = s
for _euv in EUETF.values(): wk_tickers[_euv[0]] = _euv[0]  # 유럽 ETF 티커(.KS/미국) 주봉·일봉 수집 등록
def fetch_wk(tk): return tk, yfetch(tk, '1y', '1wk')
def fetch_dy(tk): return tk, yfetch(tk, '1y', '1d')
RES = {}
with ThreadPoolExecutor(max_workers=12) as ex:
    for tk, r in ex.map(fetch_wk, list(wk_tickers)): RES[tk] = r
    for nm, tk in CRYPTO.items():
        pass
CRES = {}
with ThreadPoolExecutor(max_workers=4) as ex:
    for tk, r in ex.map(fetch_dy, list(CRYPTO.values())): CRES[tk] = r

def R(tk, scale=1.0): return ret(closes(RES.get(tk)), scale)
def S(tk): return closes(RES.get(tk))

# ===== (v3.21) 전일 대비(1일) 변동 — 일봉 마지막 2개 종가로 산출 (주봉으로는 1일 변동 계산 불가) =====
def fetch_dy1(tk): return tk, yfetch(tk, '1mo', '1d')
DRES = {}
with ThreadPoolExecutor(max_workers=12) as ex:
    for tk, r in ex.map(fetch_dy1, list(wk_tickers)): DRES[tk] = r

# (fix v3.48) 부실한 한국상장 .KS ETF 시계열을 Daum 일봉으로 보강(3.4.1/3.5.1/4.1/4.4 추세 복원)
_daum_fixed = 0
for _tk in list(wk_tickers):
    _c = _kscode(_tk)
    if not _c: continue
    if len(closes(RES.get(_tk))) < 5:
        _wr = _daum_res(_c, True)
        if _wr: RES[_tk] = _wr; _daum_fixed += 1
    if len(closes(DRES.get(_tk))) < 3:
        _dr = _daum_res(_c, False)
        if _dr: DRES[_tk] = _dr
if _daum_fixed: print('  [daum-fallback] .KS ETF weekly series patched:', _daum_fixed)
def day_stats(tk, scale=1.0):
    s = closes(DRES.get(tk))
    if len(s) < 2: return (None, None, None, None)
    cur = s[-1][1] * scale; prev = s[-2][1] * scale
    if not prev: return (None, None, None, None)
    dec = 4 if abs(cur) < 10 else (3 if abs(cur) < 100 else 2)
    # (req5) prev_pct = 직전장(2일전) 등락률 = s[-2] 대비 s[-3] (1일 칸 = 현재가 등락의 한 세션 전)
    prev_pct = round((s[-2][1] / s[-3][1] - 1) * 100, 2) if (len(s) >= 3 and s[-3][1]) else None
    return (round(cur - prev, dec), round((cur / prev - 1) * 100, 2), round(prev, dec), prev_pct)
def add_day(r, tk, scale=1.0):
    if isinstance(r, dict):
        c, p, pc, ppct = day_stats(tk, scale)
        if ppct is not None: r['prev_pct'] = ppct  # (req5) 1일 칸 = 직전장 등락률
        if pc is not None:
            # (req10 fix) 현재가는 ret()의 최신 종가(r['current']) 기준으로 두고, 1일 변동/전일종가를
            #   '현재가 vs 전일종가(일봉 직전)'로 일관 재계산한다 → 표의 현재가·▲절대변동·(±%)·전일종가(1일전)가
            #   서로 정합(주봉 현재가 ↔ 일봉 변동 불일치 제거). 일봉이 stale 해도 현재가는 그대로 유지.
            cur = r.get('current')
            if cur is not None and pc:
                dec = 4 if abs(cur) < 10 else (3 if abs(cur) < 100 else 2)
                r['prev_close'] = pc
                r['chg'] = round(cur - pc, dec)
                r['1d_pct'] = round((cur / pc - 1) * 100, 2)
            else:
                r['chg'] = c; r['1d_pct'] = p; r['prev_close'] = pc  # 폴백(현재가 없음)
    return r

# ===== nmr_markets.json =====
def block(mp, scales=None):
    scales = scales or {}
    o = {}
    for nm, tk in mp.items():
        r = R(tk, scales.get(nm, 1.0)); r['trend'] = trend(r); add_day(r, tk, scales.get(nm, 1.0)); o[nm] = r
    return o
markets = {
 'korea': block({'kospi': '^KS11', 'kosdaq': '^KQ11'}),
 'us_markets': block({k: IDX[k] for k in ('sp500','nasdaq','dow','vix','dxy','us10y')}),
 'asia_markets': block({k: IDX[k] for k in ('nikkei','shanghai','hsi','taiwan','sensex','vietnam')}),
 'europe_markets': block({k: IDX[k] for k in ('stoxx50','dax','ftse')}),
 'fx_markets': block({'usd_krw':'KRW=X','eur_krw':'EURKRW=X','jpy_krw':'JPYKRW=X','cny_krw':'CNYKRW=X','hkd_krw':'HKDKRW=X'},
                     scales={'jpy_krw': 100.0}),
 'fx_usd': block({'usd_eur':'EUR=X','usd_jpy':'JPY=X','usd_cny':'CNY=X'}),
}
# (fix) CNY/KRW cross fallback: CNYKRW=X 희박/실패 시 USD_KRW / USD_CNY 합성 (5장 '-' 방지)
def _cross(a_tk, b_tk):
    A = {d: v for d, v in closes(RES.get(a_tk))}; B = {d: v for d, v in closes(RES.get(b_tk))}
    return [[d, round(A[d] / B[d], 2)] for d in sorted(set(A) & set(B)) if B.get(d)]
if not (markets['fx_markets'].get('cny_krw') or {}).get('current'):
    _cs = _cross('KRW=X', 'CNY=X')
    if len(_cs) >= 2:
        _r = ret(_cs); _r['trend'] = trend(_r); markets['fx_markets']['cny_krw'] = _r
# (v3.23) KSVKOSPI (코스피 변동성지수) — investing.com 페이지 파싱(현재+1주~1년+anchors), CNBC 폴백
#   CNBC 는 현재값만 제공(이력 API 차단). investing.com 페이지(api 아님)는 차단 없이 받아지며
#   본문에 "last":<현재> + "priceChanges":{pct_1d/1w/1m/3m/6m/1y} 구조가 내장돼 있어 1주~1년 전부 확보.
def _vkospi_cnbc():
    try:
        j = json.loads(get('https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?symbols=.KSVKOSPI&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json', timeout=10, tries=2))
        q = j['FormattedQuoteResult']['FormattedQuote'][0]
        def _n(x):
            try: return float(str(x).replace(',', '').replace('%', '').replace('+', ''))
            except Exception: return None
        cur = _n(q.get('last'))
        if cur is None: return None
        r = {'current': round(cur, 2), 'trend': '실시간(CNBC .KSVKOSPI)'}
        for k, src in (('prev_close', 'previous_day_closing'), ('chg', 'change'), ('1d_pct', 'change_pct')):
            v = _n(q.get(src))
            if v is not None: r[k] = round(v, 2)
        return r
    except Exception as e:
        print('vkospi CNBC 실패:', e); return None

def _vkospi_cache_enrich(base):
    # (req1 fix) investing.com 이 403 으로 막혀 1주~1년·스파크가 비므로, CNBC 현재값을 매 실행
    #   nmr_vkospi_history.json(일별 캐시)에 누적 → 캐시에서 1주~1년 수익률·스파크 앵커를 계산한다(HY 캐시와 동일 패턴).
    import datetime as _dt
    if not base or base.get('current') is None: return base
    cur = base['current']
    cdir = (sorted(glob.glob('/sessions/*/mnt/claudeCowork/_market_report_data'))
            or sorted(glob.glob('/sessions/*/mnt/outputs/_market_report_data')) or ['.'])[0]
    cpath = os.path.join(cdir, 'nmr_vkospi_history.json')
    try: hist = json.load(open(cpath)) if os.path.exists(cpath) else {'series': []}
    except Exception: hist = {'series': []}
    ser = [p for p in hist.get('series', []) if p and p[0] != _dt.date.today().isoformat()]
    ser.append([_dt.date.today().isoformat(), cur]); ser.sort()
    hist['series'] = ser; hist['updated'] = _dt.date.today().isoformat()
    try: json.dump(hist, open(cpath, 'w'), ensure_ascii=False)
    except Exception: pass
    if len(ser) >= 2:
        td = _dt.date.fromisoformat(ser[-1][0])
        for key, days in (('1w_pct',7),('1mo_pct',30),('3mo_pct',91),('6mo_pct',182),('1y_pct',365)):
            past = [p for p in ser if _dt.date.fromisoformat(p[0]) <= td - _dt.timedelta(days=days)]
            if past and past[-1][1]: base[key] = round((cur/past[-1][1]-1)*100, 2)
        if len(ser) >= 3: base['anchors'] = [[p[0], p[1]] for p in ser]
        if base.get('1y_pct') is not None:
            base['trend'] = '캐시 누적 1년 %+.1f%%·1개월 %+.1f%% (CNBC .KSVKOSPI 일별누적)' % (base['1y_pct'], base.get('1mo_pct') or 0)
    return base

def fetch_vkospi():
    # 1순위: investing.com 페이지 본문 내장 JSON("last"+"priceChanges") 파싱 → 현재+1일~1년 + 차트 앵커
    #   ※ investing.com 이 403(anti-bot)으로 막히면 CNBC + 일별캐시(_vkospi_cache_enrich)로 폴백.
    try:
        import re as _re
        req = urllib.request.Request('https://kr.investing.com/indices/kospi-volatility', headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
            'Accept-Language': 'ko,en;q=0.9'})
        html = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', 'replace')
        def _f(s):
            try: return round(float(s), 2)
            except Exception: return None
        mlast = _re.search(r'"last":\s*(-?\d+\.?\d*)', html)
        mpc = _re.search(r'"priceChanges":\s*\{([^}]*)\}', html)
        if mlast and mpc:
            cur = _f(mlast.group(1)); body = mpc.group(1)
            def g(k):
                mm = _re.search(r'"%s":\s*(-?\d+\.?\d*)' % k, body); return _f(mm.group(1)) if mm else None
            r = {'current': cur, 'source': 'investing.com'}
            for dk, sk in (('1d_pct', 'pct_1d'), ('1w_pct', 'pct_1w'), ('1mo_pct', 'pct_1m'), ('3mo_pct', 'pct_3m'), ('6mo_pct', 'pct_6m'), ('1y_pct', 'pct_1y')):
                v = g(sk)
                if v is not None: r[dk] = v
            if cur is not None and r.get('1d_pct') is not None:
                r['prev_close'] = round(cur / (1 + r['1d_pct'] / 100), 2); r['chg'] = round(cur - r['prev_close'], 2)
            # 스파크라인 앵커(기간수익률 역산: 값=현재/(1+pct/100))
            td = dt.date.today(); anch = []
            for sk_, days in (('1y_pct', 365), ('6mo_pct', 182), ('3mo_pct', 91), ('1mo_pct', 30), ('1w_pct', 7), (None, 0)):
                if sk_ is None: anch.append([td.isoformat(), cur])
                elif r.get(sk_) is not None: anch.append([(td - dt.timedelta(days=days)).isoformat(), round(cur / (1 + r[sk_] / 100), 2)])
            if len(anch) >= 3: r['anchors'] = anch
            def _p(x): return ('+%.1f' % x) if x >= 0 else ('%.1f' % x)
            r['trend'] = ('급등세 1년 %s%%·1개월 %s%% (investing.com)' % (_p(r['1y_pct']), _p(r.get('1mo_pct') or 0))) if r.get('1y_pct') is not None else '실시간(investing.com KSVKOSPI)'
            if cur is not None: return r
    except Exception as e:
        print('vkospi investing 실패(403 등)→CNBC+일별캐시 폴백:', e)
    return _vkospi_cache_enrich(_vkospi_cnbc())
_vk = fetch_vkospi()
if _vk: markets['vkospi'] = _vk; print('vkospi(KSVKOSPI):', _vk.get('current'), '전일', _vk.get('prev_close'))
json.dump(markets, open('nmr_markets.json', 'w'), ensure_ascii=False)

# ===== nmr_indexseries.json =====
idxs = {k: S(IDX[k]) for k in ('kospi','kosdaq','sp500','nasdaq','dow','vix','dxy','us10y','nikkei','shanghai','hsi','taiwan','sensex','vietnam','stoxx50','dax','ftse')}
json.dump(idxs, open('nmr_indexseries.json', 'w'), ensure_ascii=False)

# ===== nmr_series2.json =====
series2 = {
 'fx': {k: S(FX[k]) for k in ('usd_krw','eur_krw','jpy_krw','cny_krw','hkd_krw','usd_jpy','usd_cny','usd_eur')},
 'commodities': {k: S(COMM[k]) for k in ('wti','brent','natgas','gold','silver','copper','platinum','rare_earth','corn','soybean','wheat','sugar','coffee','orange','crb','bdi','dba','de','ntr')},
 'strat_etf': {k: S(v) for k, v in NF.items()},  # (v3.46) 4.4 비철금속 12행 스파크(탄산리튬은 시계열 없음)
}
series2['commodities'].update({k: S(v) for k, v in ENERGY_ETF.items()})  # (사용자요청) 4.1 에너지 ETF(KODEX) 스파크라인용 1년 주봉 시계열
if len(series2['fx'].get('cny_krw') or []) < 2:
    series2['fx']['cny_krw'] = _cross('KRW=X', 'CNY=X')
json.dump(series2, open('nmr_series2.json', 'w'), ensure_ascii=False)

# ===== nmr_commod.json =====
def grpc(label, names, mp):
    rs = [mp[n] for n in names if mp.get(n) and mp[n].get('1y_pct') is not None]
    if not rs: return ''
    a1 = sum(r['1mo_pct'] or 0 for r in rs) / len(rs); ay = sum(r['1y_pct'] or 0 for r in rs) / len(rs)
    tone = '강세' if ay > 0 else '약세'
    return f"{label} 군은 최근 1개월 평균 {a1:+.1f}%, 1년 {ay:+.1f}%로 {tone} 흐름이다."
energy = block({'wti':'CL=F','brent':'BZ=F','natgas':'NG=F', **ENERGY_ETF})  # (사용자요청) WTI·천연가스 + 국내 에너지 ETF 2종(전통 화석연료·AI 전력망 인프라)
metals = block({'gold':'GC=F','silver':'SI=F','copper':'HG=F','platinum':'PL=F','rare_earth':'REMX'})
agri = block({'corn':'ZC=F','soybean':'ZS=F','wheat':'ZW=F',
              'sugar':'SB=F','coffee':'KC=F','orange':'OJ=F',
              'crb':'^TRCCRB','bdi':'BDRY','dba':'DBA','de':'DE','ntr':'NTR'})
# ===== (v3.46) 4.4 비철금속 (배터리·우라늄·전략광물 밸류체인) =====
def nfrow(name, key, note, suffix=None):
    sym = NF.get(key); r = R(sym) if sym else {}
    if sym: add_day(r, sym)
    r['name'] = name; r['note'] = note; r['spark'] = key
    if suffix: r['curSuffix'] = suffix
    r['trend'] = trend(r) if r.get('1y_pct') is not None else ''
    return r
def nfspot(name, note, suffix):  # 시계열 없는 현물 참고행(최종 폴백)
    return {'name': name, 'note': note, 'spark': None, 'curSuffix': suffix, 'current': None, 'trend': ''}
# (v3.47) 탄산리튬 현물 추세 — GFEX 碳酸锂 主连(EastMoney kline, secid=225.lcm) 무료 일봉 시계열 → 1일~1년 추세+스파크.
#  history(push2his)는 버스트에 스로틀 → 재시도, 실패 시 realtime(push2, 별도 엣지)로 현재가만, 그래도 없으면 null.
def fetch_lithium():
    # (req6 · v3.50) 탄산리튬 현물 추세 — Sina 碳酸锂 主连(LC0) 일봉 kline(GBK) 우선, EastMoney 폴백.
    #   EastMoney push2his 는 샌드박스에서 연결 차단되는 사례가 있어 Sina 를 1순위로 둔다.
    import urllib.request as _u, time as _t, re as _re
    def _sina(url, ref='https://finance.sina.com.cn'):
        return _u.urlopen(_u.Request(url, headers={'User-Agent':'Mozilla/5.0','Referer':ref}), timeout=15).read().decode('gbk','replace')
    ser = []; cur = None
    try:
        _raw = _sina('https://stock2.finance.sina.com.cn/futures/api/jsonp.php/v=/InnerFuturesNewService.getDailyKLine?symbol=LC0')
        _m = _re.search(r'(\[.*\])', _raw)
        _arr = json.loads(_m.group(1)) if _m else []
        ser = [[x['d'], round(float(x['c']), 2)] for x in _arr if x.get('d') and x.get('c')]
        if ser: cur = ser[-1][1]
    except Exception: ser = []
    if not cur:
        try:
            _q = _sina('https://hq.sinajs.cn/list=nf_LC0')
            _parts = _q.split('"')[1].split(',') if '"' in _q else []
            # nf_ 레이아웃: [0]名称 [1]时间 [2]开 [3]高 [4]低 [5..8] 매도/매수/최신 등 — 최신가는 idx8(现价) 근사
            if len(_parts) > 8:
                for _i in (8, 6, 5):
                    try:
                        _v = float(_parts[_i])
                        if _v > 0: cur = round(_v, 2); break
                    except Exception: pass
        except Exception: pass
    if not ser and not cur:  # (폴백) EastMoney
        try:
            _r = _u.urlopen(_u.Request('https://push2.eastmoney.com/api/qt/stock/get?secid=225.lcm&fields=f43', headers={'User-Agent':'Mozilla/5.0','Referer':'https://quote.eastmoney.com/'}), timeout=12).read().decode('utf-8','replace')
            _v = (json.loads(_r).get('data') or {}).get('f43')
            cur = float(_v) if _v not in (None, '-', 0) else None
        except Exception: pass
    return ser, cur
_li_ser, _li_cur = fetch_lithium()
if _li_ser:
    li_row = ret([[d, v] for d, v in _li_ser]); li_row['name'] = '탄산리튬 (Lithium Carbonate)'
    li_row['note'] = '중국 배터리급 현물(GFEX 碳酸锂 主连 선물, EastMoney)'; li_row['spark'] = 'lithium'; li_row['curSuffix'] = ' CNY/톤'
    if len(_li_ser) >= 2 and _li_ser[-2][1]: li_row['1d_pct'] = round((_li_ser[-1][1] / _li_ser[-2][1] - 1) * 100, 2)
    li_row['trend'] = trend(li_row)
elif _li_cur:
    li_row = {'name': '탄산리튬 (Lithium Carbonate)', 'note': '중국 배터리급 현물(GFEX 碳酸锂 主连) — 시계열 일시 미확보, 현재가만', 'spark': None, 'curSuffix': ' CNY/톤', 'current': _li_cur, 'trend': ''}
else:
    li_row = nfspot('탄산리튬 (Lithium Carbonate)', '중국 배터리급 현물 — 무료 시계열 일시 미확보(참고치)', ' CNY/톤')
try:  # 스파크용 시계열 주입(있을 때만)
    if _li_ser: series2['strat_etf']['lithium'] = _li_ser; json.dump(series2, open('nmr_series2.json', 'w'), ensure_ascii=False)
except Exception: pass
nonferrous = {'groups': [
 {'title': '배터리 & 전기차 (Battery & EV)',
  'desc': '전기차 침투율 둔화(캐즘) 우려와 각국의 정책(보조금·관세)에 따라 변동성이 큰 섹터입니다. 광물 가격과 전방 수요(완성차 판매량)를 동시에 체크해야 합니다.',
  'core': '탄산리튬 가격 (Lithium Carbonate)',
  'core_desc': '배터리 원가의 핵심으로, 리튬 가격의 반등 여부가 국내 2차전지 소재주(양극재)들의 실적(판가)·투심 회복의 핵심입니다.',
  'rows': [
    li_row,
    nfrow('LIT (Global X Lithium & Battery Tech ETF)', 'lit', '글로벌 리튬 채굴~배터리 셀 제조 전체 밸류체인 자금 흐름'),
    nfrow('테슬라 (TSLA)', 'tsla', '글로벌 전기차 수요·자율주행(SW) 전환의 바로미터'),
    nfrow('KODEX 2차전지산업', 'kodex_batt', 'LG에너지솔루션 등 셀 메이커·에코프로 등 소재기업 센티먼트', ' 원'),
  ]},
 {'title': '우라늄 & 원자력 (Uranium & Nuclear Power)',
  'desc': '우라늄 공급 부족과 원전 가동 연장 기조에 따른 가격 추이가 관련주 랠리의 근본 배경입니다.',
  'core': '우라늄 선물 가격 (Uranium Futures)',
  'core_desc': '우라늄 공급 부족·원전 수명 연장 기조에 따른 가격 추이가 관련주 랠리의 근본 배경입니다.',
  'rows': [
    nfrow('우라늄 (SRUUF · Sprott 실물 우라늄, 선물 근사)', 'sruuf', '무료 우라늄 선물 피드 부재 → 실물 우라늄 트러스트로 근사'),
    nfrow('URA (Global X Uranium ETF)', 'ura', '글로벌 우라늄 채굴·원전 장비 기업 — 우라늄 테마 대장 ETF'),
    nfrow('NLR (VanEck Uranium+Nuclear Energy ETF)', 'nlr', '발전소 포함 원자력 에너지 밸류체인 전반'),
    nfrow('HANARO 원자력iSelect', 'hanaro_nuke', '두산에너빌리티 등 한국 원전 시공·기자재 수출 모멘텀(체코·폴란드)', ' 원'),
  ]},
 {'title': '전략 광물 & 에너지 인프라 (Strategic Minerals)',
  'desc': "일명 '닥터 코퍼'. 경기를 선행할 뿐 아니라 전력망·전기차·AI 데이터센터 등 거의 모든 미래 산업에 필수적인 전략 광물입니다.",
  'core': '구리 선물 (Copper Futures - COMEX)',
  'core_desc': '경기 선행 지표(닥터 코퍼)이자 전력망·전기차·AI 데이터센터 등 미래 산업 전반에 필수적인 전략 광물입니다.',
  'rows': [
    nfrow('구리 선물 (Copper Futures, COMEX)', 'copper', '경기·전력·전기차·AI 인프라 수요를 선행하는 지표(닥터 코퍼)', ' $/lb'),
    nfrow('COPX (Global X Copper Miners ETF)', 'copx', '글로벌 주요 구리 채굴 기업 — 구리가격 상승 수혜 추적'),
    nfrow('REMX (VanEck Rare Earth/Strategic Metals ETF)', 'remx', '희토류·리튬·코발트 등 전략광물 채굴·정제(중국 외 공급망 트렌드)'),
    nfrow('KODEX 구리선물(H)', 'kodex_copper', '환헤지된 구리 선물 가격 추종', ' 원'),
  ]},
], 'comment': '한국은 전략광물을 직접 채굴하는 기업보다 구리·전력을 다루는 전선·산전(産電) 기업을 함께 모니터링하는 것이 유리합니다.'}
commod = {
 'energy': energy, 'metals': metals, 'agriculture': agri,
 'nonferrous': nonferrous,
 'energy_comment': grpc('에너지', ['wti','natgas','kodex_energy','kodex_aipower'], energy),
 'metals_comment': grpc('금속', ['gold','silver','copper','platinum'], metals),
 'agri_comment': grpc('농산물', ['corn','soybean','wheat','sugar','coffee','orange'], agri),
 'series': {k: S(v) for k, v in {**COMM, **STRAT}.items() if k != 'rare_earth'},
}
json.dump(commod, open('nmr_commod.json', 'w'), ensure_ascii=False)

# ===== nmr_usetf.json + nmr_etfseries.json =====
usetf = {'index': [], 'sector': [], 'theme': [], 'defensive': [], 'comment': '', 'asof': dt.date.today().isoformat()}
etfseries = {}
for sym, (grp, name, desc, wt) in ETF.items():
    r = R(sym); add_day(r, sym); row = {'symbol': sym, 'name': name, 'desc': desc, **r, 'trend': trend(r)}
    if wt is not None: row['weight'] = wt
    usetf[grp].append(row)
    etfseries[sym] = S(sym)
nidx = [x for x in usetf['index'] if x.get('1y_pct') is not None]
if nidx:
    avg = sum(x['1y_pct'] for x in nidx) / len(nidx)
    usetf['comment'] = f"미국 지수 ETF 1년 평균 {avg:+.1f}%. 분배금 큰 ETF(SCHD·JEPI·TLT·IEF)는 가격수익률 기준이라 총수익률 대비 낮게 표시됨."
json.dump(usetf, open('nmr_usetf.json', 'w'), ensure_ascii=False)

# (v3.7.x) 3.5.1 유럽 주요 ETF — 국내상장(.KS)+미국상장. 별도 파일 nmr_euetf.json 산출(merge 가 markets.europe_etfs 로 주입).
euetf = {'items': [], 'comment': '', 'asof': dt.date.today().isoformat()}
for _dsym, (_tk, _name, _desc, _region) in EUETF.items():
    _r = R(_tk); add_day(_r, _tk)
    euetf['items'].append({'symbol': _dsym, 'name': _name, 'desc': _desc, 'region': _region, **_r, 'trend': trend(_r)})
    etfseries[_dsym] = S(_tk)  # 3.5.1 추세(1Y) 스파크라인용 (charts/spark_etf_<dsym>.png)
_euok = [x for x in euetf['items'] if x.get('1y_pct') is not None]
if _euok:
    _eavg = sum(x['1y_pct'] for x in _euok) / len(_euok)
    euetf['comment'] = (f"유럽 익스포저 ETF {len(_euok)}종 1년 평균 {_eavg:+.1f}%. 국내상장분(.KS)은 원화·환헤지, "
                        f"미국상장분은 달러 기준이라 환효과가 다르게 반영됨(주봉 가격수익률·분배금 제외).")
json.dump(euetf, open('nmr_euetf.json', 'w'), ensure_ascii=False)

json.dump(etfseries, open('nmr_etfseries.json', 'w'), ensure_ascii=False)

# ===== nmr_crypto_series.json =====
cs = {}
for nm, tk in CRYPTO.items(): cs[nm] = closevol(CRES.get(tk))
try:
    j = json.loads(get('https://api.alternative.me/fng/?limit=400&format=json', timeout=8, tries=1))
    fng = [[dt.datetime.utcfromtimestamp(int(x['timestamp'])).strftime('%Y-%m-%d'), int(x['value'])] for x in j.get('data', [])]
    fng.reverse(); cs['fng'] = fng
except Exception as e:
    cs['fng'] = []; print('fng 실패(비차단):', e)
json.dump(cs, open('nmr_crypto_series.json', 'w'), ensure_ascii=False)

# ===== (req7) 김치 프리미엄 폴백 — 업비트 KRW + 바이낸스 USD + 환율 직접 계산 (CoinInfo 429 대비) =====
try:
    _fx = json.loads(get('https://open.er-api.com/v6/latest/USD', timeout=10))
    _usdkrw = _fx.get('rates', {}).get('KRW')
    _kc = {'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT', 'XRP': 'XRPUSDT', 'SOL': 'SOLUSDT'}
    _up = json.loads(get('https://api.upbit.com/v1/ticker?markets=' + ','.join('KRW-' + c for c in _kc), timeout=10))
    _upm = {x['market']: x['trade_price'] for x in _up}
    _kcoins = []
    for _c, _bs in _kc.items():
        _krw = _upm.get('KRW-' + _c)
        try: _usd = float(json.loads(get('https://api.binance.com/api/v3/ticker/price?symbol=' + _bs, timeout=10))['price'])
        except Exception: _usd = None
        _pp = round((_krw / (_usd * _usdkrw) - 1) * 100, 2) if (_krw and _usd and _usdkrw) else None
        _kcoins.append({'symbol': _c, 'upbit_krw': _krw, 'binance_usd': _usd, 'premium_pct': _pp,
                        'status': '정상' if _pp is not None else '데이터부족'})
    json.dump({'rate_usd_krw': _usdkrw, 'coins': _kcoins, 'asof': dt.date.today().isoformat()},
              open('nmr_kimchi.json', 'w'), ensure_ascii=False)
    print('kimchi:', ', '.join('%s %s%%' % (c['symbol'], c['premium_pct']) for c in _kcoins))
except Exception as e:
    print('kimchi 실패(비차단):', e)

# ===== 요약 =====
def ok(d):
    return sum(1 for g in d.values() if isinstance(g, dict) for v in g.values() if isinstance(v, dict) and v.get('current') is not None)
print('markets ok-fields:', ok(markets), '| sp500', markets['us_markets']['sp500'].get('current'), '| usd_krw', markets['fx_markets']['usd_krw'].get('current'), '| jpy_krw', markets['fx_markets']['jpy_krw'].get('current'))
print('indexseries:', {k: len(v) for k, v in idxs.items()})
print('commod: wti', energy['wti'].get('current'), '| gold', metals['gold'].get('current'), '| strat', len(series2.get('strat_etf', {})))
print('usetf: idx', len(usetf['index']), 'sector', len(usetf['sector']), 'theme', len(usetf['theme']), 'def', len(usetf['defensive']), '| etfseries', len(etfseries))
print('euetf(3.5.1):', len(euetf['items']), 'items |', ', '.join(f"{x['symbol']}={x.get('current')}" for x in euetf['items']))
print('crypto: btc', len(cs.get('btc', [])), 'fng', len(cs.get('fng', [])))
