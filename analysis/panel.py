"""Stock-day analysis panel: features known at (or before) the close of day t,
and outcomes after the close of day t.

HOLD-OUT: any outcome whose window touches a date >= HOLDOUT is set to NaN here,
so no downstream analysis can see hold-out outcomes by accident.

Timing conventions (day t):
  r_t        close(t-1) -> close(t), split-adjusted price return (what LETFs rebalance on)
  r_pre      close(t-1) -> 15:30 price (open of Yahoo's 15:30 hourly bar)
  r_last30   15:30 price -> official close(t)        [same-day "pressure" outcome]
  on1        close(t) -> open(t+1), dividend-adjusted  [overnight]
  oc1        open(t+1) -> close(t+1)
  cc1        close(t) -> close(t+1), dividend-adjusted
  cc5        close(t) -> close(t+5), dividend-adjusted
  adv20      mean dollar volume over t-20..t-1 (lagged, known before t)
  vol60      std of daily returns over t-60..t-1
  beta       60-day beta to QQQ over t-60..t-1; *_x columns are beta-adjusted
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from pipelines.prices import load_daily, load_hourly
from universe.build_universe import ROOT

HOLDOUT = pd.Timestamp("2026-03-23")
START = pd.Timestamp("2019-01-01")
BENCH = "QQQ"


def price_1530(ticker: str) -> pd.Series:
    h = load_hourly(ticker)
    if h.empty:
        return pd.Series(dtype=float)
    b = h[(h.index.hour == 15) & (h.index.minute == 30)]
    s = b["Open"].copy()
    s.index = b.index.tz_localize(None).normalize()
    return s[~s.index.duplicated()]


def stock_features(ticker: str, bench: pd.DataFrame | None = None) -> pd.DataFrame:
    d = load_daily(ticker)
    if d.empty or len(d) < 80:
        return pd.DataFrame()
    d = d[d.index >= START - pd.Timedelta(days=150)].copy()
    d.loc[d["bad"], ["Open", "Close", "Adj Close"]] = np.nan
    f = d["Adj Close"] / d["Close"]
    out = pd.DataFrame(index=d.index)
    out["close"] = d["Close"]
    out["r_t"] = d["Close"].pct_change(fill_method=None)
    ar = d["Adj Close"].pct_change(fill_method=None)
    out["r_adj"] = ar
    dv = d["Close"] * d["Volume"]
    out["dvol"] = dv
    out["adv20"] = dv.rolling(20, min_periods=15).mean().shift(1)
    out["vol60"] = ar.rolling(60, min_periods=40).std().shift(1)
    out["on1"] = (d["Open"].shift(-1) * f.shift(-1)) / (d["Close"] * f) - 1
    out["oc1"] = d["Close"].shift(-1) / d["Open"].shift(-1) - 1
    out["cc1"] = d["Adj Close"].shift(-1) / d["Adj Close"] - 1
    out["cc5"] = d["Adj Close"].shift(-5) / d["Adj Close"] - 1
    out["gap_t"] = (d["Open"] * f) / (d["Close"].shift(1) * f.shift(1)) - 1  # overnight into t
    p = price_1530(ticker).reindex(out.index)
    out["p1530"] = p
    out["r_pre"] = p / d["Close"].shift(1) - 1
    out["r_last30"] = d["Close"] / p - 1
    # dates of t+1 and t+5 for hold-out masking
    idx = pd.Series(out.index, index=out.index)
    out["d_next"] = idx.shift(-1)
    out["d_next5"] = idx.shift(-5)
    if bench is not None:
        b = bench.reindex(out.index)
        cov = ar.rolling(60, min_periods=40).cov(b["r_adj"])
        var = b["r_adj"].rolling(60, min_periods=40).var()
        out["beta"] = (cov / var).shift(1).clip(-1, 5)
        for c in ("on1", "oc1", "cc1", "cc5", "r_last30", "r_pre", "r_t"):
            out[c + "_x"] = out[c] - out["beta"] * b[c]
    out = out[out.index >= START]
    # hold-out masking
    for c in [c for c in out.columns if c.startswith(("on1", "oc1", "cc1"))]:
        out.loc[~(out["d_next"] < HOLDOUT), c] = np.nan
    for c in [c for c in out.columns if c.startswith("cc5")]:
        out.loc[~(out["d_next5"] < HOLDOUT), c] = np.nan
    for c in [c for c in out.columns if c.startswith(("r_last30", "r_pre", "r_t", "r_adj"))]:
        out.loc[out.index >= HOLDOUT, c] = np.nan
    out = out[out.index < HOLDOUT]
    out["ticker"] = ticker
    return out.drop(columns=["d_next", "d_next5"])


def bench_frame() -> pd.DataFrame:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        b = stock_features(BENCH)
    return b[["r_adj", "on1", "oc1", "cc1", "cc5", "r_last30", "r_pre", "r_t"]]


def build(tickers: list[str], min_adv: float = 0.0) -> pd.DataFrame:
    bench = bench_frame()
    parts = []
    for t in tickers:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            f = stock_features(t, bench)
        if f.empty:
            continue
        if min_adv:
            f = f[f["adv20"] >= min_adv]
        parts.append(f.reset_index().rename(columns={"index": "date"}))
    p = pd.concat(parts, ignore_index=True)
    for c in p.columns:
        if p[c].dtype == "float64" and c not in ("adv20", "dvol"):
            p[c] = p[c].astype("float32")
    return p


def attach_flows(p: pd.DataFrame) -> pd.DataFrame:
    g = pd.read_parquet(ROOT / "data" / "panel" / "stock_gamma.parquet").rename(columns={"underlying": "ticker"})
    p = p.merge(g, on=["date", "ticker"], how="left")
    p["gamma"] = p["gamma"].fillna(0.0)
    p["n_funds"] = p["n_funds"].fillna(0).astype(int)
    p["flow"] = p["gamma"] * p["r_t"]  # rebalance flow, on-target approximation
    p["flow_pre"] = p["gamma"] * p["r_pre"]  # flow predicted from the 15:30 price
    p["g_adv"] = p["gamma"] / p["adv20"]  # flow per unit return, in ADVs
    p["flow_adv"] = p["flow"] / p["adv20"]
    p["flow_pre_adv"] = p["flow_pre"] / p["adv20"]
    return p


if __name__ == "__main__":
    import sys

    which = sys.argv[1] if len(sys.argv) > 1 else "treated"
    out = ROOT / "data" / "panel"
    if which == "treated":
        g = pd.read_parquet(out / "stock_gamma.parquet")
        tick = sorted(g["underlying"].unique())
        p = attach_flows(build(tick))
        p.to_parquet(out / "panel_treated.parquet")
    else:
        from pipelines.fetch_control_prices import control_tickers

        g = pd.read_parquet(out / "stock_gamma.parquet")
        tick = sorted(set(control_tickers()) | set(g["underlying"].unique()))
        p = attach_flows(build(tick, min_adv=20e6))
        p.to_parquet(out / "panel_all.parquet")
    print(which, len(p), p["ticker"].nunique(), p["date"].min(), p["date"].max())
