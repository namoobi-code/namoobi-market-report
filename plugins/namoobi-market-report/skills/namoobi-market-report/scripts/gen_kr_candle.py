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
def candle(df, flows, out, title):
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
    ap=[mpf.make_addplot(bbu,color="#3b82f6",width=0.7),mpf.make_addplot(bbd,color="#10b981",width=0.7),
        mpf.make_addplot(r,panel=2,color="#d97706",width=0.9,ylabel="RSI"),
        mpf.make_addplot(pd.Series(70,index=df.index),panel=2,color="#cbd5e1",width=0.5),
        mpf.make_addplot(pd.Series(30,index=df.index),panel=2,color="#cbd5e1",width=0.5),
        mpf.make_addplot(cF,panel=3,color="#dc2626",width=1.1,ylabel="누적순매수(조)"),
        mpf.make_addplot(cI,panel=3,color="#2563eb",width=1.1),
        mpf.make_addplot(cP,panel=3,color="#059669",width=1.1)]
    fig,axes=mpf.plot(df,type="candle",style=style,mav=(5,20,60,120),volume=True,addplot=ap,
        panel_ratios=(6,1.2,1.4,2.0),figratio=(15,10),figscale=1.15,returnfig=True,
        datetime_format="%y/%m",xrotation=0,tight_layout=True,title=dict(title=title,fontsize=11))
    if have:
        axes[6].legend(handles=[Line2D([0],[0],color="#dc2626",lw=1.4,label="외국인"),Line2D([0],[0],color="#2563eb",lw=1.4,label="기관"),Line2D([0],[0],color="#059669",lw=1.4,label="개인")],loc="upper left",fontsize=6.5,frameon=False,ncol=3)
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
        "KOSPI 1년 일봉 — 캔들+이동평균(5/20/60/120)+볼린저 / 거래량 / RSI / 누적순매수","KOSPI 1년 주봉 — 종가 + 이동평균"),
       ("kosdaq","kosdaq_ohlcv","kosdaq_flows_daily",
        "KOSDAQ 1년 일봉 — 캔들+이동평균(5/20/60/120)+볼린저 / 거래량 / RSI / 누적순매수","KOSDAQ 1년 주봉 — 종가 + 이동평균")]
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
                candle(df, kr.get(fkey), f"charts/{name}_tech.png", tc); done=True; print(name,"캔들 OK(",len(df),"행)")
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
