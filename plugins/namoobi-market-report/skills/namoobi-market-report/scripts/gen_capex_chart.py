# -*- coding: utf-8 -*-
# 3.1.8 AI 빅테크 CAPEX 차트 (req6 2026-07-12 전면 재작성 — 대시보드와 동일한 4분할 회사별 라인)
# 출력(cwd 상대): charts/capex_capex.png · capex_rev.png · capex_fcf.png · capex_ratio.png
# 데이터: ① db/capex.json (통합 DB — companies/years/capex/revenue/fcf/capex_to_rev, Meta 포함 5개사)
#        ② argv[1] report_data.markets.bigtech_capex.{capex,rev,fcf}_series (라이브 오버라이드)
# 회사: Microsoft · Amazon · Alphabet · Meta · Oracle (5개사 — req6 '메타 추가' 반영)
import os, sys, glob, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

_cands=[os.path.join(os.path.dirname(__file__),"fonts","nmr_kr.ttf"), os.path.join(os.getcwd(),"fonts","nmr_kr.ttf")]
_f=[p for p in _cands if os.path.exists(p)] or glob.glob("/sessions/*/mnt/**/namoobi-market-report/scripts/fonts/nmr_kr.ttf", recursive=True)
if _f: fm.fontManager.addfont(_f[0]); matplotlib.rcParams["font.family"]="NanumBarunGothic"
matplotlib.rcParams["axes.unicode_minus"]=False

COLORS={"Microsoft":"#4A90E2","Amazon":"#F5A623","Alphabet":"#2E9E5B","Meta":"#7C4DFF","Oracle":"#E2342E"}

def _num(x):
    try:
        v=float(str(x).replace(",",""))
        return v
    except Exception: return None

def _load_db():
    for p in (glob.glob("/sessions/*/mnt/claudeCowork/namoobi-market-report-server/db/capex.json")
              + glob.glob(os.path.join(os.getcwd(),"namoobi-market-report-server","db","capex.json"))):
        try:
            d=json.load(open(p,encoding="utf-8")); return d.get("data") or d
        except Exception: pass
    return None

def _from_report(rd):
    try:
        cx=(rd.get("markets") or {}).get("bigtech_capex") or {}
        out={}
        for key,src in (("capex","capex_series"),("revenue","rev_series"),("fcf","fcf_series")):
            s=cx.get(src) or {}
            if s.get("years"):
                out.setdefault("years",s["years"])
                out[key]={k:v for k,v in s.items() if k!="years"}
        return out if out.get("years") else None
    except Exception: return None

db=_load_db() or {}
rd=None
if len(sys.argv)>1 and os.path.isfile(sys.argv[1]):
    try: rd=json.load(open(sys.argv[1],encoding="utf-8"))
    except Exception: rd=None
ov=_from_report(rd) if rd else None

years=[str(y) for y in (db.get("years") or (ov or {}).get("years") or [])]
comps=db.get("companies") or list(COLORS)
SERIES={"capex":("CAPEX 추이 (십억 달러)","capex_capex.png"),
        "revenue":("매출 추이 (십억 달러)","capex_rev.png"),
        "fcf":("잉여현금흐름 FCF (십억 달러)","capex_fcf.png"),
        "capex_to_rev":("CAPEX / 매출 — AI 투자 강도 (%)","capex_ratio.png")}
os.makedirs("charts",exist_ok=True)
made=0
for key,(title,fname) in SERIES.items():
    data=db.get(key) or {}
    if ov and key in ("capex","revenue","fcf") and ov.get(key): data={**data, **ov[key]}
    if not years or not data: print(f"capex chart {key}: 데이터 없음 → 스킵"); continue
    fig,ax=plt.subplots(figsize=(9.2,3.5),dpi=150)
    plotted=0
    for c in comps:
        vals=[_num(v) for v in (data.get(c) or [])]
        if not any(v is not None for v in vals): continue
        xs=[y for y,v in zip(years,vals) if v is not None]
        ys=[v for v in vals if v is not None]
        ax.plot(xs,ys,marker="o",ms=4.5,lw=2.0,color=COLORS.get(c,"#9CA3AF"),label=c)
        plotted+=1
    if not plotted: plt.close(fig); continue
    ax.set_title(title,fontsize=13,fontweight="bold")
    ax.grid(alpha=0.2); ax.legend(fontsize=8,frameon=False,ncol=5,loc="upper left")
    for sp in ("top","right"): ax.spines[sp].set_visible(False)
    ax.text(0,-0.18,"실선=실적(2023~2025)·이후=가이던스/컨센서스(E) — 자료: 각사 SEC/FMP · db/capex.json (매일 대조·변동 셀만 갱신)",
            transform=ax.transAxes,fontsize=7.5,color="#666")
    plt.tight_layout(); plt.savefig(f"charts/{fname}",dpi=150,bbox_inches="tight"); plt.close(fig)
    made+=1; print(f"capex chart -> charts/{fname}")
print(f"capex charts: {made}/4 · 회사 {comps}")
