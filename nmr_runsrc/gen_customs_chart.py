#!/usr/bin/env python3
# 3.1.10 관세청 수출 주요품목별 10일 단위 잠정치 — 그룹막대 차트 2종
# 출력: charts/수출_전체_24개월.png, charts/수출_반도체_24개월.png
# 입력 우선순위: 1) <WORK>/nmr_customs.json(변경 시 신규분)  2) 폴백 db/customs.json 의 data
# 변경없음(fresh 없음) + 두 차트 모두 존재 → 스킵(기존 그래프 유지).
import json, sys, os, glob, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.font_manager as fm
from matplotlib.ticker import FuncFormatter

_f=[p for p in [os.path.join(os.path.dirname(__file__),"fonts","nmr_kr.ttf"),"fonts/nmr_kr.ttf"] if os.path.exists(p)]
if _f: fm.fontManager.addfont(_f[0]); matplotlib.rcParams["font.family"]="NanumBarunGothic"
matplotlib.rcParams["axes.unicode_minus"]=False

MONTHS=24
SERIES=[("p10","1~10일","#5AC8B6"),("p20","1~20일","#5B9BD5"),("pm","1~말일","#3A53C4")]
TITLES={"total":"전체","semiconductor":"반도체"}
OUT={"total":"charts/수출_전체_24개월.png","semiconductor":"charts/수출_반도체_24개월.png"}

def _load(p):
    try: return json.load(open(p,encoding="utf-8"))
    except Exception: return None

def resolve_data(WORK):
    d=_load(os.path.join(WORK,"nmr_customs.json"))
    if isinstance(d,dict) and d.get("series"): return d, True
    for dbp in (glob.glob("/sessions/*/mnt/claudeCowork/namoobi-market-report-server/db/customs.json")+
                glob.glob("/sessions/*/mnt/outputs/namoobi-market-report-server/db/customs.json")):
        e=_load(dbp)
        if isinstance(e,dict):
            data=e.get("data") if "data" in e else e
            if isinstance(data,dict) and data.get("series"): return data, False
    return None, False

def plot(months, ser, col, outpath):
    n=len(months); xs=range(n); width=0.27
    fig,ax=plt.subplots(figsize=(max(16,n*0.86),8.4),dpi=150); fig.patch.set_facecolor("white")
    vals_all=[v for k,_,_ in SERIES for v in ser[k] if v is not None]
    maxv=max(vals_all) if vals_all else 1
    for i,(k,name,color) in enumerate(SERIES):
        vals=ser[k]; offs=(i-1)*width
        ax.bar([x+offs for x in xs],[ (v if v is not None else 0) for v in vals],width=width,
               label=name,color=color,edgecolor="none",zorder=3)
        for x,v in zip(xs,vals):
            if v is not None:
                ax.text(x+offs, v+maxv*0.012, f"{int(v):,}", ha="center", va="bottom",
                        fontsize=6.4, rotation=90, color="#333333", zorder=4)
    # (v3.75) 진행 중인 달(말일 미집계)을 완결월과 나란히 두면 "수출 급감"으로 오독된다(2026-07-21 실측 문의).
    #   → ① X축 라벨에 집계 구간 명시 ② 배경 음영 ③ 캡션 경고. 데이터·색 매핑은 종전과 동일(정상).
    _inprog = [i for i,_m in enumerate(months) if ser.get("pm") and ser["pm"][i] is None]
    _lab=[]
    for i,m in enumerate(months):
        if i in _inprog:
            _upto = "1~20일" if (ser.get("p20") and ser["p20"][i] is not None) else "1~10일"
            _lab.append(f"{m[:4]}년 {m[5:7]}월\n(진행중·{_upto})")
        else:
            _lab.append(f"{m[:4]}년 {m[5:7]}월")
    for i in _inprog:
        ax.axvspan(i-0.5, i+0.5, color="#FEF3C7", alpha=0.75, zorder=0)
    ax.set_xticks(list(xs)); ax.set_xticklabels(_lab,fontsize=9)
    for i in _inprog:
        ax.get_xticklabels()[i].set_color("#B45309"); ax.get_xticklabels()[i].set_fontweight("bold")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v,p:f"{int(v):,}"))
    ax.set_ylim(0,maxv*1.18); ax.grid(axis="y",color="#E5E7EB",linewidth=0.8,zorder=0)
    for s in ("top","right","left"): ax.spines[s].set_visible(False)
    ax.tick_params(axis="both",length=0); ax.margins(x=0.01)
    ax.set_title(f"잠정치 통계(품목별) — {TITLES.get(col,col)}",fontsize=17,fontweight="bold",loc="left",pad=26,color="#1F2937")
    ax.text(0,1.028,f"[{TITLES.get(col,col)}]  {n}개월(2년)  ·  [단위] 천 달러",transform=ax.transAxes,
            fontsize=10.5,color="#4B72E8",fontweight="bold")
    ax.legend(loc="upper center",bbox_to_anchor=(0.5,-0.09),ncol=3,frameon=False,fontsize=11,handlelength=1.1)
    if _inprog:  # (v3.75) 오독 방지 캡션 — 완결월과의 절대 비교 금지, 동월 동기간(YoY) 비교를 안내
        ax.text(0.5,-0.155,"※ 음영 표시 월은 아직 진행 중(월 전체 미집계)이라 막대가 낮게 보인다 — 완결월과 직접 비교하지 말고 전년 동월 같은 구간(1~10/1~20)끼리 비교할 것.",
                transform=ax.transAxes,ha="center",fontsize=10,color="#B45309")
    fig.tight_layout(); fig.savefig(outpath,bbox_inches="tight",facecolor="white"); plt.close(fig)

def main():
    a=[x for x in sys.argv[1:] if not x.startswith("-")]
    WORK=a[0] if (a and os.path.isdir(a[0])) else (os.environ.get("NMR_OUT") or
         (sorted(glob.glob("/sessions/*/mnt/outputs"))[-1] if glob.glob("/sessions/*/mnt/outputs") else "."))
    os.makedirs("charts",exist_ok=True)
    data, is_fresh = resolve_data(WORK)
    if data is None:
        print("[customs-chart] 데이터 없음 → 스킵"); return
    if (not is_fresh) and all(os.path.exists(v) for v in OUT.values()):
        print("[customs-chart] 변경없음·기존 차트 유지 → 스킵"); return
    months=data["months"][-MONTHS:]
    for col in ("total","semiconductor"):
        s=data["series"][col]; ser={k:s[k][-MONTHS:] for k in ("p10","p20","pm")}
        plot(months, ser, col, OUT[col]); print("saved:",OUT[col])

if __name__=="__main__":
    main()
