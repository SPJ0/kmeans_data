"""Pre-launch placebo: are the "flow" effects about LETF flow or about the kind of
stock that gets an LETF (volatile retail favorites)?

For each treated stock, take its days BEFORE any LETF existed (gamma == 0) and
assign a fake gamma/ADV equal to the median g_adv over its first 60 treated
days. Run the same top-|flow| matched test (same cut as the real test) on these
placebo days. If placebo excess ~= real excess, the effect is not LETF flow.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from analysis.anticipation import load as load_hourly_panel
from analysis.baseline import PANEL, prepare
from analysis.stats import clustered_mean
from universe.build_universe import ROOT

REP = ROOT / "reports"


def fake_gadv(p: pd.DataFrame) -> pd.Series:
    t = p[p["gamma"] > 0].sort_values("date")
    return t.groupby("ticker").head(60).groupby("ticker")["g_adv"].median()


def matched_generic(p, sig_col, move_col, y, cut, treat_mask, sign_mult):
    p = p.copy()
    p["z"] = (p[move_col] / p["vol60"]).abs()
    p["zb"] = pd.cut(p["z"], [0, 0.5, 1, 1.5, 2, 3, 4, 6, np.inf], labels=False)
    p["sgn"] = np.sign(p[move_col])
    untreated_names = ~p["ticker"].isin(p.loc[p["gamma"] > 0, "ticker"].unique())
    ctl = p[untreated_names].groupby(["date", "sgn", "zb"])[y].agg(["mean", "size"]).rename(columns={"mean": "ctl", "size": "n_ctl"})
    t = p[treat_mask & (p[sig_col].abs() >= cut)].join(ctl, on=["date", "sgn", "zb"])
    t = t[t["n_ctl"] >= 2]
    s = sign_mult * np.sign(t[sig_col])
    ex = s * (t[y] - t["ctl"]) * 1e4
    m, se, n = clustered_mean(ex, t["date"])
    return dict(n=n, n_names=t["ticker"].nunique(), n_dates=t["date"].nunique(), excess_bps=m, se=se)


def main():
    rows = []
    # (a) anticipation: 13:30 -> close continuation (hourly panel, Oct 2023+)
    h = load_hourly_panel()
    g = fake_gadv(h)
    first_h = h[h["gamma"] > 0].groupby("ticker")["date"].min()
    h["pre_launch"] = h["ticker"].isin(first_h.index) & (h["gamma"] == 0) & (h["date"] < h["ticker"].map(first_h))
    h["fake_flow_1330"] = h["ticker"].map(g) * h["r_to1330"]
    cut = h.loc[h["gamma"] > 0, "flow_1330_adv"].abs().quantile(0.95)
    rows.append(dict(test="anticipation 13:30->close", sample="real (treated days)",
                     **matched_generic(h, "flow_1330_adv", "r_to1330", "r_1330_close_x_w", cut, h["gamma"] > 0, 1)))
    rows.append(dict(test="anticipation 13:30->close", sample="placebo (pre-launch days, fake gamma)",
                     **matched_generic(h, "fake_flow_1330", "r_to1330", "r_1330_close_x_w", cut, h["pre_launch"], 1)))
    # (b) overnight reversal after close (daily panel, 2022-07+ ; pre-launch days back to 2022-07)
    p = prepare(pd.read_parquet(PANEL / "panel_all.parquet"))
    g2 = fake_gadv(p)
    first = p[p["gamma"] > 0].groupby("ticker")["date"].min()
    p["pre_launch"] = p["ticker"].isin(first.index) & (p["gamma"] == 0) & (p["date"] < p["ticker"].map(first))
    p["fake_flow"] = p["ticker"].map(g2) * p["r_t"]
    cut2 = p.loc[p["gamma"] > 0, "flow_adv"].abs().quantile(0.90)
    for y in ("on1_x_w", "cc1_x_w"):
        rows.append(dict(test=f"reversal {y}", sample="real (treated days)",
                         **matched_generic(p, "flow_adv", "r_t", y, cut2, p["gamma"] > 0, -1)))
        rows.append(dict(test=f"reversal {y}", sample="placebo (pre-launch days, fake gamma)",
                         **matched_generic(p, "fake_flow", "r_t", y, cut2, p["pre_launch"], -1)))
    r = pd.DataFrame(rows)
    r.to_csv(REP / "placebo_prelaunch.csv", index=False)
    pd.set_option("display.width", 200)
    print(r.to_string(float_format=lambda v: f"{v:,.1f}"))


if __name__ == "__main__":
    main()
