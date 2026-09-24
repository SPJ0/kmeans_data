"""Capital, positions, losing days and drawdown for the illustrative LETF-premium P&L
(rule in letf_premium_sim.py; |e_t| >= 50 bps, size = min($1M, 1% of fund ADV), 1-day hold)."""
import warnings

import numpy as np
import pandas as pd

from analysis.letf_premium import fund_frame, load_navs
from universe.build_universe import ROOT

if __name__ == "__main__":
    u = pd.read_csv(ROOT / "universe" / "letf_universe_final.csv")
    u = u[u["price_ticker"].notna()]
    sched = pd.read_parquet(ROOT / "universe" / "leverage_schedule.parquet")
    navs = load_navs()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        p = pd.concat([fund_frame(r, sched, navs.get(r["price_ticker"])) for _, r in u.iterrows()], ignore_index=True)
    p = p[p["e"].abs().lt(0.2) & p["e_next"].abs().lt(0.2)]
    p["fund_adv"] = p.groupby("ticker")["dvol_fund"].transform(lambda s: s.rolling(20, min_periods=10).mean().shift(1))
    bdays = pd.bdate_range(p["date"].min(), p["date"].max())
    rows = []
    for adv_min, cost, lab in ((0, 5, "All funds, 5 bps"), (20e6, 5, "Fund ADV >= $20M, 5 bps"), (0, 10, "All funds, 10 bps")):
        s = p[(p["e"].abs() >= 0.005) & (p["fund_adv"] >= adv_min)].copy()
        s["size"] = np.minimum(1e6, 0.01 * s["fund_adv"])
        s["hedge"] = s["size"] * s["L"].abs()
        s["pnl"] = s["size"] * (-np.sign(s["e"]) * s["e_next"] * 1e4 - cost - 1) / 1e4
        d = s.groupby("date").agg(n=("pnl", "size"), fund_leg=("size", "sum"), hedge_leg=("hedge", "sum"), pnl=("pnl", "sum"))
        d["gross"] = d["fund_leg"] + d["hedge_leg"]
        for per, lo in (("full 2022-07..2026-03", "2000"), ("2025-01..2026-03", "2025-01-01")):
            x = d[d.index >= lo]
            allb = x["pnl"].reindex(bdays[bdays >= lo], fill_value=0.0)
            cum = allb.cumsum()
            dd = cum - cum.cummax()
            trough = dd.idxmin()
            peak = cum.loc[:trough].idxmax()
            rows.append({
                "rule": lab, "period": per,
                "trade days": len(x), "share of bdays with trades": len(x) / len(allb),
                "positions/day (trade days) mean": x["n"].mean(), "positions/day median": x["n"].median(),
                "positions/day max": x["n"].max(),
                "fund leg $/day mean": x["fund_leg"].mean(), "gross (fund+hedge) $/day mean": x["gross"].mean(),
                "gross $/day p95": x["gross"].quantile(0.95), "gross $/day max": x["gross"].max(),
                "total pnl": x["pnl"].sum(),
                "losing days": int((x["pnl"] < 0).sum()), "losing share of trade days": (x["pnl"] < 0).mean(),
                "worst day": x["pnl"].min(), "best day": x["pnl"].max(),
                "max drawdown $": dd.min(), "dd peak": peak.date(), "dd trough": trough.date(),
            })
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "reports" / "letf_premium_sim_stats.csv", index=False)
    pd.set_option("display.width", 250, "display.max_columns", 50)
    print(out.T.to_string())
