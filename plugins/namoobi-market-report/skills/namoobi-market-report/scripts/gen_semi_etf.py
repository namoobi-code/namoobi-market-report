import json,os,sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
HERE=os.path.dirname(__file__); CH=os.path.join(HERE,"charts")
fp=os.path.join(HERE,"fonts","nmr_kr.ttf")
if os.path.exists(fp):
    font_manager.fontManager.addfont(fp)
    matplotlib.rcParams["font.family"]=font_manager.FontProperties(fname=fp).get_name()
matplotlib.rcParams["axes.unicode_minus"]=False
GRN,RED="#059669","#DC2626"
d=json.load(open(os.path.join(HERE,"etf_compact.json")))
def mini(ys,out):
    ys=[y for y in ys if y is not None]
    if len(ys)<2: return False
    col=GRN if ys[-1]>=ys[0] else RED
    fig,ax=plt.subplots(figsize=(2.5,1.45),dpi=150)
    pos=[y for y in ys if y>0]
    if len(pos)>=2 and (max(pos)/min(pos))>3: ax.set_yscale("log")
    ax.plot(range(len(ys)),ys,color=col,linewidth=1.9)
    ax.fill_between(range(len(ys)),ys,min(ys),color=col,alpha=0.08)
    ax.scatter([len(ys)-1],[ys[-1]],color=col,s=16,zorder=5)
    ax.axis("off"); ax.margins(x=0.02,y=0.10)
    chg=(ys[-1]/ys[0]-1)*100 if ys[0] else 0
    ax.set_title(f"{chg:+.0f}% (1Y)",fontsize=9,color=col,fontweight="bold")
    plt.tight_layout(pad=0.2); plt.savefig(out,bbox_inches="tight",transparent=True); plt.close(); return True
c=0
for k,ys in d.items():
    if mini(ys, os.path.join(CH,f"semi_e_{k}.png")): c+=1
print("semi_e charts:",c)
