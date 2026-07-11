# -*- coding: utf-8 -*-
# 3.1.9 반도체 주가 체크용 메모리+HBM 지표 대시보드 생성기 (v3.10.0 신규)
# 출력(cwd 상대): charts/hbm_dashboard.png
#   - 빌더(build_report.js renderKoreaExtras)가 ③그룹 첫 항목(3.1.9)에 imagePara 로 임베드.
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
matplotlib.rcParams.update({"font.size":14,"axes.titlesize":20,"axes.labelsize":15,"xtick.labelsize":13.5,"ytick.labelsize":13.5,"legend.fontsize":12.5})

C_SPOT="#7C4DFF"; C_DDR5="#F5A623"; C_DDR4="#4A90E2"; C_NAND="#2E9E5B"
C_SHIP="#4A90E2"; C_MKT="#2E9E5B"; C_HBM3E="#F5A623"; C_HBM4="#7C4DFF"
C_SAMS="#4A90E2"; C_SK="#F5A623"; C_MICRON="#2E9E5B"; C_ETC="#9CA3AF"; C_GAP="#E2342E"
GRID=dict(alpha=0.18, linewidth=0.8)
LEG=dict(fontsize=12.5, frameon=True, framealpha=0.85, edgecolor="#E5E7EB", handletextpad=0.5, borderpad=0.4)

# ================= 내장 기본(예시·추정) =================
def _outdir():
    for a in sys.argv[1:]:
        if os.path.isdir(a): return a
    return os.environ.get("NMR_OUT") or "."

def _memdb():
    """(v3.59) 데이터 소스: ① db/memory.json (통합 DB — merge/서버 cron 이 매일 갱신)
                          ② WORK/nmr_memory.json (이번 회차 수집분)
    둘 다 없으면 차트 생략(비차단)."""
    O=_outdir()
    cands=[]
    for pat in (O+"/_market_report_data/db/memory.json",
                O+"/../_market_report_data/db/memory.json",
                "/sessions/*/mnt/claudeCowork/_market_report_data/db/memory.json"):
        cands += sorted(glob.glob(pat))
    for c in cands:
        try:
            d=json.load(open(c,encoding="utf-8"))
            return (d.get("data") or d), c
        except Exception: pass
    for c in sorted(glob.glob(O+"/nmr_memory.json")) + sorted(glob.glob("nmr_memory.json")):
        try: return json.load(open(c,encoding="utf-8")), c
        except Exception: pass
    return None, None

def _series(key):
    """db/series_mem_<key>.json 누적 시계열 → [(date, {item: val}), ...]"""
    O=_outdir()
    for pat in (O+"/_market_report_data/db/series_mem_%s.json"%key,
                O+"/../_market_report_data/db/series_mem_%s.json"%key,
                "/sessions/*/mnt/claudeCowork/_market_report_data/db/series_mem_%s.json"%key):
        for c in sorted(glob.glob(pat)):
            try:
                d=(json.load(open(c,encoding="utf-8")) or {}).get("data") or []
                return sorted(d, key=lambda r: r[0])
            except Exception: pass
    return []

D, SRC = _memdb()
if not D or not D.get("tables"):
    print("memory: 데이터 없음 — hbm_dashboard 차트 생략(비차단)")
else:
    T=D["tables"]; H=D.get("hbm") or {}
    PAL=[C_DDR5,C_DDR4,C_NAND,C_SPOT,C_SAMS,C_MICRON,C_ETC]

    def _style(ax):
        for sp in ("top","right"): ax.spines[sp].set_visible(False)
        ax.grid(**GRID)
    def _cap(ax, t, y=-0.27):
        ax.text(0,y,t,transform=ax.transAxes,fontsize=9,color="#666",va="top")

    def _trend(ax, key, title, ylab):
        """누적 시계열이 2점 이상이면 추세선, 1점이면 현재값 막대."""
        ser=_series(key)
        t=T.get(key) or {}
        if len(ser)>=2:
            xs=[datetime.strptime(r[0],"%Y-%m-%d") for r in ser]
            items=sorted({k for r in ser for k in r[1]})
            for i,it in enumerate(items):
                v=[r[1].get(it) for r in ser]
                ax.plot(xs,v,marker="o",ms=4,lw=1.8,color=PAL[i%len(PAL)],label=it)
            ax.set_xticks(xs if len(xs)<=8 else xs[::max(1,len(xs)//7)])
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
            ax.margins(x=0.06)
            ax.legend(fontsize=6.5,frameon=False,ncol=2)
            ax.set_title("%s  (누적 %d일)"%(title,len(ser)),fontsize=13,fontweight="bold")
        else:
            rows=t.get("rows") or []
            if not rows: ax.set_visible(False); return
            xs=range(len(rows)); vs=[r["avg"] for r in rows]
            ax.bar(xs,vs,width=0.55,color=[PAL[i%len(PAL)] for i in xs])
            for i,r in enumerate(rows):
                ax.text(i,r["avg"]*1.02,"%.1f"%r["avg"],ha="center",fontsize=8,fontweight="bold")
            ax.set_xticks(list(xs))
            ax.set_xticklabels([r["item"].replace(" (","\n(") for r in rows],fontsize=6.5)
            ax.set_ylim(top=max(vs)*1.2)
            ax.set_title("%s  (누적 1일 — 내일부터 추세선)"%title,fontsize=13,fontweight="bold")
        ax.set_ylabel(ylab,fontsize=9); _style(ax)
        _cap(ax,"[실측] TrendForce 공개 가격표 · 갱신 %s"%(t.get("last_update") or ""))

    fig=plt.figure(figsize=(16.0,12.2), dpi=150)
    fig.suptitle("반도체 주가 체크용 메모리·HBM 지표 (전 항목 실측·자동 수집)",
                 fontsize=21, fontweight="bold", y=0.982)
    fig.text(0.5, 0.941, "기준 %s · TrendForce 공개 가격표 + Silicon Analysts 공개 API"%(D.get("asof") or ""),
             ha="center", fontsize=11, color="#666")
    gs=fig.add_gridspec(3,2, top=0.885, bottom=0.085, left=0.055, right=0.985,
                        hspace=0.86, wspace=0.22)

    _trend(fig.add_subplot(gs[0,0]),"dram_spot",    "① DRAM 현물(스팟)",   "USD")
    _trend(fig.add_subplot(gs[0,1]),"dram_contract","② DRAM 고정거래(계약)","USD")
    _trend(fig.add_subplot(gs[1,0]),"nand_spot",    "③ NAND 현물(스팟)",   "USD")
    _trend(fig.add_subplot(gs[1,1]),"nand_contract","④ NAND 고정거래(계약)","USD")

    # ⑤ 스팟 − 계약 갭 (핵심 선행지표)
    ax5=fig.add_subplot(gs[2,0])
    g=lambda k: {r["item"]: r["avg"] for r in (T.get(k) or {}).get("rows",[])}
    ds,dc,ns,nc=g("dram_spot"),g("dram_contract"),g("nand_spot"),g("nand_contract")
    PAIRS=[("DDR4 8Gb","DDR4 8Gb (1Gx8) 3200","DDR4 8Gb 1Gx8",ds,dc),
           ("DDR4 16Gb","DDR4 16Gb (2Gx8) 3200","DDR4 16Gb 2Gx8",ds,dc),
           ("NAND 64Gb","MLC 64Gb 8GBx8","NAND 64Gb 8Gx8 MLC",ns,nc),
           ("NAND 32Gb","MLC 32Gb 4GBx8","NAND 32Gb 4Gx8 MLC",ns,nc)]
    lab,val=[],[]
    for l,si,ci,S,K in PAIRS:
        if si in S and ci in K and K[ci]:
            lab.append(l); val.append((S[si]/K[ci]-1)*100)
    if val:
        ax5.bar(lab,val,width=0.5,color=[C_GAP if v>0 else C_DDR4 for v in val])
        for i,v in enumerate(val):
            ax5.text(i, v+(3 if v>0 else -7), "%+.0f%%"%v, ha="center",
                     fontsize=11, fontweight="bold")
        ax5.axhline(0,color="#888",lw=0.9)
        ax5.set_ylim(min(val)*1.5 if min(val)<0 else 0, max(val)*1.28)
    ax5.set_title("⑤ 스팟-계약 갭 (계약가 인상 압력 선행지표)",fontsize=13,fontweight="bold")
    ax5.set_ylabel("%",fontsize=9); _style(ax5)
    _cap(ax5,"[계산] 현물÷계약-1. 현물이 계약가를 크게 상회하면 다음 계약 협상의 인상 압력\n     → 메모리 3사 실적 선행지표")

    # ⑥ HBM 업체별 점유율 (실측)
    ax6=fig.add_subplot(gs[2,1])
    sh=H.get("share") or []
    if sh:
        nm=[r["vendor"] for r in sh]; vv=[r.get("share_pct") or 0 for r in sh]
        ax6.bar(nm,vv,width=0.5,color=[C_SAMS,C_SK,C_MICRON,C_ETC][:len(nm)])
        for i,v in enumerate(vv):
            ax6.text(i,v+1.2,"%.0f%%"%v,ha="center",fontsize=12,fontweight="bold")
        ax6.set_ylim(0,max(vv)*1.25)
    else:
        ax6.set_visible(False)
    ax6.set_title("⑥ HBM 업체별 점유율 (최신 실측)",fontsize=13,fontweight="bold")
    ax6.set_ylabel("%",fontsize=9); _style(ax6)
    _cap(ax6,"[실측] Silicon Analysts 공개 API · %s"%(D.get("asof") or ""))

    OUT="charts/hbm_dashboard.png"
    os.makedirs("charts",exist_ok=True)
    plt.savefig(OUT, dpi=150, facecolor="white"); plt.close()
    print("hbm dashboard -> %s (%d bytes) | src=%s"%(OUT, os.path.getsize(OUT), SRC))


def _semi_cycle_signals():
    import json as _j, glob as _g, os as _os
    sc=None
    for _p in [_os.path.join(_outdir(),"nmr_semi_cycle.json")]+_g.glob("/sessions/*/mnt/claudeCowork/_market_report_data/db/semi_cycle.json"):
        try:
            _d=_j.load(open(_p,encoding="utf-8")); _d=_d.get("data",_d)
            if isinstance(_d,dict) and isinstance(_d.get("series"),dict): sc=_d; break
        except Exception: pass
    if not sc: print("semi_cycle_signals: series 없음 → 스킵"); return
    S=sc["series"]; import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(13.2,3.4))
    inv=S.get("inventory") or {}
    ax=axes[0]; xs=inv.get("labels",[]); ys=inv.get("values",[])
    if xs and ys:
        ax.plot(xs,ys,marker="o",color="#1D9E75",lw=2)
        al=inv.get("alert")
        if al is not None: ax.axhline(al,color="#E24B4A",ls="--",lw=1.3); ax.text(len(xs)-1,al+0.8,f"경보선 {al}주",color="#E24B4A",fontsize=8,ha="right")
        for x,y in zip(xs,ys): ax.annotate(f"{y}주",(x,y),textcoords="offset points",xytext=(0,7),fontsize=8,ha="center")
    ax.set_title("① 재고주수 (공급자 DRAM)",fontsize=10); ax.set_ylim(bottom=0); ax.grid(alpha=.25)
    pq=S.get("price_qoq") or {}
    ax=axes[1]; xs=pq.get("labels",[]); ys=pq.get("values",[])
    if xs and ys:
        cols=["#1D9E75" if not str(l).endswith("E") else "#EF9F27" for l in xs]
        ax.bar(xs,ys,color=cols)
        for x,y in zip(xs,ys): ax.annotate(f"+{y}%",(x,y),textcoords="offset points",xytext=(0,3),fontsize=8,ha="center")
    ax.set_title("② DRAM 계약가 상승률 (QoQ)",fontsize=10); ax.grid(alpha=.25,axis="y")
    cx=S.get("capex_yoy") or {}
    ax=axes[2]; xs=cx.get("labels",[]); ys=cx.get("values",[])
    if xs and ys:
        cols=["#378ADD" if y<0 else ("#639922" if y<40 and str(x).endswith("E") else "#BA7517") for x,y in zip(xs,ys)]
        ax.bar(xs,ys,color=cols); ax.axhline(0,color="#888",lw=.8)
        for x,y in zip(xs,ys): ax.annotate(f"{'+' if y>0 else ''}{y}%",(x,y),textcoords="offset points",xytext=(0,3 if y>=0 else -12),fontsize=8,ha="center")
    ax.set_title("③ CAPEX 증가율 (SK하이닉스·YoY)",fontsize=10); ax.grid(alpha=.25,axis="y")
    for ax in axes:
        for s in ["top","right"]: ax.spines[s].set_visible(False)
    plt.tight_layout(); plt.savefig("charts/semi_cycle_signals.png",dpi=110,bbox_inches="tight"); plt.close()
    print("semi_cycle_signals OK")
try: _semi_cycle_signals()
except Exception as _e: print("semi_cycle_signals 실패(비차단):",_e)
