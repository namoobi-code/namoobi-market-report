import json, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import mplfinance as mpf
O="/sessions/upbeat-elegant-allen/mnt/outputs"
kr=json.load(open(O+"/nmr_kr_ohlcv.json"))
def rsi(close,n=14):
    d=close.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0)
    ru=up.ewm(alpha=1/n,adjust=False).mean(); rd=dn.ewm(alpha=1/n,adjust=False).mean()
    return 100-100/(1+ru/rd.replace(0,np.nan))
def tech(ohlcv,flows,out,title):
    df=pd.DataFrame(ohlcv,columns=["Date","Open","High","Low","Close","Volume"])
    df["Date"]=pd.to_datetime(df["Date"]); df=df.set_index("Date").sort_index()
    mid=df["Close"].rolling(20).mean(); std=df["Close"].rolling(20).std()
    bbu=mid+2*std; bbd=mid-2*std; r=rsi(df["Close"])
    if flows:
        fdf=pd.DataFrame(flows,columns=["Date","F","I","P"]); fdf["Date"]=pd.to_datetime(fdf["Date"]); fdf=fdf.set_index("Date").sort_index()
        fdf=fdf.reindex(df.index).fillna(0.0)
        cF=fdf["F"].cumsum()/10000.0; cI=fdf["I"].cumsum()/10000.0; cP=fdf["P"].cumsum()/10000.0
    else: cF=cI=cP=pd.Series(0,index=df.index)
    mc=mpf.make_marketcolors(up="#e11d48",down="#2563eb",edge="inherit",wick="inherit",volume="#9ca3af")
    style=mpf.make_mpf_style(marketcolors=mc,gridstyle=":",gridcolor="#e5e7eb",facecolor="white",rc={"font.size":8})
    ap=[mpf.make_addplot(bbu,color="#3b82f6",width=0.7),mpf.make_addplot(bbd,color="#10b981",width=0.7),
        mpf.make_addplot(r,panel=2,color="#d97706",width=0.9,ylabel="RSI"),
        mpf.make_addplot(pd.Series(70,index=df.index),panel=2,color="#cbd5e1",width=0.5),
        mpf.make_addplot(pd.Series(30,index=df.index),panel=2,color="#cbd5e1",width=0.5),
        mpf.make_addplot(cF,panel=3,color="#dc2626",width=1.1,ylabel="CumNetBuy(tril)"),
        mpf.make_addplot(cI,panel=3,color="#2563eb",width=1.1),
        mpf.make_addplot(cP,panel=3,color="#059669",width=1.1)]
    fig,axes=mpf.plot(df,type="candle",style=style,mav=(5,20,60,120),volume=True,addplot=ap,
      panel_ratios=(6,1.2,1.4,2.0),figratio=(15,10),figscale=1.15,returnfig=True,
      datetime_format="%y/%m",xrotation=0,tight_layout=True,title=dict(title=title,fontsize=11))
    axes[6].legend(handles=[Line2D([0],[0],color="#dc2626",lw=1.4,label="Foreign"),
                            Line2D([0],[0],color="#2563eb",lw=1.4,label="Institution"),
                            Line2D([0],[0],color="#059669",lw=1.4,label="Individual")],
                   loc="upper left",fontsize=6.5,frameon=False,ncol=3)
    fig.savefig(out,dpi=150,bbox_inches="tight"); plt.close(fig)
tech(kr["kospi_ohlcv"],kr.get("kospi_flows_daily"),"charts/kospi_tech.png","KOSPI 1Y — Candle+MA(5/20/60/120)+BB / Volume / RSI / Cumulative Net-Buy")
tech(kr["kosdaq_ohlcv"],kr.get("kosdaq_flows_daily"),"charts/kosdaq_tech.png","KOSDAQ 1Y — Candle+MA(5/20/60/120)+BB / Volume / RSI / Cumulative Net-Buy")
print("wide tech charts done")
