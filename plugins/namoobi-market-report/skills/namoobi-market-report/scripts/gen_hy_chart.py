# 3.2.3 하이일드(HY) OAS 차트 — robust (v3.6.31)
# 출력: charts/hy_oas.png  (빌더 data.markets.hy_spread.chart 기본값과 일치)
# 입력 우선순위:
#   1) 1년 일별 series: <O>/nmr_hy_series.json 또는 ./hy_oas.json  ({"series":[["YYYY-MM-DD",oas],...],"points":{"current":[d,v]}})
#   2) 폴백: report_data 의 markets.hy_spread 레벨 6점(current/w1/m1/m3/m6/y1)으로 추이선 — FRED 실패해도 표 값으로 항상 그래프
# (구버전 버그: hy_oas_chart.png 로 저장→빌더(charts/hy_oas.png)와 불일치, series 필수라 FRED 실패 시 크래시.)
import json, sys, os, glob, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as mdates, matplotlib.font_manager as fm
from datetime import datetime, timedelta
_f=[p for p in [os.path.join(os.path.dirname(__file__),"fonts","nmr_kr.ttf"),"fonts/nmr_kr.ttf"] if os.path.exists(p)]
if _f: fm.fontManager.addfont(_f[0]); matplotlib.rcParams["font.family"]="NanumBarunGothic"
matplotlib.rcParams["axes.unicode_minus"]=False
O=os.environ.get("NMR_OUT") or (sorted(glob.glob("/sessions/*/mnt/outputs"))[-1] if glob.glob("/sessions/*/mnt/outputs") else ".")
os.makedirs("charts", exist_ok=True)
OUT="charts/hy_oas.png"
def _report_path():
    for a in sys.argv[1:]:
        if a.endswith(".json") and os.path.exists(a) and "report_data" in a: return a
    c=(sorted(glob.glob(O+"/_market_report_data/report_data_*.json")) or sorted(glob.glob(O+"/report_data_*.json"))
       or sorted(glob.glob("/sessions/*/mnt/claudeCowork/_market_report_data/report_data_*.json")))  # v3.13.1: 연결폴더 직전 report_data 폴백 → FRED 실패해도 HY 차트 항상 렌더
    return c[-1] if c else None
series=None; cur=None
for cand in ["hy_oas.json", O+"/hy_oas.json", O+"/nmr_hy_series.json"]:
    if os.path.exists(cand):
        try:
            d=json.load(open(cand)); s=d.get("series") or []
            sv=[(datetime.fromisoformat(p[0]), float(p[1])) for p in s if p and p[1] is not None]
            if len(sv)>=5:
                series=sv
                pc=(d.get("points") or {}).get("current")
                if pc: cur=(datetime.fromisoformat(pc[0]), float(pc[1]))
                break
        except Exception: pass
if not series:
    rp=_report_path()
    if rp:
        try:
            hs=((json.load(open(rp)).get("markets") or {}).get("hy_spread")) or {}
            today=datetime.today(); pts=[]
            for k,days in [("y1",365),("m6",182),("m3",91),("m1",30),("w1",7),("current",0)]:
                v=hs.get(k)
                if v is not None:
                    try: pts.append((today-timedelta(days=days), float(v)))
                    except Exception: pass
            if len(pts)>=2: series=pts; cur=pts[-1]
        except Exception: pass
if not series:
    print("hy: 데이터 없음 — 차트 생략(표는 hy_spread 값으로 렌더됨)"); sys.exit(0)
xs=[p[0] for p in series]; ys=[p[1] for p in series]
if cur is None: cur=series[-1]
fig,ax=plt.subplots(figsize=(7.2,2.6),dpi=150)
mk="o" if len(xs)<=8 else None
ax.plot(xs,ys,color="#1E40AF",linewidth=1.8,marker=mk,ms=4)
ax.fill_between(xs,ys,min(ys)-0.1,color="#1E40AF",alpha=0.07)
ax.scatter([cur[0]],[cur[1]],color="#DC2626",zorder=5,s=28)
ax.annotate(f"{cur[1]:.2f}%",(cur[0],cur[1]),textcoords="offset points",xytext=(-30,7),color="#DC2626",fontsize=9,fontweight="bold")
# (v3.6.33 req7) 월별 장기 추이 — nmr_hy_series.json 에 FRED BAMLH0A0HYM2 월별 시계열(가능한 최장; 무료 CSV 는 약 3년 상한)을 넣는다.
span=f"{xs[0].strftime('%Y.%m')}~{xs[-1].strftime('%Y.%m')}"
ax.set_title(f"美 하이일드 OAS — ICE BofA US HY (FRED BAMLH0A0HYM2, 월별 {span})",fontsize=9.5,color="#334155")
if (xs[-1]-xs[0]).days>900:
    ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
else:
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1,7])); ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m"))
ax.grid(True,alpha=0.25); ax.set_ylabel("OAS (%)",fontsize=8,color="#64748B")
for s in ["top","right"]: ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig(OUT,bbox_inches="tight"); print("hy chart ->",OUT,"(pts",len(series),")")
