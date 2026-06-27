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
m['hbm'] = L('nmr_hbm.json')  # 3.1.5 HBM 대시보드: gen_hbm_dashboard.py 오버라이드 + 캡션 asof/source (없으면 {} → 내장 예시·추정 사용)

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
      {"name": "원/달러 환율", "current": 1380, "1w_pct": 0.2, "1mo_pct": 0.5, "3mo_pct": 1.0, "6mo_pct": 1.5, "1y_pct": 2.0, "trend": "원화 약세(추정)", "spark": "charts/spark_usdkrw.png", "meaning": "외국인 수급 영향", "use": "1,400원↑ → 외국인 이탈 가속"},
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
        return isinstance(_r.get('fed_funds'), dict) and bool((mm.get('inflation') or {}).get('rows')) and bool((mm.get('employment') or {}).get('rows')) and bool((mm.get('sentiment') or {}).get('rows'))
    except Exception:
        return False
if _macro and not _macro_ok(_macro):
    print('  [macro] nmr_macro 구조 불일치(rates.fed_funds 가 dict 아님/rows 비어있음) -> MACRO_DEFAULT 폴백')
    _macro = None
macro = _macro if _macro else json.loads(json.dumps(MACRO_DEFAULT))
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
for _r in ((macro.get('sentiment') or {}).get('rows') or []):
    if isinstance(_r, dict) and 'VKOSPI' in str(_r.get('name', '')).upper():
        _r['name'] = 'KSVKOSPI (KOSPI Volatility)'
        if _vk: _reuse(_r, _vk)
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
