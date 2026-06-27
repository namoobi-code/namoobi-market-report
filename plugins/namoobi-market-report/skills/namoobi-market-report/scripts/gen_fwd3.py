#!/usr/bin/env python3
# 3.1.5 — 지수/12M 선행EPS/선행PER 를 '하나의 그래프'에 3중 Y축으로 합쳐서 표시.
# 데이터 출처: nmr_fwd_history.json (매일 누적되는 DB). 지수 = 선행EPS x 선행PER (에이전트 산식과 동일하게 복원 → 전구간 표시).
import json,os,sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
W=sys.argv[1] if len(sys.argv)>1 else '.'
FP=os.path.join(W,'fonts','nmr_kr.ttf')
try: fm.fontManager.addfont(FP); plt.rcParams['font.family']=fm.FontProperties(fname=FP).get_name()
except Exception: pass
plt.rcParams['axes.unicode_minus']=False
def L(f):
    try: return json.load(open(os.path.join(W,f)))
    except Exception: return {}
def pad(a,lo=0.12,hi=0.18):
    mn,mx=min(a),max(a); r=mx-mn
    if r<=0: return mn*0.9, mx*1.1
    return mn-r*lo, mx+r*hi
def chart(series,name,out,unit):
    s=[x for x in (series or []) if x.get('fwd_eps') is not None and x.get('fwd_per')]
    s=sorted(s,key=lambda z:z['date'])
    if len(s)<2: print('skip',name,len(s)); return
    dates=[x['date'] for x in s]; eps=[float(x['fwd_eps']) for x in s]; per=[float(x['fwd_per']) for x in s]
    idx=[e*p for e,p in zip(eps,per)]; xs=list(range(len(dates)))
    C_IDX='#1E3A8A'; C_EPS='#D97706'; C_PER='#059669'
    fig,ax=plt.subplots(figsize=(11.6,5.8))
    l1=ax.plot(xs,idx,'-o',color=C_IDX,lw=2.6,ms=5.5,label='지수 (pt)',zorder=4)
    ax.set_ylabel('지수 (pt)',color=C_IDX,fontsize=11,fontweight='bold'); ax.tick_params(axis='y',labelcolor=C_IDX)
    ax.set_ylim(*pad(idx))
    ax2=ax.twinx(); l2=ax2.plot(xs,eps,'-s',color=C_EPS,lw=2.3,ms=5,label='12M 선행 EPS ('+unit+')',zorder=4)
    ax2.set_ylabel('12M 선행 EPS ('+unit+')',color=C_EPS,fontsize=11,fontweight='bold'); ax2.tick_params(axis='y',labelcolor=C_EPS); ax2.set_ylim(*pad(eps))
    ax3=ax.twinx(); ax3.spines['right'].set_position(('outward',62))
    l3=ax3.plot(xs,per,'-^',color=C_PER,lw=2.1,ms=5,label='선행 PER (배)',zorder=4)
    ax3.set_ylabel('선행 PER (배)',color=C_PER,fontsize=11,fontweight='bold'); ax3.tick_params(axis='y',labelcolor=C_PER); ax3.set_ylim(*pad(per))
    step=max(1,(len(dates)+11)//12)
    ax.set_xticks(xs[::step]); ax.set_xticklabels([dates[i] for i in xs[::step]],rotation=45,ha='right',fontsize=9)
    ax.set_xlim(-0.5,len(dates)-0.5); ax.grid(axis='both',ls=':',alpha=0.30,zorder=0)
    for i,(c,arr,ax_,fmt) in enumerate([(C_IDX,idx,ax,'{:,.0f}'),(C_EPS,eps,ax2,'{:,.1f}'),(C_PER,per,ax3,'{:.1f}')]):
        for j in (0,len(xs)-1):
            ax_.annotate(fmt.format(arr[j]),(xs[j],arr[j]),color=c,fontsize=8.2,fontweight='bold',
                         xytext=(0,9 if i!=2 else -13),textcoords='offset points',ha='center')
    ax.set_title(name+' · 지수 / 12M 선행 EPS / 선행 PER  (월말 · 동일 날짜축)',fontsize=13,fontweight='bold',pad=12)
    lns=l1+l2+l3; ax.legend(lns,[x.get_label() for x in lns],loc='upper left',fontsize=9.5,framealpha=0.92,ncol=3)
    fig.tight_layout(); os.makedirs(os.path.join(W,'charts'),exist_ok=True)
    fig.savefig(os.path.join(W,out),dpi=125,bbox_inches='tight'); plt.close(fig)
    print(name,'combined ok',len(s),'pts  idx',round(idx[-1]),'eps',eps[-1],'per',per[-1])
_h=L('nmr_fwd_history.json')
_spx=_h.get('spx') or (L('nmr_spx_fwd_series.json').get('series') or [])
_kospi=_h.get('kospi') or (L('nmr_kospi_fwd_series.json').get('series') or [])
chart(_spx,'S&P500','charts/fwd3_spx.png','$')
chart(_kospi,'KOSPI','charts/fwd3_kospi.png','p')
