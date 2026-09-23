"""Secondary check: index-level leveraged ETF flow (TQQQ/SQQQ, SOXL/SOXS, UPRO/SPXU, ...).

Each index family's rebalance flow is computed exactly as for single stocks,
using a liquid proxy ETF's daily return as the index return. Because these
funds hedge through swaps/futures on a whole basket, there is no clean
"auction proxy"; flow is standardized by its trailing 250-day std instead.

Time-series tests per index, Newey-West (5 lags) SEs:
  (a) next return on standardized flow alone (flow is ~ Gamma * r_t, so r_t and
      flow are nearly collinear in a single series and cannot enter together);
  (b) next return on r_t and r_t * (Gamma_t / trailing-250d mean Gamma): does the
      reversal per unit move get stronger when lev-ETF Gamma is high?
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from common.paths import REPORTS, UNIVERSE
from flows import prices as px
from flows.build_panel import LAST_DATE, build_fund_days

PROXY = {"QQQ": "QQQ", "S&P500": "SPY", "S&P 500": "SPY", "Semiconductor": "SOXX", "Semiconductors": "SOXX",
         "Technology": "XLK", "Small Cap": "IWM", "Russell2000": "IWM", "Russell 2000": "IWM", "Dow30": "DIA",
         "Financial": "XLF", "Financials": "XLF", "S&P Biotech": "XBI", "Energy": "XLE", "Regional Banks": "KRE",
         "FTSE China": "FXI"}


def main():
    i = pd.read_csv(UNIVERSE / "index_candidates.csv")
    i = i[i["underlying_token"].isin(PROXY) & i["ticker"].notna() & (i["reset"] == "daily")].copy()
    i["underlying"] = i["underlying_token"].map(PROXY)
    px.download(sorted(set(i["underlying"]) | set(i["ticker"])))
    last = {t: (px.load(t).index.max() if px.load(t) is not None else pd.NaT) for t in i["ticker"]}
    i["status"] = ["active" if pd.notna(last[t]) and last[t] >= LAST_DATE - pd.Timedelta(days=7) else "closed"
                   for t in i["ticker"]]
    fd, val, lev = build_fund_days(i, None)
    fd.to_parquet(REPORTS.parent / "data" / "cache" / "index_fund_days.parquet", index=False)
    rows = []
    for proxy, g in fd.groupby("underlying"):
        g = g.assign(G=g["A_prev"] * g["L"] * (g["L"] - 1))
        flow = g.groupby("date")["T"].sum()
        gam = g.groupby("date")["G"].sum()
        c = px.clean(proxy, px.load(proxy))
        d = pd.DataFrame({"flow": flow, "gamma": gam}).join(c[["r_cc", "r_co_next", "r_cc_next"]], how="inner")
        d = d.dropna()
        d["flow_z"] = d["flow"] / d["flow"].rolling(250, min_periods=60).std().shift(1)
        d["r_x_grel"] = d["r_cc"] * d["gamma"] / d["gamma"].rolling(250, min_periods=60).mean().shift(1)
        d = d[d.index >= "2022-07-01"].dropna()
        for y in ("r_co_next", "r_cc_next"):
            ra = sm.OLS(d[y] * 1e4, sm.add_constant(d[["flow_z"]])).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
            rb = sm.OLS(d[y] * 1e4, sm.add_constant(d[["r_cc", "r_x_grel"]])).fit(
                cov_type="HAC", cov_kwds={"maxlags": 5})
            rows.append({"proxy": proxy, "funds": ",".join(sorted(i.loc[i["underlying"] == proxy, "ticker"])),
                         "outcome": y, "n_days": len(d), "a_coef_flow_z_bps": ra.params["flow_z"],
                         "a_t_flow_z": ra.tvalues["flow_z"], "b_coef_r_x_gamma_rel": rb.params["r_x_grel"],
                         "b_t_r_x_gamma_rel": rb.tvalues["r_x_grel"], "b_coef_r_t": rb.params["r_cc"],
                         "avg_abs_flow_musd": d["flow"].abs().mean() / 1e6,
                         "avg_gamma_busd": d["gamma"].mean() / 1e9})
    out = pd.DataFrame(rows)
    out.to_csv(REPORTS / "t9_index_secondary_check.csv", index=False)
    print(out.round(3).to_string())


if __name__ == "__main__":
    main()
