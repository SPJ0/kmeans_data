"""Leveraged-ETF rebalancing flow.

For fund i with target leverage L, prior-close net assets A_{t-1}, prior-close
dollar exposure E_{t-1} and underlying close-to-close return r_t:

    A_t  = A_{t-1} + E_{t-1} * r_t              (fees/financing ignored)
    T_t  = L * A_t - E_{t-1} * (1 + r_t)         (dollars, + = buy)

With E_{t-1} = L * A_{t-1} this is T_t = A_{t-1} * L * (L - 1) * r_t.
L*(L-1) > 0 for L > 1 and L < 0, so long and inverse funds trade in the
same direction and stack.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def gamma_multiplier(L):
    """L * (L - 1): dollars traded per dollar of assets per unit return."""
    L = np.asarray(L, dtype=float)
    return L * (L - 1.0)


def rebalance_trade(L, A_prev, r, E_prev=None):
    """Required rebalance trade in dollars (+ = buy the underlying).

    ``E_prev`` defaults to ``L * A_prev`` (fund exactly on target at prior close).
    Works elementwise on scalars / arrays / Series.
    """
    L = np.asarray(L, dtype=float)
    A_prev = np.asarray(A_prev, dtype=float)
    r = np.asarray(r, dtype=float)
    E_prev = L * A_prev if E_prev is None else np.asarray(E_prev, dtype=float)
    A_now = A_prev + E_prev * r
    return L * A_now - E_prev * (1.0 + r)


def rebalance_trade_simple(L, A_prev, r):
    """Closed form when E_prev == L * A_prev."""
    return np.asarray(A_prev, dtype=float) * gamma_multiplier(L) * np.asarray(r, dtype=float)


def creation_trade(L, net_new_money):
    """Underlying trade from creations/redemptions (not known live; modelled separately)."""
    return np.asarray(L, dtype=float) * np.asarray(net_new_money, dtype=float)


def stock_aggregates(fund_days: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fund-day rows to stock-day rows.

    ``fund_days`` needs columns: underlying, date, L, A_prev, r and optionally
    E_prev. Returns Flow (sum of T), Gamma (sum of A*L*(L-1)), and the long /
    inverse split of Gamma plus fund counts.
    """
    fd = fund_days.copy()
    E = fd["E_prev"] if "E_prev" in fd else None
    fd["T"] = rebalance_trade(fd["L"], fd["A_prev"], fd["r"], E)
    fd["G"] = fd["A_prev"] * gamma_multiplier(fd["L"])
    fd["G_long"] = np.where(fd["L"] > 0, fd["G"], 0.0)
    fd["G_inv"] = np.where(fd["L"] < 0, fd["G"], 0.0)
    fd["A_long"] = np.where(fd["L"] > 0, fd["A_prev"], 0.0)
    fd["A_inv"] = np.where(fd["L"] < 0, fd["A_prev"], 0.0)
    g = fd.groupby(["underlying", "date"], sort=True)
    out = g.agg(Flow=("T", "sum"), Gamma=("G", "sum"), Gamma_long=("G_long", "sum"),
                Gamma_inv=("G_inv", "sum"), A_long=("A_long", "sum"), A_inv=("A_inv", "sum"),
                n_funds=("T", "size"))
    return out.reset_index()


def auction_proxy(dollar_volume: pd.Series, window: int = 20, frac: float = 0.10) -> pd.Series:
    """0.10 * 20-day average dollar volume, lagged one day (no look-ahead).

    ``dollar_volume`` must be a single stock's series indexed by date.
    """
    return frac * dollar_volume.rolling(window, min_periods=window).mean().shift(1)
