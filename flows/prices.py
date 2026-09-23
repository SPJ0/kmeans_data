"""Daily OHLCV from Yahoo (yfinance) with a per-ticker parquet cache and sanity filters.

Conventions
  * yfinance ``Close`` is split-adjusted; ``Adj Close`` is split+dividend adjusted.
    Close is taken as the official closing-auction price (our entry); Open as an
    approximation of the opening-cross price.
  * Returns use dividend-adjusted prices; the open is put on the same basis
    with the day's AdjClose/Close factor so ex-dividend gaps are not counted as
    overnight returns.
  * Download window is fixed (START..END) so reruns are reproducible.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from common.paths import CACHE

PRICE_DIR = CACHE / "prices"
START = "2021-06-01"
END = "2026-09-23"   # exclusive -> data through 2026-09-22
FIELDS = ["Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends", "Stock Splits"]


def _path(t: str):
    return PRICE_DIR / f"{t.replace('/', '_')}.parquet"


def _empty_marker(t: str):
    return PRICE_DIR / f"{t.replace('/', '_')}.empty"


def download(tickers, batch: int = 80, pause: float = 2.0, refresh: bool = False) -> None:
    """Fetch any tickers not yet cached. Tickers Yahoo has no data for get an .empty marker."""
    import yfinance as yf
    PRICE_DIR.mkdir(parents=True, exist_ok=True)
    todo = [t for t in dict.fromkeys(tickers)
            if refresh or not (_path(t).exists() or _empty_marker(t).exists())]
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        for attempt in range(4):
            try:
                df = yf.download(chunk, start=START, end=END, auto_adjust=False, actions=True, progress=False,
                                 group_by="ticker", threads=True, timeout=60)
                break
            except Exception as e:  # throttled / network: back off
                print("yfinance error", e, "retrying", flush=True)
                time.sleep(pause * 2 ** (attempt + 1))
        else:
            continue
        for t in chunk:
            try:
                sub = df[t] if isinstance(df.columns, pd.MultiIndex) else df
            except KeyError:
                sub = pd.DataFrame()
            sub = sub.reindex(columns=FIELDS)
            sub = sub.dropna(subset=["Close"])
            if sub.empty:
                _empty_marker(t).write_text("")
                continue
            sub.index = pd.to_datetime(sub.index).tz_localize(None).normalize()
            sub.index.name = "date"
            sub.to_parquet(_path(t))
        print(f"prices {min(i + batch, len(todo))}/{len(todo)}", flush=True)
        time.sleep(pause)


SNAPSHOT = CACHE / "prices_snapshot.parquet"   # committed consolidated copy of the per-ticker cache
_snap: dict | None = None


def load(t: str) -> pd.DataFrame | None:
    p = _path(t)
    if p.exists():
        return pd.read_parquet(p)
    global _snap
    if _snap is None:
        _snap = ({k: g.drop(columns="ticker") for k, g in pd.read_parquet(SNAPSHOT).groupby("ticker")}
                 if SNAPSHOT.exists() else {})
    return _snap.get(t)


def write_snapshot() -> None:
    """Consolidate the per-ticker cache into one zstd parquet (what gets committed)."""
    parts = [pd.read_parquet(p).assign(ticker=p.stem) for p in sorted(PRICE_DIR.glob("*.parquet"))]
    pd.concat(parts).to_parquet(SNAPSHOT, compression="zstd")


def clean(t: str, df: pd.DataFrame) -> pd.DataFrame:
    """Per-ticker daily frame with adjusted returns and data-quality flags."""
    d = df.copy().sort_index()
    d = d[~d.index.duplicated(keep="last")]
    d = d[(d["Close"] > 0) & d["Close"].notna()]
    adj = (d["Adj Close"] / d["Close"]).where(lambda x: (x > 0) & (x <= 1.5)).ffill().fillna(1.0)
    o = d["Open"].where(d["Open"] > 0)
    out = pd.DataFrame(index=d.index)
    out["ticker"] = t
    out["open"], out["high"], out["low"], out["close"] = o, d["High"], d["Low"], d["Close"]
    out["volume"] = d["Volume"]
    out["dollar_volume"] = d["Close"] * d["Volume"]
    out["adj_close"] = d["Close"] * adj
    out["adj_open"] = o * adj
    out["r_cc"] = out["adj_close"].pct_change()                                  # close_{t-1} -> close_t
    out["r_co_next"] = out["adj_open"].shift(-1) / out["adj_close"] - 1          # close_t -> open_{t+1}
    out["r_cc_next"] = out["adj_close"].shift(-1) / out["adj_close"] - 1         # close_t -> close_{t+1}
    out["r_oc_next"] = out["adj_close"].shift(-1) / out["adj_open"].shift(-1) - 1  # open_{t+1} -> close_{t+1}
    out["r_oc"] = out["adj_close"] / out["adj_open"] - 1                        # open_t -> close_t (same day)
    split = d["Stock Splits"].fillna(0)
    near_split = (split > 0) | (split.shift(1) > 0) | (split.shift(-1) > 0)
    big = out["r_cc"].abs() > 0.5
    # a >50% move that coincides with a split Yahoo did not adjust for
    bad_split = big & near_split
    ratio = out["close"] / out["close"].shift(1)
    split_like = big & ratio.apply(lambda x: np.isfinite(x) and any(
        abs(x - k) / k < 0.03 for k in (2, 3, 4, 5, 10, 20, 0.5, 1 / 3, 0.25, 0.2, 0.1, 0.05)))
    out["flag_bad_split"] = bad_split | split_like
    out["flag_big_move"] = big
    out["flag_open_outside"] = (o > d["High"] * 1.001) | (o < d["Low"] * 0.999)
    out["flag_zero_vol"] = d["Volume"].fillna(0) <= 0
    # stale: identical OHLC to prior day with tiny volume (Yahoo fills halted days this way)
    out["flag_stale"] = (d["Close"] == d["Close"].shift(1)) & (d["Open"] == d["Open"].shift(1)) & (
        d["High"] == d["High"].shift(1))
    bad = out["flag_bad_split"] | out["flag_open_outside"] | out["flag_zero_vol"] | out["flag_stale"]
    out["bad_today"] = bad
    # outcome windows touching a bad day are unusable
    out["bad_next"] = bad.shift(-1, fill_value=False) | bad
    return out


def panel(tickers) -> pd.DataFrame:
    parts = []
    for t in tickers:
        df = load(t)
        if df is not None and len(df) > 5:
            parts.append(clean(t, df).reset_index())
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


if __name__ == "__main__":
    # universe ETFs + underlyings, index funds, benchmarks, placebo pool
    from common.paths import RAW, UNIVERSE
    u = pd.read_csv(UNIVERSE / "single_stock_candidates.csv")
    ix = pd.read_csv(UNIVERSE / "index_candidates.csv")
    pool = pd.read_csv(sorted((RAW / "lists").glob("placebo_pool_*.csv"))[-1])["ticker"]
    bench = ["SPY", "QQQ", "SMH", "BITO", "IBIT", "GBTC", "IWM", "SOXX", "XLK", "ARKK", "DIA", "XLF", "XBI", "XLE",
             "KRE", "FXI"]
    download(bench + sorted(set(u["ticker"].dropna()) | set(u["underlying"].dropna()) | set(ix["ticker"].dropna()))
             + list(pool))
    write_snapshot()
