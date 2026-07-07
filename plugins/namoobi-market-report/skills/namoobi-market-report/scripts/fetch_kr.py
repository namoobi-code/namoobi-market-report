#!/usr/bin/env python3
# fetch_kr.py (v3.7) — 한국 시장데이터 sandbox 수집 (Chrome 불필요, stdlib only).
# KoreaTechFlowsAgent 데이터 수집 완전 대체. Phase 1 단일 메시지에서 Agent 발행과 동시 tool-call,
# 스레드 병렬 → 단독 ~10초(각 bash 호출은 독립 45초 예산). FRED 는 비차단·빠른 실패.
# 산출: nmr_kr_ohlcv.json, nmr_kr_invest.json, nmr_hy_series.json(비차단)
# 사용: python3 fetch_kr.py [WORK_DIR]
import json, urllib.request, datetime as dt, time, sys, os
from concurrent.futures import ThreadPoolExecutor
_SDIR = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, _SDIR)  # v3.16: chdir 전에 확보(nmr_fred 임포트용)
if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
    os.chdir(sys.argv[1])
H = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json', 'Referer': 'https://finance.daum.net/'}

def get(url, headers=H, tries=2, timeout=12):
    last = None
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout).read().decode('utf-8', 'replace')
        except Exception as e:
            last = e; time.sleep(1)
    raise last

def yahoo_ohlc(sym):
    u = f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1y&interval=1d'
    j = json.loads(get(u, {'User-Agent': 'Mozilla/5.0'})); r = j['chart']['result'][0]
    ts = r['timestamp']; q = r['indicators']['quote'][0]; out = {}
    for i, t in enumerate(ts):
        d = dt.datetime.utcfromtimestamp(t + 32400).strftime('%Y-%m-%d')
        o, h, l, c = q['open'][i], q['high'][i], q['low'][i], q['close'][i]
        if None in (o, h, l, c): continue
        out[d] = [round(o, 2), round(h, 2), round(l, 2), round(c, 2)]
    return out

def daum_days(mkt):
    u = f'https://finance.daum.net/api/market_index/days?page=1&perPage=250&market={mkt}&pagination=true'
    j = json.loads(get(u)); rows = []
    for d in j['data']:
        rows.append([d['date'][:10], d['tradePrice'], int(d['accTradeVolume']),
                     round(d['foreignStraightPurchasePrice'] / 1e8),
                     round(d['institutionStraightPurchasePrice'] / 1e8),
                     round(d['individualStraightPurchasePrice'] / 1e8)])
    rows.reverse()
    return rows

def build_ohlcv(yh, daum):
    ohlcv = []; flows = []
    for date, close, vol, F, I, P in daum:
        flows.append([date, F, I, P])
        if date in yh:
            o, h, l, c = yh[date]; ohlcv.append([date, o, h, l, c, vol])
        else:
            ohlcv.append([date, close, close, close, close, vol])
    return ohlcv, flows

def inv(mkt, itype):
    u = f'https://finance.daum.net/api/trend/investor_purchase?page=1&perPage=10&market={mkt}&investorType={itype}&pagination=true'
    j = json.loads(get(u, {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json', 'Referer': 'https://finance.daum.net/domestic/influential_investors'}))
    d = j.get('data', {})
    def lst(arr): return [{'name': x['name'], 'detail': f"순매수 {round(x['straightPurchasePrice'] / 1e8):,}억원 (주가 {x['changeRate'] * 100:+.1f}%)"} for x in (arr or [])[:10]]
    def lstS(arr): return [{'name': x['name'], 'detail': f"순매도 {abs(round(x['straightPurchasePrice'] / 1e8)):,}억원 (주가 {x['changeRate'] * 100:+.1f}%)"} for x in (arr or [])[:10]]
    return lst(d.get('BUY')), lstS(d.get('SELL'))

def _hy_cache():  # v3.14: FRED 차단 시 영구 누적 캐시(연결폴더) 폴백 — HY 표·차트 항상 채움
    import glob as _g
    for p in [os.path.join(os.getcwd(), '_market_report_data', 'nmr_hy_history.json')] + _g.glob('/sessions/*/mnt/claudeCowork/_market_report_data/nmr_hy_history.json') + _g.glob('/sessions/*/mnt/outputs/_market_report_data/nmr_hy_history.json'):
        try:
            s = (json.load(open(p)).get('series')) or []
            if len(s) >= 5: return {'series': s, 'points': {'current': s[-1]}, 'source': 'persistent cache (FRED 차단 폴백)'}
        except Exception: pass
    return None

def _hy_fredapi():  # v3.16: FRED API 키(SECURITY/secrets.env FRED_API_KEY) 직접 호출 — 공식 실측·미러 불필요·~0.4s
    from nmr_fred import fred_key, fred_series
    if not fred_key(): raise ValueError('no FRED_API_KEY')
    daily = fred_series('BAMLH0A0HYM2', start=(dt.date.today() - dt.timedelta(days=1200)).isoformat())
    if len(daily) < 30: raise ValueError('fred api <30')
    cut = (dt.date.today() - dt.timedelta(days=430)).isoformat()
    return {'series': [p for p in daily if p[0] >= cut], 'points': {'current': daily[-1]}, '_full': daily,
            'source': 'ICE BofA US HY OAS (FRED BAMLH0A0HYM2) — FRED API 일별 실측'}

def _hy_equibles():  # v3.15: FRED CSV 직접호출은 sandbox 차단 → equibles.com(FRED 실측 미러)에서 일별 OAS 파싱
    import re as _re
    html = get('https://equibles.com/economicdata/bamlh0a0hym2', {'User-Agent': 'Mozilla/5.0'}, tries=2, timeout=20)
    pairs = _re.findall(r'<td[^>]*>\s*(\d{4}-\d{2}-\d{2})\s*</td>\s*<td[^>]*>\s*([0-9]+\.[0-9]+)\s*</td>', html)
    daily = sorted([[d, float(v)] for d, v in pairs])
    if len(daily) < 30: raise ValueError('equibles parse<30')
    cut = (dt.date.today() - dt.timedelta(days=430)).isoformat()
    return {'series': [p for p in daily if p[0] >= cut], 'points': {'current': daily[-1]}, '_full': daily,
            'source': 'ICE BofA US HY OAS (FRED BAMLH0A0HYM2) — equibles.com 실측 일별'}

def hy_series():  # v3.16: FRED API(키) → equibles 미러 → 영구 캐시 폴백
    for fn in (_hy_fredapi, _hy_equibles):
        try: return fn()
        except Exception: pass
    c = _hy_cache()
    if c: return c
    raise ValueError('HY 수집 실패 — FRED API·equibles·영구캐시 모두 불가')

def safe(fn, *a):
    try: return fn(*a)
    except Exception as e: return e

with ThreadPoolExecutor(max_workers=9) as ex:
    f_ksy = ex.submit(yahoo_ohlc, '%5EKS11'); f_kqy = ex.submit(yahoo_ohlc, '%5EKQ11')
    f_ksd = ex.submit(daum_days, 'KOSPI'); f_kqd = ex.submit(daum_days, 'KOSDAQ')
    f_iff = ex.submit(safe, inv, 'KOSPI', 'FOREIGN'); f_ifi = ex.submit(safe, inv, 'KOSPI', 'INSTITUTION')
    f_iqf = ex.submit(safe, inv, 'KOSDAQ', 'FOREIGN'); f_iqi = ex.submit(safe, inv, 'KOSDAQ', 'INSTITUTION')
    f_hy = ex.submit(safe, hy_series)
ks_y, kq_y, ks_d, kq_d = f_ksy.result(), f_kqy.result(), f_ksd.result(), f_kqd.result()

ko, kf = build_ohlcv(ks_y, ks_d); qo, qf = build_ohlcv(kq_y, kq_d)
json.dump({'kospi_ohlcv': ko, 'kosdaq_ohlcv': qo, 'kospi_flows_daily': kf, 'kosdaq_flows_daily': qf},
          open('nmr_kr_ohlcv.json', 'w'), ensure_ascii=False)
print('OHLCV: kospi', len(ko), 'kosdaq', len(qo), '| last kospi', ko[-1], '| flows last', kf[-1])

def ok2(x): return isinstance(x, tuple)
if ok2(f_iff.result()) and ok2(f_ifi.result()) and ok2(f_iqf.result()) and ok2(f_iqi.result()):
    (ks_f_b, ks_f_s), (ks_i_b, ks_i_s) = f_iff.result(), f_ifi.result()
    (kq_f_b, kq_f_s), (kq_i_b, kq_i_s) = f_iqf.result(), f_iqi.result()
    invest = {'asof': ks_d[-1][0],
              'kospi_foreign_buy': ks_f_b, 'kospi_foreign_sell': ks_f_s, 'kospi_inst_buy': ks_i_b, 'kospi_inst_sell': ks_i_s,
              'kosdaq_foreign_buy': kq_f_b, 'kosdaq_foreign_sell': kq_f_s, 'kosdaq_inst_buy': kq_i_b, 'kosdaq_inst_sell': kq_i_s}
    json.dump(invest, open('nmr_kr_invest.json', 'w'), ensure_ascii=False)
    print('수급: KOSPI외인매수', len(ks_f_b), '매도', len(ks_f_s), '| 기관매수', len(ks_i_b), '| KOSDAQ외인매수', len(kq_f_b))
else:
    json.dump({'asof': '', 'note': '수급 수집 실패'}, open('nmr_kr_invest.json', 'w'), ensure_ascii=False)
    print('수급 실패(빈값으로 진행):', f_iff.result())

hy = f_hy.result()
if isinstance(hy, dict):
    json.dump(hy, open('nmr_hy_series.json', 'w'), ensure_ascii=False)
    try:  # v3.14: 영구 누적 캐시 갱신(연결폴더) — FRED 차단돼도 다음 실행이 폴백
        import glob as _g
        _cp = _g.glob('/sessions/*/mnt/claudeCowork/_market_report_data')
        if _cp:
            _hp = os.path.join(_cp[0], 'nmr_hy_history.json')
            _hist = {}
            if os.path.exists(_hp):
                try: _hist = json.load(open(_hp))
                except Exception: _hist = {}
            _mer = {d: v for d, v in (_hist.get('series') or [])}
            for d, v in (hy.get('_full') or hy['series']): _mer[d] = v
            _cur = hy.get('points', {}).get('current')
            if _cur: _mer[_cur[0]] = _cur[1]
            _hist['series'] = [[d, _mer[d]] for d in sorted(_mer)]
            _hist['updated'] = dt.date.today().isoformat()
            json.dump(_hist, open(_hp, 'w'), ensure_ascii=False)
    except Exception: pass
    print('HY: months', len(hy['series']), 'current', hy['points']['current'])
else:
    print('HY 실패(차트 비차단, 캐시/에이전트 폴백):', hy)
# v3.16 end
