#!/usr/bin/env python3
# merge.py (v3.7) — nmr_*.json 들을 report_data_YYYYMMDD.json 으로 병합 (Phase 3).
# 매 실행 즉석 작성하던 병합 로직을 결정적 스크립트로 베이크 (토큰·변동성 제거).
# 사용: python3 merge.py [WORK_DIR] [REPORT_DATE_YYYYMMDD]
#   WORK_DIR 없으면 cwd. REPORT_DATE 없으면 env NMR_DATE 또는 오늘(KST).
#   mode 는 env NMR_MODE(scheduled/normal) 또는 'normal'.
import json, os, sys, datetime as dt

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

mk = L('nmr_markets.json'); com = L('nmr_commod.json'); cr = L('nmr_crypto.json'); ue = L('nmr_usetf.json')
nw = L('nmr_news.json'); gs = L('nmr_globalsec.json'); um = L('nmr_usmacro.json'); rb = L('nmr_rebalance.json')
n2 = L('nmr_news2.json'); semi = L('nmr_semi.json'); krs = L('nmr_kr_series.json'); ohlcv = L('nmr_kr_ohlcv.json')
inv = L('nmr_kr_invest.json'); lead = L('nmr_leading.json'); sec = L('nmr_securities.json'); an = L('nmr_analysis.json')
tr = L('nmr_trendtext.json')

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
    return out

def koTrend(r):
    y = r.get('1y_pct'); m3 = r.get('3mo_pct')
    if y is None: return ''
    s = '강세' if y > 0 else '약세'; t = f"1년 {y:+.0f}%"
    if m3 is not None: t += f", 3개월 {m3:+.0f}%" + (' 가속' if (m3 or 0) > 0 and y > 0 else (' 조정' if (m3 or 0) < 0 else ''))
    return t + f" ({s})"

m = {}
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
themes = krs.get('themes', {}); trows = []
for t in (semi.get('korea_themes') or []):
    nm = t.get('theme'); s = themes.get(nm) or []
    r = ret(s); r.update({'theme': nm, 'direction': t.get('direction'), 'comment': t.get('comment'),
                          'chart': f"charts/theme_{san(nm)}.png", 'trend': koTrend(r)})
    trows.append(r)
m['korea_theme_rows'] = trows; m['korea_themes_comment'] = semi.get('korea_themes_comment') or ''

def aumfmt(v):
    try:
        v = float(v)
        if v >= 1e12: return f"{v / 1e12:,.0f}조원"
        if v >= 1e8: return f"{v / 1e8:,.0f}억원"
        return str(v)
    except Exception:
        return v if v else ''
ss = []
for i, x in enumerate(semi.get('semi_ai_stocks', [])[:10]):
    s = (krs.get('stocks') or {}).get(x.get('name')) or []
    r = ret(s); r.update({'name': x.get('name'), 'aum': aumfmt(x.get('aum')), 'note': x.get('note', ''), 'chart': f"charts/semi_s_{i}.png", 'trend': koTrend(r)})
    ss.append(r)
se = []
for i, x in enumerate(semi.get('semi_ai_etfs', [])[:20]):
    s = (krs.get('etfs') or {}).get(x.get('name')) or []
    r = ret(s); r.update({'name': x.get('name'), 'aum': aumfmt(x.get('aum')), 'note': x.get('note', ''), 'chart': f"charts/semi_e_{i}.png", 'trend': koTrend(r)})
    se.append(r)
m['semi_ai_stocks'] = ss; m['semi_ai_stocks_comment'] = semi.get('semi_ai_stocks_comment', '')
m['semi_ai_etfs'] = se; m['semi_ai_etfs_comment'] = semi.get('semi_ai_etfs_comment', '')

m['us_etfs'] = ue
m['bigtech_capex'] = um.get('bigtech_capex', {}); m['fomc_dotplot'] = um.get('fomc_dotplot', {})
# (fix) FOMC 점도표 '변화' 열 = jun - mar (build_report r.change 비어 '-' 표시되던 문제)
for _r in ((m.get('fomc_dotplot') or {}).get('rows') or []):
    if not str(_r.get('change') or '').strip():
        try: _r['change'] = "%+.1f" % (float(_r.get('jun')) - float(_r.get('mar')))
        except Exception: _r['change'] = ''
m['us_credit'] = um.get('us_credit', {}); m['us_treasury_curve'] = um.get('us_treasury_curve')
uc = um.get('us_credit', {})
m['hy_spread'] = {'current': uc.get('hy_oas'), 'hy_oas': uc.get('hy_oas'), 'hy_yield': uc.get('hy_yield'),
                  'implied_ust': uc.get('implied_ust'), 'comment': uc.get('comment'), 'chart': 'charts/hy_oas.png'}
# (fix) HY 1주~1년 OAS 히스토리 (nmr_hy_series.json 월별) — 3.2.3 의 1주/1개월~1년 열이 '-' 이던 문제
_hys = L('nmr_hy_series.json'); _hser = (_hys.get('series') if isinstance(_hys, dict) else _hys) or []
_hpts = sorted([(dt.date.fromisoformat(str(d)[:10]), float(v)) for d, v in _hser if v is not None])
if len(_hpts) >= 2:
    _last = _hpts[-1][0]
    for _k, _days in [('w1', 7), ('m1', 30), ('m3', 91), ('m6', 182), ('y1', 365)]:
        _tgt = _last - dt.timedelta(days=_days)
        _cand = [p for p in _hpts if p[0] <= _tgt] or [_hpts[0]]
        m['hy_spread'][_k] = round(_cand[-1][1], 2)
m['index_rebalance'] = {k: v for k, v in rb.items() if k != 'latest_change_date'}

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

# news (+ longterm 병합·중복제거·빈event 방어 필터: 2.2 가 "-" 로 새지 않도록)
news = dict(nw)
lt = (nw.get('events_calendar_longterm') or []) + (n2.get('events_calendar_longterm') or [])
seen = set(); ltu = []
for e in lt:
    if not (e and e.get('event')): continue
    k = (e.get('date', ''), e.get('event', ''))
    if k not in seen: seen.add(k); ltu.append(e)
news['events_calendar_longterm'] = ltu

data = {'report_date': RD_ISO,
        'metadata': {'report_date': RD_ISO, 'generated_at': now.strftime('%Y-%m-%d %H:%M KST'), 'mode': MODE},
        'news': news, 'markets': m, 'commodities': com, 'crypto': crd, 'analysis': an,
        'securities': sec, 'global_securities': gs, 'berkshire': n2.get('berkshire', {}), 'ai_trends': n2.get('ai_trends', {})}
os.makedirs(os.path.join(W, '_market_report_data'), exist_ok=True)
outp = os.path.join(W, '_market_report_data', f'report_data_{RD}.json')
json.dump(data, open(outp, 'w'), ensure_ascii=False, indent=1)
print('MERGED →', outp)
print('  sections:', [k for k in data])
print('  themes', len(trows), 'semi_stocks', len(ss), 'semi_etfs', len(se), '| longterm', len(ltu))
print('  korea_investors kospi:', m['korea_investors']['kospi'].get('comment', ''))
print('  leading:', m['korea_leading_comment'])
