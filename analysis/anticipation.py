"""Variant: is the tradeable effect *anticipation* (momentum into the close)?

Motivation (event study 2026-09-23): price moves in the direction of the flow
from ~13:30, with no excess in the last 30 minutes and no net reversal by
t+1's close. So test a signal knowable at 13:30:

  flow_1330_adv = gamma * r(close[t-1] -> 13:30) / ADV20
  y             = beta-adjusted return 13:30 -> close (and its two halves)

Controls: r_to1330, |r_to1330|, r_to1330 * vol60, date FE; SEs clustered by
date and stock. The comparison universe is the treated names plus 600
volatile, liquid untreated stocks with hourly data (Oct 2023 onward).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from analysis.baseline import concentration, prepare
from analysis.stats import clustered_mean, fe_ols, winsorize
from universe.build_universe import ROOT

REP = ROOT / "reports"


def load() -> pd.DataFrame:
    p = pd.read_parquet(ROOT / "data" / "panel" / "panel_all.parquet")
    p = p[p["r_to1330"].notna()]
    p = prepare(p)
    p["abs_r_to1330"] = p["r_to1330"].abs()
    p["r_to1330_vol"] = p["r_to1330"] * p["vol60"]
    nz = p["flow_1330_adv"].notna() & (p["flow_1330_adv"] != 0)
    a, b = p.loc[nz, "flow_1330_adv"].quantile([0.005, 0.995])
    p["flow_1330_adv_w"] = p["flow_1330_adv"].clip(a, b)
    for c in ("r_1330_close_x", "r_1330_1530_x", "r_last30_x"):
        p[c + "_w"] = winsorize(p[c], 0.001, 0.999)
    return p


def regressions(p: pd.DataFrame) -> pd.DataFrame:
    X = ["flow_1330_adv_w", "r_to1330", "abs_r_to1330", "r_to1330_vol"]
    out = []
    for y in ("r_1330_close_x_w", "r_1330_1530_x_w", "r_last30_x_w", "on1_x_w", "oc1_x_w", "cc1_x_w"):
        out.append(fe_ols(p, y, X).assign(model="pooled", y=y))
    # within-stock: stock-specific slopes on r_to1330 for treated names
    names = p.loc[p["treated"], "ticker"].unique()
    q = p[p["ticker"].isin(names)].copy()
    slopes = {f"rt_{t}": np.where(q["ticker"] == t, q["r_to1330"], 0.0) for t in names}
    q = pd.concat([q, pd.DataFrame(slopes, index=q.index)], axis=1)
    for y in ("r_1330_close_x_w", "cc1_x_w"):
        r = fe_ols(q, y, ["flow_1330_adv_w", "abs_r_to1330", "r_to1330_vol", *slopes])
        out.append(r.loc[["flow_1330_adv_w"]].assign(model="within-stock", y=y))
    return pd.concat(out).reset_index(names="var")


def matched(p: pd.DataFrame, y: str, top_q: float = 0.95) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Top |flow_1330_adv| treated days vs untreated stocks on the same date with
    the same sign and standardized size of the move to 13:30. Returns are signed
    in the flow direction, so positive = continuation (anticipation profit)."""
    p = p.copy()
    p["z"] = (p["r_to1330"] / p["vol60"]).abs()
    p["zb"] = pd.cut(p["z"], [0, 0.5, 1, 1.5, 2, 3, 4, 6, np.inf], labels=False)
    p["sgn"] = np.sign(p["r_to1330"])
    ctl = p[~p["treated"]].groupby(["date", "sgn", "zb"])[y].agg(["mean", "size"]).rename(columns={"mean": "ctl", "size": "n_ctl"})
    t = p[p["treated"] & p["flow_1330_adv"].notna()].copy()
    t = t[t["flow_1330_adv"].abs() >= t["flow_1330_adv"].abs().quantile(top_q)]
    t = t.join(ctl, on=["date", "sgn", "zb"])
    t = t[t["n_ctl"] >= 2]
    s = np.sign(t["flow_1330_adv"])
    t["cont_treated"] = s * t[y] * 1e4
    t["cont_ctl"] = s * t["ctl"] * 1e4
    t["excess"] = t["cont_treated"] - t["cont_ctl"]
    rows = []
    groups = [("all", t), *[(f"year={k}", v) for k, v in t.groupby("year")],
              ("up days", t[t["r_to1330"] > 0]), ("down days", t[t["r_to1330"] < 0])]
    for name, g in groups:
        r = dict(subset=name, n=len(g), n_dates=g["date"].nunique(), n_names=g["ticker"].nunique())
        for c in ("cont_treated", "cont_ctl", "excess"):
            m, se, _ = clustered_mean(g[c], g["date"])
            r[c + "_bps"], r[c + "_se"] = m, se
        rows.append(r)
    return pd.DataFrame(rows), t


def main():
    p = load()
    print(f"hourly sample: {len(p):,} stock-days, {p['ticker'].nunique()} stocks "
          f"({p.loc[p['treated'], 'ticker'].nunique()} treated), {p['date'].min().date()}..{p['date'].max().date()}")
    reg = regressions(p)
    reg.to_csv(REP / "anticipation_regressions.csv", index=False)
    res = []
    for y in ("r_1330_close_x_w", "r_1330_1530_x_w", "r_last30_x_w"):
        m, t = matched(p, y)
        res.append(m.assign(y=y))
        if y == "r_1330_close_x_w":
            conc = concentration(t, "excess")
            top = t
    mt = pd.concat(res)
    mt.to_csv(REP / "anticipation_matched.csv", index=False)
    pd.set_option("display.width", 220)
    print(reg[reg["var"] == "flow_1330_adv_w"].to_string(float_format=lambda v: f"{v:,.4f}"))
    print(mt.to_string(float_format=lambda v: f"{v:,.1f}"))
    print("concentration (excess 13:30->close):", conc)
    print("top-5% cut |flow_1330_adv| =", round(p.loc[p['treated'], 'flow_1330_adv'].abs().quantile(0.95), 4))
    print(top.groupby("ticker")["excess"].agg(["size", "mean", "sum"]).sort_values("sum", ascending=False).head(12).round(1))


if __name__ == "__main__":
    main()
