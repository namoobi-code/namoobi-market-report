#!/usr/bin/env python3
# 3.1.5 통합차트 — 지수=일일선(실측 일봉), 12M 선행EPS·PER=조사 시점(sparse) 마커. 하나의 그래프 3중 Y축.
import json,os,sys,datetime as dt
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager as fm
W=sys.argv[1] if len(sys.argv)>1 else '.'
try: fm.fontManager.addfont(W+'/fonts/nmr_kr.ttf'); plt.rcParams['font.family']=fm.FontProperties(fname=W+'/fonts/nmr_kr.ttf').get_name()
except Exception: pass
plt.rcParams['axes.unicode_minus']=False
def L(f):
    try: return json.load(open(os.path.join(W,f)))
    except Exception: return {}
def D(s): return dt.datetime.strptime((s[:10] if len(s)>7 else s+'-15'),'%Y-%m-%d')
def pad(a,lo=0.10,hi=0.16):
    mn,mx=min(a),max(a); r=(mx-mn) or (abs(mx) or 1)*0.1; return mn-r*lo,mx+r*hi
def chart(daily,pts,name,out,unit):
    pts=[x for x in (pts or []) if x.get('eps') and x.get('per')]
    pts=sorted(pts,key=lambda z:z.get('eps_date') or z['date'])
    if not daily or len(pts)<2: print('skip',name); return
    start=D(pts[0].get('eps_date') or pts[0]['date'])-dt.timedelta(days=20)
    dl=[(dt.datetime.strptime(d,'%Y-%m-%d'),c) for d,c in daily]
    dl=[(a,b) for a,b in dl if a>=start]
    dx=[a for a,_ in dl]; dy=[b for _,b in dl]
    ed=[D(p.get('eps_date') or p['date']) for p in pts]; ev=[p['eps'] for p in pts]
    pdt=[D(p.get('per_date') or p['date']) for p in pts]; pv=[p['per'] for p in pts]
    C_IDX='#1E3A8A'; C_EPS='#D97706'; C_PER='#059669'
    fig,ax=plt.subplots(figsize=(11.6,5.8))
    l1=ax.plot(dx,dy,'-',color=C_IDX,lw=1.6,label='지수 (일봉·실측)',zorder=3)
    ax.set_ylabel('지수 (pt)',color=C_IDX,fontsize=11,fontweight='bold'); ax.tick_params(axis='y',labelcolor=C_IDX); ax.set_ylim(*pad(dy))
    ax2=ax.twinx(); l2=ax2.plot(ed,ev,'-s',color=C_EPS,lw=2.0,ms=6,label='12M 선행 EPS ('+unit+')',zorder=4)
    ax2.set_ylabel('12M 선행 EPS ('+unit+')',color=C_EPS,fontsize=11,fontweight='bold'); ax2.tick_params(axis='y',labelcolor=C_EPS); ax2.set_ylim(*pad(ev))
    ax3=ax.twinx(); ax3.spines['right'].set_position(('outward',62))
    l3=ax3.plot(pdt,pv,'-^',color=C_PER,lw=1.8,ms=6,label='선행 PER (배)',zorder=4)
    ax3.set_ylabel('선행 PER (배)',color=C_PER,fontsize=11,fontweight='bold'); ax3.tick_params(axis='y',labelcolor=C_PER); ax3.set_ylim(*pad(pv))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2)); ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    for lab in ax.get_xticklabels(): lab.set_rotation(45); lab.set_ha('right'); lab.set_fontsize(9)
    ax.grid(axis='both',ls=':',alpha=0.3)
    ax.annotate(f'{dy[-1]:,.0f}',(dx[-1],dy[-1]),color=C_IDX,fontsize=8.5,fontweight='bold',xytext=(2,6),textcoords='offset points')
    ax2.annotate(f'{ev[-1]:,.1f}',(ed[-1],ev[-1]),color=C_EPS,fontsize=8.5,fontweight='bold',xytext=(2,7),textcoords='offset points')
    ax3.annotate(f'{pv[-1]:.1f}',(pdt[-1],pv[-1]),color=C_PER,fontsize=8.5,fontweight='bold',xytext=(2,-13),textcoords='offset points')
    ax.set_title(name+' · 일일 지수 + 12M 선행 EPS·PER (실적 vs 밸류)',fontsize=13,fontweight='bold',pad=12)
    lns=l1+l2+l3; ax.legend(lns,[x.get_label() for x in lns],loc='upper left',fontsize=9.5,framealpha=0.92,ncol=3)
    fig.tight_layout(); os.makedirs(os.path.join(W,'charts'),exist_ok=True)
    fig.savefig(os.path.join(W,out),dpi=125,bbox_inches='tight'); plt.close(fig)
    print(name,'daily-chart ok  idx_days',len(dx),'eps_pts',len(ev))
idl=L('nmr_idx_daily.json'); h=L('nmr_fwd_history.json')
chart(idl.get('spx'),h.get('spx'),'S&P500','charts/fwd3_spx.png','$')
chart(idl.get('kospi'),h.get('kospi'),'KOSPI','charts/fwd3_kospi.png','p')
