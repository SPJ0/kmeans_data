"""Intraday event study around high-flow days (hourly bars, Oct 2023 onward).

Events: treated stock-days in the top 5% of |flow_pre_adv| (flow predicted from
the 15:30 price, i.e. knowable before the close). Comparison: treated-name days
with below-median gamma/ADV and the same sign and size bucket of the move to
15:30 (|r_pre| / vol60), reweighted to the events' bucket mix.

Path: log price relative to 13:30 on day t, signed by the flow direction (so
"up" = in the direction of the predicted flow), beta-adjusted with QQQ.
Positive after the close = continuation; falling back toward zero = reversal.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis.baseline import prepare
from analysis.panel import HOLDOUT
from analysis.stats import clustered_mean
from pipelines.prices import load_daily, load_hourly
from universe.build_universe import ROOT

BLUE, ORANGE, GRAY, INK, MUTED = "#2a78d6", "#eb6834", "#8a8984", "#0b0b0b", "#52514e"
POINTS = (["t 09:30", "t 10:30", "t 11:30", "t 12:30", "t 13:30", "t 14:30", "t 15:30", "t close",
           "t+1 open", "t+1 10:30", "t+1 11:30", "t+1 12:30", "t+1 13:30", "t+1 14:30", "t+1 15:30", "t+1 close",
           "t+2 close", "t+3 close", "t+4 close", "t+5 close"])
REF = POINTS.index("t 13:30")


def price_grid(ticker: str) -> pd.DataFrame:
    """Per date: hourly bar opens 09:30..15:30, daily open and official close."""
    h, d = load_hourly(ticker), load_daily(ticker)
    if h.empty or d.empty:
        return pd.DataFrame()
    h = h[h.index.minute == 30]
    g = h["Open"].copy()
    g.index = pd.MultiIndex.from_arrays([h.index.tz_localize(None).normalize(), h.index.hour])
    g = g[~g.index.duplicated()].unstack()
    g.columns = [f"{c:02d}:30" for c in g.columns]
    g["open"] = d["Open"].reindex(g.index)
    g["close"] = d["Close"].reindex(g.index)
    # drop dates where hourly and daily data disagree (see analysis.panel.hourly_opens)
    last = h[h.index.hour == 15]["Close"]
    last = last.set_axis(last.index.tz_localize(None).normalize())
    last = last[~last.index.duplicated()].reindex(g.index)
    g = g[(np.log(last / g["close"]).abs() <= 0.03)]
    return g.dropna(subset=["close"])


def paths(ticker: str, dates: pd.DatetimeIndex, grid: pd.DataFrame) -> pd.DataFrame:
    idx = grid.index
    rows = {}
    for t in dates:
        k = idx.searchsorted(t)
        if k >= len(idx) or idx[k] != t or k + 5 >= len(idx) or idx[k + 5] >= HOLDOUT:
            continue
        a, b = grid.iloc[k], grid.iloc[k + 1]
        v = [a.get("09:30"), a.get("10:30"), a.get("11:30"), a.get("12:30"), a.get("13:30"), a.get("14:30"),
             a.get("15:30"), a["close"], b["open"], b.get("10:30"), b.get("11:30"), b.get("12:30"), b.get("13:30"),
             b.get("14:30"), b.get("15:30"), b["close"]] + [grid.iloc[k + j]["close"] for j in (2, 3, 4, 5)]
        rows[t] = np.log(np.array(v, dtype=float))
    return pd.DataFrame.from_dict(rows, orient="index", columns=POINTS)


def main():
    p = prepare(pd.read_parquet(ROOT / "data" / "panel" / "panel_treated.parquet"))
    p = p[p["r_pre"].notna() & p["beta"].notna()]
    names = p.loc[p["treated"], "ticker"].unique()
    p = p[p["ticker"].isin(names)].copy()
    p["z"] = (p["r_pre"] / p["vol60"]).abs()
    p["zb"] = pd.cut(p["z"], [0, 0.5, 1, 1.5, 2, 3, 4, np.inf], labels=False)
    p["sgn"] = np.sign(p["r_pre"])
    tr = p[p["treated"]]
    cut = tr["flow_pre_adv"].abs().quantile(0.95)
    ev = tr[tr["flow_pre_adv"].abs() >= cut].copy()
    med = tr["g_adv"].median()
    cmp_ = p[(p["g_adv"] < med)].copy()

    qqq = price_grid("QQQ")
    qpath = paths("QQQ", qqq.index, qqq)
    qpath = qpath.sub(qpath[POINTS[REF]], axis=0)

    def collect(frame: pd.DataFrame) -> pd.DataFrame:
        out = []
        for t, g in frame.groupby("ticker"):
            grid = price_grid(t)
            if grid.empty:
                continue
            pa = paths(t, pd.DatetimeIndex(g["date"]), grid)
            if pa.empty:
                continue
            pa = pa.sub(pa[POINTS[REF]], axis=0)
            gg = g.set_index("date").loc[pa.index]
            pa = pa - qpath.reindex(pa.index).mul(gg["beta"], axis=0)  # beta-adjust
            sign = np.sign(gg["flow_pre_adv"]).where(gg["flow_pre_adv"] != 0, gg["sgn"])
            pa = pa.mul(sign, axis=0)
            pa["ticker"], pa["date"] = t, pa.index
            pa["bucket"] = list(zip(gg["sgn"], gg["zb"]))
            out.append(pa.reset_index(drop=True))
        return pd.concat(out, ignore_index=True)

    E = collect(ev)
    C = collect(cmp_)
    # reweight comparison to the events' bucket mix
    w_ev = E["bucket"].value_counts(normalize=True)
    cmean = C.groupby("bucket")[POINTS].mean()
    cm = (cmean.reindex(w_ev.index).mul(w_ev, axis=0)).sum() / w_ev[w_ev.index.isin(cmean.index)].sum()

    rows = []
    for c in POINTS:
        m, se, n = clustered_mean(E[c] * 1e4, E["date"])
        rows.append(dict(point=c, event_bps=m, event_se=se, n=n, comparison_bps=cm[c] * 1e4))
    tab = pd.DataFrame(rows)
    tab["excess_bps"] = tab["event_bps"] - tab["comparison_bps"]
    tab.to_csv(ROOT / "reports" / "event_study_hourly.csv", index=False)

    fig, ax = plt.subplots(figsize=(11, 5.2), dpi=150)
    x = np.arange(len(POINTS))
    ax.axhline(0, color=GRAY, lw=1)
    for xv in (POINTS.index("t close") + 0.5, POINTS.index("t+1 close") + 0.5):
        ax.axvline(xv, color=GRAY, lw=0.8, ls=":")
    ax.fill_between(x, tab["event_bps"] - 1.96 * tab["event_se"], tab["event_bps"] + 1.96 * tab["event_se"],
                    color=BLUE, alpha=0.15, lw=0)
    ax.plot(x, tab["event_bps"], color=BLUE, lw=2, marker="o", ms=4, label=f"Top 5% predicted flow (n={len(E):,})")
    ax.plot(x, tab["comparison_bps"], color=ORANGE, lw=2, marker="o", ms=4,
            label=f"Same-size moves, low LETF gamma (n={len(C):,}, reweighted)")
    ax.set_xticks(x, POINTS, rotation=45, ha="right", fontsize=8, color=MUTED)
    ax.set_ylabel("bps, signed in flow direction, beta-adj., rel. to 13:30 on t", color=MUTED, fontsize=9)
    ax.set_title("Price path around high predicted-flow days (Oct 2023 – Mar 2026, hourly)", color=INK, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#e6e5e0", lw=0.6)
    fig.tight_layout()
    fig.savefig(ROOT / "reports" / "event_study_hourly.png")
    pd.set_option("display.width", 200)
    print(f"events {len(E)} ({E['ticker'].nunique()} names, {E['date'].nunique()} dates); |flow_pre_adv| cut {cut:.4f}")
    print(tab.to_string(float_format=lambda v: f"{v:,.1f}"))


if __name__ == "__main__":
    main()
