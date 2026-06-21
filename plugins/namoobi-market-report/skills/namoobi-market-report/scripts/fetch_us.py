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

# ===== nmr_markets.json =====
def block(mp, scales=None):
    scales = scales or {}
    o = {}
    for nm, tk in mp.items():
        r = R(tk, scales.get(nm, 1.0)); r['trend'] = trend(r); o[nm] = r
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
json.dump(markets, open('nmr_markets.json', 'w'), ensure_ascii=False)

# ===== nmr_indexseries.json =====
idxs = {k: S(IDX[k]) for k in ('kospi','kosdaq','sp500','nasdaq','dow','vix','dxy','us10y','nikkei','shanghai','hsi','taiwan','sensex','vietnam','stoxx50','dax','ftse')}
json.dump(idxs, open('nmr_indexseries.json', 'w'), ensure_ascii=False)

# ===== nmr_series2.json =====
series2 = {
 'fx': {k: S(FX[k]) for k in ('usd_krw','eur_krw','jpy_krw','cny_krw','hkd_krw','usd_jpy')},
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
    r = R(sym); r['name'] = sym; r['trend'] = trend(r); strat_etf_rows.append(r)
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
    r = R(sym); row = {'symbol': sym, 'name': name, 'desc': desc, **r, 'trend': trend(r)}
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
