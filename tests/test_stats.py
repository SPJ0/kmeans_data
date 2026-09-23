import numpy as np
import pandas as pd

from analysis.stats import clustered_mean, fe_ols


def test_fe_ols_recovers_coefficients_with_date_effects():
    rng = np.random.default_rng(0)
    n_dates, n_stocks = 300, 40
    d = pd.DataFrame(
        [(t, s) for t in range(n_dates) for s in range(n_stocks)], columns=["date", "ticker"]
    )
    date_shock = rng.normal(0, 1, n_dates)[d["date"]]
    d["x1"] = rng.normal(size=len(d)) + 0.5 * date_shock
    d["x2"] = rng.normal(size=len(d))
    d["y"] = 0.3 * d["x1"] - 0.2 * d["x2"] + 2.0 * date_shock + rng.normal(0, 0.5, len(d))
    r = fe_ols(d, "y", ["x1", "x2"])
    assert abs(r.loc["x1", "coef"] - 0.3) < 0.02
    assert abs(r.loc["x2", "coef"] + 0.2) < 0.02
    assert (r["se"] > 0).all()


def test_clustered_mean_inflates_se_under_within_cluster_correlation():
    rng = np.random.default_rng(1)
    g = np.repeat(np.arange(50), 20)
    y = rng.normal(0, 1, 50)[g] + rng.normal(0, 0.1, len(g))
    m, se, n = clustered_mean(pd.Series(y), pd.Series(g))
    naive = y.std(ddof=1) / np.sqrt(len(y))
    assert n == 1000 and se > 3 * naive
