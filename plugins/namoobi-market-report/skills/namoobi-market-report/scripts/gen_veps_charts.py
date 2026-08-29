#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_veps_charts.py "$WORK" — (v3.72) 3.1.15 선행 EPS·신용잔고·HY스프레드·DDR5 vs 지수
서버 DB API 4종을 회수해 기사식 이중축 차트 4장 + 요약 JSON 생성 (Phase 1.5 · 완전 비차단).
  입력: http://161.33.190.254/api/db/{fwd_eps, margin_debt, series_hy_oas, series_mem_dram_spot}
  출력: $WORK/charts/veps_1..4.png + $WORK/nmr_veps.json (빌더 renderVeps 입력, merge.py가 m['veps']로)
  ① 선행이익(자체 프록시) vs KOSPI  ② 신용잔고 YoY vs S&P500(로그, 1997~)
  ③ HY 가산금리 vs S&P500(로그, 1997~)  ④ DDR5 현물가 vs KOSPI
x축은 전기간·연도 눈금(사용자 요구 2026-08-01). 실패 시 빈 JSON — 빌더가 섹션 생략.
"""
import json, math, os, sys, urllib.request
from datetime import datetime

WORK = sys.argv[1] if len(sys.argv) > 1 else "."
CH = os.path.join(WORK, "charts"); os.makedirs(CH, exist_ok=True)
API = "http://161.33.190.254/api/db/"

def jget(name):
    for _ in range(3):
        try:
            with urllib.request.urlopen(API + name, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            pass
    return None

def main():
    F, M, HY, D = jget("fwd_eps"), jget("margin_debt"), jget("series_hy_oas"), jget("series_mem_dram_spot")
    out = {"as_of": datetime.now().strftime("%Y-%m-%d %H:%M")}
    if not (M and HY):
        print("[veps] 서버 API 실패 — 섹션 생략(비차단)"); json.dump({}, open(os.path.join(WORK, "nmr_veps.json"), "w")); return

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager as fm, dates as mdates
    ko = [f.name for f in fm.fontManager.ttflist if "CJK" in f.name or "Nanum" in f.name or "Malgun" in f.name]
    if ko: plt.rcParams["font.family"] = ko[0]
    plt.rcParams["axes.unicode_minus"] = False
    RED, GRAY = "#c0392b", "#6b7280"
    def dt(s):
        s = str(s).replace("-", "")
        return datetime(int(s[:4]), int(s[4:6]), int(s[6:8]) if len(s) >= 8 else 1)
    def base():
        fig, ax = plt.subplots(figsize=(9.6, 3.4), dpi=130); ax2 = ax.twinx()
        for a in (ax, ax2): a.tick_params(labelsize=8)
        ax.grid(alpha=.25, lw=.5); return fig, ax, ax2
    def finish(fig, ax, ax2, fn, yearly=True, marks=None):
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y" if yearly else "%y.%m"))
        for m, lb in (marks or []):
            ax.axvline(dt(m), color="#9aa2ad", ls=":", lw=.9)
            ax.annotate(lb, (dt(m), 1), xycoords=("data", "axes fraction"), ha="left", va="top",
                        fontsize=7, color="#6b7280", xytext=(2, -2), textcoords="offset points")
        h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8, frameon=False)
        fig.tight_layout(); fig.savefig(os.path.join(CH, fn)); plt.close(fig)

    # ① 선행이익 vs KOSPI — (v3.84e · 2026-08-29 사용자 지시) 보고서에서 제거.
    #   누적 11일차(개시 2026-08-01·과거 백필 불가)라 2년 KOSPI 축 우측 끝에 수직 지그재그로만 보여
    #   판독 불가였다. 서버 fwd_eps.py 일일 누적(16:20 크론)과 홈피 대시보드 패널은 유지 —
    #   수 개월 축적 후 재수록하려면 이 블록과 out["eps"] 를 복원하면 된다(빌더는 V.eps 없으면 자동 생략).
    #   ※ F(fwd_eps) 회수는 ④ DDR5 vs KOSPI 의 kospi_hist 입력으로 계속 필요하니 유지한다.
    # ② 신용잔고 YoY vs S&P500(로그)
    spx_t = [dt(t) for t in (M.get("spx") or {}).get("t") or []]
    spx_v = [math.log(v) for v in (M.get("spx") or {}).get("v") or []]
    fig, ax, ax2 = base()
    ax2.plot(spx_t, spx_v, color=GRAY, lw=1.1, label="S&P500(로그)")
    ax.plot([dt(t) for t in M["t"]], [v if v is not None else float("nan") for v in M["yoy"]],
            color=RED, lw=1.2, label="신용잔고 YoY%")
    ax.axhline(0, color="#bbb", lw=.7)
    ax.set_ylabel("신용잔고 YoY(%)", fontsize=8, color=RED); ax2.set_ylabel("S&P500 log", fontsize=8, color=GRAY)
    finish(fig, ax, ax2, "veps_2.png", marks=[("20000301", "00.3"), ("20071001", "07.10"), ("20211101", "21.11")])
    mi = len(M["t"]) - 1; cur = M["yoy"][mi]
    pk = max(v for v in M["yoy"][-24:] if v is not None)
    out["margin"] = {"month": M["t"][mi], "debit_t": round(M["debit"][mi] / 1e6, 2), "yoy": cur, "peak2y": pk,
                     "turn": bool(cur is not None and cur < pk - 3)}
    # ③ HY 가산금리 vs S&P500(로그)
    fig, ax, ax2 = base()
    ax2.plot(spx_t, spx_v, color=GRAY, lw=1.1, label="S&P500(로그)")
    hd = HY["data"][::3] + [HY["data"][-1]]
    ax.plot([dt(r[0]) for r in hd], [r[1] for r in hd], color=RED, lw=1.0, label="HY 가산금리%p")
    ax.set_ylabel("HY 가산금리(%p)", fontsize=8, color=RED); ax2.set_ylabel("S&P500 log", fontsize=8, color=GRAY)
    finish(fig, ax, ax2, "veps_3.png",
           marks=[("20000301", "00.3"), ("20071001", "07.10"), ("20200201", "20.2"), ("20211201", "21.12")])
    hl = HY["data"][-1]
    out["hy"] = {"date": hl[0], "oas": hl[1], "y_hi": max(r[1] for r in HY["data"][-252:])}
    # ④ DDR5 vs KOSPI
    if D and D.get("data") and F and F.get("kospi_hist"):
        key = "DDR5 16Gb (2Gx8) 4800/5600"
        ddt = [r[0] for r in D["data"]]; ddv = [(r[1] or {}).get(key) for r in D["data"]]
        kh = F["kospi_hist"]; d0 = str(ddt[0]).replace("-", "")
        ki = [i for i, t in enumerate(kh["t"]) if t >= d0]
        fig, ax, ax2 = base()
        if ki:
            s = max(0, ki[0] - 5)
            ax2.plot([dt(t) for t in kh["t"][s:]], kh["v"][s:], color=GRAY, lw=1.1, label="KOSPI")
        ax.plot([dt(t) for t in ddt], [v if v is not None else float("nan") for v in ddv],
                color=RED, lw=1.6, marker="o", ms=2.5, label="DDR5 16Gb($)")
        ax.set_ylabel("DDR5 16Gb($)", fontsize=8, color=RED); ax2.set_ylabel("KOSPI(pt)", fontsize=8, color=GRAY)
        finish(fig, ax, ax2, "veps_4.png", yearly=False)
        dl = [v for v in ddv if v is not None]
        out["ddr"] = {"date": ddt[-1], "px": dl[-1], "start": dl[0],
                      "chg_pct": round((dl[-1] / dl[0] - 1) * 100, 1) if dl[0] else None}
    json.dump(out, open(os.path.join(WORK, "nmr_veps.json"), "w"), ensure_ascii=False)
    print("[veps] ✅ 차트 %d장 · margin %s YoY %s%% · HY %s %s%%p" %
          (sum(1 for f in ("veps_1", "veps_2", "veps_3", "veps_4") if os.path.exists(os.path.join(CH, f + ".png"))),
           out.get("margin", {}).get("month"), out.get("margin", {}).get("yoy"),
           out.get("hy", {}).get("date"), out.get("hy", {}).get("oas")))

if __name__ == "__main__":
    main()
