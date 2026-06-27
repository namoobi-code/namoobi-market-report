# -*- coding: utf-8 -*-
# 3.2.1 AI 빅테크 자본지출(CAPEX) 차트 생성기 (v3.9.0 신규)
# 출력(cwd 상대): charts/capex_stack_ratio.png · charts/capex_fcf.png
#   - 빌더(build_report.js renderUSExtras)가 3.2.1 표·코멘트 다음(맨 아래)에 imagePara 로 임베드.
#   - 파일이 없으면 빌더가 조용히 생략(imagePara→null) → 본 스크립트 실패해도 보고서는 깨지지 않음.
# 스타일: gen_hy_chart.py / gen_rest_charts.py 와 동일(NanumBarunGothic·슬레이트 팔레트·spines off, dpi150).
#
# 데이터(기본 내장 = 확인된 실적 + 가이던스, 단위 십억 달러):
#   - 2023~2025 실적: 각사 10-K cashflow/income (FMP statements: capitalExpenditure 절대값·revenue·freeCashFlow)
#   - 2026(E): 각사 공식 가이던스(2026.6 기준) — GOOGL $175~185B·AMZN ~$200B·META $125~145B·MSFT ~$120B·ORCL FY26 ~$50B(FCF ~ -$23.7B)
#   - 2027~2029(E): 컨센서스 추세 기반 전망(일러스트레이션). IB 컨센서스 확보 시 교체.
# 라이브 오버라이드(선택): report_data.markets.bigtech_capex 에 아래 키가 있으면 우선 사용(없으면 내장값).
#   capex_series={"years":[...], "<Company>":[...]} · rev_series={"years":[...], "<Company>":[...]}
#   fcf_series={"years":[...], "<Company>":[...]}
import os, sys, glob, json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.font_manager as fm
from matplotlib.ticker import MultipleLocator

# ---- 폰트(한글) ----
_cands=[os.path.join(os.path.dirname(__file__), "fonts", "nmr_kr.ttf"),
        os.path.join(os.getcwd(), "fonts", "nmr_kr.ttf"), os.environ.get("NMR_FONT", "")]
_f=[p for p in _cands if p and os.path.exists(p)]
if _f:
    fm.fontManager.addfont(_f[0]); matplotlib.rcParams["font.family"]="NanumBarunGothic"
matplotlib.rcParams["axes.unicode_minus"]=False

os.makedirs("charts", exist_ok=True)
OUT_STACK="charts/capex_stack_ratio.png"; OUT_FCF="charts/capex_fcf.png"

EST_FROM=2026
COMPANIES=["Amazon","Microsoft","Alphabet","Meta","Oracle"]
COLORS={"Amazon":"#1F3A5F","Microsoft":"#E8833A","Alphabet":"#2BA98E","Meta":"#5B6CE0","Oracle":"#9B4DCA"}
KLABEL={"Amazon":"아마존","Microsoft":"마이크로소프트","Alphabet":"알파벳","Meta":"메타","Oracle":"오라클"}

# ---- 내장 기본 데이터(십억 달러) ----
YEARS=[2023,2024,2025,2026,2027,2028,2029]
CAPEX={"Microsoft":[28,44,65,120,150,175,195],"Amazon":[53,83,132,200,245,280,305],
       "Alphabet":[32,53,91,180,220,250,270],"Meta":[27,37,70,135,165,185,200],"Oracle":[9,7,21,50,70,80,88]}
REV={"Microsoft":[212,245,282,320,365,415,470],"Amazon":[575,638,717,795,880,970,1065],
     "Alphabet":[307,350,403,458,520,590,665],"Meta":[135,165,201,238,278,320,365],"Oracle":[50,53,57,67,90,108,125]}
FCF_YEARS=[2024,2025,2026,2027,2028,2029]
FCF={"Microsoft":[74,72,55,60,85,115],"Alphabet":[73,73,58,65,90,115],"Meta":[54,46,40,48,70,95],
     "Amazon":[33,8,-35,-30,5,45],"Oracle":[12,0,-24,-20,-5,10]}

# ---- 선택: report_data 라이브 오버라이드 ----
def _report():
    for a in sys.argv[1:]:
        if a.endswith(".json") and os.path.exists(a) and "report_data" in a: return a
    O=os.environ.get("NMR_OUT") or (sorted(glob.glob("/sessions/*/mnt/outputs"))[-1] if glob.glob("/sessions/*/mnt/outputs") else ".")
    c=sorted(glob.glob(O+"/_market_report_data/report_data_*.json")) or sorted(glob.glob(O+"/report_data_*.json"))
    return c[-1] if c else None
def _apply(series, years_key, store_years, store):
    """series={'years':[...], '<Co>':[...]} 형태가 온전하면 내장값 덮어쓰기."""
    try:
        if not isinstance(series, dict): return store_years, store
        ys=series.get("years")
        if not (isinstance(ys, list) and len(ys)>=2): return store_years, store
        ok={}
        for c in COMPANIES:
            v=series.get(c) or series.get(KLABEL[c])
            if isinstance(v, list) and len(v)==len(ys) and all(isinstance(x,(int,float)) for x in v): ok[c]=list(v)
        if len(ok)==len(COMPANIES): return [int(y) for y in ys], ok
    except Exception: pass
    return store_years, store
try:
    rp=_report()
    if rp:
        bc=((json.load(open(rp)).get("markets") or {}).get("bigtech_capex")) or {}
        YEARS,CAPEX=_apply(bc.get("capex_series"),"years",YEARS,CAPEX)
        _,REV       =_apply(bc.get("rev_series"),"years",YEARS,REV)
        FCF_YEARS,FCF=_apply(bc.get("fcf_series"),"years",FCF_YEARS,FCF)
except Exception: pass
# ---- (v3.35) 표(rows)로 CAPEX·매출·FCF 모두 구동 → 두 차트 완전 일치 (2024~2029) ----
try:
    if rp:
        _bc=((json.load(open(rp)).get("markets") or {}).get("bigtech_capex")) or {}
        _rows=_bc.get("rows")
        if isinstance(_rows,list) and _rows:
            _Y=[2024,2025,2026,2027,2028,2029]; _cap={}; _rev={}; _fcf={}; _ok=True
            for c in COMPANIES:
                _row=next((r for r in _rows if str(r.get("company","")).split(" (")[0].strip()==c), None)
                if not _row: _ok=False; break
                try:
                    _cap[c]=[float(_row["y%d"%y]) for y in _Y]
                    _rev[c]=[float(_row["rev%d"%y]) for y in _Y]
                    _fcf[c]=[float(_row["fcf%d"%y]) for y in _Y]
                except Exception: _ok=False; break
            if _ok:
                YEARS=_Y; CAPEX=_cap; REV=_rev; FCF_YEARS=_Y; FCF=_fcf
except Exception: pass

tot_capex=[sum(CAPEX[c][i] for c in COMPANIES) for i in range(len(YEARS))]
tot_rev=[sum(REV[c][i] for c in COMPANIES) for i in range(len(YEARS))]
ratio=[round(100*tot_capex[i]/tot_rev[i]) for i in range(len(YEARS))]
GRID="#CBD5E1"; INK="#334155"; SUB="#64748B"; FAINT="#94A3B8"

def style_ax(ax):
    for s in ["top","right"]: ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(GRID); ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=SUB, labelsize=8)
def xl(yrs): return [f"{y}\n(E)" if y>=EST_FROM else str(y) for y in yrs]

def chart_stack(ax):
    x=list(range(len(YEARS))); bottom=[0]*len(YEARS)
    est_x=next((i for i,y in enumerate(YEARS) if y>=EST_FROM), len(YEARS))
    ax.axvspan(est_x-0.5, len(YEARS)-0.5, color="#F1F5F9", zorder=0)
    for c in COMPANIES:
        ax.bar(x, CAPEX[c], 0.62, bottom=bottom, color=COLORS[c], label=KLABEL[c], edgecolor="white", linewidth=0.6, zorder=3)
        bottom=[bottom[i]+CAPEX[c][i] for i in range(len(YEARS))]
    ax.text((est_x-0.5+len(YEARS)-0.5)/2, max(tot_capex)*1.12, "전망(E)", ha="center", fontsize=7.5, color=FAINT)
    for i,t in enumerate(tot_capex):
        ax.text(i, t+max(tot_capex)*0.012, f"{t:,}", ha="center", va="bottom", fontsize=7.2, color=SUB)
    style_ax(ax); ax.set_ylim(0, max(tot_capex)*1.2)
    ax.set_xticks(x); ax.set_xticklabels(xl(YEARS))
    ax.set_ylabel("자본지출 합계 (십억 달러)", fontsize=8.5, color=SUB)
    ax.yaxis.set_major_locator(MultipleLocator(200)); ax.grid(axis="y", alpha=0.25, color=GRID); ax.set_axisbelow(True)
    ax2=ax.twinx()
    ax2.plot(x, ratio, color="#DC2626", linewidth=2.2, marker="o", ms=6, markeredgecolor="white", markeredgewidth=1.2, zorder=7, label="Capex/매출 비율(우)")
    for i,r in enumerate(ratio):
        ax2.annotate(f"{r}%", (i, ratio[i]), textcoords="offset points", xytext=(0,10), ha="center", fontsize=8.2,
                     color="#DC2626", fontweight="bold", zorder=8, bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85))
    ax2.set_ylim(0, max(ratio)*1.6); ax2.set_ylabel("Capex / 매출 (%)", fontsize=8.5, color="#DC2626")
    ax2.tick_params(colors="#DC2626", labelsize=8)
    for s in ["top","left"]: ax2.spines[s].set_visible(False)
    ax2.spines["right"].set_color("#FCA5A5")
    h1,l1=ax.get_legend_handles_labels(); h2,l2=ax2.get_legend_handles_labels()
    ax.legend(h1+h2, l1+l2, loc="upper left", fontsize=7.6, ncol=3, frameon=False, handlelength=1.2, columnspacing=1.0, borderaxespad=0.2)
    ax.set_title(f"치솟는 빅테크 CAPEX — 매출 대비 비중 최대 {max(ratio)}%까지 상승", fontsize=11, color=INK, fontweight="bold", pad=10, loc="left")

def chart_fcf(ax):
    x=list(range(len(FCF_YEARS))); order=[c for c in ["Microsoft","Alphabet","Meta","Amazon","Oracle"] if c in FCF]
    est_x=next((i for i,y in enumerate(FCF_YEARS) if y>=EST_FROM), len(FCF_YEARS))
    ax.axvspan(est_x-0.5, len(FCF_YEARS)-0.5, color="#F1F5F9", zorder=0)
    ymax=max(max(FCF[c]) for c in order); ymin=min(min(FCF[c]) for c in order)
    ax.text((est_x-0.5+len(FCF_YEARS)-0.5)/2, ymax*0.92, "전망(E)", ha="center", fontsize=7.5, color=FAINT)
    ax.axhline(0, color="#475569", linewidth=1.0, linestyle=(0,(4,3)), zorder=2)
    for c in order:
        ax.plot(x, FCF[c], color=COLORS[c], linewidth=2.0, marker="o", ms=4.5, markeredgecolor="white", markeredgewidth=0.8, label=KLABEL[c], zorder=4)
    style_ax(ax); ax.set_xlim(-0.3, len(FCF_YEARS)-0.55); ax.set_ylim(ymin-12, ymax+8)
    ax.set_xticks(x); ax.set_xticklabels(xl(FCF_YEARS))
    ax.set_ylabel("잉여현금흐름 FCF (십억 달러)", fontsize=8.5, color=SUB)
    ax.yaxis.set_major_locator(MultipleLocator(40)); ax.grid(axis="y", alpha=0.25, color=GRID); ax.set_axisbelow(True)
    ax.legend(loc="upper left", fontsize=7.6, ncol=5, frameon=False, handlelength=1.2, columnspacing=1.0, borderaxespad=0.2)
    neg=[KLABEL[c] for c in order if min(FCF[c])<0]
    if neg: ax.annotate("·".join(neg)+" 마이너스 전환", (max(0,est_x), ymin*0.8 if ymin<0 else ymin), fontsize=7.6, color="#B91C1C", fontweight="bold", ha="center")
    ax.set_title("일부 빅테크는 FCF(잉여현금흐름) 마이너스 구간 진입", fontsize=11, color=INK, fontweight="bold", pad=10, loc="left")

NOTE=("2023~2025 실적(각사 10-K, 단위 십억 달러) · 2026 회사 가이던스 · 2027~2029 전망(E) · 회색=전망구간 · 자료: 각사 SEC 보고서/FMP, AI Research")

fig,ax=plt.subplots(figsize=(8.2,3.6),dpi=150); chart_stack(ax)
fig.text(0.01,0.005,NOTE,fontsize=6.6,color=FAINT,ha="left")
plt.tight_layout(rect=[0,0.04,1,1]); plt.savefig(OUT_STACK,bbox_inches="tight"); plt.close(); print("capex stack ->",OUT_STACK)

fig,ax=plt.subplots(figsize=(8.2,3.3),dpi=150); chart_fcf(ax)
fig.text(0.01,0.005,NOTE,fontsize=6.6,color=FAINT,ha="left")
plt.tight_layout(rect=[0,0.04,1,1]); plt.savefig(OUT_FCF,bbox_inches="tight"); plt.close(); print("capex fcf ->",OUT_FCF)
print("ratio:",ratio,"| capex tot:",tot_capex)
