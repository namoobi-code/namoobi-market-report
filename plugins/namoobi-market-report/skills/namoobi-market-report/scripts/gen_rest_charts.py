import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys, glob, os
# 출력(nmr_*.json) 디렉터리 자동 탐지 — argv[1] > NMR_OUT 환경변수 > 현재 세션 mnt/outputs (하드코딩 세션경로 금지)
O = sys.argv[1] if len(sys.argv) > 1 else (os.environ.get("NMR_OUT") or sorted(glob.glob("/sessions/*/mnt/outputs"))[-1])
GRN="#059669"; RED="#DC2626"
def spark(pairs,out):
    # (fix-r6) 추세(1Y) 라벨과 일치하도록 날짜형 시계열은 최근 365일만 사용(장기 시계열 혼입 시 색·모양 왜곡 방지)
    try:
        _dp=[p for p in pairs if p and p[1] is not None]
        if _dp and isinstance(_dp[-1][0],str) and len(str(_dp[-1][0]))>=10:
            from datetime import datetime as _dt, timedelta as _td
            _last=_dt.strptime(str(_dp[-1][0])[:10],'%Y-%m-%d'); _cut=(_last-_td(days=365)).strftime('%Y-%m-%d')
            _w=[p for p in _dp if str(p[0])[:10]>=_cut]
            if len(_w)>=2: pairs=_w
    except Exception: pass
    ys=[p[1] for p in pairs if p and p[1] is not None]
    if len(ys)<2: return False
    col=GRN if ys[-1]>=ys[0] else RED
    fig,ax=plt.subplots(figsize=(1.5,0.5),dpi=150)
    ax.plot(range(len(ys)),ys,color=col,linewidth=1.1)
    ax.fill_between(range(len(ys)),ys,min(ys),color=col,alpha=0.08)
    ax.axis("off"); ax.margins(x=0,y=0.1); ax.scatter([len(ys)-1],[ys[-1]],color=col,s=6,zorder=5)
    plt.tight_layout(pad=0); plt.savefig(out,bbox_inches="tight",transparent=True); plt.close(); return True
def mini(pairs,out):
    ys=[p[1] for p in pairs if p and p[1] is not None]
    if len(ys)<2: return False
    col=GRN if ys[-1]>=ys[0] else RED
    fig,ax=plt.subplots(figsize=(2.4,0.8),dpi=150)
    ax.plot(range(len(ys)),ys,color=col,linewidth=1.3)
    ax.fill_between(range(len(ys)),ys,min(ys),color=col,alpha=0.10)
    ax.axis("off"); ax.margins(x=0,y=0.12)
    chg=(ys[-1]/ys[0]-1)*100
    yrs=len(ys)/12.0  # nmr_themeseries1y/semi series 는 v3.6.33부터 10년 월별 → 실제 보유기간으로 라벨
    span=(f"{yrs:.0f}Y" if yrs>=1.2 else f"{len(ys)}M")
    ax.set_title(f"{chg:+.0f}% ({span})",fontsize=8,color=col,fontweight="bold")
    plt.tight_layout(pad=0.2); plt.savefig(out,bbox_inches="tight",transparent=True); plt.close(); return True

# theme 1Y (overwrite) — 데이터 주도: nmr_themeseries1y.json 의 모든 테마 키로 차트 생성 (AI·원자력·전력기기 등 신규 테마 자동 포함)
ts=json.load(open(O+"/nmr_themeseries1y.json"))
for t,series in ts.items():
    if series:
        t2=t.replace("/","_").replace(" ","_"); mini(series, f"charts/theme_{t2}.png")
# legacy 별칭: 우주 시계열 없으면 방산으로 대체
if not ts.get("우주") and ts.get("방산"): mini(ts["방산"], "charts/theme_우주.png")
print("theme charts:", sum(1 for v in ts.values() if v))

# commodities + strat + fx sparklines (1Y)
s2=json.load(open(O+"/nmr_series2.json"))
for k,v in s2.get("commodities",{}).items(): spark(v, f"charts/spark_{k}.png")
sm={"lit":"lit","remx":"remx","ura":"ura","urnm":"urnm"}
for k,v in s2.get("strat_etf",{}).items(): spark(v, f"charts/spark_{k}.png")
for k,v in s2["fx"].items(): spark(v, f"charts/spark_{k}.png")
print("sparklines: commodities",len(s2['commodities']),"strat",len(s2['strat_etf']),"fx",len(s2['fx']))

# 지수 1Y 스파크라인 (3.2 미국·3.3 아시아·3.4 유럽) — nmr_indexseries.json 있으면 (IndexSeriesAgent 수집)
try:
    idx=json.load(open(O+"/nmr_indexseries.json"))
    nidx=0
    for k,v in idx.items():
        if v and spark(v, f"charts/spark_{k}.png"): nidx+=1
    print("index sparklines:", nidx, "of", len(idx))
except FileNotFoundError:
    print("nmr_indexseries.json 없음 — 지수 스파크라인 생략")

# (v3.6.8) 미국 ETF 1Y 스파크라인 (3.2.2) — nmr_etfseries.json {SYMBOL:[["YYYY-MM-DD",close]..] 또는 [close..]}
try:
    et=json.load(open(O+"/nmr_etfseries.json"))
    netf=0
    for sym,series in et.items():
        if not series: continue
        pairs=series if isinstance(series[0],(list,tuple)) else [[i,v] for i,v in enumerate(series)]
        if spark(pairs, f"charts/spark_etf_{sym}.png"): netf+=1
    print("etf sparklines:", netf, "of", len(et))
except FileNotFoundError:
    print("nmr_etfseries.json 없음 — ETF 스파크라인 생략")

# crypto coin charts: price + volume (1Y)
cs=json.load(open(O+"/nmr_crypto_series.json"))
import matplotlib.dates as mdates
from datetime import datetime
def coin(rows,out,label):
    rows=[r for r in rows if r and r[1] is not None]
    if len(rows)<2: return False
    xs=[datetime.fromisoformat(r[0]) for r in rows]; pr=[r[1] for r in rows]; vol=[r[2] for r in rows]
    col=GRN if pr[-1]>=pr[0] else RED
    fig,(ax1,ax2)=plt.subplots(2,1,figsize=(3.4,2.0),dpi=150,sharex=True,gridspec_kw={"height_ratios":[3,1]})
    ax1.plot(xs,pr,color=col,linewidth=1.2); ax1.fill_between(xs,pr,min(pr),color=col,alpha=0.08)
    chg=(pr[-1]/pr[0]-1)*100
    ax1.set_title(f"{label}  ${pr[-1]:,.2f}  ({chg:+.0f}% 1Y)",fontsize=8,color="#111")
    ax1.tick_params(labelsize=6); ax1.grid(alpha=0.2)
    for s in ["top","right"]: ax1.spines[s].set_visible(False)
    ax2.bar(xs,vol,color="#9ca3af",width=2); ax2.tick_params(labelsize=6); ax2.set_ylabel("Vol",fontsize=6)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m"))
    for s in ["top","right"]: ax2.spines[s].set_visible(False)
    plt.tight_layout(pad=0.3); plt.savefig(out,bbox_inches="tight"); plt.close(); return True
coin(cs.get("btc",[]),"charts/coin_btc.png","BTC"); coin(cs.get("eth",[]),"charts/coin_eth.png","ETH")
coin(cs.get("xrp",[]),"charts/coin_xrp.png","XRP"); coin(cs.get("sol",[]),"charts/coin_sol.png","SOL")

# fear & greed 1Y
fng=[r for r in cs.get("fng",[]) if r and r[1] is not None]
if fng:
 xs=[datetime.fromisoformat(r[0]) for r in fng]; ys=[r[1] for r in fng]
 fig,ax=plt.subplots(figsize=(6.6,1.8),dpi=150)
 for lo,hi,c in [(0,25,"#fca5a5"),(25,45,"#fdba74"),(45,55,"#fde68a"),(55,75,"#bbf7d0"),(75,100,"#86efac")]:
     ax.axhspan(lo,hi,color=c,alpha=0.45)
 ax.plot(xs,ys,color="#111827",linewidth=1.1)
 ax.scatter([xs[-1]],[ys[-1]],color="#dc2626",s=22,zorder=5)
 ax.annotate(f"{ys[-1]}",(xs[-1],ys[-1]),fontsize=8,fontweight="bold",color="#dc2626",textcoords="offset points",xytext=(-22,4))
 ax.set_ylim(0,100); ax.set_title("Crypto Fear & Greed Index (1Y)",fontsize=9,color="#334155")
 ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m")); ax.tick_params(labelsize=7); ax.grid(alpha=0.15)
 for s in ["top","right"]: ax.spines[s].set_visible(False)
 plt.tight_layout(); plt.savefig("charts/fng_1y.png",bbox_inches="tight"); plt.close()
print("crypto+fng done")
# (v3.6.33) 반도체/AI 종목·ETF 추세차트(semi_s_<i>/semi_e_<i>) + 테마 10년 — 신스키마(semi_ai_stocks/etfs) 기반.
#   [근본원인] 구버전은 nmr_semi_series.json + nmr_koreamacro.semi_ai_breakdown(구스키마)로 charts/semi_<i>.png 를 만들었으나,
#   빌더는 신스키마 semi_ai_stocks/etfs 와 charts/semi_s_<i>.png·semi_e_<i>.png 를 참조 → 항상 불일치로 추세열이 "-" 였다.
#   [데이터 소스] 한국 종목/ETF 10년 월별 종가 = Yahoo .KS/.KQ (Daum charts API /charts/A{code}/days 는 현재 403).
#                 신규상장 종목은 가용 최대기간(라벨에 N년/N개월 표기), 수집 실패(소스 버그)는 아래 경고로 표면화한다.
import glob as _g
def _sani(s): return str(s).replace("/","_").replace(" ","_")
try:
    krs=json.load(open(O+"/nmr_kr_series.json"))
    rdc=sorted(_g.glob(O+"/_market_report_data/report_data_*.json"))
    M=(json.load(open(rdc[-1])).get("markets") if rdc else {}) or {}
    if not (M.get("semi_ai_stocks") or M.get("semi_ai_etfs")):  # (v3.71) merge 전(Phase 1.5)에도 semi_s_/semi_e_ 생성 — nmr_semi.json 직접 폴백
        try:
            _sm=json.load(open(O+"/nmr_semi.json"))
            M={**M,"semi_ai_stocks":(_sm.get("semi_ai_stocks") or [])[:20],"semi_ai_etfs":(_sm.get("semi_ai_etfs") or [])[:20]}
        except Exception as _se: print("semi fallback skip:",repr(_se)[:50])
    THEME_ORDER=["반도체/AI","전력기기","조선","방산","원자력","증권","로봇","우주"]
    th=krs.get("themes") or {}; nt=0
    for t in THEME_ORDER:
        s=th.get(t)
        if s and mini(s, "charts/theme_"+_sani(t)+".png"): nt+=1
    print("theme charts(10y):", nt, "of", len(THEME_ORDER))
    miss=[]; ns=0; ne=0
    for i,x in enumerate(M.get("semi_ai_stocks",[])):
        s=(krs.get("stocks") or {}).get(x.get("name"))
        if s and mini(s, f"charts/semi_s_{i}.png"): ns+=1
        else: miss.append("stock:"+str(x.get("name")))
    for i,x in enumerate(M.get("semi_ai_etfs",[])):
        s=(krs.get("etfs") or {}).get(x.get("name"))
        if s and mini(s, f"charts/semi_e_{i}.png"): ne+=1
        else: miss.append("etf:"+str(x.get("name")))
    print("semi_s:", ns, "of", len(M.get("semi_ai_stocks",[])), "| semi_e:", ne, "of", len(M.get("semi_ai_etfs",[])))
    if miss: print("⚠️ NMR_BLOCK 추세차트 미생성(데이터 확인 필요 — '-' 무단표시 금지 정책):", miss)
except FileNotFoundError as e:
    print("⚠️ NMR_BLOCK nmr_kr_series.json/report_data 없음 — 반도체/테마 추세차트 생략(수집 필요):", e)
import os; print("total chart files:", len([f for f in os.listdir('charts') if f.endswith('.png')]))

# (3.4.1) 아시아 주요 ETF(한국상장) 1Y 스파크라인 — nmr_asia_etf_series.json {code:[[date,close]..]} → charts/spark_aetf_<code>.png
try:
    ae=json.load(open(O+"/nmr_asia_etf_series.json")); nae=0
    for code,series in ae.items():
        if series and spark(series, f"charts/spark_aetf_{code}.png"): nae+=1
    print("asia etf sparklines:", nae, "of", len(ae))
except FileNotFoundError:
    print("nmr_asia_etf_series.json 없음 — 아시아 ETF 스파크라인 생략")
# (v3.51) [부록C] AI 반도체 밸류체인 1Y 스파크 — nmr_appc_series.json {sym:[[date,close]..]} → charts/spark_c_<sym(.→_)>.png
try:
    ac=json.load(open(O+"/nmr_appc_series.json")); nac=0
    for sym,series in ac.items():
        if series and spark(series, f"charts/spark_c_{sym.replace('.','_')}.png"): nac+=1
    print("appc sparklines:", nac, "of", len(ac))
except FileNotFoundError:
    print("nmr_appc_series.json 없음 — 부록C 스파크라인 생략")
