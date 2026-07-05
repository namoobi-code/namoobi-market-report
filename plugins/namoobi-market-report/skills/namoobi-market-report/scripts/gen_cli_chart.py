# 3.1.4 OECD 경기선행지수(CLI) 통합 차트 — 모든 나라 1장 (v3.43)
# 출력: charts/oecd_cli.png
# 입력 우선순위:
#   1) <O>/nmr_oecd_cli.json  (이번 실행 KOSIS 신규 스크랩분 — Chrome, 자료갱신일 변경 시에만 생성)
#   2) 폴백: 통합 DB db/oecd_cli.json 의 data (변동 없으면 항상 이 경로 — 비차단)
# 데이터 스키마: {"months":["YYYY.MM",...], "series":{"국가명":[v,...]}, "unit","source","data_updated"}
import json, sys, os, glob, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.font_manager as fm

_f=[p for p in [os.path.join(os.path.dirname(__file__),"fonts","nmr_kr.ttf"),"fonts/nmr_kr.ttf"] if os.path.exists(p)]
if _f: fm.fontManager.addfont(_f[0]); matplotlib.rcParams["font.family"]="NanumBarunGothic"
matplotlib.rcParams["axes.unicode_minus"]=False

_a1=sys.argv[1] if len(sys.argv)>1 else None
O=(_a1 if (_a1 and not _a1.endswith(".json") and os.path.isdir(_a1)) else
   (os.environ.get("NMR_OUT") or (sorted(glob.glob("/sessions/*/mnt/outputs"))[-1] if glob.glob("/sessions/*/mnt/outputs") else ".")))
os.makedirs("charts", exist_ok=True)

def _load(p):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return None

d=None
fresh=_load(os.path.join(O,"nmr_oecd_cli.json"))
if isinstance(fresh,dict) and fresh.get("months") and fresh.get("series"): d=fresh
if d is None:
    for base in (glob.glob("/sessions/*/mnt/claudeCowork/_market_report_data/db/oecd_cli.json")+
                 glob.glob("/sessions/*/mnt/outputs/_market_report_data/db/oecd_cli.json")+
                 [os.path.join(O,"_market_report_data","db","oecd_cli.json")]):
        e=_load(base)
        if isinstance(e,dict) and isinstance(e.get("data"),dict) and e["data"].get("months"):
            d=e["data"]; break
if d is None:
    print("gen_cli_chart: 데이터 없음(nmr_oecd_cli.json·db/oecd_cli.json 모두 부재) — 차트 생략(비차단)"); sys.exit(0)

months=[str(m) for m in d["months"]]
series={k:v for k,v in (d.get("series") or {}).items() if isinstance(v,list) and any(x is not None for x in v)}
if not months or not series:
    print("gen_cli_chart: months/series 비어있음 — 차트 생략(비차단)"); sys.exit(0)

items=sorted(series.items(), key=lambda kv: next((x for x in reversed(kv[1]) if x is not None), -1e9), reverse=True)
cmap=plt.get_cmap("tab20"); colors={name:cmap(i%20) for i,(name,_) in enumerate(items)}
x=list(range(len(months)))
fig,ax=plt.subplots(figsize=(16,9),dpi=150)
for name,vals in items:
    vv=[(v if v is not None else float("nan")) for v in vals][:len(months)]
    lw=3.2 if name=="대한민국" else 1.8
    ax.plot(x[:len(vv)],vv,linewidth=lw,color=colors[name],zorder=5 if name=="대한민국" else 3)

flat=[v for vv in series.values() for v in vv if v is not None]
ymin,ymax=min(flat),max(flat); span=(ymax-ymin) or 1.0
last=[(n,next((v for v in reversed(vv) if v is not None),None)) for n,vv in items]
last=[(n,v) for n,v in last if v is not None]
gap=span*0.028; adj=[v for _,v in last]
for i in range(1,len(adj)):
    if adj[i-1]-adj[i]<gap: adj[i]=adj[i-1]-gap
for (name,val),ay in zip(last,adj):
    ax.annotate("%s (%.2f)"%(name,val),xy=(x[-1],val),xytext=(x[-1]+0.8,ay),fontsize=12,
                color=colors[name],va="center",fontweight="bold" if name=="대한민국" else "normal")
ax.axhline(100,color="gray",linestyle="--",linewidth=1.1,alpha=0.8)
step=max(1,len(months)//18); ticks=list(range(0,len(months),step))
if ticks and ticks[-1]!=len(months)-1: ticks.append(len(months)-1)
ax.set_xticks(ticks); ax.set_xticklabels([months[i].replace("20","'",1) for i in ticks],fontsize=10,rotation=45,ha="right")
ax.tick_params(axis="y",labelsize=12)
ax.set_xlim(-0.5,len(months)-1+max(6,len(months)*0.16))
ax.set_ylim(ymin-span*0.04,ymax+span*0.04)
ax.set_xlabel("월",fontsize=13); ax.set_ylabel("지수 (진폭조정, CLI)",fontsize=13)
ax.set_title("OECD 종합선행지표(CLI) — 국가별 통합 추이 (%s ~ %s)"%(months[0],months[-1]),fontsize=16,pad=12)
ax.grid(True,alpha=0.3)
for s in ("top","right"): ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig("charts/oecd_cli.png",bbox_inches="tight"); plt.close(fig)
print("gen_cli_chart: charts/oecd_cli.png (%d개월 x %d개국, 기준 %s)"%(len(months),len(items),d.get("data_updated") or d.get("data_downloaded") or "-"))
# EOF — namoobi-market-report gen_cli_chart.py
