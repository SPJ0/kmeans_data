"""Rough P&L sizing for LETF closing-premium reversion (proxy e_t, all funds).

Rule (knowable at the close only if the fund's closing price and the underlying's
closing price are both known, i.e. this assumes execution *in* both closing
auctions at those prices; see caveats in RESEARCH_LOG):
  if e_t <= -k: buy fund at close, short L x underlying at close; unwind at t+1 close
  if e_t >= +k: the reverse
Gross P&L per $ = -sign(e_t) * e_{t+1} (includes fee/financing drift of the fund).
Costs: `cost_bps` per round trip on the fund leg (fees, impact; no spread since both
legs are auction prints) + 1 bp for the hedge leg.
Size: min($1M, 1% of fund's 20-day ADV) per event -- the closing auction is a
fraction of ADV, so 1% of ADV is already aggressive for thin funds.
"""
import numpy as np
import pandas as pd

from analysis.letf_premium import fund_frame, load_navs
from analysis.stats import clustered_mean
from universe.build_universe import ROOT

if __name__ == "__main__":
    u = pd.read_csv(ROOT / "universe" / "letf_universe_final.csv")
    u = u[u["price_ticker"].notna()]
    sched = pd.read_parquet(ROOT / "universe" / "leverage_schedule.parquet")
    navs = load_navs()
    p = pd.concat([fund_frame(r, sched, navs.get(r["price_ticker"])) for _, r in u.iterrows()], ignore_index=True)
    p = p[p["e"].abs().lt(0.2) & p["e_next"].abs().lt(0.2)]
    p["fund_adv"] = p.groupby("ticker")["dvol_fund"].transform(lambda s: s.rolling(20, min_periods=10).mean().shift(1))
    p = p[p["fund_adv"].notna()]
    rows = []
    for k in (25, 50, 100):
        for cost in (5, 10):
            for adv_min, lab in ((0, "all funds"), (20e6, "fund ADV >= $20M")):
                s = p[(p["e"].abs() * 1e4 >= k) & (p["fund_adv"] >= adv_min)].copy()
                s["size"] = np.minimum(1e6, 0.01 * s["fund_adv"])
                s["net_bps"] = -np.sign(s["e"]) * s["e_next"] * 1e4 - cost - 1
                s["pnl"] = s["size"] * s["net_bps"] / 1e4
                daily = s.groupby("date")["pnl"].sum()
                allday = daily.reindex(pd.bdate_range(p["date"].min(), p["date"].max()), fill_value=0.0)
                yr = s.groupby(s["date"].dt.year)["pnl"].sum()
                m, se, n = clustered_mean(s["net_bps"], s["date"])
                rows.append(dict(k_bps=k, cost_bps=cost, universe=lab, n_events=n, n_funds=s["ticker"].nunique(),
                                 net_bps=m, se=se, avg_size=s["size"].mean(), pnl_total=s["pnl"].sum(),
                                 pnl_2025=yr.get(2025, 0.0), sharpe_ann=allday.mean() / allday.std() * np.sqrt(252),
                                 share_top10_days=daily.nlargest(10).sum() / s["pnl"].sum() if s["pnl"].sum() > 0 else np.nan,
                                 share_top5_funds=s.groupby("ticker")["pnl"].sum().nlargest(5).sum() / s["pnl"].sum() if s["pnl"].sum() > 0 else np.nan))
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "reports" / "letf_premium_sim.csv", index=False)
    pd.set_option("display.width", 240)
    print(out.to_string(float_format=lambda v: f"{v:,.2f}"))
