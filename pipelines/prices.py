"""Daily and hourly price downloads from Yahoo (yfinance), cached to parquet.

Every download is cached per ticker; reruns never re-hit Yahoo unless
``refresh=True``. Daily bars are stored unadjusted (``Close`` = Yahoo close,
split-adjusted only) together with ``Adj Close`` (splits + dividends).
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
DAILY_DIR = ROOT / "data" / "raw" / "yahoo_daily"
HOURLY_DIR = ROOT / "data" / "raw" / "yahoo_1h"
START = "2018-01-01"


def _path(d: Path, ticker: str) -> Path:
    return d / f"{ticker.replace('/', '_')}.parquet"


def _missing(tickers, d: Path, refresh: bool):
    d.mkdir(parents=True, exist_ok=True)
    return [t for t in dict.fromkeys(tickers) if refresh or not _path(d, t).exists()]


def download_daily(tickers, refresh: bool = False, batch: int = 50, pause: float = 1.0) -> None:
    """Fetch daily OHLCV for tickers not yet cached. Empty results are cached too
    (as an empty frame) so dead tickers are not retried every run."""
    todo = _missing(tickers, DAILY_DIR, refresh)
    for i in range(0, len(todo), batch):
        chunk = todo[i : i + batch]
        raw = yf.download(
            chunk, start=START, auto_adjust=False, actions=False, group_by="ticker",
            progress=False, threads=True,
        )
        for t in chunk:
            try:
                df = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
            except KeyError:
                df = pd.DataFrame()
            df = df.dropna(how="all")
            df.index.name = "date"
            df.to_parquet(_path(DAILY_DIR, t))
        time.sleep(pause)


def download_hourly(tickers, refresh: bool = False, batch: int = 25, pause: float = 1.0) -> None:
    """Fetch 60-minute bars (Yahoo keeps ~730 days)."""
    todo = _missing(tickers, HOURLY_DIR, refresh)
    for i in range(0, len(todo), batch):
        chunk = todo[i : i + batch]
        raw = yf.download(
            chunk, period="730d", interval="60m", auto_adjust=False, actions=False,
            group_by="ticker", progress=False, threads=True, prepost=False,
        )
        for t in chunk:
            try:
                df = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
            except KeyError:
                df = pd.DataFrame()
            df = df.dropna(how="all")
            df.index.name = "ts"
            df.to_parquet(_path(HOURLY_DIR, t))
        time.sleep(pause)


def load_daily(ticker: str) -> pd.DataFrame:
    p = _path(DAILY_DIR, ticker)
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p)
    if df.empty:
        return df
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return clean_daily(df)


def load_hourly(ticker: str) -> pd.DataFrame:
    p = _path(HOURLY_DIR, ticker)
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p)
    if not df.empty:
        idx = pd.to_datetime(df.index)
        if idx.tz is None:
            idx = idx.tz_localize("UTC")
        df.index = idx.tz_convert("America/New_York")
    return df


def clean_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Sanity filters. Adds a ``bad`` flag rather than dropping rows."""
    df = df.copy()
    df = df[~df.index.duplicated(keep="last")].sort_index()
    for c in ("Open", "High", "Low", "Close", "Adj Close"):
        if c in df:
            df.loc[df[c] <= 0, c] = np.nan
    bad = df["Close"].isna() | df["Open"].isna() | (df["Volume"] <= 0)
    # Open/Close outside the day's range means a bad print.
    bad |= (df["Open"] > df["High"] * 1.001) | (df["Open"] < df["Low"] * 0.999)
    bad |= (df["Close"] > df["High"] * 1.001) | (df["Close"] < df["Low"] * 0.999)
    # Isolated spikes: a > 60% move that fully reverses the next day.
    r = np.log(df["Close"]).diff()
    bad |= (r.abs() > 0.47) & (r.shift(-1).abs() > 0.47) & (np.sign(r) != np.sign(r.shift(-1)))
    df["bad"] = bad
    return df
