"""Render reports/Phase_A1_Report.pdf from the tables in reports/ and the cached panels.

    python -m reports.make_pdf
"""
from __future__ import annotations

import json
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import letter  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import inch  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,  # noqa: E402
                                Spacer, Table, TableStyle)

from common.paths import CACHE, REPORTS  # noqa: E402

FIG = REPORTS / "pdf_figs"
OUT = REPORTS / "Phase_A1_Report.pdf"

# palette (reference data-viz palette, light mode)
BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
INK, MUTED, GRID, RULE = "#0b0b0b", "#52514e", "#ecebe6", "#d6d5d0"
BLUE_L, BLUE_M = "#a9c9f0", "#6aa3e6"
GOOD, WARN, BAD = "#1f7a3d", "#a86400", "#b3261e"

# ----------------------------------------------------------------------------- fonts
FONT_DIR = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("DV", FONT_DIR + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DV-B", FONT_DIR + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV", boldItalic="DV-B")
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "axes.titlesize": 10.5,
                     "axes.titleweight": "bold", "axes.labelcolor": MUTED, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.edgecolor": RULE, "legend.frameon": False})


def _style(ax, ygrid=True):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0, labelsize=8.5)
    if ygrid:
        ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _save(fig, name):
    FIG.mkdir(exist_ok=True)
    p = FIG / f"{name}.png"
    fig.savefig(p, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return p


# ----------------------------------------------------------------------------- data
def load():
    R = {}
    R["summary"] = json.loads((REPORTS / "summary.json").read_text())
    for k in ("t1_deciles_absFR", "t1c_fixed_thresholds", "t2_double_sort", "t3_regressions",
              "t4b_matched_by_year", "t5_splits_top_decile", "t6_pnl_performance", "t6b_pnl_by_year",
              "t7_concentration", "t9_index_secondary_check", "asset_validation"):
        R[k] = pd.read_csv(REPORTS / f"{k}.csv")
    tr = pd.read_csv(REPORTS / "t8_sim_trades_gross.csv", parse_dates=["date"])
    tr["hedge"] = 0.5 * tr["beta_pick"].abs().fillna(1)
    R["trades"] = tr
    fd = pd.read_parquet(CACHE / "fund_days.parquet", columns=["date", "A_prev", "L", "underlying"])
    fd["G"] = fd["A_prev"] * fd["L"] * (fd["L"] - 1)
    R["gamma"] = fd.groupby("date")["G"].sum()
    R["assets"] = fd.groupby("date")["A_prev"].sum()
    R["universe"] = pd.read_csv("universe/single_stock_universe.csv")
    return R


def daily_pnl(tr: pd.DataFrame, fixed: float | None, all_dates) -> pd.Series:
    pnl = tr["gross_pnl"].copy()
    if fixed is not None:
        pnl = pnl - tr["size"] * (tr["half_spread_bps"] + fixed + tr["hedge"]) / 1e4
    return pnl.groupby(tr["date"]).sum().reindex(all_dates, fill_value=0.0)


# ----------------------------------------------------------------------------- charts
def chart_cum_pnl(R):
    tr = R["trades"]
    dates = pd.bdate_range(tr["date"].min(), tr["date"].max())
    fig, ax = plt.subplots(figsize=(7.2, 2.9))
    ax.axvspan(pd.Timestamp("2026-01-01"), dates[-1], color="#eef4fc", zorder=0)
    ax.text(pd.Timestamp("2026-01-15"), 0.02, "2026", transform=ax.get_xaxis_transform(), color=BLUE,
            fontsize=8.5, fontweight="bold")
    series = [("Gross", None, GRAY), ("Net: half-spread + 2 bps", 2.0, BLUE), ("Net: half-spread + 5 bps", 5.0, ORANGE)]
    for lab, fx, c in series:
        cum = daily_pnl(tr, fx, dates).cumsum() / 1e6
        ax.plot(cum.index, cum, color=c, linewidth=2, label=lab)
        ax.annotate(f"{cum.iloc[-1]:+.2f}", (cum.index[-1], cum.iloc[-1]), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=8, color=INK)
    ax.axhline(0, color=INK, linewidth=0.7)
    ax.set_ylabel("Cumulative P&L, $M")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.legend(loc="upper left", fontsize=8.5)
    _style(ax)
    return _save(fig, "cum_pnl")


def chart_deciles(R):
    d = R["t1_deciles_absFR"]
    se = d["on_xs_bps"] / d["on_xs_t"]
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    cols = [BLUE if v > 0 else GRAY for v in d["on_xs_bps"]]
    ax.bar(d["decile"], d["on_xs_bps"], width=0.66, color=cols, zorder=2)
    ax.errorbar(d["decile"], d["on_xs_bps"], yerr=1.96 * se, fmt="none", ecolor=MUTED, elinewidth=1, capsize=3,
                zorder=3)
    ax.axhline(0, color=INK, linewidth=0.7)
    ax.axhspan(10, 20, color="#fdf0e9", zorder=0)
    ax.text(0.6, 15, "continue bar: 10–20 bps", fontsize=7.5, color=ORANGE, va="center")
    ax.set_xticks(d["decile"])
    ax.set_xticklabels([f"D{i}\n{m:.3f}" for i, m in zip(d["decile"], d["absFR_median"])], fontsize=7.5)
    ax.set_xlabel("Decile of |FlowRatio|  (median |FlowRatio| below each label)")
    ax.set_ylabel("Signed reversal, bps")
    _style(ax)
    return _save(fig, "deciles")


def chart_double_sort(R):
    ds = R["t2_double_sort"]
    groups = [("no lev ETF", GRAY), ("Gamma low", BLUE_L), ("Gamma mid", BLUE_M), ("Gamma high", BLUE)]
    qs = sorted(ds["abs_r_quintile"].unique())
    fig, ax = plt.subplots(figsize=(7.2, 2.9))
    w = 0.2
    for i, (g, c) in enumerate(groups):
        sub = ds[ds["group"] == g].set_index("abs_r_quintile").reindex(qs)
        ax.bar(np.arange(len(qs)) + (i - 1.5) * w, sub["on_xs_bps"], width=w * 0.88, color=c, label=g, zorder=2)
    ax.axhline(0, color=INK, linewidth=0.7)
    ax.set_xticks(np.arange(len(qs)))
    ax.set_xticklabels([f"{q.replace('|r| ', '')}\n(smallest moves)" if q.endswith("Q1") else
                        f"{q.replace('|r| ', '')}\n(largest moves)" if q.endswith("Q5") else q.replace("|r| ", "")
                        for q in qs], fontsize=8)
    ax.set_xlabel("Quintile of same-day |return|")
    ax.set_ylabel("Signed reversal, bps")
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.28), fontsize=8.5)
    _style(ax)
    return _save(fig, "double_sort")


def chart_forest(R):
    reg = R["t3_regressions"]
    f = reg[reg["var"] == "FR_w"].iloc[::-1]
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    y = np.arange(len(f))
    ax.errorbar(f["coef"], y, xerr=1.96 * f["se"], fmt="o", color=BLUE, ecolor=BLUE_M, elinewidth=2, capsize=0,
                markersize=6)
    ax.axvline(0, color=INK, linewidth=0.7)
    ax.set_yticks(y)
    names = {"A": "All stocks, date FE", "B": "+ own reversal slope for lev-ETF stocks",
             "C": "+ stock FE, 2-way clustered", "D": "Lev-ETF stocks only", "E": "Lev-ETF stocks only, + stock FE",
             "F": "Raw return (no beta hedge)", "G": "Close-to-close outcome"}
    ax.set_yticklabels([f"{k[0]}. {names[k[0]]}" for k in f["spec"]], fontsize=8)
    for yi, (c, t) in enumerate(zip(f["coef"], f["t"])):
        ax.text(25, yi, f"t = {t:.2f}".replace("-", "−"), va="center", fontsize=8, color=MUTED)
    ax.set_xlim(-220, 60)
    ax.set_xlabel("FlowRatio coefficient, bps of next-day return per 1.0 FlowRatio  (95% CI)")
    ax.xaxis.grid(True, color=GRID)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    return _save(fig, "forest")


def chart_placebo_year(R):
    m = R["t4b_matched_by_year"]
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    x = np.arange(len(m))
    ax.bar(x - 0.2, m["rev_treated"], width=0.38, color=BLUE, label="Top-decile lev-ETF stock", zorder=2)
    ax.bar(x + 0.2, m["rev_match"], width=0.38, color=GRAY, label="Matched stock, no lev ETF", zorder=2)
    for xi, (d, t, n) in enumerate(zip(m["diff"], m["diff_t"], m["n"])):
        ax.text(xi, 30, f"gap {d:+.1f} bps (t={t:.1f})\nn={n:,}", ha="center", fontsize=7.5, color=INK,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=RULE))
    ax.axhline(0, color=INK, linewidth=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(m["year"].astype(str))
    ax.set_ylim(min(m[["rev_treated", "rev_match"]].min().min() - 5, -30), 45)
    ax.set_ylabel("Signed overnight reversal, bps")
    ax.legend(loc="lower right", fontsize=8.5)
    _style(ax)
    return _save(fig, "placebo_year")


def chart_pnl_year(R):
    y = R["t6b_pnl_by_year"].set_index("date")
    fig, ax = plt.subplots(figsize=(7.2, 2.2))
    x = np.arange(len(y))
    ax.bar(x - 0.2, y["gross"], width=0.38, color=GRAY, label="Gross", zorder=2)
    ax.bar(x + 0.2, y["net: half-spread + 2bps"], width=0.38, color=BLUE, label="Net (half-spread + 2 bps)", zorder=2)
    for xi, v in enumerate(y["net: half-spread + 2bps"]):
        ax.text(xi + 0.2, v + (0.06 if v >= 0 else -0.06), f"{v:+.2f}", ha="center",
                va="bottom" if v >= 0 else "top", fontsize=7.5)
    ax.axhline(0, color=INK, linewidth=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels([str(i) + (" YTD" if i == 2026 else "") for i in y.index])
    lo = min(y["gross"].min(), y["net: half-spread + 2bps"].min())
    ax.set_ylim(lo - 0.35, None)
    ax.set_ylabel("P&L, $M")
    ax.legend(loc="upper left", fontsize=8.5)
    _style(ax)
    return _save(fig, "pnl_year")


def chart_gamma(R):
    g = R["gamma"].resample("W").mean() / 1e9
    a = R["assets"].resample("W").mean() / 1e9
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
    for ax, s, c, lab in ((axes[0], a, BLUE, "Fund net assets, $B"),
                          (axes[1], g / 100, ORANGE, "Rebalance flow per 1% move, $B")):
        ax.plot(s.index, s, color=c, linewidth=2)
        ax.fill_between(s.index, s, color=c, alpha=0.08)
        ax.set_title(lab, loc="left", fontsize=9.5)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        _style(ax)
    fig.tight_layout(w_pad=3)
    return _save(fig, "gamma")


def chart_asset_validation(R):
    v = R["asset_validation"]
    h = v[(v["check"] == "quarter_holdout") & (v["actual"] > 5e6)]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
    for ax, col, c, lab in ((axes[0], "pred", BLUE, "With N-PORT monthly flows"),
                            (axes[1], "pred_no_flow", GRAY, "Ignoring creations/redemptions")):
        ax.scatter(h["actual"] / 1e6, h[col] / 1e6, s=7, color=c, alpha=0.5, edgecolors="none")
        lim = (3, h["actual"].max() / 1e6 * 1.5)
        ax.plot(lim, lim, color=INK, linewidth=0.7)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(lim)
        ax.set_ylim(lim)
        err = np.log(h[col] / h["actual"]).abs().median()
        ax.set_title(f"{lab}\nmedian error {err:.1%}", loc="left", fontsize=9)
        ax.set_xlabel("Actual quarter-end assets, $M")
        _style(ax, ygrid=False)
    axes[0].set_ylabel("Predicted, $M")
    fig.tight_layout(w_pad=3)
    return _save(fig, "asset_validation")


# ----------------------------------------------------------------------------- pdf helpers
S = {
    "title": ParagraphStyle("title", fontName="DV-B", fontSize=22, leading=27, textColor=colors.HexColor(INK)),
    "subtitle": ParagraphStyle("subtitle", fontName="DV", fontSize=11, leading=15, textColor=colors.HexColor(MUTED)),
    "h1": ParagraphStyle("h1", fontName="DV-B", fontSize=15, leading=19, spaceBefore=4, spaceAfter=6,
                         textColor=colors.HexColor(INK)),
    "h2": ParagraphStyle("h2", fontName="DV-B", fontSize=11.5, leading=15, spaceBefore=8, spaceAfter=4,
                         textColor=colors.HexColor(INK)),
    "body": ParagraphStyle("body", fontName="DV", fontSize=9.4, leading=13.6, spaceAfter=6,
                           textColor=colors.HexColor("#222222")),
    "bullet": ParagraphStyle("bullet", fontName="DV", fontSize=9.4, leading=13.4, leftIndent=12, bulletIndent=2,
                             spaceAfter=3, textColor=colors.HexColor("#222222")),
    "caption": ParagraphStyle("caption", fontName="DV", fontSize=8.2, leading=11, spaceAfter=10,
                              textColor=colors.HexColor(MUTED)),
    "cell": ParagraphStyle("cell", fontName="DV", fontSize=8.3, leading=10.8),
    "cellb": ParagraphStyle("cellb", fontName="DV-B", fontSize=8.3, leading=10.8),
    "cellr": ParagraphStyle("cellr", fontName="DV", fontSize=8.3, leading=10.8, alignment=2),
    "cellbr": ParagraphStyle("cellbr", fontName="DV-B", fontSize=8.3, leading=10.8, alignment=2),
    "kpi_v": ParagraphStyle("kpi_v", fontName="DV-B", fontSize=19, leading=23, alignment=TA_CENTER,
                            textColor=colors.HexColor(INK)),
    "kpi_l": ParagraphStyle("kpi_l", fontName="DV", fontSize=7.8, leading=10, alignment=TA_CENTER,
                            textColor=colors.HexColor(MUTED)),
    "callout": ParagraphStyle("callout", fontName="DV", fontSize=9.6, leading=14, textColor=colors.HexColor(INK),
                              alignment=TA_LEFT),
}
W = letter[0] - 1.5 * inch


def _fmt(text: str) -> str:
    text = re.sub(r"&(?!amp;|lt;|gt;|#)", "&amp;", str(text))
    text = text.replace("$+", "+$").replace("$-", "−$")
    return re.sub(r"(?<![A-Za-z0-9/_.])-(?=\d|\$)", "−", text)


def P(text, style="body"):
    return Paragraph(_fmt(text), S[style])


def bullets(items):
    return [Paragraph(_fmt(t), S["bullet"], bulletText="•") for t in items]


def fig(path, caption=None, width=W):
    img = Image(str(path))
    img.drawWidth, img.drawHeight = width, width * img.imageHeight / img.imageWidth
    parts = [img]
    if caption:
        parts.append(P(caption, "caption"))
    return KeepTogether(parts)


_NUM = re.compile(r"^[\s+\-−$(]*[\d.,]+[%MBk]?( bps)?(\s*\([^)]*\))?$")


def table(rows, widths, header=True, zebra=True, status_col=None):
    numeric_cols = {j for j in range(len(rows[0]))
                    if all(_NUM.match(str(r[j]).strip()) for r in rows[1:] if str(r[j]).strip())}
    data = []
    for i, r in enumerate(rows):
        line = []
        for j, c in enumerate(r):
            right = j in numeric_cols
            if header and i == 0:
                st_name = "cellbr" if right else "cellb"
            else:
                st_name = "cellr" if right else "cell"
            if status_col is not None and i > 0 and j == status_col:
                txt = str(c).upper()
                col = GOOD if txt.startswith("PASS") else WARN if txt.startswith("MARGINAL") else BAD
                line.append(Paragraph(f"<b>{c}</b>", ParagraphStyle("st", parent=S["cell"],
                                                                     textColor=colors.HexColor(col))))
            else:
                line.append(Paragraph(_fmt(c), S[st_name]))
        data.append(line)
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
          ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
          ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor(INK)),
          ("LINEBELOW", (0, -1), (-1, -1), 0.6, colors.HexColor(RULE))]
    if zebra:
        for r in range(1, len(rows)):
            if r % 2 == 0:
                st.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#f6f6f3")))
    t.setStyle(TableStyle(st))
    return t


def kpis(items):
    cells = [[P(v, "kpi_v") for v, _ in items], [P(lab, "kpi_l") for _, lab in items]]
    t = Table(cells, colWidths=[W / len(items)] * len(items))
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f7fc")),
                           ("LINEAFTER", (0, 0), (-2, -1), 2, colors.white),
                           ("TOPPADDING", (0, 0), (-1, 0), 9), ("BOTTOMPADDING", (0, -1), (-1, -1), 9),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    return t


def callout(text, color=BLUE, bg="#f4f7fc"):
    t = Table([[P(text, "callout")]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)),
                           ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor(color)),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return t


def on_page(canv, doc):
    canv.saveState()
    canv.setFont("DV", 7.5)
    canv.setFillColor(colors.HexColor(MUTED))
    canv.drawString(0.75 * inch, 0.5 * inch, "Phase A1 · Leveraged-ETF rebalancing reversal · free-data test")
    canv.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch, f"{doc.page}")
    canv.setStrokeColor(colors.HexColor(RULE))
    canv.line(0.75 * inch, 0.62 * inch, letter[0] - 0.75 * inch, 0.62 * inch)
    canv.restoreState()


def on_first(canv, doc):
    canv.saveState()
    canv.setFillColor(colors.HexColor(BLUE))
    canv.rect(0, letter[1] - 0.22 * inch, letter[0], 0.22 * inch, stroke=0, fill=1)
    canv.restoreState()
    on_page(canv, doc)


# ----------------------------------------------------------------------------- build
def f1(x):
    return f"{x:+.1f}"


def build():
    R = load()
    s = R["summary"]
    dec = R["t1_deciles_absFR"]
    top = dec.iloc[-1]
    mp = s["matched_placebo"]
    reg = R["t3_regressions"]
    fr = reg[reg["var"] == "FR_w"].set_index("spec")
    perf = R["t6_pnl_performance"].set_index("Unnamed: 0")
    conc = R["t7_concentration"].set_index("Unnamed: 0")
    mpy = R["t4b_matched_by_year"].set_index("year")
    uni = R["universe"]
    inc = uni[uni["include"]]
    spl = R["t5_splits_top_decile"]
    val = R["asset_validation"]
    ho = val[(val["check"] == "quarter_holdout") & (val["actual"] > 5e6)]
    ho_err = np.log(ho["pred"] / ho["actual"]).abs().median()
    ho_err_nf = np.log(ho["pred_no_flow"] / ho["actual"]).abs().median()
    net2 = perf.loc["net: half-spread + 2bps"]
    gross = perf.loc["gross"]
    specA = fr.loc["A: on_xs ~ FR (all stocks, date FE)"]
    specB = fr.loc["B: A + r*treated"]
    specD = fr.loc["D: treated only, date FE"]
    y26 = spl[(spl["split"] == "year") & (spl["value"] == "2026")].iloc[0]
    gam = R["gamma"]
    g_by_year = gam.groupby(gam.index.year).mean() / 1e9

    charts = {k: fn(R) for k, fn in [("cum", chart_cum_pnl), ("dec", chart_deciles), ("ds", chart_double_sort),
                                      ("forest", chart_forest), ("py", chart_placebo_year), ("pnly", chart_pnl_year),
                                      ("gamma", chart_gamma), ("aval", chart_asset_validation)]}

    story = []
    # ---------------- page 1: executive summary
    story += [Spacer(1, 6), P("Leveraged-ETF Rebalancing Reversal", "title"),
              P("Phase A1 results: a test of the hypothesis on free data (SEC EDGAR + Yahoo), "
                "July 2022 to September 2026", "subtitle"), Spacer(1, 14)]
    story.append(kpis([(f"{top['on_xs_bps']:+.1f} bps", "Top-decile overnight reversal<br/>(beta-adjusted, before costs)"),
                       (f"t = {top['on_xs_t']:.2f}", "Date-clustered t-stat<br/>for that mean"),
                       (f"{net2['sharpe']:+.2f}", "Net Sharpe of simulated<br/>strategy (half-spread + 2 bps)"),
                       (f"{conc.loc['gross', 'top10_days_share']:.0%}", "Share of gross P&L from<br/>the 10 best days")]))
    story.append(Spacer(1, 14))
    story.append(callout(
        "<b>Recommendation: stop. Don't pay for data.</b> Leveraged-ETF rebalancing flow shows at most a small, "
        "fragile overnight reversal in single stocks. It falls short of the 10–20 bps bar, it isn't clearly "
        "separate from ordinary short-term reversal, and its P&L depends on a handful of days and names. "
        "The one reason for caution is that the effect appears only in 2026, the year leveraged-ETF flow "
        "peaked. That is worth watching cheaply, not funding."))
    story.append(Spacer(1, 12))
    story.append(P("Scorecard against the continue/kill criteria", "h2"))
    story.append(table([
        ["Criterion (from the handoff)", "What the data show", "Result"],
        ["Top bucket ≥ 10–20 bps beta-adjusted reversal before costs",
         f"Top decile of |FlowRatio|: {f1(top['on_xs_bps'])} bps overnight (t = {top['on_xs_t']:.2f}; "
         f"{top['on_xs_t_2way(date,stock)']:.2f} clustered by date and stock)", "FAIL"],
        ["Significant beyond generic short-term reversal",
         f"Flow coefficient t = {specA['t']:.2f} with date fixed effects, but t = {specB['t']:.2f} once "
         f"lev-ETF stocks may reverse differently; matched-placebo gap {f1(mp['diff']['mean'])} bps "
         f"(t = {mp['diff']['t']:.2f})", "MARGINAL"],
        ["Not concentrated in a few days or names",
         f"Gross P&L is negative without the 10 best days ({conc.loc['gross', 'top10_days_share']:.0%} share) "
         f"and without the top 5 names ({conc.loc['gross', 'top5_names_share']:.0%}): "
         f"{conc.loc['gross', 'top5_names'].split(' (')[0]}, …", "FAIL"],
        ["Present in the most recent year",
         f"2026: {f1(y26['on_xs_bps'])} bps (t = {y26['t']:.2f}); {f1(mpy.loc[2026, 'diff'])} bps vs matched "
         f"stocks (t = {mpy.loc[2026, 'diff_t']:.2f})", "PASS"],
    ], [1.9 * inch, 3.95 * inch, 1.15 * inch], status_col=2))
    story.append(Spacer(1, 10))
    story.append(P("What was tested", "h2"))
    story += bullets([
        f"<b>Universe:</b> {len(inc)} daily-reset single-stock leveraged/inverse ETFs on {inc['underlying'].nunique()} "
        f"US-listed stocks, including <b>{int((inc['status'] == 'closed').sum())} funds that have since closed</b>. "
        f"The source is SEC fund registrations 2022–2026, with each fund's underlying checked against the swaps "
        f"it reports to the SEC.",
        "<b>Flow:</b> each fund's required rebalance trade, T = A·L·(L−1)·r, summed per stock and divided by an "
        "estimate of closing-auction size (10% of 20-day average dollar volume) to give <b>FlowRatio</b>.",
        "<b>Outcome:</b> close-to-next-open return, beta-hedged, signed against the flow. Positive means the "
        "price reverted, which is what the trade would earn.",
        f"<b>Sample:</b> {s['notes']['treated_rows']:,} stock-days with leveraged ETFs, plus "
        f"{s['notes']['rows_final'] - s['notes']['treated_rows']:,} stock-days of S&P 1500 stocks as the "
        f"comparison group. Earnings days are excluded.",
    ])
    story.append(PageBreak())

    # ---------------- page 2: the P&L story
    story.append(P("1. The trade would have lost money for three years, then made it back in 2026", "h1"))
    story.append(P(
        "The simulation fades the flow each day in the stocks whose |FlowRatio| is in the top 10% of the "
        "trailing year, so there is no look-ahead in the cutoff. Rules: enter at the close, beta-hedge, exit at "
        "the next open. Size is 10% of predicted flow, capped at $500k per name and $5M gross."))
    story.append(fig(charts["cum"], "Figure 1. Cumulative P&L on $5M of capital. Shaded: 2026. Costs are "
                                    "an assumed half-spread by liquidity bucket (1–20 bps) plus 2 or 5 bps, plus "
                                    "0.5 bp for the hedge."))
    story.append(table([
        ["", "Annual return", "Volatility", "Sharpe", "Max drawdown", "Total P&L"],
        *[[lab, f"{perf.loc[k, 'ann_return_pct']:+.1f}%", f"{perf.loc[k, 'ann_vol_pct']:.1f}%",
           f"{perf.loc[k, 'sharpe']:+.2f}", f"{perf.loc[k, 'max_drawdown_pct']:.0f}%",
           f"${perf.loc[k, 'total_pnl_musd']:+.2f}M"]
          for lab, k in [("Gross", "gross"), ("Net: half-spread + 2 bps", "net: half-spread + 2bps"),
                         ("Net: half-spread + 5 bps", "net: half-spread + 5bps"),
                         ("Net: full spread + 5 bps", "net: full spread + 5bps (harsh)")]]],
        [1.9 * inch] + [1.02 * inch] * 5))
    story.append(Spacer(1, 8))
    story.append(P(
        f"The size-weighted gross edge is <b>{s['trade_stats']['avg_gross_bps_per_trade_sizeweighted']:.1f} bps "
        f"per trade</b>, against about {s['trade_stats']['avg_cost_bps_halfspread+2']:.1f} bps of assumed cost. "
        f"Average capital deployed was only ${gross['avg_deployed_musd']:.1f}M of the $5M."))
    story.append(fig(charts["pnly"], "Figure 2. P&L by calendar year, $M. All of the positive P&L comes from "
                                     "late 2025 and 2026."))
    story.append(PageBreak())

    # ---------------- page 3: sorts
    story.append(P("2. Only the very largest flows reverse, and not by much", "h1"))
    story.append(P(
        "If rebalancing flow pushes the close away from fair value, reversal should rise steadily with flow "
        "size. It doesn't. Deciles 4–9 drift slightly <i>with</i> the flow, and only the top decile reverses. "
        f"Even there the average is {f1(top['on_xs_bps'])} bps with a 95% interval that includes zero."))
    story.append(fig(charts["dec"], "Figure 3. Overnight beta-adjusted signed reversal by decile of |FlowRatio| "
                                    "among stock-days with leveraged ETFs. Bars: mean, bps. Whiskers: 95% CI "
                                    "clustered by date. Shaded band: the 10–20 bps threshold."))
    rows = [["Decile", "Median |FlowRatio|", "Median flow", "Overnight, bps (t)", "Close→close, bps (t)",
             "Hit rate", "Stocks"]]
    for _, r in dec.iterrows():
        rows.append([f"D{int(r['decile'])}", f"{r['absFR_median']:.3f}", f"${r['flow_musd_median']:.1f}M",
                     f"{r['on_xs_bps']:+.1f} ({r['on_xs_t']:.1f})", f"{r['cc_xs_bps']:+.1f} ({r['cc_xs_t']:.1f})",
                     f"{r['on_xs_hit']:.0%}", f"{int(r['n_stocks'])}"])
    story.append(table(rows, [0.6 * inch, 1.15 * inch, 0.95 * inch, 1.25 * inch, 1.3 * inch, 0.8 * inch,
                              0.95 * inch]))
    fb = R["t1c_fixed_thresholds"]
    b = fb[fb["absFR_bin"] == "[0.3, 1.0)"].iloc[0]
    story.append(Spacer(1, 8))
    story.append(P(
        f"Using fixed thresholds instead of deciles, flow between 30% and 100% of the auction proxy shows "
        f"{f1(b['on_xs_bps'])} bps (t = {b['t']:.2f}, {int(b['n']):,} stock-days, {int(b['n_stocks'])} stocks). "
        "Flow above 100% turns negative again. This is one of six bins tested, so treat it as a nominal result "
        "rather than a finding."))
    story.append(PageBreak())

    # ---------------- page 4: control
    story.append(P("3. Most of it looks like ordinary short-term reversal", "h1"))
    story.append(P(
        "Stocks with big daily moves tend to give some back overnight whether or not leveraged ETFs trade them. "
        "Two tests ask whether leveraged-ETF flow adds anything on top of that."))
    story.append(P("Same-size moves, with and without leveraged ETFs", "h2"))
    story.append(fig(charts["ds"], "Figure 4. Within each quintile of same-day |return|: S&P 1500 stocks with "
                                   "no leveraged ETF (gray) vs leveraged-ETF stocks split into terciles of "
                                   "Gamma relative to liquidity (blue). More Gamma does not bring more reversal."))
    story.append(P("Regression with controls for the size of the move", "h2"))
    story.append(P(
        "Next-day overnight return regressed on the day's return, its absolute value, the prior day's return, "
        "return × liquidity, return × volatility and FlowRatio, with date fixed effects. The flow coefficient "
        f"is negative as the hypothesis predicts. It is only borderline significant ({specA['t']:.2f}) and "
        f"weakens to {specB['t']:.2f} once leveraged-ETF stocks are allowed their own reversal slope."))
    story.append(fig(charts["forest"], "Figure 5. FlowRatio coefficient across specifications (95% CI). "
                                       "At the top-decile median FlowRatio of 0.20, a coefficient of about −60 "
                                       "means roughly 12 bps of reversal."))
    story.append(PageBreak())

    # ---------------- page 5: placebo + splits
    story.append(P("4. Against matched stocks, the gap is real only in 2026", "h1"))
    story.append(P(
        "Each top-decile stock-day is paired with the most similar stock that has never had a leveraged ETF: "
        "same day, same direction of move, closest in move size, dollar volume and volatility. Overall the "
        f"leveraged-ETF stock reverses {f1(mp['rev_treated']['mean'])} bps and its match "
        f"{f1(mp['rev_match']['mean'])} bps, a gap of <b>{f1(mp['diff']['mean'])} bps (t = {mp['diff']['t']:.2f})"
        "</b>. By year, the gap comes entirely from 2026."))
    story.append(fig(charts["py"], "Figure 6. Top-decile stock-days vs matched non-ETF stocks, by year. The top "
                                   "decile has no 2022–23 days because flows were still small."))
    story.append(P("Splits of the top decile", "h2"))
    lab = {"year": "Year", "mix": "Long vs inverse", "adv_bucket": "Liquidity", "direction": "Flow direction",
           "opex_day": "Options expiry"}
    rows = [["Split", "Group", "Stock-days", "Overnight, bps (t)", "vs matched, bps (t)"]]
    for k in ["year", "mix", "adv_bucket", "direction", "opex_day"]:
        for _, r in spl[spl["split"] == k].iterrows():
            ex = "" if pd.isna(r["excess_vs_placebo_bps"]) else f"{r['excess_vs_placebo_bps']:+.1f} ({r['excess_t']:.1f})"
            rows.append([lab[k], r["value"], f"{int(r['n']):,}", f"{r['on_xs_bps']:+.1f} ({r['t']:.1f})", ex])
    story.append(table(rows, [1.25 * inch, 2.2 * inch, 0.95 * inch, 1.3 * inch, 1.3 * inch]))
    story.append(Spacer(1, 6))
    story.append(P("No split is stable enough to build a rule on. The quad-witching figure rests on 119 "
                   "observations, and with about 30 splits tested, one or two will look significant by chance.",
                   "caption"))
    story.append(PageBreak())

    # ---------------- page 6: data quality
    story.append(P("5. Is the data good enough to trust a null?", "h1"))
    story.append(P(
        "A weak result is only informative if the flow estimates are right. The hard part is each fund's "
        "daily assets. They are rebuilt from SEC N-PORT filings (quarter-end net assets plus monthly "
        "creations and redemptions), each fund's own daily return, and a current-AUM anchor."))
    story.append(fig(charts["gamma"], "Figure 7. Reconstructed single-stock leveraged-ETF assets and the "
                                      "aggregate flow they generate for a 1% move in every underlying. "
                                      f"Yearly average flow per 1%: {', '.join(f'{y}: ${v / 100:.2f}B' for y, v in g_by_year.items() if y >= 2024)}."))
    story.append(fig(charts["aval"], f"Figure 8. Hold-out test: predict each quarter-end N-PORT figure from the "
                                     f"previous one ({len(ho):,} fund-quarters above $5M). Using the monthly "
                                     f"flow data cuts the median error from {ho_err_nf:.0%} to {ho_err:.1%}."))
    story += bullets([
        "<b>External check:</b> the model gives <b>−$2.4B</b> of MSTR rebalancing flow on 2024-11-21, "
        "consistent with press reports of $2B+ single-day MSTR flows that month.",
        "<b>Leverage changes are handled.</b> Several funds ran at 1.5x before moving to 2x (TSLL, NVDL, "
        "CONL, …). Leverage comes from each fund's measured daily returns, quarter by quarter.",
        "<b>Channel size:</b> reconstructed assets reach about $33–40B in 2026, against the ~$41–42B reported. "
        "The gap is crypto, private-company and non-US underlyings, which are excluded.",
        "<b>SEC filing errors are caught.</b> MSTZ's Nov-2024 report was also filed under a second series; "
        "the duplicate is removed.",
    ])
    story.append(PageBreak())

    # ---------------- page 7: caveats + index check + next steps
    story.append(P("6. Caveats, secondary check, and what I'd do next", "h1"))
    story.append(P("What could still be wrong", "h2"))
    story += bullets([
        "<b>How much flow actually hits the close is unknown.</b> Swap dealers can hedge during the day, and "
        "the 10%-of-volume auction proxy is a guess. If most flow is absorbed before 3:50 pm, a weak overnight "
        "reversal is what you'd expect. Only closing-imbalance data (Phase A2) settles this.",
        "<b>Mild look-ahead that favors the signal:</b> flow uses the full-day return (live, you'd estimate "
        "it at about 3:50 pm), and asset paths interpolate toward the next quarter-end filing. Neither can "
        "explain a weak result.",
        "<b>Costs are assumed.</b> There is no free quote history. Auction-to-auction trades avoid the spread "
        "but face adverse selection, which is not modeled.",
        "<b>Survivorship:</b> the 116 closed funds are included, but the comparison stocks are today's "
        "S&P 1500. Market cap is proxied by dollar volume, and Yahoo's open approximates the opening cross.",
    ])
    story.append(P("Secondary check: index-level leveraged funds", "h2"))
    ix = R["t9_index_secondary_check"]
    ix = ix[ix["outcome"] == "r_co_next"].sort_values("avg_gamma_busd", ascending=False)
    rows = [["Index proxy", "Funds", "Avg daily |flow|", "Flow → next overnight, bps per SD (t)"]]
    for _, r in ix.iterrows():
        funds = r["funds"].split(",")
        rows.append([r["proxy"], ", ".join(funds[:5]) + ("…" if len(funds) > 5 else ""),
                     f"${r['avg_abs_flow_musd']:,.0f}M", f"{r['a_coef_flow_z_bps']:+.1f} ({r['a_t_flow_z']:.2f})"])
    story.append(table(rows, [1.0 * inch, 2.9 * inch, 1.2 * inch, 1.9 * inch]))
    story.append(P("Newey-West standard errors, 1,058 days. No index shows a reliable reversal after large "
                   "leveraged-ETF flow; the one |t| ≈ 2 (FXI) is about what chance gives across 11 tests.",
                   "caption"))
    story.append(P("Next steps", "h2"))
    story.append(callout(
        "<b>Stop here and buy no data.</b> Because the effect exists only in 2026, the year flow peaked, "
        "there is a cheap way to keep the option open. Run the zero-cost Phase A2 recorders (IBKR "
        "closing-imbalance logger, daily issuer holdings scraper) for one quarter, then re-test out of sample. "
        "That would also answer the key open question: how much of the predicted flow actually shows up in "
        "the closing auction.", color=ORANGE, bg="#fdf3ee"))
    story.append(Spacer(1, 8))
    story.append(P("Everything in this document is reproducible from the repository: universe in "
                   "<font face='DV-B'>universe/</font>, pipeline in <font face='DV-B'>flows/</font>, statistics in "
                   "<font face='DV-B'>analysis/run_a1.py</font>, and all tables as CSV in "
                   "<font face='DV-B'>reports/</font>.", "caption"))

    doc = SimpleDocTemplate(str(OUT), pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.85 * inch,
                            title="Leveraged-ETF Rebalancing Reversal: Phase A1 Results", author="Phase A1 research")
    doc.build(story, onFirstPage=on_first, onLaterPages=on_page)
    print("wrote", OUT)


if __name__ == "__main__":
    build()
