"""Reconstruct daily fund assets (AUM) for leveraged ETFs.

Sources, best first:
  exact  -- issuer daily AUM (GraniteShares API, ProShares history file)
  interp -- quarterly N-PORT net assets converted to share-count anchors, with
            the monthly N-PORT dollar flows (sales - redemptions) shaping the
            share path between anchors; AUM = shares x daily NAV proxy
  extrap -- after the last anchor: shares held flat

N-PORT's own monthly returns are NOT used: they are unreliable (some filings
report decimals instead of percent; some are not split-adjusted, e.g. MULL
shows -95% in a month its assets grew 8x). Returns come from our NAV proxy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pipelines.prices import load_daily
from universe.build_universe import ROOT

NPORT = ROOT / "data" / "nport" / "nport_fund.parquet"


def nav_proxy(price_ticker: str | None, underlying: str, leverage: pd.Series | float,
              price_window: tuple | None = None) -> pd.Series:
    """Daily NAV proxy: fund's adjusted close where attributable, spliced with a
    synthetic (1 + L * underlying return) path elsewhere (e.g. closed funds)."""
    u = load_daily(underlying)
    ur = u["Close"].pct_change().fillna(0.0)
    L = leverage.reindex(ur.index).ffill().bfill() if isinstance(leverage, pd.Series) else leverage
    synth = (1 + L * ur).clip(lower=0.01).cumprod()
    if isinstance(price_ticker, str):
        f = load_daily(price_ticker)
        if not f.empty:
            fp = f.loc[~f["bad"], "Adj Close"].reindex(synth.index)
            if price_window is not None:
                fp = fp[(fp.index >= price_window[0]) & (fp.index <= price_window[1])].reindex(synth.index)
            # synthetic returns fill gaps; chain so levels stay continuous
            fr = fp.pct_change()
            sr = synth.pct_change()
            first = fp.first_valid_index()
            if first is not None:
                r = fr.where(fr.notna() & fp.notna() & fp.shift().notna(), sr).fillna(0.0)
                out = (1 + r).cumprod()
                return out * fp[first] / out[first]
    return synth


def share_path(f: pd.DataFrame, nav: pd.Series, launch: pd.Timestamp | None) -> pd.Series:
    """Daily shares outstanding from quarterly N-PORT anchors + monthly flows.

    Between the previous anchor S0 and the quarter-end anchor S3, month-end
    shares are S0 + cumulative (net flow / average NAV proxy in that month);
    the residual S3 - S(m3) is then spread linearly over the three months.
    Before the first filing the fund starts from zero shares at launch.
    Month-ends are joined by linear interpolation.
    """
    idx = nav.index
    f = f.dropna(subset=["net_assets"]).sort_values("rep_date").drop_duplicates("rep_date", keep="last")
    pts: dict[pd.Timestamp, float] = {}

    def last_td(d):
        k = idx[idx <= d]
        return k[-1] if len(k) and (d - k[-1]).days <= 7 else None

    prev = None  # (date, shares)
    if launch is not None and len(idx):
        prev = (idx[0], 0.0)
        pts[idx[0]] = 0.0
    for _, r in f.iterrows():
        qe = pd.Timestamp(r["rep_date"]) + pd.offsets.MonthEnd(0)
        d3 = last_td(qe)
        if d3 is None:
            continue
        s3 = r["net_assets"] / nav[d3]
        path, cum = [], (prev[1] if prev else np.nan)
        for k, lag in ((1, 2), (2, 1), (3, 0)):
            me = qe - pd.offsets.MonthEnd(lag)
            ms = me - pd.offsets.MonthBegin(1)
            navm = nav[(nav.index >= ms) & (nav.index <= me)].mean()
            flow = (r.get(f"sales{k}") or 0.0) - (r.get(f"redemption{k}") or 0.0) + (r.get(f"reinvest{k}") or 0.0)
            cum = cum + (flow / navm if np.isfinite(navm) and navm > 0 else 0.0)
            path.append((me, cum))
        if prev is not None and np.isfinite(path[-1][1]):
            gap = s3 - path[-1][1]
            for k, (me, sh) in enumerate(path[:-1], start=1):
                d = last_td(me)
                if d is not None and d > prev[0]:
                    pts[d] = max(sh + gap * k / 3.0, 0.0)
        pts[d3] = s3
        prev = (d3, s3)
    sh = pd.Series(np.nan, index=idx)
    if pts:
        a = pd.Series(pts).sort_index()
        sh.loc[a.index] = a.values
        sh = sh.interpolate(method="time", limit_area="inside")
    return sh


def daily_assets(series: pd.Series, fd: pd.DataFrame, exact: pd.DataFrame | None,
                 leverage: pd.Series | float) -> pd.DataFrame:
    """Daily end-of-day AUM for one fund (row of the final universe).

    ``leverage`` is the fund's daily leverage schedule (or a constant).
    """
    window = None
    if isinstance(series.get("price_ticker"), str):
        window = (pd.Timestamp(series["price_from"]), pd.Timestamp(series["price_to"]))
    nav = nav_proxy(series.get("price_ticker"), series["underlying"], leverage, window)
    start = pd.Timestamp(series["active_from"])
    end = pd.Timestamp(series["active_to"])
    launch = None
    if isinstance(series.get("price_ticker"), str):
        start = max(start, pd.Timestamp(series["price_from"]) - pd.Timedelta(days=5))
        launch = start
    idx = nav.index[(nav.index >= start) & (nav.index <= end)]
    out = pd.DataFrame(index=idx)
    out["nav_proxy"] = nav.reindex(idx)
    shares = share_path(fd[fd["series_id"] == series["series_id"]], out["nav_proxy"], launch)
    out["aum_source"] = np.where(shares.notna(), "interp", "none")
    last_anchor = shares.last_valid_index()
    if last_anchor is not None:
        out.loc[out.index > last_anchor, "aum_source"] = "extrap"
        shares = shares.ffill()
    out["shares_proxy"] = shares
    out["aum_interp"] = shares * out["nav_proxy"]
    out["aum"] = out["aum_interp"]

    if exact is not None and len(exact):
        e = exact.drop_duplicates("date", keep="last").set_index("date")["aum"]
        e = e[e > 0].reindex(idx)
        has = e.notna()
        out.loc[has, "aum"] = e[has]
        out.loc[has, "aum_source"] = "exact"
    out["series_id"] = series["series_id"]
    out["underlying"] = series["underlying"]
    out.index.name = "date"
    return out.reset_index()


def load_exact() -> dict[str, pd.DataFrame]:
    ex: dict[str, pd.DataFrame] = {}
    gs = ROOT / "data" / "raw" / "issuer" / "graniteshares" / "graniteshares_nav_aum.parquet"
    if gs.exists():
        g = pd.read_parquet(gs)
        for t, d in g.groupby("ticker"):
            ex[t] = d[["date", "aum"]]
    ps = ROOT / "data" / "raw" / "issuer" / "proshares" / "historical_nav_2026-09-22.parquet"
    if ps.exists():
        p = pd.read_parquet(ps)
        for t, d in p.groupby("ticker"):
            ex[t] = d[["date", "aum"]]
    return ex
