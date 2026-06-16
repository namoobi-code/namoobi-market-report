import matplotlib, sys, os
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
from datetime import datetime

# Korean font
fp = os.path.join(os.path.dirname(__file__), "fonts", "nmr_kr.ttf")
if os.path.exists(fp):
    font_manager.fontManager.addfont(fp)
    matplotlib.rcParams["font.family"] = font_manager.FontProperties(fname=fp).get_name()
matplotlib.rcParams["axes.unicode_minus"] = False

src = sys.argv[1]  # kr_flows.txt
outdir = sys.argv[2]  # charts dir
blocks = {}
cur = None
for line in open(src, encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    if "|" not in line:
        cur = line
        blocks[cur] = []
        continue
    p = line.split("|")
    blocks[cur].append((datetime.strptime("20"+p[0], "%Y-%m-%d"), float(p[1]), float(p[2]), float(p[3]), float(p[4])))

def draw(name, rows, title, outpath):
    xs = [r[0] for r in rows]
    close = [r[1] for r in rows]
    f = [r[2] for r in rows]
    i = [r[3] for r in rows]
    p = [r[4] for r in rows]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.0, 4.4), dpi=150, sharex=True,
                                   gridspec_kw={"height_ratios": [1.3, 1.0]})
    ax1.plot(xs, close, color="#0F172A", linewidth=1.8)
    ax1.fill_between(xs, close, min(close), color="#1E40AF", alpha=0.06)
    ax1.set_title(title, fontsize=11, color="#1E3A8A", fontweight="bold")
    ax1.scatter([xs[-1]], [close[-1]], color="#DC2626", s=24, zorder=5)
    ax1.annotate(f"{close[-1]:,.0f}", (xs[-1], close[-1]), textcoords="offset points",
                 xytext=(-38, 4), color="#DC2626", fontsize=9, fontweight="bold")
    ax1.set_ylabel("지수", fontsize=8, color="#64748B")
    ax1.grid(True, alpha=0.22)
    ax2.plot(xs, f, color="#DC2626", linewidth=1.5, label="외국인")
    ax2.plot(xs, i, color="#2563EB", linewidth=1.5, label="기관")
    ax2.plot(xs, p, color="#059669", linewidth=1.5, label="개인")
    ax2.axhline(0, color="#94A3B8", linewidth=0.7)
    ax2.set_ylabel("누적순매수(조원)", fontsize=8, color="#64748B")
    ax2.legend(fontsize=8, ncol=3, loc="upper left", frameon=False)
    ax2.grid(True, alpha=0.22)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m"))
    for ax in (ax1, ax2):
        for s in ["top", "right"]:
            ax.spines[s].set_visible(False)
    plt.tight_layout()
    plt.savefig(outpath, bbox_inches="tight")
    plt.close()
    print("saved", outpath)

draw("kospi", blocks["KOSPI"], "코스피 지수 & 투자자별 누적순매수 (최근 1년)", os.path.join(outdir, "kospi_flows.png"))
draw("kosdaq", blocks["KOSDAQ"], "코스닥 지수 & 투자자별 누적순매수 (최근 1년)", os.path.join(outdir, "kosdaq_flows.png"))
