#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_debt_charts.py "$WORK" — (v3.75) 3.1.8 하위블록 「조달 구조 — 회사채·부채 추이」
서버 DB(bigtech_debt)를 회수해 차트 2장 + 요약 JSON 생성 (Phase 1.5 · 완전 비차단).
  입력: http://161.33.190.254/api/db/bigtech_debt (fetch_bigtech_debt.py · 매일 06:45 · SEC EDGAR XBRL + FRED)
  출력: $WORK/charts/debt_1.png(증분부채÷CAPEX + 총부채) · debt_2.png(기업별 LTM 발행액)
        $WORK/nmr_debt.json (빌더 renderCapexFunding 입력, merge.py 가 m['bigtech_debt'] 로)
핵심 지표 = 증분부채 ÷ CAPEX. 자기 현금으로 짓던 데이터센터를 빚으로 짓기 시작한 전환점을 한 줄로 보여준다.
실패 시 빈 JSON — 빌더가 하위블록을 통째로 생략(3.1.8 본문은 그대로).
"""
import json, os, sys, urllib.request
from datetime import datetime

WORK = sys.argv[1] if len(sys.argv) > 1 else "."
CH = os.path.join(WORK, "charts"); os.makedirs(CH, exist_ok=True)
API = "http://161.33.190.254/api/db/"
COLS = {"MSFT": "#0ea5e9", "AMZN": "#b45309", "GOOGL": "#16a34a", "META": "#4f46e5", "ORCL": "#e11d48"}


def jget(name):
    for _ in range(3):
        try:
            with urllib.request.urlopen(API + name, timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            pass
    return None


def main():
    D = jget("bigtech_debt")
    out_p = os.path.join(WORK, "nmr_debt.json")
    if not D or not D.get("agg"):
        print("[debt] 서버 API 실패 — 하위블록 생략(비차단)")
        json.dump({}, open(out_p, "w")); return

    agg = D["agg"]; rows = D.get("rows", [])
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager as fm
    ko = [f.name for f in fm.fontManager.ttflist if "CJK" in f.name or "Nanum" in f.name or "Malgun" in f.name]
    if ko: plt.rcParams["font.family"] = ko[0]
    plt.rcParams["axes.unicode_minus"] = False

    xs = [a["d"][2:7] for a in agg]           # YY-MM
    # ── ① 총부채(막대) + 증분부채÷CAPEX(선·우축)
    fig, ax = plt.subplots(figsize=(9.2, 3.5))
    ax.bar(xs, [a.get("debt") for a in agg], color="#cbd5e1", label="5사 합산 총부채(십억$)")
    ax.set_ylabel("총부채 (십억 $)", fontsize=9)
    ax2 = ax.twinx()
    ax2.plot(xs, [a.get("dd_capex") for a in agg], color="#c0392b", lw=2.2, marker="o", ms=3.5,
             label="증분부채 ÷ CAPEX (%)")
    ax2.axhline(0, color="#94a3b8", lw=0.8, ls=":")
    ax2.set_ylabel("증분부채 ÷ CAPEX (%)", fontsize=9, color="#c0392b")
    ax2.tick_params(axis="y", colors="#c0392b", labelsize=8)
    ax.tick_params(axis="x", rotation=45, labelsize=7.5); ax.tick_params(axis="y", labelsize=8)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left", framealpha=0.9)
    ax.set_title("빅테크 5사 총부채와 '증분부채 ÷ CAPEX' — 현금 조달에서 차입 조달로", fontsize=10.5)
    ax.grid(axis="y", alpha=0.25); fig.tight_layout()
    fig.savefig(os.path.join(CH, "debt_1.png"), dpi=132); plt.close(fig)

    # ── ② 기업별 LTM 회사채 발행액
    fig, ax = plt.subplots(figsize=(9.2, 3.3))
    drew = 0
    for r in rows:
        ser = r.get("series", [])
        ys = []
        for a in agg:
            c = [s for s in ser if s["d"] <= a["d"] and s.get("issue_ltm") is not None]
            ys.append(c[-1]["issue_ltm"] if c else None)
        if not any(v is not None for v in ys):
            continue
        ax.plot(xs, ys, color=COLS.get(r["sym"], "#334155"), lw=1.8, marker="o", ms=3, label=r["name"])
        drew += 1
    ax.set_ylabel("최근 12개월 회사채 발행액 (십억 $)", fontsize=9)
    ax.tick_params(axis="x", rotation=45, labelsize=7.5); ax.tick_params(axis="y", labelsize=8)
    if drew: ax.legend(fontsize=8, ncol=3)
    ax.set_title("기업별 최근 12개월 회사채 발행액 — 누가 먼저·얼마나 크게 빚을 내는가", fontsize=10.5)
    ax.grid(alpha=0.25); fig.tight_layout()
    fig.savefig(os.path.join(CH, "debt_2.png"), dpi=132); plt.close(fig)

    last = agg[-1]
    prev = agg[-5] if len(agg) >= 5 else agg[0]
    summary = {
        "as_of": D.get("as_of"), "gen": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "last": last, "prev": prev,
        "rows": [{"sym": r["sym"], "name": r["name"],
                  "last": (r.get("series") or [{}])[-1]} for r in rows],
        "deals": D.get("deals", []), "ratings": D.get("ratings", []), "bench": D.get("bench", {}),
        "charts": ["charts/debt_1.png", "charts/debt_2.png"],
    }
    json.dump(summary, open(out_p, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[debt] ✅ {last['d']} 총부채 {last.get('debt')}B · 증분부채/CAPEX {last.get('dd_capex')}% · 차트 2장")


if __name__ == "__main__":
    main()
