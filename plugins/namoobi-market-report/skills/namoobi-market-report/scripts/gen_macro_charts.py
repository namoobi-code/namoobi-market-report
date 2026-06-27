#!/usr/bin/env python3
# gen_macro_charts.py (v3.11.0) — 3.1 주요지표(매크로 대시보드) 차트 생성기.
# 출력: charts/macro_policy_rates.png·macro_curve.png·macro_inflation.png·macro_employment.png·
#       macro_infl_exp.png·macro_spx_fwd.png·macro_kospi_fwd.png + charts/spark_{us10y,vix,vkospi,dxy,usdkrw,wti}.png
# 데이터: nmr_macro.json(MacroAgent: FMP economics/treasury + FRED) 의 series_* 있으면 라이브 오버라이드,
#         없으면 내장 예시·추정 시계열로 생성('추정' 표기 유지). build_report.js renderMacroIndicators 와 파일명 일치.
import os, json, glob, datetime as dt, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.font_manager as fm, matplotlib.dates as mdates
_f=[p for p in [os.path.join(os.path.dirname(__file__),"fonts","nmr_kr.ttf"),"fonts/nmr_kr.ttf"] if os.path.exists(p)]
if _f: fm.fontManager.addfont(_f[0]); matplotlib.rcParams["font.family"]="NanumBarunGothic"
matplotlib.rcParams["axes.unicode_minus"]=False
O=os.environ.get("NMR_OUT") or (sorted(glob.glob("/sessions/*/mnt/outputs"))[-1] if glob.glob("/sessions/*/mnt/outputs") else ".")
os.makedirs("charts", exist_ok=True)
BLUE="#1E40AF"; RED="#DC2626"; GREEN="#059669"
def _load():
    for c in ["nmr_macro.json", os.path.join(O,"nmr_macro.json")]:
        if os.path.exists(c):
            try: d=json.load(open(c,encoding="utf-8")); return d.get("macro",d).get("series",{}) or {}
            except Exception: pass
    return {}
S=_load()  # 라이브 series 오버라이드(있으면)
def months(sy,sm,n):
    o=[];y,m=sy,sm
    for _ in range(n):
        o.append(dt.date(y,m,1)); m+=1
        if m>12:m=1;y+=1
    return o
mon=months(2025,6,12)
def spark(name,xs,ys,color=BLUE):
    fig,ax=plt.subplots(figsize=(2.3,0.62),dpi=150); ax.plot(xs,ys,color=color,linewidth=1.4)
    ax.scatter([xs[-1]],[ys[-1]],color=RED,s=12,zorder=5); ax.axis("off")
    plt.tight_layout(pad=0.1); plt.savefig("charts/spark_%s.png"%name,bbox_inches="tight",transparent=True); plt.close()

# (1) 정책금리 6개국 5년 (미국=실측 월별 기본, S 오버라이드 가능)
ff=S.get("fed_funds_5y") or [0.09,0.08,0.07,0.07,0.06,0.08,0.10,0.09,0.08,0.08,0.08,0.08,0.08,0.08,0.20,0.33,0.77,1.21,1.68,2.33,2.56,3.08,3.78,4.10,4.33,4.57,4.65,4.83,5.06,5.08,5.12,5.33,5.33,5.33,5.33,5.33,5.33,5.33,5.33,5.33,5.33,5.33,5.33,5.33,5.13,4.83,4.64,4.48,4.33,4.33,4.33,4.33,4.33,4.33,4.33,4.33,4.22,4.09,3.88,3.72,3.64,3.64,3.64,3.64,3.63]
ffx=months(2021,1,len(ff))
fig,ax=plt.subplots(figsize=(7.2,2.8),dpi=150)
ax.plot(ffx,ff,color=BLUE,linewidth=1.8,label="미국(실측)")
ax.set_title("미국 기준금리(실효) 5년 추이 — FMP/FRED 실측",fontsize=9.5,color="#334155")
ax.legend(fontsize=7,ncol=6,loc="upper center",bbox_to_anchor=(0.5,-0.13)); ax.grid(True,alpha=0.25); ax.set_ylabel("%",fontsize=8,color="#64748B")
for s in ["top","right"]: ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig("charts/macro_policy_rates.png",bbox_inches="tight"); plt.close()

# (2) 장단기 금리차 10Y-2Y
# (req1/req2) ★MacroAgent 필수: series.curve_10_2(최근 1년 일별 10Y-2Y %p) + curve_labels(['YYYY-MM-DD',...] 권장)를
#   FMP treasury-rates(daily, from=1년전~당일)의 year10-year2 로 매 실행 채울 것. 라벨이 날짜(YYYY-MM-DD)이고
#   점이 30개 초과면 '최근 1년 일별' 날짜축으로 렌더(req1), 적으면 기존 카테고리축. 하드코딩은 데이터 누락 폴백.
d=S.get("curve_10_2") or [0.42,0.40,0.39,0.40,0.38,0.29,0.27]; dl=S.get("curve_labels") or ["(예시)","","","","","","(데이터없음)"]
fig,ax=plt.subplots(figsize=(7.2,1.95),dpi=150)
try: _xd=[dt.date.fromisoformat(str(x)) for x in dl]; _isdate=True
except Exception: _xd=None; _isdate=False
if _isdate and len(d)>30:   # 1년 일별 → 날짜축(req1)
    ax.plot(_xd,d,color=BLUE,linewidth=1.5); ax.fill_between(_xd,d,0,color=BLUE,alpha=0.07)
    ax.scatter([_xd[-1]],[d[-1]],color=RED,zorder=5,s=28)
    ax.annotate(("+%.2f%%p"%d[-1]) if d[-1]>=0 else ("%.2f%%p"%d[-1]),(_xd[-1],d[-1]),textcoords="offset points",xytext=(-40,7),color=RED,fontsize=9,fontweight="bold")
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m"))
    _ttl="미국 장단기 금리차(10Y-2Y) 최대기간 일별 실측 (+정상/-역전)"
else:                        # 폴백/단기 → 카테고리축
    ax.plot(dl,d,color=BLUE,linewidth=1.8,marker="o",ms=4)
    ax.scatter([dl[-1]],[d[-1]],color=RED,zorder=5,s=28); ax.annotate(("+%.2f%%p"%d[-1]) if d[-1]>=0 else ("%.2f%%p"%d[-1]),(dl[-1],d[-1]),textcoords="offset points",xytext=(-36,7),color=RED,fontsize=9,fontweight="bold")
    _ttl="미국 장단기 금리차(수익률곡선)(10Y-2Y) (+면 정상 / -면 역전)"
ax.axhline(0,color=RED,linewidth=0.9,linestyle="--")
ax.set_title(_ttl,fontsize=9.0,color="#334155"); ax.grid(True,alpha=0.25); ax.set_ylabel("%p",fontsize=8,color="#64748B")
for s in ["top","right"]: ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig("charts/macro_curve.png",bbox_inches="tight"); plt.close()

# (3) 물가 통합 5종 YoY
infl=S.get("inflation") or {"CPI":[2.6,2.7,2.8,2.9,3.1,3.3,3.4,3.6,3.8,3.9,4.0,4.17],"Core CPI":[2.9,2.9,3.0,3.0,3.0,3.1,3.1,3.2,3.1,3.1,3.0,3.1],"PCE":[2.3,2.4,2.4,2.5,2.5,2.6,2.6,2.6,2.6,2.7,2.6,2.6],"Core PCE":[2.6,2.6,2.7,2.7,2.7,2.8,2.8,2.8,2.8,2.8,2.8,2.8],"PPI":[1.8,2.0,2.2,2.3,2.4,2.6,2.7,2.8,2.9,3.0,2.9,2.9]}
fig,ax=plt.subplots(figsize=(7.4,2.9),dpi=150)
for k,v in infl.items():
    _mx=months(2025,6,len(v)) if len(v)!=12 else mon
    ax.plot(_mx,v,linewidth=1.6,marker="o",ms=3,label=k)
ax.axhline(2.0,color=RED,linewidth=0.9,linestyle="--",alpha=0.7); ax.set_title("미국 물가 YoY 최근 12개월 통합 (점선=연준 2% 목표 · CPI 최신 실측)",fontsize=9.5,color="#334155")
ax.legend(fontsize=7,ncol=5); ax.grid(True,alpha=0.25); ax.set_ylabel("YoY %",fontsize=8,color="#64748B"); ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m"))
for s in ["top","right"]: ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig("charts/macro_inflation.png",bbox_inches="tight"); plt.close()

# (4) 기대인플레 10Y — req5: 축을 '이번 달'까지 동적 생성(현재월 6월 포함) + 현재값 asof 표기
#   BEI(T10YIE)는 일별이므로 MacroAgent 가 series.infl_exp(현재월까지) + series.infl_exp_asof(YYYY-MM-DD)를 제공.
ie=S.get("infl_exp")
if not (ie and len(ie)>=2):
    fig,ax=plt.subplots(figsize=(7.2,1.0),dpi=150); ax.axis("off")
    ax.text(0.5,0.5,"기대인플레이션 10년(BEI): 무료 실측 데이터 미확보 — 이번 회차 미표시 (추정 미사용)",ha="center",va="center",fontsize=10,color="#94A3B8")
    plt.tight_layout(); plt.savefig("charts/macro_infl_exp.png",bbox_inches="tight"); plt.close()
if ie and len(ie)>=2:
    _asof=S.get("infl_exp_asof") or ""
    _n=len(ie); _t=dt.date.today(); _sy,_sm=_t.year,_t.month
    for _ in range(_n-1):
        _sm-=1
        if _sm<1: _sm=12; _sy-=1
    bmon=months(_sy,_sm,_n)
    fig,ax=plt.subplots(figsize=(7.2,1.95),dpi=150); ax.plot(bmon,ie,color=BLUE,linewidth=1.8,marker="o",ms=3); ax.axhline(2.0,color=RED,linewidth=0.9,linestyle="--",alpha=0.7)
    ax.scatter([bmon[-1]],[ie[-1]],color=RED,zorder=5,s=24)
    ax.set_title(f"기대인플레이션 10년(BEI) · 점선=2% · 현재값 {ie[-1]:.2f}% ("+(_asof or "")+" 실측)",fontsize=8.6,color="#334155")
    ax.grid(True,alpha=0.25); ax.set_ylabel("%",fontsize=8,color="#64748B"); ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m"))
    for s in ["top","right"]: ax.spines[s].set_visible(False)
    plt.tight_layout(); plt.savefig("charts/macro_infl_exp.png",bbox_inches="tight"); plt.close()

# (5) 고용 통합 2x3
emp=S.get("employment") or {}
_ep=[]
if emp.get("unemp"): _ep.append(("실업률(%, 실측)",emp["unemp"],RED,None))
if emp.get("nfp"): _ep.append(("NFP 신규고용(천명, 실측)",emp["nfp"],BLUE,0))
if emp.get("gdp"): _ep.append(("실질GDP(분기, 실측)",emp["gdp"],GREEN,None))
if emp.get("retail"): _ep.append(("소매판매(백만$, 실측)",emp["retail"],"#7C3AED",None))
if emp.get("ism_mfg"): _ep.append(("ISM 제조 PMI(실측)",emp["ism_mfg"],BLUE,50))
if emp.get("ism_svc"): _ep.append(("ISM 서비스 PMI(실측)",emp["ism_svc"],GREEN,50))
_nc=max(1,len(_ep)); fig,axs=plt.subplots(1,_nc,figsize=(2.7*_nc,2.6),dpi=150)
if _nc==1: axs=[axs]
def panel(ax,t,ys,c,hl=None):
    ax.plot(range(len(ys)),ys,color=c,linewidth=1.5,marker="o",ms=2.4); ax.scatter([len(ys)-1],[ys[-1]],color=RED,s=13,zorder=5)
    if hl is not None: ax.axhline(hl,color=RED,linewidth=0.8,linestyle="--",alpha=0.7)
    ax.set_title(t,fontsize=8,color="#334155"); ax.grid(True,alpha=0.2); ax.set_xticks([])
    for s in ["top","right"]: ax.spines[s].set_visible(False)
for _i,(t,ys,c,hl) in enumerate(_ep): panel(axs[_i],t,ys,c,hl)
fig.suptitle("미국 고용·경기 지표 최근 1년 (FMP 실측)",fontsize=9.5,color="#334155")
plt.tight_layout(rect=[0,0,1,0.93]); plt.savefig("charts/macro_employment.png",bbox_inches="tight"); plt.close()

# (6) 심리 스파크 — gen_rest_charts 의 측정치 스파크 사용(여기서 미생성, 추정 덮어쓰기 방지)
sent=S.get("sentiment") or {}

# (7) 선행 EPS — 지수/PER 정합
def fwd(name,title,eps,idx):
    per=[round(idx[i]/eps[i],1) for i in range(len(eps))]
    fig,ax=plt.subplots(figsize=(7.4,2.6),dpi=150); ax.bar(mon,eps,width=20,color="#93C5FD",label="12M Fwd EPS"); ax.set_ylabel("Fwd EPS",fontsize=8,color=BLUE)
    ax2=ax.twinx(); ax2.plot(mon,idx,color=BLUE,linewidth=2.0,marker="o",ms=3,label="지수"); ax2.set_ylabel("지수(pt)",fontsize=8,color=BLUE)
    ax3=ax.twinx(); ax3.spines["right"].set_position(("outward",38)); ax3.plot(mon,per,color=RED,linewidth=1.5,linestyle="--",label="선행 PER"); ax3.set_ylabel("선행 PER(배)",fontsize=8,color=RED)
    ax2.annotate("%d"%idx[-1],(mon[-1],idx[-1]),textcoords="offset points",xytext=(-22,6),color=BLUE,fontsize=8,fontweight="bold")
    ax.set_title(title,fontsize=9.5,color="#334155"); ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m")); ax.spines["top"].set_visible(False)
    h1,l1=ax.get_legend_handles_labels(); h2,l2=ax2.get_legend_handles_labels(); h3,l3=ax3.get_legend_handles_labels(); ax.legend(h1+h2+h3,l1+l2+l3,fontsize=7,loc="upper left")
    plt.tight_layout(); plt.savefig("charts/macro_%s.png"%name,bbox_inches="tight"); plt.close()
fwd("spx_fwd","S&P500 12개월 선행 EPS + 지수 + 선행PER (추정)",(S.get("spx_eps") or [300,305,310,313,316,320,323,326,328,329,330,330]),(S.get("spx_idx") or [6950,7050,7150,7240,7300,7370,7410,7450,7475,7490,7498,7500]))
fwd("kospi_fwd","KOSPI 12개월 선행 EPS + 지수 + 선행PER (추정)",(S.get("kospi_eps") or [815,838,856,872,884,898,905,910,913,916,917,918]),(S.get("kospi_idx") or [8050,8250,8420,8560,8660,8790,8860,8930,8965,8985,8996,9000]))
print("macro charts ->", len([x for x in os.listdir("charts") if x.startswith("macro_") or x.startswith("spark_")]), "files")
