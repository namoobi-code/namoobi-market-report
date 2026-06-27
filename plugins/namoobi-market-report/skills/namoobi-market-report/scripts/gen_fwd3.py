#!/usr/bin/env python3
# 3.1.5 3단(지수/12M 선행EPS/선행PER) 공유축 차트. 출력 charts/fwd3_spx.png, fwd3_kospi.png
import json,os,sys,datetime as dt,matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt, matplotlib.font_manager as fm, matplotlib.dates as mdates
O=sys.argv[1] if (len(sys.argv)>1 and os.path.isdir(sys.argv[1])) else (os.environ.get('NMR_OUT') or '.')
_f=[p for p in [O+'/fonts/nmr_kr.ttf','fonts/nmr_kr.ttf'] if os.path.exists(p)]
if _f: fm.fontManager.addfont(_f[0]); matplotlib.rcParams['font.family']='NanumBarunGothic'
matplotlib.rcParams['axes.unicode_minus']=False
os.makedirs('charts',exist_ok=True)
def L(p):
    try: return json.load(open(os.path.join(O,p),encoding='utf-8'))
    except Exception: return {}
B="#1E40AF";R="#DC2626";GR="#059669"
idxs=L('nmr_indexseries.json')
def md(m): return dt.datetime.strptime(str(m)[:7],'%Y-%m')
def tier(sfile,idx_key,name,out,unit):
    s=[x for x in (L(sfile).get('series') or []) if x.get('fwd_eps') is not None]
    if len(s)<2: print('skip',name,'(<2pts)'); return
    de=[md(x['date']) for x in s]; eps=[x['fwd_eps'] for x in s]; per=[x.get('fwd_per') for x in s]
    idx=[(dt.date.fromisoformat(str(d)[:10]),v) for d,v in (idxs.get(idx_key) or []) if v is not None]
    fig,(a1,a2,a3)=plt.subplots(3,1,figsize=(7.2,5.4),dpi=150,sharex=True,gridspec_kw={'hspace':0.16,'height_ratios':[1,1,1]})
    if idx: a1.plot([d for d,_ in idx],[v for _,v in idx],color=B,lw=1.6)
    a1.set_ylabel('지수',fontsize=8,color=B); a1.set_title(name+' — 지수 · 12M 선행EPS · 선행PER (월말 공유축, %d포인트)'%len(s),fontsize=9.3,color='#334155'); a1.grid(alpha=0.2)
    a2.plot(de,eps,color=GR,lw=1.7,marker='o',ms=3.5); a2.set_ylabel('선행EPS(%s)'%unit,fontsize=8,color=GR); a2.grid(alpha=0.2)
    a2.annotate(('%s'%eps[-1]),(de[-1],eps[-1]),textcoords='offset points',xytext=(-4,6),fontsize=8,color=GR,fontweight='bold')
    pv=[(de[i],per[i]) for i in range(len(per)) if per[i] is not None]
    if pv:
        a3.plot([d for d,_ in pv],[v for _,v in pv],color=R,lw=1.7,marker='s',ms=3.5)
        a3.annotate(('%.1f배'%pv[-1][1]),pv[-1],textcoords='offset points',xytext=(-6,6),fontsize=8,color=R,fontweight='bold')
    a3.set_ylabel('선행PER(배)',fontsize=8,color=R); a3.grid(alpha=0.2)
    a3.xaxis.set_major_locator(mdates.MonthLocator(interval=2)); a3.xaxis.set_major_formatter(mdates.DateFormatter('%y/%m'))
    for ax in (a1,a2,a3):
        for sp in ['top','right']: ax.spines[sp].set_visible(False)
    plt.savefig(out,bbox_inches='tight'); plt.close(); print(name,'3tier ok',len(s),'pts')
tier('nmr_spx_fwd_series.json','sp500','S&P500','charts/fwd3_spx.png','$')
tier('nmr_kospi_fwd_series.json','kospi','KOSPI','charts/fwd3_kospi.png','p')
