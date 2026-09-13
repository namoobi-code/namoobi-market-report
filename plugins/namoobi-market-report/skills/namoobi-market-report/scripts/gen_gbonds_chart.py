#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_gbonds_chart.py "$WORK" — (2026-09-13 신설) 3.1.1 「주요국 10년 국채금리」 차트 2장 + 표 JSON (Phase 1.5 · 완전 비차단)
  입력: http://161.33.190.254/api/db/gbonds  (서버 fetch_gbonds.py 05:25/15:25 — stooq 일별·FRED 월별 폴백, 11개국)
  출력: $WORK/charts/gbonds_1.png  ① 미국·독일·영국·일본·한국·중국 10년물 3년 추이
        $WORK/charts/gbonds_2.png  ② 유로존 — 독일·프랑스·이탈리아·스페인 + 우측 끝 분트 대비 스프레드(bp) 라벨
        $WORK/nmr_gbonds.json      = 서버 JSON 그대로(series 제외) + chart 경로 → merge m['gbonds'] → 빌더 renderGBonds
  홈피 3.1.1 패널(app.js)과 같은 API 를 쓰므로 리포트=홈피 동일. 실패 시 빈 JSON — 빌더가 블록 생략.
"""
import json, os, sys, urllib.request
from datetime import datetime

WORK = sys.argv[1] if len(sys.argv) > 1 else "."
CH = os.path.join(WORK, "charts"); os.makedirs(CH, exist_ok=True)
API = "http://161.33.190.254/api/db/gbonds"
OUTJ = os.path.join(WORK, "nmr_gbonds.json")

def jget():
    for _ in range(3):
        try:
            with urllib.request.urlopen(API, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            pass
    return None

def main():
    G = jget()
    if not (G and G.get("countries") and G.get("series")):
        print("[gbonds] 서버 API 실패 — 블록 생략(비차단)"); json.dump({}, open(OUTJ, "w")); return
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager as fm, dates as mdates
    ko = [f.name for f in fm.fontManager.ttflist if "CJK" in f.name or "Nanum" in f.name or "Malgun" in f.name]
    if ko: plt.rcParams["font.family"] = ko[0]
    plt.rcParams["axes.unicode_minus"] = False
    PAL = ["#d64545", "#2f6fd0", "#1e9e6a", "#e08c1a", "#8358c4", "#0d9488", "#be185d"]
    name = {c["cc"]: c["name"] for c in G["countries"]}
    SR = G["series"]
    def dt(s): return datetime.strptime(s[:10], "%Y-%m-%d")

    def draw(fn, ccs, title, spread_vs=None, bold=()):
        fig, ax = plt.subplots(figsize=(9.6, 3.6), dpi=130)
        ax.grid(alpha=.25, lw=.5); ax.tick_params(labelsize=8)
        last = {}
        for i, cc in enumerate(ccs):
            s = SR.get(cc) or []
            if not s: continue
            xs = [dt(p[0]) for p in s]; ys = [p[1] for p in s]
            ax.plot(xs, ys, color=PAL[i % len(PAL)], lw=2.2 if cc in bold else 1.4, label=name.get(cc, cc))
            last[cc] = (xs[-1], ys[-1])
            ax.annotate(f"{ys[-1]:.2f}", (xs[-1], ys[-1]), xytext=(4, 0), textcoords="offset points",
                        fontsize=7.5, color=PAL[i % len(PAL)], va="center")
        if spread_vs and spread_vs in last:
            parts = []
            for cc in ccs:
                if cc != spread_vs and cc in last:
                    parts.append(f"{name.get(cc, cc)}−{name.get(spread_vs)} {(last[cc][1] - last[spread_vs][1]) * 100:+.0f}bp")
            if parts:
                ax.text(0.01, 0.97, "분트 대비 스프레드: " + " · ".join(parts), transform=ax.transAxes,
                        fontsize=8, va="top", color="#374151",
                        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#e5e7eb", alpha=.9))
        ax.set_title(title, fontsize=10, loc="left"); ax.set_ylabel("%", fontsize=8)
        ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.legend(loc="upper left" if not spread_vs else "lower left", fontsize=8, frameon=False, ncol=3)
        fig.tight_layout(); fig.savefig(os.path.join(CH, fn)); plt.close(fig)
        return True

    ok1 = draw("gbonds_1.png", ["US", "DE", "GB", "JP", "KR", "CN"], "① 주요국 10년 국채금리 — 미국·독일·영국·일본·한국·중국 (3년)", bold=("US", "KR"))
    ok2 = draw("gbonds_2.png", ["DE", "FR", "IT", "ES"], "② 유로존 10년 국채금리 — 독일(분트)·프랑스·이탈리아·스페인 (3년)", spread_vs="DE", bold=("DE",))
    out = {k: v for k, v in G.items() if k != "series"}
    out["chart1"] = "charts/gbonds_1.png" if ok1 else None
    out["chart2"] = "charts/gbonds_2.png" if ok2 else None
    out["generated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    json.dump(out, open(OUTJ, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[gbonds] {len(G['countries'])}국 · 차트 2장 · as_of {G.get('as_of')}")

if __name__ == "__main__":
    try: main()
    except Exception as e:
        print("[gbonds] 실패(비차단):", type(e).__name__, e); json.dump({}, open(OUTJ, "w"))
# EOF — namoobi-market-report gen_gbonds_chart
