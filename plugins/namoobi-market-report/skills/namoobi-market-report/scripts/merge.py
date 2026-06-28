#!/usr/bin/env python3
# merge.py (v3.7) — nmr_*.json 들을 report_data_YYYYMMDD.json 으로 병합 (Phase 3).
# 매 실행 즉석 작성하던 병합 로직을 결정적 스크립트로 베이크 (토큰·변동성 제거).
# 사용: python3 merge.py [WORK_DIR] [REPORT_DATE_YYYYMMDD]
#   WORK_DIR 없으면 cwd. REPORT_DATE 없으면 env NMR_DATE 또는 오늘(KST).
#   mode 는 env NMR_MODE(scheduled/normal) 또는 'normal'.
import json, os, sys, glob, datetime as dt

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
_CWROOT = (glob.glob('/sessions/*/mnt/claudeCowork/_market_report_data') or [os.path.join(W, '_market_report_data')])[0]
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
for i, x in enumerate(semi.get('semi_ai_stocks', [])[:10]):
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
m['hbm'] = LCF('nmr_hbm.json')  # 3.1.5 HBM 대시보드: gen_hbm_dashboard.py 오버라이드 + 캡션 asof/source (없으면 {} → 내장 예시·추정 사용)
# (req6) HBM eps_per -> eps_yearly (빌더 표 스키마)
try:
    _hb = m.get('hbm') or {}
    if isinstance(_hb, dict) and not _hb.get('eps_yearly') and isinstance(_hb.get('eps_per'), list):
        _ey=[]
        for _o in _hb['eps_per']:
            if not isinstance(_o, dict): continue
            _ey.append({'name': _o.get('company') or _o.get('name') or '-',
                'y2025_eps': _o.get('eps_2025'), 'y2025_per': _o.get('per_2025'),
                'y2026_eps': _o.get('eps_2026'), 'y2026_per': _o.get('per_2026'),
                'y2027_eps': _o.get('eps_2027'), 'y2027_per': _o.get('per_2027'),
                'y2028_eps': _o.get('eps_2028'), 'y2028_per': _o.get('per_2028'),
                'currency': _o.get('currency') or ''})
        if _ey: _hb['eps_yearly']=_ey; m['hbm']=_hb; print('  [req6] HBM eps_yearly 매핑:', len(_ey))
except Exception as _he: print('  [req6] hbm eps_yearly skip:', _he)

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
    ],
    "spx_fwd": {"fwd_eps": 330, "fwd_per": 22.7, "asof": "2026-06", "chart": "charts/macro_spx_fwd.png", "note": "출처: LSEG/Yardeni 공개치(월간 캐시) — 추정. 지수 7,500 / EPS 330 → 선행PER 22.7배로 정합"},
    "kospi_fwd": {"fwd_eps": 918, "fwd_per": 9.8, "asof": "2026-06", "chart": "charts/macro_kospi_fwd.png", "note": "출처: 연합인포맥스/WISEfn(월간 캐시) — 추정. 지수 9,000 / EPS 918 → 선행PER 9.8배로 정합"}
  }
}
''')
_mac = L('nmr_macro.json')
_macro = _mac.get('macro') if (isinstance(_mac, dict) and _mac.get('macro')) else (_mac if (isinstance(_mac, dict) and _mac) else None)
# v3.13.2 재발방지: 에이전트 nmr_macro 가 빌더(MACRO_DEFAULT) 구조를 못 맞추면(평면구조 rates.fed_funds=숫자·inflation.cpi_yoy 등) 무시하고 MACRO_DEFAULT 사용 → 3.1.1~3.1.5 빈표 방지
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
# (v3.43) 에이전트가 sentiment.rows(심리 6지표 골격)를 안 줘도 inflation/employment 를 살린다 — MACRO_DEFAULT 골격만 주입(merge가 VIX·DXY·KSVKOSPI·원달러·WTI·US10Y 라이브값 주입). spx_fwd/kospi_fwd 는 에이전트값 보존.
if not ((macro.get('sentiment') or {}).get('rows')):
    _sd = macro.setdefault('sentiment', {})
    _sd['rows'] = json.loads(json.dumps(MACRO_DEFAULT['sentiment']['rows']))
    for _fk in ('spx_fwd', 'kospi_fwd'):
        if not _sd.get(_fk): _sd[_fk] = MACRO_DEFAULT['sentiment'].get(_fk, {})
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
      ('NFP (비농업취업자 변화)', [], ['nfp','비농업'], [], '비농업 신규고용 — 시장이 가장 민감하게 반응하는 고용지표', '연준 금리경로·경기 침체/연착륙 판단에 직결', '신규고용 호조는 연착륙 신호지만 과열 시 금리인상 우려.'),
      ('실업률', ['실업'], [], [], '고용 건전성(연준 이중책무 핵심)', '상승=경기둔화·금리인하 명분 / 시장 민감', '실업률 상승은 인하 명분이 되어 단기 증시엔 양면적.'),
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
_macro_canon(macro)
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
        _vp = (glob.glob('/sessions/*/mnt/claudeCowork/_market_report_data/nmr_vkospi_history.json') or glob.glob(os.path.join(W,'_market_report_data','nmr_vkospi_history.json')) or [None])[0]
        if _vp:
            _vser = (json.load(open(_vp)).get('series') or [])
            if _vser: _vk = {'current': _vser[-1][1], 'trend': '캐시(CNBC .KSVKOSPI 일별누적)', 'anchors': _vser}
    except Exception: pass
for _r in ((macro.get('sentiment') or {}).get('rows') or []):
    if isinstance(_r, dict) and 'VKOSPI' in str(_r.get('name', '')).upper():
        _r['name'] = 'KSVKOSPI (KOSPI Volatility)'
        if _vk: _reuse(_r, _vk)
# (req10) VKOSPI 이력 DB(nmr_vkospi_history.json)에서 1주~1년·prev_pct(1일=D-1) 주입 → '-' 제거
try:
    _vh = LCF('nmr_vkospi_history.json')
    if not isinstance(_vh, dict):
        _vp2 = (glob.glob('/sessions/*/mnt/claudeCowork/_market_report_data/nmr_vkospi_history.json') or [None])[0]
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
_pr = L('nmr_policyrates.json')
if isinstance(_pr, dict) and _pr.get('policy_rates'):
    (macro.setdefault('rates', {}))['policy_rates'] = _pr['policy_rates']
# (REQ6/REQ5) 1년 금리차 차트·美10년물 실측 스파크 경로(생성 시 사용, 없으면 빌더가 자동 생략)
_rt = macro.get('rates') or {}
if isinstance(_rt.get('yield_curve'), dict): _rt['yield_curve']['chart'] = 'charts/macro_curve_1y.png'
if isinstance(_rt.get('us10y'), dict): _rt['us10y']['spark'] = 'charts/spark_us10y_v2.png'

m['us_etfs'] = ue
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
# [DB화] CAPEX 풀매트릭스 보강 — 표 actuals 우선 + 내장 컨센서스로 결측연도 채움 → 표·차트(2024~2029) 완전 일치
try:
    _CY=[2024,2025,2026,2027,2028,2029]
    _CCAP={"Microsoft":[44.5,64.6,190,215,235,255],"Amazon":[83,132,200,245,280,305],"Alphabet":[52.5,91.4,185,250,280,305],"Meta":[37.3,69.7,135,175,200,220],"Oracle":[7,21,55.7,92,95,100]}
    _CREV={"Microsoft":[245,282,329,384,455,535],"Amazon":[638,717,824,933,1064,1189],"Alphabet":[350,403,486,580,680,788],"Meta":[165,201,253,302,352,406],"Oracle":[53,57,67,89,104,120]}
    _CFCF={"Microsoft":[74,72,-31,-29,-15,4],"Alphabet":[73,73,13,-13,-3,16],"Meta":[54,46,11,-1,3,14],"Amazon":[33,8,-39,-63,-72,-73],"Oracle":[12,0,-24,-59,-57,-56]}
    _bc=m.get('bigtech_capex') or {}; _rows=_bc.get('rows') or []
    def _has(v): return v not in (None,'','-')
    for _r in _rows:
        _co=str(_r.get('company','')).split(' (')[0].strip()
        if _co not in _CCAP: continue
        for _i,_y in enumerate(_CY):
            if not _has(_r.get('y%d'%_y)):   _r['y%d'%_y]=_CCAP[_co][_i]
            if not _has(_r.get('rev%d'%_y)): _r['rev%d'%_y]=_CREV[_co][_i]
            if not _has(_r.get('fcf%d'%_y)): _r['fcf%d'%_y]=_CFCF[_co][_i]
            try: _r['ratio%d'%_y]=round(100*float(_r['y%d'%_y])/float(_r['rev%d'%_y]))
            except Exception: pass
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
m['us_credit'] = um.get('us_credit', {}); m['us_treasury_curve'] = um.get('us_treasury_curve')
uc = um.get('us_credit', {})
m['hy_spread'] = {'current': uc.get('hy_oas'), 'hy_oas': uc.get('hy_oas'), 'hy_yield': uc.get('hy_yield'),
                  'implied_ust': uc.get('implied_ust'), 'comment': uc.get('comment'), 'chart': 'charts/hy_oas.png'}
# (fix) HY 1주~1년 OAS 히스토리 (nmr_hy_series.json 월별) — 3.2.3 의 1주/1개월~1년 열이 '-' 이던 문제
_hys = L('nmr_hy_series.json'); _hser = (_hys.get('series') if isinstance(_hys, dict) else _hys) or []
_hpts = sorted([(dt.date.fromisoformat(str(d)[:10]), float(v)) for d, v in _hser if v is not None])
if len(_hpts) >= 2:
    _last = _hpts[-1][0]
    m['hy_spread']['d1'] = round(_hpts[-2][1], 2)
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
    _mc.setdefault('inflation', {})['rows'] = _ndb.sync('inflation', _ir, _today, _mx(_ir, ['asof', 'release']) or _run_m, _dd)
    _er = (_mc.get('employment') or {}).get('rows')
    _mc.setdefault('employment', {})['rows'] = _ndb.sync('employment', _er, _today, _mx(_er, ['asof', 'release']) or _run_m, _dd)
    _rt['policy_rates'] = _ndb.sync('policy_rates', _rt.get('policy_rates'), _today, _run_m, _dd)
    _rt['fomc_meetings'] = _ndb.sync('fomc_meetings', _rt.get('fomc_meetings'), _today, _mx(_rt.get('fomc_meetings'), ['date']) or _run_m, _dd)
    _dp = m.get('fomc_dotplot') or {}
    m['fomc_dotplot'] = _ndb.sync('dot_plot', _dp, _today, (_dp.get('fomc_sep_date') or _run_m), _dd)
    m['korea_leading'] = _ndb.sync('leading', m.get('korea_leading'), _today, _mx(m.get('korea_leading'), ['period']) or _run_m, _dd)
    print('  [DB] 비매일 섹션 동기화: inflation/employment/policy_rates/fomc_meetings/dot_plot/leading -> db/')
except Exception as _dbe:
    print('  [DB] 동기화 skip(비차단):', _dbe)
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
        if _src:
            _o['current'] = _src['current']; _o['prev_close'] = _src['prev_close']
            _o['chg'] = round(_src['current'] - _src['prev_close'], 3)
            for _hk in ('1d_pct','prev_pct','1w_pct','1mo_pct','3mo_pct','6mo_pct','1y_pct'):
                _o[_hk] = _src.get(_hk)
        # 대전제: 현재가셀=1d_pct(D0 전일대비), '1일'컬럼=prev_pct(D-1 일간변동) — 구분 유지
        _o['spark'] = 'charts/spark_%s.png' % _bk
        _o['trend'] = _ko_trend_bond(_o)
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
        _senf = macro.get('sentiment') or {}
        if isinstance(_senf.get('spx_fwd'), dict): _senf['spx_fwd']['chart'] = 'charts/fwd3_spx.png'
        if isinstance(_senf.get('kospi_fwd'), dict): _senf['kospi_fwd']['chart'] = 'charts/fwd3_kospi.png'
        print('  [R4] 차트경로 강제: inflation/employment/spx_fwd/kospi_fwd')
    except Exception as _ce: print('  [R4] 차트경로 강제 skip:', _ce)
    print('  [R4] 국채 단일소스 강제: us10y', _rates_fin.get('us10y',{}).get('current'),
          '1d', _rates_fin.get('us10y',{}).get('1d_pct'),
          '| us2y', _rates_fin.get('us2y',{}).get('current'),
          '1d', _rates_fin.get('us2y',{}).get('1d_pct'))
except Exception as _e:
    print('  [R4] 국채 단일소스 강제 skip(비차단):', _e)

outp = os.path.join(W, '_market_report_data', f'report_data_{RD}.json')
json.dump(data, open(outp, 'w'), ensure_ascii=False, indent=1)
print('MERGED →', outp)
print('  sections:', [k for k in data])
print('  themes', len(trows), 'semi_stocks', len(ss), 'semi_etfs', len(se), '| longterm', len(ltu))
print('  korea_investors kospi:', m['korea_investors']['kospi'].get('comment', ''))
print('  leading:', m['korea_leading_comment'])
