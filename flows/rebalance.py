"""Daily-reset leveraged ETF rebalancing flow.

Conventions
-----------
All amounts are in dollars. A positive trade means the fund (or its swap
dealer) must BUY the underlying. ``r`` is the underlying's return over the
fund's reset period (close-to-close for a daily-reset fund). Fees, financing
and creations/redemptions are ignored here; see ``creation_trade`` for the
latter.

For fund i with target leverage L, prior-close net assets A and prior-close
exposure E (dollar notional to the underlying):

    A_t = A + E * r                  # fund P&L from the move
    T   = L * A_t - E * (1 + r)      # trade needed to restore E_t = L * A_t

If the fund was on target (E = L * A) this reduces to

    T = A * L * (L - 1) * r

so long (L > 1) and inverse (L < 0) funds trade in the SAME direction.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def multiplier(leverage):
    """Flow per unit of assets per unit of return, L * (L - 1)."""
    L = np.asarray(leverage, dtype=float)
    return L * (L - 1.0)


def rebalance_trade(assets_prev, leverage, ret, exposure_prev=None):
    """General rebalance trade.

    ``exposure_prev`` defaults to ``leverage * assets_prev`` (on target). Pass
    the actual prior exposure (e.g. from a holdings file) when the fund was
    off target, such as when swap capacity was constrained.
    """
    A = np.asarray(assets_prev, dtype=float)
    L = np.asarray(leverage, dtype=float)
    r = np.asarray(ret, dtype=float)
    E = L * A if exposure_prev is None else np.asarray(exposure_prev, dtype=float)
    assets_now = A + E * r
    return L * assets_now - E * (1.0 + r)


def rebalance_trade_on_target(assets_prev, leverage, ret):
    """Simplified trade assuming the fund started the day on target."""
    return np.asarray(assets_prev, dtype=float) * multiplier(leverage) * np.asarray(ret, dtype=float)


def creation_trade(net_new_money, leverage):
    """Underlying trade implied by net creations (+) / redemptions (-)."""
    return np.asarray(leverage, dtype=float) * np.asarray(net_new_money, dtype=float)


def stock_flows(fund_days: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fund-level rebalance flow to stock-day level.

    ``fund_days`` needs columns: date, underlying, leverage, assets_prev, ret,
    and optionally exposure_prev (NaN means assume on target).

    Returns one row per (date, underlying) with:
      flow   -- sum of rebalance trades (dollars, + = buy)
      gamma  -- sum of A * L * (L - 1), the flow per unit return
      n_funds
    """
    df = fund_days.copy()
    if "exposure_prev" in df:
        exposure = df["exposure_prev"].fillna(df["leverage"] * df["assets_prev"])
    else:
        exposure = df["leverage"] * df["assets_prev"]
    df["flow"] = rebalance_trade(df["assets_prev"], df["leverage"], df["ret"], exposure)
    df["gamma"] = df["assets_prev"] * multiplier(df["leverage"])
    out = (
        df.groupby(["date", "underlying"], sort=True)
        .agg(flow=("flow", "sum"), gamma=("gamma", "sum"), n_funds=("flow", "size"))
        .reset_index()
    )
    return out
