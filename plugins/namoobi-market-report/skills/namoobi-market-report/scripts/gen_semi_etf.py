import json,os,sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE=os.path.dirname(__file__); CH=os.path.join(HERE,"charts")
GRN,RED="#059669","#DC2626"
d=json.load(open(os.path.join(HERE,"etf_compact.json")))
def mini(ys,out):
    if len(ys)<2: return False
    col=GRN if ys[-1]>=ys[0] else RED
    fig,ax=plt.subplots(figsize=(2.5,0.82),dpi=150)
    pos=[y for y in ys if y and y>0]
    logged=len(pos)>=2 and (max(pos)/min(pos))>3
    if logged: ax.set_yscale("log")
    ax.plot(range(len(ys)),ys,color=col,linewidth=1.3)
    ax.fill_between(range(len(ys)),ys,min(ys),color=col,alpha=0.10)
    ax.axis("off"); ax.margins(x=0,y=0.12)
    chg=(ys[-1]/ys[0]-1)*100 if ys[0] else 0
    ax.set_title(f"{chg:+.0f}% (1Y)"+("  ·로그" if logged else ""),fontsize=8,color=col,fontweight="bold")
    plt.tight_layout(pad=0.2); plt.savefig(out,bbox_inches="tight",transparent=True); plt.close(); return True
c=0
for k,ys in d.items():
    if mini(ys, os.path.join(CH,f"semi_e_{k}.png")): c+=1
print("semi_e charts:",c)
