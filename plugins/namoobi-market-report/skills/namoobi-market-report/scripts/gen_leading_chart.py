import json,sys,os,glob,matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.font_manager as fm
from datetime import datetime
O=sys.argv[1] if len(sys.argv)>1 else (os.environ.get("NMR_OUT") or sorted(glob.glob("/sessions/*/mnt/outputs"))[-1])
fp=[p for p in [os.path.join(os.path.dirname(__file__),"fonts","nmr_kr.ttf"),"fonts/nmr_kr.ttf"] if os.path.exists(p)]
if fp: fm.fontManager.addfont(fp[0]); matplotlib.rcParams["font.family"]="NanumBarunGothic"
matplotlib.rcParams["axes.unicode_minus"]=False
s=json.load(open(O+"/nmr_leading_series.json"))
xs=[datetime.strptime(d,"%Y-%m") for d,_ in s]; ys=[v for _,v in s]
fig,ax=plt.subplots(figsize=(7.2,2.7),dpi=150)
ax.plot(xs,ys,color="#e11d48",lw=1.6)
ax.fill_between(xs,ys,min(ys)-0.3,color="#e11d48",alpha=0.07)
ax.axhline(100,color="#94a3b8",lw=0.9,ls="--"); ax.text(xs[0],100.05,"기준선 100",fontsize=7,color="#64748b",va="bottom")
ax.scatter([xs[-1]],[ys[-1]],color="#e11d48",s=26,zorder=5)
ax.annotate(f"{ys[-1]:.1f}",(xs[-1],ys[-1]),fontsize=9,fontweight="bold",color="#e11d48",textcoords="offset points",xytext=(-4,8),ha="right")
ax.set_title("선행종합지수 순환변동치 (월별, 2016.06~2026.04)",fontsize=10,color="#334155")
import matplotlib.dates as mdates
ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.tick_params(labelsize=7); ax.grid(alpha=0.18)
for sp in ["top","right"]: ax.spines[sp].set_visible(False)
ax.text(0.012,0.06,"출처: 국가데이터처 / INDEXerGO",transform=ax.transAxes,fontsize=7,color="#94a3b8")
plt.tight_layout(pad=0.4); fig.savefig("charts/leading_cycle.png",dpi=150,bbox_inches="tight"); print("leading chart done")
