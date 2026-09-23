"""Small statistics helpers: date-clustered means and FE regressions."""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm


def clustered_mean(y: pd.Series, groups: pd.Series) -> dict:
    """Mean of y with standard error clustered by ``groups`` (e.g. date)."""
    m = y.notna() & groups.notna()
    y, g = y[m].astype(float), groups[m]
    if len(y) < 3 or g.nunique() < 3:
        return {"mean": y.mean() if len(y) else np.nan, "se": np.nan, "t": np.nan, "n": len(y),
                "n_clusters": g.nunique()}
    X = np.ones((len(y), 1))
    res = sm.OLS(y.to_numpy(), X).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(g)[0]})
    return {"mean": res.params[0], "se": res.bse[0], "t": res.tvalues[0], "n": len(y),
            "n_clusters": g.nunique()}


def clustered_mean_2way(y: pd.Series, g1: pd.Series, g2: pd.Series) -> dict:
    """Mean with SEs clustered two ways (e.g. date and stock)."""
    m = y.notna() & g1.notna() & g2.notna()
    y = y[m].astype(float)
    groups = np.column_stack([pd.factorize(g1[m])[0], pd.factorize(g2[m])[0]])
    res = sm.OLS(y.to_numpy(), np.ones((len(y), 1))).fit(cov_type="cluster", cov_kwds={"groups": groups})
    return {"mean": res.params[0], "se": res.bse[0], "t": res.tvalues[0], "n": len(y)}


def demean(df: pd.DataFrame, cols, by) -> pd.DataFrame:
    out = df[cols].astype(float)
    for b in ([by] if isinstance(by, str) else by):
        out = out - out.groupby(df[b]).transform("mean")
    return out


def fe_ols(df: pd.DataFrame, y: str, xs: list[str], fe=("date",), cluster=("date",), iters: int = 1) -> pd.DataFrame:
    """OLS of y on xs absorbing fixed effects by (alternating) demeaning; clustered SEs.

    With two FE dimensions the alternating projection is iterated ``iters`` times
    (approximate but adequate for coefficient/SE reporting on an unbalanced panel).
    """
    d = df.dropna(subset=[y] + xs + list(fe) + list(cluster)).copy()
    Z = d[[y] + xs].astype(float)
    for _ in range(max(iters, 1)):
        for f in fe:
            Z = Z - Z.groupby(d[f]).transform("mean")
    X, Y = Z[xs].to_numpy(), Z[y].to_numpy()
    if len(cluster) == 1:
        groups = pd.factorize(d[cluster[0]])[0]
    else:
        groups = np.column_stack([pd.factorize(d[c])[0] for c in cluster])
    res = sm.OLS(Y, X).fit(cov_type="cluster", cov_kwds={"groups": groups})
    return pd.DataFrame({"coef": res.params, "se": res.bse, "t": res.tvalues}, index=xs).assign(
        n=len(d), n_dates=d["date"].nunique(), r2_within=res.rsquared)
