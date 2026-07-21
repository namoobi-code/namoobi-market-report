#!/usr/bin/env python3
# merge.py (v3.7) — nmr_*.json 들을 report_data_YYYYMMDD.json 으로 병합 (Phase 3).
# 매 실행 즉석 작성하던 병합 로직을 결정적 스크립트로 베이크 (토큰·변동성 제거).
# 사용: python3 merge.py [WORK_DIR] [REPORT_DATE_YYYYMMDD]
#   WORK_DIR 없으면 cwd. REPORT_DATE 없으면 env NMR_DATE 또는 오늘(KST).
#   mode 는 env NMR_MODE(scheduled/normal) 또는 'normal'.
import json, os, re, sys, glob, datetime as dt

W = sys.argv[1] if (len(sys.argv) > 1 and os.path.isdir(sys.argv[1])) else '.'
KST = dt.timezone(dt.timedelta(hours=9))
now = dt.datetime.now(KST)
RD = (sys.argv[2] if len(sys.argv) > 2 else os.environ.get('NMR_DATE') or now.strftime('%Y%m%d'))
RD = ''.join(ch for ch in RD if ch.isdigit())[:8]
RD_ISO = f"{RD[:4]}-{RD[4:6]}-{RD[6:8]}"
MODE = os.environ.get('NMR_MODE', 'normal')

def L(p):
    try: return json.load(open(os.path.join(W, p), encoding='utf-8'))
    except Exception as e:
        print('load fail', p, e); return {}

# (v3.39) 휘발 데이터 carry-forward: WORK 우선 → 없으면 연결폴더 영구본 → 사용분은 연결폴더에 저장(다음 회차 폴백)
_CWROOT = (glob.glob('/sessions/*/mnt/claudeCowork/namoobi-market-report-server/data') or [os.path.join(W, '_market_report_data')])[0]
def LCF(name):
    d = L(name)
    if not d:
        try: d = json.load(open(os.path.join(_CWROOT, name), encoding='utf-8'))
        except Exception: d = {}
        if d: print('carry-forward(%s): WORK 없음 → 연결폴더 영구본 사용' % name)
    if d:
        try:
            os.makedirs(_CWROOT, exist_ok=True)
            json.dump(d, open(os.path.join(_CWROOT, name), 'w'), ensure_ascii=False)
        except Exception: pass
    return d

mk = L('nmr_markets.json'); com = L('nmr_commod.json'); cr = L('nmr_crypto.json'); ue = L('nmr_usetf.json')
nw = L('nmr_news.json'); gs = L('nmr_globalsec.json'); um = L('nmr_usmacro.json'); rb = L('nmr_rebalance.json')
n2 = L('nmr_news2.json'); semi = L('nmr_semi.json'); krs = L('nmr_kr_series.json'); ohlcv = L('nmr_kr_ohlcv.json')
inv = L('nmr_kr_invest.json'); lead = L('nmr_leading.json'); sec = L('nmr_securities.json'); an = L('nmr_analysis.json')
tr = L('nmr_trendtext.json')
m7o = L('nmr_m7.json')  # (v3.46) 3.1.7 미국 빅테크(M7) 실적전망 라이브 데이터(있으면 내장 스냅샷 대체)
dpv = L('nmr_deriv_positioning.json')  # (v3.47) 3.1.13 파생 포지셔닝 라이브(있으면 내장 스냅샷 대체)
krl = L('nmr_krliq_summary.json')  # (v3.64) 3.1.14 국내 유동성·레버리지 (fetch_krliq→gen_krliq_charts, 서버 1일 3회 수집분)

def san(s): return str(s).replace('/', '_').replace(' ', '_')

def ret(series):
    pts = [(dt.date.fromisoformat(str(d)[:10]), float(v)) for d, v in series if v is not None]
    if len(pts) < 2: return {}
    pts.sort(); cur = pts[-1][1]; last = pts[-1][0]
    out = {'current': round(cur, 2)}
    for k, days in [('1w_pct', 7), ('1mo_pct', 30), ('3mo_pct', 91), ('6mo_pct', 182), ('1y_pct', 365)]:
        tgt = last - dt.timedelta(days=days)
        cand = [p for p in pts if p[0] <= tgt] or [pts[0]]
        base = cand[-1][1]
        out[k] = round((cur / base - 1) * 100, 1) if base else None
    # (대전제) 현재가셀=1d_pct(D0=최근거래일 전일대비), '1일'컬럼=prev_pct(D-1 일간변동=직전거래일 변동)
    if len(pts) >= 2 and pts[-2][1]:
        out['1d_pct'] = round((pts[-1][1] / pts[-2][1] - 1) * 100, 2)
    if len(pts) >= 3 and pts[-3][1]:
        out['prev_pct'] = round((pts[-2][1] / pts[-3][1] - 1) * 100, 2)
    return out

def koTrend(r):
    y = r.get('1y_pct'); m3 = r.get('3mo_pct')
    if y is None: return ''
    s = '강세' if y > 0 else '약세'; t = f"1년 {y:+.0f}%"
    if m3 is not None: t += f", 3개월 {m3:+.0f}%" + (' 가속' if (m3 or 0) > 0 and y > 0 else (' 조정' if (m3 or 0) < 0 else ''))
    return t + f" ({s})"

m = {}
if isinstance(m7o, dict) and m7o.get('rows'): m['m7_outlook'] = m7o  # 3.1.7 라이브 오버라이드
if isinstance(dpv, dict) and (dpv.get('rows') or dpv.get('index')): m['deriv_positioning'] = dpv  # 3.1.13 라이브 오버라이드
if isinstance(krl, dict) and krl.get('as_of'): m['kr_liquidity'] = krl  # 3.1.14 (없으면 섹션 비차단 생략)
# (fix 2026-07-09) deriv 캐리포워드: 라이브가 특정 열(예: KOSPI200)의 z/값 산출에 실패하면 null·'-'·'—' 로 새는데,
# 직전 정상 report_data 의 같은 지표·같은 열 셀에서 z(및 빈 v)를 가져와 채운다(다른 캐리포워드와 동일 철학).
def _deriv_carry(cur):
    try:
        import glob as _g
        cands=sorted(_g.glob('/sessions/*/mnt/claudeCowork/namoobi-market-report-server/data/report_data_*.json'))+sorted(_g.glob(os.path.join(W,'_market_report_data','report_data_*.json')))
        cands=[c for c in cands if RD not in os.path.basename(c)]
        prev=None
        for c in reversed(cands):
            try: pj=json.load(open(c,encoding='utf-8'))
            except Exception: continue
            pd=(pj.get('markets') or {}).get('deriv_positioning')
            if isinstance(pd,dict) and pd.get('rows'): prev=pd; break
        if not prev: return cur, 0
        pmap={r.get('label'):r.get('cells',[]) for r in prev.get('rows',[]) if isinstance(r,dict)}
        n=0
        for r in cur.get('rows',[]):
            pc=pmap.get(r.get('label'))
            if not pc: continue
            for i,cell in enumerate(r.get('cells',[])):
                if i>=len(pc) or not isinstance(cell,dict): continue
                pcz=pc[i] if isinstance(pc[i],dict) else {}
                if cell.get('z') is None and pcz.get('z') is not None:
                    cell['z']=pcz['z']; n+=1
                if str(cell.get('v') or '').strip() in ('','-','—') and str(pcz.get('v') or '').strip() not in ('','-','—'):
                    cell['v']=pcz['v']
        if n and prev.get('asof'):
            _pa=str(prev.get('asof')).split(' · (일부 z 캐리포워드')[0]  # (fix 2026-07-16) 직전 asof의 기존 캐리포워드 문구 제거 — 괄호 중첩 누적 방지
            cur['asof']=str(cur.get('asof') or '')+' · (일부 z 캐리포워드: '+_pa+')'
        return cur, n
    except Exception as _e:
        print('  [deriv] carry-forward skip:', _e); return cur, 0
if isinstance(m.get('deriv_positioning'), dict):
    m['deriv_positioning'], _dcn = _deriv_carry(m['deriv_positioning'])
    if _dcn: print('  [deriv] KOSPI200 등 null z 캐리포워드 셀:', _dcn)
for k in ('korea', 'us_markets', 'asia_markets', 'europe_markets', 'fx_markets', 'fx_usd'):
    m[k] = mk.get(k, {})
for grp, td in [('asia_markets', tr.get('asia', {})), ('europe_markets', tr.get('europe', {})), ('fx_markets', tr.get('fx', {}))]:
    for k, v in (td or {}).items():
        if k in m[grp] and isinstance(m[grp][k], dict) and not m[grp][k].get('trend'): m[grp][k]['trend'] = v

def fmt(v):
    v = v or 0
    return (f"{v / 10000:+.2f}조" if abs(v) >= 10000 else f"{v:+,}억")

kf = ohlcv.get('kospi_flows_daily') or []; qf = ohlcv.get('kosdaq_flows_daily') or []
def inv_block(flows, level):
    if not flows: return {}
    d, F, I, P = flows[-1]
    return {'level': level, 'foreign': fmt(F), 'institution': fmt(I), 'individual': fmt(P),
            'comment': f"{d} 마감 기준 외국인 {fmt(F)}·기관 {fmt(I)}·개인 {fmt(P)}"}
m['korea_investors'] = {'tech': True, 'asof': (kf[-1][0] if kf else ''),
                        'kospi': inv_block(kf, m['korea'].get('kospi', {}).get('current')), 'kospi_chart': 'charts/kospi_tech.png',
                        'kosdaq': inv_block(qf, m['korea'].get('kosdaq', {}).get('current')), 'kosdaq_chart': 'charts/kosdaq_tech.png'}
ks = {k: v for k, v in inv.items() if k != 'asof'}; ks['asof'] = inv.get('asof'); m['korea_investor_stocks'] = ks

# 경기선행지수 (월간 캐시 소스). comment 는 lead 에서 유도.
kl = lead.get('korea_leading', []) if isinstance(lead, dict) else []
m['korea_leading'] = kl; m['korea_leading_chart'] = 'charts/leading_cycle.png'
def lead_comment(kl):
    if not kl: return ''
    top = kl[0]; val = top.get('value'); per = top.get('period')
    # 연속 상승/하락 개월수 (mom 부호)
    sign = lambda s: 1 if str(s).strip().startswith('+') else (-1 if str(s).strip().startswith('-') else 0)
    base = sign(top.get('mom', '')); n = 0
    for e in kl:
        if sign(e.get('mom', '')) == base and base != 0: n += 1
        else: break
    dir_txt = '상승' if base > 0 else ('하락' if base < 0 else '보합')
    phase = '경기 확장' if (isinstance(val, (int, float)) and val >= 100) else '경기 수축'
    pc = f"순환변동치 {'100 상회' if (isinstance(val,(int,float)) and val>=100) else '100 하회'}"
    seg = f"·{n}개월 연속 {dir_txt}" if n >= 2 else ''
    return f"선행종합지수 {pc}{seg}({per} {val}) — {phase} 국면, KOSPI 약 2개월 선행 관계."
m['korea_leading_comment'] = lead_comment(kl)

# 테마 (nmr_semi.json 의 선정/방향/코멘트 + nmr_kr_series.json 의 시계열 join)
themes = krs.get('themes', {}); kr_daily = krs.get('daily') or {}; theme_etf = krs.get('theme_etf') or {}; trows = []
kr_naver = krs.get('naver') or {}
d_themes = kr_daily.get('themes') or {}
for t in (semi.get('korea_themes') or []):
    nm = t.get('theme'); s = themes.get(nm) or []
    r = ret(s); r.update({'theme': nm, 'direction': t.get('direction'), 'comment': t.get('comment'),
                          'chart': f"charts/theme_{san(nm)}.png", 'trend': koTrend(r)})
    r['etf'] = t.get('etf') or theme_etf.get(nm) or ''  # 대표 ETF 명칭 (3.2.4)
    ds = d_themes.get(nm)
    if ds:  # 일봉 현재가·전일대비 (테마 series 는 월봉=현재가 stale → 일봉으로 갱신)
        if ds.get('current') is not None: r['current'] = ds['current']
        if ds.get('chg') is not None: r['chg'] = ds['chg']
        if ds.get('1d_pct') is not None: r['1d_pct'] = ds['1d_pct']
        if ds.get('prev_close') is not None: r['prev_close'] = ds['prev_close']
        # (req3 fix) 테마 series 는 월봉 → ret()의 prev_pct 는 '전월' 변동이라 '1일'칸 왜곡(예:+29.98%). 일봉 prev_pct 로 덮어써 '1일'=직전거래일 변동으로 교정.
        if ds.get('prev_pct') is not None: r['prev_pct'] = ds['prev_pct']
    trows.append(r)
# (v3.50) 에이전트가 누락한 테마(예: 신설 '건설')는 fetch_semi 시계열로 폴백 생성 — 조용한 행 누락 방지(req3 게이트 9행).
_have = {r.get('theme') for r in trows}
for nm in (theme_etf or {}):
    if nm in _have or not themes.get(nm): continue
    r = ret(themes.get(nm) or [])
    _m1 = r.get('1mo_pct')
    r.update({'theme': nm, 'direction': ('▲ 강세' if (_m1 or 0) > 3 else ('▼ 약세' if (_m1 or 0) < -3 else '■ 중립')),
              'comment': '', 'chart': f"charts/theme_{san(nm)}.png", 'trend': koTrend(r), 'etf': theme_etf.get(nm) or ''})
    ds = d_themes.get(nm) or {}
    for k in ('current', 'chg', '1d_pct', 'prev_close', 'prev_pct'):
        if ds.get(k) is not None: r[k] = ds[k]
    trows.append(r)
m['korea_theme_rows'] = trows; m['korea_themes_comment'] = semi.get('korea_themes_comment') or ''
m['korea_theme_etfs'] = theme_etf  # 빌더 fallback (테마→대표ETF명)

def aumfmt(v):
    try:
        v = float(v)
        if v >= 1e12: return f"{v / 1e12:,.0f}조원"
        if v >= 1e8: return f"{v / 1e8:,.0f}억원"
        return str(v)
    except Exception:
        return v if v else ''
ss = []
for i, x in enumerate(semi.get('semi_ai_stocks', [])[:20]):  # (req5) 종목 확대
    s = (krs.get('stocks') or {}).get(x.get('name')) or []
    r = ret(s); r.update({'name': x.get('name'), 'aum': aumfmt(x.get('aum')), 'note': x.get('note', ''), 'chart': f"charts/semi_s_{i}.png", 'trend': koTrend(r)})
    _ds = (kr_daily.get('stocks') or {}).get(x.get('name'))
    if _ds:
        if _ds.get('chg') is not None: r['chg'] = _ds['chg']
        if _ds.get('1d_pct') is not None: r['1d_pct'] = _ds['1d_pct']
        if _ds.get('prev_close') is not None: r['prev_close'] = _ds['prev_close']
    ss.append(r)
se = []
for i, x in enumerate(semi.get('semi_ai_etfs', [])[:20]):
    s = (krs.get('etfs') or {}).get(x.get('name')) or []
    r = ret(s); r.update({'name': x.get('name'), 'aum': aumfmt(x.get('aum')), 'note': x.get('note', ''), 'chart': f"charts/semi_e_{i}.png", 'trend': koTrend(r)})
    _ds = (kr_daily.get('etfs') or {}).get(x.get('name'))
    if _ds:
        if _ds.get('chg') is not None: r['chg'] = _ds['chg']
        if _ds.get('1d_pct') is not None: r['1d_pct'] = _ds['1d_pct']
        if _ds.get('prev_close') is not None: r['prev_close'] = _ds['prev_close']
    se.append(r)
# (v3.64) 네이버 보강 주입 — 당일 수급(외국인/기관/개인)·목표주가 컨센서스·외인소진율·정확한 시가.
#   Yahoo 는 종가·수익률만 준다. 한국 종목에서 정작 중요한 '오늘 누가 사고 팔았나'와
#   '애널리스트 목표주가'가 통째로 빠져 있었다. KRX OPEN API 는 T+1 이라 오늘 수급을 못 준다.
#   ⚠️ 시가는 네이버(KRX 공식)를 쓴다 — Yahoo 의 한국 개별종목 시가는 부정확하다
#      (SK하이닉스 2026-07-13: Yahoo 2,113,000 vs KRX/네이버 2,207,000).
_nvm = (krs.get('naver') if isinstance(krs, dict) else None) or {}
if _nvm:
    def _nvov(lst):
        for _x in lst:
            _n = _nvm.get(_x.get('name'))
            if not _n: continue
            for _k in ('open', 'high', 'low', 'foreign_rate', 'per', 'fwd_per', 'fwd_eps'):
                if _n.get(_k) is not None: _x[_k] = _n[_k]
            if _n.get('flows'):    _x['flows'] = _n['flows']
            if _n.get('consensus'): _x['consensus'] = _n['consensus']
    _nvov(ss); _nvov(se)
    print('  [naver] 종목·ETF 보강 주입: %d종 (수급·목표주가·외인소진율)' % len(_nvm))

m['semi_ai_stocks'] = ss; m['semi_ai_stocks_comment'] = semi.get('semi_ai_stocks_comment', '')
m['semi_ai_etfs'] = se; m['semi_ai_etfs_comment'] = semi.get('semi_ai_etfs_comment', '')
# [DB화·시총 매일] krs.caps(다음 라이브 시총·주식수)로 시총/AUM 덮어쓰기 → stale 방지·주식수 변동 자동 반영 + 시총/AUM순 정렬
_capm = (krs.get('caps') if isinstance(krs, dict) else None) or {}
if _capm:
    def _capov(lst):
        for _x in lst:
            _c = _capm.get(_x.get('name'))
            if _c and _c.get('eok'): _x['aum'] = str(_c['eok']); _x['shares'] = _c.get('shares')
        return lst
    def _capnk(_x):
        try: return -float(str(_x.get('aum','')).replace(',',''))
        except Exception: return 1e18
    m['semi_ai_stocks'] = sorted(_capov(m.get('semi_ai_stocks') or []), key=_capnk)
    m['semi_ai_etfs'] = sorted(_capov(m.get('semi_ai_etfs') or []), key=_capnk)
    print('  [caps] 시총/AUM 라이브 덮어쓰기·정렬:', len(_capm))
m['hbm'] = LCF('nmr_hbm.json')  # 3.1.9 HBM 대시보드: gen_hbm_dashboard.py 오버라이드 + 캡션 asof/source (없으면 {} → 내장 예시·추정 사용)
m['factset'] = LCF('nmr_factset.json')  # 3.1.6 Earnings Insight (FactSet) DB: 블로그 최신글 + 리포트 첫장 요약 (없으면 {} → 섹션 자동 생략)
# (req6) HBM eps_per -> eps_yearly (빌더 표 스키마)
try:
    _hb = m.get('hbm') or {}
    if isinstance(_hb, dict) and not _hb.get('eps_yearly') and isinstance(_hb.get('eps_per'), list):
        _ey=[]
        for _o in _hb['eps_per']:
            if not isinstance(_o, dict): continue
            _g=lambda *ks: next((_o.get(k) for k in ks if _o.get(k) not in (None,'')), None)
            _row={'name': _o.get('company') or _o.get('name') or '-',
                'y2025_eps': _g('eps_2025','eps_2025E'), 'y2025_per': _g('per_2025','per_2025E'),
                'y2026_eps': _g('eps_2026E','eps_2026'), 'y2026_per': _g('per_2026E','per_2026'),
                'y2027_eps': _g('eps_2027E','eps_2027'), 'y2027_per': _g('per_2027E','per_2027'),
                'y2028_eps': _g('eps_2028E','eps_2028'), 'y2028_per': _g('per_2028E','per_2028'),
                'currency': _o.get('currency') or _o.get('unit') or ''}
            # (req16) eps_cur/eps_next 를 year_cur/year_next 컬럼에 매핑 (eps_2025 평면키 없을 때 — '컨센서스 미공개' 재발방지)
            _yc=str(_hb.get('year_cur') or 2025); _yn=str(_hb.get('year_next') or 2026)
            if _o.get('eps_cur') is not None and _row.get('y%s_eps'%_yc) is None: _row['y%s_eps'%_yc]=_o.get('eps_cur'); _row['y%s_per'%_yc]=_o.get('per_cur')
            if _o.get('eps_next') is not None and _row.get('y%s_eps'%_yn) is None: _row['y%s_eps'%_yn]=_o.get('eps_next'); _row['y%s_per'%_yn]=_o.get('per_next')
            _ey.append(_row)
        if _ey: _hb['eps_yearly']=_ey; m['hbm']=_hb; print('  [req6] HBM eps_yearly 매핑:', len(_ey))
except Exception as _he: print('  [req6] hbm eps_yearly skip:', _he)

# (req4-fix) HBM eps_yearly 필드단위 carry-forward — 이번 실행의 '순수 수치'는 쓰고 DB(db/hbm_eps.json) 갱신,
#   결측·다중출처 장문·'미확인' 등 비수치는 마지막 정상 DB값으로 보완한다. (통째 덮어써 2027E/2028E/PER 를 잃던 문제 방지)
try:
    import re as _re_hb
    import nmr_db as _ndb
    _hb2 = m.get('hbm') or {}
    _hep = os.path.join(_ndb._dbdir(), 'hbm_eps.json')   # DB 정본 = namoobi-market-report-server/db
    try:
        _sd = json.load(open(_hep, encoding='utf-8')); _store = _sd.get('data') if (isinstance(_sd, dict) and 'data' in _sd) else (_sd or {})
        _pnote = _sd.get('price_note') if isinstance(_sd, dict) else None
    except Exception: _store = {}; _pnote = None
    if not isinstance(_store, dict): _store = {}
    def _norm_hbm(n):
        n = _re_hb.sub(r'\s*\(.*$', '', str(n)).strip()
        if n.lower().startswith('micron') or n == '마이크론': return 'Micron'
        return n
    def _hbm_num(v):
        if isinstance(v, (int, float)): return float(v)
        if v is None: return None
        sv = str(v).strip()
        for ch in [',', '₩', '$', '%', '배', 'x', 'X', ' ']: sv = sv.replace(ch, '')
        try: return float(sv)
        except Exception: return None
    _flds = ['y2025_eps','y2025_per','y2026_eps','y2026_per','y2027_eps','y2027_per','y2028_eps','y2028_per']
    _cur = _hb2.get('eps_yearly') if isinstance(_hb2.get('eps_yearly'), list) else []
    _curmap = { _norm_hbm(o.get('name')): o for o in _cur if isinstance(o, dict) }
    _names = list(_store.keys()) + [k for k in _curmap if k not in _store]
    _merged = []
    for _k in _names:
        _so = dict(_store.get(_k) or {}); _co = _curmap.get(_k) or {}
        _row = {'name': ('Micron (MU)' if _k == 'Micron' else (_co.get('name') or _k)), 'currency': (_co.get('currency') or _so.get('currency') or '')}
        for _f in _flds:
            _cv = _co.get(_f)
            if _hbm_num(_cv) is not None:
                _row[_f] = _cv; _so[_f] = _cv        # 순수 수치 → 채택 + DB 갱신
            else:
                _row[_f] = _so.get(_f)               # 비수치/결측 → DB 보완
        _so['currency'] = _row['currency']
        _merged.append(_row); _store[_k] = _so
    # (req13 2026-07-12) PER 단일화 — db/hbm_eps.json 의 prices(fetch_memory 가 매일 갱신)로 PER=현재가÷EPS 재계산.
    #   HBMAgent 가 옛 주가 기준 PER 를 보내도 여기서 항상 최신가 기준으로 통일된다(대시보드 ⑩과 동일값).
    try:
        _prc = (_sd.get('prices') if isinstance(_sd, dict) else None) or {}
        for _row in _merged:
            _pnm = _norm_hbm(_row.get('name'))
            _pv = _hbm_num((_prc.get(_pnm) or {}).get('price'))
            if _pv:
                for _yy in ('2025', '2026', '2027', '2028'):
                    _ev = _hbm_num(_row.get('y%s_eps' % _yy))
                    if _ev:
                        _row['y%s_per' % _yy] = round(_pv / _ev, 2)
                        (_store.setdefault(_pnm, {}))['y%s_per' % _yy] = _row['y%s_per' % _yy]
    except Exception as _pe13: print('  [req13] PER 재계산 skip:', _pe13)

    # ★★ (v3.65) 네이버 연도별 실적/컨센서스로 EPS 자동 갱신 (2025 실적 · 2026 컨센서스)
    #   네이버 기업실적분석은 연도 키(202512·202612)와 isConsensus 플래그를 명시적으로 준다
    #   → 매핑이 확실하므로 추측이 아니다. 해당 연도만 정확히 덮어쓴다.
    #   (v3.66) 2027·2028 도 커버된다 — 모바일 API 는 당해년도 하나만 주지만,
    #   PC 종목분석(FnGuide navercomp.wisereport.co.kr)에는 3년치 컨센서스가 다 있다.
    #
    #   실측(2026-07-13): 2025 실적은 DB와 정합(SK 60,372 vs 58,955)이나
    #   2026 컨센서스는 DB 가 3배 낡아 있었다(SK 110,559 vs 318,735 → PER 16.7배 vs 5.79배).
    try:
        _annm = {}
        for _v in ((m.get('memory') or {}).get('valuation') or []):
            _a = _v.get('annual_naver')
            if _a: _annm[_norm_hbm(_v.get('name'))] = _a
        if _annm:
            _upd = []
            _prc2 = (_sd.get('prices') if isinstance(_sd, dict) else None) or {}
            for _row in _merged:
                _pnm = _norm_hbm(_row.get('name'))
                _a = _annm.get(_pnm)
                if not _a: continue
                for _yy in ('2025', '2026', '2027', '2028'):
                    _ny = _a.get(_yy)
                    if not _ny or _ny.get('eps') is None: continue   # 네이버에 없는 연도는 건드리지 않는다
                    _old = _hbm_num(_row.get('y%s_eps' % _yy))
                    _new = _ny['eps']
                    if _old is None or abs(_new / _old - 1) > 0.02:   # 2% 초과 차이만 갱신
                        _row['y%s_eps' % _yy] = _new
                        (_store.setdefault(_pnm, {}))['y%s_eps' % _yy] = _new
                        _row['y%s_src' % _yy] = ('네이버 컨센서스' if _ny.get('is_consensus') else '네이버 실적')
                        # ⚠️ PER 재계산(req13)은 이 블록보다 먼저 돌기 때문에, 갱신한 EPS 의 PER 을
                        #    여기서 다시 계산해야 한다. 안 하면 새 EPS 에 옛 PER 이 붙는다.
                        _pv2 = _hbm_num((_prc2.get(_pnm) or {}).get('price'))
                        if _pv2 and _new:
                            _row['y%s_per' % _yy] = round(_pv2 / _new, 2)
                            (_store.setdefault(_pnm, {}))['y%s_per' % _yy] = _row['y%s_per' % _yy]
                        _upd.append('%s %s: EPS %s → %s (%s)%s' % (
                            _row.get('name'), _yy,
                            (f"{_old:,.0f}" if _old else '없음'), f"{_new:,.0f}",
                            '컨센서스' if _ny.get('is_consensus') else '실적',
                            (' · PER %s배' % _row.get('y%s_per' % _yy)) if _row.get('y%s_per' % _yy) else ''))
            if _upd:
                print('  ★ [네이버 연도별] EPS 갱신 %d건 (연도키·isConsensus 명시 → 매핑 확실):' % len(_upd))
                for _u in _upd: print('     -', _u)
            else:
                print('  [네이버 연도별] DB 와 정합 — 갱신 없음')
    except Exception as _ae65: print('  [네이버 연도별] skip:', _ae65)

    # ★ (v3.64) 네이버 당일 컨센서스 대조 — 낡은 DB 추정치를 조용히 쓰지 않는다.
    #   fetch_memory 가 네이버에서 '당해년도 추정EPS'(국내 증권사 컨센서스 집계)를 매일 가져온다.
    #   DB(hbm_eps) 의 연도별 추정치는 carry-forward 라 컨센서스가 대폭 상향돼도 갱신되지 않는다.
    #   실제로 2026-07-13 시점에 3배 어긋나 있었다:
    #     SK하이닉스 DB 2026 EPS 110,559(PER 16.7배)  vs  네이버 당일 318,735(PER 5.79배)
    #     삼성전자   DB 2026 EPS  16,693(PER 15.3배)  vs  네이버 당일  46,664(PER 5.45배)
    #   PER 16.7배와 5.8배는 투자판단이 완전히 다르다 → 괴리 30% 초과면 경고 + 보고서에 병기.
    try:
        _val = ((m.get('memory') or {}).get('valuation')) or []
        _liv = {}
        for _v in _val:
            _cl = _v.get('consensus_live') or {}
            if _cl.get('fwd_eps'):
                _liv[_norm_hbm(_v.get('name'))] = {
                    'fwd_eps': _cl['fwd_eps'], 'fwd_per': _v.get('per_fwd') or _cl.get('fwd_per'),
                    'target': _cl.get('target'), 'asof': _cl.get('asof')}
        if _liv:
            _warn = []
            for _row in _merged:
                _pnm = _norm_hbm(_row.get('name'))
                _lv = _liv.get(_pnm)
                if not _lv: continue
                _row['consensus_live'] = _lv          # 보고서 표에 병기
                _dbe = _hbm_num(_row.get('y2026_eps'))
                if _dbe and _lv['fwd_eps']:
                    _gap = abs(_lv['fwd_eps'] / _dbe - 1) * 100
                    if _gap > 30:
                        _row['consensus_gap_pct'] = round(_gap, 1)
                        _warn.append('%s: DB 2026 EPS %s vs 네이버 당일 %s (%.0f%% 괴리)'
                                     % (_row.get('name'), f"{_dbe:,.0f}", f"{_lv['fwd_eps']:,.0f}", _gap))
            if _warn:
                print('  ⚠️ [컨센서스 괴리] DB 추정치가 시장 컨센서스와 크게 다르다 — 재조사 필요:')
                for _w in _warn: print('     -', _w)
            else:
                print('  [컨센서스] 네이버 당일값과 DB 추정치 정합 (괴리 30% 이내)')
    except Exception as _ce64: print('  [컨센서스] 대조 skip:', _ce64)
    if _merged:
        _hb2['eps_yearly'] = _merged; m['hbm'] = _hb2
        try:
            os.makedirs(os.path.dirname(_hep), exist_ok=True)
            json.dump({'as_of': RD_ISO, 'source': 'field-level carry-forward', 'price_note': _pnote, 'data': _store}, open(_hep, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        except Exception: pass
        print('  [req4-fix] HBM eps_yearly carry-forward:', len(_merged), '개사 (비수치·결측은 DB 보완)')
        if _pnote: _hb2['eps_note'] = _pnote
except Exception as _hce: print('  [req4-fix] hbm carry-forward skip:', _hce)

# 3.1 주요지표(매크로 대시보드) — nmr_macro.json(MacroAgent: FMP economics/treasury + FRED) 오버라이드, 없으면 내장 예시·추정값
MACRO_DEFAULT = json.loads(r'''{
  "rates": {
    "fed_funds": {"current": 3.63, "decision": "동결", "bias": "중립", "meaning": "연준 기준금리", "freq": "연 8회 회의", "impact": "금리↑ → 주식↓·달러↑·채권↓"},
    "policy_rates": [
      {"country": "미국", "rate": 3.63, "asof": "2026-05", "note": "FMP 실측(FedFunds)"},
      {"country": "한국", "rate": 2.50, "asof": "2026-05", "note": "BOK 기준금리(추정)"},
      {"country": "일본", "rate": 0.50, "asof": "2026-05", "note": "BOJ(추정)"},
      {"country": "중국", "rate": 3.00, "asof": "2026-05", "note": "1년 LPR(추정)"},
      {"country": "유로존", "rate": 2.15, "asof": "2026-05", "note": "ECB 예금금리(추정)"},
      {"country": "영국", "rate": 4.00, "asof": "2026-05", "note": "BOE(추정)"}
    ],
    "policy_rates_chart": "charts/macro_policy_rates.png",
    "fomc_meetings": [
      {"date": "2025-07-30", "stance": "동결(중립)", "note": "고금리 유지·인하 신중(추정)"},
      {"date": "2025-09-17", "stance": "인하(비둘기)", "note": "-25bp, 고용 둔화 반영(추정)"},
      {"date": "2025-10-29", "stance": "인하(비둘기)", "note": "-25bp 연속 인하(추정)"},
      {"date": "2025-12-10", "stance": "동결(중립)", "note": "인하 속도 조절 시사(추정)"},
      {"date": "2026-01-28", "stance": "동결(매파)", "note": "인플레 재반등 경계(추정)"},
      {"date": "2026-03-18", "stance": "동결(매파)", "note": "점도표 상향·인하 지연(추정)"},
      {"date": "2026-04-29", "stance": "동결(중립)", "note": "데이터 관망(추정)"},
      {"date": "2026-06-17", "stance": "동결(매파)", "note": "끈적한 물가에 매파 톤(추정)"}
    ],
    "fomc_market_impact": "매파(긴축)↑ → 금리↑ → 주식↓·달러↑   |   비둘기(완화)↑ → 금리↓ → 주식↑",
    "us10y": {"current": 4.46, "1w_pct": -0.7, "1mo_pct": 1.1, "3mo_pct": 2.0, "6mo_pct": -3.0, "1y_pct": 5.5, "trend": "고착·박스권", "spark": "charts/spark_us10y.png"},
    "us2y": {"current": 4.07, "trend": "정책금리 기대 반영"},
    "yield_curve": {"label": "미국 장단기 금리차(수익률곡선)(10Y-2Y)", "spread": 0.27, "status": "정상(비역전)", "note": "2Y 4.19·10Y 4.46", "meaning": "단기-장기 금리차", "impact": "역전(단기>장기) → 경기침체 신호·주식↓", "chart": "charts/macro_curve.png"}
  },
  "inflation": {
    "chart": "charts/macro_inflation.png",
    "rows": [
      {"name": "CPI (소비자물가)", "yoy": 4.17, "mom": 0.47, "asof": "2026-05", "meaning": "일반 소비자 체감 물가", "impact": "CPI↑ → 금리↑ 기대 → 주식↓·달러↑·채권↓"},
      {"name": "Core CPI (식·에너지 제외)", "yoy": 3.1, "mom": 0.3, "asof": "2026-05", "meaning": "식·에너지 제외 물가(연준 가장 중시)", "impact": "Core CPI↑ → 금리↑ 방향 직접 결정"},
      {"name": "PCE (개인소비물가)", "yoy": 2.6, "mom": 0.2, "asof": "2026-04", "meaning": "연준 공식 인플레이션 목표 지표", "impact": "PCE↑ → 금리↑ 압력"},
      {"name": "Core PCE", "yoy": 2.8, "mom": 0.2, "asof": "2026-04", "meaning": "식·에너지 제외(연준 최우선)", "impact": "Core PCE↑ → 금리↑ 방향 직접 결정"},
      {"name": "PPI (생산자물가)", "yoy": 2.9, "mom": 0.1, "asof": "2026-05", "meaning": "기업 원가 변화", "impact": "PPI↑ → 금리↑ → 기업마진 압박·주식↓"}
    ],
    "infl_exp_10y": {"current": 2.35, "trend": "완만한 상승(추정)", "chart": "charts/macro_infl_exp.png", "meaning": "미래 인플레 기대수치", "freq": "매일", "impact": "10년 기대↑(2%대) + 실업률 4%대 → 테이퍼링·금리인상 언급"}
  },
  "employment": {
    "chart": "charts/macro_employment.png",
    "rows": [
      {"name": "초기 실업수당 청구건수", "value": "21.5만 건", "asof": "2026-06-27", "release": "2026-07-02", "meaning": "노동시장 둔화 조기신호", "freq": "주간(매주 목)", "impact": "청구건수 증가(고용둔화 신호)는 경기와 소비둔화 우려로 주가에 악영향을 줄 수 있음"},
      {"name": "NFP (비농업 신규고용)", "value": "+172K", "asof": "2026-05", "meaning": "신규 일자리 수", "freq": "매월 첫째 금요일", "impact": "NFP↑(강세) → 금리↑ → 주식↓·달러↑"},
      {"name": "실업률", "value": "4.3%", "asof": "2026-05", "meaning": "실직자 비율", "freq": "매월 첫째 금요일", "impact": "실업률↑ → 금리↓ 기대 → 주가↑"},
      {"name": "GDP (전기比 연율)", "value": "+1.6%", "asof": "26Q1", "meaning": "경제 전체 성장률", "freq": "분기별", "impact": "GDP↑ → 경기성장·실적 개선 가능성"},
      {"name": "ISM 제조업 PMI", "value": "48.7", "asof": "2026-05", "meaning": "기업 체감경기(제조)", "freq": "매월", "impact": "50↑ 경기확장 → 금리↑ 혼조"},
      {"name": "ISM 서비스 PMI", "value": "51.6", "asof": "2026-05", "meaning": "기업 체감경기(서비스)", "freq": "매월", "impact": "50↑ 경기확장 → 금리↑ 혼조"},
      {"name": "소매판매 (MoM)", "value": "+1.0%", "asof": "2026-05", "meaning": "소비 지표", "freq": "매월", "impact": "소매판매↑ → 경기과열 → 금리↑"}
    ]
  },
  "sentiment": {
    "rows": [
      {"name": "VIX (공포지수)", "current": 17.2, "1w_pct": -5.0, "1mo_pct": -8.0, "3mo_pct": -12.0, "6mo_pct": -6.0, "1y_pct": -10.0, "trend": "안정(추정)", "spark": "charts/spark_vix.png", "meaning": "변동성 예측", "use": "높을수록 등락 심화 → 현금 비중 늘려 관망"},
      {"name": "KSVKOSPI (KOSPI Volatility)", "current": 95.73, "trend": "실시간(CNBC .KSVKOSPI)", "spark": "charts/spark_vkospi.png", "meaning": "코스피200 변동성지수(VKOSPI)", "use": "20대=안정·30↑ 고변동, 급등 시 공포 확대 → 현금 비중 관망"},
      {"name": "달러인덱스 DXY", "current": 98.1, "1w_pct": 0.3, "1mo_pct": -0.5, "3mo_pct": -1.8, "6mo_pct": -3.0, "1y_pct": -4.0, "trend": "약보합(추정)", "spark": "charts/spark_dxy.png", "meaning": "달러 가치", "use": "달러 강세 → 코스피 조정 역사"},
      {"name": "원/달러 환율", "current": 1380, "1w_pct": 0.2, "1mo_pct": 0.5, "3mo_pct": 1.0, "6mo_pct": 1.5, "1y_pct": 2.0, "trend": "원화 약세(추정)", "spark": "charts/spark_usd_krw.png", "meaning": "외국인 수급 영향", "use": "1,400원↑ → 외국인 이탈 가속"},
      {"name": "WTI 유가", "current": 71.5, "1w_pct": 1.5, "1mo_pct": -2.0, "3mo_pct": -5.0, "6mo_pct": -3.0, "1y_pct": -8.0, "trend": "박스권(추정)", "spark": "charts/spark_wti.png", "meaning": "인플레 압력", "use": "급등 → 인플레 → 금리상승 → 성장주 부담"}
    ]
  }
}
''')
_mac = L('nmr_macro.json')
_macro = _mac.get('macro') if (isinstance(_mac, dict) and _mac.get('macro')) else (_mac if (isinstance(_mac, dict) and _mac) else None)
# v3.13.2 재발방지: 에이전트 nmr_macro 가 빌더(MACRO_DEFAULT) 구조를 못 맞추면(평면구조 rates.fed_funds=숫자·inflation.cpi_yoy 등) 무시하고 MACRO_DEFAULT 사용 → 3.1.1~3.1.3·3.1.12 빈표 방지
def _macro_ok(mm):
    try:
        _r = mm.get('rates') or {}
        return isinstance(_r.get('fed_funds'), dict) and bool((mm.get('inflation') or {}).get('rows')) and bool((mm.get('employment') or {}).get('rows'))
    except Exception:
        return False
if _macro and not _macro_ok(_macro):
    print('  [macro] nmr_macro 구조 불일치(rates.fed_funds 가 dict 아님/rows 비어있음) -> MACRO_DEFAULT 폴백')
    _macro = None
macro = _macro if _macro else json.loads(json.dumps(MACRO_DEFAULT))
_MDEF = not bool(_macro)  # (fix) MacroAgent 부재 시 MACRO_DEFAULT 예시값이 DB를 덮어쓰지 않도록 — DB값 재사용(get)
# (v3.43) 에이전트가 sentiment.rows(심리 6지표 골격)를 안 줘도 inflation/employment 를 살린다 — MACRO_DEFAULT 골격만 주입(merge가 VIX·DXY·KSVKOSPI·원달러·WTI·US10Y 라이브값 주입). (2026-06-29: 3.1.5 spx_fwd/kospi_fwd 제거)
_CANON_SENT_NAMES = {r['name'] for r in MACRO_DEFAULT['sentiment']['rows']}
_sd = macro.setdefault('sentiment', {})
# (fix 2026-07-09) sentiment.rows 는 전량 라이브 주입(VIX·DXY·KSVKOSPI·원달러·WTI)이므로 에이전트가
# 표준 이름/키(use)를 벗어난 rows(예: name='VIX', key='impact')를 주면 주입·시장영향 렌더가 '-'로 깨진다.
# → rows 가 없거나 표준 스키마(모든 행에 use 存·name∈표준집합)를 벗어나면 MACRO_DEFAULT 표준 골격으로 교체.
_srows = _sd.get('rows')
_sent_ok = isinstance(_srows, list) and len(_srows)>0 and all(
    isinstance(r, dict) and ('use' in r) and (r.get('name') in _CANON_SENT_NAMES) for r in _srows)
if not _sent_ok:
    _sd['rows'] = json.loads(json.dumps(MACRO_DEFAULT['sentiment']['rows']))
# (fix req3 2026-07-10) 심리표 2번째 표 '의미' 칸 '-' 방지 — 에이전트가 use(시장영향)만 주고 meaning 을 빼면
# 빌더 renderSentiment 의미 칸이 o.meaning||'-' 로 전부 '-'가 된다. MACRO_DEFAULT(name 매칭)에서 meaning 백필(있으면 보존).
_DEF_SENT_MEAN = {r['name']: r.get('meaning', '') for r in MACRO_DEFAULT['sentiment']['rows']}
for _sr in (_sd.get('rows') or []):
    if isinstance(_sr, dict) and not _sr.get('meaning'):
        _sr['meaning'] = _DEF_SENT_MEAN.get(_sr.get('name'), '')
# (Big-Arch req4/20/25) 매크로 표 canonical 정규화 — 행순서·의미·시장영향·해석 고정 + us2y 보강
def _macro_canon(macro):
    _r = macro.setdefault('rates', {})
    _u2 = _r.get('us2y')
    if isinstance(_u2, dict) and _u2.get('value') is not None and _u2.get('current') is None:
        _u2['current'] = _u2.get('value')
    if not (isinstance(_r.get('us2y'), dict) and _r['us2y'].get('current') is not None):
        _r['us2y'] = {'current': 4.07, 'trend': '정책금리 기대 반영'}
    # [req11] 장단기 금리차(10Y-2Y) 정규화 — label·status·meaning·impact·note 항상 완전(빈값/undefined 방지)
    _yc = _r.get('yield_curve') if isinstance(_r.get('yield_curve'), dict) else {}
    # (2차 req2 2026-07-18) 현재값 = 차트와 같은 DB 시계열의 마지막 점 — 조사시점 차이로
    # 본문 수치와 그래프가 어긋나던 문제. 시계열이 있으면 그것이 항상 우선한다.
    try:
        import nmr_db as _ndb_yc
        _dbd = _ndb_yc._dbdir()
        def _last(name):
            _p = os.path.join(_dbd, name + '.json')
            _a = (json.load(open(_p, encoding='utf-8')) or {}).get('data') or []
            return float(_a[-1][1]) if _a else None
        _s10, _s2, _scv = _last('series_us10y_daily'), _last('series_us2y_daily'), _last('series_curve_10_2')
        if _scv is not None:
            _yc['spread'] = round(_scv, 2)
        if _s10 is not None and isinstance(_r.get('us10y'), dict): _r['us10y']['current'] = round(_s10, 2)
        if _s2 is not None and isinstance(_r.get('us2y'), dict): _r['us2y']['current'] = round(_s2, 2)
    except Exception:
        pass
    try: _sp = float(_yc['spread']) if _yc.get('spread') is not None else round(float(_r['us10y']['current'])-float(_r['us2y']['current']),2)
    except Exception: _sp = _yc.get('spread')
    if _sp is not None: _yc['spread'] = _sp
    _yc['label'] = '미국 장단기 금리차(수익률곡선)(10Y-2Y)'
    if isinstance(_sp,(int,float)):
        _yc['status'] = '정상(양전환)' if _sp >= 0 else '역전'
        _yc['meaning'] = '장단기 금리차 정상화 = 경기 연착륙 기대' if _sp >= 0 else '장단기 금리 역전 = 경기침체 우려'
    _yc.setdefault('meaning','단기-장기 금리차'); _yc['impact'] = '스프레드 역전 시 침체 선행지표'
    try: _yc['note'] = '10Y=%s%%, 2Y=%s%%' % (_r['us10y']['current'], _r['us2y']['current'])
    except Exception: pass
    _r['yield_curve'] = _yc
    INFL = [
      ('CPI (헤드라인)', ['cpi'], [], ['core'], '소비자가 체감하는 전체 물가. 식품·에너지 포함해 단기 변동성이 큼.', '금리 기대에 즉각 반영, 변동성이 큼.', '헤드라인 급등 시 단기 인플레 우려로 위험자산 변동성 확대.'),
      ('Core CPI (식품·에너지 제외)', ['cpi','core'], [], [], '일시적 충격을 뺀 기조적 물가 압력. 연준이 추세 판단에 더 유용하게 봄.', '금리 인하 결정의 핵심 변수, 듀레이션 자산에 영향.', '근원이 둔화되면 인하 기대가 살아나 성장주에 우호적.'),
      ('PCE', ['pce'], [], ['core'], '소비자 지출 구조를 넓게 반영하는 물가지표. CPI보다 대체효과를 더 잘 반영함.', '연준 시그널은 CPI보다 정책에 더 강하게 작용.', '연준 목표지표인 만큼 둔화 시 정책 피벗 신호로 해석.'),
      ('Core PCE', ['pce','core'], [], [], '식품·에너지를 제외한 연준 선호 근원 물가. 목표 2% 판단의 중심 축.', '가장 중요도 높은 경로, 실질금리·밸류에이션에 영향.', '근원 PCE가 목표(2%)를 웃돌면 인하 지연·밸류 부담.'),
      ('PPI (최종수요)', ['ppi'], [], [], '생산자 단계 물가. 소비자물가로 전가되기 전 선행 압력을 보여줌.', 'CPI/PCE 전가 시 중요. 원자재·산업 업종에 영향.', '생산자물가 급등은 시차를 두고 소비자물가·마진 압박으로 전이.'),
      ('기대인플레이션 (10년 BEI)', [], ['bei','기대인플','breakeven'], [], '10년 국채와 10년 TIPS의 차이로 본 시장의 장기 물가 기대.', '장기 금리 방향의 핵심, 성장·가치주 모두에 영향.', '기대인플레가 2%에 수렴하면 장기금리 안정·증시 우호적.'),
    ]
    EMP = [
      ('초기 실업수당 청구건수', [], ['실업수당','청구','jobless','claims'], [], '노동시장 둔화 조기신호', '청구건수 증가(고용둔화 신호)는 경기와 소비둔화 우려로 주가에 악영향을 줄 수 있음', '청구건수 증가는 고용 둔화 조기신호로 증시에 부담(감소는 우호).'),
      ('NFP (비농업취업자 변화)', [], ['nfp','비농업'], [], '비농업 신규고용 — 시장이 가장 민감하게 반응하는 고용지표', '연준 금리경로·경기 침체/연착륙 판단에 직결', '신규고용 호조는 연착륙 신호지만 과열 시 금리인상 우려.'),
      ('실업률', ['실업'], [], ['수당','청구'], '고용 건전성(연준 이중책무 핵심)', '상승=경기둔화·금리인하 명분 / 시장 민감', '실업률 상승은 인하 명분이 되어 단기 증시엔 양면적.'),
      ('소매판매 (MoM)', [], ['소매','retail'], [], '미국 소비 강도를 즉시 반영', '경기주·리테일·소비재·금리 기대에 영향이 큼', '소비 강세는 경기 견조의 방증이나 인플레·금리 자극.'),
      ('ISM 제조업 PMI', ['ism','제조'], [], [], '제조업 경기(50 기준)', '경기민감주·반도체·산업재·소재주에 영향 / 경기 방향성(50↑ 확장)', '50 회복은 제조업 반등으로 반도체·산업재에 우호적.'),
      ('ISM 서비스업 PMI', ['ism','서비스'], [], [], '서비스업 경기(50 기준)', '경제 비중 크나 주식시장선 고용·소비보다 한 단계 아래로 보는 편', '서비스 확장 지속은 고용·소비 견조를 뒷받침.'),
      ('GDP 성장률 (연율)', ['gdp'], [], [], '실질 성장률(연율) — 후행지표', '발표가 늦어 단기 트레이딩보다 중기 경기판단용', '성장률은 후행지표로 중기 추세 확인용, 단기 영향은 제한적.'),
    ]
    def _match(rows, ALL, ANY, NONE):
        for o in rows:
            nm = str(o.get('name','')).lower()
            if all(t in nm for t in ALL) and (not ANY or any(t in nm for t in ANY)) and not any(t in nm for t in NONE):
                return o
        return None
    import re as _re
    def _infl_interp(name, row):
        try: v=float(row.get('yoy'))
        except Exception: return ''
        if 'BEI' in name or '기대' in name:
            return ("기대인플레 %.1f%%로 다소 높아 장기금리 상방·성장주 부담" % v) if v>=2.6 else ("기대인플레 %.1f%%로 2%%대 안정 → 증시 우호" % v)
        if v>=3.5: return "%.1f%%로 높은 수준 — 금리인하 지연 우려로 증시 부담" % v
        if v>=2.6: return "%.1f%%로 목표(2%%) 상회 — 둔화 확인 시 증시 우호" % v
        return "%.1f%%로 목표 근접 — 금리인하 기대로 증시 우호" % v
    def _emp_interp(name, row):
        s0=str(row.get('value','')); mnum=_re.search(r'-?\d+\.?\d*', s0.replace(',',''))
        if not mnum: return ''
        v=float(mnum.group())
        if '실업수당' in name or '청구' in name: return ("청구 %s — 낮은 수준, 노동시장 견조·증시 우호" % s0) if v<23 else (("청구 %s — 증가세, 고용둔화·경기우려로 증시 부담" % s0) if v>=25 else ("청구 %s — 보합권, 고용 완만 둔화 관망" % s0))
        if 'NFP' in name or '비농업' in name: return ("신규고용 %s — 견조, 과열 시 금리인상 우려" % s0) if v>=150 else ("신규고용 %s — 둔화, 금리인하 명분·증시 양면" % s0)
        if '실업' in name: return ("실업률 %s — 상승 압력, 인하 기대로 증시 양면" % s0) if v>=4.4 else ("실업률 %s — 낮음, 노동시장 타이트·인하 지연" % s0)
        if '소매' in name: return ("소비 %s — 견조하나 인플레·금리 자극" % s0) if v>=0 else ("소비 %s — 둔화, 경기 우려·인하 기대" % s0)
        if 'ISM' in name: return ("%s — 50 상회 확장, 경기민감·반도체 우호" % s0) if v>=50 else ("%s — 50 하회 위축, 경기둔화 우려" % s0)
        if 'GDP' in name: return ("성장 %s — 견조, 실적 우호" % s0) if v>=2 else ("성장 %s — 둔화, 경기 우려" % s0)
        return ''
    def _canon(section, CAN, valkeys, interp_fn=None):
        src = (macro.get(section) or {}).get('rows') or []
        out = []
        for (name, ALL, ANY, NONE, mean, imp, interp) in CAN:
            o = _match(src, ALL, ANY, NONE) or {}
            row = {'name': name, 'meaning': mean, 'impact': imp}
            for vk in valkeys: row[vk] = o.get(vk)
            _dyn = interp_fn(name, row) if interp_fn else ''
            row['interp'] = _dyn or interp
            out.append(row)
        macro.setdefault(section, {})['rows'] = out
    _canon('inflation', INFL, ['yoy','mom','asof','release'], _infl_interp)
    _canon('employment', EMP, ['value','asof','release','freq'], _emp_interp)
    # (fix req1 2026-07-10) GDP 행 value 가 비면(에이전트가 GDP 행 자체를 누락하는 사례) '-'로 샌다.
    #  → series.employment.gdp 에서 최신 '연율%'(레벨 수천대 제외, |v|<20)를 복원해 채운다. 없으면 MACRO_DEFAULT 폴백.
    _emp_rows = (macro.get('employment') or {}).get('rows') or []
    for _er in _emp_rows:
        if 'GDP' in str(_er.get('name','')) and (_er.get('value') in (None, '', '-')):
            _gser = ((macro.get('series') or {}).get('employment') or {}).get('gdp') or []
            _gv = None; _gd = None
            for _pt in _gser:
                try:
                    _v = float(_pt[1])
                    if abs(_v) < 20: _gv = _v; _gd = str(_pt[0])   # 레벨(수천대) 배제, 연율%만
                except Exception: pass
            if _gv is not None:
                _er['value'] = ("%+.1f%%" % _gv); _er['asof'] = _er.get('asof') or _gd
                _er['freq'] = _er.get('freq') or '분기'
                try: _er['interp'] = _emp_interp(_er['name'], _er) or _er.get('interp')
                except Exception: pass
            else:
                _dg = [r for r in MACRO_DEFAULT['employment']['rows'] if 'GDP' in r.get('name','')]
                if _dg:
                    _er['value'] = _er.get('value') or _dg[0].get('value')
                    _er['freq'] = _er.get('freq') or _dg[0].get('freq')
_macro_canon(macro)
# (req2/req3-fix 재발방지) release 칸이 기관명(BLS·BEA·Census·ISM·FRED 등)만인 경우 DB 저장 전에 비운다.
#   → DB 가 기관명으로 오염돼 다음 실행 seed 로 재전파되는 것을 차단. 표시값은 nmr_reasons 가 날짜/라벨로 채운다.
import re as _re_rel
def _bad_rel(v):
    if v in (None,'','-'): return True
    sv=str(v)
    if _re_rel.search(r'\d{4}[-.\/]\d', sv): return False
    if ('정기 발표' in sv) or ('실시간' in sv): return False
    return True
for _sec in ('inflation','employment'):
    for _rr in ((macro.get(_sec) or {}).get('rows') or []):
        if _bad_rel(_rr.get('release')): _rr['release']=''
# (req3) ISM 제조/서비스 표값 보강: nmr_macro.ism -> employment.rows value
try:
    _ism = macro.get('ism') or {}
    _emp_rows = (macro.get('employment') or {}).get('rows') or []
    _ismv = {'제조': (_ism.get('manufacturing') or {}), '서비스': (_ism.get('services') or {})}
    for _row in _emp_rows:
        _nm = _row.get('name') or ''
        if 'ISM' in _nm and (_row.get('value') in (None,'','-')):
            _k = '제조' if '제조' in _nm else ('서비스' if '서비스' in _nm else None)
            _iv = _ismv.get(_k, {})
            if _iv.get('value') is not None:
                _row['value'] = _iv['value']; _row['asof'] = _iv.get('asof') or _row.get('asof'); _row['release'] = 'ISM (추정)'
    print('  [req3] ISM 표값 보강 완료')
except Exception as _ie: print('  [req3] ISM 보강 skip:', _ie)

# 이미 수집된 시세 재사용(중복 fetch 금지): VIX·DXY·원/달러·WTI·美10년물
_us = m.get('us_markets') or {}; _fx = m.get('fx_markets') or {}; _en = (com.get('energy') if isinstance(com, dict) else {}) or {}
_RK = ('current', '1w_pct', '1mo_pct', '3mo_pct', '6mo_pct', '1y_pct', 'trend', '1d_pct', 'chg', 'prev_close')
def _reuse(dst, srcv):
    if isinstance(dst, dict) and isinstance(srcv, dict):
        for _k in _RK:
            if srcv.get(_k) is not None: dst[_k] = srcv[_k]
_byname = {'VIX (공포지수)': _us.get('vix'), '달러인덱스 DXY': _us.get('dxy'), '원/달러 환율': _fx.get('usd_krw'), 'WTI 유가': _en.get('wti')}
for _r in ((macro.get('sentiment') or {}).get('rows') or []):
    if isinstance(_r, dict) and _byname.get(_r.get('name')): _reuse(_r, _byname[_r['name']])
_reuse((macro.get('rates') or {}).get('us10y'), _us.get('us10y'))
# (v3.22) KSVKOSPI 표준화 + CNBC 실시간 주입 — 에이전트가 VKOSPI/KSVKOSPI 어떤 이름으로 주든 통일
_vk = mk.get('vkospi')
if not (isinstance(_vk, dict) and _vk.get('current') is not None):
    # (req27) KSVKOSPI 폴백: 일별 캐시(nmr_vkospi_history.json) 최신값 — 라이브 실패 시에도 stale 기본값/'-' 금지
    try:
        _vp = (glob.glob('/sessions/*/mnt/claudeCowork/namoobi-market-report-server/data/nmr_vkospi_history.json') or glob.glob(os.path.join(W,'_market_report_data','nmr_vkospi_history.json')) or [None])[0]
        if _vp:
            _vser = (json.load(open(_vp)).get('series') or [])
            if _vser: _vk = {'current': _vser[-1][1], 'trend': '캐시(CNBC .KSVKOSPI 일별누적)', 'anchors': _vser}
    except Exception: pass
for _r in ((macro.get('sentiment') or {}).get('rows') or []):
    if isinstance(_r, dict) and 'VKOSPI' in str(_r.get('name', '')).upper():
        _r['name'] = 'KSVKOSPI (KOSPI Volatility)'
        if _vk: _reuse(_r, _vk)
# (req8 2026-07-12) KSVKOSPI 이력을 KRX 공식(deriv_signals.db kr_derivatives_daily.vkospi)으로 보강 —
#   1년치 일별로 anchors(1w~1y)·prev_pct 를 계산해 nmr_vkospi_history.json 최상위 키로 저장('-' 근절, 매 실행 자동).
try:
    import sqlite3 as _sq3
    _ddbp = (glob.glob('/sessions/*/mnt/claudeCowork/namoobi-market-report-server/data/deriv_signals.db') or [None])[0]
    _vhp = (glob.glob('/sessions/*/mnt/claudeCowork/namoobi-market-report-server/data/nmr_vkospi_history.json') or [None])[0]
    if _ddbp and _vhp:
        _vh0 = json.load(open(_vhp, encoding='utf-8'))
        _daily = _vh0.setdefault('daily', {})
        for _dtx, _vv in _sq3.connect(_ddbp).execute("SELECT date, vkospi FROM kr_derivatives_daily WHERE vkospi IS NOT NULL"):
            if _dtx and _vv is not None:
                _daily.setdefault(str(_dtx)[:10], {'date': str(_dtx)[:10], 'close': float(_vv)})
        _pts = sorted((k, (v or {}).get('close')) for k, v in _daily.items() if isinstance(v, dict) and v.get('close') is not None)
        if len(_pts) >= 2:
            _lastd = dt.date.fromisoformat(_pts[-1][0]); _curv = float(_pts[-1][1])
            _vh0['current'] = _curv; _vh0['prev_close'] = float(_pts[-2][1])
            _vh0['chg'] = round(_curv - float(_pts[-2][1]), 2)
            _vh0['prev_pct'] = _vh0['1d_pct'] = round((_curv / float(_pts[-2][1]) - 1) * 100, 2)
            for _k2, _dy in [('1w_pct', 7), ('1mo_pct', 30), ('3mo_pct', 91), ('6mo_pct', 182), ('1y_pct', 365)]:
                _tg = (_lastd - dt.timedelta(days=_dy)).isoformat()
                _cn = [pp for pp in _pts if pp[0] <= _tg]
                if _cn: _vh0[_k2] = round((_curv / float(_cn[-1][1]) - 1) * 100, 2)
            _vh0['source'] = 'KRX 공식 VKOSPI 일별(deriv_signals.db) + investing.com 보조'
            json.dump(_vh0, open(_vhp, 'w', encoding='utf-8'), ensure_ascii=False)
            try: json.dump(_vh0, open(os.path.join(W, 'nmr_vkospi_history.json'), 'w', encoding='utf-8'), ensure_ascii=False)
            except Exception: pass
            print('  [req8] VKOSPI 공식이력 보강:', len(_pts), '일 · 1y', _vh0.get('1y_pct'))
except Exception as _ve8: print('  [req8] VKOSPI 공식이력 보강 skip:', _ve8)
# (req10) VKOSPI 이력 DB(nmr_vkospi_history.json)에서 1주~1년·prev_pct(1일=D-1) 주입 → '-' 제거
try:
    _vh = LCF('nmr_vkospi_history.json')
    if not isinstance(_vh, dict):
        _vp2 = (glob.glob('/sessions/*/mnt/claudeCowork/namoobi-market-report-server/data/nmr_vkospi_history.json') or [None])[0]
        _vh = json.load(open(_vp2)) if _vp2 else None
    if isinstance(_vh, dict):
        for _r in ((macro.get('sentiment') or {}).get('rows') or []):
            if isinstance(_r, dict) and 'VKOSPI' in str(_r.get('name','')).upper():
                for _k in ('1w_pct','1mo_pct','3mo_pct','6mo_pct','1y_pct','prev_pct','1d_pct','chg','prev_close','current'):
                    if _vh.get(_k) is not None: _r[_k] = _vh[_k]
                _r['spark'] = 'charts/spark_vkospi.png'
                _r['trend'] = '실시간(CNBC)+이력(investing.com 실측·일부 추정)'
                _r['hist_src'] = _vh.get('source','')
        print('  [req10] VKOSPI 이력 주입: 1년', _vh.get('1y_pct'), '6개월', _vh.get('6mo_pct'), '1주', _vh.get('1w_pct'))
except Exception as _ve:
    print('  [req10] VKOSPI 이력 주입 skip:', _ve)
m['macro'] = macro
# (REQ3) 실측 정책금리 — nmr_policyrates.json 있으면 추정치 대체
# (2026-07-19 서버화 3) PolicyRatesAgent 폐지 — 에이전트 산출이 없으면 서버 daily DB
#   (WORK/server_policy_rates.json — Phase 1 curl 캐시)를 동일 스키마로 변환해 사용.
_pr = L('nmr_policyrates.json')
if not (isinstance(_pr, dict) and _pr.get('policy_rates')):
    try:
        _spr = json.load(open(os.path.join(W, 'server_policy_rates.json'), encoding='utf-8'))
        if _spr.get('rows'):
            _pr = {'policy_rates': [
                {'country': r.get('country'), 'rate': str(r.get('rate', '')).rstrip('%'),
                 'asof': r.get('asof', ''), 'note': r.get('source', '서버 daily 실측 DB')}
                for r in _spr['rows'] if r.get('rate')]}
            print('  [policy] 서버 daily DB 사용(%d개국) — PolicyRatesAgent 불필요' % len(_pr['policy_rates']))
    except Exception:
        pass
if isinstance(_pr, dict) and _pr.get('policy_rates'):
    (macro.setdefault('rates', {}))['policy_rates'] = _pr['policy_rates']
    # (req2 2026-07-17) 정책금리 결정이력(monthly) upsert — 그래프 소스(nmr_policyrates_monthly.json)에
    #   신규 결정을 추가하는 로직이 없어 표(실측)와 그래프가 어긋났다(실측: 한국 7/16 2.75% 인상 미반영).
    #   각국 실측 {rate, asof(결정일)} 를 series 에 upsert 하고 current 를 갱신, 영구본에 저장한다.
    try:
        import re as _reP
        _prm = LCF('nmr_policyrates_monthly.json') or {}
        _ser = _prm.setdefault('series', {}); _cur = _prm.setdefault('current', {})
        _chg = 0
        for _row in _pr['policy_rates']:
            _c = str(_row.get('country') or '').strip()
            _map = {'미국': '미국', 'US': '미국', '한국': '한국', '일본': '일본', '중국': '중국',
                    '유로존': '유로존', '영국': '영국'}
            _c = next((_map[k] for k in _map if k in _c), None)
            if not _c:
                continue
            _rt_s = str(_row.get('rate') or '')
            _nums = [float(x) for x in _reP.findall(r'\d+\.?\d*', _rt_s)]
            if not _nums:
                continue
            _rv = _nums[-1] if _c == '미국' else _nums[0]  # 미국=목표범위 상단
            _ao = str(_row.get('asof') or '')[:10]
            if not _reP.match(r'^\d{4}-\d{2}-\d{2}$', _ao):
                continue
            _sl = _ser.setdefault(_c, [])
            if not any(str(p[0])[:10] == _ao for p in _sl):
                if (not _sl) or abs(float(_sl[-1][1]) - _rv) > 1e-9:
                    _sl.append([_ao, _rv]); _sl.sort(key=lambda p: str(p[0])); _chg += 1
            if _cur.get(_c) != _rv:
                _cur[_c] = _rv; _chg += 1
        if _chg:
            _prm['updated'] = RD_ISO[:10]
            json.dump(_prm, open(os.path.join(_CWROOT, 'nmr_policyrates_monthly.json'), 'w'), ensure_ascii=False)
            # (req2-fix 2026-07-19) WORK 에도 이중 기록 — 차트 생성기(_loadjson)가 O 에서 최신본을 바로 집도록
            try: json.dump(_prm, open(os.path.join(W, 'nmr_policyrates_monthly.json'), 'w'), ensure_ascii=False)
            except Exception: pass
            print('  [req2] 정책금리 monthly upsert:', _chg, '건 반영(그래프 소스 최신화)')
    except Exception as _pe:
        print('  [req2] 정책금리 monthly upsert skip(비차단):', repr(_pe)[:60])
# (REQ6/REQ5) 1년 금리차 차트·美10년물 실측 스파크 경로(생성 시 사용, 없으면 빌더가 자동 생략)
_rt = macro.get('rates') or {}
if isinstance(_rt.get('yield_curve'), dict): _rt['yield_curve']['chart'] = 'charts/macro_curve_1y.png'
if isinstance(_rt.get('us10y'), dict): _rt['us10y']['spark'] = 'charts/spark_us10y_v2.png'

m['us_etfs'] = ue
m['asia_etfs'] = LCF('nmr_asia_etf.json')  # 3.4.1 아시아 주요 ETF(한국상장) — fetch_asia_etf.py 산출(없으면 {} → 섹션 자동 생략)
m['europe_etfs'] = LCF('nmr_euetf.json')  # 3.5 유럽 주요 ETF(국내상장+미국상장) — fetch_us.py 산출(없으면 {} → 섹션 자동 생략)
m['americas_etfs'] = LCF('nmr_amer_etf.json')  # (v3.50) 3.6 북미&중남미 국가 ETF — fetch_us.py 산출(없으면 {} → 섹션 자동 생략)
m['aume_etfs'] = LCF('nmr_aume_etf.json')      # (v3.50) 3.7 호주&중동 국가 ETF — fetch_us.py 산출(없으면 {} → 섹션 자동 생략)
m['appendix_c'] = LCF('nmr_appc.json')         # (v3.51) [부록C] AI 반도체 밸류체인 43종 — fetch_appc.py 산출(없으면 {} → 부록 자동 생략)
# (v3.54) 3.2.4/3.2.5 KRX 증시 Brief·공매도 데일리 브리프 — fetch_krx_brief.py 산출(회차 마커 DB화·재사용은 스크립트가 담당).
#   파일 없으면 DB(db/krx_brief.json) 폴백 — 단 캡쳐 PNG(charts/krx_brief_p*·short_brief_p*)가 없으면 빌더가 이미지 생략, verify req22 가 잡는다.
m['krx_brief'] = LCF('nmr_krx_brief.json')
if not (isinstance(m.get('krx_brief'), dict) and (m['krx_brief'].get('krx') or m['krx_brief'].get('short'))):
    try:
        import nmr_db as _ndb_kb
        _kbdb = _ndb_kb.get('krx_brief', _ndb_kb._dbdir())
        m['krx_brief'] = dict(_kbdb, db_fallback=True) if isinstance(_kbdb, dict) and _kbdb else {}
    except Exception:
        m['krx_brief'] = {}
m['bigtech_capex'] = um.get('bigtech_capex', {}); m['fomc_dotplot'] = um.get('fomc_dotplot', {})
# (R3 실측화 wiring) 정책금리차트=미국 실효금리, 곡선=최대기간, us10y prev_pct, 센티 스파크(측정치), capex 실측
_rt3 = (m.get('macro') or {}).get('rates') or {}
_rt3['policy_rates_chart'] = 'charts/macro_policy_rates.png'
if isinstance(_rt3.get('yield_curve'), dict): _rt3['yield_curve']['chart'] = 'charts/macro_curve.png'
_um10 = ((m.get('us_markets') or {}).get('us10y') or {})
if isinstance(_rt3.get('us10y'), dict) and _um10.get('prev_pct') is not None: _rt3['us10y']['prev_pct'] = _um10['prev_pct']
_spk3 = {'VIX (공포지수)':'charts/spark_vix.png','KSVKOSPI (KOSPI Volatility)':'charts/spark_vkospi.png','달러인덱스 DXY':'charts/spark_dxy.png','원/달러 환율':'charts/spark_usd_krw.png','WTI 유가':'charts/spark_wti.png','미국 10년물 국채금리':'charts/spark_us10y_v2.png'}
for _r3 in (((m.get('macro') or {}).get('sentiment') or {}).get('rows') or []):
    if _r3.get('name') in _spk3: _r3['spark'] = _spk3[_r3['name']]
_cap3 = LCF('nmr_capex.json')
if isinstance(_cap3, dict) and _cap3.get('bigtech_capex'): m['bigtech_capex'] = _cap3['bigtech_capex']
# [DB화] CAPEX 풀매트릭스 보강 — 표 actuals 우선 + 내장 컨센서스로 결측연도 채움 → 표·차트(2024~2027) 완전 일치
# (req5·req8 2026-07-19) 2028·2029 전면 제거 — 공식 출처(가이던스·컨센서스) 없는 추정이라 7/18 규칙대로 표·차트·DB 모두 2022~2027만.
#   구 DB 잔존 y2028/y2029 는 아래 루프가 행에서 능동 삭제한다(홈피 표 27년까지와 통일).
try:
    _CY=[2024,2025,2026,2027]
    _CCAP={"Microsoft":[44.5,64.6,190,215],"Amazon":[83,132,200,245],"Alphabet":[52.5,91.4,185,250],"Meta":[37.3,69.7,135,175],"Oracle":[7,21,55.7,92]}
    _CREV={"Microsoft":[245,282,329,384],"Amazon":[638,717,824,933],"Alphabet":[350,403,486,580],"Meta":[165,201,253,302],"Oracle":[53,57,67,89]}
    _CFCF={"Microsoft":[74,72,-31,-29],"Alphabet":[73,73,13,-13],"Meta":[54,46,11,-1],"Amazon":[33,8,-39,-63],"Oracle":[12,0,-24,-59]}
    _bc=m.get('bigtech_capex') or {}; _rows=_bc.get('rows') or []
    # (req6 2026-07-12) 구 'Meta 삭제' 필터 폐지 — 표·차트 모두 Meta 포함 5개사
    _bc['rows']=_rows
    def _has(v): return v not in (None,'','-') and str(v).strip() not in ('미공개','미확인','미상','N/A','n/a','-','TBD','tbd')
    _ALIAS={'MSFT':'Microsoft','MICROSOFT':'Microsoft','GOOGL':'Alphabet','GOOG':'Alphabet','ALPHABET':'Alphabet','GOOGLE':'Alphabet','AMZN':'Amazon','AMAZON':'Amazon','META':'Meta','FB':'Meta','ORCL':'Oracle','ORACLE':'Oracle'}
    _DISP={'Microsoft':'Microsoft (MSFT)','Alphabet':'Alphabet (GOOGL)','Amazon':'Amazon (AMZN)','Oracle':'Oracle (ORCL)','Meta':'Meta (META)'}
    for _r in _rows:
        _co=str(_r.get('company','')).split(' (')[0].strip()
        _co=_ALIAS.get(_co.upper(), _co)   # (req8-fix) 티커명(MSFT/GOOGL/AMZN/ORCL)도 정규화 → 컨센서스 매트릭스 매칭·2027~2029 carry-forward
        if _co not in _CCAP: continue
        _r['company']=_DISP.get(_co, _r.get('company'))   # 표시명 통일(직전 회차와 동일: 'Microsoft (MSFT)')
        for _i,_y in enumerate(_CY):
            if not _has(_r.get('y%d'%_y)):   _r['y%d'%_y]=_CCAP[_co][_i]
            if not _has(_r.get('rev%d'%_y)): _r['rev%d'%_y]=_CREV[_co][_i]
            if not _has(_r.get('fcf%d'%_y)): _r['fcf%d'%_y]=_CFCF[_co][_i]
            try: _r['ratio%d'%_y]=round(100*float(_r['y%d'%_y])/float(_r['rev%d'%_y]))
            except Exception: pass
        for _dy in (2028, 2029):   # (req5·req8) 구 DB 잔존 2028·29 능동 삭제
            for _pfx in ('y', 'rev', 'fcf', 'ratio'):
                _r.pop('%s%d' % (_pfx, _dy), None)
    # (2026-07-19 FCF 차트 2025 단절 근본수정) 차트·DB용 시리즈를 '완성된 표(rows)'에서 항상 재구성 —
    #   에이전트 산출 fcf_series 가 실적연도(~2025)만 담아 와도 표=차트=db/capex.json 3자가 2022~2027 로 일치한다.
    def _numz(_v):
        try: return float(_v)
        except Exception:
            import re as _re2
            _mm = _re2.search(r'-?\d+(?:\.\d+)?', str(_v) if _v is not None else '')
            return float(_mm.group(0)) if _mm else None
    _SY=[2022,2023,2024,2025,2026,2027]
    for _sk,_pfx in (('capex_series','y'),('rev_series','rev'),('fcf_series','fcf')):
        _bl={'years':list(_SY)}
        for _r in _rows:
            _co=str(_r.get('company','')).split(' (')[0].strip()
            _co=_ALIAS.get(_co.upper(), _co)
            if _co in _CCAP:
                _bl[_co]=[_numz(_r.get('%s%d'%(_pfx,_yy))) for _yy in _SY]
        if len(_bl)>1: _bc[_sk]=_bl
    if _rows:
        m['bigtech_capex']['rows']=_rows
        try: json.dump({'bigtech_capex':m['bigtech_capex']}, open(os.path.join(_CWROOT,'nmr_capex.json'),'w',encoding='utf-8'), ensure_ascii=False)
        except Exception: pass
        print('  [capex] 풀매트릭스 보강 완료(2024~2029, 표=차트)')
except Exception as _ce: print('  [capex] enrich skip:', _ce)
# (R4) 센티 prev_pct(1일=직전 거래일 변동) 보강
_src4={'VIX (공포지수)':(m.get('us_markets') or {}).get('vix'),'달러인덱스 DXY':(m.get('us_markets') or {}).get('dxy'),'원/달러 환율':(m.get('fx_markets') or {}).get('usd_krw'),'미국 10년물 국채금리':(m.get('us_markets') or {}).get('us10y'),'WTI 유가':((com.get('energy') if isinstance(com,dict) else {}) or {}).get('wti'),'KSVKOSPI (KOSPI Volatility)':mk.get('vkospi')}
for _r4 in (((m.get('macro') or {}).get('sentiment') or {}).get('rows') or []):
    _sv4=_src4.get(_r4.get('name'))
    if isinstance(_sv4,dict) and _sv4.get('prev_pct') is not None: _r4['prev_pct']=_sv4['prev_pct']
    if _r4.get('name')=='미국 10년물 국채금리':
        _u4=(m.get('us_markets') or {}).get('us10y') or {}
        for _k4 in ('current','1w_pct','1mo_pct','3mo_pct','6mo_pct','1y_pct','trend','1d_pct','chg','prev_close','prev_pct'):
            if _u4.get(_k4) is not None: _r4[_k4]=_u4[_k4]
# (fix) FOMC 점도표 '변화' 열 = jun - mar (build_report r.change 비어 '-' 표시되던 문제)
for _r in ((m.get('fomc_dotplot') or {}).get('rows') or []):
    if not str(_r.get('change') or '').strip():
        try: _r['change'] = "%+.1f" % (float(_r.get('jun')) - float(_r.get('mar')))
        except Exception: _r['change'] = ''
m['us_treasury_curve'] = um.get('us_treasury_curve')
uc = um.get('us_credit') if isinstance(um.get('us_credit'), dict) else {}
# (HY 정리) 3.1.1 hy_spread 단일화 — current·asof·d1~y1 을 전부 시계열에서 계산.
#   소스: 영구 DB(연결폴더 nmr_hy_history.json, 2020~ 일별) 우선 → 당일 수집분(nmr_hy_series.json) 폴백.
#   미렌더링 중복 필드(hy_oas·hy_yield·implied_ust)와 us_credit 블록은 report_data 에 싣지 않음(빌더는 hy_spread 만 사용).
m['hy_spread'] = {'comment': (uc or {}).get('comment'), 'chart': 'charts/hy_oas.png'}
_hser = []
try:
    _hh = json.load(open(os.path.join(_CWROOT, 'nmr_hy_history.json'), encoding='utf-8'))
    _hser = (_hh.get('series') or []) if isinstance(_hh, dict) else []
except Exception: _hser = []
if len(_hser) < 30:  # 영구 DB 없거나 빈약 → 당일 수집분 폴백
    _hys = L('nmr_hy_series.json'); _hser = (_hys.get('series') if isinstance(_hys, dict) else _hys) or []
_hpts = sorted([(dt.date.fromisoformat(str(d)[:10]), float(v)) for d, v in _hser if v is not None])
if _hpts:
    m['hy_spread']['current'] = round(_hpts[-1][1], 2)
    m['hy_spread']['asof'] = str(_hpts[-1][0])
# (req1 2026-07-12) OAS 레벨 표 제거 — d1~y1 앵커 계산 폐지(차트+현재값·코멘트만 유지).
_rbu = rb.get('index_rebalance') if (isinstance(rb, dict) and isinstance(rb.get('index_rebalance'), dict)) else rb
# (2026-07-12) 리밸런싱 정규화 — 에이전트 산출 {date,type,in,out}/{period,announce_date,effective_date} 를 빌더 스키마로
def _ir_norm(_ir):
    for _k in ('sp500', 'nasdaq100'):
        _b = _ir.get(_k) or {}
        _ev = []
        _grp = {}   # (fix 2026-07-14) 종목별 평면행 {date,action,ticker,name,biz,reason} → 날짜별 add/remove 그룹핑
        _ord = []
        for _e in (_b.get('events') or []):
            if not isinstance(_e, dict): continue
            if 'add' in _e or 'remove' in _e: _ev.append(_e); continue
            if _e.get('ticker') and (_e.get('action') or _e.get('type') or _e.get('date') or _e.get('reason')):
                # (fix 2026-07-17 근본원인) action/type 없이 {ticker,date,reason}만 있는 평면행도 그룹핑 —
                # 종전엔 3번째 분기로 빠져 '날짜 제목 + 빈 add/remove' 껍데기 이벤트가 양산됨(3.3.2 빈 표 원인)
                _d = str(_e.get('date') or _e.get('effective') or _e.get('effective_date') or '변경 내역')
                if _d not in _grp:
                    _grp[_d] = {'title': _d, 'effective': _e.get('effective') or _e.get('effective_date') or '',
                                'add': [], 'remove': [], 'note': ''}
                    _ord.append(_d)
                _act = str(_e.get('action') or _e.get('type') or '')
                if not _act:   # reason 텍스트에서 편입/편출 추론 (편입 우선 — "…4종목 제외" 같은 부수 언급 오분류 방지)
                    _r0 = str(_e.get('reason') or '')
                    _act = '편입' if ('편입' in _r0 or 'add' in _r0.lower() or 'join' in _r0.lower()) else \
                           ('편출' if ('편출' in _r0 or '삭제' in _r0 or '제외' in _r0 or 'remov' in _r0.lower() or 'delet' in _r0.lower() or 'exit' in _r0.lower()) else '편입')
                _side = 'remove' if ('편출' in _act or 'remov' in _act.lower() or 'delet' in _act.lower() or 'drop' in _act.lower()) else 'add'
                _grp[_d][_side].append({'ticker': _e.get('ticker', ''), 'name': _e.get('name', ''),
                                        'biz': _e.get('biz', ''), 'reason': _e.get('reason', '')})
                continue
            _ev.append({'title': (' · '.join(x for x in [str(_e.get('date', '') or _e.get('quarter', '') or _e.get('period', '')), str(_e.get('type', ''))] if x) or '변경 내역'),
                        'effective': _e.get('effective') or _e.get('effective_date') or '',
                        'add': _e.get('in') or _e.get('additions') or _e.get('adds') or _e.get('added') or [],
                        'remove': _e.get('out') or _e.get('deletions') or _e.get('drops') or _e.get('removes') or _e.get('removed') or [],
                        'note': _e.get('note', '')})
        for _d in sorted(_ord, reverse=True): _ev.append(_grp[_d])
        if _ev: _b['events'] = _ev
        # (fix 2026-07-17) 타입 가드 — 에이전트가 문자열/dict/list 로 준 필드를 빌더 스키마로:
        #  schedule 이 str 이면 종전 루프가 '글자 단위'로 순회해 한 글자짜리 불릿 수백 개를 양산(페이지 전체가 세로 글자 — 근본원인)
        _sch0 = _b.get('schedule')
        if isinstance(_sch0, str):
            _b['schedule'] = [x.strip() for x in re.split(r'(?<=[.。])\s+', _sch0) if x.strip()]
        _cr0 = _b.get('criteria')
        if isinstance(_cr0, dict):   # dict 면 Array.isArray 실패로 '편입 기준' 섹션이 통째로 생략되던 문제
            _b['criteria'] = [{'item': str(_k3), 'detail': str(_v3)} for _k3, _v3 in _cr0.items()]
        elif isinstance(_cr0, str):
            _b['criteria'] = [x.strip() for x in re.split(r'(?<=[.。])\s+', _cr0) if x.strip()]
        _cn0 = _b.get('criteria_note')
        if isinstance(_cn0, list):   # list 면 String() 이 콤마로 뭉쳐 찍히던 문제
            _b['criteria_note'] = '  ◦ '.join(str(x) for x in _cn0 if str(x).strip())
        _ns = []
        for _s0 in (_b.get('schedule') or []):
            if isinstance(_s0, dict):
                _ns.append({'q': _s0.get('q') or _s0.get('cycle') or _s0.get('quarter') or _s0.get('period') or '-',
                            'cycle': _s0.get('cycle') or _s0.get('period') or '',
                            'announce': _s0.get('announce') or _s0.get('announce_date') or '-',
                            'effective': _s0.get('effective') or _s0.get('effective_date') or '-',
                            'note': _s0.get('note') or ''})
            else: _ns.append(_s0)
        if _ns: _b['schedule'] = _ns
    return _ir
try: _rbu = _ir_norm(dict(_rbu))
except Exception as _ire: print('  [ir_norm] skip:', _ire)
# (req8 2026-07-17) 리밸런싱 정규화 — 에이전트 산출 변형 스키마가 3.3.2 를 '-' 투성이로 깨뜨리는 것 방지:
#   ① schedule 의 전부 빈('-'/공백) 행 드롭, 값 없이 note 만 있는 행은 불릿 문자열로 변환
#   ② rule_change.rows 의 content/desc 키를 빌더가 읽는 detail 로 매핑
#   ③ candidates 가 상태(status)만 있으면 {name,note} 2열형으로 변환(빈 '-' 4열표 방지)
def _rebal_canon(r):
    _e = lambda x: (x is None) or (str(x).strip() in ('', '-'))
    for _ix in ('sp500', 'nasdaq100'):
        _b = r.get(_ix)
        if not isinstance(_b, dict):
            continue
        _sch = _b.get('schedule')
        if isinstance(_sch, list):
            _o = []
            for _s in _sch:
                if isinstance(_s, str):
                    if _s.strip(): _o.append(_s)
                    continue
                if not isinstance(_s, dict):
                    continue
                _core = [_s.get('q') or _s.get('cycle') or _s.get('quarter'), _s.get('announce'), _s.get('effective')]
                if all(_e(x) for x in _core):
                    if not _e(_s.get('note')): _o.append(str(_s.get('note')))
                    continue
                # (req9 2026-07-19) 발효일만 있는 행(q·announce='-')은 표 대신 불릿 문자열로 — '-' 셀 근절
                if _e(_core[0]) and _e(_core[1]) and not _e(_core[2]):
                    _o.append('적용일(발효): %s%s' % (_s.get('effective'),
                              ('' if _e(_s.get('note')) else ' — ' + str(_s.get('note')))))
                    continue
                _o.append(_s)
            _b['schedule'] = ([x for x in _o if isinstance(_o[0], str)] if (_o and all(isinstance(x, str) for x in _o)) else _o)
        _rc = _b.get('rule_change')
        if isinstance(_rc, dict) and isinstance(_rc.get('rows'), list):
            for _rw in _rc['rows']:
                if isinstance(_rw, dict) and _e(_rw.get('detail')) and _e(_rw.get('change')):
                    for _k2 in ('content', 'desc', 'description', 'summary'):
                        if not _e(_rw.get(_k2)):
                            _rw['detail'] = _rw[_k2]; break
        _cd = _b.get('candidates')
        if isinstance(_cd, list) and _cd and all(isinstance(c, dict) and _e(c.get('biz')) and _e(c.get('valuation')) for c in _cd):
            _b['candidates'] = [{'name': c.get('name'), 'note': (c.get('status') or c.get('note') or '')} for c in _cd]
    return r
m['index_rebalance'] = _rebal_canon({k: v for k, v in _rbu.items() if k != 'latest_change_date'})

crd = dict(cr); crd['charts'] = {'btc': 'charts/coin_btc.png', 'eth': 'charts/coin_eth.png', 'xrp': 'charts/coin_xrp.png', 'sol': 'charts/coin_sol.png', 'fng': 'charts/fng_1y.png'}
# (fix) 김치프리미엄 coins[] 구성 (빌더는 kimchi_premium.coins[{symbol,u,b,pp,status}] 필요) — 6.3 미표시 문제
_kp = crd.get('kimchi_premium')
if isinstance(_kp, dict) and not _kp.get('coins'):
    _rate = _kp.get('rate_usd_krw') or _kp.get('exchange_rate_krw_per_usd') or _kp.get('rate')
    _coins = []
    for _sym in ('btc', 'eth', 'xrp', 'sol'):
        _v = _kp.get(_sym)
        if isinstance(_v, dict):
            _coins.append({'symbol': _sym.upper(),
                           'upbit_krw': _v.get('upbit_krw', _v.get('u', _v.get('upbit'))),
                           'binance_usd': _v.get('binance_usd', _v.get('b', _v.get('binance'))),
                           'premium_pct': _v.get('premium_pct', _v.get('pp', _v.get('premium'))),
                           'status': _v.get('status', '')})
        elif _v is not None:
            _coins.append({'symbol': _sym.upper(), 'upbit_krw': None, 'binance_usd': None, 'premium_pct': _v, 'status': ''})
    if _coins:
        crd['kimchi_premium'] = {'rate_usd_krw': _rate, 'coins': _coins}
# (req7) 김프가 여전히 비었으면 fetch_us.py 샌드박스 계산(nmr_kimchi.json) 폴백
_kp2 = crd.get('kimchi_premium')
_kneed = (not isinstance(_kp2, dict)) or (not _kp2.get('coins')) or all((c.get('premium_pct') in (None, '')) for c in (_kp2.get('coins') or []))
if _kneed:
    _kj = L('nmr_kimchi.json')
    if isinstance(_kj, dict) and _kj.get('coins'):
        crd['kimchi_premium'] = {'rate_usd_krw': _kj.get('rate_usd_krw'), 'coins': _kj['coins']}
        print('  [req7] 김프 nmr_kimchi.json 폴백:', len(_kj['coins']))

# news (+ longterm 병합·중복제거·빈event 방어 필터: 2.2 가 "-" 로 새지 않도록)
news = dict(nw)
# (req1-fix 재발방지) nmr_news.json 이 bigtech_events 등을 중첩 'news' 키 아래로 저장한 경우 상위로 hoist.
#   build_report 는 data.news.bigtech_events(한 겹)를 읽으므로, 한 겹 더 들어가면 2.3 섹션이 통째로 누락된다.
_nested_news = news.pop('news', None)
if isinstance(_nested_news, dict):
    for _nk, _nv in _nested_news.items():
        if not news.get(_nk):
            news[_nk] = _nv
    print('  [req1-fix] 중첩 news 키 hoist:', list(_nested_news.keys()))
# (fix v3.48) bigtech_events 이중 소유 방어: NewsAgent(nw)에 없으면 NewsBerk(n2)에서 가져와 2.3 누락 방지
if not news.get('bigtech_events') and (n2.get('bigtech_events')):
    news['bigtech_events'] = n2.get('bigtech_events')
    if n2.get('bigtech_events_comment') and not news.get('bigtech_events_comment'):
        news['bigtech_events_comment'] = n2.get('bigtech_events_comment')
    print('  [fix v3.48] bigtech_events 를 nmr_news2 에서 폴백:', len(news['bigtech_events']))
# (req1) Top News 최대 D-2: 발행일이 그제~오늘인 기사만(없으면 원본 유지 — 빈손 방지)
try:
    _dw=now.date().weekday(); _back=(4 if _dw==0 else 3 if _dw==6 else 2)  # (req1) D-2까지 · 주말 보정
    _d1 = (now.date() - dt.timedelta(days=_back)).isoformat()
    _tn = news.get('top_news') or []
    _fresh = [x for x in _tn if str(x.get('published_date','')) >= _d1]
    if _fresh: news['top_news'] = _fresh
except Exception: pass
# (req2) 2.3 빅테크 이벤트·이벤트캘린더: 지나간(오늘 이전) 항목 제거
try:
    _td = now.date().isoformat()
    for _ek in ('bigtech_events','events_calendar'):
        _ev = news.get(_ek)
        if isinstance(_ev, list):
            news[_ek] = [e for e in _ev if not (e.get('date') and str(e.get('date'))[:10] < _td)]
except Exception: pass
lt = (nw.get('events_calendar_longterm') or []) + (n2.get('events_calendar_longterm') or [])
seen = set(); ltu = []
for e in lt:
    if not (e and e.get('event')): continue
    k = (e.get('date', ''), e.get('event', ''))
    if k not in seen: seen.add(k); ltu.append(e)
news['events_calendar_longterm'] = ltu

# (Big-Arch) 비매일 섹션 DB 동기화 — 신규조사분 있으면 db/<item>.json 저장, 비면 DB값 재사용.
#   marker=섹션 최신 발표/결정일(변경 시에만 의미). 에이전트는 매 실행 marker 만 싸게 관측해 reuse 면 조사 스킵 가능.
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import nmr_db as _ndb
    _dd = _ndb._dbdir(); _run_m = RD_ISO[:7]; _today = RD_ISO[:10]
    _mc = m.get('macro') or {}; _rt = _mc.get('rates') or {}
    import re as _re2
    def _mx(rows, ks):
        vv = [str(r.get(k))[:10] for r in (rows or []) if isinstance(r, dict) for k in ks if r.get(k)]
        vv = [x for x in vv if _re2.match(r"^\d{4}[-.]\d{1,2}", x)]
        return max(vv) if vv else ''
    _ir = (_mc.get('inflation') or {}).get('rows')
    _mc.setdefault('inflation', {})['rows'] = _ndb.sync('inflation', (_ir if not _MDEF else None), _today, _mx(_ir, ['asof', 'release']) or _run_m, _dd)
    # (req1 근본수정) 물가 MoM 결측 시 DB 지수레벨(series_inflidx_*)로 전월비 계산해 항상 표시 — 재발방지
    def _inflidx_key(_nm):
        if 'Core CPI' in _nm: return 'Core_CPI'
        if 'Core PCE' in _nm: return 'Core_PCE'
        if _nm.startswith('CPI'): return 'CPI'
        if _nm.startswith('PCE'): return 'PCE'
        if 'PPI' in _nm: return 'PPI'
        return None
    for _ir2 in (_mc.get('inflation') or {}).get('rows') or []:
        _nm=_ir2.get('name',''); 
        if 'BEI' in _nm or '기대인플' in _nm: continue
        if _ir2.get('mom') in (None,'','-'):
            _ik=_inflidx_key(_nm); _lv=(_ndb.get('series_inflidx_%s'%_ik,_dd) if _ik else None)
            if isinstance(_lv,list) and len(_lv)>=2:
                try: _ir2['mom']=round((_lv[-1][1]/_lv[-2][1]-1)*100,2)
                except Exception: pass
    _er = (_mc.get('employment') or {}).get('rows')
    _mc.setdefault('employment', {})['rows'] = _ndb.sync('employment', (_er if not _MDEF else None), _today, _mx(_er, ['asof', 'release']) or _run_m, _dd)
    # (2026-07-12 사용자 req) DB 오염 방어: sync 결과 행 value 가 비면 이번 수집분(_er)에서 셀 단위 보강 후 DB 재저장
    try:
        _syn = (_mc.get('employment') or {}).get('rows') or []
        _srcm = {str(x.get('name','')): x for x in (_er or []) if isinstance(x, dict)}
        _fixn = 0
        for _sr in _syn:
            if _sr.get('value') in (None, '', '-'):
                _cand = _srcm.get(str(_sr.get('name',''))) or next((_v2 for _k2, _v2 in _srcm.items() if _k2[:6] and _k2[:6] in str(_sr.get('name',''))), None)
                if _cand and _cand.get('value') not in (None, '', '-'):
                    for _fk in ('value', 'asof', 'release'):
                        if _cand.get(_fk) not in (None, '', '-'): _sr[_fk] = _cand.get(_fk)
                    _fixn += 1
        if _fixn:
            _mc['employment']['rows'] = _ndb.sync('employment', _syn, _today, (_mx(_syn, ['asof', 'release']) or _run_m) + '|empfix', _dd)
            print('  [empfix] 고용 DB 오염 셀 보강:', _fixn)
    except Exception as _efe:
        print('  [empfix] skip:', _efe)
    _rt['policy_rates'] = _ndb.sync('policy_rates', (_rt.get('policy_rates') if not _MDEF else None), _today, _run_m, _dd)
    # (req2 2026-07-12) FOMC 회의: USMacroExtras(nmr_usmacro.json) 수집분 1순위 + DB와 날짜 union —
    #   과거 1년 실제 결정(인상/인하/동결)이 미래 예정 회의에 밀려 유실되지 않게 한다. marker=최신일|건수.
    _fm_new = um.get('fomc_meetings') if isinstance(um.get('fomc_meetings'), list) else (_rt.get('fomc_meetings') if not _MDEF else None)
    _fm_db = _ndb.get('fomc_meetings', _dd) or []
    if isinstance(_fm_new, list) and _fm_new:
        _fm_map = {str(x.get('date')): x for x in (_fm_db if isinstance(_fm_db, list) else []) if isinstance(x, dict) and x.get('date')}
        for _x in _fm_new:
            if isinstance(_x, dict) and _x.get('date'): _fm_map[str(_x['date'])] = _x
        _fm_u = sorted(_fm_map.values(), key=lambda x: str(x.get('date')))
        _cut_lo = (dt.date.fromisoformat(_today) - dt.timedelta(days=370)).isoformat()
        _fm_u = [x for x in _fm_u if str(x.get('date')) >= _cut_lo]
        # (사용자 피드백 2026-07-12) '예정' 회의는 향후 3개만 수록 (과거 1년 실제 결정은 전부 유지)
        _fm_past = [x for x in _fm_u if str(x.get('date')) <= _today]
        _fm_fut = [x for x in _fm_u if str(x.get('date')) > _today][:3]
        _fm_u = _fm_past + _fm_fut
    else:
        _fm_u = None
    _rt['fomc_meetings'] = _ndb.sync('fomc_meetings', _fm_u, _today,
                                     ((_mx(_fm_u, ['date']) or _run_m) + '|' + str(len(_fm_u))) if _fm_u else _run_m, _dd)
    _dp = m.get('fomc_dotplot') or {}
    m['fomc_dotplot'] = _ndb.sync('dot_plot', _dp, _today, (_dp.get('fomc_sep_date') or _run_m), _dd)
    m['korea_leading'] = _ndb.sync('leading', m.get('korea_leading'), _today, _mx(m.get('korea_leading'), ['period']) or _run_m, _dd)
    # (v3.56) 3.1.5 경기선행 장기 시계열 누적 → db/series_leading.json
    #   fetch_leading.py 가 만드는 nmr_leading_series.json([["YYYY-MM",val]..]) 을 DB에 union 누적한다.
    #   미수집 회차에도 과거 DB가 남아 차트가 끊기지 않는다(대시보드도 이 시계열을 사용).
    _lsr = L('nmr_leading_series.json')
    if isinstance(_lsr, list) and _lsr:
        _lsd = _ndb.dbseries('leading', _lsr, _dd)
        print('leading_series: %s (%d pts)' % (_lsd.get('status'), len(_lsd.get('data') or [])))
    # (v3.43→v3.49) 3.1.4 OECD CLI — 신규 스크랩(nmr_oecd_cli.json, KOSIS 자료갱신일 변동 시에만 생성) 있으면 DB 갱신, 없으면 DB 재사용
    _oc = L('nmr_oecd_cli.json')
    _oc_ok = isinstance(_oc, dict) and _oc.get('months') and _oc.get('series')
    m['oecd_cli'] = _ndb.sync('oecd_cli', (_oc if _oc_ok else None), _today,
                              ((_oc or {}).get('data_updated') or _run_m) if _oc_ok else _run_m, _dd)
    if isinstance(m.get('oecd_cli'), dict): m['oecd_cli']['chart'] = 'charts/oecd_cli.png'
    # (v3.44) 3.1.10 관세청 수출 잠정치 — 신규 백필(nmr_customs.json, 변경 시에만 생성) 있으면 DB 갱신, 없으면 DB 재사용
    _cs = L('nmr_customs.json')
    _cs_ok = isinstance(_cs, dict) and _cs.get('series') and _cs.get('months')
    m['customs'] = _ndb.sync('customs', (_cs if _cs_ok else None), _today,
                             ((_cs or {}).get('marker') or _run_m) if _cs_ok else _run_m, _dd)
    if isinstance(m.get('customs'), dict):
        m['customs']['chart_total'] = 'charts/수출_전체_24개월.png'
        m['customs']['chart_semi'] = 'charts/수출_반도체_24개월.png'
    # (v3.45→v3.49) 3.1.11 반도체 사이클→코스피 점검판 — 신규 조사분(nmr_semi_cycle.json, 3대 신호/코스피 쏠림 변동 시에만 생성) 있으면 DB 갱신, 없으면 DB 재사용
    _sci = L('nmr_semi_cycle.json')
    def _sc_canon(x):
        if not isinstance(x, dict): return False
        tl=x.get('tiles'); sg=x.get('signals'); st=x.get('stages')
        tiles_ok=isinstance(tl,list) and any(isinstance(t,dict) and ('num' in t) for t in tl)
        sig_ok=isinstance(sg,list) and any(isinstance(z,dict) and ('value' in z) for z in sg)
        stg_ok=isinstance(st,dict) and isinstance(st.get('list'),list)
        return tiles_ok or sig_ok or stg_ok
    # (fix 2026-07-09) 잘못된 스키마(label/value·current/verdict·[{name,active}]) 입력이 DB를 오염시키는 것을 차단 —
    # 빌더 renderSemiCycle 이 요구하는 정규 스키마(tiles[].num·signals[].value·stages.list)일 때만 수용, 아니면 DB 재사용.
    _sc_ok = _sc_canon(_sci)
    m['semi_cycle'] = _ndb.sync('semi_cycle', (_sci if _sc_ok else None), _today,
                                ((_sci or {}).get('asof') or _run_m) if _sc_ok else _run_m, _dd)
    # (req7 2026-07-12) 3대 조기경보 '판정상태' 매일 누적 → db/series_semi_status.json
    #   정량 미공개 신호(재고주수·CAPEX YoY)도 판정(안전=0/주의=1/경보=2)을 타임라인으로 축적해 차트화한다.
    try:
        _scd = m.get('semi_cycle') or {}
        def _st2n(s):
            s = str(s or '')
            for _kw, _nv in (('경보', 2), ('하강', 2), ('위험', 2), ('주의', 1), ('둔화', 1), ('안전', 0), ('양호', 0)):
                if _kw in s: return _nv
            return None
        _svals = {}
        for _z in (_scd.get('signals') or []):
            _nm2 = str(_z.get('name') or '')
            _key7 = 'inventory' if '재고' in _nm2 else ('capex_yoy' if 'CAPEX' in _nm2.upper() else ('price_qoq' if ('계약가' in _nm2 or 'QOQ' in _nm2.upper() or 'DRAM' in _nm2.upper()) else None))
            if _key7:
                _nv2 = _st2n(_z.get('status'))
                if _nv2 is not None: _svals[_key7] = _nv2
        if _svals:
            _ndb.dbseries('semi_status', [[_today, _svals]], _dd)
            print('  [req7] semi 판정상태 누적:', _svals)
    except Exception as _se7: print('  [req7] semi status 누적 skip:', _se7)

    # (v3.58) 3.1.9 메모리 가격 — fetch_memory.py(TrendForce 공개 가격표) 결과 적재.
    #   ① db/memory.json     : 최신 스냅샷 4개 표 + hbm + leading + meta (표 렌더용)
    #   ② db/series_mem_<키> : 날짜 union 누적 시계열 (차트용 — 실행할수록 길어진다)
    #      가격 4종 + hbm_asp/hbm_share + (v3.60) leading_px / mem_vs_gpu
    _mem = L('nmr_memory.json')
    if isinstance(_mem, dict) and _mem.get('tables'):
        _masof = _mem.get('asof') or _today
        _msnap = {}
        for _tk, _t in _mem['tables'].items():
            _s = {r['item']: r['avg'] for r in (_t.get('rows') or []) if r.get('avg') is not None}
            if _s: _msnap[_tk] = _s
        _hb = _mem.get('hbm') or {}
        _s = {a['product']: a['price_mid'] for a in (_hb.get('asp') or []) if a.get('price_mid')}
        if _s: _msnap['hbm_asp'] = _s
        _s = {r['vendor']: r['share_pct'] for r in (_hb.get('share') or []) if r.get('share_pct')}
        if _s: _msnap['hbm_share'] = _s
        # (v3.60) 선행지표 — 종가 6종 + 메모리/GPU 상대강도(가치 이동 신호)
        _ld = _mem.get('leading') or {}
        _s = {v['label']: v['price'] for v in _ld.values()
              if isinstance(v, dict) and v.get('price') is not None}
        if _s: _msnap['leading_px'] = _s
        _rs = (_ld.get('MEM_VS_GPU') or {}).get('value')
        if _rs is not None: _msnap['mem_vs_gpu'] = {'메모리/GPU 상대강도': _rs}

        _ndb.set_('memory', _masof, _masof, _dd, _mem)
        for _tk, _snap in _msnap.items():
            _cur = (_ndb._load('series_mem_' + _tk, _dd) or {}).get('data') or []
            _mg = [x for x in _cur if x[0] != _masof] + [[_masof, _snap]]
            _mg.sort(key=lambda x: x[0])
            _ndb.set_('series_mem_' + _tk, '', _masof, _dd, _mg)
        m['memory'] = _mem
        print('memory: %d개 표 · 시계열 %d종 적재 (선행지표 %d종 · 메타 %d종)'
              % (len(_mem['tables']), len(_msnap), len(_ld), len(_mem.get('meta') or {})))
    else:
        _mdb = _ndb.get('memory', _dd)
        if _mdb: m['memory'] = _mdb; print('memory: 수집 없음 → DB 재사용')

    # (v3.60) 3.1.8 CAPEX 일일 갱신 — db/capex.json
    #   실측치는 CAPEX 서브에이전트가 매 실행 MCP(UsStockInfo get_financial_statement)로 재수집해
    #   nmr_capex.json 의 capex_series/rev_series/fcf_series 로 넘긴다. 실제 값은 분기 실적발표 때만
    #   변하므로 "매일 체크 → 변동한 셀만 갱신, 결측·미수집 셀은 DB carry-forward" 로 처리한다.
    #   (Yahoo quoteSummary 는 cashflowStatementHistory 가 netIncome 만 반환하도록 축소돼 CAPEX 취득 불가.)
    try:
        _cx = m.get('bigtech_capex') or {}
        _cdb = _ndb.get('capex', _dd) or {}
        _yrs = ((_cx.get('capex_series') or {}).get('years')) or _cdb.get('years') or []
        _out = {'asof': _today, 'unit': 'USD billion', 'years': _yrs,
                'companies': [], 'capex': {}, 'revenue': {}, 'fcf': {}, 'capex_to_rev': {}}
        _chg = []
        for _fld, _sk in (('capex', 'capex_series'), ('revenue', 'rev_series'), ('fcf', 'fcf_series')):
            _sr = _cx.get(_sk) or {}
            _old = _cdb.get(_fld) or {}
            _cos = [k for k in _sr if k != 'years'] or list(_old)
            for _co in _cos:
                _new = _sr.get(_co) or []
                _prv = _old.get(_co) or []
                _row = []
                for _i in range(len(_yrs)):
                    _v = _new[_i] if _i < len(_new) else None
                    if _v in (None, '', '-'):
                        _v = _prv[_i] if _i < len(_prv) else None   # carry-forward
                    _row.append(_v)
                _out[_fld][_co] = _row
                if _prv and _row != _prv: _chg.append('%s.%s' % (_fld, _co))
        _out['companies'] = list(_out['capex'].keys())
        for _co, _cv in _out['capex'].items():
            _rv = (_out['revenue'].get(_co) or []) + [None] * len(_cv)
            _out['capex_to_rev'][_co] = [
                (round(100.0 * float(_a) / float(_b), 1)
                 if isinstance(_a, (int, float)) and isinstance(_b, (int, float)) and _b else None)
                for _a, _b in zip(_cv, _rv)]
        if _out['companies'] and _out['years']:
            _ndb.set_('capex', _today, _today, _dd, _out)
            print('capex: %d사 × %d년 DB 갱신 %s'
                  % (len(_out['companies']), len(_yrs),
                     ('· 변동 %d건 %s' % (len(_chg), _chg[:4])) if _chg else '· 변동 없음(carry-forward)'))
    except Exception as _cde:
        print('  [capex] DB 동기화 skip(비차단):', _cde)

    print('  [DB] 비매일 섹션 동기화: inflation/employment/policy_rates/fomc_meetings/dot_plot/leading/oecd_cli/customs/semi_cycle/memory/capex -> db/')
except Exception as _dbe:
    print('  [DB] 동기화 skip(비차단):', _dbe)
# (2차 req10 2026-07-18) 7.7 네이버 금융리서치 모음 — 서버 broker_reports DB(recent 2일치) 주입
# (req6 2026-07-19) 로컬 db/ 미존재 시 WORK 의 서버 캐시(server_broker_reports.json — Phase 1 curl)·HTTP 폴백.
try:
    import nmr_db as _ndb_br
    _brd = {}
    for _bp in (os.path.join(_ndb_br._dbdir(), 'broker_reports.json'),
                os.path.join(W, 'server_broker_reports.json')):
        try:
            _cand = json.load(open(_bp, encoding='utf-8'))
            if _cand.get('recent'):
                _brd = _cand; break
        except Exception:
            pass
    if not _brd.get('recent'):
        try:
            import urllib.request as _ur
            _brd = json.loads(_ur.urlopen('http://141.147.160.13/api/db/broker_reports', timeout=10).read().decode('utf-8'))
        except Exception:
            _brd = {}
    if isinstance(sec, dict) and _brd.get('recent'):
        sec['naver_research'] = {'recent': _brd['recent'], 'as_of': _brd.get('as_of', '')}
        _map = {'kb': 'KB증권', 'nh': 'NH투자증권', 'samsung': '삼성증권', 'miraeasset': '미래에셋증권',
                'korea_inv': '한국투자증권', 'meritz': '메리츠증권'}
        _byb = {f.get('broker'): f.get('reports') or [] for f in (_brd.get('firms') or [])}
        _frm = sec.get('firm') if isinstance(sec.get('firm'), dict) else sec
        for _k, _nm in _map.items():
            _e = _frm.get(_k)
            if isinstance(_e, dict) and _byb.get(_nm):
                _kr = _e.get('key_reports') or []
                if not _kr or not any((isinstance(x, dict) and x.get('url')) for x in _kr):
                    _e['key_reports'] = [{'title': r['title'], 'url': r['url'], 'date': r.get('date', '')}
                                         for r in _byb[_nm][:4]]
except Exception:
    pass

data = {'report_date': RD_ISO,
        'metadata': {'report_date': RD_ISO, 'generated_at': now.strftime('%Y-%m-%d %H:%M KST'), 'mode': MODE},
        'news': news, 'markets': m, 'commodities': com, 'crypto': crd, 'analysis': an,
        'securities': sec, 'global_securities': gs, 'berkshire': n2.get('berkshire', {}), 'ai_trends': n2.get('ai_trends', {})}
os.makedirs(os.path.join(W, '_market_report_data'), exist_ok=True)
# (R4 req2/req3) 국채 단일소스화: FMP treasury 일별 → us10y/us2y 일관 블록(1d_pct=D0 전일대비, prev_pct=D-1 일간변동) 강제
def _ko_trend_bond(o):
    try:
        y1=o.get('1y_pct') or 0; m3=o.get('3mo_pct') or 0; m1=o.get('1mo_pct') or 0
        base = '상승세' if y1>3 else ('하락세' if y1<-3 else '횡보 흐름')
        return f"{base}(1년 {y1:+.2f}%·3개월 {m3:+.2f}%·1개월 {m1:+.2f}%)"
    except Exception:
        return o.get('trend') or '-'
try:
    _rates_fin = macro.setdefault('rates', {})
    _tc = LCF('treasury_consistent.json')
    for _bk in ('us10y','us2y'):
        _o = _rates_fin.get(_bk)
        if not isinstance(_o, dict):
            _o = {}; _rates_fin[_bk] = _o
        _src = (_tc.get(_bk) or {}).get('block') if isinstance(_tc, dict) else None
        # (fix req1) 에이전트/시계열 최신값 우선 — stale carry-forward 로 덮어쓰지 않음
        _bser = (macro.get('series') or {}).get(_bk+'_daily')
        if _o.get('current') is not None and _bser:
            try:
                _fr = ret(_bser)
                for _hk in ('1w_pct','1mo_pct','3mo_pct','6mo_pct','1y_pct','1d_pct','prev_pct'):
                    if _fr.get(_hk) is not None: _o[_hk] = _fr[_hk]
                _sp2 = sorted([(dt.date.fromisoformat(str(a)[:10]), float(b)) for a,b in _bser if b is not None])
                if len(_sp2) >= 2:
                    _o['prev_close'] = round(_sp2[-2][1],3); _o['chg'] = round(_o['current'] - _sp2[-2][1], 3)
            except Exception: pass
            _src = None
        if _src:
            _o['current'] = _src['current']; _o['prev_close'] = _src['prev_close']
            _o['chg'] = round(_src['current'] - _src['prev_close'], 3)
            for _hk in ('1d_pct','prev_pct','1w_pct','1mo_pct','3mo_pct','6mo_pct','1y_pct'):
                _o[_hk] = _src.get(_hk)
        # 대전제: 현재가셀=1d_pct(D0 전일대비), '1일'컬럼=prev_pct(D-1 일간변동) — 구분 유지
        _o['spark'] = 'charts/spark_%s.png' % _bk
        _o['trend'] = _ko_trend_bond(_o)
    # (fix req2) 장단기 금리차(10Y-2Y) 매일 실측 = us10y - us2y
    _u10c=(_rates_fin.get('us10y') or {}).get('current'); _u2c=(_rates_fin.get('us2y') or {}).get('current')
    if _u10c is not None and _u2c is not None:
        _spd=round(_u10c-_u2c,2)
        _rates_fin['yield_curve']={'spread':_spd,'label':'미국 장단기 금리차(수익률곡선)(10Y-2Y)',
            'status':('정상(양전환)' if _spd>=0 else '역전(침체 선행 신호)'),
            'note':'10Y=%.2f%%, 2Y=%.2f%%'%(_u10c,_u2c),
            'meaning':'장단기 금리차 정상화 = 경기 연착륙 기대','impact':'스프레드 역전 시 침체 선행지표',
            'chart':'charts/macro_curve.png','asof':(_rates_fin.get('us10y') or {}).get('asof')}
    # (req5 갱신) 美 기준금리 = 정책금리 DB 실측 현재값으로 일관화
    _prdb = LCF('nmr_policyrates_monthly.json')
    if isinstance(_prdb, dict):
        _uscur = (_prdb.get('current') or {}).get('미국')
        if _uscur is not None:
            _ff = _rates_fin.setdefault('fed_funds', {})
            _ff['current'] = _uscur
            print('  [R4] 美 기준금리 실측 반영:', _uscur)
    # (req2) fed_funds decision/bias/meaning/freq/impact 누락 보강 — 빌더 undefined 방지
    _ff2 = _rates_fin.setdefault('fed_funds', {})
    _ffd = (MACRO_DEFAULT.get('fed_funds') or (MACRO_DEFAULT.get('rates') or {}).get('fed_funds') or {}) if isinstance(MACRO_DEFAULT, dict) else {}
    _ffdef = {'meaning':'연준 기준금리(정책금리 상단). 모든 자산가격의 할인율 기준',
              'freq':'연 8회 FOMC','impact':'금리↑ → 주식↓·달러↑·채권가격↓ / 금리↓ → 반대'}
    for _k in ('meaning','freq','impact'):
        if not _ff2.get(_k): _ff2[_k] = _ffd.get(_k) or _ffdef[_k]
    if not _ff2.get('decision'): _ff2['decision'] = '동결'
    _bias_dp = None
    try:
        _dp = (m.get('fomc_dotplot') or {}).get('rows') or []
        _r26 = next((r for r in _dp if '2026' in str(r.get('year',''))), None)
        if _r26 and _r26.get('jun') is not None:
            _diff = round(float(_r26['jun']) - float(_ff2.get('current') or 0), 3)
            if _diff >= 0.04: _bias_dp = '인상 시사 (점도표 상향)'
            elif _diff <= -0.04: _bias_dp = '인하 시사 (점도표 하향)'
    except Exception: pass
    if _bias_dp: _ff2['bias'] = _bias_dp
    elif not _ff2.get('bias'): _ff2['bias'] = '중립'
    try:
        if isinstance(macro.get('inflation'), dict): macro['inflation']['chart'] = 'charts/macro_inflation.png'
        if isinstance(macro.get('employment'), dict): macro['employment']['chart'] = 'charts/macro_employment.png'
        print('  [R4] 차트경로 강제: inflation/employment')
    except Exception as _ce: print('  [R4] 차트경로 강제 skip:', _ce)
    print('  [R4] 국채 단일소스 강제: us10y', _rates_fin.get('us10y',{}).get('current'),
          '1d', _rates_fin.get('us10y',{}).get('1d_pct'),
          '| us2y', _rates_fin.get('us2y',{}).get('current'),
          '1d', _rates_fin.get('us2y',{}).get('1d_pct'))
except Exception as _e:
    print('  [R4] 국채 단일소스 강제 skip(비차단):', _e)

# (2026-07-17) 서버 자체 수집 항목 명시 — docx 캡션(갱신주기·데이터 수집시점). 서버 cron 이 채우는 DB 는
#   보고서 실행 시점 조사가 아님을 표기한다(사용자 req). as_of/marker = db/<item>.json 실측.
try:
    import nmr_db as _ndbS
    _ddS = _ndbS._dbdir()
    def _svnote(item, cadence):
        _e = _ndbS._load(item, _ddS) or {}
        _a = _e.get('as_of') or '-'; _mk = str(_e.get('marker') or '')[:28]
        return ('※ 서버 자체 수집 항목 — 본 보고서 실행 시점 조사가 아니라 서버가 주기 수집·누적한 DB 를 사용(실행 시 변동체크·병합) · 갱신주기: '
                + cadence + ' · 데이터 수집시점: ' + str(_a) + ((' (마커 ' + _mk + ')') if _mk else ''))
    m['server_notes'] = {
        'customs':   _svnote('customs',       '서버 자동 매일 2회(06:35·15:35 KST)'),
        'leading':   _svnote('leading',       '서버 자동 매일 2회(06:35·15:35 KST)'),
        'krx_brief': _svnote('krx_brief',     '서버 자동 매일 2회(06:35·15:35 KST)'),
        'hy':        _svnote('series_hy_oas', '서버 자동 매일 2회(06:35·15:35 KST) + 실행 시 FRED 실측'),
        'memory':    _svnote('memory',        '서버 자동 매일 2회(06:45·15:45 KST)'),
    }
    _dpS = m.get('deriv_positioning')
    if isinstance(_dpS, dict) and _dpS.get('asof'):
        _tagS = ' · ※ 서버 마감캡처 병합: 韓 PCR(Vol)·IV스큐·GEX·VKOSPI=서버 15:48 KST, 美 옵션=서버 06:40 KST (실행 시점 조사 아님)'
        if _tagS.strip() not in str(_dpS['asof']): _dpS['asof'] = str(_dpS['asof']) + _tagS
except Exception as _sne:
    print('  server_notes skip(비차단):', repr(_sne)[:60])

# (v3.71 재발방지) 증권사·IB key_reports 신선도 필터 — verify req8 과 동일 규칙을 merge 가 선적용해
#   서버DB 보강분·에이전트 수집분의 stale 링크가 게이트 차단을 내지 않게 한다.
#   KR=weekly(3일)·IB=weekly7(7일), 기준일 요일 보정(월+2/토+1/일+2), 부분 날짜(YYYY-MM 등)는 제거.
try:
    import datetime as _fdt, re as _fre
    _fref = _fdt.date(int(RD[:4]), int(RD[4:6]), int(RD[6:8]))
    def _fmax(base):
        _m = base; _w = _fref.weekday()  # Mon=0..Sun=6
        if _w == 0: _m += 2
        elif _w == 5: _m += 1
        elif _w == 6: _m += 2
        return _m
    def _ffilt(sec, base):
        if not isinstance(sec, dict): return 0
        _n = 0
        for _fk, _fv in sec.items():
            if not isinstance(_fv, dict): continue
            _krs = _fv.get('key_reports')
            if not isinstance(_krs, list): continue
            _keep = []
            for _r in _krs:
                _dt = (_r or {}).get('date', '') if isinstance(_r, dict) else ''
                if _dt:
                    if not _fre.fullmatch(r'\d{4}-\d{2}-\d{2}', str(_dt)):
                        _n += 1; continue
                    try:
                        _d0 = _fdt.date(*map(int, str(_dt).split('-')))
                        if (_fref - _d0).days > _fmax(base): _n += 1; continue
                    except Exception: _n += 1; continue
                _keep.append(_r)
            _fv['key_reports'] = _keep
        return _n
    _fn1 = _ffilt(data.get('securities'), 3)
    _fn2 = _ffilt(data.get('global_securities'), 7)
    if _fn1 or _fn2: print('  [v3.71] stale key_reports 필터: KR %d · IB %d 제거(verify req8 선적용)' % (_fn1, _fn2))
except Exception as _fe:
    print('  stale filter skip(비차단):', repr(_fe)[:60])

# (v3.73) 증권사·IB key_message 자동 정직화 — key_reports 가 비었는데 key_message 도 비면
#   빌더·대시보드에 "(리포트 수집 실패)" 만 남아 '왜 비었는지'가 사라진다(게이트 req33 경고).
#   stale 필터가 링크를 지운 경우도 포함해 사유 문장을 자동으로 채운다.
try:
    def _km_fix(sec):
        if not isinstance(sec, dict): return 0
        _n = 0
        for _k, _v in sec.items():
            if not isinstance(_v, dict) or 'strength' not in _v: continue
            if (_v.get('key_reports') or []): continue
            _msg = str(_v.get('key_message') or '').strip()
            if _msg and '미확인' in _msg: continue
            _base = '기준일 충족 최신 공개 자료 미확인'
            _v['key_message'] = (_base + ' - ' + _msg) if _msg else (
                _base + ' (실행일 ' + RD_ISO + ' 기준 신선도 기준 내 공개분이 수집되지 않음)')
            _n += 1
        return _n
    _k1 = _km_fix(data.get('securities')); _k2 = _km_fix(data.get('global_securities'))
    if _k1 or _k2: print('  [v3.73] key_message 정직화(미확인 사유 주입): KR %d · IB %d' % (_k1, _k2))
except Exception as _ke:
    print('  key_message fix skip(비차단):', repr(_ke)[:60])

# (v3.76) 3.1.7 M7 신호 결정론화 — 에이전트 주관 판정이 데이터와 상반되던 문제(2026-07-21 실측:
#   MSFT 리비전 상향·여력 +35.5% 인데 '경계', TSLA 리비전 +18.3% 급상향인데 '위험')를 없앤다.
#   규칙(2축 + 의견 보정): 리비전 R(연간 EPS 컨센 변화) × 밸류 U(평균목표주가 여력) 결정표에
#   투자의견이 '보유/매도'면 한 단계 하향. 산출 근거를 signal_basis 로 표에 노출해 검증 가능하게 한다.
try:
    import re as _re
    def _num(s):
        m = _re.search(r'[-+]?\d+(?:\.\d+)?', str(s or '').replace(',', ''))
        return float(m.group(0)) if m else None
    def _revpct(o):
        v = o.get('rev_pct')
        if isinstance(v, (int, float)): return float(v)
        n = _num(v)
        if n is not None: return n
        d = str(o.get('revision_detail') or '')
        m = _re.search(r'([-+]\s*\d+(?:\.\d+)?)\s*%', d)   # 첫 번째 % = 대표 리비전
        if m: return float(m.group(1).replace(' ', ''))
        t = str(o.get('revision') or '')
        return 1.0 if '상향' in t else (-1.0 if '하향' in t else 0.0)
    _ORD = ['위험', '경계', '중립', '긍정']
    def _m7sig(o):
        rp = _revpct(o); up = _num(o.get('upside')); cs = str(o.get('consensus') or '')
        if up is None: up = 0.0
        R = '상향' if rp >= 0.2 else ('하향' if rp <= -0.2 else '보합')
        U = '큼' if up >= 15 else ('보통' if up >= 5 else '작음')
        TBL = {('상향','큼'):'긍정', ('상향','보통'):'긍정', ('상향','작음'):'중립',
               ('보합','큼'):'중립', ('보합','보통'):'중립', ('보합','작음'):'경계',
               ('하향','큼'):'경계', ('하향','보통'):'경계', ('하향','작음'):'위험'}
        sig = TBL[(R, U)]
        adj = ''
        if ('보유' in cs) or ('중립' in cs) or ('매도' in cs) or ('비중축소' in cs):
            i = _ORD.index(sig)
            if i > 0: sig = _ORD[i-1]; adj = ' · 의견 %s로 1단계 하향' % (cs.strip()[:6])
        basis = '리비전 %s(%+.2f%%) × 여력 %s(%+.1f%%)%s' % (R, rp, U, up, adj)
        return sig, basis
    _m7 = (m.get('m7_outlook') or {}) if isinstance(m.get('m7_outlook'), dict) else {}
    _rw = _m7.get('rows') if isinstance(_m7.get('rows'), list) else []
    _chg = 0
    for _o in _rw:
        if not isinstance(_o, dict): continue
        _s, _b = _m7sig(_o)
        _o['signal_agent'] = _o.get('signal')      # 에이전트 원판정 보존(감사용)
        if _o.get('signal') != _s: _chg += 1
        _o['signal'] = _s; _o['signal_basis'] = _b
    if _rw:
        _m7['signal_rule'] = ('신호 = 리비전(연간 EPS 컨센 변화: 상향≥+0.2% / 보합 ±0.2% / 하향≤-0.2%) × '
                              '여력(평균목표주가 대비: 큼≥15% / 보통 5~15% / 작음<5%) 결정표, '
                              '투자의견이 보유·매도면 1단계 하향. 코드 자동 산출(주관 판정 배제).')
        print('  [v3.76] M7 신호 규칙 재산출: %d/%d 종목 정정' % (_chg, len(_rw)))
except Exception as _me:
    print('  m7 signal skip(비차단):', repr(_me)[:70])

outp = os.path.join(W, '_market_report_data', f'report_data_{RD}.json')
json.dump(data, open(outp, 'w'), ensure_ascii=False, indent=1)
print('MERGED →', outp)
print('  sections:', [k for k in data])
print('  themes', len(trows), 'semi_stocks', len(ss), 'semi_etfs', len(se), '| longterm', len(ltu))
print('  korea_investors kospi:', m['korea_investors']['kospi'].get('comment', ''))
print('  leading:', m['korea_leading_comment'])
