#!/usr/bin/env python3
# fetch_macro.py — 결정적 매크로 수집 (FRED 직접·sandbox·stdlib). 에이전트 변동성 제거 → 물가·BEI·고용·금리 매일 확실 수집.
# 산출: nmr_macro.json {macro:{series, rates, inflation:{rows}, employment:{rows}, sentiment}}  (ISM·선행EPS/PER 는 미수집→merge dbrows/DB 가 백필)
# FRED 도달 확인됨(http200). YoY/MoM/변화율은 지수레벨에서 계산. 실패 시리즈는 빈값(merge 가 DB 백필+'변경 미확인' 플래그).
# v3.16: FRED API 키(SECURITY/secrets.env FRED_API_KEY) 직접 호출 우선 → fredgraph.csv 폴백 (nmr_fred.py 공용 헬퍼).
import sys, os, json, datetime as dt, subprocess
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nmr_fred import fred_series as _fred
W = sys.argv[1] if (len(sys.argv) > 1 and os.path.isdir(sys.argv[1])) else '.'

def fred(sid, cosd='2023-01-01'):
    # API JSON(키) 단건 ~0.4s, 실패/무키 시 CSV 폴백 — 재시도 포함 (nmr_fred.fred_series)
    return _fred(sid, start=cosd)

def _get(sid, cosd='2023-01-01'):
    try: return fred(sid, cosd)
    except Exception as e: sys.stderr.write('fred %s fail %s\n' % (sid, e)); return []

IDS = {'CPIAUCSL':'2023-01-01','CPILFESL':'2023-01-01','PCEPI':'2023-01-01','PCEPILFE':'2023-01-01','PPIFIS':'2023-01-01',
       'T10YIE':'2025-06-01','DGS2':'2024-06-01','DGS10':'2024-06-01','DFF':'2021-06-01','FEDFUNDS':'2021-06-01',
       'UNRATE':'2024-06-01','PAYEMS':'2024-06-01','RSAFS':'2024-06-01','A191RL1Q225SBEA':'2023-01-01',
       'ICSA':'2025-06-01'}
D = {}; _fails = 0; _items = list(IDS.items())
for _idx, (k, cosd) in enumerate(_items):
    D[k] = _get(k, cosd)
    if not D[k]:
        _fails += 1
        if _idx >= 1 and _fails == _idx + 1:   # 첫 2개 연속 실패 = FRED 도달 불가 → 조기중단(나머지 빈값→DB 백필+'변경 미확인')
            sys.stderr.write('fetch_macro: FRED 도달 불가(early-abort) — 나머지 %d개 skip, DB 백필 위임\n' % (len(_items)-_idx-1))
            for _k2, _ in _items[_idx+1:]: D[_k2] = []
            break

def yoy(lv):
    m = {d[:7]: x for d, x in lv}; out = []
    for d, x in lv:
        py = str(int(d[:4]) - 1) + d[4:7]
        if py in m and m[py]: out.append([d[:7], round((x / m[py] - 1) * 100, 2)])
    return out
def mom(lv):
    out = []
    for i in range(1, len(lv)):
        if lv[i-1][1]: out.append([lv[i][0][:7], round((lv[i][1] / lv[i-1][1] - 1) * 100, 2)])
    return out
def nfp_chg(lv):  # PAYEMS level(천명) → 월 신규(천명)
    return [[lv[i][0][:7], round(lv[i][1] - lv[i-1][1])] for i in range(1, len(lv))]
def last(lv): return lv[-1] if lv else [None, None]
def pct_changes(lv):  # 일별 → 1d/1w/1mo.. 변화율(%)
    if len(lv) < 2: return {}
    cur = lv[-1][1]; ld = dt.date.fromisoformat(lv[-1][0]); o = {'current': cur}
    def at(days):
        tgt = ld - dt.timedelta(days=days); c = [p for p in lv if dt.date.fromisoformat(p[0]) <= tgt]
        return (c[-1][1] if c else lv[0][1])
    o['1d_pct'] = round((cur/lv[-2][1]-1)*100, 2) if lv[-2][1] else None
    for k, dd in [('1w_pct',7),('1mo_pct',30),('3mo_pct',91),('6mo_pct',182),('1y_pct',365)]:
        b = at(dd); o[k] = round((cur/b-1)*100, 2) if b else None
    return o

INFL = [('CPI','CPIAUCSL','CPI (헤드라인)'),('Core CPI','CPILFESL','Core CPI (식품·에너지 제외)'),
        ('PCE','PCEPI','PCE'),('Core PCE','PCEPILFE','Core PCE'),('PPI','PPIFIS','PPI (최종수요)')]
series = {}; infl_lines = {}; infl_rows = []
for key, sid, nm in INFL:
    lv = D.get(sid, []); yv = yoy(lv); mv = mom(lv)
    infl_lines[key] = yv
    infl_rows.append({'name': nm, 'yoy': (yv[-1][1] if yv else None), 'mom': (mv[-1][1] if mv else None),
                      'asof': (yv[-1][0] if yv else None), 'release': None})
bei = D.get('T10YIE', [])
infl_rows.append({'name': '기대인플레이션 (10년 BEI)', 'yoy': (last(bei)[1] if bei else None), 'mom': None,
                  'asof': (last(bei)[0] if bei else None), 'release': '실시간'})
series['inflation'] = infl_lines
series['infl_exp'] = bei

dgs2 = D.get('DGS2', []); dgs10 = D.get('DGS10', [])
series['us2y_daily'] = dgs2; series['us10y_daily'] = dgs10
m2 = {d: v for d, v in dgs2}; curve = [[d, round(v - m2[d], 2)] for d, v in dgs10 if d in m2]
series['curve_10_2'] = curve; series['curve_labels'] = [p[0] for p in curve]
ff = D.get('FEDFUNDS', []); series['fed_funds_5y'] = [[d[:7], v] for d, v in ff]

unrate = D.get('UNRATE', []); payems = D.get('PAYEMS', []); retail = D.get('RSAFS', []); gdp = D.get('A191RL1Q225SBEA', [])
nfpc = nfp_chg(payems); retm = mom(retail)
series['employment'] = {'nfp': nfpc, 'unemp': [[d[:7], v] for d, v in unrate],
                        'retail': retm, 'gdp': [[d[:7], v] for d, v in gdp], 'ism_mfg': [], 'ism_svc': []}
# 초기 실업수당 청구건수(주간·계절조정 ICSA) — 만 건 단위로 시계열 저장(주간 발표=매주 목). 노동시장 둔화 조기신호.
icsa = D.get('ICSA', [])
series['employment']['jobless'] = [[d, round(v/10000.0, 2)] for d, v in icsa]
_jc = icsa[-1] if icsa else [None, None]
_jc_val = ('%.1f만 건' % (_jc[1]/10000.0)) if _jc[1] else None
try: _jc_rel = (dt.date.fromisoformat(_jc[0]) + dt.timedelta(days=5)).isoformat() if _jc[0] else None  # 주 종료(토)+5일=발표(목)
except Exception: _jc_rel = None
emp_rows = [
 {'name':'초기 실업수당 청구건수','value': _jc_val,'asof': (_jc[0] or None),'release': _jc_rel,'freq':'주간(매주 목)'},
 {'name':'NFP (비농업취업자 변화)','value': ('%d천명'%nfpc[-1][1] if nfpc else None),'asof': (nfpc[-1][0] if nfpc else None),'freq':'월간'},
 {'name':'실업률','value': (last(unrate)[1] if unrate else None),'asof': (last(unrate)[0][:7] if unrate else None),'freq':'월간'},
 {'name':'소매판매 (MoM)','value': (retm[-1][1] if retm else None),'asof': (retm[-1][0] if retm else None),'freq':'월간'},
 {'name':'ISM 제조업 PMI','value': None,'asof': None,'freq':'월간'},
 {'name':'ISM 서비스업 PMI','value': None,'asof': None,'freq':'월간'},
 {'name':'GDP 성장률 (연율)','value': (last(gdp)[1] if gdp else None),'asof': (last(gdp)[0][:7] if gdp else None),'freq':'분기'},
]

def spread(a, b):
    try: return round(a - b, 2)
    except Exception: return None
u2 = last(dgs2)[1]; u10 = last(dgs10)[1]; ffc = last(D.get('DFF', []))[1]
rates = {'us2y': dict(pct_changes(dgs2), trend='정책금리 기대 반영'),
         'us10y': dict(pct_changes(dgs10), trend='장기 기준금리'),
         'fed_funds': {'current': ffc, 'target_range': '3.50-3.75', 'decision': '동결', 'bias': '중립', 'asof': last(D.get('DFF',[]))[0]},
         'yield_curve': {'spread': spread(u10, u2)}}

macro = {'series': series, 'rates': rates, 'inflation': {'rows': infl_rows}, 'employment': {'rows': emp_rows}, 'sentiment': {}}
# no-clobber: FRED 다운(수집 거의 0)인데 기존 nmr_macro.json(에이전트 FMP 등)이 있으면 덮지 않는다(merge/DB가 백필).
_pts = sum(len(v) for v in series.get('inflation', {}).values()) + len(series.get('curve_10_2', []))
_mpath = os.path.join(W, 'nmr_macro.json')
if _pts == 0 and os.path.exists(_mpath):
    print('fetch_macro: FRED 무수집 → 기존 nmr_macro.json 보존(덮지 않음), DB/에이전트 위임'); sys.exit(0)
try:
    _ex = json.load(open(_mpath, encoding='utf-8')).get('macro', {})
    if _ex.get('sentiment'): macro['sentiment'] = _ex['sentiment']   # 선행EPS/PER(FactSet/FnGuide) 보존
    _ee = (_ex.get('series', {}) or {}).get('employment', {}) or {}
    for _ek in ('ism_mfg', 'ism_svc'):                                # ISM(FRED 부재) 기존 보존
        if not series['employment'].get(_ek) and _ee.get(_ek): series['employment'][_ek] = _ee[_ek]
except Exception: pass
json.dump({'macro': macro}, open(_mpath, 'w', encoding='utf-8'), ensure_ascii=False)
print('fetch_macro OK — infl', {k: len(v) for k, v in infl_lines.items()}, '| BEI', len(bei), '| curve', len(curve),
      '| fed_funds_5y', len(series['fed_funds_5y']), '| emp', {k: len(v) for k, v in series['employment'].items()})
print('  rows: 물가', sum(1 for r in infl_rows if r['yoy'] is not None), '/6 채움 · 고용', sum(1 for r in emp_rows if r['value'] is not None), '/7 채움 (ISM 2개는 FRED 부재→DB 백필)')
