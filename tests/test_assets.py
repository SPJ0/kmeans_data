import numpy as np
import pandas as pd
import pytest

from flows.assets import holdout_errors, reconstruct


def _setup():
    dates = pd.bdate_range("2024-01-01", "2024-06-28")
    rng = np.random.default_rng(1)
    ret = pd.Series(rng.normal(0, 0.03, len(dates)), index=dates)
    return dates, ret


def test_hits_anchors_exactly():
    dates, ret = _setup()
    nf = pd.DataFrame({"report_date": pd.to_datetime(["2024-03-29", "2024-06-28"]),
                       "net_assets": [100e6, 250e6],
                       "sales_flow_mon1": [0, 50e6], "redemption_flow_mon1": [0, 0],
                       "sales_flow_mon2": [0, 50e6], "redemption_flow_mon2": [0, 10e6],
                       "sales_flow_mon3": [0, 30e6], "redemption_flow_mon3": [0, 0]})
    out = reconstruct(dates, ret, nf, inception=dates[0], end=None)
    assert out.loc["2024-03-29", "A"] == pytest.approx(100e6)
    assert out.loc["2024-06-28", "A"] == pytest.approx(250e6)
    assert out.loc["2024-03-29", "src"] == "anchor"
    assert (out.loc["2024-04-01":"2024-06-27", "src"] == "interp_flows").all()
    assert (out["A"] > 0).all()


def test_no_flow_path_follows_fund_return():
    dates, ret = _setup()
    nf = pd.DataFrame({"report_date": pd.to_datetime(["2024-03-29"]), "net_assets": [100e6]})
    out = reconstruct(dates, ret, nf, inception=dates[0], end=None)
    after = out.loc["2024-03-29":]
    implied = after["A"].pct_change().dropna()
    np.testing.assert_allclose(implied.to_numpy(), ret.loc[implied.index].to_numpy(), rtol=1e-9)
    assert (after["src"].iloc[1:] == "extrapolated").all()


def test_current_anchor_and_end():
    dates, ret = _setup()
    nf = pd.DataFrame({"report_date": pd.to_datetime(["2024-02-29"]), "net_assets": [50e6]})
    out = reconstruct(dates, ret, nf, inception=dates[10], end=pd.Timestamp("2024-06-14"),
                      current=(pd.Timestamp("2024-06-14"), 80e6))
    assert out.index[0] == dates[10] and out.index[-1] == pd.Timestamp("2024-06-14")
    assert out["A"].iloc[-1] == pytest.approx(80e6)


def test_holdout_perfect_when_flows_consistent():
    dates = pd.bdate_range("2024-01-01", "2024-06-28")
    ret = pd.Series(0.0, index=dates)
    nf = pd.DataFrame({"report_date": pd.to_datetime(["2024-03-29", "2024-06-28"]),
                       "net_assets": [100e6, 160e6],
                       "sales_flow_mon1": [0, 20e6], "redemption_flow_mon1": [0, 0],
                       "sales_flow_mon2": [0, 20e6], "redemption_flow_mon2": [0, 0],
                       "sales_flow_mon3": [0, 20e6], "redemption_flow_mon3": [0, 0]})
    h = holdout_errors(dates, ret, nf)
    assert h["pred_with_flow"].iloc[0] == pytest.approx(160e6)
    assert h["pred_no_flow"].iloc[0] == pytest.approx(100e6)
