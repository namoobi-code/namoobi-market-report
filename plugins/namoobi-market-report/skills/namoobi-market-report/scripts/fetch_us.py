#!/usr/bin/env python3
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
        'platinum':'PL=F','rare_earth':'REMX','corn':'ZC=F','soybean':'ZS=F','wheat':'ZW=F'}
STRAT = {'lit':'LIT','remx':'REMX','ura':'URA','urnm':'URNM'}
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
CRYPTO = {'btc':'BTC-USD','eth':'ETH-USD','xrp':'XRP-USD','sol':'SOL-USD'}

# ===== 병렬 fetch =====
wk_tickers = {}  # name->ticker for weekly
for d in (IDX, FX, COMM, STRAT): wk_tickers.update({v: v for v in d.values()})
for s in ETF: wk_tickers[s] = s
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
def day_stats(tk, scale=1.0):
    s = closes(DRES.get(tk))
    if len(s) < 2: return (None, None, None, None)
    cur = s[-1][1] * scale; prev = s[-2][1] * scale
    if not prev: return (None, None, None, None)
    dec = 4 if abs(cur) < 10 else (3 if abs(cur) < 100 else 2)
    prev_pct = round((s[-2][1] / s[-3][1] - 1) * 100, 2) if (len(s) >= 3 and s[-3][1]) else None  # (req5) 직전장
    return (round(cur - prev, dec), round((cur / prev - 1) * 100, 2), round(prev, dec), prev_pct)
def add_day(r, tk, scale=1.0):
    if isinstance(r, dict):
        c, p, pc, ppct = day_stats(tk, scale)
        if ppct is not None: r['prev_pct'] = ppct  # (req5) 1일 칸=직전장 등락률
        if pc is not None:
            cur = r.get('current')  # (req10) 현재가 기준 1일변동 재계산(정합)
            if cur is not None and pc:
                dec = 4 if abs(cur) < 10 else (3 if abs(cur) < 100 else 2)
                r['chg'] = round(cur - pc, dec); r['1d_pct'] = round((cur / pc - 1) * 100, 2); r['prev_close'] = pc
            else: r['chg'] = c; r['1d_pct'] = p; r['prev_close'] = pc
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
    # (req1) investing.com 403 차단 시 CNBC 현재값을 nmr_vkospi_history.json(일별캐시) 누적 → 1주~1년·스파크 계산.
    import datetime as _dt
    if not base or base.get('current') is None: return base
    cur=base['current']
    cdir=(sorted(glob.glob('/sessions/*/mnt/claudeCowork/_market_report_data')) or sorted(glob.glob('/sessions/*/mnt/outputs/_market_report_data')) or ['.'])[0]
    cpath=os.path.join(cdir,'nmr_vkospi_history.json')
    try: hist=json.load(open(cpath)) if os.path.exists(cpath) else {'series':[]}
    except Exception: hist={'series':[]}
    ser=[p for p in hist.get('series',[]) if p and p[0]!=_dt.date.today().isoformat()]
    ser.append([_dt.date.today().isoformat(),cur]); ser.sort()
    hist['series']=ser; hist['updated']=_dt.date.today().isoformat()
    try: json.dump(hist,open(cpath,'w'),ensure_ascii=False)
    except Exception: pass
    if len(ser)>=2:
        td=_dt.date.fromisoformat(ser[-1][0])
        for key,days in (('1w_pct',7),('1mo_pct',30),('3mo_pct',91),('6mo_pct',182),('1y_pct',365)):
            past=[p for p in ser if _dt.date.fromisoformat(p[0])<=td-_dt.timedelta(days=days)]
            if past and past[-1][1]: base[key]=round((cur/past[-1][1]-1)*100,2)
        if len(ser)>=3: base['anchors']=[[p[0],p[1]] for p in ser]
    return base

def fetch_vkospi():
    # 1순위: investing.com 페이지 본문 내장 JSON("last"+"priceChanges") 파싱 → 현재+1일~1년 + 차트 앵커
    #   ※ investing.com 403 차단 시 CNBC+일별캐시 폴백. (워크플로우는 web_fetch 권장)
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
            td = dt.date.today(); anch = []
            for sk_, days in (('1y_pct', 365), ('6mo_pct', 182), ('3mo_pct', 91), ('1mo_pct', 30), ('1w_pct', 7), (None, 0)):
                if sk_ is None: anch.append([td.isoformat(), cur])
                elif r.get(sk_) is not None: anch.append([(td - dt.timedelta(days=days)).isoformat(), round(cur / (1 + r[sk_] / 100), 2)])
            if len(anch) >= 3: r['anchors'] = anch
            def _p(x): return ('+%.1f' % x) if x >= 0 else ('%.1f' % x)
            r['trend'] = ('급등세 1년 %s%%·1개월 %s%% (investing.com)' % (_p(r['1y_pct']), _p(r.get('1mo_pct') or 0))) if r.get('1y_pct') is not None else '실시간(investing.com KSVKOSPI)'
            if cur is not None: return r
    except Exception as e:
        print('vkospi investing 실패(403)→CNBC+일별캐시 폴백:', e)
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
 'commodities': {k: S(COMM[k]) for k in ('wti','brent','natgas','gold','silver','copper','platinum','rare_earth','corn','soybean','wheat')},
 'strat_etf': {k: S(STRAT[k]) for k in STRAT},
}
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
energy = block({'wti':'CL=F','brent':'BZ=F','natgas':'NG=F'})
metals = block({'gold':'GC=F','silver':'SI=F','copper':'HG=F','platinum':'PL=F','rare_earth':'REMX'})
agri = block({'corn':'ZC=F','soybean':'ZS=F','wheat':'ZW=F'})
strat_etf_rows = []
for k, sym in STRAT.items():
    r = R(sym); r['name'] = sym; r['trend'] = trend(r); add_day(r, sym); strat_etf_rows.append(r)
commod = {
 'energy': energy, 'metals': metals, 'agriculture': agri,
 'strategic_metals': {'etf': strat_etf_rows},
 'energy_comment': grpc('에너지', ['wti','brent','natgas'], energy),
 'metals_comment': grpc('금속', ['gold','silver','copper','platinum'], metals),
 'agri_comment': grpc('농산물', ['corn','soybean','wheat'], agri),
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

# ===== 요약 =====
def ok(d):
    return sum(1 for g in d.values() if isinstance(g, dict) for v in g.values() if isinstance(v, dict) and v.get('current') is not None)
print('markets ok-fields:', ok(markets), '| sp500', markets['us_markets']['sp500'].get('current'), '| usd_krw', markets['fx_markets']['usd_krw'].get('current'), '| jpy_krw', markets['fx_markets']['jpy_krw'].get('current'))
print('indexseries:', {k: len(v) for k, v in idxs.items()})
print('commod: wti', energy['wti'].get('current'), '| gold', metals['gold'].get('current'), '| strat', len(strat_etf_rows))
print('usetf: idx', len(usetf['index']), 'sector', len(usetf['sector']), 'theme', len(usetf['theme']), 'def', len(usetf['defensive']), '| etfseries', len(etfseries))
print('crypto: btc', len(cs.get('btc', [])), 'fng', len(cs.get('fng', [])))
