"""Phase A1: does leveraged-ETF rebalancing flow predict next-period reversal?

Reads data/cache/stock_days.parquet (flows/build_panel.py) and writes tables
and charts to reports/. All t-stats use standard errors clustered by date
unless stated otherwise.

Sign convention: signed reversal = -sign(Flow_t) * R, in bps; positive means
the stock moved against the rebalancing flow (the trade we want to make).
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from analysis.stats import clustered_mean, clustered_mean_2way, fe_ols  # noqa: E402
from common.paths import CACHE, REPORTS  # noqa: E402
from flows.earnings import exclusion_mask  # noqa: E402

START = pd.Timestamp("2022-07-01")
OUTCOMES = {  # label -> column
    "on_raw": "r_co_next", "on_xs": "r_co_next_xs", "on_xsQQQ": "r_co_next_xsQQQ",
    "cc_raw": "r_cc_next", "cc_xs": "r_cc_next_xs", "oc_xs": "r_oc_next_xs",
}
MAIN = "on_xs"          # close_t -> open_{t+1}, beta-adjusted: the proposed trade
BLUE, ORANGE, GRAY, INK, MUTED = "#2a78d6", "#eb6834", "#8a8984", "#0b0b0b", "#52514e"


# ----------------------------------------------------------------------------- sample
def load_sample() -> tuple[pd.DataFrame, dict]:
    sd = pd.read_parquet(CACHE / "stock_days.parquet")
    notes = {"rows_raw": len(sd)}
    sd = sd[(sd["date"] >= START) & sd["r_co_next"].notna() & sd["r_cc_next"].notna()]
    notes["rows_in_window"] = len(sd)
    sd = sd[~sd["bad_next"].astype(bool)]
    notes["after_bad_print_filter"] = len(sd)
    sd = sd[(sd["auction_proxy"] > 0) & sd["vol60"].notna() & sd["r_cc"].notna() & sd["r_co_next_xs"].notna()]
    sd = sd[sd["close"] >= 2.0]
    notes["after_liquidity_history_filter"] = len(sd)
    ed = pd.read_parquet(CACHE / "earnings_dates.parquet")
    sd = sd.reset_index(drop=True)
    earn = exclusion_mask(sd, ed)
    notes["earnings_window_rows_dropped"] = int(earn.sum())
    notes["tickers_without_earnings_dates"] = sorted(set(ed.loc[ed["source"] == "none", "ticker"]) & set(sd["ticker"]))
    sd = sd[~earn].copy()
    sd["treated"] = sd["Gamma"] > 0
    sd["year"] = sd["date"].dt.year
    sgn = -np.sign(sd["Flow"].where(sd["treated"], sd["r_cc"]))
    for k, c in OUTCOMES.items():
        sd[f"rev_{k}"] = sgn * sd[c] * 1e4
    sd["absFR"] = sd["FlowRatio"].abs()
    sd["abs_r"] = sd["r_cc"].abs()
    notes["rows_final"] = len(sd)
    notes["treated_rows"] = int(sd["treated"].sum())
    notes["treated_stocks"] = int(sd.loc[sd["treated"], "ticker"].nunique())
    return sd, notes


def cm_row(g: pd.DataFrame, col: str) -> dict:
    r = clustered_mean(g[col], g["date"])
    return {"mean_bps": r["mean"], "t": r["t"], "n": r["n"], "hit": (g[col] > 0).mean()}


# ----------------------------------------------------------------------------- 1. sorts
def decile_sorts(tr: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    tr = tr.copy()
    tr["dec"] = pd.qcut(tr["absFR"].rank(method="first"), 10, labels=range(1, 11)).astype(int)
    rows = []
    for d, g in tr.groupby("dec"):
        row = {"decile": d, "n": len(g), "absFR_median": g["absFR"].median(), "abs_r_mean": g["abs_r"].mean(),
               "flow_musd_median": g["Flow"].abs().median() / 1e6}
        for k in ("on_raw", "on_xs", "cc_xs", "oc_xs"):
            r = cm_row(g, f"rev_{k}")
            row[f"{k}_bps"], row[f"{k}_t"], row[f"{k}_hit"] = r["mean_bps"], r["t"], r["hit"]
        row["on_xs_t_2way(date,stock)"] = clustered_mean_2way(g[f"rev_{MAIN}"], g["date"], g["ticker"])["t"]
        row["n_stocks"] = g["ticker"].nunique()
        rows.append(row)
    dec = pd.DataFrame(rows)
    # signed FlowRatio deciles: raw next returns (asymmetry between buy- and sell-flow days)
    tr["sdec"] = pd.qcut(tr["FlowRatio"].rank(method="first"), 10, labels=range(1, 11)).astype(int)
    rows = []
    for d, g in tr.groupby("sdec"):
        r = clustered_mean(g["r_co_next_xs"] * 1e4, g["date"])
        rows.append({"signed_decile": d, "FR_median": g["FlowRatio"].median(), "r_t_mean": g["r_cc"].mean(),
                     "next_on_xs_bps": r["mean"], "t": r["t"], "n": r["n"]})
    sdec = pd.DataFrame(rows)
    # fixed ex-ante thresholds (no in-sample breakpoints)
    bins = [0, 0.01, 0.03, 0.1, 0.3, 1.0, np.inf]
    tr["fbin"] = pd.cut(tr["absFR"], bins, right=False)
    rows = []
    for b, g in tr.groupby("fbin", observed=True):
        r = cm_row(g, f"rev_{MAIN}")
        rows.append({"absFR_bin": str(b), "n": r["n"], "abs_r_mean": g["abs_r"].mean(),
                     "on_xs_bps": r["mean_bps"], "t": r["t"], "hit": r["hit"],
                     "n_dates": g["date"].nunique(), "n_stocks": g["ticker"].nunique()})
    fbin = pd.DataFrame(rows)
    return dec, sdec, fbin


def double_sort(sd: pd.DataFrame) -> pd.DataFrame:
    """Within |r_t| quintiles: placebo-universe stocks (no funds) vs treated terciles of GammaRatio."""
    d = sd.copy()
    d["rq"] = pd.qcut(d["abs_r"].rank(method="first"), 5, labels=[f"|r| Q{i}" for i in range(1, 6)])
    d["grp"] = "no lev ETF"
    t = d["treated"]
    d.loc[t, "grp"] = pd.qcut(d.loc[t, "GammaRatio"].rank(method="first"), 3,
                              labels=["Gamma low", "Gamma mid", "Gamma high"]).astype(str)
    rows = []
    for (rq, grp), g in d.groupby(["rq", "grp"], observed=True):
        r = cm_row(g, f"rev_{MAIN}")
        rows.append({"abs_r_quintile": rq, "group": grp, "abs_r_mean": g["abs_r"].mean(),
                     "absFR_median": g["absFR"].median(), "on_xs_bps": r["mean_bps"], "t": r["t"], "n": r["n"]})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- 2. regression
def control_regressions(sd: pd.DataFrame) -> pd.DataFrame:
    d = sd.copy()
    lo, hi = d.loc[d["treated"], "FlowRatio"].quantile([0.005, 0.995])
    d["FR_w"] = d["FlowRatio"].clip(lo, hi)
    d["z_ladv"] = (np.log(d["adv20"]) - np.log(d["adv20"]).mean()) / np.log(d["adv20"]).std()
    d["z_vol"] = (d["vol60"] - d["vol60"].mean()) / d["vol60"].std()
    d["r_x_ladv"] = d["r_cc"] * d["z_ladv"]
    d["r_x_vol"] = d["r_cc"] * d["z_vol"]
    d["r_x_treated"] = d["r_cc"] * d["treated"]
    d["y_on"] = d["r_co_next_xs"] * 1e4
    d["y_cc"] = d["r_cc_next_xs"] * 1e4
    d["y_on_raw"] = d["r_co_next"] * 1e4
    base = ["r_cc", "abs_r", "r_cc_lag1", "r_x_ladv", "r_x_vol"]
    specs = [
        ("A: on_xs ~ FR (all stocks, date FE)", "y_on", base + ["FR_w"], ("date",), ("date",), d),
        ("B: A + r*treated", "y_on", base + ["r_x_treated", "FR_w"], ("date",), ("date",), d),
        ("C: A, date+stock FE, 2-way cluster", "y_on", base + ["FR_w"], ("date", "ticker"), ("date", "ticker"), d),
        ("D: treated only, date FE", "y_on", base + ["FR_w"], ("date",), ("date",), d[d["treated"]]),
        ("E: treated only, date+stock FE", "y_on", base + ["FR_w"], ("date", "ticker"), ("date",), d[d["treated"]]),
        ("F: raw overnight (no beta adj), date FE", "y_on_raw", base + ["FR_w"], ("date",), ("date",), d),
        ("G: close-to-close next day, date FE", "y_cc", base + ["FR_w"], ("date",), ("date",), d),
    ]
    out = []
    for name, y, xs, fe, cl, dd in specs:
        res = fe_ols(dd, y, xs, fe=fe, cluster=cl, iters=3 if len(fe) > 1 else 1)
        res["spec"] = name
        out.append(res.reset_index(names="var"))
    tab = pd.concat(out, ignore_index=True)
    tab.attrs["FR_winsor"] = (lo, hi)
    return tab


# ----------------------------------------------------------------------------- 3. matched placebo
def matched_placebo(sd: pd.DataFrame, top: pd.DataFrame) -> pd.DataFrame:
    """Each top-bucket treated stock-day vs the nearest never-treated stock on the same date.

    Match: same sign of r_t, nearest in standardized (r_t, log ADV20, vol60).
    ADV stands in for market cap (no free point-in-time market-cap history).
    """
    pool = sd[~sd["treated_ever"]]
    feats = ["r_cc", "ladv", "vol60"]
    sd = sd.assign(ladv=np.log(sd["adv20"]))
    pool = pool.assign(ladv=np.log(pool["adv20"]))
    top = top.assign(ladv=np.log(top["adv20"]))
    scale = sd[feats].std()
    by_date = {d: g for d, g in pool.groupby("date")}
    rows = []
    for _, r in top.iterrows():
        g = by_date.get(r["date"])
        if g is None:
            continue
        g = g[np.sign(g["r_cc"]) == np.sign(r["r_cc"])]
        if g.empty:
            continue
        dist = (((g[feats] - r[feats].astype(float)) / scale) ** 2).sum(axis=1)
        m = g.loc[dist.idxmin()]
        s = -np.sign(r["Flow"])
        rows.append({"date": r["date"], "ticker": r["ticker"], "match": m["ticker"], "dist": dist.min(),
                     "r_t": r["r_cc"], "r_t_match": m["r_cc"], "ladv": r["ladv"], "ladv_match": m["ladv"],
                     "vol": r["vol60"], "vol_match": m["vol60"],
                     "rev_treated": s * r["r_co_next_xs"] * 1e4, "rev_match": s * m["r_co_next_xs"] * 1e4,
                     "rev_treated_cc": s * r["r_cc_next_xs"] * 1e4, "rev_match_cc": s * m["r_cc_next_xs"] * 1e4})
    mp = pd.DataFrame(rows)
    mp["diff"] = mp["rev_treated"] - mp["rev_match"]
    mp["diff_cc"] = mp["rev_treated_cc"] - mp["rev_match_cc"]
    return mp


# ----------------------------------------------------------------------------- 4. splits
def opex_flags(dates: pd.Series) -> pd.DataFrame:
    cal = pd.DatetimeIndex(sorted(dates.unique()))
    s = pd.Series(cal, index=cal)
    third_fri = set()
    for (y, m), g in s.groupby([cal.year, cal.month]):
        fr = pd.Timestamp(y, m, 15) + pd.offsets.Week(weekday=4) if pd.Timestamp(y, m, 15).weekday() != 4 else \
            pd.Timestamp(y, m, 15)
        # last trading day on/before the third Friday (holiday -> Thursday)
        ok = g[g <= fr]
        if len(ok):
            third_fri.add(ok.iloc[-1])
    opex = dates.isin(third_fri)
    quarterly = opex & dates.dt.month.isin([3, 6, 9, 12])
    return pd.DataFrame({"opex": opex, "quad_witching": quarterly})


def splits(top: pd.DataFrame, mp: pd.DataFrame) -> pd.DataFrame:
    t = top.copy()
    t["inv_share"] = np.where(t["Gamma"] > 0, t["Gamma_inv"] / t["Gamma"], np.nan)
    t["mix"] = pd.cut(t["inv_share"], [-0.01, 0.2, 0.5, 1.01], labels=["mostly long (<20% inv Gamma)",
                                                                        "mixed", "inverse-heavy (>50%)"])
    t["adv_bucket"] = pd.qcut(t["adv20"], 3, labels=["ADV low", "ADV mid", "ADV high"])
    t["dow"] = t["date"].dt.day_name()
    t = pd.concat([t.reset_index(drop=True), opex_flags(t["date"]).reset_index(drop=True)], axis=1)
    t["opex_day"] = np.where(t["quad_witching"], "quad witching", np.where(t["opex"], "monthly opex", "non-opex"))
    t["direction"] = np.where(t["Flow"] > 0, "buy flow (up day)", "sell flow (down day)")
    mpd = mp.set_index(["date", "ticker"])["diff"]
    t["diff_vs_match"] = [mpd.get((d, k), np.nan) for d, k in zip(t["date"], t["ticker"])]
    rows = []
    for dim in ("year", "mix", "adv_bucket", "dow", "opex_day", "direction"):
        for v, g in t.groupby(dim, observed=True):
            r = cm_row(g, f"rev_{MAIN}")
            r2 = clustered_mean(g["diff_vs_match"], g["date"])
            rc = clustered_mean(g["rev_cc_xs"], g["date"])
            rows.append({"split": dim, "value": str(v), "n": r["n"], "on_xs_bps": r["mean_bps"], "t": r["t"],
                         "hit": r["hit"], "cc_xs_bps": rc["mean"], "cc_t": rc["t"],
                         "excess_vs_placebo_bps": r2["mean"], "excess_t": r2["t"], "n_stocks": g["ticker"].nunique()})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- 5. P&L sim
# Assumed quoted half-spreads by liquidity (bps). No free historical quote data; typical
# US-equity values. Phase A2 replaces this with measured spreads/auction prints.
HALF_SPREAD_BUCKETS = [(1e9, 1.0), (2e8, 2.0), (5e7, 5.0), (1e7, 10.0), (0, 20.0)]


def half_spread_bps(adv: pd.Series) -> pd.Series:
    out = pd.Series(20.0, index=adv.index)
    for lo, hs in reversed(HALF_SPREAD_BUCKETS):
        out[adv >= lo] = hs
    return out


def simulate(tr: pd.DataFrame, capital: float = 5e6, frac: float = 0.10, name_cap: float = 0.5e6,
             fixed_bps: float = 2.0, hedge_bps: float = 0.5, spread_mult: float = 1.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Trade top-bucket names each day; bucket threshold is the trailing-250-day 90th pct of |FlowRatio|.

    size = min(frac * |Flow|, name_cap), scaled so gross <= capital. Fade the flow at
    the close, beta-hedge, exit at next open. P&L on beta-adjusted overnight return.
    Cost per round trip = spread_mult * half_spread + fixed_bps (+ hedge_bps on the hedge notional).
    """
    d = tr.sort_values("date").copy()
    daily_q = d.groupby("date")["absFR"].apply(lambda x: x.to_numpy())
    dates = daily_q.index
    thr = {}
    hist = []
    for i, dt in enumerate(dates):
        past = np.concatenate(hist[-250:]) if hist else np.array([])
        thr[dt] = np.quantile(past, 0.9) if len(hist) >= 60 else np.nan
        hist.append(daily_q.iloc[i])
    d["thr"] = d["date"].map(thr)
    sel = d[d["absFR"] >= d["thr"]].copy()
    sel["size"] = np.minimum(frac * sel["Flow"].abs(), name_cap)
    gross = sel.groupby("date")["size"].transform("sum")
    sel["size"] = sel["size"] * np.minimum(1.0, capital / gross)
    sel["half_spread_bps"] = half_spread_bps(sel["adv20"])
    sel["cost_bps"] = spread_mult * sel["half_spread_bps"] + fixed_bps + hedge_bps * sel["beta_pick"].abs().fillna(1)
    sel["gross_pnl"] = sel["size"] * sel[f"rev_{MAIN}"] / 1e4
    sel["net_pnl"] = sel["gross_pnl"] - sel["size"] * sel["cost_bps"] / 1e4
    day = sel.groupby("date").agg(gross_pnl=("gross_pnl", "sum"), net_pnl=("net_pnl", "sum"),
                                  deployed=("size", "sum"), n=("ticker", "size"))
    day = day.reindex(dates, fill_value=0.0)
    return sel, day


def perf(day: pd.DataFrame, capital: float, col: str = "net_pnl") -> dict:
    r = day[col] / capital
    eq = r.cumsum()
    dd = (eq - eq.cummax()).min()
    return {"ann_return_pct": r.mean() * 252 * 100, "ann_vol_pct": r.std() * np.sqrt(252) * 100,
            "sharpe": r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else np.nan,
            "max_drawdown_pct": dd * 100, "pct_days_traded": (day["n"] > 0).mean() * 100,
            "avg_deployed_musd": day.loc[day["n"] > 0, "deployed"].mean() / 1e6,
            "total_pnl_musd": day[col].sum() / 1e6, "worst_day_pct": r.min() * 100, "best_day_pct": r.max() * 100}


def concentration(sel: pd.DataFrame, day: pd.DataFrame, col: str = "gross_pnl") -> dict:
    tot = day[col].sum()
    top10 = day[col].nlargest(10).sum()
    by_name = sel.groupby("ticker")[col].sum().sort_values(ascending=False)
    return {"total_musd": tot / 1e6, "top10_days_share": top10 / tot if tot else np.nan,
            "top5_names_share": by_name.head(5).sum() / tot if tot else np.nan,
            "top5_names": ", ".join(f"{k} ({v / 1e6:.2f}M)" for k, v in by_name.head(5).items()),
            "pnl_ex_top10_days_musd": (tot - top10) / 1e6,
            "pnl_ex_top5_names_musd": (tot - by_name.head(5).sum()) / 1e6}


# ----------------------------------------------------------------------------- charts
def _style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#d6d5d0")
    ax.spines["bottom"].set_color("#d6d5d0")
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.yaxis.grid(True, color="#ecebe6", linewidth=0.8)
    ax.set_axisbelow(True)


def charts(dec, ds, day, day_by_cost, gam, mp_year):
    plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold"})
    # 1. decile bars with 95% CI
    fig, ax = plt.subplots(figsize=(8, 4.2))
    se = dec["on_xs_bps"] / dec["on_xs_t"]
    ax.bar(dec["decile"], dec["on_xs_bps"], width=0.7, color=BLUE, yerr=1.96 * se,
           error_kw={"ecolor": MUTED, "elinewidth": 1, "capsize": 3})
    ax.axhline(0, color=INK, linewidth=0.8)
    ax.set_xticks(dec["decile"])
    ax.set_xlabel("Decile of |FlowRatio| (treated stock-days)", color=MUTED)
    ax.set_ylabel("Signed reversal, bps", color=MUTED)
    ax.set_title("Overnight beta-adjusted reversal by |FlowRatio| decile (95% CI, date-clustered)", loc="left")
    _style(ax)
    fig.tight_layout()
    fig.savefig(REPORTS / "fig1_deciles.png", dpi=150)
    plt.close(fig)

    # 2. double sort: placebo vs treated terciles within |r| quintiles
    fig, ax = plt.subplots(figsize=(8, 4.2))
    groups = ["no lev ETF", "Gamma low", "Gamma mid", "Gamma high"]
    cols = [GRAY, "#9ec3ee", "#5b9be3", BLUE]
    qs = sorted(ds["abs_r_quintile"].unique())
    w = 0.2
    for i, (g, c) in enumerate(zip(groups, cols)):
        sub = ds[ds["group"] == g].set_index("abs_r_quintile").reindex(qs)
        ax.bar(np.arange(len(qs)) + (i - 1.5) * w, sub["on_xs_bps"], width=w * 0.9, color=c, label=g)
    ax.axhline(0, color=INK, linewidth=0.8)
    ax.set_xticks(np.arange(len(qs)))
    ax.set_xticklabels(qs)
    ax.set_ylabel("Signed reversal, bps", color=MUTED)
    ax.set_title("Same-size moves: stocks with more lev-ETF Gamma vs stocks with none", loc="left")
    ax.legend(frameon=False, fontsize=9, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.08))
    _style(ax)
    fig.tight_layout()
    fig.savefig(REPORTS / "fig2_double_sort.png", dpi=150)
    plt.close(fig)

    # 3. cumulative P&L under cost scenarios
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(day.index, day["gross_pnl"].cumsum() / 1e6, color=GRAY, linewidth=2, label="gross")
    for (lab, dd), c in zip(day_by_cost.items(), [BLUE, ORANGE]):
        ax.plot(dd.index, dd["net_pnl"].cumsum() / 1e6, color=c, linewidth=2, label=lab)
    ax.axhline(0, color=INK, linewidth=0.8)
    ax.set_ylabel("Cumulative P&L, \\$M (on \\$5M capital)", color=MUTED)
    ax.set_title("Simulated fade of top-decile flow, exit next open, beta-hedged", loc="left")
    ax.legend(frameon=False, fontsize=9)
    _style(ax)
    fig.tight_layout()
    fig.savefig(REPORTS / "fig3_cum_pnl.png", dpi=150)
    plt.close(fig)

    # 4. aggregate single-stock Gamma through time
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(gam.index, gam / 1e9, color=BLUE, linewidth=2)
    ax.set_ylabel("$B per 100% move", color=MUTED)
    ax.set_title("Single-stock lev-ETF Gamma = sum A*L*(L-1), all underlyings", loc="left")
    _style(ax)
    fig.tight_layout()
    fig.savefig(REPORTS / "fig4_gamma_growth.png", dpi=150)
    plt.close(fig)

    # 5. per-year: treated top bucket vs matched placebo
    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = np.arange(len(mp_year))
    ax.bar(x - 0.2, mp_year["rev_treated"], width=0.38, color=BLUE, label="top-decile treated")
    ax.bar(x + 0.2, mp_year["rev_match"], width=0.38, color=GRAY, label="matched no-ETF stock")
    ax.axhline(0, color=INK, linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(mp_year.index.astype(str))
    ax.set_ylabel("Signed overnight reversal, bps", color=MUTED)
    ax.set_title("Top bucket vs matched placebo, by year", loc="left")
    ax.legend(frameon=False, fontsize=9)
    _style(ax)
    fig.tight_layout()
    fig.savefig(REPORTS / "fig5_placebo_by_year.png", dpi=150)
    plt.close(fig)


# ----------------------------------------------------------------------------- main
def main():
    sd, notes = load_sample()
    tr = sd[sd["treated"]].copy()
    dec, sdec, fbin = decile_sorts(tr)
    ds = double_sort(sd)
    reg = control_regressions(sd)
    cut = tr["absFR"].quantile(0.9)
    top = tr[tr["absFR"] >= cut].copy()
    mp = matched_placebo(sd, top)
    mp["year"] = mp["date"].dt.year
    mp_sum = {k: clustered_mean(mp[k], mp["date"]) for k in ("rev_treated", "rev_match", "diff", "diff_cc")}
    mp_year = mp.groupby("year")[["rev_treated", "rev_match", "diff"]].mean()
    mp_year_t = mp.groupby("year").apply(lambda g: clustered_mean(g["diff"], g["date"])["t"], include_groups=False)
    mp_year["diff_t"] = mp_year_t
    mp_year["n"] = mp.groupby("year").size()
    spl = splits(top, mp)

    sel, day = simulate(tr, fixed_bps=0.0, spread_mult=0.0, hedge_bps=0.0)
    sims = {}
    for lab, kw in {"net: half-spread + 2bps": dict(fixed_bps=2.0),
                    "net: half-spread + 5bps": dict(fixed_bps=5.0),
                    "net: full spread + 5bps (harsh)": dict(fixed_bps=5.0, spread_mult=2.0)}.items():
        s_sel, s_day = simulate(tr, **kw)
        sims[lab] = (s_sel, s_day)
    perf_tab = pd.DataFrame({"gross": perf(day, 5e6, "gross_pnl"),
                             **{k: perf(v[1], 5e6) for k, v in sims.items()}}).T
    yr = pd.DataFrame({k: v[1]["net_pnl"].groupby(v[1].index.year).sum() / 1e6 for k, v in sims.items()})
    yr["gross"] = day["gross_pnl"].groupby(day.index.year).sum() / 1e6
    conc = pd.DataFrame({"gross": concentration(sel, day, "gross_pnl"),
                         "net: half-spread + 2bps": concentration(sims["net: half-spread + 2bps"][0],
                                                                  sims["net: half-spread + 2bps"][1], "net_pnl")}).T
    trade_stats = {"trades": len(sel), "avg_gross_bps_per_trade_sizeweighted":
                   (sel["gross_pnl"].sum() / sel["size"].sum() * 1e4) if len(sel) else np.nan,
                   "avg_cost_bps_halfspread+2": sims["net: half-spread + 2bps"][0]["cost_bps"].mean(),
                   "median_assumed_half_spread_bps": sel["half_spread_bps"].median()}
    gam = tr.groupby("date")["Gamma"].sum()

    charts(dec, ds, day, {k: v[1] for k, v in list(sims.items())[:2]}, gam, mp_year)

    # write tables
    dec.to_csv(REPORTS / "t1_deciles_absFR.csv", index=False)
    sdec.to_csv(REPORTS / "t1b_deciles_signedFR.csv", index=False)
    fbin.to_csv(REPORTS / "t1c_fixed_thresholds.csv", index=False)
    ds.to_csv(REPORTS / "t2_double_sort.csv", index=False)
    reg.to_csv(REPORTS / "t3_regressions.csv", index=False)
    mp.to_csv(REPORTS / "t4_matched_pairs.csv", index=False)
    mp_year.to_csv(REPORTS / "t4b_matched_by_year.csv")
    spl.to_csv(REPORTS / "t5_splits_top_decile.csv", index=False)
    perf_tab.to_csv(REPORTS / "t6_pnl_performance.csv")
    yr.to_csv(REPORTS / "t6b_pnl_by_year.csv")
    conc.to_csv(REPORTS / "t7_concentration.csv")
    sel.to_csv(REPORTS / "t8_sim_trades_gross.csv", index=False)
    summary = {"notes": notes, "top_decile_cut_absFR": cut, "matched_placebo": mp_sum,
               "FR_winsor_bounds": reg.attrs.get("FR_winsor"), "trade_stats": trade_stats}
    (REPORTS / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
