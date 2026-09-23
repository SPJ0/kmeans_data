"""Predicted rebalance flow per stock from the latest fund state + an intraday return.

Fund state (A_{t-1}, E_{t-1}) comes from the newest holdings snapshot
(recorders/holdings.py). Exposure is taken from holdings when it is sane
(same sign as L and within 25% of L*A); otherwise E = L*A.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common.paths import CACHE, UNIVERSE
from flows.flow import rebalance_trade
from recorders import holdings


def fund_state(asof_before: str | None = None) -> pd.DataFrame:
    """One row per active fund: ticker, underlying, L, A_prev, E_prev, source columns."""
    u = pd.read_csv(UNIVERSE / "single_stock_universe.csv")
    u = u[u["include"] & (u["status"] == "active")][["ticker", "underlying", "leverage", "issuer"]]
    h = holdings.latest(asof_before)
    if len(h):
        h = h.copy()
        if "exposure_trusted" in h:
            h.loc[~h["exposure_trusted"].astype(bool), "exposure_usd"] = np.nan
        f = u.merge(h[["ticker", "net_assets", "exposure_usd", "asof", "source"]], on="ticker", how="left")
    else:
        f = u.assign(net_assets=np.nan, exposure_usd=np.nan, asof=None, source=None)
    # fallback for funds the scraper missed: last known AUM
    aum_p = CACHE / "current_aum.parquet"
    if aum_p.exists():
        aum = pd.read_parquet(aum_p).set_index("ticker")["total_assets"]
        miss = f["net_assets"].isna()
        f.loc[miss, "net_assets"] = f.loc[miss, "ticker"].map(aum)
        f.loc[miss & f["net_assets"].notna(), "source"] = "current_aum_cache"
    f = f.rename(columns={"leverage": "L", "net_assets": "A_prev"})
    target = f["L"] * f["A_prev"]
    sane = (np.sign(f["exposure_usd"]) == np.sign(f["L"])) & ((f["exposure_usd"] / target - 1).abs() < 0.25)
    f["E_prev"] = np.where(sane, f["exposure_usd"], target)
    f["E_source"] = np.where(sane, "holdings", "L*A")
    return f.dropna(subset=["A_prev"])


def predicted_flows(state: pd.DataFrame, r: pd.Series, adv: pd.Series | None = None) -> pd.DataFrame:
    """Aggregate predicted rebalance trade by underlying.

    r    intraday return of each underlying vs prior close (index = underlying)
    adv  20-day average dollar volume (index = underlying); FlowRatio uses 10% of it
    """
    s = state.copy()
    s["r"] = s["underlying"].map(r)
    s = s.dropna(subset=["r"])
    s["T"] = rebalance_trade(s["L"], s["A_prev"], s["r"], s["E_prev"])
    s["G"] = s["A_prev"] * s["L"] * (s["L"] - 1)
    out = s.groupby("underlying").agg(r=("r", "first"), flow=("T", "sum"), gamma=("G", "sum"),
                                      n_funds=("ticker", "size"), assets=("A_prev", "sum"))
    if adv is not None:
        out["auction_proxy"] = 0.10 * out.index.map(adv)
        out["flow_ratio"] = out["flow"] / out["auction_proxy"]
    else:
        out["auction_proxy"] = np.nan
        out["flow_ratio"] = np.nan
    key = out["flow_ratio"].abs().fillna(0) + 1e-12 * out["flow"].abs()
    return out.assign(rank_key=key).sort_values("rank_key", ascending=False).drop(columns="rank_key")
