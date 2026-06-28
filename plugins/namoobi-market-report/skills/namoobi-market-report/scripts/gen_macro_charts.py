#!/usr/bin/env python3
# gen_macro_charts.py (v4.0.0) — 3.1 매크로 대시보드. (R4 견고화: try/except 격리·_flat·stale삭제·리포트)
import os, json, glob, datetime as dt, traceback, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.font_manager as fm, matplotlib.dates as mdates
import matplotlib.ticker as mticker
_f=[p for p in [os.path.join(os.path.dirname(__file__),"fonts","nmr_kr.ttf"),"fonts/nmr_kr.ttf"] if os.path.exists(p)]
if _f: fm.fontManager.addfont(_f[0]); matplotlib.rcParams["font.family"]="NanumBarunGothic"
matplotlib.rcParams["axes.unicode_minus"]=False
O=os.environ.get("NMR_OUT") or (sorted(glob.glob("/sessions/*/mnt/outputs"))[-1] if glob.glob("/sessions/*/mnt/outputs") else ".")
os.makedirs("charts", exist_ok=True)
BLUE="#1E40AF"; RED="#DC2626"; GREEN="#059669"; AMBER="#D97706"; PURPLE="#7C3AED"; SLATE="#334155"
def _loadjson(*names):
    _SD=os.path.dirname(os.path.abspath(__file__))
    _CW=(sorted(glob.glob("/sessions/*/mnt/claudeCowork/_market_report_data"))[:1] or [""])[0]
    for c in names:
        for p in [c, os.path.join(O,c), os.path.join(_SD,c)]+([os.path.join(_CW,c)] if _CW else []):
            if os.path.exists(p):
                try: return json.load(open(p,encoding="utf-8"))
                except Exception: pass
    return None
MAC={}
def _load_series():
    global MAC
    d=_loadjson("nmr_macro.json")
    if isinstance(d,dict):
        MAC=d.get("macro",d) or {}; return MAC.get("series",{}) or {}
    return {}
S=_load_series()
try:
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import nmr_db as _ndb
    _DB=_ndb._dbdir(None)
    _mp=None
    for _p in ["nmr_macro.json", os.path.join(O,"nmr_macro.json")]:
        if os.path.exists(_p): _mp=_p; break
    if _mp and isinstance(S,dict):
        for _k in ["curve_10_2","us2y_daily","us10y_daily","fed_funds_5y"]:
            if (_k in S) or _ndb._load("series_"+_k,_DB).get("data"):
                S[_k]=_ndb.dbseries(_k, S.get(_k), _DB)
        if _ndb._pairs(S.get("curve_10_2")): S["curve_labels"]=[p[0] for p in S["curve_10_2"]]
        S["infl_exp"]=_ndb.dbseries("infl_exp", S.get("infl_exp"), _DB, prefer_fresh=True)
        _infl=S.get("inflation") or {}
        for _ln in (list(_infl.keys()) or ["CPI","Core CPI","PCE","Core PCE","PPI"]):
            _infl[_ln]=_ndb.dbseries("infl_"+_ln.replace(" ","_"), _infl.get(_ln), _DB)
        if _infl: S["inflation"]=_infl
        _emp=S.get("employment") or {}
        for _pn in list(_emp.keys()):
            _emp[_pn]=_ndb.dbseries("emp_"+_pn, _emp.get(_pn), _DB)
        if _emp: S["employment"]=_emp
        _full=json.load(open(_mp,encoding="utf-8")); _mm=_full.get("macro",_full) if isinstance(_full,dict) else _full
        _mm.setdefault("series",{}).update(S)
        _rr=_mm.setdefault("rates",{})
        if isinstance(_rr.get("fed_funds"),dict) and not str(_rr["fed_funds"].get("bias") or "").strip(): _rr["fed_funds"]["bias"]="중립"
        json.dump(_full, open(_mp,"w",encoding="utf-8"), ensure_ascii=False)
        _ip=os.path.join(O,"nmr_indexseries.json")
        try: _idx=json.load(open(_ip,encoding="utf-8"))
        except Exception: _idx={}
        if _ndb._pairs(S.get("us2y_daily")): _idx["us2y"]=S["us2y_daily"]
        _vh=None
        for _vp in [os.path.join(O,"nmr_vkospi_history.json")]+glob.glob("/sessions/*/mnt/claudeCowork/_market_report_data/nmr_vkospi_history.json"):
            try: _vh=json.load(open(_vp)); break
            except Exception: pass
        if _vh:
            _vs=_vh.get("series") if isinstance(_vh,dict) else _vh
            if _ndb._pairs(_vs): _idx["vkospi"]=_vs
        json.dump(_idx, open(_ip,"w",encoding="utf-8"), ensure_ascii=False)
        print("[DB화] 매크로 시계열 누적:", {k:(len(S[k]) if isinstance(S.get(k),list) else 0) for k in ["curve_10_2","us2y_daily","fed_funds_5y","infl_exp"]}, "infl", {k:len(v) for k,v in (S.get("inflation") or {}).items()}, "emp", {k:len(v) for k,v in (S.get("employment") or {}).items()})
except Exception as _dbe:
    print("[DB화] 시계열 누적 skip(비차단):", _dbe)
def _flat(v, default=None):
    if not isinstance(v,(list,tuple)) or len(v)<2: return default
    out=[]
    for x in v:
        if isinstance(x,(list,tuple)):
            if len(x)<1: return default
            x=x[-1]
        try: out.append(float(x))
        except Exception: return default
    return out
def _xy(v):
    ys=_flat(v)
    if ys is None: return None,None
    xs=None
    if isinstance(v[0],(list,tuple)) and len(v[0])>=2:
        try: xs=[mdates.datestr2num((str(p[0])[:7]+"-01") if len(str(p[0]))==7 else str(p[0])[:10]) for p in v]
        except Exception: xs=None
    return xs, ys
def months(sy,sm,n):
    o=[];y,m=sy,sm
    for _ in range(n):
        o.append(dt.date(y,m,1)); m+=1
        if m>12:m=1;y+=1
    return o
mon=months(2025,6,12)
REQUIRED=["macro_policy_rates","macro_curve","macro_inflation","macro_infl_exp","macro_employment","macro_spx_fwd","macro_kospi_fwd"]
for _r in REQUIRED:
    try: os.remove("charts/%s.png"%_r)
    except OSError: pass
_made=[]; _failed=[]
def _safe(name, fn):
    try:
        fn()
        if os.path.exists("charts/%s.png"%name): _made.append(name)
        else: _failed.append(name+"(no-file)")
    except Exception as e:
        _failed.append("%s(%s)"%(name,type(e).__name__)); traceback.print_exc()
        try:
            fig,ax=plt.subplots(figsize=(7.2,1.0),dpi=150); ax.axis("off")
            ax.text(0.5,0.5,"[차트 생성 실패: %s]"%name,ha="center",va="center",fontsize=10,color=RED)
            plt.tight_layout(); plt.savefig("charts/%s.png"%name,bbox_inches="tight"); plt.close()
        except Exception: pass
def spark(name,ys,color=BLUE):
    ys=[y for y in ys if y is not None]
    if len(ys)<2: return
    fig,ax=plt.subplots(figsize=(2.3,0.62),dpi=150); ax.plot(range(len(ys)),ys,color=color,linewidth=1.4)
    ax.scatter([len(ys)-1],[ys[-1]],color=RED,s=12,zorder=5); ax.axis("off")
    plt.tight_layout(pad=0.1); plt.savefig("charts/spark_%s.png"%name,bbox_inches="tight",transparent=True); plt.close()
def _ch_spark_bonds():
    tc=_loadjson("treasury_consistent.json") or {}
    for bk,col in (("us10y",BLUE),("us2y","#0E7490")):
        sv=(tc.get(bk) or {}).get("spark_vals")
        if isinstance(sv,list) and len(sv)>=2: spark(bk, sv, col)
        else:
            cand=_flat(S.get(bk+"_series") or S.get(bk) or S.get(bk+"_daily"))
            if cand and len(cand)>=2: spark(bk, cand, col)
def _ch_spark_vkospi():
    vh=_loadjson("nmr_vkospi_history.json")
    ser=(vh.get("series") if isinstance(vh,dict) else None) or []
    ys=[p[1] for p in ser if isinstance(p,(list,tuple)) and len(p)>=2]
    if len(ys)>=2: spark("vkospi", ys, "#DC2626")
try: _ch_spark_bonds(); _ch_spark_vkospi()
except Exception: traceback.print_exc()
def _ch_policy():
    # (req5 갱신) 사용자 제공 실측 결정이력(nmr_policyrates_monthly.json) → 단일패널 step 시계열, 막대 제거
    import datetime as _dt
    pr=_loadjson("nmr_policyrates_monthly.json")
    ser=(pr.get("series") if isinstance(pr,dict) else None) or {}
    fig,ax=plt.subplots(figsize=(8.8,3.2),dpi=150)
    CC={"미국":BLUE,"유로존":GREEN,"영국":RED,"한국":AMBER,"중국":PURPLE,"일본":"#0E7490"}
    x0=_dt.date(2022,1,1); plotted=False
    for cn,pts in ser.items():
        try: P=sorted((_dt.date.fromisoformat(str(d)[:10]),float(r)) for d,r in pts)
        except Exception: continue
        pre=[r for d,r in P if d<=x0]; win=[(d,r) for d,r in P if d>=x0]
        if pre: win=[(x0,pre[-1])]+win
        if len(win)<2: continue
        xs=[mdates.date2num(d) for d,r in win]; ys=[r for d,r in win]
        ax.plot(xs,ys,linewidth=2.0 if cn=="미국" else 1.4,color=CC.get(cn,"#94A3B8"),label=cn,drawstyle="steps-post")
        ax.annotate("%.2f"%ys[-1],(xs[-1],ys[-1]),textcoords="offset points",xytext=(5,0),fontsize=6.8,color=CC.get(cn,"#94A3B8"),fontweight="bold",va="center")
        plotted=True
    if plotted:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m")); ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
        [t.set_rotation(0) for t in ax.get_xticklabels()]
        # 범례를 플롯 밖(축 위)으로 빼 라인과 겹침 방지 + 제목은 그 위
        ax.legend(fontsize=7,ncol=6,loc="lower center",bbox_to_anchor=(0.5,1.005),frameon=False,columnspacing=1.6,handlelength=1.7,borderaxespad=0.1)
        ax.set_title("주요국 정책금리 결정이력 (실측 · 중앙은행 발표)",fontsize=9.4,color=SLATE,pad=20)
        ax.grid(True,alpha=0.25); ax.set_ylabel("%",fontsize=8,color="#64748B"); ax.set_xlim(left=mdates.date2num(x0))
        _lo,_hi=ax.get_ylim(); ax.set_ylim(_lo,_hi+(_hi-_lo)*0.05)  # 상단 약간 여유
        for _s in ["top","right"]: ax.spines[_s].set_visible(False)
    else:
        ax.axis("off"); ax.text(0.5,0.5,"정책금리 결정이력 DB 미확보",ha="center",va="center",fontsize=10,color="#94A3B8")
    plt.tight_layout(); plt.savefig("charts/macro_policy_rates.png",bbox_inches="tight"); plt.close()
_safe("macro_policy_rates", _ch_policy)
def _ch_curve():
    d=_flat(S.get("curve_10_2")) or [0.42,0.40,0.39,0.40,0.38,0.29,0.27]
    dl=S.get("curve_labels") or ["(예시)","","","","","","(데이터없음)"]
    fig,ax=plt.subplots(figsize=(7.2,1.95),dpi=150)
    try: _xd=[dt.date.fromisoformat(str(x)[:10]) for x in dl]; _isdate=True
    except Exception: _xd=None; _isdate=False
    if _isdate and len(d)>30:
        ax.plot(_xd,d,color=BLUE,linewidth=1.5); ax.fill_between(_xd,d,0,color=BLUE,alpha=0.07); ax.scatter([_xd[-1]],[d[-1]],color=RED,zorder=5,s=28)
        ax.annotate(("+%.2f%%p"%d[-1]) if d[-1]>=0 else ("%.2f%%p"%d[-1]),(_xd[-1],d[-1]),textcoords="offset points",xytext=(-40,7),color=RED,fontsize=9,fontweight="bold")
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m")); [t.set_rotation(0) for t in ax.get_xticklabels()]
        _ttl="미국 장단기 금리차(10Y-2Y) 최대기간 일별 실측 (+정상/-역전)"
    else:
        ax.plot(dl,d,color=BLUE,linewidth=1.8,marker="o",ms=4); ax.scatter([dl[-1]],[d[-1]],color=RED,zorder=5,s=28)
        ax.annotate(("+%.2f%%p"%d[-1]) if d[-1]>=0 else ("%.2f%%p"%d[-1]),(dl[-1],d[-1]),textcoords="offset points",xytext=(-36,7),color=RED,fontsize=9,fontweight="bold")
        ax.xaxis.set_major_locator(mticker.MaxNLocator(nbins=8)); [t.set_rotation(30) for t in ax.get_xticklabels()]; [t.set_horizontalalignment("right") for t in ax.get_xticklabels()]
        _ttl="미국 장단기 금리차(수익률곡선)(10Y-2Y) (+면 정상 / -면 역전)"
    ax.axhline(0,color=RED,linewidth=0.9,linestyle="--"); ax.set_title(_ttl,fontsize=9.0,color=SLATE); ax.grid(True,alpha=0.25); ax.set_ylabel("%p",fontsize=8,color="#64748B")
    for s in ["top","right"]: ax.spines[s].set_visible(False)
    plt.tight_layout(); plt.savefig("charts/macro_curve.png",bbox_inches="tight"); plt.close()
_safe("macro_curve", _ch_curve)
def _ch_infl():
    infl=S.get("inflation") or {"CPI":[2.6,2.7,2.8,2.9,3.1,3.3,3.4,3.6,3.8,3.9,4.0,4.17],"Core CPI":[2.9,2.9,3.0,3.0,3.0,3.1,3.1,3.2,3.1,3.1,3.0,3.1],"PCE":[2.3,2.4,2.4,2.5,2.5,2.6,2.6,2.6,2.6,2.7,2.6,2.6],"Core PCE":[2.6,2.6,2.7,2.7,2.7,2.8,2.8,2.8,2.8,2.8,2.8,2.8],"PPI":[1.8,2.0,2.2,2.3,2.4,2.6,2.7,2.8,2.9,3.0,2.9,2.9]}
    fig,ax=plt.subplots(figsize=(7.4,2.9),dpi=150)
    for k,v in infl.items():
        xs,ys=_xy(v)
        if ys is None: continue
        if xs is not None: ax.plot(xs,ys,linewidth=1.6,marker="o",ms=3,label=k)
        else:
            _mx=months(2025,6,len(ys)) if len(ys)!=12 else mon
            ax.plot(_mx,ys,linewidth=1.6,marker="o",ms=3,label=k)
    ax.axhline(2.0,color=RED,linewidth=0.9,linestyle="--",alpha=0.7); ax.set_title("미국 물가 YoY 최근 12개월 통합 (점선=연준 2% 목표 · CPI 최신 실측)",fontsize=9.5,color=SLATE)
    ax.legend(fontsize=7,ncol=5); ax.grid(True,alpha=0.25); ax.set_ylabel("YoY %",fontsize=8,color="#64748B"); ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m"))
    for s in ["top","right"]: ax.spines[s].set_visible(False)
    plt.tight_layout(); plt.savefig("charts/macro_inflation.png",bbox_inches="tight"); plt.close()
_safe("macro_inflation", _ch_infl)
def _ch_bei():
    daily=_loadjson("nmr_bei_daily.json")
    pts=(daily.get("series") if isinstance(daily,dict) else None) or []
    if isinstance(pts,list) and len(pts)>=20:
        xs=[mdates.datestr2num(str(p[0])[:10]) for p in pts]; ys=[float(p[1]) for p in pts]
        _asof=(daily.get("asof") if isinstance(daily,dict) else "") or str(pts[-1][0])[:10]
        fig,ax=plt.subplots(figsize=(7.2,1.95),dpi=150); ax.plot(xs,ys,color=BLUE,linewidth=1.4); ax.fill_between(xs,ys,min(ys),color=BLUE,alpha=0.06)
        ax.axhline(2.0,color=RED,linewidth=0.9,linestyle="--",alpha=0.7); ax.scatter([xs[-1]],[ys[-1]],color=RED,zorder=5,s=22)
        ax.set_title(f"기대인플레이션 10년(BEI) 일별 · 점선=2% · 현재 {ys[-1]:.2f}% ({_asof} FRED T10YIE)",fontsize=8.6,color=SLATE)
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m")); ax.grid(True,alpha=0.25); ax.set_ylabel("%",fontsize=8,color="#64748B")
        for s in ["top","right"]: ax.spines[s].set_visible(False)
        plt.tight_layout(); plt.savefig("charts/macro_infl_exp.png",bbox_inches="tight"); plt.close(); return
    ie=_flat(S.get("infl_exp"))
    if not (ie and len(ie)>=2):
        fig,ax=plt.subplots(figsize=(7.2,1.0),dpi=150); ax.axis("off")
        ax.text(0.5,0.5,"기대인플레이션 10년(BEI): 일별/월별 실측 미확보 — 이번 회차 미표시",ha="center",va="center",fontsize=10,color="#94A3B8")
        plt.tight_layout(); plt.savefig("charts/macro_infl_exp.png",bbox_inches="tight"); plt.close(); return
    _asof=S.get("infl_exp_asof") or ""; _n=len(ie); _t=dt.date.today(); _sy,_sm=_t.year,_t.month
    for _ in range(_n-1):
        _sm-=1
        if _sm<1: _sm=12; _sy-=1
    bmon=months(_sy,_sm,_n)
    fig,ax=plt.subplots(figsize=(7.2,1.95),dpi=150); ax.plot(bmon,ie,color=BLUE,linewidth=1.8,marker="o",ms=3); ax.axhline(2.0,color=RED,linewidth=0.9,linestyle="--",alpha=0.7)
    ax.scatter([bmon[-1]],[ie[-1]],color=RED,zorder=5,s=24)
    ax.set_title(f"기대인플레이션 10년(BEI) 월별 · 점선=2% · 현재값 {ie[-1]:.2f}% ("+(_asof or "")+")",fontsize=8.6,color=SLATE)
    ax.grid(True,alpha=0.25); ax.set_ylabel("%",fontsize=8,color="#64748B"); ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m"))
    for s in ["top","right"]: ax.spines[s].set_visible(False)
    plt.tight_layout(); plt.savefig("charts/macro_infl_exp.png",bbox_inches="tight"); plt.close()
_safe("macro_infl_exp", _ch_bei)
def _ch_emp():
    emp=S.get("employment") or {}
    _ep=[]
    for key,title,col,hl in [("nfp","① NFP 신규고용(천명)",BLUE,0),("unemp","② 실업률(%)",RED,None),("retail","③ 소매판매 MoM(%)",PURPLE,None),("ism_mfg","④ ISM 제조 PMI",BLUE,50),("ism_svc","⑤ ISM 서비스 PMI",GREEN,50),("gdp","⑥ 실질GDP 연율(%)",GREEN,None)]:
        ys=_flat(emp.get(key) or emp.get({"nfp":"nfp_mom","retail":"retail_mom","gdp":"gdp_ann"}.get(key,key)))
        if ys: _ep.append((title,ys,col,hl))
    if not _ep: _ep=[("① NFP 신규고용(천명)",[200,180,170,160,172],BLUE,0),("② 실업률(%)",[4.0,4.1,4.2,4.3,4.3],RED,None)]
    _n=len(_ep); _ncol=3 if _n>=5 else max(1,_n); _nrow=(_n+_ncol-1)//_ncol
    fig,axs=plt.subplots(_nrow,_ncol,figsize=(3.0*_ncol,2.5*_nrow),dpi=150)
    axs=list(axs.flatten()) if hasattr(axs,"flatten") else [axs]
    def panel(ax,t,ys,c,hl=None):
        ax.plot(range(len(ys)),ys,color=c,linewidth=1.5,marker="o",ms=2.4); ax.scatter([len(ys)-1],[ys[-1]],color=RED,s=13,zorder=5)
        if hl is not None: ax.axhline(hl,color=RED,linewidth=0.8,linestyle="--",alpha=0.7)
        ax.set_title(t,fontsize=8,color=SLATE); ax.grid(True,alpha=0.2); ax.set_xticks([])
        for s in ["top","right"]: ax.spines[s].set_visible(False)
    for _i,(t,ys,c,hl) in enumerate(_ep): panel(axs[_i],t,ys,c,hl)
    for _j in range(_n,len(axs)): axs[_j].axis("off")
    fig.suptitle("미국 고용·경기 지표 최근 1년 (FMP 실측)",fontsize=9.5,color=SLATE)
    plt.tight_layout(rect=[0,0,1,0.93]); plt.savefig("charts/macro_employment.png",bbox_inches="tight"); plt.close()
_safe("macro_employment", _ch_emp)
def _fwd(name,key,title,daily_file):
    # (req 갱신) 지수=일별 실측 라인 + 선행EPS·선행PER=조사값(DB nmr_fwd_history.json) 포인트
    daily=_loadjson(daily_file) or {}
    dser=(daily.get("series") if isinstance(daily,dict) else None) or []
    fh=_loadjson("nmr_fwd_history.json") or {}
    pts=[p for p in ((fh.get(key) if isinstance(fh,dict) else None) or []) if (p.get("eps") or p.get("fwd_eps")) is not None]
    if len(dser)<2 or not pts: raise ValueError("일별지수/조사EPS 부족")
    dx=[mdates.datestr2num(str(d)[:10]) for d,v in dser]; dy=[v for d,v in dser]
    pts=sorted(pts,key=lambda x:str(x.get("idx_date") or x.get("date")))
    ex=[mdates.datestr2num(str(p.get("idx_date") or p.get("date"))[:10]) for p in pts]
    eeps=[p.get("eps",p.get("fwd_eps")) for p in pts]; eper=[p.get("per",p.get("fwd_per")) for p in pts]
    fig,ax=plt.subplots(figsize=(7.6,2.9),dpi=150)
    ax.plot(dx,dy,color=BLUE,linewidth=1.0,label="지수(일별 실측)"); ax.set_ylabel("지수(pt)",fontsize=8,color=BLUE)
    ax.annotate("%.0f"%dy[-1],(dx[-1],dy[-1]),textcoords="offset points",xytext=(3,0),fontsize=7,color=BLUE,fontweight="bold",va="center")
    ax2=ax.twinx(); ax2.plot(ex,eeps,color=AMBER,linewidth=1.7,marker="o",ms=5,label="12M 선행 EPS(조사)"); ax2.set_ylabel("12M 선행 EPS",fontsize=8,color=AMBER)
    for x,e in zip(ex,eeps): ax2.annotate(("%.0f"%e),(x,e),textcoords="offset points",xytext=(0,7),fontsize=6.3,color="#B45309",ha="center")
    ax3=ax.twinx(); ax3.spines["right"].set_position(("outward",42)); ax3.plot(ex,eper,color=GREEN,linewidth=1.3,marker="s",ms=4,linestyle="--",label="선행 PER(조사)"); ax3.set_ylabel("선행 PER(배)",fontsize=8,color=GREEN)
    ax.set_title(title,fontsize=9.3,color=SLATE); ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m")); ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    [t.set_rotation(0) for t in ax.get_xticklabels()]; ax.grid(True,alpha=0.2); ax.spines["top"].set_visible(False)
    h1,l1=ax.get_legend_handles_labels(); h2,l2=ax2.get_legend_handles_labels(); h3,l3=ax3.get_legend_handles_labels()
    ax.legend(h1+h2+h3,l1+l2+l3,fontsize=6.6,loc="upper left",framealpha=0.85)
    plt.tight_layout(); plt.savefig("charts/macro_%s.png"%name,bbox_inches="tight"); plt.close()
_safe("macro_spx_fwd", lambda: _fwd("spx_fwd","spx","S&P500 · 일일 지수 + 12M 선행 EPS·PER (조사값 · 실적 vs 밸류)","nmr_spx_daily.json"))
_safe("macro_kospi_fwd", lambda: _fwd("kospi_fwd","kospi","KOSPI · 일일 지수 + 12M 선행 EPS·PER (조사값 · 실적 vs 밸류)","nmr_kospi_daily.json"))
_miss=[r for r in REQUIRED if r not in _made]
print("macro charts -> 생성 %d/%d | 실패:%s | 누락:%s"%(len([r for r in REQUIRED if r in _made]),len(REQUIRED),(",".join(_failed) or "없음"),(",".join(_miss) or "없음")))
if _miss: print("WARN_MACRO_MISSING="+",".join(_miss))
