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
    if isinstance(S,dict):  # (fix) DB 시계열은 nmr_macro.json 없어도 항상 로드
        for _k in ["curve_10_2","us2y_daily","us10y_daily","fed_funds_5y"]:
            if (_k in S) or _ndb._load("series_"+_k,_DB).get("data"):
                S[_k]=(_ndb.dbseries(_k, S.get(_k), _DB) or {}).get('data')
        if _ndb._pairs(S.get("curve_10_2")): S["curve_labels"]=[p[0] for p in S["curve_10_2"]]
        S["infl_exp"]=(_ndb.dbseries("infl_exp", S.get("infl_exp"), _DB, prefer_fresh=True) or {}).get('data')
        if isinstance(S.get("infl_exp"),list):  # (req2) 월/일 혼합 방지 — 일별(YYYY-MM-DD)만
            _dd=[p for p in S["infl_exp"] if len(str(p[0]))==10]
            if len(_dd)>=20: S["infl_exp"]=_dd
        try:  # (req2) BEI 일별 차트 파일 보장 — _ch_bei 가 우선 사용해 월/일 혼합 차트 방지
            _bp=os.path.join(O,"nmr_bei_daily.json")
            if not os.path.exists(_bp):
                _bd=[p for p in (S.get("infl_exp") or []) if len(str(p[0]))==10]
                if len(_bd)>=20: json.dump({"asof":str(_bd[-1][0]),"source":"FRED T10YIE (10Y BEI, daily)","series":_bd}, open(_bp,"w",encoding="utf-8"), ensure_ascii=False)
        except Exception: pass
        _infl=S.get("inflation") or {}
        for _ln in (list(_infl.keys()) or ["CPI","Core CPI","PCE","Core PCE","PPI"]):
            _infl[_ln]=(_ndb.dbseries("infl_"+_ln.replace(" ","_"), _infl.get(_ln), _DB) or {}).get('data')
        if _infl: S["inflation"]=_infl
        _emp=S.get("employment") or {}
        # (fix GDP 오염) 분기 키를 분기 시작일(YYYY-MM-DD)로 정규화·레벨값(|v|>=20, GDP 수천대) 배제 — 포맷 혼재(2026-01/2026-Q1/2026Q1) 중복 누적 방지
        def _gdpkey(k):
            import re as _re
            k=str(k); m=_re.match(r'^(\d{4})-?Q([1-4])$',k)
            if m: return '%s-%02d-01'%(m.group(1),(int(m.group(2))-1)*3+1)
            m=_re.match(r'^(\d{4})-(\d{2})',k)
            if m: return '%s-%02d-01'%(m.group(1),((int(m.group(2))-1)//3)*3+1)
            return None
        def _gdpsan(s):
            out={}
            for p in (s or []):
                try:
                    _k=_gdpkey(p[0]); _val=float(p[1])
                    if _k and abs(_val)<20: out[_k]=_val
                except Exception: pass
            return [[k,out[k]] for k in sorted(out)]
        for _pn in ["jobless","nfp","unemp","retail","gdp","ism_mfg","ism_svc","nfp_mom","retail_mom","gdp_ann"]:  # (req3) nmr_macro 에 series.employment 없어도 DB 시계열 항상 로드 (jobless=초기 실업수당 청구, 주간)
            _fv=_gdpsan(_emp.get(_pn)) if _pn=="gdp" else _emp.get(_pn)
            _v=(_ndb.dbseries("emp_"+_pn, _fv, _DB) or {}).get('data')
            if _v: _emp[_pn]=_v
        if _emp: S["employment"]=_emp
        _full=(json.load(open(_mp,encoding="utf-8")) if _mp else {}); _mm=_full.get("macro",_full) if isinstance(_full,dict) else _full
        _mm.setdefault("series",{}).update(S)
        _rr=_mm.setdefault("rates",{})
        if isinstance(_rr.get("fed_funds"),dict) and not str(_rr["fed_funds"].get("bias") or "").strip(): _rr["fed_funds"]["bias"]="중립"
        if _mp: json.dump(_full, open(_mp,"w",encoding="utf-8"), ensure_ascii=False)
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
REQUIRED=["macro_policy_rates","macro_curve","macro_inflation","macro_infl_exp","macro_employment"]
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
    for bk,col in (("us10y",BLUE),("us2y",BLUE)):  # (req1) 10Y/2Y 스파크 색 통일
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
        if isinstance(v,list):  # (fix-r3) null 페어·레벨 혼입(|v|>30) 개별 제거 — 라인 탈락/스파이크 방지
            v=[q for q in v if ((isinstance(q,(list,tuple)) and len(q)==2 and isinstance(q[1],(int,float)) and abs(q[1])<=30) or (not isinstance(q,(list,tuple)) and isinstance(q,(int,float)) and abs(q)<=30))]
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
    _asof=S.get("infl_exp_asof") or ""; _n=len(ie)
    _xvb,_=_xy(S.get("infl_exp"))
    if _xvb and len(_xvb)==_n:
        bmon=_xvb
    else:
        _t=dt.date.today(); _sy,_sm=_t.year,_t.month
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
    # (req6) 6개 지표 패널을 항상 표시 — 빈 시계열도 자리 유지(미확보 표기)
    _ep=[]
    # (req2/3/6) 레벨 시계열을 변화값으로 정규화 — NFP=전월차(월 신규고용), 소매=전월비%, GDP=연율%만(레벨 혼입 제거)
    def _empdisp(key):
        lvl=[v for v in _flat(emp.get(key)) if isinstance(v,(int,float))]
        # (req1/2 2026-07-05) 레벨·증감 "혼합" 시계열 내성 변환 — 연속 레벨 구간만 차분/전월비로 바꾸고
        # 레벨→증감 경계에서는 변환하지 않는다(구버전은 max>임계면 전체 차분 → 경계에서 -15만 절벽 스파이크).
        def _mixfix(vals,thr,conv):
            out=[];prev=None
            for v in vals:
                if abs(v)>thr:
                    if prev is not None: out.append(conv(prev,v))
                    prev=v
                else:
                    out.append(v);prev=None
            return out
        if key=="nfp":
            if lvl: lvl=_mixfix(lvl,5000,lambda a,b:round(b-a,1))  # PAYEMS 레벨→전월차(천명)
            return lvl or [v for v in _flat(emp.get("nfp_mom")) if isinstance(v,(int,float)) and abs(v)<=5000]
        if key=="retail":
            if lvl: lvl=_mixfix(lvl,50,lambda a,b:round((b/a-1)*100,2))  # 소매 레벨→전월비 %
            return lvl or [v for v in _flat(emp.get("retail_mom")) if isinstance(v,(int,float)) and abs(v)<=50]
        if key=="gdp":  # 연율(%) 값만 유지(레벨/이상치 제거) + (fix-r4) 최근 8분기만
            g=[v for v in lvl if abs(v)<50]
            ga=[v for v in _flat(emp.get("gdp_ann")) if isinstance(v,(int,float)) and abs(v)<50]
            _gv=(g if len(g)>=2 else (ga or g))
            _gd=[]
            for _v in _gv:
                if not _gd or _v!=_gd[-1]: _gd.append(_v)  # (fix-r4) 월별 중복 분기값 제거
            return _gd[-8:]
        if key=="jobless":  # (fix-r4) 단위 혼입 정규화: 건(>10000)→만건 + 최근 52주
            lvl=[(round(v/10000.0,1) if abs(v)>10000 else v) for v in lvl]
            return lvl[-52:]
        return lvl[-24:]  # (fix-r4) 월간 패널 최근 24개월 윈도우
    for key,title,col,hl in [("jobless","① 초기 실업수당 청구건수(만 건)",AMBER,None),("nfp","② NFP 월 신규고용(천명)",BLUE,0),("unemp","③ 실업률(%)",RED,None),("retail","④ 소매판매 MoM(%)",PURPLE,None),("ism_mfg","⑤ ISM 제조 PMI",BLUE,50),("ism_svc","⑥ ISM 서비스 PMI",GREEN,50),("gdp","⑦ 실질GDP 연율(%)",GREEN,None)]:
        ys=_empdisp(key)
        _ep.append((title,ys,col,hl))
    # 7패널 3/2/2 배치(맨앞=초기 실업수당 청구건수): 1행 ①②③, 2행 ④⑤, 3행 ⑥⑦ (6열 그리드에 colspan 2/3/3)
    _n=7
    fig=plt.figure(figsize=(9.0,7.6),dpi=150)
    _gs=fig.add_gridspec(3,6)
    axs=[fig.add_subplot(_gs[0,0:2]),fig.add_subplot(_gs[0,2:4]),fig.add_subplot(_gs[0,4:6]),
         fig.add_subplot(_gs[1,0:3]),fig.add_subplot(_gs[1,3:6]),
         fig.add_subplot(_gs[2,0:3]),fig.add_subplot(_gs[2,3:6])]
    def panel(ax,t,ys,c,hl=None):
        if not ys:
            ax.text(0.5,0.5,"데이터 미확보",ha="center",va="center",fontsize=8,color="#94A3B8")
            ax.set_title(t,fontsize=8,color=SLATE); ax.set_xticks([]); ax.set_yticks([])
            for s in ["top","right"]: ax.spines[s].set_visible(False); return
        ax.plot(range(len(ys)),ys,color=c,linewidth=1.5,marker="o",ms=2.4); ax.scatter([len(ys)-1],[ys[-1]],color=RED,s=13,zorder=5)
        if hl is not None: ax.axhline(hl,color=RED,linewidth=0.8,linestyle="--",alpha=0.7)
        ax.set_title(t,fontsize=8,color=SLATE); ax.grid(True,alpha=0.2); ax.set_xticks([])
        for s in ["top","right"]: ax.spines[s].set_visible(False)
    for _i,(t,ys,c,hl) in enumerate(_ep): panel(axs[_i],t,ys,c,hl)
    for _j in range(_n,len(axs)): axs[_j].axis("off")
    fig.suptitle("미국 고용·경기 지표 최근 1년 (초기 실업수당 청구=주간·나머지 월간)",fontsize=9.5,color=SLATE)
    fig.subplots_adjust(top=0.90,bottom=0.06,left=0.07,right=0.97,hspace=0.62,wspace=0.6)
    plt.savefig("charts/macro_employment.png",bbox_inches="tight"); plt.close()
_safe("macro_employment", _ch_emp)
# (2026-06-29) 3.1.5 선행EPS/PER 차트(_fwd / macro_spx_fwd / macro_kospi_fwd) 제거됨 — 섹션 삭제
_miss=[r for r in REQUIRED if r not in _made]
print("macro charts -> 생성 %d/%d | 실패:%s | 누락:%s"%(len([r for r in REQUIRED if r in _made]),len(REQUIRED),(",".join(_failed) or "없음"),(",".join(_miss) or "없음")))
if _miss: print("WARN_MACRO_MISSING="+",".join(_miss))
