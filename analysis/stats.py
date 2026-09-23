"""Regression helpers: date fixed effects by within-date demeaning (exact for
OLS with one FE, by Frisch-Waugh-Lovell) and one- or two-way clustered SEs."""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm


def winsorize(s: pd.Series, lo: float, hi: float) -> pd.Series:
    a, b = s.quantile([lo, hi])
    return s.clip(a, b)


def fe_ols(df: pd.DataFrame, y: str, xs: list[str], fe: str | None = "date",
           cluster: tuple[str, ...] = ("date", "ticker")) -> pd.DataFrame:
    """OLS of y on xs with an optional absorbed fixed effect and clustered SEs.

    Returns a table: coef, se, t, n, and the number of clusters.
    """
    d = df[[y, *xs, *(c for c in cluster if c not in (y, *xs)), *([fe] if fe and fe not in cluster else [])]].dropna()
    Y = d[y].astype(float)
    X = d[xs].astype(float)
    if fe:
        Y = Y - Y.groupby(d[fe]).transform("mean")
        X = X - X.groupby(d[fe]).transform("mean")
    else:
        X = sm.add_constant(X)
    groups = np.column_stack([pd.factorize(d[c])[0] for c in cluster]) if len(cluster) > 1 else pd.factorize(d[cluster[0]])[0]
    res = sm.OLS(Y.values, X.values).fit(cov_type="cluster", cov_kwds={"groups": groups})
    names = list(X.columns)
    out = pd.DataFrame({"coef": res.params, "se": res.bse, "t": res.tvalues}, index=names)
    out["n"] = len(d)
    out["n_dates"] = d["date"].nunique() if "date" in d else np.nan
    out["n_stocks"] = d["ticker"].nunique() if "ticker" in d else np.nan
    return out


def clustered_mean(s: pd.Series, groups: pd.Series) -> tuple[float, float, int]:
    """Mean with SE clustered by ``groups`` (e.g. date)."""
    d = pd.DataFrame({"y": s, "g": groups}).dropna()
    if len(d) < 3:
        return np.nan, np.nan, len(d)
    res = sm.OLS(d["y"].values, np.ones(len(d))).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d["g"])[0]})
    return float(res.params[0]), float(res.bse[0]), len(d)
