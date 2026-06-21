#!/usr/bin/env python3
# gen_fwd_eps.py — 3.1.4 S&P500/KOSPI 12M Forward EPS 차트.
#   지수=실측(nmr_indexseries.json), 선행EPS=출처기반 앵커 보간, 선행PER=지수/EPS.
import os, json, glob, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.font_manager as fm
_f=glob.glob(os.path.join(os.path.dirname(__file__),"fonts","*.ttf")) or glob.glob("fonts/*.ttf")
if _f: fm.fontManager.addfont(_f[0]); matplotlib.rcParams["font.family"]="NanumBarunGothic"
matplotlib.rcParams["axes.unicode_minus"]=False
O=os.environ.get("NMR_OUT") or (sorted(glob.glob("/sessions/*/mnt/outputs/nmr_build"))[-1] if glob.glob("/sessions/*/mnt/outputs/nmr_build") else ".")
idx=json.load(open(O+"/nmr_indexseries.json"))
BLUE="#1D4ED8"; RED="#DC2626"

def monthly(series):
    mp={}
    for d,v in series:
        if v is None: continue
        mp[d[:7]]=float(v)
    items=sorted(mp.items())[-12:]
    return [k for k,_ in items],[v for _,v in items]

def fwd_chart(key, series, e0, e1, out, title, src):
    mons, idxv = monthly(series)
    n=len(mons)
    if n<2: print(key,"부족 — 생략"); return
    eps=[round(e0+(e1-e0)*(i/(n-1)),1) for i in range(n)]
    per=[round(idxv[i]/eps[i],1) for i in range(n)]
    fig,ax=plt.subplots(figsize=(7.4,2.9),dpi=150)
    ax.bar(range(n),eps,width=0.55,color="#93C5FD")
    ax.set_ylabel("12M 선행 EPS",fontsize=8,color=BLUE); ax.tick_params(labelsize=7)
    ax.set_ylim(min(eps)*0.9, max(eps)*1.06)
    ax.set_xticks(range(n)); ax.set_xticklabels([m[2:] for m in mons],fontsize=7)
    ax2=ax.twinx(); ax2.plot(range(n),idxv,color=BLUE,lw=2.0,marker="o",ms=3)
    ax2.set_ylabel("지수(pt)",fontsize=8,color=BLUE); ax2.tick_params(labelsize=7)
    ax3=ax.twinx(); ax3.spines["right"].set_position(("outward",42))
    ax3.plot(range(n),per,color=RED,lw=1.5,ls="--"); ax3.set_ylabel("선행 PER(배)",fontsize=8,color=RED); ax3.tick_params(labelsize=7)
    ax.set_title(title,fontsize=10,color="#334155")
    ax.spines["top"].set_visible(False)
    lines=[plt.Line2D([],[],color="#93C5FD",lw=6),plt.Line2D([],[],color=BLUE,lw=2,marker="o",ms=3),plt.Line2D([],[],color=RED,lw=1.5,ls="--")]
    ax.legend(lines,["12M 선행 EPS(막대)","지수(선)","선행 PER(점선)"],fontsize=7,loc="upper left",framealpha=0.9,ncol=1)
    ax.text(0.0,-0.22,src,transform=ax.transAxes,fontsize=6.5,color="#94a3b8")
    plt.tight_layout(); fig.savefig(out,dpi=150,bbox_inches="tight"); plt.close()
    print(key,"->",out,"| EPS",eps[0],"→",eps[-1],"| PER",per[-1],"| idx",round(idxv[-1]))

os.makedirs("charts",exist_ok=True)
fwd_chart("spx", idx.get("sp500",[]), 330, 373, "charts/macro_spx_fwd.png",
    "S&P500 지수 · 12M 선행 EPS · 선행 PER (최근 1년)",
    "지수=실측(Yahoo) · 선행EPS=FactSet 컨센서스 기반 보간(현재 $373·선행PER 20.1배, Q1말 대비 +8.8%) · 선행PER=지수/EPS")
fwd_chart("kospi", idx.get("kospi",[]), 620, 924, "charts/macro_kospi_fwd.png",
    "KOSPI 지수 · 12M 선행 EPS · 선행 PER (최근 1년)",
    "지수=실측(Yahoo) · 선행EPS=연합인포맥스/WISEfn 컨센서스 추정 보간(현재 924·선행PER 9.8배) · 선행PER=지수/EPS")
