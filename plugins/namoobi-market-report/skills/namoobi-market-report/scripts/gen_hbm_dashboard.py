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
    for pat in (O+"/namoobi-market-report-server/db/memory.json",
                O+"/../namoobi-market-report-server/db/memory.json",
                "/sessions/*/mnt/claudeCowork/namoobi-market-report-server/db/memory.json"):
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
    for pat in (O+"/namoobi-market-report-server/db/series_mem_%s.json"%key,
                O+"/../namoobi-market-report-server/db/series_mem_%s.json"%key,
                "/sessions/*/mnt/claudeCowork/namoobi-market-report-server/db/series_mem_%s.json"%key):
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

    fig=plt.figure(figsize=(16.0,21.8), dpi=150)
    fig.suptitle("반도체 주가 체크용 메모리·HBM 지표 (가격·주가 실측 + ⑦⑧⑨ 공개 추정 환산)",
                 fontsize=21, fontweight="bold", y=0.988)
    fig.text(0.5, 0.966, "기준 %s · TrendForce 공개 가격표 + Silicon Analysts 공개 API + Yole(시장규모) + Yahoo Finance(선행지표)"%(D.get("asof") or ""),
             ha="center", fontsize=11, color="#666")
    gs=fig.add_gridspec(6,2, top=0.935, bottom=0.045, left=0.055, right=0.985,
                        hspace=0.95, wspace=0.22)

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

    # ⑦ HBM ASP 추이 (req10 2026-07-12 — docx에도 표시)
    ax7a=fig.add_subplot(gs[3,0])
    aser=_series("hbm_asp")
    if len(aser)>=2:
        xs=[datetime.strptime(r[0],"%Y-%m-%d") for r in aser]
        items=sorted({k for r in aser for k in r[1]})
        for i,it in enumerate(items):
            ax7a.plot(xs,[r[1].get(it) for r in aser],marker="o",ms=4,lw=1.8,color=PAL[i%len(PAL)],label=it)
        ax7a.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d")); ax7a.margins(x=0.06)
        ax7a.legend(fontsize=7,frameon=False)
        ax7a.set_title("⑦ HBM ASP 추이 (USD/스택)  (누적 %d일)"%len(aser),fontsize=13,fontweight="bold")
    elif aser:
        it=aser[-1][1]; nm=list(it.keys()); vv=[it[k] for k in nm]
        ax7a.bar(nm,vv,width=0.5,color=[C_HBM3E,C_HBM4,C_SPOT][:len(nm)])
        for i,v in enumerate(vv): ax7a.text(i,v*1.02,"$%s"%format(int(v),","),ha="center",fontsize=9,fontweight="bold")
        ax7a.set_xticklabels(nm,fontsize=7.5); ax7a.set_ylim(top=max(vv)*1.2)
        ax7a.set_title("⑦ HBM ASP (USD/스택)  (누적 1일 — 매일 08:30 자동 누적)",fontsize=13,fontweight="bold")
    else: ax7a.set_visible(False)
    if aser: ax7a.set_ylabel("USD",fontsize=9); _style(ax7a); _cap(ax7a,"[추정] Silicon Analysts 공개 API · 서버 daily cron(08:30 KST) 누적")

    # ⑧ HBM 시장규모·수요 증가율 (req9 2026-07-12 — 연간, Yole 추정)
    ax8a=fig.add_subplot(gs[3,1])
    mser=_series("hbm_market")
    if mser:
        yrs=[r[0] for r in mser]; mv=[list(r[1].values())[0] for r in mser]
        ax8a.bar(yrs,mv,width=0.5,color=C_MKT)
        for i,v in enumerate(mv):
            ax8a.text(i,v*1.02,"$%dB"%v,ha="center",fontsize=11,fontweight="bold")
            if i>0 and mv[i-1]:
                ax8a.text(i,v*0.5,"+%.0f%% YoY"%((v/mv[i-1]-1)*100),ha="center",fontsize=9,color="white",fontweight="bold")
        ax8a.set_ylim(top=max(mv)*1.22)
        ax8a.set_title("⑧ HBM 시장규모 · 수요 증가율 (연간, 추정)",fontsize=13,fontweight="bold")
        ax8a.set_ylabel("십억 달러",fontsize=9); _style(ax8a)
        _cap(ax8a,"[추정] Yole Group·TrendForce 연간 전망 — 연 1~2회 갱신(조사기관 발표 시)")
    else: ax8a.set_visible(False)

    # ⑨ HBM:DDR5 GB당 단가 격차 (req12 2026-07-12 — 환산 추정, 매일 계산)
    ax9a=fig.add_subplot(gs[4,0])
    gser=_series("hbm_ddr5_gap")
    if len(gser)>=2:
        xs=[datetime.strptime(r[0],"%Y-%m-%d") for r in gser]
        ax9a.plot(xs,[r[1].get("배율") for r in gser],marker="o",ms=5,lw=2.0,color=C_SPOT)
        ax9a.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d")); ax9a.margins(x=0.06)
        ax9a.set_title("⑨ HBM : DDR5 GB당 단가 격차 (배)  (누적 %d일)"%len(gser),fontsize=13,fontweight="bold")
    elif gser:
        g1=gser[-1][1]
        ax9a.bar(["HBM $/GB","DDR5 $/GB"],[g1.get("HBM $/GB") or 0,g1.get("DDR5 $/GB") or 0],width=0.45,color=[C_HBM3E,C_DDR4])
        for i,v in enumerate([g1.get("HBM $/GB") or 0,g1.get("DDR5 $/GB") or 0]):
            ax9a.text(i,v*1.02,"$%.1f"%v,ha="center",fontsize=11,fontweight="bold")
        ax9a.set_title("⑨ HBM : DDR5 GB당 단가 = %s배  (누적 1일 — 내일부터 추세선)"%(g1.get("배율") or "-"),fontsize=13,fontweight="bold")
    else: ax9a.set_visible(False)
    if gser: ax9a.set_ylabel("USD/GB · 배",fontsize=9); _style(ax9a)
    _cap(ax9a,"[환산 추정] HBM3E 스택 ASP÷용량 vs DDR5 계약가 $/GB 환산(칩가 없으면 모듈가 환산). 통상 5~6배 —\n     배율 급락 = 범용 DRAM 급등(삼성 상대 유리) 신호")

    # ─── (v3.60) 선행지표 2패널 ────────────────────────────────────────
    LD=D.get("leading") or {}

    # ⑩ 선행지표 1년 성과 — 수요처(NVDA) vs 공급자(MU) 괴리
    ax7=fig.add_subplot(gs[4,1])
    ORD=["SOX","NVDA","AMD","TSM","KOSPI","MU"]
    ln=[LD[k]["label"] for k in ORD if LD.get(k) and LD[k].get("chg_1y_pct") is not None]
    lv=[LD[k]["chg_1y_pct"] for k in ORD if LD.get(k) and LD[k].get("chg_1y_pct") is not None]
    if lv:
        cols=[C_SPOT,C_DDR4,C_DDR5,C_NAND,C_ETC,C_SK][:len(lv)]
        ax7.bar(ln,lv,width=0.55,color=cols)
        for i,v in enumerate(lv):
            ax7.text(i, v+(max(lv)*0.02 if v>=0 else max(lv)*-0.05), "%+.0f%%"%v,
                     ha="center", fontsize=10, fontweight="bold")
        ax7.axhline(0,color="#888",lw=0.9)
        ax7.set_ylim(min(0,min(lv)*1.2), max(lv)*1.22)
        ax7.set_xticks(range(len(ln))); ax7.set_xticklabels(ln,fontsize=7.5)
    else:
        ax7.set_visible(False)
    ax7.set_title("⑩ 선행지표 1년 성과 — 수요처(엔비디아) vs 공급자(마이크론)",fontsize=13,fontweight="bold")
    ax7.set_ylabel("%",fontsize=9); _style(ax7)
    _cap(ax7,"[실측] Yahoo Finance · 반도체 업황(SOX) · HBM 수요처(NVDA·AMD) · CoWoS 병목(TSM)\n     공급자(MU)가 수요처를 크게 앞서면 = 메모리가 협상력을 쥔 공급부족 국면")

    # ⑪ 메모리/GPU 상대강도 — 가치 이동 신호 (누적 2일↑이면 추세선)
    ax8=fig.add_subplot(gs[5,0])
    fig.add_subplot(gs[5,1]).set_visible(False)
    rser=_series("mem_vs_gpu")
    rs=(LD.get("MEM_VS_GPU") or {}).get("value")
    if len(rser)>=2:
        xs=[datetime.strptime(r[0],"%Y-%m-%d") for r in rser]
        vs=[list(r[1].values())[0] for r in rser]
        ax8.plot(xs,vs,marker="o",ms=5,lw=2.2,color=C_GAP)
        ax8.axhline(1.0,color="#888",lw=1.0,ls="--")
        ax8.set_xticks(xs if len(xs)<=8 else xs[::max(1,len(xs)//7)])
        ax8.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        ax8.margins(x=0.06)
        ax8.set_title("⑪ 메모리/GPU 상대강도 (MU÷NVDA)  (누적 %d일)"%len(rser),fontsize=13,fontweight="bold")
    elif rs is not None:
        ax8.barh([0],[rs],height=0.38,color=C_GAP if rs>1 else C_DDR4)
        ax8.axvline(1.0,color="#888",lw=1.2,ls="--")
        ax8.text(rs*1.03, 0, "%.2f배 → %s"%(rs,(LD.get("MEM_VS_GPU") or {}).get("signal","")),
                 va="center", fontsize=12, fontweight="bold", color=C_GAP if rs>1 else C_DDR4)
        ax8.set_xlim(0, max(1.4, rs*1.42))
        ax8.set_ylim(-0.62, 0.62)
        ax8.set_yticks([0]); ax8.set_yticklabels(["MU ÷ NVDA (1년)"], fontsize=9)
        ax8.text(1.0, 0.44, "균형선(1.0)", ha="center", fontsize=8, color="#888")
        ax8.set_xlabel("배", fontsize=9)
        ax8.set_title("⑪ 메모리/GPU 상대강도 (MU÷NVDA)  (누적 1일 — 내일부터 추세선)",fontsize=13,fontweight="bold")
    else:
        ax8.set_visible(False)
    if len(rser)>=2: ax8.set_ylabel("배",fontsize=9)
    _style(ax8)
    _cap(ax8,"[계산] 1년 상승률 비율. 1 초과 = 가치가 수요처(GPU)→공급자(메모리)로 이동 = 공급부족 심화\n     꺾이기 시작하면 공급부족 완화 = 사이클 고점 경계 신호")

    OUT="charts/hbm_dashboard.png"
    os.makedirs("charts",exist_ok=True)
    plt.savefig(OUT, dpi=150, facecolor="white"); plt.close()
    print("hbm dashboard -> %s (%d bytes) | src=%s"%(OUT, os.path.getsize(OUT), SRC))


def _semi_cycle_signals():
    """(req7 2026-07-12) 재설계 — 정량 미공개 신호(재고주수·CAPEX YoY)는 빈 그래프 대신
    '판정상태(안전/주의/경보) 타임라인'(db/series_semi_status.json, 매일 누적)으로 표시하고,
    정량이 있는 DRAM 계약가 QoQ 만 수치 그래프로 남긴다."""
    import json as _j, glob as _g, os as _os
    sc=None
    for _p in [_os.path.join(_outdir(),"nmr_semi_cycle.json")]+_g.glob("/sessions/*/mnt/claudeCowork/namoobi-market-report-server/db/semi_cycle.json"):
        try:
            _d=_j.load(open(_p,encoding="utf-8")); _d=_d.get("data",_d)
            if isinstance(_d,dict) and isinstance(_d.get("series"),dict): sc=_d; break
        except Exception: pass
    st=[]
    for _p in _g.glob("/sessions/*/mnt/claudeCowork/namoobi-market-report-server/db/series_semi_status.json")+[_os.path.join(_outdir(),"namoobi-market-report-server","db","series_semi_status.json")]:
        try:
            _d=_j.load(open(_p,encoding="utf-8")); st=(_d.get("data") or []); break
        except Exception: pass
    if not sc and not st: print("semi_cycle_signals: 데이터 없음 → 스킵"); return
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(13.2,3.6))
    # ① DRAM 계약가 QoQ (정량 실측·전망)
    pq=(sc or {}).get("series",{}).get("price_qoq") or {}
    ax=axes[0]; xs0=pq.get("labels",[]); ys=pq.get("values",[])
    xs=[str(l).split(" ")[0].split("(")[0] for l in xs0]   # 긴 라벨 → 분기 토큰만
    if xs and ys:
        cols=["#EF9F27" if "E" in x.upper().replace("Q","") else "#1D9E75" for x in xs]
        ax.bar(xs,ys,color=cols)
        for x,y in zip(xs,ys): ax.annotate(f"+{y}%",(x,y),textcoords="offset points",xytext=(0,3),fontsize=9,ha="center")
        ax.set_title("① DRAM 계약가 상승률 QoQ (%) — 초록=실측·주황=전망(E)",fontsize=10)
    else:
        ax.text(0.5,0.5,"데이터 미확보",ha="center",va="center",fontsize=9,color="#94A3B8"); ax.set_xticks([])
        ax.set_title("① DRAM 계약가 상승률 QoQ",fontsize=10)
    ax.grid(alpha=.25,axis="y")
    # ② 3신호 판정상태 타임라인 (안전=0/주의=1/경보=2 · 매일 누적)
    ax=axes[1]
    if st:
        from datetime import datetime as _dt2
        xs=[_dt2.strptime(r[0],"%Y-%m-%d") for r in st]
        KEYS=[("inventory","재고주수","#1D9E75"),("price_qoq","DRAM 계약가 QoQ","#EF9F27"),("capex_yoy","SK하이닉스 CAPEX YoY","#378ADD")]
        off={"inventory":0.06,"price_qoq":0.0,"capex_yoy":-0.06}
        for k,lab,c in KEYS:
            vs=[(r[1] or {}).get(k) for r in st]
            pts=[(x,v+off[k]) for x,v in zip(xs,vs) if v is not None]
            if pts: ax.step([p[0] for p in pts],[p[1] for p in pts],where="post",lw=2.0,color=c,label=lab,marker="o",ms=5)
        ax.set_yticks([0,1,2]); ax.set_yticklabels(["안전","주의","경보"]); ax.set_ylim(-0.4,2.4)
        ax.axhspan(1.5,2.4,color="#FEE2E2",alpha=0.5)
        ax.legend(fontsize=7.5,frameon=False,loc="upper left",ncol=1)
        import matplotlib.dates as _md2
        ax.xaxis.set_major_formatter(_md2.DateFormatter("%m-%d"))
        ax.set_title("② 3대 조기경보 판정상태 타임라인 (매일 관측·DB 누적 %d일)"%len(st),fontsize=10)
        ax.grid(alpha=.2,axis="x")
    else:
        ax.text(0.5,0.5,"판정 누적 시작 전",ha="center",va="center",fontsize=9,color="#94A3B8"); ax.set_xticks([])
        ax.set_title("② 3대 조기경보 판정상태 타임라인",fontsize=10)
    for ax in axes:
        for sp in ["top","right"]: ax.spines[sp].set_visible(False)
    fig.text(0.01,-0.04,"판정 근거: 재고주수=TrendForce·공급사 코멘트(정량 비공개→정성 판정) · QoQ=TrendForce 계약가 전망 · CAPEX=회사 가이던스/실적 — 2개 이상 '경보'면 고점·하강 신호",fontsize=7.5,color="#666")
    plt.tight_layout(); plt.savefig("charts/semi_cycle_signals.png",dpi=110,bbox_inches="tight"); plt.close()
    print("semi_cycle_signals OK (QoQ+판정 타임라인)")
try: _semi_cycle_signals()
except Exception as _e: print("semi_cycle_signals 실패(비차단):",_e)
