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
def _mser(start_ym, vals):
    y,m=[int(z) for z in start_ym.split("-")]; out=[]
    for v in vals:
        out.append([f"{y:04d}-{m:02d}", v]); m+=1
        if m>12: m=1; y+=1
    return out
# (v3.57) 수집 불가한 하드코딩 연도 시계열(hbm_shipment/hbm_market/hbm3e_price/hbm4_price/share 2024~2027)
#   제거. 해당 값들은 어떤 소스로도 연도별 시계열을 확보할 수 없어 매 실행 동일한 고정 그림만 그려졌고,
#   HBMAgent 가 수집한 최신 실측 스칼라는 _compat 스키마 불일치로 전량 폐기되고 있었다(실측 점유율
#   32/56/10/2%E 대신 2024년 고정값 42/52/5/1 이 렌더됨). 이제 LIVE 실측만 사용한다.
DEF={}

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
fig=plt.figure(figsize=(15.0,10.6), dpi=150)
fig.suptitle("반도체 주가 체크용 메모리·HBM 지표 (실측)", fontsize=22, fontweight="bold", y=0.974)
_src=D.get("source") or "TrendForce·실적 컨센서스·언론 종합"
_tag="추정치" if USED_LIVE else "예시·추정 데이터"
# 차트별 갱신 주기·최종 갱신일 라벨
_CAD={"spot":"월별 추정","dram":"월별 추정","ship":"분기·연간 추정","hbmprice":"분기 추정","share":"분기 추정","gap":"분기 추정(계산값)"}
_CAD.update(D.get("cadence") or {})
_AM=D.get("asof_map") or {}; _ASOF=D.get("asof","")
def cad(k):
    a=_AM.get(k) or ((_ASOF) if _ASOF and _ASOF!="예시·추정" else None)
    return "  ▪ "+_CAD.get(k,"추정")+(" · 최종 갱신 "+a if a else " (예시값)")
fig.text(0.5,0.917, f"※ 모든 수치는 {_tag} — 확인 불가 항목은 미표기('추정' 표기)",
         ha="center", fontsize=11.5, color="#B45309")
OUT="charts/hbm_dashboard.png"
gs=fig.add_gridspec(1,2, top=0.80, bottom=0.20, left=0.07, right=0.98, wspace=0.30)
def style(ax):
    for sp in ("top","right"): ax.spines[sp].set_visible(False)
def caption(ax, text, y=-0.22):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=11, color="#555", va="top", wrap=True)

def _num(o, *keys):
    """LIVE 스칼라에서 숫자 추출.
    대응: 47.8 / "32%E" / "20-28"(중간값) / "~500 (mid-$500s)" / "300-360" / value_pct=89.0
    실측값이 'E'(추정) 접미사나 단위·기호를 달고 오는 경우가 많아 정규식으로 첫 수치를 뽑는다."""
    import re as _re
    if not isinstance(o, dict): return None
    for k in keys:
        v = o.get(k)
        if v in ("", None): continue
        if isinstance(v, (int, float)): return float(v)
        t = str(v)
        nums = _re.findall(r"\d+(?:\.\d+)?", t)
        if not nums: continue
        if len(nums) >= 2 and _re.search(r"\d\s*[-~]\s*\d", t):   # "20-28" → 중간값
            return (float(nums[0]) + float(nums[1])) / 2
        return float(nums[0])
    return None

# ── 패널 1: 메모리 스팟 현재가 (LIVE 실측)
ax1=fig.add_subplot(gs[0,0])
spot=[("DDR5 16Gb", _num(D.get("ddr5_16gb"),"value")),
      ("DDR4 8Gb",  _num(D.get("ddr4_8gb"),"value")),
      ("NAND MLC 64Gb", _num(D.get("nand_mlc_64gb"),"value","value_range"))]
spot=[(n,v) for n,v in spot if v is not None]
if spot:
    ax1.bar([n for n,_ in spot],[v for _,v in spot], width=0.5, color=[C_DDR5,C_DDR4,C_NAND][:len(spot)])
    for i,(n,v) in enumerate(spot):
        ax1.text(i, v*1.02, f"${v:g}", ha="center", fontsize=13, fontweight="bold")
    ax1.set_ylim(top=max(v for _,v in spot)*1.22)
ax1.set_title("메모리 스팟 현재가 (USD)", fontsize=18, fontweight="bold")
ax1.set_ylabel("USD"); style(ax1); ax1.grid(**GRID)
_gap=_num(D.get("gap_ratio"),"value_pct","value")
caption(ax1, "[실측] TrendForce/DRAMeXchange 스팟." + (f" DDR4 스팟-계약가 갭 +{_gap:g}% → 계약가 추가 인상 압력." if _gap else ""))

# ── 패널 2: HBM 업체별 점유율 (LIVE 실측 — 종전엔 2024년 고정값이 렌더됐음)
ax2=fig.add_subplot(gs[0,1])
_sh=D.get("share") or {}
_pairs=[("Samsung",_num(_sh,"samsung")),("SK hynix",_num(_sh,"sk_hynix")),
        ("Micron",_num(_sh,"micron")),("기타",_num(_sh,"others"))]
_pairs=[(n,v) for n,v in _pairs if v is not None]
if _pairs:
    cols=[C_SAMS,C_SK,C_MICRON,C_ETC][:len(_pairs)]
    ax2.bar([n for n,_ in _pairs],[v for _,v in _pairs], width=0.55, color=cols)
    for i,(n,v) in enumerate(_pairs):
        ax2.text(i, v+1.2, f"{v:g}%", ha="center", fontsize=13, fontweight="bold")
    ax2.set_ylim(0, max(v for _,v in _pairs)*1.25)
ax2.set_title("HBM 업체별 점유율 (최신 실측)", fontsize=18, fontweight="bold")
ax2.set_ylabel("점유율 (%)"); style(ax2); ax2.grid(**GRID)
caption(ax2, "[실측] SK하이닉스 IDC(SEC 제출서류) 1Q26 기준 · 나머지는 벤더 집계 중간값(E). 갱신: %s" % (D.get("asof") or ""))

plt.savefig(OUT, dpi=150, facecolor="white"); plt.close()
print("hbm dashboard ->", os.path.abspath(OUT), os.path.getsize(OUT), "bytes | live_override:", USED_LIVE)

# ── (req6 2026-07-05) 3.1.11 반도체 사이클 3대 조기경보 차트 (charts/semi_cycle_signals.png) ──
# 입력: $WORK/nmr_semi_cycle.json(신규) 또는 연결폴더 db/semi_cycle.json 의 data.series (없으면 스킵·비차단)
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
