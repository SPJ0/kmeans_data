import numpy as np
import pandas as pd
import pytest

from flows.rebalance import (
    creation_trade,
    multiplier,
    rebalance_trade,
    rebalance_trade_on_target,
    stock_flows,
)

LEVERAGES = [2.0, 1.5, 1.25, 1.75, 3.0, -1.0, -2.0, -3.0]
RETURNS = [-0.25, -0.05, -0.001, 0.0, 0.003, 0.07, 0.30]


@pytest.mark.parametrize(
    "L, expected", [(2, 2), (-1, 2), (-2, 6), (3, 6), (-3, 12), (1.5, 0.75), (1.25, 0.3125), (1, 0)]
)
def test_multiplier_table(L, expected):
    assert multiplier(L) == pytest.approx(expected)


@pytest.mark.parametrize("L", LEVERAGES)
@pytest.mark.parametrize("r", RETURNS)
def test_general_matches_simplified_when_on_target(L, r):
    A = 100e6
    assert rebalance_trade(A, L, r) == pytest.approx(rebalance_trade_on_target(A, L, r))
    assert rebalance_trade(A, L, r, exposure_prev=L * A) == pytest.approx(
        rebalance_trade_on_target(A, L, r)
    )


@pytest.mark.parametrize("L", LEVERAGES)
@pytest.mark.parametrize("r", RETURNS)
def test_trade_restores_target_exposure(L, r):
    A, E = 50e6, 0.8 * L * 50e6  # deliberately off target
    T = rebalance_trade(A, L, r, exposure_prev=E)
    assets_now = A + E * r
    exposure_now = E * (1 + r) + T
    assert exposure_now == pytest.approx(L * assets_now)


def test_worked_example_2x():
    # $100 fund, 2x, stock +10%: exposure 200 -> 220, assets 100 -> 120,
    # target 240, so buy 20 = 100 * 2 * 1 * 0.10.
    assert rebalance_trade(100.0, 2.0, 0.10) == pytest.approx(20.0)


def test_worked_example_minus2x():
    # $100 fund, -2x, stock +10%: exposure -200 -> -220, assets 100 -> 80,
    # target -160, so buy 60 = 100 * (-2) * (-3) * 0.10.
    assert rebalance_trade(100.0, -2.0, 0.10) == pytest.approx(60.0)


@pytest.mark.parametrize("L", [1.25, 1.5, 2.0, 3.0, -1.0, -2.0, -3.0])
def test_long_and_inverse_trade_with_the_move(L):
    assert rebalance_trade(1.0, L, 0.05) > 0
    assert rebalance_trade(1.0, L, -0.05) < 0


def test_unlevered_fund_never_trades():
    assert rebalance_trade(1e6, 1.0, 0.2) == pytest.approx(0.0)


def test_zero_return_zero_trade():
    for L in LEVERAGES:
        assert rebalance_trade(1e6, L, 0.0) == pytest.approx(0.0)


def test_underexposed_fund_buys_catch_up_even_on_flat_day():
    # Swap capacity constrained: 2x fund with $100 assets but only $150 exposure.
    assert rebalance_trade(100.0, 2.0, 0.0, exposure_prev=150.0) == pytest.approx(50.0)


def test_vectorized():
    A = np.array([1.0, 2.0, 3.0])
    L = np.array([2.0, -1.0, 3.0])
    r = np.array([0.1, -0.1, 0.02])
    np.testing.assert_allclose(rebalance_trade(A, L, r), A * L * (L - 1) * r)


def test_creation_trade():
    assert creation_trade(10.0, 2.0) == pytest.approx(20.0)
    assert creation_trade(10.0, -2.0) == pytest.approx(-20.0)


def test_stock_flows_stack_long_and_inverse():
    d = pd.Timestamp("2025-01-02")
    fund_days = pd.DataFrame(
        {
            "date": [d, d, d],
            "underlying": ["XYZ", "XYZ", "ABC"],
            "leverage": [2.0, -2.0, 1.5],
            "assets_prev": [100.0, 50.0, 10.0],
            "ret": [0.10, 0.10, -0.04],
            "exposure_prev": [np.nan, -100.0, np.nan],
        }
    )
    out = stock_flows(fund_days).set_index("underlying")
    # XYZ: 100*2*1*0.1 + 50*6*0.1 = 20 + 30
    assert out.loc["XYZ", "flow"] == pytest.approx(50.0)
    assert out.loc["XYZ", "gamma"] == pytest.approx(100 * 2 + 50 * 6)
    assert out.loc["XYZ", "n_funds"] == 2
    assert out.loc["ABC", "flow"] == pytest.approx(10 * 0.75 * -0.04)
