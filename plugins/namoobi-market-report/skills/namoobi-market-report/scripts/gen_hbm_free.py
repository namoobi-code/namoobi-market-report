#!/usr/bin/env python3
# gen_hbm_free.py — 무료 공개 출처(TrendForce 보도·언론 인용)에서 확인된 '시점값'만으로
#   DDR5 가격 추이 + HBM3E:DDR5 프리미엄 배수 별도 그래프 생성 (유료 DataTrack 미사용).
import json, os, sys, glob, re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
O = sys.argv[1] if (len(sys.argv)>1 and os.path.isdir(sys.argv[1])) else (os.environ.get("NMR_OUT") or ".")
for fp in [os.path.join(O,"fonts","nmr_kr.ttf"), os.path.join(os.path.dirname(os.path.abspath(__file__)),"fonts","nmr_kr.ttf")]:
    if os.path.exists(fp):
        try: fm.fontManager.addfont(fp); plt.rcParams["font.family"]=fm.FontProperties(fname=fp).get_name()
        except Exception: pass
        break
plt.rcParams["axes.unicode_minus"]=False
def load():
    for p in [os.path.join(O,"nmr_hbm_free.json")]+glob.glob("/sessions/*/mnt/outputs/nmr_build/nmr_hbm_free.json")+glob.glob("/sessions/*/mnt/claudeCowork/_market_report_data/nmr_hbm_free.json"):
        try: return json.load(open(p,encoding="utf-8"))
        except Exception: pass
    return {}
d=load(); dram=d.get("dram_series") or []; gap=d.get("gap_series") or []
def midnum(v):
    if isinstance(v,(int,float)): return float(v)
    s=str(v).replace(">","").replace("<","").replace("배","").replace("x","").strip()
    m=re.findall(r"[\d.]+", s)
    if not m: return None
    if "~" in s and len(m)>=2: return (float(m[0])+float(m[1]))/2
    return float(m[0])
BLUE="#1D4ED8"; RED="#DC2626"; SLATE="#334155"; GREEN="#059669"
fig,axs=plt.subplots(1,2,figsize=(11.0,3.5),dpi=150)
# Panel A: DDR5 16Gb 칩 가격 (spot/contract) 시점값
chip=[(x.get("date"),midnum(x.get("value")),x.get("metric","")) for x in dram if "DDR5_16Gb_chip" in str(x.get("metric",""))]
chip=[c for c in chip if c[1] is not None]
chip.sort(key=lambda z:str(z[0]))
ax=axs[0]
if chip:
    xs=[c[0] for c in chip]; ys=[c[1] for c in chip]
    ax.plot(range(len(xs)),ys,color=BLUE,marker="o",ms=6,linewidth=2)
    for i,(x,y,mt) in enumerate(chip):
        ax.annotate(f"${y:g}",(i,y),textcoords="offset points",xytext=(0,8),ha="center",fontsize=9,color=SLATE,fontweight="bold")
    ax.set_xticks(range(len(xs))); ax.set_xticklabels(xs,fontsize=8,rotation=0)
    ax.set_title("DDR5 16Gb 칩 가격 ($/칩) — 무료 공개 시점값",fontsize=10,color=SLATE)
    ax.set_ylabel("USD / 16Gb",fontsize=8,color="#64748B"); ax.grid(True,alpha=0.25)
else:
    ax.axis("off"); ax.text(0.5,0.5,"무료 시점값 미확보",ha="center",va="center",color="#94A3B8")
for s in ["top","right"]: ax.spines[s].set_visible(False)
# Panel B: HBM3E:DDR5 프리미엄 배수
gp=[(str(x.get("period")),midnum(x.get("ratio"))) for x in gap if midnum(x.get("ratio")) is not None]
ax=axs[1]
if gp:
    xs=[g[0] for g in gp]; ys=[g[1] for g in gp]
    bars=ax.bar(range(len(xs)),ys,color=[RED if "26" in x else BLUE for x in xs],alpha=0.85,width=0.55)
    for i,y in enumerate(ys): ax.annotate(f"{y:g}x",(i,y),textcoords="offset points",xytext=(0,4),ha="center",fontsize=9,color=SLATE,fontweight="bold")
    ax.set_xticks(range(len(xs))); ax.set_xticklabels(xs,fontsize=9)
    ax.set_title("HBM3E : DDR5 가격 프리미엄(배) — 무료 공개",fontsize=10,color=SLATE)
    ax.set_ylabel("배수(x)",fontsize=8,color="#64748B"); ax.grid(True,alpha=0.25,axis="y")
else:
    ax.axis("off"); ax.text(0.5,0.5,"무료 시점값 미확보",ha="center",va="center",color="#94A3B8")
for s in ["top","right"]: ax.spines[s].set_visible(False)
fig.suptitle("무료 공개 출처 실측 — DDR5 가격·HBM 프리미엄 (TrendForce 보도·언론 인용, 시점값)",fontsize=10.5,color=SLATE)
os.makedirs("charts",exist_ok=True)
plt.tight_layout(rect=[0,0,1,0.93]); plt.savefig("charts/hbm_free.png",bbox_inches="tight"); plt.close()
print("hbm_free chart -> charts/hbm_free.png | dram_chip_pts",len(chip),"gap_pts",len(gp))
# EOF — namoobi-market-report gen_hbm_free
