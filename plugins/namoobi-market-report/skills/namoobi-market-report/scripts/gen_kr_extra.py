# gen_kr_extra.py (v3.6.18) — 보조 차트 일괄 생성 + 매니페스트
# 빌더는 각 행/필드의 chart 경로를 데이터에서 읽으므로, 여기서 생성한 PNG 경로를
# nmr_chart_manifest.json 으로 내보내 Phase 3 병합이 결정적으로 wire 하게 한다.
#
# 입력(있는 것만 처리, 없으면 건너뜀):
#   <O>/nmr_semi_etf20_raw.json : {"mc":{code:[name,cap]}, "series":{code:[[date,close]..]}}  → 3.1.4 반도체/AI ETF20
#   <O>/nmr_semi_series_v3.json  (또는 nmr_semi_series2.json) : {name:[[date,close]..]}        → 3.1.4 종목 미니차트
#   <O>/nmr_theme_etf.json : {"series":{theme:[[date,close]..]}, "etfs":{theme:{"name":..}}}   → 3.1.4 테마8 차트(우주 분리)
#   <O>/hy_oas.csv : 'YYYY-MM-DD,oas;...' (FRED BAMLH0A0HYM2 1년 일별)                          → 3.2.1 charts/hy_oas_chart.png
# 출력: charts/*.png + <O>/nmr_chart_manifest.json
#   {"etf":{code:path}, "stock":{name:path}, "theme":{name:{"chart":path,"etf":etfname}}}
import sys, os, glob, json, re
import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm, matplotlib.pyplot as plt
_f=[p for p in [os.path.join(os.path.dirname(__file__),"fonts","nmr_kr.ttf"),"fonts/nmr_kr.ttf"] if os.path.exists(p)]
if _f: fm.fontManager.addfont(_f[0]); matplotlib.rcParams["font.family"]="NanumBarunGothic"
matplotlib.rcParams["axes.unicode_minus"]=False
O = sys.argv[1] if len(sys.argv)>1 else (os.environ.get("NMR_OUT") or sorted(glob.glob("/sessions/*/mnt/outputs"))[-1])
os.makedirs("charts", exist_ok=True)
GRN="#059669"; RED="#DC2626"
def load(name):
    p=os.path.join(O,name)
    return json.load(open(p,encoding="utf-8")) if os.path.exists(p) else None
def safe(s): return re.sub(r"[^0-9A-Za-z가-힣]","_", str(s))
def mini(pairs, out, label="1Y"):
    ys=[p[1] for p in (pairs or []) if p and p[1] is not None]
    if len(ys)<2: return False
    col=GRN if ys[-1]>=ys[0] else RED
    fig,ax=plt.subplots(figsize=(2.4,0.8),dpi=150)
    ax.plot(range(len(ys)),ys,color=col,lw=1.3)
    ax.fill_between(range(len(ys)),ys,min(ys),color=col,alpha=0.10); ax.axis("off"); ax.margins(x=0,y=0.12)
    chg=(ys[-1]/ys[0]-1)*100
    ax.set_title(f"{chg:+.0f}% ({label})",fontsize=8,color=col,fontweight="bold")
    plt.tight_layout(pad=0.2); plt.savefig(out,bbox_inches="tight",transparent=True); plt.close(); return True

manifest={"etf":{}, "stock":{}, "theme":{}}

# 1) 반도체/AI ETF 20 (다음 charts 시계열). 상장 1년 미만(짧은 series)은 '상장후' 라벨.
se=load("nmr_semi_etf20_raw.json")
if se and isinstance(se.get("series"),dict):
    for code,s in se["series"].items():
        out=f"charts/semietf_{safe(code)}.png"
        recent = len(s)<30
        if mini(s,out,"상장후" if recent else "1Y"): manifest["etf"][code]=out
    print("semi ETF charts:", len(manifest["etf"]))

# 2) 반도체/AI 종목 미니차트
ss=load("nmr_semi_series_v3.json") or load("nmr_semi_series2.json")
if isinstance(ss,dict):
    for name,s in ss.items():
        out=f"charts/semi_{safe(name)}.png"
        if mini(s,out): manifest["stock"][name]=out
    print("semi stock charts:", len(manifest["stock"]))

# 3) 테마 8개 (우주 분리). 슬래시/공백 포함 테마명 sanitize.
te=load("nmr_theme_etf.json")
if te and isinstance(te.get("series"),dict):
    etfs=te.get("etfs",{})
    for t,s in te["series"].items():
        out=f"charts/theme_{safe(t)}.png"
        ok=mini(s,out)
        manifest["theme"][t]={"chart": out if ok else "", "etf": (etfs.get(t,{}) or {}).get("name","-")}
    print("theme charts:", sum(1 for v in manifest["theme"].values() if v["chart"]))

# 4) HY OAS 1년 차트 (FRED). hy_oas.csv = 'date,oas;...'
hp=os.path.join(O,"hy_oas.csv")
if os.path.exists(hp):
    import matplotlib.dates as mdates
    from datetime import datetime
    rows=[r.split(",") for r in open(hp).read().strip().split(";") if r]
    xs=[datetime.fromisoformat(r[0]) for r in rows]; ys=[float(r[1]) for r in rows]
    fig,ax=plt.subplots(figsize=(6.5,1.9),dpi=150)
    ax.plot(xs,ys,color="#dc2626",lw=1.1); ax.fill_between(xs,ys,min(ys),color="#fca5a5",alpha=0.15)
    ax.scatter([xs[-1]],[ys[-1]],color="#b91c1c",s=18,zorder=5)
    ax.annotate(f"{ys[-1]:.2f}%",(xs[-1],ys[-1]),fontsize=8,fontweight="bold",color="#b91c1c",textcoords="offset points",xytext=(-30,4))
    ax.set_title("미국 하이일드 OAS (ICE BofA, 1년)",fontsize=9,color="#334155")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m")); ax.tick_params(labelsize=7); ax.grid(alpha=0.2)
    for sp in ["top","right"]: ax.spines[sp].set_visible(False)
    plt.tight_layout(); fig.savefig("charts/hy_oas_chart.png",bbox_inches="tight"); plt.close()
    manifest["hy"]="charts/hy_oas_chart.png"; print("hy chart done")

json.dump(manifest, open(os.path.join(O,"nmr_chart_manifest.json"),"w"), ensure_ascii=False)
print("manifest:", os.path.join(O,"nmr_chart_manifest.json"))
