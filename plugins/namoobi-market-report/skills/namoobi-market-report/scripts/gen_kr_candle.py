# 3.1.1 한국 증시 기술적 차트 — robust (v3.6.31)
# 출력: charts/kospi_tech.png, charts/kosdaq_tech.png
# 1순위: nmr_kr_ohlcv.json 일봉 OHLCV(+다음 일별 수급)로 캔들 멀티패널(캔들+MA+볼린저/거래량/RSI/누적순매수)
#        — OHLCV 검증·세정(0/음수/High<Low/±40%급변/중복일/NaN 제거)으로 '차트 이상'(깨진 캔들·튀는 값) 차단.
# 2순위(폴백): 일봉 없거나 유효행 부족하면 nmr_indexseries.json 주봉 종가로 종가선+이동평균 차트
#        — 구버전은 파일 없으면 FileNotFoundError 크래시 → 3.1.1 통째 누락. 이제 항상 그린다.
import sys, glob, os, json, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm, matplotlib.pyplot as plt, matplotlib.dates as mdates
from matplotlib.lines import Line2D
_f=[p for p in [os.path.join(os.path.dirname(__file__),"fonts","nmr_kr.ttf"),"fonts/nmr_kr.ttf"] if os.path.exists(p)]
if _f: fm.fontManager.addfont(_f[0]); matplotlib.rcParams["font.family"]="NanumBarunGothic"
matplotlib.rcParams["axes.unicode_minus"]=False
def _ensure_mpf():  # v3.14: 캔들엔 mplfinance 필수 — 빌드환경(휘발성)에 없으면 자동설치, 실패할 때만 주봉 폴백
    try:
        import mplfinance  # noqa
        return True
    except Exception:
        import subprocess
        try:
            _rr=subprocess.run([sys.executable,"-m","pip","install","mplfinance","--prefer-binary","--break-system-packages","-q"],timeout=180)
            if getattr(_rr,"returncode",1)!=0:  # (v3.71) 1회 재시도 — 일시 네트워크/인덱스 오류 대비
                subprocess.run([sys.executable,"-m","pip","install","mplfinance","--prefer-binary","--break-system-packages","-q"],timeout=180)
            import importlib; importlib.invalidate_caches(); import mplfinance  # noqa
            return True
        except Exception as e:
            print("mplfinance 자동설치 실패 → 주봉 폴백:",repr(e)); return False
_HAS_MPF=_ensure_mpf()
O=sys.argv[1] if (len(sys.argv)>1 and os.path.isdir(sys.argv[1])) else (os.environ.get("NMR_OUT") or (sorted(glob.glob("/sessions/*/mnt/outputs"))[-1] if glob.glob("/sessions/*/mnt/outputs") else "."))
os.makedirs("charts", exist_ok=True)
def rsi(c,n=14):
    d=c.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0)
    return 100-100/(1+up.ewm(alpha=1/n,adjust=False).mean()/dn.ewm(alpha=1/n,adjust=False).mean().replace(0,np.nan))
def clean_ohlcv(rows):
    df=pd.DataFrame(rows,columns=["Date","Open","High","Low","Close","Volume"])
    df["Date"]=pd.to_datetime(df["Date"],errors="coerce")
    for c in ["Open","High","Low","Close","Volume"]: df[c]=pd.to_numeric(df[c],errors="coerce")
    df=df.dropna(subset=["Date","Open","High","Low","Close"])
    df=df[(df[["Open","High","Low","Close"]]>0).all(axis=1)]
    df=df[df["High"]>=df["Low"]]
    df=df.sort_values("Date").drop_duplicates("Date")
    if len(df)>3:
        r=df["Close"].pct_change().abs()
        df=df[(r.isna())|(r<0.40)]
    df["Volume"]=df["Volume"].fillna(0).clip(lower=0)
    return df.set_index("Date").sort_index()
def load_program():
    # (2026-08-02) 서버 수집 프로그램매매(차익·비차익, program_trading.py) — 3.2.1 캔들차트 5번째 패널
    # (v3.84f 재발방지 · 2026-08-29 실측) 로컬 사본 1순위 → 서버 폴백이던 순서가 사고 원인:
    #   서버는 매 영업일 16:15/18:40 누적(8/28·419일)하는데 로컬 사본은 8/2 도입 시점(7/31·400일)에
    #   멈춰 있어 차트가 한 달 stale 로 그려졌다('자동 최신화 안 됨'). → **서버 API 1순위**로 뒤집고,
    #   성공 시 로컬 사본을 write-through 갱신(리포트 실행일마다 최신화) · 로컬은 서버 불통 폴백 전용.
    _lp=(glob.glob("/sessions/*/mnt/claudeCowork/namoobi-market-report-server/data/db/program_trading.json")
         + ["D:/claudeCowork/namoobi-market-report-server/data/db/program_trading.json"])
    try:
        import urllib.request
        d=json.loads(urllib.request.urlopen("http://161.33.190.254/api/db/program_trading",timeout=20).read())
        if d and (d.get("kospi") or {}).get("t"):
            for p in _lp:
                try: json.dump(d, open(p,"w",encoding="utf-8"), ensure_ascii=False); break
                except Exception: pass
            return d
    except Exception as e:
        print("프로그램매매 서버 조회 실패 → 로컬 사본 폴백:",repr(e))
    for p in _lp:
        try: return json.load(open(p))
        except Exception: pass
    print("프로그램매매 데이터 없음(패널 생략)"); return None
PRG=load_program()
if PRG:
    try:  # build_report.js(3.2.1 표)용으로 워크디어에 전달
        json.dump(PRG, open(os.path.join(O,"nmr_program.json"),"w",encoding="utf-8"), ensure_ascii=False)
    except Exception as _pe: print("nmr_program.json 저장 실패:",repr(_pe))
def candle(df, flows, out, title, prg=None):
    import mplfinance as mpf
    mid=df["Close"].rolling(20).mean(); std=df["Close"].rolling(20).std()
    bbu=mid+2*std; bbd=mid-2*std; r=rsi(df["Close"])
    if flows:
        fdf=pd.DataFrame(flows,columns=["Date","F","I","P"]); fdf["Date"]=pd.to_datetime(fdf["Date"],errors="coerce")
        for c in ["F","I","P"]: fdf[c]=pd.to_numeric(fdf[c],errors="coerce")
        fdf=fdf.dropna(subset=["Date"]).drop_duplicates("Date").set_index("Date").sort_index()
        fdf=fdf.reindex(df.index, method="nearest", tolerance=pd.Timedelta("3D")).fillna(0.0)
        cF=fdf["F"].cumsum()/1e4; cI=fdf["I"].cumsum()/1e4; cP=fdf["P"].cumsum()/1e4; have=True
    else:
        cF=cI=cP=pd.Series(0.0,index=df.index); have=False
    mc=mpf.make_marketcolors(up="#e11d48",down="#2563eb",edge="inherit",wick="inherit",volume="#9ca3af")
    style=mpf.make_mpf_style(marketcolors=mc,gridstyle=":",gridcolor="#e5e7eb",facecolor="white",rc={"font.size":8,"font.family":"NanumBarunGothic","axes.unicode_minus":False})
    # (2026-08-30 근본수정) secondary_y=False 강제 — mplfinance 기본값 secondary_y="auto"가 같은 패널의
    # 스케일이 다른 시리즈를 임의로 우측 트윈축에 분리해 왔다(실측: RSI 기준선 30이 우축 29~31로,
    # 누적순매수 개인이 우축 0~100으로, 프로그램 비차익이 우축 ±5조로 분리 → 표·타 시리즈와 비교 불가한 '이상한 그래프').
    # 전 addplot 을 명시적으로 좌축 단일 스케일에 고정한다.
    ap=[mpf.make_addplot(bbu,color="#3b82f6",width=0.7,secondary_y=False),mpf.make_addplot(bbd,color="#10b981",width=0.7,secondary_y=False),
        mpf.make_addplot(r,panel=2,color="#d97706",width=0.9,ylabel="RSI",secondary_y=False),
        mpf.make_addplot(pd.Series(70,index=df.index),panel=2,color="#cbd5e1",width=0.5,secondary_y=False),
        mpf.make_addplot(pd.Series(30,index=df.index),panel=2,color="#cbd5e1",width=0.5,secondary_y=False),
        mpf.make_addplot(cF,panel=3,color="#dc2626",width=1.1,ylabel="누적순매수(조)",secondary_y=False),
        mpf.make_addplot(cI,panel=3,color="#2563eb",width=1.1,secondary_y=False),
        mpf.make_addplot(cP,panel=3,color="#059669",width=1.1,secondary_y=False)]
    # (2026-08-02) 5번째 패널 — 프로그램 차익/비차익 순매수(억원/일, 같은 X축·거래일 정렬)
    pr=(6,1.2,1.4,2.0); hasprg=False
    if prg and prg.get("t"):
        try:
            pt=pd.to_datetime(pd.Series(prg["t"]),format="%Y%m%d",errors="coerce")
            pa=pd.Series(pd.to_numeric(pd.Series(prg["arb"]),errors="coerce").values,index=pt)
            pn=pd.Series(pd.to_numeric(pd.Series(prg["nonarb"]),errors="coerce").values,index=pt)
            pa=pa[~pa.index.duplicated()].reindex(df.index); pn=pn[~pn.index.duplicated()].reindex(df.index)
            if pa.notna().sum()>=10:
                # 차익(수백~수천억)과 비차익(수천억~수조)을 같은 좌축에 그린다(secondary_y=False) —
                # 트윈축 분리 시 두 선이 비슷한 진폭으로 보여 규모 차이를 오독하게 만들던 결함 수정(2026-08-30).
                ap+=[mpf.make_addplot(pa,panel=4,color="#e08e3c",width=0.9,ylabel="프로그램(억)",secondary_y=False),
                     mpf.make_addplot(pn,panel=4,color="#1f6feb",width=0.9,secondary_y=False),
                     mpf.make_addplot(pd.Series(0.0,index=df.index),panel=4,color="#cbd5e1",width=0.5,secondary_y=False)]
                pr=(6,1.2,1.4,2.0,1.8); hasprg=True
        except Exception as e: print("프로그램 패널 생략:",repr(e))
    fig,axes=mpf.plot(df,type="candle",style=style,mav=(5,20,60,120),volume=True,addplot=ap,
        panel_ratios=pr,figratio=(15,11 if hasprg else 10),figscale=1.15,returnfig=True,
        datetime_format="%y/%m",xrotation=0,tight_layout=True,title=dict(title=title,fontsize=11))
    if have:
        axes[6].legend(handles=[Line2D([0],[0],color="#dc2626",lw=1.4,label="외국인"),Line2D([0],[0],color="#2563eb",lw=1.4,label="기관"),Line2D([0],[0],color="#059669",lw=1.4,label="개인")],loc="upper left",fontsize=6.5,frameon=False,ncol=3)
    if hasprg:
        axes[8].legend(handles=[Line2D([0],[0],color="#e08e3c",lw=1.4,label="차익 순매수"),Line2D([0],[0],color="#1f6feb",lw=1.4,label="비차익 순매수")],loc="upper left",fontsize=6.5,frameon=False,ncol=2)
    fig.savefig(out,dpi=150,bbox_inches="tight"); plt.close(fig)
def weekly_fallback(series, out, title):
    series=[p for p in series if p and p[1] is not None]
    if len(series)<5: return False
    xs=[pd.to_datetime(p[0]) for p in series]; c=np.array([float(p[1]) for p in series])
    ma=lambda w: pd.Series(c).rolling(w,min_periods=1).mean().values
    col="#e11d48" if c[-1]>=c[0] else "#2563eb"
    fig,ax=plt.subplots(figsize=(11,3.6),dpi=150)
    ax.plot(xs,c,color="#111827",lw=1.4,label="종가(주봉)")
    if len(c)>=4:  ax.plot(xs,ma(4), lw=0.9,color="#f59e0b",label="MA4주")
    if len(c)>=12: ax.plot(xs,ma(12),lw=0.9,color="#2563eb",label="MA12주")
    if len(c)>=26: ax.plot(xs,ma(26),lw=0.9,color="#16a34a",label="MA26주")
    ax.fill_between(xs,c,c.min(),color=col,alpha=0.06)
    chg=(c[-1]/c[0]-1)*100
    ax.set_title(f"{title}  최근 {c[-1]:,.2f} (1년 {chg:+.0f}%)",fontsize=11)
    ax.legend(loc="upper left",fontsize=8,ncol=4,frameon=False); ax.grid(alpha=0.2); ax.tick_params(labelsize=8)
    for s in ["top","right"]: ax.spines[s].set_visible(False)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m"))
    ax.text(0.012,0.035,"※ 일별 수급 데이터 미수집 — 주봉 종가 기반 약식 차트",transform=ax.transAxes,fontsize=7,color="#94a3b8")
    plt.tight_layout(); plt.savefig(out,dpi=150,bbox_inches="tight"); plt.close(); return True
def load(p):
    try: return json.load(open(p))
    except Exception: return None
kr=load(O+"/nmr_kr_ohlcv.json"); idx=load(O+"/nmr_indexseries.json")
specs=[("kospi","kospi_ohlcv","kospi_flows_daily",
        "KOSPI 1년 일봉 — 캔들+이동평균(5/20/60/120)+볼린저 / 거래량 / RSI / 누적순매수 / 프로그램","KOSPI 1년 주봉 — 종가 + 이동평균"),
       ("kosdaq","kosdaq_ohlcv","kosdaq_flows_daily",
        "KOSDAQ 1년 일봉 — 캔들+이동평균(5/20/60/120)+볼린저 / 거래량 / RSI / 누적순매수 / 프로그램","KOSDAQ 1년 주봉 — 종가 + 이동평균")]
for name,key,fkey,tc,tw in specs:
    done=False; mark=f"charts/{name}_tech.weekly"
    try:
        if os.path.exists(mark): os.remove(mark)  # 캔들 성공 시 직전 폴백 마커 제거
    except Exception: pass
    if os.path.exists(mark):  # (v3.71) 마운트가 unlink 차단(EPERM)해도 rename 은 허용 — 잔존 마커가 게이트 req1 을 오탐시키는 사례 수정
        try: os.rename(mark, f"charts/_dead_{name}_{os.getpid()}.weeklyold")
        except Exception as _me: print(name, "폴백마커 제거 실패(수동 mv 필요):", repr(_me))
    if _HAS_MPF and kr and kr.get(key):
        try:
            df=clean_ohlcv(kr[key])
            if len(df)>=30:
                candle(df, kr.get(fkey), f"charts/{name}_tech.png", tc, (PRG or {}).get(name)); done=True; print(name,"캔들 OK(",len(df),"행)")
            else: print(name,"일봉 유효행 부족(",len(df),") → 폴백")
        except Exception as e: print(name,"캔들 실패:",repr(e),"→ 폴백")
    if not done and idx and idx.get(name):
        if weekly_fallback(idx[name], f"charts/{name}_tech.png", tw):
            done=True
            try: open(mark,"w").write("weekly fallback (mplfinance 미설치 또는 일봉 부족) — 게이트가 차단")
            except Exception: pass
            print(name,"주봉 폴백 OK — 게이트 마커 기록")
    if not done: print(name,"차트 생성 실패(데이터 없음)")
print("kr tech charts done")
