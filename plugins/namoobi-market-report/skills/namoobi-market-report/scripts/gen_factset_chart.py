#!/usr/bin/env python3
# Key Metrics 6패널 대시보드 (자체 작성 · FactSet 이미지 비복제) — DB report.metrics 기반
import json, os, sys, glob
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

O = sys.argv[1] if (len(sys.argv) > 1 and os.path.isdir(sys.argv[1])) else (sorted(glob.glob("/sessions/*/mnt/outputs"))[-1])
for fp in [os.path.join(O, "fonts", "nmr_kr.ttf"), os.environ.get("NMR_FONT", "")]:
    if fp and os.path.exists(fp):
        font_manager.fontManager.addfont(fp); plt.rcParams["font.family"] = font_manager.FontProperties(fname=fp).get_name(); break
plt.rcParams["axes.unicode_minus"] = False

def load():
    for p in [os.path.join(O, "nmr_factset.json")] + glob.glob("/sessions/*/mnt/claudeCowork/_market_report_data/nmr_factset.json"):
        try: return json.load(open(p, encoding="utf-8"))
        except Exception: pass
    return {}

m = ((load().get("report") or {}).get("metrics")) or {}
if not m:
    print("dash skip: metrics 없음"); sys.exit(0)
B, N, S, G, R = "#60A5FA", "#1E3A8A", "#38BDF8", "#16A34A", "#DC2626"

# (key, title, ylab, fmt, colorfn, refline)
SPECS = [
 ("growth", "Earnings Growth (YoY)", "이익성장률 %", "+%.1f%%", lambda i,v,vs:(N if v==max(vs) else B), 20),
 ("revisions", "Earnings Revisions (Q2 추정)", "추정 성장률 %", "%.1f%%", lambda i,v,vs:(N if i==len(vs)-1 else S), None),
 ("guidance", "EPS Guidance (Q2, 기업수)", "기업 수", "%.0f", lambda i,v,vs:(G if i==0 else R), None),
 ("valuation", "Forward 12M P/E", "배(x)", "%.1f", lambda i,v,vs:(N if i==0 else (B if i==1 else S)), None),
 ("eps_vs_price", "EPS vs Price (3/31 이후 변화)", "% 변화", "+%.1f%%", lambda i,v,vs:(S if i==0 else N), None),
 ("rev_margin", "Revenue & Margin (Q2)", "%", "%.1f%%", lambda i,v,vs:(B if i==0 else G), None),
]
fig, axes = plt.subplots(2, 3, figsize=(11.2, 6.6), dpi=150)
fig.suptitle("S&P 500 Earnings Insight — Key Metrics (FactSet, 2026-06-26)", fontsize=13.5, fontweight="bold", color="#0F172A", y=0.995)
for ax, (key, title, ylab, fmt, cfn, ref) in zip(axes.flat, SPECS):
    ser = m.get(key) or []
    if not ser:
        ax.axis("off"); ax.set_title(title, fontsize=10.5, color="#94A3B8"); continue
    labels = [str(x[0]) for x in ser]; vals = [float(x[1]) for x in ser]
    cols = [cfn(i, vals[i], vals) for i in range(len(vals))]
    bb = ax.bar(labels, vals, width=0.6, color=cols)
    for b, v in zip(bb, vals):
        ax.annotate(fmt % v, (b.get_x()+b.get_width()/2, v), textcoords="offset points", xytext=(0, 3),
                    ha="center", fontsize=9, fontweight="bold", color="#0F172A")
    ax.set_title(title, fontsize=10.5, fontweight="bold", color="#0F172A")
    ax.set_ylabel(ylab, fontsize=7.5, color="#475569")
    ax.set_ylim(0, max(vals)*1.25); ax.grid(axis="y", alpha=0.2)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False); ax.tick_params(labelsize=8.5)
    if ref is not None: ax.axhline(ref, color="#94A3B8", lw=0.7, ls="--", alpha=0.7)
fig.text(0.5, 0.005, "데이터 출처: FactSet Earnings Insight (2026-06-26) — 공시 수치 기반 · 자체 작성 그래프(FactSet 차트 비복제)",
         ha="center", fontsize=8, color="#64748B")
plt.tight_layout(rect=[0, 0.02, 1, 0.96])
out = os.path.join(O, "charts", "factset_keymetrics.png"); os.makedirs(os.path.dirname(out), exist_ok=True)
plt.savefig(out, bbox_inches="tight"); plt.close()
print("OK ->", out)
