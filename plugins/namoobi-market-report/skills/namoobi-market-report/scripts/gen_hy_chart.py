import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
d=json.load(open("hy_oas.json"))
series=d["series"]
xs=[datetime.fromisoformat(p[0]) for p in series]
ys=[p[1] for p in series]
pts=d["points"]
fig,ax=plt.subplots(figsize=(7.2,2.6),dpi=150)
ax.plot(xs,ys,color="#1E40AF",linewidth=1.6)
ax.fill_between(xs,ys,min(ys)-0.1,color="#1E40AF",alpha=0.07)
cur=pts["current"]
ax.scatter([datetime.fromisoformat(cur[0])],[cur[1]],color="#DC2626",zorder=5,s=28)
ax.annotate(f"{cur[1]:.2f}%",(datetime.fromisoformat(cur[0]),cur[1]),textcoords="offset points",xytext=(-32,6),color="#DC2626",fontsize=9,fontweight="bold")
ax.set_title("US High Yield OAS  (FRED BAMLH0A0HYM2, daily)",fontsize=10,color="#334155")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m"))
ax.grid(True,alpha=0.25)
for s in ["top","right"]: ax.spines[s].set_visible(False)
ax.set_ylabel("OAS (%)",fontsize=8,color="#64748B")
plt.tight_layout()
plt.savefig("hy_oas_chart.png",bbox_inches="tight")
print("chart saved", )
