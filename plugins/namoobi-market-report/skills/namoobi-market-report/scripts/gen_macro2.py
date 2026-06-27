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
ax.set_title('미국 물가 YoY 추이 (최신, BLS/BEA 실측)',fontsize=9.5,color='#334155')
if drew: ax.legend(fontsize=7,ncol=5)
ax.grid(alpha=0.25); ax.set_ylabel('YoY %',fontsize=8,color='#64748B'); ax.xaxis.set_major_formatter(mdates.DateFormatter('%y/%m'))
for s in ['top','right']: ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig('charts/macro_inflation.png',bbox_inches='tight'); plt.close()
# (3) employment 6 panels
emp=(m2.get('series') or {}).get('employment') or {}
gd=L('nmr_gdp.json'); gdpv=[v for _,v in (gd.get('gdp_growth') or []) if v is not None]
pn=[('① NFP 신규고용(천명)','nfp',B,0),('② 실업률(%)','unemp',R,None),('③ 소매판매 MoM(%)','retail','#7C3AED',0),('④ ISM 제조 PMI','ism_mfg',B,50),('⑤ ISM 서비스 PMI','ism_svc',G,50)]
av=[(t,[x for x in (emp.get(k) or []) if x is not None],c,hl) for t,k,c,hl in pn]
if len(gdpv)>=2: av.append(('⑥ 실질 GDP 연율(%)',gdpv,G,0))
av=[p for p in av if len(p[1])>=2]
nc=3; nr=max(1,(len(av)+2)//3); fig,axs=plt.subplots(nr,nc,figsize=(2.6*nc,2.4*nr),dpi=150)
axs=list(axs.flatten()) if hasattr(axs,'flatten') else [axs]
for i,(t,v,c,hl) in enumerate(av):
    ax=axs[i]; ax.plot(range(len(v)),v,color=c,lw=1.5,marker='o',ms=2.5); ax.scatter([len(v)-1],[v[-1]],color=R,s=12,zorder=5)
    if hl is not None: ax.axhline(hl,color=R,lw=0.8,ls='--',alpha=0.6)
    ax.set_title(t,fontsize=8,color='#334155'); ax.grid(alpha=0.2); ax.set_xticks([])
    for s in ['top','right']: ax.spines[s].set_visible(False)
for j in range(len(av),len(axs)): axs[j].axis('off')
fig.suptitle('미국 고용·경기 6개 지표 — 주식 관점 중요도 순 (실측)',fontsize=9.5,color='#334155')
plt.tight_layout(rect=[0,0,1,0.94]); plt.savefig('charts/macro_employment.png',bbox_inches='tight'); plt.close()
# (4) BEI
bd=L('nmr_bei_daily.json'); daily=(bd.get('daily') if isinstance(bd,dict) else None) or []
_infl=(m2.get('series') or {}).get('inflation') or {}
_nmax=max((len([z for z in (v or []) if z is not None]) for v in _infl.values()), default=23)
_xs0=mlab(_nmax)[0]
bei=[x for x in ((m2.get('series') or {}).get('infl_exp') or []) if x is not None]
dd=[(dt.date.fromisoformat(str(p[0])),p[1]) for p in daily if p and p[1] is not None]
dd=[p for p in dd if p[0]>=_xs0]
if len(dd)>=2:
    xs=[p[0] for p in dd]; ys=[p[1] for p in dd]
    fig,ax=plt.subplots(figsize=(7.2,1.95),dpi=150); ax.plot(xs,ys,color=B,lw=1.0); ax.axhline(2.0,color=R,lw=0.9,ls='--',alpha=0.6); ax.scatter([xs[-1]],[ys[-1]],color=R,s=18,zorder=5)
    ax.set_xlim(_xs0,dt.date(2026,6,30))
    ax.set_title('기대인플레이션 10년(BEI) 일별 추이 · 점선=2%% · 현재 %.2f%% (FRED T10YIE 일별 실측)'%ys[-1],fontsize=8.6,color='#334155')
    ax.grid(alpha=0.25); ax.set_ylabel('%',fontsize=8,color='#64748B'); ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2)); ax.xaxis.set_major_formatter(mdates.DateFormatter('%y/%m'))
    for s in ['top','right']: ax.spines[s].set_visible(False)
    plt.tight_layout(); plt.savefig('charts/macro_infl_exp.png',bbox_inches='tight'); plt.close()
elif len(bei)>=2:
    fig,ax=plt.subplots(figsize=(7.2,1.95),dpi=150); ax.plot(mlab(len(bei)),bei,color=B,lw=1.8,marker='o',ms=3); ax.axhline(2.0,color=R,lw=0.9,ls='--',alpha=0.6)
    ax.set_xlim(_xs0,dt.date(2026,6,30)); ax.set_title('기대인플레이션 10년(BEI) 추이 · 점선=2% (월별 실측)',fontsize=8.6,color='#334155')
    ax.grid(alpha=0.25); ax.xaxis.set_major_formatter(mdates.DateFormatter('%y/%m'))
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
# (6) spx/kospi 선행EPS·지수·PER (nmr_fwd)
fw=L('nmr_fwd.json')
def _fwd_chart(node,out,name):
    e=[v for v in (node.get('eps') or []) if v is not None]; i=[v for v in (node.get('idx') or []) if v is not None]; mo=node.get('months') or []
    try:
        if len(e)>=2 and len(e)==len(i):
            xm=[dt.datetime.strptime(m,'%Y-%m') for m in mo[:len(e)]]; per=[round(i[k]/e[k],1) for k in range(len(e))]
            fig,ax=plt.subplots(figsize=(7.2,2.5),dpi=150); ax.bar(xm,e,width=20,color='#93C5FD',label='12M Fwd EPS'); ax.set_ylabel('Fwd EPS',fontsize=8,color=B)
            ax2=ax.twinx(); ax2.plot(xm,i,color=B,lw=2,marker='o',ms=3,label='지수')
            ax3=ax.twinx(); ax3.spines['right'].set_position(('outward',40)); ax3.plot(xm,per,color=R,lw=1.5,ls='--',label='선행PER'); ax3.set_ylabel('선행PER(x)',fontsize=8,color=R)
            ax.set_title(name+' 12개월 선행EPS·지수·선행PER (실측)',fontsize=9,color='#334155'); ax.xaxis.set_major_formatter(mdates.DateFormatter('%y/%m'))
            h1,l1=ax.get_legend_handles_labels();h2,l2=ax2.get_legend_handles_labels();h3,l3=ax3.get_legend_handles_labels(); ax.legend(h1+h2+h3,l1+l2+l3,fontsize=7,loc='upper left')
            plt.tight_layout(); plt.savefig(out,bbox_inches='tight'); plt.close(); return
        if len(i)>=2:
            xm=[dt.datetime.strptime(m,'%Y-%m') for m in mo[:len(i)]]
            fig,ax=plt.subplots(figsize=(7.2,2.2),dpi=150); ax.plot(xm,i,color=B,lw=2,marker='o',ms=3)
            ax.set_title(name+' 지수 추이 (선행EPS 미확보 — 지수만)',fontsize=9,color='#334155'); ax.xaxis.set_major_formatter(mdates.DateFormatter('%y/%m')); ax.grid(alpha=0.25)
            for s in ['top','right']: ax.spines[s].set_visible(False)
            plt.tight_layout(); plt.savefig(out,bbox_inches='tight'); plt.close()
    except Exception as e: print('fwd chart err',name,e)
_fwd_chart(fw.get('spx') or {},'charts/macro_spx_fwd.png','S&P500')
_fwd_chart(fw.get('kospi') or {},'charts/macro_kospi_fwd.png','KOSPI')
# (7) GDP 성장률 분기 (최근 ~1년)
gd=L('nmr_gdp.json'); gg=[(str(q),v) for q,v in (gd.get('gdp_growth') or []) if v is not None]
if len(gg)>=2:
    labs=[q for q,_ in gg]; ys=[v for _,v in gg]; cols=[G if v>=0 else R for v in ys]
    fig,ax=plt.subplots(figsize=(5.8,2.15),dpi=150); ax.bar(range(len(ys)),ys,color=cols,width=0.6); ax.axhline(0,color='#9ca3af',lw=0.8)
    for i,v in enumerate(ys): ax.text(i,v+(0.08 if v>=0 else -0.22),('%+.1f'%v),ha='center',fontsize=8,color='#334155')
    ax.set_xticks(range(len(labs))); ax.set_xticklabels(labs,fontsize=8); ax.set_ylabel('%',fontsize=8,color='#64748B')
    ax.set_title('미국 실질 GDP 성장률(전기比 연율) 최근 %d분기 실측'%len(ys),fontsize=9,color='#334155'); ax.grid(alpha=0.2,axis='y')
    for sp in ['top','right']: ax.spines[sp].set_visible(False)
    plt.tight_layout(); plt.savefig('charts/macro_gdp.png',bbox_inches='tight'); plt.close(); print('gdp chart',len(ys),'q')
print('gen_macro2 done')
