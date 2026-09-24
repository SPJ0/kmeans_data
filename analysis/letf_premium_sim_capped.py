"""Illustrative LETF-premium P&L with a daily capital cap.

Base rule as in letf_premium_sim.py (|e_t| >= 50 bps, fade at close, L x underlying hedge,
exit next close, per-position size = min($1M, 1% of fund ADV)). Then cap the day's total:
  cap on gross  = sum(size * (1 + |L|))  <= CAP   (ETF + hedge)
  cap on ETF leg = sum(size)             <= CAP
Allocation when the cap binds:
  pro-rata   -- scale all positions down by the same factor
  strongest  -- fill positions in order of |e_t| until the cap is used (last one partial)
"""
import warnings

import numpy as np
import pandas as pd

from analysis.letf_premium import fund_frame, load_navs
from universe.build_universe import ROOT

CAP = 5e6


def allocate(g: pd.DataFrame, basis: str, how: str) -> pd.Series:
    w = g["size"] * ((1 + g["L"].abs()) if basis == "gross" else 1.0)  # capital each position uses
    if w.sum() <= CAP:
        return g["size"]
    if how == "pro-rata":
        return g["size"] * CAP / w.sum()
    order = g["e"].abs().sort_values(ascending=False).index
    left, out = CAP, pd.Series(0.0, index=g.index)
    for i in order:
        take = min(1.0, left / w[i]) if w[i] > 0 else 0.0
        out[i] = g.at[i, "size"] * take
        left -= w[i] * take
        if left <= 0:
            break
    return out


def stats(s: pd.DataFrame, bdays: pd.DatetimeIndex, lo: str) -> dict:
    x = s[s["date"] >= lo]
    d = x[x["alloc"] > 0].groupby("date").agg(n=("pnl", "size"), etf=("alloc", "sum"), gross=("gross", "sum"), pnl=("pnl", "sum"))
    allb = d["pnl"].reindex(bdays[bdays >= lo], fill_value=0.0)
    cum = allb.cumsum()
    dd = cum - cum.cummax()
    trough = dd.idxmin()
    yrs = len(allb) / 252
    return {
        "P&L": x["pnl"].sum(), "P&L per year": x["pnl"].sum() / yrs, "return on $5M per year": x["pnl"].sum() / yrs / CAP,
        "days with trades": len(d), "share of days": len(d) / len(allb),
        "positions/day avg": d["n"].mean(), "positions/day median": d["n"].median(), "positions/day max": d["n"].max(),
        "ETF $/day avg": d["etf"].mean(), "gross $/day avg": d["gross"].mean(), "gross $/day max": d["gross"].max(),
        "days cap binds": int((x.groupby("date")["capped"].first()).sum()),
        "losing days": int((d["pnl"] < 0).sum()), "losing share": (d["pnl"] < 0).mean(),
        "worst day": d["pnl"].min(), "best day": d["pnl"].max(),
        "max drawdown": dd.min(), "dd from": cum.loc[:trough].idxmax().date(), "dd to": trough.date(),
        "sharpe (daily, ann.)": allb.mean() / allb.std() * np.sqrt(252),
    }


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
    base = p[(p["e"].abs() >= 0.005) & p["fund_adv"].notna()].copy()
    base["size"] = np.minimum(1e6, 0.01 * base["fund_adv"])
    bdays = pd.bdate_range(p["date"].min(), p["date"].max())
    rows = []
    for basis in ("gross", "etf"):
        for how in ("pro-rata", "strongest"):
            for cost in (5, 10):
                s = base.copy()
                s["alloc"] = s.groupby("date", group_keys=False).apply(lambda g: allocate(g, basis, how))
                w = s["size"] * ((1 + s["L"].abs()) if basis == "gross" else 1.0)
                s["capped"] = s.groupby("date")["size"].transform("size").astype(bool) & (w.groupby(s["date"]).transform("sum") > CAP)
                s["gross"] = s["alloc"] * (1 + s["L"].abs())
                s["pnl"] = s["alloc"] * (-np.sign(s["e"]) * s["e_next"] * 1e4 - cost - 1) / 1e4
                for per, lo in (("2025-01..2026-03", "2025-01-01"), ("2022-07..2026-03", "2000-01-01")):
                    rows.append({"cap on": "ETF+hedge (gross)" if basis == "gross" else "ETF leg only",
                                 "allocation": how, "cost bps": cost, "period": per, **stats(s, bdays, lo)})
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "reports" / "letf_premium_sim_capped_5M.csv", index=False)
    pd.set_option("display.width", 250, "display.max_columns", 60)
    print(out.T.to_string())
