"""Build fund-day and stock-day leveraged-ETF panels.

fund_day.parquet  -- date, series_id, underlying, leverage, aum, aum_prev, aum_source
stock_gamma.parquet -- date, underlying, gamma (= sum A_{t-1} L (L-1), known before
                       the open of day t), aum_long/aum_inverse, n_funds, share of
                       gamma from exact-AUM funds and from interpolated funds.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from flows.assets import daily_assets, load_exact
from flows.rebalance import multiplier
from universe.build_universe import ROOT

OUT = ROOT / "data" / "panel"


def build_fund_day() -> pd.DataFrame:
    u = pd.read_csv(ROOT / "universe" / "letf_universe_final.csv")
    fd = pd.read_parquet(ROOT / "data" / "nport" / "nport_fund.parquet")
    sched = pd.read_parquet(ROOT / "universe" / "leverage_schedule.parquet")
    ex = load_exact()
    parts = []
    for _, s in u.iterrows():
        lev = sched.loc[sched["series_id"] == s["series_id"]].set_index("date")["leverage"]
        t = s["price_ticker"] if isinstance(s["price_ticker"], str) else s["ticker"]
        exact = ex.get(t) if isinstance(t, str) and (isinstance(s["price_ticker"], str) or s["has_exact"]) else None
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            d = daily_assets(s, fd, exact, lev if len(lev) else float(s["leverage_parsed"]))
        if d.empty:
            continue
        L = lev.reindex(d["date"]).ffill().bfill().values if len(lev) else np.full(len(d), s["leverage_parsed"])
        d["leverage"] = L
        d["aum_prev"] = d["aum"].shift(1)
        d["src_prev"] = d["aum_source"].shift(1)
        parts.append(d[["date", "series_id", "underlying", "leverage", "aum", "aum_prev", "aum_source", "src_prev"]])
    f = pd.concat(parts, ignore_index=True)
    f = f[f["aum_prev"].notna() & (f["aum_prev"] > 0)]
    return f


def build_stock_gamma(f: pd.DataFrame) -> pd.DataFrame:
    f = f.copy()
    f["gamma"] = f["aum_prev"] * multiplier(f["leverage"])
    f["g_exact"] = np.where(f["src_prev"] == "exact", f["gamma"], 0.0)
    f["g_extrap"] = np.where(f["src_prev"] == "extrap", f["gamma"], 0.0)
    f["aum_long"] = np.where(f["leverage"] > 0, f["aum_prev"], 0.0)
    f["aum_inverse"] = np.where(f["leverage"] < 0, f["aum_prev"], 0.0)
    f["g_inverse"] = np.where(f["leverage"] < 0, f["gamma"], 0.0)
    g = f.groupby(["date", "underlying"]).agg(
        gamma=("gamma", "sum"), g_exact=("g_exact", "sum"), g_extrap=("g_extrap", "sum"),
        g_inverse=("g_inverse", "sum"), aum_long=("aum_long", "sum"), aum_inverse=("aum_inverse", "sum"),
        n_funds=("series_id", "nunique"),
    ).reset_index()
    for c in ("g_exact", "g_extrap", "g_inverse"):
        g["share_" + c[2:]] = g[c] / g["gamma"]
    return g.drop(columns=["g_exact", "g_extrap", "g_inverse"])


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    f = build_fund_day()
    f.to_parquet(OUT / "fund_day.parquet")
    g = build_stock_gamma(f)
    g.to_parquet(OUT / "stock_gamma.parquet")
    print(f"fund-days {len(f):,}; stock-days {len(g):,}; underlyings {g['underlying'].nunique()}")
    print(f.groupby("aum_source")["aum_prev"].sum() / f["aum_prev"].sum())
