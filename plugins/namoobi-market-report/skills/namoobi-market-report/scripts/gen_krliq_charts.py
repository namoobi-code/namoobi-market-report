#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_krliq_charts.py — 3.1.14 차트 4종 (Phase 1.5).

입력: W/nmr_krliq.json (fetch_krliq.py) + deriv_signals.db(vkospi)
출력: charts/krliq_1.png  ① 예탁금 vs 거래대금 vs 코스피 + 회전배수 (2단, 제목에 자동판정)
      charts/krliq_2.png  ② M2 YoY vs 코스피·코스닥 YoY (월별 10년)
      charts/krliq_3.png  ③ 신용융자 vs 코스피 vs VKOSPI + 반대매매(미수금 기반) (2단)
      charts/krliq_4.png  ④ 코스닥 신용융자 vs 코스닥 지수 vs 비중 + 일간증감 (2단, 마진콜 조기경보)
      W/nmr_krliq_summary.json (merge → report_data.markets.kr_liquidity)
Usage: gen_krliq_charts.py <WORK_DIR>
"""
import json, os, sys, glob, sqlite3, datetime as dt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

W = sys.argv[1] if len(sys.argv) > 1 else "."
HERE = os.path.dirname(os.path.abspath(__file__))
for fp in (os.path.join(HERE, "fonts", "nmr_kr.ttf"),):
    if os.path.exists(fp):
        font_manager.fontManager.addfont(fp)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=fp).get_name()
plt.rcParams["axes.unicode_minus"] = False
os.makedirs(os.path.join(W, "charts"), exist_ok=True)
D = lambda s: dt.datetime.strptime(s, "%Y%m%d")
FD = lambda t: f"{t[4:6]}/{t[6:]}"

J = json.load(open(os.path.join(W, "nmr_krliq.json"), encoding="utf-8"))
rows, monthly, V = J["daily"], J["monthly"], J.get("verdict")
# 컬럼: 0date 1예탁금 2미수금 3반대매매 4비중 5신용전체 6신용KP 7신용KQ 8KOSPI 9KP대금 10KOSDAQ 11KQ대금
g = lambda i, scale=1.0: {r[0]: r[i] / scale for r in rows if r[i] is not None}
dep = g(1, 1e12); trd = g(9, 1e12); ks = g(8); kq = g(10)
opp = g(3, 1e8); oppr = g(4); crw = g(5, 1e12); crq = g(7, 1e12)
cra = {r[0]: (r[7] / r[5] * 100) for r in rows if r[5] and r[7]}
SUM = {"as_of": J.get("as_of"), "src": J.get("src"), "verdict": V}

# ── ① 예탁금+거래대금+코스피 / 회전배수 ──────────────────────────────
dxs, txs, kxs = sorted(dep), sorted(set(trd) & set(dep)), sorted(ks)
turn = {t: trd[t] / dep[t] for t in txs}
vtxt = (f"자동 판정: {V['label']}({V['tone']}) — 예탁금 5일 {V['dep_5d_pct']:+.1f}% · "
        f"회전배수 5일 {V['turn_5d_chg']:+.2f}p (기준 {FD(V['as_of'])})") if V else ""
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.8, 6.2), dpi=110, sharex=True,
                             gridspec_kw={"height_ratios": [3, 2]})
tall = sorted(trd)
a1.bar([D(t) for t in tall], [trd[t] for t in tall], width=1.0, color="#BFDBFE",
       label="KOSPI 거래대금(조원/일 · T+0)")
axd = a1.twinx(); axd.plot([D(t) for t in dxs], [dep[t] for t in dxs], color="#1D4ED8", lw=2.2,
                           label="투자자예탁금(조원 · T+2)")
axk = a1.twinx(); axk.spines["right"].set_position(("outward", 42))
axk.plot([D(t) for t in kxs], [ks[t] for t in kxs], color="#94A3B8", lw=1.5, label="코스피 · T+0")
ld, lk = dxs[-1], kxs[-1]
axd.annotate(f"예탁금 {dep[ld]:.1f}조 · {FD(ld)} (T+2)", xy=(D(ld), dep[ld]),
             xytext=(0.985, 0.30), textcoords="axes fraction", ha="right", fontsize=7.5,
             color="#1D4ED8", fontweight="bold", arrowprops=dict(arrowstyle="->", color="#1D4ED8", lw=.8))
axk.annotate(f"코스피 {ks[lk]:,.0f} · {FD(lk)} (T+0)", xy=(D(lk), ks[lk]),
             xytext=(0.985, 0.06), textcoords="axes fraction", ha="right", fontsize=7.5,
             color="#475569", fontweight="bold", arrowprops=dict(arrowstyle="->", color="#94A3B8", lw=.8))
a1.set_title("① 투자자예탁금 vs 거래대금 vs 코스피 — 일별 1년\n" + vtxt, fontsize=10)
h = []; l = []
for ax in (a1, axd, axk):
    hh, ll = ax.get_legend_handles_labels(); h += hh; l += ll
a1.legend(h, l, fontsize=7.5, loc="upper left"); a1.grid(alpha=.3)
a2.bar([D(t) for t in tall], [trd[t] for t in tall], width=1.0, color="#BFDBFE")
c2x = a2.twinx(); c2x.plot([D(t) for t in txs], [turn[t] for t in txs], color="#EA580C", lw=1.6,
                           label="일 회전배수 = 거래대금÷예탁금")
c2x.legend(fontsize=7.5, loc="upper left"); a2.grid(alpha=.3)
plt.tight_layout(); plt.savefig(os.path.join(W, "charts", "krliq_1.png"), bbox_inches="tight"); plt.close()
SUM["deposit_t"] = round(dep[ld], 1); SUM["turnover"] = round(turn[txs[-1]], 2)

# ── ② M2 YoY vs 코스피·코스닥 YoY ──────────────────────────────────
mi = {r[0]: r for r in monthly}
def yoy(t, i):
    p = mi.get(str(int(t) - 100))
    return (mi[t][i] / p[i] - 1) * 100 if (p and p[i] and mi[t][i]) else None
ts = [t for t in sorted(mi) if t >= "201601" and all(yoy(t, i) is not None for i in (1, 2))]
xm = [dt.datetime.strptime(t + "15", "%Y%m%d") for t in ts]
fig, ax = plt.subplots(figsize=(8.8, 3.6), dpi=110)
ax.plot(xm, [yoy(t, 1) for t in ts], color="#059669", lw=2.4, label="M2 YoY(%)")
ax2 = ax.twinx()
ax2.plot(xm, [yoy(t, 2) for t in ts], color="#DC2626", lw=1.8, label="KOSPI YoY(%, 우축)")
ax2.plot(xm, [yoy(t, 3) for t in ts], color="#F59E0B", lw=1.6, ls="--", label="KOSDAQ YoY(%, 우축)")
ax2.axhline(0, color="#DC2626", lw=.6, alpha=.35)
ax.set_title("② M2 YoY vs KOSPI·KOSDAQ YoY — 월별 10년 · M2 약 2개월 지연", fontsize=10.5)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, fontsize=7.5, loc="upper left"); ax.grid(alpha=.3)
plt.tight_layout(); plt.savefig(os.path.join(W, "charts", "krliq_2.png"), bbox_inches="tight"); plt.close()
lm = ts[-1] if ts else None
if lm:
    SUM["m2_month"] = lm; SUM["m2_yoy"] = round(yoy(lm, 1), 1)
    SUM["kospi_yoy"] = round(yoy(lm, 2), 1)
    SUM["kosdaq_yoy"] = round(yoy(lm, 3), 1) if yoy(lm, 3) is not None else None

# ── ③ 신용융자 vs 코스피 vs VKOSPI + 반대매매 ───────────────────────
vk = []
for p in (glob.glob("/sessions/*/mnt/claudeCowork/namoobi-market-report-server/data/deriv_signals.db")
          or [os.path.join("D:/claudeCowork/namoobi-market-report-server/data", "deriv_signals.db")]):
    try:
        con = sqlite3.connect(p)
        vk = [(dt.datetime.strptime(a, "%Y-%m-%d"), b, a.replace("-", ""))
              for a, b in con.execute("SELECT date,vkospi FROM kr_derivatives_daily "
                                      "WHERE id='KOSPI200' AND vkospi IS NOT NULL ORDER BY date")]
        con.close(); break
    except Exception: pass
cxs = sorted(crw)
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.8, 6.6), dpi=110, sharex=True,
                             gridspec_kw={"height_ratios": [3, 2]})
a1.plot([D(t) for t in cxs], [crw[t] for t in cxs], color="#7C3AED", lw=2.2, label="신용융자잔고(조원 · T+2)")
b1 = a1.twinx(); b1.plot([D(t) for t in kxs], [ks[t] for t in kxs], color="#94A3B8", lw=1.5, label="코스피 · T+0")
b2 = a1.twinx(); b2.spines["right"].set_position(("outward", 42))
if vk:
    x0 = D(cxs[0])
    vkc = [(x, y, d0) for x, y, d0 in vk if x >= x0]
    b2.plot([x for x, _, _ in vkc], [y for _, y, _ in vkc], color="#EA580C", lw=1.4, ls="--", label="VKOSPI · T+1")
    if vkc:
        b2.annotate(f"VKOSPI {vkc[-1][1]:.1f} · {FD(vkc[-1][2])} (T+1)", xy=(vkc[-1][0], vkc[-1][1]),
                    xytext=(0.98, 0.90), textcoords="axes fraction", ha="right", fontsize=7.5,
                    color="#EA580C", fontweight="bold", arrowprops=dict(arrowstyle="->", color="#EA580C", lw=.8))
lc = cxs[-1]
a1.annotate(f"신용융자 {crw[lc]:.1f}조 · {FD(lc)} (T+2)", xy=(D(lc), crw[lc]),
            xytext=(0.98, 0.60), textcoords="axes fraction", ha="right", fontsize=7.5,
            color="#7C3AED", fontweight="bold", arrowprops=dict(arrowstyle="->", color="#7C3AED", lw=.8))
a1.set_title("③ 신용융자 vs 코스피 vs VKOSPI + 반대매매 — 일별 1년", fontsize=10.5)
h = []; l = []
for ax in (a1, b1, b2):
    hh, ll = ax.get_legend_handles_labels(); h += hh; l += ll
a1.legend(h, l, fontsize=7.5, loc="upper left"); a1.grid(alpha=.3)
uxs = sorted(opp)
a2.bar([D(t) for t in uxs], [opp[t] for t in uxs], width=1.0, color="#FCA5A5",
       label="반대매매금액(억원/일 · T+2, 미수금 기반)")
c3x = a2.twinx(); c3x.plot([D(t) for t in uxs], [oppr.get(t) for t in uxs], color="#B91C1C", lw=1.3,
                           label="미수금 대비 반대매매 비중(%, 우축)")
lu = uxs[-1]
a2.annotate(f"{opp[lu]:,.0f}억 · 비중 {oppr.get(lu, 0):.1f}% ({FD(lu)})", xy=(D(lu), opp[lu]),
            xytext=(0.98, 0.85), textcoords="axes fraction", ha="right", fontsize=7.5,
            color="#B91C1C", fontweight="bold", arrowprops=dict(arrowstyle="->", color="#B91C1C", lw=.8))
h1, l1 = a2.get_legend_handles_labels(); h2, l2 = c3x.get_legend_handles_labels()
a2.legend(h1 + h2, l1 + l2, fontsize=7.5, loc="upper left"); a2.grid(alpha=.3)
plt.tight_layout(); plt.savefig(os.path.join(W, "charts", "krliq_3.png"), bbox_inches="tight"); plt.close()
SUM["crd_t"] = round(crw[lc], 1); SUM["opp_amt_e"] = round(opp[lu]); SUM["opp_ratio"] = oppr.get(lu)
SUM["opp_date"] = lu

# ── ④ 코스닥 신용 + 일간증감 (마진콜 조기경보) ───────────────────────
qxs = sorted(crq); kqx = sorted(kq)
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.8, 6.6), dpi=110, sharex=True,
                             gridspec_kw={"height_ratios": [3, 2]})
a1.plot([D(t) for t in qxs], [crq[t] for t in qxs], color="#7C3AED", lw=2.2, label="코스닥 신용융자잔고(조원 · T+2)")
b1 = a1.twinx(); b1.plot([D(t) for t in kqx], [kq[t] for t in kqx], color="#94A3B8", lw=1.5, label="코스닥 지수 · T+0")
b2 = a1.twinx(); b2.spines["right"].set_position(("outward", 42))
sxs = sorted(cra)
b2.plot([D(t) for t in sxs], [cra[t] for t in sxs], color="#EA580C", lw=1.4, ls="--",
        label="전체 신용잔고 중 코스닥 비중(% · T+2)")
lq = qxs[-1]
a1.annotate(f"코스닥 신용 {crq[lq]:.2f}조 · {FD(lq)} (T+2)", xy=(D(lq), crq[lq]),
            xytext=(0.98, 0.55), textcoords="axes fraction", ha="right", fontsize=7.5,
            color="#7C3AED", fontweight="bold", arrowprops=dict(arrowstyle="->", color="#7C3AED", lw=.8))
b2.annotate(f"비중 {cra[sxs[-1]]:.1f}% ({FD(sxs[-1])})", xy=(D(sxs[-1]), cra[sxs[-1]]),
            xytext=(0.98, 0.90), textcoords="axes fraction", ha="right", fontsize=7.5,
            color="#EA580C", fontweight="bold", arrowprops=dict(arrowstyle="->", color="#EA580C", lw=.8))
a1.set_title("④ 코스닥 신용융자 vs 코스닥 지수 vs 비중 + 일간 증감 — 마진콜 조기경보", fontsize=10.5)
h = []; l = []
for ax in (a1, b1, b2):
    hh, ll = ax.get_legend_handles_labels(); h += hh; l += ll
a1.legend(h, l, fontsize=7.5, loc="upper left"); a1.grid(alpha=.3)
chg = [(qxs[i], (crq[qxs[i]] - crq[qxs[i - 1]]) * 1e4) for i in range(1, len(qxs))]  # 억원
a2.bar([D(t) for t, _ in chg], [v for _, v in chg], width=1.0,
       color=["#B91C1C" if v < 0 else "#93C5FD" for _, v in chg],
       label="코스닥 신용잔고 일간 증감(억원 · T+2, 감소=적색)")
a2.axhline(0, color="#64748B", lw=.6)
mn = min(chg, key=lambda x: x[1])
a2.annotate(f"최대 감소 {mn[1]:,.0f}억 · {FD(mn[0])}", xy=(D(mn[0]), mn[1]),
            xytext=(0.02, 0.08), textcoords="axes fraction", fontsize=7.5,
            color="#B91C1C", fontweight="bold", arrowprops=dict(arrowstyle="->", color="#B91C1C", lw=.8))
a2.legend(fontsize=7.5, loc="upper left"); a2.grid(alpha=.3)
plt.tight_layout(); plt.savefig(os.path.join(W, "charts", "krliq_4.png"), bbox_inches="tight"); plt.close()
SUM["crd_kosdaq_t"] = round(crq[lq], 2); SUM["kosdaq_share"] = round(cra[sxs[-1]], 1)
SUM["kosdaq_chg5_e"] = round(sum(v for _, v in chg[-5:]))

# ── (2026-07-17) VKOSPI 1년 스파크 — 3.1.12 심리 표 추세열용 (deriv_signals.db 이력, 종전 미생성 404) ──
if vk:
    try:
        fig, ax = plt.subplots(figsize=(3.0, 0.8), dpi=100)
        ys = [y for _, y, _ in vk][-250:]
        col = "#DC2626" if ys[-1] >= ys[0] else "#059669"   # 변동성 상승=적색(위험)
        ax.plot(range(len(ys)), ys, color=col, lw=1.4)
        ax.axis("off"); fig.patch.set_alpha(0)
        plt.savefig(os.path.join(W, "charts", "spark_vkospi.png"), bbox_inches="tight",
                    pad_inches=0.02, transparent=True)
        plt.close()
    except Exception as _e:
        print("spark_vkospi skip:", _e)

json.dump(SUM, open(os.path.join(W, "nmr_krliq_summary.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("krliq charts OK:", {k: SUM[k] for k in ("as_of", "deposit_t", "crd_t", "opp_amt_e", "kosdaq_chg5_e")},
      "| verdict:", V and V["label"])
