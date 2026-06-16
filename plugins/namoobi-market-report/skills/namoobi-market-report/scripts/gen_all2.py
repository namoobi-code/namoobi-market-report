import json, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
from datetime import datetime

HERE = os.path.dirname(__file__)
O = sys.argv[1] if len(sys.argv) > 1 else "/sessions/youthful-blissful-johnson/mnt/outputs"
CH = os.path.join(HERE, "charts")
os.makedirs(CH, exist_ok=True)

fp = os.path.join(HERE, "fonts", "nmr_kr.ttf")
if os.path.exists(fp):
    font_manager.fontManager.addfont(fp)
    matplotlib.rcParams["font.family"] = font_manager.FontProperties(fname=fp).get_name()
matplotlib.rcParams["axes.unicode_minus"] = False
GRN, RED, BLU = "#059669", "#DC2626", "#2563EB"

def loadj(name):
    p = os.path.join(O, name)
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception as e:
            print("load fail", name, e)
    return None

def spark(pairs, out):
    ys = [p[1] for p in pairs if p and len(p) > 1 and p[1] is not None]
    if len(ys) < 2:
        return False
    col = GRN if ys[-1] >= ys[0] else RED
    fig, ax = plt.subplots(figsize=(1.6, 0.52), dpi=150)
    ax.plot(range(len(ys)), ys, color=col, linewidth=1.2)
    ax.fill_between(range(len(ys)), ys, min(ys), color=col, alpha=0.10)
    ax.axis("off"); ax.margins(x=0, y=0.12)
    ax.scatter([len(ys)-1], [ys[-1]], color=col, s=7, zorder=5)
    plt.tight_layout(pad=0); plt.savefig(out, bbox_inches="tight", transparent=True); plt.close()
    return True

def mini(pairs, out):
    ys = [p[1] for p in pairs if p and len(p) > 1 and p[1] is not None]
    if len(ys) < 2:
        return False
    col = GRN if ys[-1] >= ys[0] else RED
    fig, ax = plt.subplots(figsize=(2.5, 0.82), dpi=150)
    ax.plot(range(len(ys)), ys, color=col, linewidth=1.3)
    ax.fill_between(range(len(ys)), ys, min(ys), color=col, alpha=0.10)
    ax.axis("off"); ax.margins(x=0, y=0.12)
    chg = (ys[-1]/ys[0]-1)*100 if ys[0] else 0
    ax.set_title(f"{chg:+.0f}% (1Y)", fontsize=8, color=col, fontweight="bold")
    plt.tight_layout(pad=0.2); plt.savefig(out, bbox_inches="tight", transparent=True); plt.close()
    return True

def sma(vals, n):
    out = []
    for i in range(len(vals)):
        if i+1 < n:
            out.append(None)
        else:
            out.append(sum(vals[i+1-n:i+1])/n)
    return out

def candle_chart(name, ohlcv, flows, title, out):
    """ohlcv: [[date,o,h,l,c,v]...] daily ; flows: [(dt,close,cumF,cumI,cumP)...]"""
    if not ohlcv or len(ohlcv) < 20:
        print("candle skip (no ohlcv)", name); return False
    xs = [datetime.fromisoformat(str(r[0])[:10]) for r in ohlcv]
    o = [r[1] for r in ohlcv]; h = [r[2] for r in ohlcv]; l = [r[3] for r in ohlcv]
    c = [r[4] for r in ohlcv]; v = [r[5] if len(r) > 5 and r[5] else 0 for r in ohlcv]
    n = len(xs)
    fig = plt.figure(figsize=(9.2, 6.9), dpi=150)
    gs = fig.add_gridspec(3, 1, height_ratios=[3.0, 1.0, 1.4], hspace=0.12)
    ax1 = fig.add_subplot(gs[0]); ax2 = fig.add_subplot(gs[1], sharex=ax1); ax3 = fig.add_subplot(gs[2], sharex=ax1)
    # candles
    import numpy as np
    xi = np.arange(n)
    w = 0.7
    for i in range(n):
        up = c[i] >= o[i]
        col = RED if up else BLU
        ax1.plot([i, i], [l[i], h[i]], color=col, linewidth=0.6, zorder=2)
        ax1.add_patch(plt.Rectangle((i-w/2, min(o[i], c[i])), w, max(abs(c[i]-o[i]), (h[i]-l[i])*0.001), color=col, zorder=3))
    for win, cl in [(5, "#F59E0B"), (20, "#16A34A"), (60, "#9333EA"), (120, "#6B7280")]:
        ma = sma(c, win)
        ax1.plot(xi, ma, color=cl, linewidth=1.0, label=f"MA{win}")
    ax1.set_title(title, fontsize=13, color="#1E3A8A", fontweight="bold")
    ax1.legend(fontsize=8, ncol=4, loc="upper left", frameon=False)
    ax1.grid(True, alpha=0.2); ax1.margins(x=0.005)
    ax1.set_ylabel("지수", fontsize=9, color="#475569")
    for s in ["top", "right"]:
        ax1.spines[s].set_visible(False)
    # volume
    ax2.bar(xi, v, color=["#FCA5A5" if c[i] >= o[i] else "#BFDBFE" for i in range(n)], width=0.8)
    ax2.set_ylabel("거래량", fontsize=9, color="#475569"); ax2.grid(True, alpha=0.15)
    for s in ["top", "right"]:
        ax2.spines[s].set_visible(False)
    ax2.tick_params(labelsize=7)
    # cumulative flows (re-indexed onto trading-day axis by date)
    if flows:
        fxd = [f[0] for f in flows]
        # map flow dates to nearest candle index
        def idx_of(d):
            best, bd = 0, 1e18
            for k, x in enumerate(xs):
                dd = abs((x - d).days)
                if dd < bd:
                    bd, best = dd, k
            return best
        fi = [idx_of(d) for d in fxd]
        ax3.plot(fi, [f[2] for f in flows], color=RED, linewidth=1.4, label="외국인")
        ax3.plot(fi, [f[3] for f in flows], color=BLU, linewidth=1.4, label="기관")
        ax3.plot(fi, [f[4] for f in flows], color=GRN, linewidth=1.4, label="개인")
        ax3.axhline(0, color="#94A3B8", linewidth=0.7)
        ax3.legend(fontsize=8, ncol=3, loc="upper left", frameon=False)
        ax3.set_ylabel("누적순매수(조)", fontsize=9, color="#475569")
    ax3.grid(True, alpha=0.15)
    for s in ["top", "right"]:
        ax3.spines[s].set_visible(False)
    # x ticks as dates
    step = max(1, n//10)
    ax3.set_xticks(list(xi[::step]))
    ax3.set_xticklabels([xs[i].strftime("%y/%m") for i in xi[::step]], fontsize=7)
    plt.setp(ax1.get_xticklabels(), visible=False); plt.setp(ax2.get_xticklabels(), visible=False)
    plt.savefig(out, bbox_inches="tight"); plt.close()
    print("candle saved", out); return True

# ---- KOSPI/KOSDAQ candles ----
kt = loadj("nmr_korea_tech.json") or {}
ohlcv = (kt.get("kr_ohlcv") or {})
# flows from kr_flows.txt (downsampled cumulative, 조)
def load_flows(market):
    p = os.path.join(O, "kr_flows.txt")
    if not os.path.exists(p):
        return None
    blocks = {}; cur = None
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        if "|" not in line:
            cur = line; blocks[cur] = []; continue
        a = line.split("|")
        blocks[cur].append((datetime.strptime("20"+a[0], "%Y-%m-%d"), float(a[1]), float(a[2]), float(a[3]), float(a[4])))
    return blocks.get(market)
candle_chart("kospi", ohlcv.get("kospi"), load_flows("KOSPI"), "코스피 일봉 캔들·이동평균 / 거래량 / 투자자별 누적순매수 (1년)", os.path.join(CH, "kospi_candle.png"))
candle_chart("kosdaq", ohlcv.get("kosdaq"), load_flows("KOSDAQ"), "코스닥 일봉 캔들·이동평균 / 거래량 / 투자자별 누적순매수 (1년)", os.path.join(CH, "kosdaq_candle.png"))

# ---- commodity + strategic sparklines ----
cm = loadj("nmr_commod.json") or {}
ser = cm.get("series") or {}
nc = 0
for k, v in ser.items():
    if spark(v, os.path.join(CH, f"spark_{k}.png")):
        nc += 1
print("commodity/strat sparklines:", nc)

# ---- theme charts ----
semi = loadj("nmr_semi.json") or {}
ts = semi.get("theme_series") or {}
nt = 0
for t, s in ts.items():
    t2 = t.replace("/", "_").replace(" ", "_")
    if mini(s, os.path.join(CH, f"theme_{t2}.png")):
        nt += 1
print("theme charts:", nt)

# ---- semi stock/etf mini charts (by array order) ----
def order_charts(items, series_map, prefix):
    cnt = 0
    for i, it in enumerate(items or []):
        nm = it.get("name") if isinstance(it, dict) else None
        s = series_map.get(nm) if nm else None
        if s and mini(s, os.path.join(CH, f"{prefix}_{i}.png")):
            cnt += 1
    return cnt
ns = order_charts(semi.get("semi_ai_stocks"), semi.get("stock_series") or {}, "semi_s")
ne = order_charts(semi.get("semi_ai_etfs"), semi.get("etf_series") or {}, "semi_e")
print("semi stock charts:", ns, "etf charts:", ne)

# ---- fx extra (usd_jpy, usd_cny) ----
tt = loadj("nmr_trendtext.json") or {}
fxs = tt.get("fx_series") or {}
nf = 0
for k, v in fxs.items():
    if spark(v, os.path.join(CH, f"spark_{k}.png")):
        nf += 1
print("fx extra sparklines:", nf)
print("DONE total png:", len([f for f in os.listdir(CH) if f.endswith('.png')]))
