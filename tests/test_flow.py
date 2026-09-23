import numpy as np
import pandas as pd
import pytest

from flows.flow import (auction_proxy, gamma_multiplier, rebalance_trade,
                        rebalance_trade_simple, stock_aggregates)


@pytest.mark.parametrize("L,mult", [(2, 2), (-1, 2), (-2, 6), (3, 6), (-3, 12), (1.5, 0.75),
                                    (1.25, 0.3125), (1, 0), (0, 0)])
def test_multiplier_table(L, mult):
    assert gamma_multiplier(L) == pytest.approx(mult)


# Hand-worked: A_prev=100, r=+10%.
@pytest.mark.parametrize("L,expected", [
    (2, 20.0),     # E=200 -> 220; A=120 -> target 240; buy 20
    (1.5, 7.5),    # E=150 -> 165; A=115 -> target 172.5; buy 7.5
    (-1, 20.0),    # E=-100 -> -110; A=90 -> target -90; buy 20 (cover)
    (-2, 60.0),    # E=-200 -> -220; A=80 -> target -160; buy 60
    (3, 60.0),     # E=300 -> 330; A=130 -> target 390; buy 60
])
def test_hand_worked(L, expected):
    assert rebalance_trade(L, 100.0, 0.10) == pytest.approx(expected)
    assert rebalance_trade_simple(L, 100.0, 0.10) == pytest.approx(expected)


@pytest.mark.parametrize("L", [2, 1.5, -1, -2, 3, -3, 1.25])
def test_long_and_inverse_trade_with_the_move(L):
    # both long and inverse funds buy after up days and sell after down days
    assert rebalance_trade(L, 50.0, 0.04) > 0
    assert rebalance_trade(L, 50.0, -0.04) < 0


def test_general_matches_simple_when_on_target():
    rng = np.random.default_rng(0)
    L = rng.choice([2, 1.5, -1, -2, 3, -3, 1.25], 1000)
    A = rng.uniform(1e6, 1e9, 1000)
    r = rng.normal(0, 0.05, 1000)
    np.testing.assert_allclose(rebalance_trade(L, A, r), rebalance_trade_simple(L, A, r), rtol=1e-9, atol=1e-3)


def test_general_exposure_off_target():
    # under-exposed 2x fund: E=190 on A=100, r=+10%: A=119, target 238, drifted 209 -> buy 29
    assert rebalance_trade(2, 100.0, 0.10, E_prev=190.0) == pytest.approx(29.0)
    # zero return still closes the gap to target: 200 - 190 = 10
    assert rebalance_trade(2, 100.0, 0.0, E_prev=190.0) == pytest.approx(10.0)


@pytest.mark.parametrize("L", [2, -2, 3, 1.5, -1])
def test_post_trade_exposure_hits_target(L):
    A_prev, E_prev, r = 250.0, L * 250.0 * 1.03, -0.07
    T = rebalance_trade(L, A_prev, r, E_prev)
    A_now = A_prev + E_prev * r
    assert E_prev * (1 + r) + T == pytest.approx(L * A_now)


def test_unlevered_fund_never_trades():
    assert rebalance_trade(1, 123.0, 0.2) == pytest.approx(0.0)


def test_stock_aggregates_stack():
    fd = pd.DataFrame({"underlying": ["X", "X", "Y"], "date": ["d", "d", "d"],
                       "L": [2, -2, 2], "A_prev": [100.0, 100.0, 10.0], "r": [0.1, 0.1, -0.05]})
    out = stock_aggregates(fd).set_index("underlying")
    assert out.loc["X", "Flow"] == pytest.approx(20 + 60)       # long and inverse stack
    assert out.loc["X", "Gamma"] == pytest.approx(200 + 600)
    assert out.loc["X", "Gamma_inv"] == pytest.approx(600)
    assert out.loc["Y", "Flow"] == pytest.approx(10 * 2 * -0.05)
    assert out.loc["X", "n_funds"] == 2


def test_auction_proxy_is_lagged():
    dv = pd.Series(np.arange(1, 31, dtype=float))
    ap = auction_proxy(dv)
    assert ap.iloc[:20].isna().all()                       # needs 20 prior days
    assert ap.iloc[20] == pytest.approx(0.1 * np.mean(np.arange(1, 21)))  # excludes day 21 itself
