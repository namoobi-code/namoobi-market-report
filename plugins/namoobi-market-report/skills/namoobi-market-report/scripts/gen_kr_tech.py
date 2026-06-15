# 3.1.1 한국 기술차트 (v3.6.16) — 다음금융 동일출처 1년 일별(종가·거래량·외국인/기관/개인 순매수) 기반.
# 지수 OHLC 캔들 API(/api/charts/...)는 403이므로 종가선 기반 멀티패널을 그린다.
# 입력: <O>/kospi_daily.csv, <O>/kosdaq_daily.csv  (각 행 'YYYY-MM-DD,close,vol,foreign억,inst억,indiv억' ';'구분)
# 출력: charts/kospi_tech.png, charts/kosdaq_tech.png
import sys, glob, os, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm, matplotlib.pyplot as plt, matplotlib.dates as mdates
from matplotlib.lines import Line2D
_font=[p for p in [os.path.join(os.path.dirname(__file__),"fonts","nmr_kr.ttf"),"fonts/nmr_kr.ttf"] if os.path.exists(p)]
if _font: fm.fontManager.addfont(_font[0]); matplotlib.rcParams["font.family"]="NanumBarunGothic"
matplotlib.rcParams["axes.unicode_minus"]=False
O = sys.argv[1] if len(sys.argv)>1 else (os.environ.get("NMR_OUT") or sorted(glob.glob("/sessions/*/mnt/outputs"))[-1])
def load(p):
    rows=[r for r in open(p).read().strip().split(";") if r]
    df=pd.DataFrame([r.split(",") for r in rows],columns=["Date","Close","Vol","F","I","P"])
    df["Date"]=pd.to_datetime(df["Date"])
    for c in ["Close","Vol","F","I","P"]: df[c]=pd.to_numeric(df[c])
    return df.set_index("Date").sort_index()
def rsi(c,n=14):
    d=c.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0)
    return 100-100/(1+up.ewm(alpha=1/n,adjust=False).mean()/dn.ewm(alpha=1/n,adjust=False).mean().replace(0,np.nan))
def tech(df,out,title):
    c=df["Close"]; mid=c.rolling(20).mean(); std=c.rolling(20).std()
    cF=df["F"].cumsum()/1e4; cI=df["I"].cumsum()/1e4; cP=df["P"].cumsum()/1e4
    fig,(a1,a2,a3,a4)=plt.subplots(4,1,figsize=(11,8.2),dpi=150,sharex=True,gridspec_kw={"height_ratios":[6,1.3,1.5,2.2]})
    a1.plot(df.index,c,color="#111827",lw=1.3,label="종가")
    for w,col in [(5,"#f59e0b"),(20,"#2563eb"),(60,"#16a34a"),(120,"#9333ea")]: a1.plot(df.index,c.rolling(w).mean(),lw=0.8,color=col,label=f"MA{w}")
    a1.plot(df.index,mid+2*std,color="#3b82f6",lw=0.6,ls="--"); a1.plot(df.index,mid-2*std,color="#10b981",lw=0.6,ls="--")
    a1.fill_between(df.index,mid-2*std,mid+2*std,color="#93c5fd",alpha=0.07)
    a1.set_title(title,fontsize=11); a1.legend(loc="upper left",fontsize=7,ncol=6,frameon=False); a1.grid(alpha=0.2); a1.tick_params(labelsize=7)
    a2.bar(df.index,df["Vol"]/1e3,color="#9ca3af",width=1.0); a2.set_ylabel("거래량(천)",fontsize=7); a2.tick_params(labelsize=6); a2.grid(alpha=0.15)
    a3.plot(df.index,rsi(c),color="#d97706",lw=0.9); a3.axhline(70,color="#cbd5e1",lw=0.5); a3.axhline(30,color="#cbd5e1",lw=0.5)
    a3.set_ylim(0,100); a3.set_ylabel("RSI",fontsize=7); a3.tick_params(labelsize=6); a3.grid(alpha=0.15)
    a4.plot(df.index,cF,color="#dc2626",lw=1.2); a4.plot(df.index,cI,color="#2563eb",lw=1.2); a4.plot(df.index,cP,color="#059669",lw=1.2)
    a4.axhline(0,color="#9ca3af",lw=0.5); a4.set_ylabel("누적순매수(조원)",fontsize=7); a4.tick_params(labelsize=6); a4.grid(alpha=0.15)
    a4.legend(handles=[Line2D([0],[0],color="#dc2626",lw=1.4,label="외국인"),Line2D([0],[0],color="#2563eb",lw=1.4,label="기관"),Line2D([0],[0],color="#059669",lw=1.4,label="개인")],loc="upper left",fontsize=7,ncol=3,frameon=False)
    a4.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m"))
    for ax in (a1,a2,a3,a4):
        for s in ["top","right"]: ax.spines[s].set_visible(False)
    plt.tight_layout(pad=0.4); fig.savefig(out,dpi=150,bbox_inches="tight"); plt.close(fig)
if os.path.exists(O+"/kospi_daily.csv"): tech(load(O+"/kospi_daily.csv"),"charts/kospi_tech.png","KOSPI 1년 일별 — 종가+이동평균(5/20/60/120)+볼린저밴드 / 거래량 / RSI / 누적순매수")
if os.path.exists(O+"/kosdaq_daily.csv"): tech(load(O+"/kosdaq_daily.csv"),"charts/kosdaq_tech.png","KOSDAQ 1년 일별 — 종가+이동평균(5/20/60/120)+볼린저밴드 / 거래량 / RSI / 누적순매수")
print("kr tech charts done")
