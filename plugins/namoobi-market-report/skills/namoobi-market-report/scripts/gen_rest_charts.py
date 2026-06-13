import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
O="/sessions/upbeat-elegant-allen/mnt/outputs"
GRN="#059669"; RED="#DC2626"
def spark(pairs,out):
    ys=[p[1] for p in pairs if p and p[1] is not None]
    if len(ys)<2: return False
    col=GRN if ys[-1]>=ys[0] else RED
    fig,ax=plt.subplots(figsize=(1.5,0.5),dpi=150)
    ax.plot(range(len(ys)),ys,color=col,linewidth=1.1)
    ax.fill_between(range(len(ys)),ys,min(ys),color=col,alpha=0.08)
    ax.axis("off"); ax.margins(x=0,y=0.1); ax.scatter([len(ys)-1],[ys[-1]],color=col,s=6,zorder=5)
    plt.tight_layout(pad=0); plt.savefig(out,bbox_inches="tight",transparent=True); plt.close(); return True
def mini(pairs,out):
    ys=[p[1] for p in pairs if p and p[1] is not None]
    if len(ys)<2: return False
    col=GRN if ys[-1]>=ys[0] else RED
    fig,ax=plt.subplots(figsize=(2.4,0.8),dpi=150)
    ax.plot(range(len(ys)),ys,color=col,linewidth=1.3)
    ax.fill_between(range(len(ys)),ys,min(ys),color=col,alpha=0.10)
    ax.axis("off"); ax.margins(x=0,y=0.12)
    chg=(ys[-1]/ys[0]-1)*100
    ax.set_title(f"{chg:+.0f}% (1Y)",fontsize=8,color=col,fontweight="bold")
    plt.tight_layout(pad=0.2); plt.savefig(out,bbox_inches="tight",transparent=True); plt.close(); return True

# theme 1Y (overwrite)
ts=json.load(open(O+"/nmr_themeseries1y.json"))
tmap={"반도체":"반도체","조선":"조선","방산":"방산","전력":"전력","증권":"증권","로봇":"로봇","우주":"방산"}
for t,k in tmap.items(): mini(ts.get(k,[]), f"charts/theme_{t}.png")

# commodities + strat + fx sparklines (1Y)
s2=json.load(open(O+"/nmr_series2.json"))
for k,v in s2["commodities"].items(): spark(v, f"charts/spark_{k}.png")
sm={"lit":"lit","remx":"remx","ura":"ura","urnm":"urnm"}
for k,v in s2["strat_etf"].items(): spark(v, f"charts/spark_{k}.png")
for k,v in s2["fx"].items(): spark(v, f"charts/spark_{k}.png")
print("sparklines: commodities",len(s2['commodities']),"strat",len(s2['strat_etf']),"fx",len(s2['fx']))

# crypto coin charts: price + volume (1Y)
cs=json.load(open(O+"/nmr_crypto_series.json"))
import matplotlib.dates as mdates
from datetime import datetime
def coin(rows,out,label):
    rows=[r for r in rows if r and r[1] is not None]
    if len(rows)<2: return False
    xs=[datetime.fromisoformat(r[0]) for r in rows]; pr=[r[1] for r in rows]; vol=[r[2] for r in rows]
    col=GRN if pr[-1]>=pr[0] else RED
    fig,(ax1,ax2)=plt.subplots(2,1,figsize=(3.4,2.0),dpi=150,sharex=True,gridspec_kw={"height_ratios":[3,1]})
    ax1.plot(xs,pr,color=col,linewidth=1.2); ax1.fill_between(xs,pr,min(pr),color=col,alpha=0.08)
    chg=(pr[-1]/pr[0]-1)*100
    ax1.set_title(f"{label}  ${pr[-1]:,.2f}  ({chg:+.0f}% 1Y)",fontsize=8,color="#111")
    ax1.tick_params(labelsize=6); ax1.grid(alpha=0.2)
    for s in ["top","right"]: ax1.spines[s].set_visible(False)
    ax2.bar(xs,vol,color="#9ca3af",width=2); ax2.tick_params(labelsize=6); ax2.set_ylabel("Vol",fontsize=6)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m"))
    for s in ["top","right"]: ax2.spines[s].set_visible(False)
    plt.tight_layout(pad=0.3); plt.savefig(out,bbox_inches="tight"); plt.close(); return True
coin(cs["btc"],"charts/coin_btc.png","BTC"); coin(cs["eth"],"charts/coin_eth.png","ETH")
coin(cs["xrp"],"charts/coin_xrp.png","XRP"); coin(cs["sol"],"charts/coin_sol.png","SOL")

# fear & greed 1Y
fng=[r for r in cs["fng"] if r and r[1] is not None]
xs=[datetime.fromisoformat(r[0]) for r in fng]; ys=[r[1] for r in fng]
fig,ax=plt.subplots(figsize=(6.6,1.8),dpi=150)
for lo,hi,c in [(0,25,"#fca5a5"),(25,45,"#fdba74"),(45,55,"#fde68a"),(55,75,"#bbf7d0"),(75,100,"#86efac")]:
    ax.axhspan(lo,hi,color=c,alpha=0.45)
ax.plot(xs,ys,color="#111827",linewidth=1.1)
ax.scatter([xs[-1]],[ys[-1]],color="#dc2626",s=22,zorder=5)
ax.annotate(f"{ys[-1]}",(xs[-1],ys[-1]),fontsize=8,fontweight="bold",color="#dc2626",textcoords="offset points",xytext=(-22,4))
ax.set_ylim(0,100); ax.set_title("Crypto Fear & Greed Index (1Y)",fontsize=9,color="#334155")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m")); ax.tick_params(labelsize=7); ax.grid(alpha=0.15)
for s in ["top","right"]: ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig("charts/fng_1y.png",bbox_inches="tight"); plt.close()
print("crypto+fng done")
import os; print("total chart files:", len([f for f in os.listdir('charts') if f.endswith('.png')]))
