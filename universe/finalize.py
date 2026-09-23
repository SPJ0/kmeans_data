"""Final single-stock LETF universe with validated price tickers and a daily
leverage schedule.

Problems this resolves (found in verify_leverage, 2026-09-23):
  * ticker reuse: a closed fund's ticker later used by another fund
    (NVDB: AXS 1.25x -> ProShares 2x; TSLI: GraniteShares -1x -> ProShares 2x)
  * SEC ticker errors: a series listed with another fund's ticker
    (T-REX inverse AMD/PLTR shown as AMDD/PLTD, which are Direxion -1x funds)
  * leverage changes: TSLQ -1x -> -2x, MSTX 1.75x -> 2x, CONI -1x -> -2x
  * weekly/monthly reset funds: no daily rebalance; excluded from daily flow

Rules:
  1. A series' active window is from 4 months before its first N-PORT period
     to 1 month after its last one (or to today if it has exact issuer data).
  2. A price ticker is attached to a series only on dates inside that window,
     and only if the rolling 60-day beta is within 0.35 of +/- a valid leverage
     and has the same sign as the parsed leverage.
  3. Daily leverage = rolling 20-day (centered) beta snapped to the valid grid
     where the price is attached and the fit is good (R^2 > 0.9); otherwise the
     parsed leverage. Leverage changes are announced in advance, so knowing the
     current leverage on a date is not look-ahead.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pipelines.prices import load_daily
from universe.build_universe import ROOT
from universe.verify_leverage import daily_returns

GRID = np.array([-3, -2, -1.75, -1.5, -1.25, -1, 1.25, 1.5, 1.75, 2, 3], dtype=float)


def snap(x: float) -> float:
    return float(GRID[np.argmin(np.abs(GRID - x))]) if np.isfinite(x) else np.nan


def leverage_schedule(price_ticker: str, underlying: str, parsed: float, window: tuple) -> pd.DataFrame:
    f, u = daily_returns(price_ticker), daily_returns(underlying)
    j = pd.concat([f.rename("f"), u.rename("u")], axis=1, join="inner").dropna()
    j = j[(j.index >= window[0]) & (j.index <= window[1]) & (j["f"].abs() < 0.8)]
    if len(j) < 20:
        return pd.DataFrame()
    fu = (j.f * j.u).rolling(21, center=True, min_periods=10).sum()
    uu = (j.u**2).rolling(21, center=True, min_periods=10).sum()
    ff = (j.f**2).rolling(21, center=True, min_periods=10).sum()
    beta = fu / uu
    r2 = fu**2 / (uu * ff)
    s = pd.DataFrame({"beta20": beta, "r2_20": r2})
    s["lev_est"] = s["beta20"].apply(snap)
    good = (s["r2_20"] > 0.9) & ((s["beta20"] - s["lev_est"]).abs() < 0.2) & (np.sign(s["lev_est"]) == np.sign(parsed))
    s["leverage"] = np.where(good, s["lev_est"], parsed)
    s["lev_src"] = np.where(good, "beta", "parsed")
    return s


def main():
    v = pd.read_csv(ROOT / "universe" / "letf_universe.csv")
    fd = pd.read_parquet(ROOT / "data" / "nport" / "nport_fund.parquet")
    act = fd.groupby("series_id").agg(nport_first=("rep_date", "min"), nport_last=("rep_date", "max"),
                                      nport_n=("rep_date", "size"), na_max=("net_assets", "max"))
    v = v.merge(act, left_on="series_id", right_index=True, how="left")
    from flows.assets import load_exact
    exact = load_exact()
    v["has_exact"] = v["price_ticker"].isin(exact.keys()) | v["ticker"].isin(exact.keys())
    v = v[(v["reset"] == "daily") & (v["nport_n"].notna() | v["has_exact"])].copy()

    today = pd.Timestamp("2026-09-23")
    lo = pd.to_datetime(v["nport_first"]) - pd.DateOffset(months=4)
    hi = pd.to_datetime(v["nport_last"]) + pd.DateOffset(months=1)
    v["active_from"] = lo.fillna(pd.to_datetime(v["first_date"]))
    v["active_to"] = hi.where(~v["has_exact"], today).fillna(today)

    sched = []
    for i, r in v.iterrows():
        pt = r.get("price_ticker")
        s = pd.DataFrame()
        if isinstance(pt, str) and np.sign(r.get("beta", np.nan)) == np.sign(r["leverage_parsed"]):
            s = leverage_schedule(pt, r["underlying"], r["leverage_parsed"], (r["active_from"], r["active_to"]))
        if s.empty:
            v.loc[i, "price_ticker"] = np.nan  # price not attributable to this series
            continue
        s["series_id"] = r["series_id"]
        sched.append(s.reset_index(names="date"))
        v.loc[i, "price_from"] = s.index.min()
        v.loc[i, "price_to"] = s.index.max()
        v.loc[i, "share_beta_leverage"] = (s["lev_src"] == "beta").mean()
        chg = s.loc[s["lev_src"] == "beta", "lev_est"]
        v.loc[i, "leverage_values_seen"] = ",".join(f"{x:g}" for x in sorted(chg.value_counts()[lambda c: c >= 10].index))
    sched = pd.concat(sched, ignore_index=True)
    sched.to_parquet(ROOT / "universe" / "leverage_schedule.parquet")
    keep = ["series_id", "series_name", "trust", "underlying", "leverage_parsed", "leverage_values_seen", "reset",
            "ticker", "price_ticker", "price_from", "price_to", "first_date", "last_date", "active_from", "active_to",
            "nport_first", "nport_last", "nport_n", "na_max", "has_exact", "beta", "r2", "lev_check",
            "share_beta_leverage", "all_names", "all_tickers"]
    v[keep].sort_values(["underlying", "leverage_parsed"]).to_csv(ROOT / "universe" / "letf_universe_final.csv", index=False)
    print(len(v), "series;", v["underlying"].nunique(), "underlyings;", v["price_ticker"].notna().sum(), "with attributed prices")


if __name__ == "__main__":
    main()
