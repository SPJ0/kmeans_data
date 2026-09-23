"""Build the fund-day and stock-day panels for the Phase A1 test.

Inputs (all cached): universe/single_stock_universe.csv, N-PORT extracts,
Yahoo prices, current AUM, earnings dates.

Outputs
  data/cache/fund_days.parquet    fund x day: L, A_prev, r, T, asset source flags
  data/cache/stock_days.parquet   stock x day: Flow, Gamma, FlowRatio, outcomes,
                                  betas, flags (treated and placebo stocks)
  reports/asset_validation.csv    reconstruction checks per fund
  reports/realized_leverage.csv   ETF-vs-underlying realized leverage by quarter
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from common.paths import CACHE, REPORTS, UNIVERSE
from flows import prices as px
from flows.assets import holdout_errors, reconstruct
from flows.flow import auction_proxy, rebalance_trade, stock_aggregates
from universe.parse_names import parse_name

BENCH = ["SPY", "QQQ", "SMH", "BITO"]
LAST_DATE = pd.Timestamp("2026-09-22")


def _fund_nport() -> pd.DataFrame:
    nf = pd.read_parquet(CACHE / "nport_universe_filings.parquet")   # deduped by universe build
    nf["L_name"] = nf["series_name"].map(lambda s: parse_name(str(s)).leverage)
    return nf


def leverage_path(dates: pd.DatetimeIndex, nf: pd.DataFrame, L_default: float) -> pd.Series:
    """Target leverage by date from the series name on each N-PORT report.

    The name on a report covers (previous report, this report]; after the last
    report the universe (latest) leverage applies.
    """
    L = pd.Series(L_default, index=dates, dtype=float)
    prev = pd.Timestamp("1900-01-01")
    for _, r in nf.sort_values("report_date").iterrows():
        lv = r["L_name"]
        if pd.notna(lv) and np.sign(lv) == np.sign(L_default):
            L[(L.index > prev) & (L.index <= r["report_date"])] = lv
        prev = r["report_date"]
    return L


GRID = np.array([-3, -2, -1.75, -1.5, -1.25, -1, 1.25, 1.5, 1.75, 2, 3])


def snap_leverage(dates: pd.DatetimeIndex, L_name: pd.Series, lr: pd.DataFrame) -> pd.Series:
    """Per-quarter target leverage = realized ETF-vs-underlying beta snapped to the standard grid
    (same sign as the name). Quarters without enough ETF price data keep the name-based leverage."""
    L = L_name.copy()
    if lr is None or lr.empty:
        return L
    q = dates.to_period("Q").astype(str)
    for _, r in lr.iterrows():
        if r["n"] < 15 or not np.isfinite(r["beta"]) or np.sign(r["beta"]) != np.sign(L_name.iloc[-1]):
            continue
        g = GRID[np.sign(GRID) == np.sign(r["beta"])]
        snapped = g[np.argmin(np.abs(g - r["beta"]))]
        if abs(snapped - r["beta"]) < 0.2:
            L[q == r["quarter"]] = snapped
    return L


def realized_leverage(fr: pd.Series, ur: pd.Series) -> pd.DataFrame:
    d = pd.concat([fr.rename("f"), ur.rename("u")], axis=1).dropna()
    d = d[(d["u"].abs() > 0.002) & (d["f"].abs() < 1.0)]
    rows = []
    for q, g in d.groupby(d.index.to_period("Q")):
        if len(g) >= 15:
            b = np.polyfit(g["u"], g["f"], 1)[0]
            rows.append({"quarter": str(q), "beta": b, "n": len(g)})
    return pd.DataFrame(rows)


def build_fund_days(uni: pd.DataFrame, cur_aum: pd.DataFrame | None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    nf_all = _fund_nport()
    fund_rows, val_rows, lev_rows = [], [], []
    aum = pd.DataFrame(columns=["total_assets"]) if cur_aum is None else cur_aum.dropna(subset=["total_assets"]).set_index("ticker")
    for _, f in uni.iterrows():
        u = px.load(f["underlying"])
        if u is None:
            continue
        uc = px.clean(f["underlying"], u)
        dates = uc.index[uc.index <= LAST_DATE]
        nf = nf_all[nf_all["series_id"] == f["series_id"]]
        nfp = nf[nf["net_assets"] > 0]
        L = leverage_path(dates, nf, float(f["leverage"]))

        etf = px.load(f["ticker"]) if isinstance(f["ticker"], str) else None
        etf_ret = None
        first_rep = nfp["report_date"].min() if len(nfp) else pd.NaT
        lr = None
        if etf is not None and len(etf) > 5:
            ec = px.clean(f["ticker"], etf)
            # guard against recycled tickers: keep prices within the fund's N-PORT life
            if pd.notna(first_rep):
                ec = ec[ec.index >= first_rep - pd.Timedelta(days=200)]
            if len(ec) > 5:
                etf_ret = ec["r_cc"]
                lr = realized_leverage(etf_ret.where(~ec["bad_today"]), uc["r_cc"].where(~uc["bad_today"]))
                if len(lr):
                    lr["ticker"], lr["series_id"], lr["L_target"] = f["ticker"], f["series_id"], f["leverage"]
                    lev_rows.append(lr)
        L = snap_leverage(dates, L, lr)
        # inception / end
        if etf_ret is not None:
            inception = etf_ret.index.min()
            last_px = etf_ret.index.max()
            end = None if last_px >= LAST_DATE - pd.Timedelta(days=7) else last_px
        else:
            if pd.isna(first_rep):
                continue
            first = nfp.sort_values("report_date").iloc[0]
            months = [m for m in (1, 2, 3) if (first.get(f"sales_flow_mon{m}") or 0) > 0]
            back = 3 - (months[0] if months else 3)
            inception = (first["report_date"].to_period("M") - back).to_timestamp()
            last_rep = nfp["report_date"].max()
            end = None if f["status"] == "active" else last_rep + pd.Timedelta(days=30)
        # fund return: own price if we have it, else L * underlying
        model_ret = L * uc["r_cc"].reindex(dates)
        if etf_ret is not None:
            fund_ret = etf_ret.reindex(dates)
            # bad ETF prints -> fall back to the model return that day
            dev = (fund_ret - model_ret).abs()
            fund_ret = fund_ret.where(dev < 0.25, model_ret).fillna(model_ret)
        else:
            fund_ret = model_ret
        current = None
        if f["status"] == "active" and f["ticker"] in aum.index:
            current = (LAST_DATE, float(aum.loc[f["ticker"], "total_assets"]))
        rec = reconstruct(dates, fund_ret, nfp, inception, end, current=None)
        # validation: roll-forward from last N-PORT anchor vs current AUM (held out)
        if current is not None and len(rec):
            val_rows.append({"ticker": f["ticker"], "series_id": f["series_id"], "underlying": f["underlying"],
                             "L": f["leverage"], "check": "rollforward_vs_current",
                             "last_anchor": nfp["report_date"].max(), "pred": rec["A"].iloc[-1],
                             "actual": current[1]})
            rec = reconstruct(dates, fund_ret, nfp, inception, end, current=current)
        ho = holdout_errors(dates, fund_ret, nfp)
        for _, h in ho.iterrows():
            val_rows.append({"ticker": f["ticker"], "series_id": f["series_id"], "underlying": f["underlying"],
                             "L": f["leverage"], "check": "quarter_holdout", "last_anchor": h["report_date"],
                             "pred": h["pred_with_flow"], "pred_no_flow": h["pred_no_flow"],
                             "actual": h["actual"]})
        if rec.empty:
            continue
        d = rec.copy()
        d["A_prev"] = d["A"].shift(1)
        d["src_prev"] = d["src"].shift(1)
        d = d.iloc[1:]  # first day has no prior-close assets
        d["L"] = L.reindex(d.index)
        d["r"] = uc["r_cc"].reindex(d.index)
        d["T"] = rebalance_trade(d["L"], d["A_prev"], d["r"].fillna(0.0))
        d["ticker"], d["series_id"], d["underlying"] = f["ticker"], f["series_id"], f["underlying"]
        d["issuer"] = f["issuer"]
        d["own_price"] = etf_ret is not None
        fund_rows.append(d.reset_index(names="date"))
    fd = pd.concat(fund_rows, ignore_index=True)
    val = pd.DataFrame(val_rows)
    lev = pd.concat(lev_rows, ignore_index=True) if lev_rows else pd.DataFrame()
    return fd, val, lev


def rolling_beta(y: pd.Series, x: pd.Series, win: int = 60) -> pd.Series:
    """Trailing OLS beta using days t-win..t-1 (no look-ahead into day t)."""
    cov = (y * x).rolling(win, min_periods=40).mean() - y.rolling(win, min_periods=40).mean() * x.rolling(
        win, min_periods=40).mean()
    var = x.rolling(win, min_periods=40).var(ddof=0)
    return (cov / var).shift(1)


def build_stock_days(fd: pd.DataFrame, stocks: list[str]) -> pd.DataFrame:
    agg = stock_aggregates(fd.rename(columns={"underlying": "underlying"})[
        ["underlying", "date", "L", "A_prev", "r"]].dropna())
    agg = agg.rename(columns={"underlying": "ticker"})
    bench = {b: px.clean(b, px.load(b)) for b in BENCH if px.load(b) is not None}
    parts = []
    for t in stocks:
        raw = px.load(t)
        if raw is None or len(raw) < 80:
            continue
        c = px.clean(t, raw)
        c = c[c.index <= LAST_DATE]
        c["auction_proxy"] = auction_proxy(c["dollar_volume"])
        c["adv20"] = c["dollar_volume"].rolling(20, min_periods=20).mean().shift(1)
        c["vol60"] = c["r_cc"].rolling(60, min_periods=40).std().shift(1)
        c["r_cc_lag1"] = c["r_cc"].shift(1)
        best_r2, best = None, None
        for b, bc in bench.items():
            x = bc["r_cc"].reindex(c.index)
            beta = rolling_beta(c["r_cc"], x)
            corr = c["r_cc"].rolling(60, min_periods=40).corr(x).shift(1)
            c[f"beta_{b}"] = beta
            c[f"r2_{b}"] = corr ** 2
            for w in ("r_co_next", "r_cc_next", "r_oc_next"):
                c[f"{w}_{b}"] = bc[w].reindex(c.index)
        # benchmark with the highest trailing R^2 each day (known at t)
        r2 = c[[f"r2_{b}" for b in bench]].fillna(-1)
        pick = r2.idxmax(axis=1).str.replace("r2_", "", regex=False)
        c["bench"] = pick.where(r2.max(axis=1) >= 0)
        for w in ("r_co_next", "r_cc_next", "r_oc_next"):
            bet = np.select([pick == b for b in bench], [c[f"beta_{b}"] for b in bench], np.nan)
            br = np.select([pick == b for b in bench], [c[f"{w}_{b}"] for b in bench], np.nan)
            c[f"{w}_xs"] = c[w] - bet * br
            c[f"{w}_xsQQQ"] = c[w] - c["beta_QQQ"] * c[f"{w}_QQQ"]
        c["beta_pick"] = np.select([pick == b for b in bench], [c[f"beta_{b}"] for b in bench], np.nan)
        keep = ["ticker", "open", "close", "volume", "dollar_volume", "r_cc", "r_co_next", "r_cc_next", "r_oc_next",
                "r_oc", "r_cc_lag1", "auction_proxy", "adv20", "vol60", "bench", "beta_pick", "beta_QQQ",
                "r_co_next_xs", "r_cc_next_xs", "r_oc_next_xs", "r_co_next_xsQQQ", "r_cc_next_xsQQQ",
                "r_oc_next_xsQQQ", "bad_today", "bad_next", "flag_big_move", "flag_bad_split"]
        parts.append(c[keep].reset_index())
    sd = pd.concat(parts, ignore_index=True)
    sd = sd.merge(agg, on=["ticker", "date"], how="left")
    for col in ("Flow", "Gamma", "Gamma_long", "Gamma_inv", "A_long", "A_inv"):
        sd[col] = sd[col].fillna(0.0)
    sd["n_funds"] = sd["n_funds"].fillna(0).astype(int)
    sd["FlowRatio"] = sd["Flow"] / sd["auction_proxy"]
    sd["GammaRatio"] = sd["Gamma"] / sd["auction_proxy"]   # flow per unit return / auction proxy
    return sd


def main():
    uni = pd.read_csv(UNIVERSE / "single_stock_universe.csv")
    uni = uni[uni["include"] == True]  # noqa: E712
    aum_p = CACHE / "current_aum.parquet"
    cur = pd.read_parquet(aum_p) if aum_p.exists() else None
    fd, val, lev = build_fund_days(uni, cur)
    fd.to_parquet(CACHE / "fund_days.parquet", index=False)
    val.to_csv(REPORTS / "asset_validation.csv", index=False)
    lev.to_csv(REPORTS / "realized_leverage.csv", index=False)
    pool = pd.read_csv(CACHE.parent / "raw" / "lists" / "placebo_pool_2026-09-23.csv")["ticker"].tolist()
    stocks = sorted(set(uni["underlying"]) | set(pool))
    sd = build_stock_days(fd, stocks)
    sd["treated_ever"] = sd["ticker"].isin(set(uni["underlying"]))
    sd.to_parquet(CACHE / "stock_days.parquet", index=False)
    print("fund_days", fd.shape, "stock_days", sd.shape)


if __name__ == "__main__":
    main()
