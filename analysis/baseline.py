"""Phase A1 baseline: does predicted LETF rebalancing flow move prices into the
close and reverse afterwards, beyond generic short-term reversal?

Pre-registered primary spec (RESEARCH_LOG 2026-09-23):
  y  = beta-adjusted overnight (on1_x) and next close-to-close (cc1_x) return
  x  = flow / ADV20 (flow_adv)
  controls: r_t, |r_t|, r_t * vol60; date fixed effects; SEs clustered by date and stock.
Everything else here is a logged variant.

Run: python -m analysis.baseline   (writes reports/baseline_*.csv/.md/.png)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from analysis.stats import clustered_mean, fe_ols, winsorize
from universe.build_universe import ROOT

REP = ROOT / "reports"
PANEL = ROOT / "data" / "panel"
SAMPLE_START = pd.Timestamp("2022-07-01")


# ---------------------------------------------------------------- data prep
def earnings_exclusion(p: pd.DataFrame) -> pd.Series:
    """True for stock-days within one trading day of an earnings reaction day."""
    edir = ROOT / "data" / "raw" / "earnings"
    bad = pd.Series(False, index=p.index)
    has_cal = pd.Series(False, index=p.index)
    for t, idx in p.groupby("ticker").groups.items():
        f = edir / f"{t}.parquet"
        if not f.exists():
            continue
        e = pd.read_parquet(f)
        if e.empty or "Earnings Date" not in e:
            continue
        has_cal.loc[idx] = True
        ts = pd.to_datetime(e["Earnings Date"], utc=True).dt.tz_convert("America/New_York")
        dates = p.loc[idx, "date"].sort_values()
        dvals = dates.values
        react = []
        for x in ts:
            day = pd.Timestamp(x.date())
            # after-close reports react the next session
            k = np.searchsorted(dvals, np.datetime64(day), side="right" if x.hour >= 16 else "left")
            if k < len(dvals):
                react.append(k)
        pos = set()
        for k in react:
            pos.update({k - 1, k, k + 1})
        sel = [dates.index[k] for k in pos if 0 <= k < len(dates)]
        bad.loc[sel] = True
    return bad, has_cal


def prepare(p: pd.DataFrame) -> pd.DataFrame:
    p = p[(p["date"] >= SAMPLE_START)].copy()
    p = p[p["close"] >= 3]  # penny-stock filter
    p["treated"] = p["gamma"] > 0
    bad, has_cal = earnings_exclusion(p)
    p["earn_excl"] = bad
    p["has_earn_cal"] = has_cal
    p = p[~p["earn_excl"]]
    p["abs_r_t"] = p["r_t"].abs()
    p["r_t_vol"] = p["r_t"] * p["vol60"]
    p["abs_r_pre"] = p["r_pre"].abs()
    p["r_pre_vol"] = p["r_pre"] * p["vol60"]
    nz = p["flow_adv"] != 0
    for c in ("flow_adv", "flow_pre_adv"):
        a, b = p.loc[p[c].notna() & (p[c] != 0), c].quantile([0.005, 0.995])
        p[c + "_w"] = p[c].clip(a, b)
    for c in ("on1_x", "oc1_x", "cc1_x", "cc5_x", "r_last30_x", "on1", "cc1"):
        p[c + "_w"] = winsorize(p[c], 0.001, 0.999)
    p["year"] = p["date"].dt.year
    return p


# ---------------------------------------------------------------- analyses
def regressions(p: pd.DataFrame) -> pd.DataFrame:
    out = []
    for y in ("on1_x_w", "oc1_x_w", "cc1_x_w", "cc5_x_w"):
        r = fe_ols(p, y, ["flow_adv_w", "r_t", "abs_r_t", "r_t_vol"])
        out.append(r.assign(model="reversal:flow_adv", y=y))
    q = p[p["r_pre"].notna()]
    r = fe_ols(q, "r_last30_x_w", ["flow_pre_adv_w", "r_pre", "abs_r_pre", "r_pre_vol"])
    out.append(r.assign(model="pressure:flow_pre_adv", y="r_last30_x_w"))
    for y in ("on1_x_w", "cc1_x_w"):
        r = fe_ols(q, y, ["flow_pre_adv_w", "r_pre", "abs_r_pre", "r_pre_vol", "r_last30_x_w"])
        out.append(r.assign(model="reversal:flow_pre_adv(+last30 ctrl)", y=y))
    return pd.concat(out).reset_index(names="var")


def within_stock(p: pd.DataFrame) -> pd.DataFrame:
    """Treated names only (all their days, incl. pre-launch with gamma = 0):
    stock-specific slopes on r_t, so the flow coefficient is identified only from
    time variation in each stock's LETF gamma."""
    names = p.loc[p["treated"], "ticker"].unique()
    q = p[p["ticker"].isin(names)].copy()
    slope_cols = []
    for t in names:
        c = f"rt_{t}"
        q[c] = np.where(q["ticker"] == t, q["r_t"], 0.0)
        slope_cols.append(c)
    out = []
    for y in ("on1_x_w", "cc1_x_w"):
        r = fe_ols(q, y, ["flow_adv_w", "abs_r_t", "r_t_vol", *slope_cols])
        out.append(r.loc[["flow_adv_w", "abs_r_t", "r_t_vol"]].assign(model="within-stock slopes", y=y))
    return pd.concat(out).reset_index(names="var")


def decile_table(p: pd.DataFrame, sort_col: str, outcomes: list[str]) -> pd.DataFrame:
    """Deciles of signed flow among treated stock-days, pooled."""
    t = p[p["treated"] & p[sort_col].notna()].copy()
    t["dec"] = pd.qcut(t[sort_col], 10, labels=False, duplicates="drop") + 1
    rows = []
    for d, g in t.groupby("dec"):
        row = dict(decile=d, n=len(g), mean_flow_adv=g[sort_col].mean(), mean_r_t=g["r_t"].mean())
        for y in outcomes:
            m, se, _ = clustered_mean(g[y] * 1e4, g["date"])
            row[f"{y}_bps"] = m
            row[f"{y}_se"] = se
        rows.append(row)
    return pd.DataFrame(rows)


def matched_excess(p: pd.DataFrame, sort_col: str = "flow_adv", y: str = "on1_x_w", top_q: float = 0.9) -> pd.DataFrame:
    """Top |flow| treated days vs untreated stocks on the same date with the same
    sign of move and the same standardized-move bucket (|r_t| / vol60).
    Excess signed reversal = treated - matched control."""
    p = p.copy()
    p["z"] = (p["r_t"] / p["vol60"]).abs()
    p["zb"] = pd.cut(p["z"], [0, 0.5, 1, 1.5, 2, 3, 4, 6, np.inf], labels=False)
    p["sgn"] = np.sign(p["r_t"])
    ctl = p[~p["treated"]].groupby(["date", "sgn", "zb"])[y].agg(["mean", "size"]).rename(columns={"mean": "ctl", "size": "n_ctl"})
    t = p[p["treated"] & p[sort_col].notna()].copy()
    cut = t[sort_col].abs().quantile(top_q)
    t = t[t[sort_col].abs() >= cut]
    t = t.join(ctl, on=["date", "sgn", "zb"])
    t = t[t["n_ctl"] >= 3]
    s = -np.sign(t[sort_col])
    t["rev_treated"] = s * t[y] * 1e4
    t["rev_ctl"] = s * t["ctl"] * 1e4
    t["excess"] = t["rev_treated"] - t["rev_ctl"]
    rows = []
    for name, g in [("all", t), *[(f"year={k}", v) for k, v in t.groupby("year")],
                    ("up days", t[t["r_t"] > 0]), ("down days", t[t["r_t"] < 0])]:
        r = dict(subset=name, n=len(g), n_dates=g["date"].nunique())
        for c in ("rev_treated", "rev_ctl", "excess"):
            m, se, _ = clustered_mean(g[c], g["date"])
            r[c + "_bps"], r[c + "_se"] = m, se
        rows.append(r)
    return pd.DataFrame(rows), t


def concentration(t: pd.DataFrame, col: str = "rev_treated") -> dict:
    by_day = t.groupby("date")[col].sum()
    by_name = t.groupby("ticker")[col].sum()
    tot = t[col].sum()
    return dict(
        total=tot,
        share_top10_days=by_day.nlargest(10).sum() / tot if tot else np.nan,
        share_top5_names=by_name.nlargest(5).sum() / tot if tot else np.nan,
        top5_names=", ".join(by_name.nlargest(5).index),
        total_ex_top10_days=tot - by_day.nlargest(10).sum(),
    )


def main():
    REP.mkdir(exist_ok=True)
    f = PANEL / "panel_all.parquet"
    p = pd.read_parquet(f if f.exists() else PANEL / "panel_treated.parquet")
    p = prepare(p)
    print(f"sample: {len(p):,} stock-days, {p['ticker'].nunique()} stocks, treated days {p['treated'].sum():,}")
    reg = regressions(p)
    reg.to_csv(REP / "baseline_regressions.csv", index=False)
    ws = within_stock(p)
    ws.to_csv(REP / "baseline_within_stock.csv", index=False)
    dec = decile_table(p, "flow_adv_w", ["on1_x_w", "oc1_x_w", "cc1_x_w", "cc5_x_w"])
    dec.to_csv(REP / "baseline_deciles_flow.csv", index=False)
    decp = decile_table(p[p["r_pre"].notna()], "flow_pre_adv_w", ["r_last30_x_w", "on1_x_w", "cc1_x_w"])
    decp.to_csv(REP / "baseline_deciles_flow_pre.csv", index=False)
    mx_on, t_on = matched_excess(p, "flow_adv_w", "on1_x_w")
    mx_cc, t_cc = matched_excess(p, "flow_adv_w", "cc1_x_w")
    mx = pd.concat([mx_on.assign(y="on1_x"), mx_cc.assign(y="cc1_x")])
    mx.to_csv(REP / "baseline_matched_excess.csv", index=False)
    conc = pd.DataFrame([concentration(t_on, "rev_treated") | {"y": "on1_x", "col": "rev_treated"},
                         concentration(t_on, "excess") | {"y": "on1_x", "col": "excess"},
                         concentration(t_cc, "excess") | {"y": "cc1_x", "col": "excess"}])
    conc.to_csv(REP / "baseline_concentration.csv", index=False)
    pd.set_option("display.width", 220)
    fmt = lambda v: f"{v:,.4f}"
    print(reg[reg["var"].str.startswith("flow")].to_string(float_format=fmt))
    print(ws[ws["var"] == "flow_adv_w"].to_string(float_format=fmt))
    print(dec.to_string(float_format=lambda v: f"{v:,.2f}"))
    print(decp.to_string(float_format=lambda v: f"{v:,.2f}"))
    print(mx.to_string(float_format=lambda v: f"{v:,.2f}"))
    print(conc.to_string())


if __name__ == "__main__":
    main()
