# -*- coding: utf-8 -*-
# 6.3 김치 프리미엄 1Y 차트 (req19 2026-07-18 신규)
# 출력(cwd 상대): charts/kimp_30d.png — BTC·ETH·XRP·SOL 4분할, kimpwatda 30D 뷰와 같은 구간
# 데이터: 서버 /api/db/kimp_series (업비트÷(바이낸스×USD/KRW)−1 · 10분 수집 · 1년 백필)
import os, sys, glob, json, urllib.request
from datetime import datetime, timedelta
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

_cands=[os.path.join(os.path.dirname(__file__),"fonts","nmr_kr.ttf"), os.path.join(os.getcwd(),"fonts","nmr_kr.ttf")]
_f=[p for p in _cands if os.path.exists(p)] or glob.glob("/sessions/*/mnt/**/namoobi-market-report/scripts/fonts/nmr_kr.ttf", recursive=True)
if _f: fm.fontManager.addfont(_f[0]); matplotlib.rcParams["font.family"]="NanumBarunGothic"
matplotlib.rcParams["axes.unicode_minus"]=False

SRV="http://141.147.160.13/api/db/kimp_series"
SYMS=["BTC","ETH","XRP","SOL"]

def main():
    try:
        req=urllib.request.Request(SRV, headers={"User-Agent":"Mozilla/5.0"})
        d=json.loads(urllib.request.urlopen(req, timeout=20).read().decode())
    except Exception as e:
        print("kimp_series 조회 실패:", e); return 1
    st=d.get("s") or {}
    cut=(datetime.now()-timedelta(days=365)).strftime("%Y-%m-%d")  # (2차 req31) 1년
    fig,axes=plt.subplots(2,2,figsize=(11,5.6),dpi=110)
    for ax,s in zip(axes.flat, SYMS):
        arr=[x for x in (st.get(s) or []) if x[0]>=cut]
        if not arr:
            ax.set_title(f"{s} — 데이터 없음"); continue
        xs=list(range(len(arr))); ys=[x[1] for x in arr]
        ax.plot(xs, ys, color="#E2342E", lw=1.1)
        ax.fill_between(xs, ys, min(ys), color="#E2342E", alpha=.06)
        ax.axhline(0, color="#94A3B8", lw=.7, ls="--")
        cur=ys[-1]
        ax.set_title(f"{s} 김프 1Y   현재 {cur:+.2f}%  ·  최고 {max(ys):+.2f}%  ·  최저 {min(ys):+.2f}%",
                     fontsize=9.5, loc="left")
        # x축 눈금: 대략 6개 날짜
        step=max(1,len(arr)//8)
        ax.set_xticks(xs[::step]); ax.set_xticklabels([arr[i][0][5:10] for i in xs[::step]], fontsize=7.5)
        ax.tick_params(axis="y", labelsize=7.5)
        ax.yaxis.set_major_formatter(lambda v,_: f"{v:.1f}%")
        ax.grid(alpha=.25, lw=.4)
    fig.suptitle("김치 프리미엄 1Y — 업비트 ÷ (바이낸스 × USD/KRW) - 1 · 서버 10분 수집", fontsize=10)
    fig.tight_layout(rect=[0,0,1,0.95])
    os.makedirs("charts", exist_ok=True)
    out="charts/kimp_30d.png"  # 파일명은 빌더 호환 유지
    fig.savefig(out, bbox_inches="tight")
    print("saved", out)
    return 0

if __name__=="__main__":
    sys.exit(main())
