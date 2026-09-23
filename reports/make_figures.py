"""Figures for the PDF report (reports/figures/*.png). Run from repo root:
    python -m reports.make_figures
Palette: validated reference categorical slots (blue, orange, aqua) + neutral inks.
"""

from __future__ import annotations

import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis.panel import HOLDOUT
from universe.build_universe import ROOT

REP = ROOT / "reports"
FIG = REP / "figures"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID, BASE = "#0b0b0b", "#52514e", "#e6e5e0", "#8a8984"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": BASE, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.titlecolor": INK, "axes.titlelocation": "left", "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.7, "legend.frameon": False,
    "figure.dpi": 200, "savefig.bbox": "tight", "savefig.pad_inches": 0.15,
})


def fig_aum():
    f = pd.read_parquet(ROOT / "data" / "panel" / "fund_day.parquet")
    f = f[f["date"] < HOLDOUT]
    tot = f.groupby("date")["aum_prev"].sum() / 1e9
    top = f[f["underlying"].isin(["TSLA", "NVDA"])].groupby("date")["aum_prev"].sum() / 1e9
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    ax.fill_between(tot.index, tot.values, color=BLUE, alpha=0.18, lw=0)
    ax.plot(tot.index, tot.values, color=BLUE, lw=2, label="All single-stock LETFs")
    ax.plot(top.index, top.reindex(tot.index).values, color=ORANGE, lw=2, label="Of which TSLA + NVDA funds")
    ax.set_ylabel("$ billions")
    ax.set_title("Single-stock leveraged ETF assets (reconstructed)")
    ax.legend(loc="upper left", fontsize=9)
    ax.annotate(f"${tot.max():.0f}B peak", (tot.idxmax(), tot.max()), xytext=(-60, 4), textcoords="offset points",
                fontsize=9, color=INK)
    fig.savefig(FIG / "aum.png")
    plt.close(fig)


def fig_event_study():
    t = pd.read_csv(REP / "event_study_hourly.csv")
    t = t[~t["point"].isin(["t 09:30", "t 10:30"])].reset_index(drop=True)  # morning move is huge by construction
    x = np.arange(len(t))
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    ax.axhline(0, color=BASE, lw=1)
    for lab in ("t close", "t+1 close"):
        ax.axvline(t.index[t["point"] == lab][0] + 0.5, color=BASE, lw=0.8, ls=":")
    ax.axvspan(t.index[t["point"] == "t 13:30"][0], t.index[t["point"] == "t 15:30"][0], color=AQUA, alpha=0.08, lw=0)
    ax.fill_between(x, t["event_bps"] - 1.96 * t["event_se"], t["event_bps"] + 1.96 * t["event_se"], color=BLUE, alpha=0.15, lw=0)
    ax.plot(x, t["event_bps"], color=BLUE, lw=2, marker="o", ms=4, label="Top 5% predicted LETF flow")
    ax.plot(x, t["comparison_bps"], color=ORANGE, lw=2, marker="o", ms=4, label="Same-size moves, little LETF flow")
    ax.set_xticks(x, [p.replace("t+1 ", "+1 ").replace("t ", "") for p in t["point"]], rotation=60, ha="right", fontsize=7.5)
    ax.set_ylabel("bps in flow direction, vs 13:30")
    ax.set_ylim(-110, 180)
    ax.set_title("Where the price pressure happens")
    ax.text(t.index[t["point"] == "t 13:30"][0] + 0.1, 150, "extra move\n13:30-15:30", fontsize=8, color=MUTED, va="top")
    ax.text(t.index[t["point"] == "t close"][0] + 0.6, 165, "day t+1", fontsize=8, color=MUTED)
    ax.text(t.index[t["point"] == "t+1 close"][0] + 0.6, 165, "days t+2..t+5", fontsize=8, color=MUTED)
    ax.legend(loc="lower right", fontsize=8.5)
    fig.savefig(FIG / "event_study.png")
    plt.close(fig)


def fig_overnight():
    m = pd.read_csv(REP / "baseline_matched_excess.csv")
    m = m[m["y"] == "on1_x"].set_index("subset")
    labels = ["All days", "2024", "2025", "2026\n(Q1)", "Up\ndays", "Down\ndays", "Excl.\ntop-10 days"]
    keys = ["all", "year=2024", "year=2025", "year=2026", "up days", "down days", None]
    vals = [m.loc[k, "excess_bps"] if k else 5.84 for k in keys]
    errs = [m.loc[k, "excess_se"] if k else 5.54 for k in keys]  # ex-top-10 from RESEARCH_LOG run
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    cols = [BLUE] * 6 + [ORANGE]
    ax.bar(x, vals, color=cols, width=0.6, edgecolor="white", linewidth=1.5, zorder=3)
    ax.errorbar(x, vals, yerr=1.96 * np.array(errs), fmt="none", ecolor=INK, elinewidth=1, capsize=3, zorder=4)
    ax.axhline(0, color=BASE, lw=1)
    ax.set_xticks(x, labels, fontsize=8.5)
    ax.set_ylabel("bps, vs matched stocks")
    ax.set_title("Overnight reversal after top-decile flow days (95% CI)")
    for xi, v, e in zip(x, vals, errs):
        ax.annotate(f"{v:+.0f}", (xi, v + 1.96 * e), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=9, color=INK)
    ax.set_ylim(-40, 75)
    fig.savefig(FIG / "overnight.png")
    plt.close(fig)


def fig_placebo():
    p = pd.read_csv(REP / "placebo_prelaunch.csv")
    tests = ["anticipation 13:30->close", "reversal on1_x_w", "reversal cc1_x_w"]
    names = ["Afternoon momentum\n(13:30 to close)", "Overnight reversal\n(close to open)", "Next-day reversal\n(close to close)"]
    real = [p[(p.test == t) & p["sample"].str.startswith("real")].iloc[0] for t in tests]
    plac = [p[(p.test == t) & p["sample"].str.startswith("placebo")].iloc[0] for t in tests]
    x = np.arange(len(tests))
    w = 0.36
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    for off, rows, c, lab in ((-w / 2, real, BLUE, "Days with LETFs"), (w / 2, plac, ORANGE, "Same stocks before LETFs existed")):
        v = [r["excess_bps"] for r in rows]
        e = [r["se"] for r in rows]
        ax.bar(x + off, v, width=w, color=c, label=lab, edgecolor="white", linewidth=1.5, zorder=3)
        ax.errorbar(x + off, v, yerr=1.96 * np.array(e), fmt="none", ecolor=INK, elinewidth=1, capsize=3, zorder=4)
    ax.axhline(0, color=BASE, lw=1)
    ax.set_xticks(x, names, fontsize=8.5)
    ax.set_ylabel("excess bps vs matched stocks")
    ax.set_title("Pre-launch placebo test (95% CI)")
    ax.legend(fontsize=8.5, loc="lower left")
    fig.savefig(FIG / "placebo.png")
    plt.close(fig)


def fig_premium_threshold():
    t = pd.read_csv(REP / "letf_premium.csv")
    ex = t[t["item"].str.startswith("exact: next-day premium reversion")]
    ks = [10, 25, 50, 100]
    vals = ex["value"].values
    errs = ex["se"].values
    x = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(7.5, 3.3))
    ax.bar(x, vals, color=BLUE, width=0.55, edgecolor="white", linewidth=1.5, zorder=3, label="Reversion next day")
    ax.errorbar(x, vals, yerr=1.96 * errs, fmt="none", ecolor=INK, elinewidth=1, capsize=3, zorder=4)
    ax.plot(x, ks, color=ORANGE, lw=2, marker="o", ms=6, zorder=5, label="Premium threshold (for scale)")
    for xi, v in zip(x, vals):
        ax.annotate(f"{v:.0f}", (xi, v), xytext=(10, 2), textcoords="offset points", fontsize=9, color=INK)
    ax.set_xticks(x, [f"|premium| >= {k} bps" for k in ks], fontsize=8.5)
    ax.set_ylabel("bps")
    ax.set_title("Closing premium vs NAV reverts next day (exact NAV, 38 funds)")
    ax.legend(fontsize=8.5, loc="upper left")
    fig.savefig(FIG / "premium_threshold.png")
    plt.close(fig)


def fig_intraday():
    d = pd.read_csv(REP / "letf_premium_intraday.csv").set_index("sample").loc["fund ADV >= $20M"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.5, 3.2), gridspec_kw={"wspace": 0.45})
    v = [-d["slope_next_on_e_pre"] * 100, -d["slope_next_on_e_last"] * 100]
    a1.bar([0, 1], v, color=[ORANGE, BLUE], width=0.55, edgecolor="white", linewidth=1.5, zorder=3)
    a1.set_xticks([0, 1], ["Formed before\n15:30", "Formed 15:30\nto close"], fontsize=8.5)
    a1.set_ylabel("% reverted next day")
    a1.set_title("Which part reverts", fontsize=11)
    for xi, vi in enumerate(v):
        a1.annotate(f"{vi:.0f}%", (xi, vi), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=9, color=INK)
    v2 = [d["rev_e_next_am_bps"], d["rev_e_next_rest_bps"]]
    e2 = [d["rev_e_next_am_se"], d["rev_e_next_rest_se"]]
    a2.bar([0, 1], v2, color=[BLUE, ORANGE], width=0.55, edgecolor="white", linewidth=1.5, zorder=3)
    a2.errorbar([0, 1], v2, yerr=1.96 * np.array(e2), fmt="none", ecolor=INK, elinewidth=1, capsize=3, zorder=4)
    a2.axhline(0, color=BASE, lw=1)
    a2.set_xticks([0, 1], ["Close to\n10:30 next day", "10:30 to\nnext close"], fontsize=8.5)
    a2.set_ylabel("bps reverted")
    a2.set_title("When it reverts (|e| >= 50 bps)", fontsize=11)
    for xi, vi in enumerate(v2):
        a2.annotate(f"{vi:+.0f}", (xi, max(vi, 0)), xytext=(8, 3), textcoords="offset points", fontsize=9, color=INK)
    fig.savefig(FIG / "premium_intraday.png")
    plt.close(fig)


def fig_venue():
    v = pd.read_csv(REP / "letf_premium_by_venue.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.5, 3.0), gridspec_kw={"wspace": 0.45})
    x = np.arange(len(v))
    a1.bar(x, v["event_rate"] * 100, color=BLUE, width=0.55, edgecolor="white", linewidth=1.5, zorder=3)
    a1.set_xticks(x, v["venue"], fontsize=8.5)
    a1.set_ylabel("% of fund-days")
    a1.set_title("How often |e| >= 50 bps", fontsize=11)
    a2.bar(x, v["rev_bps"], color=BLUE, width=0.55, edgecolor="white", linewidth=1.5, zorder=3)
    a2.errorbar(x, v["rev_bps"], yerr=1.96 * v["se"], fmt="none", ecolor=INK, elinewidth=1, capsize=3, zorder=4)
    a2.set_xticks(x, v["venue"], fontsize=8.5)
    a2.set_ylabel("bps")
    a2.set_title("Next-day reversion", fontsize=11)
    for a, col, fmt in ((a1, v["event_rate"] * 100, "{:.0f}%"), (a2, v["rev_bps"], "{:.0f}")):
        for xi, vi in zip(x, col):
            a.annotate(fmt.format(vi), (xi, vi), xytext=(10, 2), textcoords="offset points", fontsize=9, color=INK)
    fig.savefig(FIG / "premium_venue.png")
    plt.close(fig)


def fig_pnl():
    from analysis.letf_premium import fund_frame, load_navs

    u = pd.read_csv(ROOT / "universe" / "letf_universe_final.csv")
    u = u[u["price_ticker"].notna()]
    sched = pd.read_parquet(ROOT / "universe" / "leverage_schedule.parquet")
    navs = load_navs()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        p = pd.concat([fund_frame(r, sched, navs.get(r["price_ticker"])) for _, r in u.iterrows()], ignore_index=True)
    p = p[p["e"].abs().lt(0.2) & p["e_next"].abs().lt(0.2)]
    p["fund_adv"] = p.groupby("ticker")["dvol_fund"].transform(lambda s: s.rolling(20, min_periods=10).mean().shift(1))
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    for adv_min, cost, c, lab in ((0, 5, BLUE, "All funds, 5 bps cost"), (20e6, 5, AQUA, "Fund ADV >= $20M, 5 bps"),
                                  (0, 10, ORANGE, "All funds, 10 bps cost")):
        s = p[(p["e"].abs() >= 0.005) & (p["fund_adv"] >= adv_min)].copy()
        s["size"] = np.minimum(1e6, 0.01 * s["fund_adv"])
        s["pnl"] = s["size"] * (-np.sign(s["e"]) * s["e_next"] * 1e4 - cost - 1) / 1e4
        cum = s.groupby("date")["pnl"].sum().sort_index().cumsum() / 1e6
        ax.plot(cum.index, cum.values, color=c, lw=2, label=lab)
    ax.axhline(0, color=BASE, lw=1)
    ax.set_ylabel("$ millions, cumulative")
    ax.set_title("Illustrative P&L: fade |premium change| >= 50 bps at the close")
    ax.legend(fontsize=8.5, loc="upper left")
    fig.savefig(FIG / "premium_pnl.png")
    plt.close(fig)


if __name__ == "__main__":
    FIG.mkdir(parents=True, exist_ok=True)
    for fn in (fig_aum, fig_event_study, fig_overnight, fig_placebo, fig_premium_threshold, fig_intraday, fig_venue, fig_pnl):
        fn()
        print("ok", fn.__name__)
