#!/usr/bin/env python3
# gen_curve_1y.py — 3.1.1 미국 장단기 금리차(10Y-2Y) 최근 1년 차트 + 美10년물 1년 스파크
# 출력: charts/macro_curve_1y.png, charts/spark_us10y_v2.png
# 입력 우선순위(차트): FRED T10Y2Y(일별 1년) → nmr_macro.json curve_10_2(FMP 월별 13개월) → 기존 macro_curve.png 복사
import json, os, sys, glob, datetime as dt, time, shutil, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt, matplotlib.font_manager as fm, matplotlib.dates as mdates
O=sys.argv[1] if (len(sys.argv)>1 and os.path.isdir(sys.argv[1])) else (os.environ.get('NMR_OUT') or (sorted(glob.glob('/sessions/*/mnt/outputs'))[-1] if glob.glob('/sessions/*/mnt/outputs') else '.'))
_f=[p for p in [os.path.join(os.path.dirname(__file__),'fonts','nmr_kr.ttf'),'fonts/nmr_kr.ttf',O+'/fonts/nmr_kr.ttf'] if os.path.exists(p)]
if _f: fm.fontManager.addfont(_f[0]); matplotlib.rcParams['font.family']='NanumBarunGothic'
matplotlib.rcParams['axes.unicode_minus']=False
os.makedirs('charts',exist_ok=True)
def fred(sid):
    # v3.16: FRED API 키(SECURITY/secrets.env) 직접 호출 우선 → fredgraph.csv 폴백 (nmr_fred 공용 헬퍼)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from nmr_fred import fred_series
    s = fred_series(sid, start=(dt.date.today()-dt.timedelta(days=380)).isoformat())
    out=[]
    for d,v in s:
        try: out.append((dt.date.fromisoformat(d),float(v)))
        except: pass
    return out or None
def load(p):
    try: return json.load(open(p))
    except Exception: return None
cut=dt.date.today()-dt.timedelta(days=370); spread=None; done=False
t=fred('T10Y2Y')
if t:
    t=[x for x in t if x[0]>=cut]
    if len(t)>=2:
        xs=[d for d,_ in t]; ys=[v for _,v in t]; spread=ys[-1]; col='#059669' if ys[-1]>=0 else '#DC2626'
        fig,ax=plt.subplots(figsize=(6.5,2.6),dpi=150); ax.axhline(0,color='#9ca3af',lw=0.8,ls='--')
        ax.plot(xs,ys,color=col,lw=1.4); ax.fill_between(xs,ys,0,color=col,alpha=0.08)
        ax.set_title('미국 장단기 금리차(10Y-2Y) 최근 1년 — 현재 %+.2f%%p (FRED T10Y2Y, 일별)'%ys[-1],fontsize=9)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%y/%m')); ax.grid(alpha=0.2); ax.tick_params(labelsize=7)
        for s in ['top','right']: ax.spines[s].set_visible(False)
        plt.tight_layout(); plt.savefig('charts/macro_curve_1y.png',bbox_inches='tight'); plt.close(); done=True; print('curve FRED', len(t))
if not done:
    mm=load(O+'/nmr_macro.json') or load(O+'/_nmr_macro_agent.json') or {}
    mac=mm.get('macro',mm) if isinstance(mm,dict) else {}
    s=(mac.get('series') or {}).get('curve_10_2') or []; pts=[]
    for d,v in s:
        try: pts.append((dt.datetime.strptime(str(d)[:7],'%Y-%m'),float(v)))
        except: pass
    pts=pts[-13:]
    if len(pts)>=2:
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]; spread=ys[-1]; col='#059669' if ys[-1]>=0 else '#DC2626'
        fig,ax=plt.subplots(figsize=(6.5,2.6),dpi=150); ax.axhline(0,color='#9ca3af',lw=0.8,ls='--')
        ax.plot(xs,ys,color=col,lw=1.5,marker='o',ms=3); ax.fill_between(xs,ys,0,color=col,alpha=0.08)
        ax.set_title('미국 장단기 금리차(10Y-2Y) 최근 1년 — 현재 %+.2f%%p (FMP 월별 실측)'%ys[-1],fontsize=9)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%y/%m')); ax.grid(alpha=0.2); ax.tick_params(labelsize=7)
        for s2 in ['top','right']: ax.spines[s2].set_visible(False)
        plt.tight_layout(); plt.savefig('charts/macro_curve_1y.png',bbox_inches='tight'); plt.close(); done=True; print('curve FMP', len(pts))
if not done and os.path.exists('charts/macro_curve.png'):
    shutil.copy('charts/macro_curve.png','charts/macro_curve_1y.png'); done=True; print('curve copied fallback')
idx=load(O+'/nmr_indexseries.json') or {}; us=[v for d,v in (idx.get('us10y') or []) if v is not None]
if len(us)>=2:
    c='#059669' if us[-1]>=us[0] else '#DC2626'
    fig,ax=plt.subplots(figsize=(2.4,0.7),dpi=150); ax.plot(range(len(us)),us,color=c,lw=1.3)
    ax.fill_between(range(len(us)),us,min(us),color=c,alpha=0.10); ax.axis('off'); ax.margins(x=0,y=0.12)
    plt.tight_layout(pad=0.1); plt.savefig('charts/spark_us10y_v2.png',bbox_inches='tight',transparent=True); plt.close(); print('us10y spark', len(us))
print('gen_curve_1y done spread=',spread)
