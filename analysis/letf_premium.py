"""Handoff item 10: is the dislocation in the LETF's own closing price?

Hypothesis: on big-move days retail trades single-stock LETFs heavily; if LETF
market makers don't fully arbitrage into the close, the LETF closes at a
premium/discount to NAV that reverts the next day. Trade: take the other side
of the premium at the close, hedge with L x underlying, unwind next day.

Measures
  exact premium (GraniteShares / ProShares funds with daily NAV):
      prem_t = ln(fund close / NAV_t)
  proxy premium change (all funds with attributable prices):
      e_t = ln(1 + r_fund,t) - ln(1 + L * r_und,t)
  e_t = Delta prem_t + daily fee/financing drift, so reversal shows up as
  negative autocorrelation of e and as -sign(prem_t) * Delta prem_{t+1} > 0.

Caveat: Yahoo's ETF close is a trade price, not a bid/ask midpoint, so part of
any "premium" can be bid-ask bounce, which reverts but is not capturable.
Compare magnitudes to typical spreads before reading anything as tradeable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from analysis.panel import HOLDOUT
from analysis.stats import clustered_mean, fe_ols
from flows.assets import load_exact
from pipelines.prices import load_daily
from universe.build_universe import ROOT

REP = ROOT / "reports"
START = pd.Timestamp("2022-07-01")


def fund_frame(row: pd.Series, sched: pd.DataFrame, nav: pd.DataFrame | None) -> pd.DataFrame:
    t, u = row["price_ticker"], row["underlying"]
    f, d = load_daily(t), load_daily(u)
    if f.empty or d.empty:
        return pd.DataFrame()
    lo, hi = pd.Timestamp(row["price_from"]), pd.Timestamp(row["price_to"])
    f = f[(f.index >= max(lo, START)) & (f.index <= hi) & (f.index < HOLDOUT) & ~f["bad"]]
    out = pd.DataFrame(index=f.index)
    out["close"] = f["Close"]
    out["dvol_fund"] = f["Close"] * f["Volume"]
    lev = sched.loc[sched["series_id"] == row["series_id"]].set_index("date")["leverage"]
    out["L"] = lev.reindex(out.index).ffill().bfill() if len(lev) else row["leverage_parsed"]
    ru = d["Close"].pct_change(fill_method=None).reindex(out.index)
    rf = f["Close"].pct_change(fill_method=None)
    # only use consecutive trading days for both
    out["r_und"] = ru
    out["r_fund"] = rf
    out["e"] = np.log1p(rf) - np.log1p(out["L"] * ru)
    out["e_next"] = out["e"].shift(-1)
    out["date_next"] = pd.Series(out.index, index=out.index).shift(-1)
    if nav is not None and len(nav):
        n = nav.drop_duplicates("date", keep="last").set_index("date")["nav"].reindex(out.index)
        out["prem"] = np.log(out["close"] / n)
        out["prem_next"] = out["prem"].shift(-1)
    out["ticker"], out["underlying"], out["series_id"] = t, u, row["series_id"]
    out = out[out["date_next"] < HOLDOUT]
    return out.reset_index(names="date")


def load_navs() -> dict[str, pd.DataFrame]:
    navs = {}
    g = pd.read_parquet(ROOT / "data" / "raw" / "issuer" / "graniteshares" / "graniteshares_nav_aum.parquet")
    for t, x in g.groupby("ticker"):
        navs[t] = x[["date", "nav"]]
    p = pd.read_parquet(ROOT / "data" / "raw" / "issuer" / "proshares" / "historical_nav_2026-09-22.parquet")
    for t, x in p.groupby("ticker"):
        navs[t] = x[["date", "nav"]]
    return navs


def main():
    u = pd.read_csv(ROOT / "universe" / "letf_universe_final.csv")
    u = u[u["price_ticker"].notna()]
    sched = pd.read_parquet(ROOT / "universe" / "leverage_schedule.parquet")
    navs = load_navs()
    fd = pd.read_parquet(ROOT / "data" / "panel" / "fund_day.parquet")[["date", "series_id", "aum_prev"]]
    g = pd.read_parquet(ROOT / "data" / "panel" / "stock_gamma.parquet")[["date", "underlying", "gamma"]]
    parts = [fund_frame(r, sched, navs.get(r["price_ticker"])) for _, r in u.iterrows()]
    p = pd.concat([x for x in parts if len(x)], ignore_index=True)
    p = p.merge(fd, on=["date", "series_id"], how="left").merge(g, on=["date", "underlying"], how="left")
    p = p[p["e"].notna() & p["e_next"].notna() & (p["e"].abs() < 0.2) & (p["e_next"].abs() < 0.2)]
    p["abs_move"] = (p["L"] * p["r_und"]).abs()
    p["small_fund"] = p["aum_prev"] < 50e6
    p["big_move"] = p["abs_move"] >= p.groupby("ticker")["abs_move"].transform(lambda s: s.quantile(0.9))
    rows = []

    # --- A. exact premium funds
    x = p[p["prem"].notna() & p["prem_next"].notna() & (p["prem"].abs() < 0.2)].copy()
    x["dprem_next"] = x["prem_next"] - x["prem"]
    # validate proxy: e_t vs exact Delta prem_t
    x["dprem"] = x.groupby("ticker")["prem"].diff()
    v = x.dropna(subset=["dprem"])
    rows.append(dict(item="proxy validation corr(e_t, dPrem_t) exact funds", value=v["e"].corr(v["dprem"]), n=len(v)))
    rows.append(dict(item="exact: median |prem| bps", value=x["prem"].abs().median() * 1e4, n=len(x)))
    rows.append(dict(item="exact: p90 |prem| bps", value=x["prem"].abs().quantile(0.9) * 1e4, n=len(x)))
    ac = x.groupby("ticker").apply(lambda g: g["prem"].autocorr(), include_groups=False)
    rows.append(dict(item="exact: median AR(1) of premium across funds", value=ac.median(), n=len(ac)))
    for k in (10, 25, 50, 100):
        s = x[x["prem"].abs() * 1e4 >= k]
        m, se, n = clustered_mean(-np.sign(s["prem"]) * s["dprem_next"] * 1e4, s["date"])
        rows.append(dict(item=f"exact: next-day premium reversion when |prem|>={k}bps (bps)", value=m, se=se, n=n,
                         n_funds=s["ticker"].nunique(), share_small=s["small_fund"].mean()))

    # --- B. proxy, all funds: does e_t reverse, and more on big-move days?
    for lab, s in (("all", p), ("big-move days (top 10% |L*r|)", p[p["big_move"]]),
                   ("funds AUM>=$50M", p[~p["small_fund"]]), ("funds AUM<$50M", p[p["small_fund"]])):
        r = fe_ols(s, "e_next", ["e"], fe="date", cluster=("date", "ticker"))
        rows.append(dict(item=f"proxy: slope of e_(t+1) on e_t [{lab}]", value=r.loc["e", "coef"], se=r.loc["e", "se"],
                         n=int(r.loc["e", "n"])))
    for k in (25, 50, 100):
        for lab, s in (("big funds", p[~p["small_fund"]]), ("small funds", p[p["small_fund"]])):
            s = s[s["e"].abs() * 1e4 >= k]
            m, se, n = clustered_mean(-np.sign(s["e"]) * s["e_next"] * 1e4, s["date"])
            rows.append(dict(item=f"proxy: next-day reversal when |e_t|>={k}bps, {lab} (bps)", value=m, se=se, n=n,
                             n_funds=s["ticker"].nunique()))
    # premium vs underlying move direction: do LETFs close rich in the direction of the move?
    for lab, s in (("exact", x), ("proxy", p)):
        col = "prem" if lab == "exact" else "e"
        s = s[s["big_move"]]
        m, se, n = clustered_mean(np.sign(s["L"] * s["r_und"]) * s[col] * 1e4, s["date"])
        rows.append(dict(item=f"{lab}: premium signed by fund move on big-move days (bps)", value=m, se=se, n=n))
    out = pd.DataFrame(rows)
    out.to_csv(REP / "letf_premium.csv", index=False)
    pd.set_option("display.width", 220, "display.max_colwidth", 80)
    print(out.to_string(float_format=lambda v: f"{v:,.3f}"))
    # per-fund exact premium summary for the biggest funds
    s = x.groupby("ticker").agg(n=("prem", "size"), med_abs_prem_bps=("prem", lambda z: z.abs().median() * 1e4),
                                ar1=("prem", lambda z: z.autocorr()), aum=("aum_prev", "median"))
    print(s.sort_values("aum", ascending=False).head(15).round(2).to_string())


if __name__ == "__main__":
    main()
