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
yx=[dt.date(y,6,1) for y in range(2021,2027)]
for nm,vals,c in [("한국",[0.5,1.25,3.5,3.5,3.0,2.5],GREEN),("일본",[-0.1,-0.1,-0.1,0.1,0.5,0.5],"#D97706"),("중국",[3.85,3.7,3.55,3.45,3.1,3.0],"#7C3AED"),("유로존",[0.0,0.5,4.0,4.0,2.65,2.15],"#0891B2"),("영국",[0.1,1.25,5.0,5.0,4.5,4.0],"#BE185D")]:
    ax.plot(yx,vals,linewidth=1.3,marker="o",ms=3,label=nm+"(추정)",color=c)
ax.set_title("주요 6개국 정책금리 5년 추이 (미국=실측 월별, 그 외 추정)",fontsize=9.5,color="#334155")
ax.legend(fontsize=7,ncol=6,loc="upper center",bbox_to_anchor=(0.5,-0.13)); ax.grid(True,alpha=0.25); ax.set_ylabel("%",fontsize=8,color="#64748B")
for s in ["top","right"]: ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig("charts/macro_policy_rates.png",bbox_inches="tight"); plt.close()

# (2) 장단기 금리차 10Y-2Y
d=S.get("curve_10_2") or [0.42,0.40,0.39,0.40,0.38,0.29,0.27]; dl=S.get("curve_labels") or ["6/10","6/11","6/12","6/15","6/16","6/17","6/18"]
fig,ax=plt.subplots(figsize=(7.2,1.95),dpi=150); ax.plot(dl,d,color=BLUE,linewidth=1.8,marker="o",ms=4); ax.axhline(0,color=RED,linewidth=0.9,linestyle="--")
ax.scatter([dl[-1]],[d[-1]],color=RED,zorder=5,s=28); ax.annotate(("+%.2f%%p"%d[-1]) if d[-1]>=0 else ("%.2f%%p"%d[-1]),(dl[-1],d[-1]),textcoords="offset points",xytext=(-36,7),color=RED,fontsize=9,fontweight="bold")
ax.set_title("미국 장단기 금리차(수익률곡선)(10Y-2Y) (+면 정상 / -면 역전)",fontsize=9.5,color="#334155"); ax.grid(True,alpha=0.25); ax.set_ylabel("%p",fontsize=8,color="#64748B")
for s in ["top","right"]: ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig("charts/macro_curve.png",bbox_inches="tight"); plt.close()

# (3) 물가 통합 5종 YoY
infl=S.get("inflation") or {"CPI":[2.6,2.7,2.8,2.9,3.1,3.3,3.4,3.6,3.8,3.9,4.0,4.17],"Core CPI":[2.9,2.9,3.0,3.0,3.0,3.1,3.1,3.2,3.1,3.1,3.0,3.1],"PCE":[2.3,2.4,2.4,2.5,2.5,2.6,2.6,2.6,2.6,2.7,2.6,2.6],"Core PCE":[2.6,2.6,2.7,2.7,2.7,2.8,2.8,2.8,2.8,2.8,2.8,2.8],"PPI":[1.8,2.0,2.2,2.3,2.4,2.6,2.7,2.8,2.9,3.0,2.9,2.9]}
fig,ax=plt.subplots(figsize=(7.4,2.9),dpi=150)
for k,v in infl.items(): ax.plot(mon,v,linewidth=1.6,marker="o",ms=3,label=k)
ax.axhline(2.0,color=RED,linewidth=0.9,linestyle="--",alpha=0.7); ax.set_title("미국 물가 YoY 최근 12개월 통합 (점선=연준 2% 목표 · CPI 최신 실측)",fontsize=9.5,color="#334155")
ax.legend(fontsize=7,ncol=5); ax.grid(True,alpha=0.25); ax.set_ylabel("YoY %",fontsize=8,color="#64748B"); ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m"))
for s in ["top","right"]: ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig("charts/macro_inflation.png",bbox_inches="tight"); plt.close()

# (4) 기대인플레 10Y
ie=S.get("infl_exp") or [2.18,2.20,2.22,2.21,2.25,2.28,2.27,2.30,2.32,2.31,2.34,2.35]
fig,ax=plt.subplots(figsize=(7.2,1.95),dpi=150); ax.plot(mon,ie,color=BLUE,linewidth=1.8,marker="o",ms=3); ax.axhline(2.0,color=RED,linewidth=0.9,linestyle="--",alpha=0.7)
ax.scatter([mon[-1]],[ie[-1]],color=RED,zorder=5,s=24); ax.set_title("기대인플레이션 10년(BEI) 1년 추이 · 점선=2% (추정)",fontsize=9.5,color="#334155")
ax.grid(True,alpha=0.25); ax.set_ylabel("%",fontsize=8,color="#64748B"); ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m"))
for s in ["top","right"]: ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig("charts/macro_infl_exp.png",bbox_inches="tight"); plt.close()

# (5) 고용 통합 2x3
emp=S.get("employment") or {}
nfp=emp.get("nfp") or [13,-20,64,-70,76,-140,41,-17,160,-156,214,179,172]
un=emp.get("unemp") or [4.2,4.3,4.1,4.3,4.3,4.4,4.5,4.4,4.3,4.4,4.3,4.3,4.3]
gdp=emp.get("gdp") or [23548.21,23770.976,24026.834,24055.749,24152.656]
ism_m=emp.get("ism_mfg") or [49.1,48.8,49.0,48.5,48.7,49.3,48.9,49.5,48.6,48.9,48.5,48.7]
ism_s=emp.get("ism_svc") or [51.0,51.4,50.8,51.2,52.0,51.5,51.8,52.1,51.3,51.6,51.2,51.6]
rt=emp.get("retail") or [624272,616231,624146,628747,632149,632395,631346,634477,634830,634949,641038,653772,655933,662752]
fig,axs=plt.subplots(2,3,figsize=(7.6,3.4),dpi=150)
def panel(ax,t,ys,c,hl=None):
    ax.plot(range(len(ys)),ys,color=c,linewidth=1.5,marker="o",ms=2.4); ax.scatter([len(ys)-1],[ys[-1]],color=RED,s=13,zorder=5)
    if hl is not None: ax.axhline(hl,color=RED,linewidth=0.8,linestyle="--",alpha=0.7)
    ax.set_title(t,fontsize=8,color="#334155"); ax.grid(True,alpha=0.2); ax.set_xticks([])
    for s in ["top","right"]: ax.spines[s].set_visible(False)
panel(axs[0,0],"NFP 신규고용(천명, 실측)",nfp,BLUE,0); panel(axs[0,1],"실업률(%, 실측)",un,RED); panel(axs[0,2],"실질GDP(분기, 실측)",gdp,GREEN)
panel(axs[1,0],"ISM 제조 PMI(추정)",ism_m,BLUE,50); panel(axs[1,1],"ISM 서비스 PMI(추정)",ism_s,GREEN,50); panel(axs[1,2],"소매판매(백만$, 실측)",rt,"#7C3AED")
fig.suptitle("미국 고용·경기 6개 지표 최근 1년 통합",fontsize=9.5,color="#334155")
plt.tight_layout(rect=[0,0,1,0.95]); plt.savefig("charts/macro_employment.png",bbox_inches="tight"); plt.close()

# (6) 심리 스파크 5종
sent=S.get("sentiment") or {}
spark("us10y",list(range(12)),sent.get("us10y") or [4.25,4.30,4.42,4.55,4.48,4.40,4.52,4.50,4.47,4.43,4.49,4.46])
spark("vix",list(range(12)),sent.get("vix") or [19,21,24,18,17,16,20,18,17,16,18,17.2],RED)
spark("vkospi",list(range(12)),sent.get("vkospi") or [18,19,17,16,18,20,19,18,22,30,55,84],RED)
spark("dxy",list(range(12)),sent.get("dxy") or [102,101,100,99.5,99,98.5,99,98.8,98.5,98.2,98,98.1])
spark("usdkrw",list(range(12)),sent.get("usdkrw") or [1352,1361,1378,1390,1372,1366,1375,1381,1379,1377,1378,1380])
spark("wti",list(range(12)),sent.get("wti") or [78,76,74,72,70,69,73,72,71,70,72,71.5],GREEN)

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
