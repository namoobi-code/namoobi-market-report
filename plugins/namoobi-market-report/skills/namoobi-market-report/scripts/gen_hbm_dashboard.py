# -*- coding: utf-8 -*-
# 3.1.5 반도체 주가 체크용 메모리+HBM 지표 대시보드 생성기 (v3.10.0 신규)
# 출력(cwd 상대): charts/hbm_dashboard.png
#   - 빌더(build_report.js renderKoreaExtras)가 3.1.4 다음(3.1.5)에 imagePara 로 임베드.
#   - 파일이 없으면 빌더가 조용히 생략(imagePara→null) → 본 스크립트 실패해도 보고서는 깨지지 않음(비차단).
# 스타일: gen_capex_chart.py / gen_rest_charts.py 와 동일(NanumBarunGothic·슬레이트 팔레트, dpi150).
#
# ⚠️ 모든 수치는 '추정치'다. HBM 스팟가격·ASP·점유율은 무료 실시간 API 가 없어
#    HBMAgent 가 WebSearch+뉴스(TrendForce·각사 실적 컨센서스·언론)로 분기 추정치를 수집한다.
#    확인 불가 항목은 미표기(빈값)로 두며, 차트 상단·표 제목에 '추정' 을 명시한다.
# 데이터 우선순위: (1) nmr_hbm.json (HBMAgent 가 Phase 1 에 저장) → (2) report_data.markets.hbm
#    → (3) 내장 기본(예시) 값. 라이브 데이터가 있으면 해당 키만 오버라이드, 없으면 내장값.
import os, sys, glob, json, textwrap
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.dates as mdates

# ---- 폰트(한글) ----
_cands=[os.path.join(os.path.dirname(__file__),"fonts","nmr_kr.ttf"),
        os.path.join(os.getcwd(),"fonts","nmr_kr.ttf"), os.environ.get("NMR_FONT","")]
_f=[p for p in _cands if p and os.path.exists(p)]
if not _f:
    _g=glob.glob("/sessions/*/mnt/**/namoobi-market-report/scripts/fonts/nmr_kr.ttf", recursive=True)
    _f=_g[:1]
if _f:
    fm.fontManager.addfont(_f[0]); matplotlib.rcParams["font.family"]="NanumBarunGothic"
matplotlib.rcParams["axes.unicode_minus"]=False

C_SPOT="#7C4DFF"; C_DDR5="#F5A623"; C_DDR4="#4A90E2"; C_NAND="#2E9E5B"
C_SHIP="#4A90E2"; C_MKT="#2E9E5B"; C_HBM3E="#F5A623"; C_HBM4="#7C4DFF"
C_SAMS="#4A90E2"; C_SK="#F5A623"; C_MICRON="#2E9E5B"; C_ETC="#9CA3AF"; C_GAP="#E2342E"
GRID=dict(alpha=0.18, linewidth=0.8)
LEG=dict(fontsize=8.5, frameon=True, framealpha=0.85, edgecolor="#E5E7EB", handletextpad=0.5, borderpad=0.4)

# ================= 내장 기본(예시·추정) =================
def _mser(start_ym, vals):
    y,m=[int(z) for z in start_ym.split("-")]; out=[]
    for v in vals:
        out.append([f"{y:04d}-{m:02d}", v]); m+=1
        if m>12: m=1; y+=1
    return out
DEF={
 "asof":"예시·추정","source":"TrendForce·실적 컨센서스·언론 종합(추정)",
 "spot_index": _mser("2025-01",[100,101,103,106,110,115,124,136,142,150,164,179,194,205,214,224,238,245]),
 "ddr5_16gb":  _mser("2025-01",[3.6,4.0,4.3,4.6,5.0,5.5,6.0,8.5,19.5,25.0,30.0,32.0,34.0,36.0,36.5,37.0,37.4,37.6]),
 "ddr4_8gb":   _mser("2025-01",[1.2,1.1,1.3,1.6,2.0,2.5,3.0,5.5,7.0,8.0,9.0,11.5,13.0,14.5,16.0,16.0,19.0,20.0]),
 "nand_mlc_64gb": _mser("2025-01",[1.9,1.8,2.1,2.4,2.6,2.9,3.2,3.5,4.0,4.5,5.5,6.2,6.8,7.2,7.7,8.0,8.3,8.5]),
 "hbm_shipment": [[2024,8.5],[2025,12.0],[2026,19.0],[2027,27.5]],
 "hbm_market":   [[2024,18.2],[2025,46.7],[2026,72.0],[2027,108.0]],
 "hbm3e_price":  [[2024,320],[2025,520],[2026,560],[2027,620]],
 "hbm4_price":   [[2026,720],[2027,1080]],
 "share":[{"year":"2024","samsung":42,"sk_hynix":52,"micron":5,"others":1},
          {"year":"2025","samsung":37,"sk_hynix":52,"micron":10,"others":1},
          {"year":"2026E","samsung":30,"sk_hynix":49,"micron":19,"others":2},
          {"year":"2027E","samsung":31,"sk_hynix":47,"micron":20,"others":2}],
 "gap_ratio":[[2024,1.6],[2025,1.3],[2026,1.1],[2027,1.6]],
 "eps_per":[{"name":"SK하이닉스","eps_cur":"52,000원","eps_next":"60,000원","per_cur":"7.0x","per_next":"6.1x"},
            {"name":"삼성전자","eps_cur":"7,500원","eps_next":"9,000원","per_cur":"12.8x","per_next":"10.7x"},
            {"name":"Micron (MU)","eps_cur":"$12.00","eps_next":"$14.50","per_cur":"10.5x","per_next":"8.7x"}],
 "year_cur":"2026E","year_next":"2027E",
}

# ---- 라이브 오버라이드 로드 ----
def _outdir():
    O=os.environ.get("NMR_OUT")
    if O and os.path.isdir(O): return O
    g=sorted(glob.glob("/sessions/*/mnt/outputs"))
    return g[-1] if g else "."
def _report():
    for a in sys.argv[1:]:
        if a.endswith(".json") and os.path.exists(a) and "report_data" in a: return a
    O=_outdir(); c=sorted(glob.glob(O+"/_market_report_data/report_data_*.json")) or sorted(glob.glob(O+"/report_data_*.json"))
    return c[-1] if c else None
def _live():
    # 1) nmr_hbm.json (Phase 1.5 에 존재). argv 의 디렉터리/파일 경로도 탐색.
    cands=[]
    for a in sys.argv[1:]:
        if a.endswith("nmr_hbm.json"): cands.append(a)
        elif os.path.isdir(a): cands.append(os.path.join(a,"nmr_hbm.json"))
    O=_outdir(); cands += [os.path.join(O,"nmr_hbm.json"), "nmr_hbm.json"]
    cands += glob.glob("/sessions/*/mnt/claudeCowork/_market_report_data/nmr_hbm.json")  # (v3.39) 연결폴더 영구본 폴백
    for c in cands:
        if c and os.path.exists(c):
            try: return json.load(open(c, encoding="utf-8")) or {}
            except Exception: pass
    # 2) report_data.markets.hbm
    rp=_report()
    if rp:
        try: return ((json.load(open(rp)).get("markets") or {}).get("hbm")) or {}
        except Exception: pass
    return {}

def _compat(new, old):  # [견고화] LIVE 스키마가 내장(DEF)과 호환될 때만 적용 — 불일치는 내장값 유지(크래시 방지)
    if type(new)!=type(old): return False
    if isinstance(old,list):
        if old and isinstance(old[0],dict):
            return bool(new) and isinstance(new[0],dict) and bool(set(new[0]) & set(old[0]))
        return True
    if isinstance(old,dict): return bool(set(new) & set(old))
    return True
D=dict(DEF); LIVE=_live(); USED_LIVE=False
if isinstance(LIVE, dict):
    for k,v in LIVE.items():
        if v in (None,"",[],{}): continue
        if (k in DEF) and not _compat(v, DEF[k]): continue
        D[k]=v
        if k not in ("asof","source"): USED_LIVE=True

def _pairs_dt(series):
    out=[]
    for d,v in series:
        try:
            ds=str(d); dt=datetime.fromisoformat(ds if len(ds)>7 else ds+"-01"); out.append((dt,float(v)))
        except Exception: pass
    return out

# ================= 렌더 =================
fig=plt.figure(figsize=(15.2,8.8), dpi=150)
fig.suptitle("반도체 주가 체크용 HBM 지표 대시보드 (출하·시장규모 / ASP / 점유율)", fontsize=21, fontweight="bold", y=0.987)
_src=D.get("source") or "TrendForce·실적 컨센서스·언론 종합"
_tag="추정치" if USED_LIVE else "예시·추정 데이터"
# 차트별 갱신 주기·최종 갱신일 라벨
_CAD={"spot":"월별 추정","dram":"월별 추정","ship":"분기·연간 추정","hbmprice":"분기 추정","share":"분기 추정","gap":"분기 추정(계산값)"}
_CAD.update(D.get("cadence") or {})
_AM=D.get("asof_map") or {}; _ASOF=D.get("asof","")
def cad(k):
    a=_AM.get(k) or ((_ASOF) if _ASOF and _ASOF!="예시·추정" else None)
    return "  ▪ "+_CAD.get(k,"추정")+(" · 최종 갱신 "+a if a else " (예시값)")
fig.text(0.5,0.962, f"※ 아래 모든 수치는 {_tag}입니다 — 에이전트 웹리서치({_src}) 기준, 확인 불가 항목은 미표기('추정' 표기)",
         ha="center", fontsize=10.5, color="#B45309")
gs=fig.add_gridspec(2,2, top=0.90, bottom=0.07, left=0.06, right=0.97, hspace=0.95, wspace=0.20, height_ratios=[1,1])
def style(ax):
    for s in ["top","right"]: ax.spines[s].set_visible(False)
    ax.grid(**GRID)
def caption(ax, text, y=-0.40):
    ax.text(0.0,y, textwrap.fill("[해석] "+text, width=46), transform=ax.transAxes,
            ha="left", va="top", fontsize=9.5, color="#475569", linespacing=1.4)

# 패널3 — 출하량 + 시장규모
ax3=fig.add_subplot(gs[0,0]); shp=D["hbm_shipment"]; mkt=D["hbm_market"]
sx=[r[0] for r in shp]; sy=[r[1] for r in shp]
ax3.bar(sx,sy,width=0.55,color=C_SHIP,alpha=0.85,zorder=2,label="HBM 출하량(십억Gb)")
ax3.set_title("HBM 출하량 / 시장규모", fontsize=13, fontweight="bold"); ax3.set_ylabel("출하량 (십억Gb)")
ax3.set_ylim(top=max(sy)*1.25); ax3.set_xticks(sx)
ax3b=ax3.twinx(); mx=[r[0] for r in mkt]; my=[r[1] for r in mkt]
ax3b.plot(mx,my,color=C_MKT,marker="o",ms=6,lw=2.2,zorder=3,label="HBM 시장규모($B)"); ax3b.set_ylabel("시장규모($B)"); ax3b.set_ylim(top=max(my)*1.18)
for x,v in zip(mx,my): ax3b.annotate(f"${v:.1f}B",(x,v),textcoords="offset points",xytext=(0,8),ha="center",fontsize=9,color=C_MKT,fontweight="bold")
ax3.spines["top"].set_visible(False); ax3b.spines["top"].set_visible(False); ax3.grid(**GRID)
ax3.legend(ax3.get_legend_handles_labels()[0]+ax3b.get_legend_handles_labels()[0],
           ax3.get_legend_handles_labels()[1]+ax3b.get_legend_handles_labels()[1], loc="upper left", **LEG)
caption(ax3, "출하량과 시장규모가 함께 늘면 수요가 실적으로 연결될 가능성이 큽니다."+cad("ship"))

# 패널4 — HBM 가격
ax4=fig.add_subplot(gs[0,1]); h3=D["hbm3e_price"]; h4=D["hbm4_price"]
ax4.plot([r[0] for r in h3],[r[1] for r in h3],color=C_HBM3E,marker="o",ms=6,lw=2.2,label="HBM3E")
ax4.plot([r[0] for r in h4],[r[1] for r in h4],color=C_HBM4,marker="o",ms=6,lw=2.2,ls="--",label="HBM4")
ax4.set_title("HBM 가격: HBM3E / HBM4", fontsize=13, fontweight="bold")
_ally=[r[1] for r in h3]+[r[1] for r in h4]; ax4.set_ylim(top=max(_ally)*1.16)
ax4.set_xticks(sorted(set([r[0] for r in h3]+[r[0] for r in h4])))
for x,v in zip([r[0] for r in h3],[r[1] for r in h3]): ax4.annotate(f"${v}",(x,v),textcoords="offset points",xytext=(0,-16),ha="center",fontsize=9,color=C_HBM3E,fontweight="bold")
for x,v in zip([r[0] for r in h4],[r[1] for r in h4]): ax4.annotate(f"${v}",(x,v),textcoords="offset points",xytext=(0,9),ha="center",fontsize=9,color=C_HBM4,fontweight="bold")
style(ax4); ax4.legend(loc="upper left", **LEG)
caption(ax4, "HBM 가격 상승은 AI 메모리 ASP와 실적 상향 가능성을 높입니다."+cad("hbmprice"))

# 패널5 — 점유율(기타 포함, 합계 100%)
ax5=fig.add_subplot(gs[1,:]); shr=D["share"]; lbl=[s.get("year") for s in shr]; xpos=list(range(len(shr)))
sams=[s.get("samsung",0) for s in shr]; sk=[s.get("sk_hynix",0) for s in shr]; mic=[s.get("micron",0) for s in shr]; etc=[s.get("others",0) for s in shr]
ax5.bar(xpos,sams,width=0.55,color=C_SAMS,label="Samsung")
ax5.bar(xpos,sk,width=0.55,bottom=sams,color=C_SK,label="SK hynix")
b2=[a+b for a,b in zip(sams,sk)]; ax5.bar(xpos,mic,width=0.55,bottom=b2,color=C_MICRON,label="Micron")
b3=[a+b for a,b in zip(b2,mic)]; ax5.bar(xpos,etc,width=0.55,bottom=b3,color=C_ETC,label="기타(중국 CXMT 등)")
for i in xpos:
    if etc[i]: ax5.annotate(f"{etc[i]}%",(i,b3[i]+etc[i]/2),ha="center",va="center",fontsize=7.5,color="white",fontweight="bold")
ax5.set_title("HBM 점유율 (합계 100%)", fontsize=13, fontweight="bold"); ax5.set_ylabel("점유율 (%)")
ax5.set_xticks(xpos); ax5.set_xticklabels(lbl); ax5.set_ylim(0,128)
style(ax5); ax5.legend(loc="upper center", ncol=4, fontsize=7.6, frameon=True, framealpha=0.85, edgecolor="#E5E7EB", handletextpad=0.4, columnspacing=0.8, borderpad=0.4)
caption(ax5, "점유율↑ 기업이 호황 이익을 더 가져갈 가능성. 나머지는 기타(중국 CXMT 등 신규)."+cad("share"))

os.makedirs("charts", exist_ok=True)
OUT="charts/hbm_dashboard.png"
plt.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white"); plt.close()
print("hbm dashboard ->", os.path.abspath(OUT), os.path.getsize(OUT), "bytes | live_override:", USED_LIVE)
