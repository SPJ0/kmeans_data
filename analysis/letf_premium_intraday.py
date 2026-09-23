"""Where does the LETF closing premium form, and how fast does it revert?

Split the day's premium change e_t into
  e_pre  : close(t-1) -> 15:30 (fund's 15:30 bar open vs L x underlying's)
  e_last : 15:30 -> close      (e_t - e_pre)
and next-day reversion into close(t) -> 10:30(t+1) and the rest of t+1.
If e_last carries the premium and reverts, it forms in the closing process.
Hourly data: Oct 2023 onward.
"""
import numpy as np
import pandas as pd

from analysis.letf_premium import fund_frame, load_navs
from analysis.panel import hourly_opens
from analysis.stats import clustered_mean, fe_ols
from pipelines.prices import load_daily, load_hourly
from universe.build_universe import ROOT


def opens_1030(ticker):
    h = load_hourly(ticker)
    if h.empty:
        return pd.Series(dtype=float)
    b = h[(h.index.hour == 10) & (h.index.minute == 30)]
    s = b["Open"].set_axis(b.index.tz_localize(None).normalize())
    return s[~s.index.duplicated()]


if __name__ == "__main__":
    u = pd.read_csv(ROOT / "universe" / "letf_universe_final.csv")
    u = u[u["price_ticker"].notna()]
    sched = pd.read_parquet(ROOT / "universe" / "leverage_schedule.parquet")
    navs = load_navs()
    cache = {}

    def hp(t):
        if t not in cache:
            d = load_daily(t)
            cache[t] = (d["Close"], hourly_opens(t, d["Close"])["p1530"], opens_1030(t))
        return cache[t]

    parts = []
    for _, r in u.iterrows():
        f = fund_frame(r, sched, navs.get(r["price_ticker"]))
        if f.empty:
            continue
        fc, f1530, f1030 = hp(r["price_ticker"])
        uc, u1530, u1030 = hp(r["underlying"])
        f = f.set_index("date")
        L = f["L"]
        fprev, uprev = fc.shift(1).reindex(f.index), uc.shift(1).reindex(f.index)
        f["e_pre"] = np.log(f1530.reindex(f.index) / fprev) - np.log1p(L * (u1530.reindex(f.index) / uprev - 1))
        f["e_last"] = f["e"] - f["e_pre"]
        # next morning: close(t) -> 10:30(t+1)
        nf = f1030.reindex(f["date_next"]).values
        nu = u1030.reindex(f["date_next"]).values
        f["e_next_am"] = np.log(nf / fc.reindex(f.index).values) - np.log1p(L.values * (nu / uc.reindex(f.index).values - 1))
        f["e_next_rest"] = f["e_next"] - f["e_next_am"]
        parts.append(f.reset_index())
    p = pd.concat(parts, ignore_index=True)
    p = p.dropna(subset=["e_pre", "e_last", "e_next_am"])
    p = p[(p[["e", "e_pre", "e_last", "e_next", "e_next_am"]].abs() < 0.2).all(axis=1)]
    p["fund_adv"] = p.groupby("ticker")["dvol_fund"].transform(lambda s: s.rolling(20, min_periods=10).mean().shift(1))
    rows = []
    for lab, s in (("all funds", p), ("fund ADV >= $20M", p[p["fund_adv"] >= 20e6])):
        r = fe_ols(s, "e_next", ["e_pre", "e_last"], fe="date", cluster=("date", "ticker"))
        ra = fe_ols(s, "e_next_am", ["e_pre", "e_last"], fe="date", cluster=("date", "ticker"))
        ev = s[s["e"].abs() >= 0.005]
        sg = -np.sign(ev["e"])
        row = dict(sample=lab, n=len(s), n_events=len(ev),
                   slope_next_on_e_pre=r.loc["e_pre", "coef"], t_pre=r.loc["e_pre", "t"],
                   slope_next_on_e_last=r.loc["e_last", "coef"], t_last=r.loc["e_last", "t"],
                   slope_am_on_e_last=ra.loc["e_last", "coef"],
                   share_of_event_e_from_last30=(np.sign(ev["e"]) * ev["e_last"]).sum() / ev["e"].abs().sum())
        for c in ("e_next_am", "e_next_rest", "e_next"):
            m, se, _ = clustered_mean(sg * ev[c] * 1e4, ev["date"])
            row[f"rev_{c}_bps"], row[f"rev_{c}_se"] = m, se
        rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "reports" / "letf_premium_intraday.csv", index=False)
    pd.set_option("display.width", 250)
    print(out.T.to_string())
