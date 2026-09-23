"""Validate interpolated AUM (N-PORT anchors + flows) against exact issuer daily AUM."""
import numpy as np
import pandas as pd

from flows.assets import daily_assets, load_exact
from universe.build_universe import ROOT

if __name__ == "__main__":
    u = pd.read_csv(ROOT / "universe" / "letf_universe_final.csv")
    fd = pd.read_parquet(ROOT / "data" / "nport" / "nport_fund.parquet")
    sched = pd.read_parquet(ROOT / "universe" / "leverage_schedule.parquet")
    ex = load_exact()
    rows = []
    for _, s in u.iterrows():
        t = s["price_ticker"] if isinstance(s["price_ticker"], str) else s["ticker"]
        if t not in ex or pd.isna(s["nport_n"]):
            continue
        lev = sched.loc[sched.series_id == s.series_id].set_index("date")["leverage"]
        d = daily_assets(s, fd, ex[t], lev if len(lev) else s["leverage_parsed"])
        d = d[(d["aum_source"] == "exact") & d["aum_interp"].notna() & (d["aum"] > 5e6)]
        d = d[d["date"] <= pd.Timestamp(s["nport_last"])]  # compare only where anchors exist
        if len(d) < 20:
            continue
        err = np.log(d["aum_interp"] / d["aum"])
        rows.append(dict(ticker=t, n=len(d), med_abs_log_err=err.abs().median(), p90=err.abs().quantile(0.9),
                         bias=err.median(), aum_med=d["aum"].median()))
    r = pd.DataFrame(rows).sort_values("aum_med", ascending=False)
    pd.set_option("display.width", 200)
    print(r.to_string(float_format=lambda x: f"{x:,.3f}"))
    w = r["aum_med"] / r["aum_med"].sum()
    print("AUM-weighted median |log err|: %.3f; funds: %d" % ((w * r["med_abs_log_err"]).sum(), len(r)))
    r.to_csv(ROOT / "reports" / "asset_validation.csv", index=False)
