"""Daily fund net-asset reconstruction between N-PORT snapshots.

Work in "shares" space so the day-to-day asset path is driven by the fund's
own return and only creations/redemptions need interpolating:

  P_t   NAV index = cumulative product of (1 + R_t), R_t the ETF's own daily
        return (Yahoo close-to-close) or, when Yahoo lacks the ETF, L * r_t of
        the underlying (fees/financing ignored).
  S_t   = A_t / P_t ("units").
  N-PORT gives A at each fiscal-quarter-end report date, and net creations
  (sales - redemptions) for each of the 3 months; those are spread evenly over
  the month's trading days: dS_t = flow_t / P_t.
  Between anchors k and k+1 the flow-driven path is scaled by a log-linear
  correction exp(lambda * tau) so it hits anchor k+1 exactly.
  After the last anchor the path is rolled forward with the fund return and no
  flows (``src='extrapolated'``), optionally re-anchored to a current AUM.

Every row carries ``src``: anchor / interp_flows / interp_loglinear / backcast /
extrapolated / current_anchor, so interpolated rows can be flagged.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SEED_ASSETS = 2e6   # typical seed capital at launch when nothing else is known


def _month_flows(nf: pd.DataFrame) -> pd.Series:
    """Net creations by calendar month (period) from the 3-month flow fields."""
    rows = {}
    for _, r in nf.iterrows():
        rd = r["report_date"]
        if pd.isna(rd):
            continue
        for m, back in ((1, 2), (2, 1), (3, 0)):
            s, red = r.get(f"sales_flow_mon{m}"), r.get(f"redemption_flow_mon{m}")
            if pd.notna(s) or pd.notna(red):
                per = (rd.to_period("M") - back)
                rows[per] = (0 if pd.isna(s) else s) - (0 if pd.isna(red) else red)
    return pd.Series(rows, dtype=float)


def reconstruct(dates: pd.DatetimeIndex, fund_ret: pd.Series, nf: pd.DataFrame, inception: pd.Timestamp,
                end: pd.Timestamp | None, current: tuple[pd.Timestamp, float] | None = None) -> pd.DataFrame:
    """Daily net assets for one fund.

    dates      trading calendar (underlying's dates)
    fund_ret   daily fund return indexed by date (NaN allowed -> 0)
    nf         this fund's N-PORT rows: report_date, net_assets, *_flow_mon*
    inception  first trading day; end: last trading day (None = still trading)
    current    optional (date, assets) anchor for the latest AUM
    """
    idx = dates[(dates >= inception) & ((dates <= end) if end is not None else True)]
    if len(idx) == 0:
        return pd.DataFrame(columns=["A", "src"])
    R = fund_ret.reindex(idx).fillna(0.0).clip(-0.95, 5.0)
    R.iloc[0] = 0.0
    P = (1 + R).cumprod()

    # anchors: last trading day on/before each report date
    anchors = []
    for _, r in nf.dropna(subset=["report_date", "net_assets"]).iterrows():
        pos = idx.searchsorted(r["report_date"], side="right") - 1
        if pos >= 0 and r["net_assets"] > 0:
            anchors.append((pos, float(r["net_assets"]), "anchor"))
    if current is not None and current[1] and current[1] > 0:
        pos = idx.searchsorted(current[0], side="right") - 1
        if pos >= 0 and (not anchors or pos > anchors[-1][0]):
            anchors.append((pos, float(current[1]), "current_anchor"))
    anchors = sorted({a[0]: a for a in anchors}.values())

    # daily flow in units from monthly net creations
    mf = _month_flows(nf)
    per = idx.to_period("M")
    ndays = pd.Series(per).map(pd.Series(per).value_counts())
    flow = pd.Series(per).map(mf).fillna(np.nan).to_numpy() / ndays.to_numpy()
    has_flow = ~np.isnan(flow)
    dS = np.where(has_flow, flow, 0.0) / P.to_numpy()

    n = len(idx)
    S = np.full(n, np.nan)
    src = np.array([""] * n, dtype=object)
    if not anchors:
        S[:] = SEED_ASSETS / P.iloc[0] if len(P) else np.nan
        src[:] = "no_anchor_seed"
        A = S * P.to_numpy()
        return pd.DataFrame({"A": A, "src": src}, index=idx)

    # before first anchor: back out flows, else log-linear from seed at inception
    p0, a0, s0 = anchors[0]
    S[p0] = a0 / P.iloc[p0]
    src[p0] = s0
    for t in range(p0 - 1, -1, -1):
        S[t] = S[t + 1] - dS[t + 1]
        src[t] = "backcast"
    if p0 > 0:
        floor = SEED_ASSETS / P.to_numpy()[: p0 + 1]
        bad = (S[: p0 + 1] <= 0) | ~np.isfinite(S[: p0 + 1])
        if bad.any() or not has_flow[: p0 + 1].any():
            # fall back to log-linear from seed at inception
            lo, hi = np.log(floor[0]), np.log(S[p0])
            tau = np.arange(p0 + 1) / max(p0, 1)
            S[: p0 + 1] = np.exp(lo + (hi - lo) * tau)
            src[:p0] = "backcast_loglinear"
            src[p0] = s0

    # between anchors
    for (pa, aa, _), (pb, ab, sb) in zip(anchors[:-1], anchors[1:]):
        Sa, Sb = aa / P.iloc[pa], ab / P.iloc[pb]
        seg = np.arange(pa, pb + 1)
        tau = (seg - pa) / (pb - pa)
        sim = Sa + np.concatenate([[0.0], np.cumsum(dS[pa + 1: pb + 1])])
        if has_flow[pa + 1: pb + 1].any() and (sim > 0).all():
            lam = np.log(Sb / sim[-1])
            S[seg] = sim * np.exp(lam * tau)
            src[pa + 1: pb] = "interp_flows"
        else:
            S[seg] = np.exp(np.log(Sa) + (np.log(Sb) - np.log(Sa)) * tau)
            src[pa + 1: pb] = "interp_loglinear"
        src[pb] = sb

    # after last anchor: no flows assumed
    pl = anchors[-1][0]
    S[pl + 1:] = S[pl]
    src[pl + 1:] = "extrapolated"
    A = S * P.to_numpy()
    return pd.DataFrame({"A": A, "src": src}, index=idx)


def holdout_errors(dates, fund_ret: pd.Series, nf: pd.DataFrame) -> pd.DataFrame:
    """Predict each anchor from the previous one: with the monthly flows and with no flows.

    Measures how far off the reconstruction is between snapshots, and how much
    ignoring creations/redemptions would cost.
    """
    nf = nf.dropna(subset=["report_date", "net_assets"]).sort_values("report_date")
    nf = nf[nf["net_assets"] > 0]
    out = []
    idx = pd.DatetimeIndex(dates)
    R = fund_ret.reindex(idx).fillna(0.0).clip(-0.95, 5.0)
    mf = _month_flows(nf)
    for (_, a), (_, b) in zip(nf.iloc[:-1].iterrows(), nf.iloc[1:].iterrows()):
        pa = idx.searchsorted(a["report_date"], side="right") - 1
        pb = idx.searchsorted(b["report_date"], side="right") - 1
        if pa < 0 or pb <= pa:
            continue
        seg = R.iloc[pa + 1: pb + 1]
        growth = float((1 + seg).prod())
        no_flow = a["net_assets"] * growth
        # with flows: each day's flow compounds from its date to the end
        per = seg.index.to_period("M")
        nd = pd.Series(per).map(pd.Series(per).value_counts()).to_numpy()
        f = pd.Series(per).map(mf).fillna(0.0).to_numpy() / nd
        tail = (1 + seg[::-1]).cumprod()[::-1].shift(-1).fillna(1.0).to_numpy()
        with_flow = no_flow + float((f * tail).sum())
        out.append({"report_date": b["report_date"], "actual": b["net_assets"], "pred_no_flow": no_flow,
                    "pred_with_flow": with_flow})
    return pd.DataFrame(out)
