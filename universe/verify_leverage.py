"""Verify parsed leverage against realized returns and add trading-history fields.

For a daily-reset fund, fund close-to-close return ~= L * underlying return. We
regress (no intercept) fund on underlying returns, full sample and in rolling
60-day windows (to catch leverage changes such as MSTX 1.75x -> 2x), and use
first/last Yahoo price dates as inception/last-trade dates.

Output: universe/letf_universe.csv — the working universe (single stocks).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pipelines.prices import load_daily
from universe.build_universe import ROOT


def daily_returns(ticker: str) -> pd.Series:
    d = load_daily(ticker)
    if d.empty:
        return pd.Series(dtype=float)
    d = d[~d["bad"]]
    return d["Adj Close"].pct_change().dropna()


def fit(fund: pd.Series, und: pd.Series) -> dict:
    j = pd.concat([fund.rename("f"), und.rename("u")], axis=1, join="inner").dropna()
    # Drop fund-side outliers from stale prints / reverse splits the adjuster missed.
    j = j[(j["f"].abs() < 0.8)]
    if len(j) < 20:
        return dict(n_obs=len(j))
    beta = (j.f * j.u).sum() / (j.u**2).sum()
    resid = j.f - beta * j.u
    r2 = 1 - (resid**2).sum() / ((j.f - j.f.mean()) ** 2).sum()
    roll = (j.f * j.u).rolling(60).sum() / (j.u**2).rolling(60).sum()
    return dict(
        n_obs=len(j), beta=beta, r2=r2, resid_sd=resid.std(),
        beta_first60=roll.dropna().iloc[0] if roll.notna().any() else np.nan,
        beta_last60=roll.dropna().iloc[-1] if roll.notna().any() else np.nan,
        beta_roll_min=roll.min(), beta_roll_max=roll.max(),
    )


def main() -> pd.DataFrame:
    u = pd.read_csv(ROOT / "universe" / "letf_universe_raw.csv")
    s = u[(u["category"] == "single_stock") & u["has_ticker"]].copy()
    und_cache: dict[str, pd.Series] = {}
    rows = []
    for _, f in s.iterrows():
        und = f["underlying"]
        if und not in und_cache:
            und_cache[und] = daily_returns(und)
        # a series may have had several tickers over time; use the one with the most history
        best = None
        for t in [x.strip() for x in str(f["all_tickers"]).split("|")]:
            px = load_daily(t)
            if px.empty:
                continue
            res = fit(daily_returns(t), und_cache[und])
            res.update(price_ticker=t, first_date=px.index.min().date(), last_date=px.index.max().date(),
                       med_dollar_vol=float((px["Close"] * px["Volume"]).tail(60).median()))
            if best is None or res.get("n_obs", 0) > best.get("n_obs", 0):
                best = res
        rows.append({**f.to_dict(), **(best or {})})
    v = pd.DataFrame(rows)
    v["lev_check"] = "no_prices"
    has = v["beta"].notna()
    ok = has & ((v["beta"] - v["leverage_parsed"]).abs() <= 0.25) & (v["r2"] > 0.8)
    v.loc[has, "lev_check"] = "MISMATCH"
    v.loc[ok, "lev_check"] = "ok"
    # A rolling-beta range wider than 0.4 flags a leverage change (or swap-capacity episode).
    v.loc[has & ((v["beta_roll_max"] - v["beta_roll_min"]) > 0.4), "lev_check"] += "+beta_varies"
    return v


if __name__ == "__main__":
    v = main()
    v.to_csv(ROOT / "universe" / "letf_universe.csv", index=False)
    print(v["lev_check"].value_counts())
