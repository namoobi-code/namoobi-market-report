#!/usr/bin/env python3
# gen_macro2.py — 측정치 매크로 차트(정책금리 6국·물가5·고용6·BEI·곡선 sparse·선행EPS)
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
m2=L('nmr_macro2.json'); rh=L('nmr_ratehist.json'); mac=L('nmr_macro.json'); S=(mac.get('macro',mac).get('series') or {})
B="#1E40AF";R="#DC2626";G="#059669"
def mlab(n,ey=2026,em=5):
    o=[];y,mm=ey,em
    for _ in range(n):
        o.append(dt.date(y,mm,1)); mm-=1
        if mm<1: mm=12;y-=1
    return list(reversed(o))
# (1) policy 6-country
labels=rh.get('labels') or []
if labels:
    xs=[dt.datetime.strptime(l,'%Y-%m') for l in labels]
    fig,ax=plt.subplots(figsize=(7.4,3.0),dpi=150)
    cm={'US':('미국',B),'KR':('한국',G),'JP':('일본','#D97706'),'CN':('중국','#7C3AED'),'EU':('유로존','#0891B2'),'UK':('영국','#BE185D')}
    for k,(nm,c) in cm.items():
        v=rh.get(k)
        if v and len(v)==len(xs): ax.plot(xs,v,lw=1.5,marker='o',ms=2.3,label=nm,color=c)
    ax.set_title('주요 6개국 기준금리 추이 (2021~2026, 각국 중앙은행 실측)',fontsize=9.5,color='#334155')
    ax.legend(fontsize=7,ncol=6,loc='upper center',bbox_to_anchor=(0.5,-0.12)); ax.grid(alpha=0.25); ax.set_ylabel('%',fontsize=8,color='#64748B')
    ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    for s in ['top','right']: ax.spines[s].set_visible(False)
    plt.tight_layout(); plt.savefig('charts/macro_policy_rates.png',bbox_inches='tight'); plt.close()
# (2) inflation 5
infl=(m2.get('series') or {}).get('inflation') or {}
disp=[('CPI','CPI'),('Core_CPI','Core CPI'),('PCE','PCE'),('Core_PCE','Core PCE'),('PPI','PPI')]
fig,ax=plt.subplots(figsize=(7.4,2.9),dpi=150); drew=False
for k,lab in disp:
    v=[x for x in (infl.get(k) or []) if x is not None]
    if len(v)>=2: ax.plot(mlab(len(v)),v,lw=1.6,marker='o',ms=3,label=lab); drew=True
ax.axhline(2.0,color=R,lw=0.9,ls='--',alpha=0.6)
ax.set_title('미국 물가 YoY 추이 (최신 2026-05, BLS/BEA 실측)',fontsize=9.5,color='#334155')
if drew: ax.legend(fontsize=7,ncol=5)
ax.grid(alpha=0.25); ax.set_ylabel('YoY %',fontsize=8,color='#64748B'); ax.xaxis.set_major_formatter(mdates.DateFormatter('%y/%m'))
for s in ['top','right']: ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig('charts/macro_inflation.png',bbox_inches='tight'); plt.close()
# (3) employment 6 panels
emp=(m2.get('series') or {}).get('employment') or {}
pn=[('NFP 신규고용(천명)','nfp',B,0),('실업률(%)','unemp',R,None),('GDP 연율(%)','gdp',G,None),('ISM 제조 PMI','ism_mfg',B,50),('ISM 서비스 PMI','ism_svc',G,50),('소매판매 MoM(%)','retail','#7C3AED',0)]
av=[(t,[x for x in (emp.get(k) or []) if x is not None],c,hl) for t,k,c,hl in pn]
av=[p for p in av if len(p[1])>=2]
nc=3; nr=max(1,(len(av)+2)//3); fig,axs=plt.subplots(nr,nc,figsize=(2.6*nc,2.4*nr),dpi=150)
axs=list(axs.flatten()) if hasattr(axs,'flatten') else [axs]
for i,(t,v,c,hl) in enumerate(av):
    ax=axs[i]; ax.plot(range(len(v)),v,color=c,lw=1.5,marker='o',ms=2.5); ax.scatter([len(v)-1],[v[-1]],color=R,s=12,zorder=5)
    if hl is not None: ax.axhline(hl,color=R,lw=0.8,ls='--',alpha=0.6)
    ax.set_title(t,fontsize=8,color='#334155'); ax.grid(alpha=0.2); ax.set_xticks([])
    for s in ['top','right']: ax.spines[s].set_visible(False)
for j in range(len(av),len(axs)): axs[j].axis('off')
fig.suptitle('미국 고용·경기 6개 지표 (최신 2026-05, BLS/BEA/ISM 실측)',fontsize=9.5,color='#334155')
plt.tight_layout(rect=[0,0,1,0.94]); plt.savefig('charts/macro_employment.png',bbox_inches='tight'); plt.close()
# (4) BEI
bei=[x for x in ((m2.get('series') or {}).get('infl_exp') or []) if x is not None]
if len(bei)>=2:
    fig,ax=plt.subplots(figsize=(7.2,1.95),dpi=150); ax.plot(mlab(len(bei)),bei,color=B,lw=1.8,marker='o',ms=3); ax.axhline(2.0,color=R,lw=0.9,ls='--',alpha=0.6)
    ax.set_title('기대인플레이션 10년(BEI) 추이 · 점선=2% (FRED T10YIE 실측)',fontsize=8.8,color='#334155')
    ax.grid(alpha=0.25); ax.set_ylabel('%',fontsize=8,color='#64748B'); ax.xaxis.set_major_formatter(mdates.DateFormatter('%y/%m'))
    for s in ['top','right']: ax.spines[s].set_visible(False)
    plt.tight_layout(); plt.savefig('charts/macro_infl_exp.png',bbox_inches='tight'); plt.close()
# (5) curve sparse-x
cl=S.get('curve_labels') or []; cv=S.get('curve_10_2') or []
pts=[(dt.date.fromisoformat(str(d)),v) for d,v in zip(cl,cv) if v is not None]
if len(pts)>=2:
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]; col=G if ys[-1]>=0 else R
    fig,ax=plt.subplots(figsize=(7.2,2.3),dpi=150); ax.axhline(0,color='#9ca3af',lw=0.8,ls='--')
    ax.plot(xs,ys,color=col,lw=1.2); ax.fill_between(xs,ys,0,color=col,alpha=0.08)
    ax.set_title('미국 장단기 금리차(10Y-2Y) %d~%d 일별 실측 — 현재 %+.2f%%p'%(xs[0].year,xs[-1].year,ys[-1]),fontsize=9,color='#334155')
    ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y')); ax.grid(alpha=0.2); ax.set_ylabel('%p',fontsize=8,color='#64748B')
    for s in ['top','right']: ax.spines[s].set_visible(False)
    plt.tight_layout(); plt.savefig('charts/macro_curve.png',bbox_inches='tight'); plt.close()
# (6) spx fwd
sf=m2.get('spx_fwd') or {}; se=[x for x in ((m2.get('series') or {}).get('spx_eps') or []) if x is not None]; si=[x for x in ((m2.get('series') or {}).get('spx_idx') or []) if x is not None]
if sf.get('fwd_eps'):
    if len(se)>=2 and len(se)==len(si):
        x=mlab(len(se)); fig,ax=plt.subplots(figsize=(7.2,2.4),dpi=150); ax.bar(x,se,width=18,color='#93C5FD',label='12M Fwd EPS'); ax.set_ylabel('Fwd EPS($)',fontsize=8,color=B)
        ax2=ax.twinx(); ax2.plot(x,si,color=B,lw=2,marker='o',ms=3,label='지수'); ax2.set_ylabel('지수',fontsize=8,color=B)
        ax.set_title('S&P500 12M 선행EPS·지수 (FactSet 실측, 선행P/E %.1fx)'%sf.get('fwd_per',0),fontsize=9,color='#334155'); ax.xaxis.set_major_formatter(mdates.DateFormatter('%y/%m'))
        for s in ['top']: ax.spines[s].set_visible(False)
        plt.tight_layout(); plt.savefig('charts/macro_spx_fwd.png',bbox_inches='tight'); plt.close()
    elif len(si)>=2:
        x=mlab(len(si)); fig,ax=plt.subplots(figsize=(7.2,2.4),dpi=150); ax.plot(x,si,color=B,lw=2,marker='o',ms=3)
        ax.set_title('S&P500 지수 추이(24개월) · 현재 선행 P/E %.1fx · 선행EPS $%.1f (FactSet 실측)'%(sf.get('fwd_per',0),sf.get('fwd_eps',0)),fontsize=9,color='#334155')
        ax.grid(alpha=0.25); ax.xaxis.set_major_formatter(mdates.DateFormatter('%y/%m'))
        for s2 in ['top','right']: ax.spines[s2].set_visible(False)
        plt.tight_layout(); plt.savefig('charts/macro_spx_fwd.png',bbox_inches='tight'); plt.close()
    else:
        fig,ax=plt.subplots(figsize=(7.2,1.3),dpi=150); ax.axis('off')
        ax.text(0.5,0.5,'S&P500 12M 선행 P/E %.1fx · 선행EPS $%.1f · 지수 %.0f (FactSet 실측, %s)'%(sf.get('fwd_per',0),sf.get('fwd_eps',0),sf.get('idx',0),sf.get('asof','')),ha='center',va='center',fontsize=11,color=B)
        plt.tight_layout(); plt.savefig('charts/macro_spx_fwd.png',bbox_inches='tight'); plt.close()
print('gen_macro2 done')
