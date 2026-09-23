"""Diagnostic: are LETF closing 'premiums' stale prints? If the fund's recorded
close is an earlier trade, prem_t ~= -L * (underlying move after that trade),
so it loads negatively on L * r_und(15:30->close), more so in thin funds."""
import numpy as np
import pandas as pd

from analysis.letf_premium import fund_frame, load_navs
from analysis.stats import clustered_mean, fe_ols
from pipelines.prices import load_daily
from analysis.panel import hourly_opens
from universe.build_universe import ROOT

if __name__ == "__main__":
    u = pd.read_csv(ROOT / "universe" / "letf_universe_final.csv")
    u = u[u["price_ticker"].notna()]
    sched = pd.read_parquet(ROOT / "universe" / "leverage_schedule.parquet")
    navs = load_navs()
    parts = []
    last30 = {}
    for _, r in u.iterrows():
        f = fund_frame(r, sched, navs.get(r["price_ticker"]))
        if f.empty:
            continue
        und = r["underlying"]
        if und not in last30:
            d = load_daily(und)
            ho = hourly_opens(und, d["Close"])
            last30[und] = (d["Close"].reindex(ho.index) / ho["p1530"] - 1)
        f["r_und_last30"] = f["date"].map(last30[und])
        parts.append(f)
    p = pd.concat(parts, ignore_index=True)
    p = p[p["e"].abs().lt(0.2) & p["e_next"].abs().lt(0.2) & p["r_und_last30"].notna()]
    p["x_last30"] = p["L"] * p["r_und_last30"]
    p["fund_adv"] = p.groupby("ticker")["dvol_fund"].transform(lambda s: s.rolling(20, min_periods=10).mean().shift(1))
    p["liq"] = pd.qcut(p["fund_adv"], 4, labels=["q1 thinnest", "q2", "q3", "q4 most liquid"])
    rows = []
    for lab, s in [("all", p), *[(str(k), v) for k, v in p.groupby("liq", observed=True)]]:
        r = fe_ols(s, "e", ["x_last30"], fe="date", cluster=("date", "ticker"))
        r2 = fe_ols(s, "e_next", ["e"], fe="date", cluster=("date", "ticker"))
        big = s[s["e"].abs() >= 0.005]
        m, se, n = clustered_mean(-np.sign(big["e"]) * big["e_next"] * 1e4, big["date"])
        rows.append(dict(sample=lab, n=len(s), fund_adv_med=s["fund_adv"].median(),
                         load_on_last30=r.loc["x_last30", "coef"], t_last30=r.loc["x_last30", "t"],
                         e_autocorr_slope=r2.loc["e", "coef"], rev_bps_if_abs_e_ge_50=m, se=se, n_ev=n))
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "reports" / "letf_premium_staleness.csv", index=False)
    pd.set_option("display.width", 220)
    print(out.to_string(float_format=lambda v: f"{v:,.3f}"))
