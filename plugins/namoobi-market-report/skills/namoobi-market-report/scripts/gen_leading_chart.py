# 3.1.5 경기선행지수 순환변동치 차트 — robust (v3.6.31)
# 출력: charts/leading_cycle.png
# 입력 우선순위:
#   1) 장기 series: <O>/nmr_leading_series.json  ([["YYYY-MM",value],...] 2016~현재, INDEXerGO echarts 추출)
#   2) 폴백: report_data 의 markets.korea_leading[].value (최근 3~4개월) — 장기 series 미수집 시에도 항상 그래프
# (구버전 버그: nmr_leading_series.json 필수라 미수집 시 FileNotFoundError 크래시 → 3.1.5 그래프 없음/이상.)
import json, sys, os, glob, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.font_manager as fm, matplotlib.dates as mdates
from datetime import datetime
_f=[p for p in [os.path.join(os.path.dirname(__file__),"fonts","nmr_kr.ttf"),"fonts/nmr_kr.ttf"] if os.path.exists(p)]
if _f: fm.fontManager.addfont(_f[0]); matplotlib.rcParams["font.family"]="NanumBarunGothic"
matplotlib.rcParams["axes.unicode_minus"]=False
_a1=sys.argv[1] if len(sys.argv)>1 else None
O=(_a1 if (_a1 and not _a1.endswith(".json") and os.path.isdir(_a1)) else
   (os.environ.get("NMR_OUT") or (sorted(glob.glob("/sessions/*/mnt/outputs"))[-1] if glob.glob("/sessions/*/mnt/outputs") else ".")))
os.makedirs("charts", exist_ok=True)
def parsem(s):
    s=str(s).strip().replace(".","-")
    while s.endswith("-"): s=s[:-1]
    for f in ("%Y-%m-%d","%Y-%m"):
        try: return datetime.strptime(s[:10] if f=="%Y-%m-%d" else s[:7], f)
        except Exception: pass
    return None
def _report_path():
    for a in sys.argv[1:]:
        if a.endswith(".json") and os.path.exists(a): return a
    c=sorted(glob.glob(O+"/_market_report_data/report_data_*.json")) or sorted(glob.glob(O+"/report_data_*.json"))
    return c[-1] if c else None
pts=None
ls=O+"/nmr_leading_series.json"
if os.path.exists(ls):
    try:
        s=json.load(open(ls)); pp=[(parsem(d),float(v)) for d,v in s if v is not None and parsem(d)]
        if len(pp)>=2: pts=sorted(pp,key=lambda z:z[0])
    except Exception: pts=None
# (v3.56) 2순위 폴백: 통합 DB 누적 시계열 db/series_leading.json
#   nmr_leading_series.json 미수집 회차에도 과거 28개월+ 시계열로 차트를 그린다.
if not pts or len(pts)<2:
    for _dbp in (sorted(glob.glob(O+"/namoobi-market-report-server/db/series_leading.json")) +
                 sorted(glob.glob(O+"/../namoobi-market-report-server/db/series_leading.json")) +
                 sorted(glob.glob("/sessions/*/mnt/claudeCowork/namoobi-market-report-server/db/series_leading.json"))):
        try:
            _d=(json.load(open(_dbp,encoding="utf-8")) or {}).get("data") or []
            pp=[(parsem(d),float(v)) for d,v in _d if v is not None and parsem(d)]
            if len(pp)>=2:
                pts=sorted(pp,key=lambda z:z[0])
                print("leading: DB 폴백 사용 (%d pts)" % len(pts))
                break
        except Exception: pass
if not pts or len(pts)<2:
    rp=_report_path()
    if rp:
        try:
            kl=((json.load(open(rp)).get("markets") or {}).get("korea_leading")) or []
            pp=[(parsem(x.get("period")), x.get("value")) for x in kl if x.get("value") is not None and parsem(x.get("period"))]
            pp=[(d,float(v)) for d,v in pp if d]
            if len(pp)>=2: pts=sorted(pp,key=lambda z:z[0])
        except Exception: pass
if not pts or len(pts)<2:
    print("leading: 데이터 부족 — 차트 생략(표는 korea_leading 으로 렌더됨)"); sys.exit(0)
xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
fig,ax=plt.subplots(figsize=(7.2,2.7),dpi=150)
mk="o" if len(xs)<=14 else None
ax.plot(xs,ys,color="#e11d48",lw=1.6,marker=mk,ms=4)
ax.fill_between(xs,ys,min(ys)-0.3,color="#e11d48",alpha=0.07)
ax.axhline(100,color="#94a3b8",lw=0.9,ls="--"); ax.text(xs[0],100.05,"기준선 100",fontsize=7,color="#64748b",va="bottom")
ax.scatter([xs[-1]],[ys[-1]],color="#e11d48",s=26,zorder=5)
ax.annotate(f"{ys[-1]:.1f}",(xs[-1],ys[-1]),fontsize=9,fontweight="bold",color="#e11d48",textcoords="offset points",xytext=(-4,8),ha="right")
span=f"{xs[0].strftime('%Y.%m')}~{xs[-1].strftime('%Y.%m')}"
ax.set_title(f"선행종합지수 순환변동치 (월별, {span})",fontsize=10,color="#334155")
if (xs[-1]-xs[0]).days>500:
    ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
else:
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%y.%m"))
ax.tick_params(labelsize=7); ax.grid(alpha=0.18)
for sp in ["top","right"]: ax.spines[sp].set_visible(False)
ax.text(0.012,0.06,"출처: 국가데이터처 「산업활동동향」 (e-나라지표, 2020=100)",transform=ax.transAxes,fontsize=7,color="#94a3b8")
plt.tight_layout(pad=0.4); fig.savefig("charts/leading_cycle.png",dpi=150,bbox_inches="tight"); print("leading chart done (pts",len(pts),")")
