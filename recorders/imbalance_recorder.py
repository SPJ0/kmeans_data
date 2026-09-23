"""Record the closing auction for leveraged-ETF underlyings via the IBKR API (ib_async).

Runs on your machine next to TWS or IB Gateway (API enabled, read-only is fine).
It places no orders.

    python -m recorders.imbalance_recorder                 # run today's session, then exit
    python -m recorders.imbalance_recorder --loop          # wait for each trading day, forever
    python -m recorders.imbalance_recorder --port 4001 --client-id 17 --max-lines 90

Timeline (US/Eastern; shifted automatically on early-close days via contract liquidHours):
  close-16m  ranking pass: stream every underlying in batches that fit the market-data line
             limit, take last vs prior close, predict flow from the latest holdings snapshot
             (recorders/live_flow.py) and rank by |flow| / (10% x 20-day $ volume)
  close-10.5m subscribe the top N with generic tick 225 (auction volume / price / imbalance /
             regulatory imbalance) and log every update plus a 1-second heartbeat of all fields
             until close+1m
  close+1m   optional IB scanner snapshots of the market-wide largest buy/sell imbalances
  close+15m  optional 1-minute bars for the recorded names (last-15-minute return, 3:45 price)

Output: data/imbalance/<YYYY-MM-DD>/
  ranking.parquet   every underlying: r at close-16m, predicted flow, gamma, flow_ratio, selected
  ticks.parquet     time-stamped last/bid/ask/volume + auction fields for the recorded names
  scanner.parquet   optional scanner results
  bars.parquet      optional 1-minute bars
  meta.json         settings, market-data type, counts, errors

Market data: tick 225 needs live (not delayed) US equity data on your account. If no
auction ticks arrive, meta.json says so. IBKR data subscriptions can cost money; this
script never changes subscriptions.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from common.paths import DATA
from recorders.live_flow import fund_state, predicted_flows

ET = ZoneInfo("America/New_York")
OUT = DATA / "imbalance"
AUCTION_FIELDS = ["auctionVolume", "auctionPrice", "auctionImbalance", "regulatoryImbalance"]
PRICE_FIELDS = ["last", "lastSize", "bid", "bidSize", "ask", "askSize", "volume", "close"]
SCAN_CODES = ["TOP_STOCK_BUY_IMBALANCE_ADV_RATIO", "TOP_STOCK_SELL_IMBALANCE_ADV_RATIO"]


def ib_symbol(t: str) -> str:
    return t.replace("-", " ")          # BRK-B -> "BRK B"


def parse_liquid_hours(liquid_hours: str, day: datetime) -> tuple[datetime, datetime] | None:
    """Regular session (open, close) for ``day`` from ContractDetails.liquidHours, or None if closed.

    Format: "20261127:0930-20261127:1300;20261128:CLOSED;..." (times in the contract's timezone).
    """
    key = day.strftime("%Y%m%d")
    for seg in liquid_hours.split(";"):
        if not seg.startswith(key):
            continue
        if "CLOSED" in seg:
            return None
        a, b = seg.split("-")
        o = datetime.strptime(a, "%Y%m%d:%H%M").replace(tzinfo=ET)
        c = datetime.strptime(b, "%Y%m%d:%H%M").replace(tzinfo=ET)
        return o, c
    return None


def _num(x):
    try:
        x = float(x)
        return x if np.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def adv20(tickers: list[str]) -> pd.Series:
    """20-day average dollar volume from Yahoo (free); empty on failure."""
    try:
        import yfinance as yf
        d = yf.download(tickers, period="2mo", auto_adjust=False, progress=False, group_by="ticker", threads=True)
        out = {}
        for t in tickers:
            try:
                sub = d[t].dropna(subset=["Close"])
                out[t] = float((sub["Close"] * sub["Volume"]).tail(20).mean())
            except KeyError:
                pass
        return pd.Series(out)
    except Exception as e:  # noqa: BLE001
        print("ADV fetch failed:", e)
        return pd.Series(dtype=float)


async def sleep_until(t: datetime):
    while True:
        dt = (t - datetime.now(ET)).total_seconds()
        if dt <= 0:
            return
        await asyncio.sleep(min(dt, 30))


class Session:
    def __init__(self, ib, args):
        self.ib, self.args = ib, args
        self.rows: list[dict] = []
        self.meta: dict = {"errors": []}

    async def contracts(self, tickers):
        from ib_async import Stock
        cs = [Stock(ib_symbol(t), "SMART", "USD") for t in tickers]
        await self.ib.qualifyContractsAsync(*cs)
        return {t: c for t, c in zip(tickers, cs) if c.conId}, [t for t, c in zip(tickers, cs) if not c.conId]

    async def ranking_pass(self, cmap: dict) -> pd.DataFrame:
        """Stream every underlying briefly (batches under the line limit) and read last vs prior close."""
        prices, n = {}, self.args.max_lines
        items = list(cmap.items())
        for i in range(0, len(items), n):
            batch = items[i:i + n]
            tks = {t: self.ib.reqMktData(c, "", False, False) for t, c in batch}
            await asyncio.sleep(self.args.rank_wait)
            for t, tk in tks.items():
                last = _num(tk.last) or _num(tk.marketPrice())
                prices[t] = {"last": last, "prior_close": _num(tk.close), "t": datetime.now(ET).isoformat()}
                self.ib.cancelMktData(tk.contract)
            await asyncio.sleep(1.0)
        px = pd.DataFrame(prices).T
        px["r"] = px["last"].astype(float) / px["prior_close"].astype(float) - 1
        return px

    def on_ticks(self, tickers):
        now = datetime.now(ET).isoformat(timespec="milliseconds")
        for tk in tickers:
            self._row(tk, now, "event")

    def _row(self, tk, now, kind):
        r = {"ts": now, "kind": kind, "symbol": tk.contract.symbol}
        for f in PRICE_FIELDS + AUCTION_FIELDS:
            r[f] = _num(getattr(tk, f, None))
        self.rows.append(r)

    async def record(self, cmap, names, end: datetime):
        self.ib.pendingTickersEvent += self.on_ticks     # attach first so no early ticks are missed
        tks = [self.ib.reqMktData(cmap[t], "225", False, False) for t in names]
        try:
            while datetime.now(ET) < end:
                now = datetime.now(ET).isoformat(timespec="milliseconds")
                for tk in tks:
                    self._row(tk, now, "heartbeat")
                await asyncio.sleep(1.0)
        finally:
            self.ib.pendingTickersEvent -= self.on_ticks
            for tk in tks:
                self.ib.cancelMktData(tk.contract)

    async def scanners(self) -> pd.DataFrame:
        from ib_async import ScannerSubscription
        rows = []
        for code in SCAN_CODES:
            try:
                sub = ScannerSubscription(instrument="STK", locationCode="STK.US.MAJOR", scanCode=code,
                                          numberOfRows=50)
                res = await asyncio.wait_for(self.ib.reqScannerDataAsync(sub), 20)
                for d in res:
                    rows.append({"scan": code, "rank": d.rank, "symbol": d.contractDetails.contract.symbol,
                                 "ts": datetime.now(ET).isoformat()})
            except Exception as e:  # noqa: BLE001 - scan code unsupported / no permission
                self.meta["errors"].append(f"scanner {code}: {e}")
        return pd.DataFrame(rows)

    async def bars(self, cmap, names) -> pd.DataFrame:
        rows = []
        for t in names[: self.args.bars_max]:      # IB pacing: ~60 historical requests / 10 min
            try:
                bs = await self.ib.reqHistoricalDataAsync(cmap[t], endDateTime="", durationStr="1 D",
                                                          barSizeSetting="1 min", whatToShow="TRADES",
                                                          useRTH=True)
                rows += [{"symbol": t, "time": b.date, "open": b.open, "high": b.high, "low": b.low,
                          "close": b.close, "volume": b.volume} for b in bs]
            except Exception as e:  # noqa: BLE001
                self.meta["errors"].append(f"bars {t}: {e}")
            await asyncio.sleep(10.5)
        return pd.DataFrame(rows)


async def run_day(args) -> None:
    from ib_async import IB, Stock
    ib = IB()
    await ib.connectAsync(args.host, args.port, clientId=args.client_id, readonly=True, timeout=20)
    s = Session(ib, args)
    try:
        ib.reqMarketDataType(args.market_data_type)
        spy = (await ib.reqContractDetailsAsync(Stock("SPY", "SMART", "USD")))[0]
        today = datetime.now(ET)
        sess = parse_liquid_hours(spy.liquidHours, today)
        if sess is None:
            print(today.date(), "market closed; nothing to record")
            return
        _, close = sess
        day = today.strftime("%Y-%m-%d")
        folder = OUT / day
        folder.mkdir(parents=True, exist_ok=True)
        s.meta.update({"date": day, "close": close.isoformat(), "max_lines": args.max_lines,
                       "market_data_type": args.market_data_type, "top_n": args.top_n})

        state = fund_state()
        unders = sorted(state["underlying"].unique())
        adv = adv20(unders)
        cmap, missing = await s.contracts(unders)
        s.meta["unqualified"] = missing

        await sleep_until(close - timedelta(minutes=16))
        px = await s.ranking_pass(cmap)
        pred = predicted_flows(state, px["r"].dropna(), adv if len(adv) else None)
        pred = pred.join(px[["last", "prior_close"]])
        top = [t for t in pred.index if t in cmap][: args.top_n]
        pred["selected"] = pred.index.isin(top)
        pred["ranked_at"] = datetime.now(ET).isoformat()
        pred.to_parquet(folder / "ranking.parquet")
        s.meta["selected"] = top
        print(f"ranked {len(pred)} names; recording {len(top)}: {top[:10]}...")

        await sleep_until(close - timedelta(minutes=10, seconds=30))
        await s.record(cmap, top, close + timedelta(minutes=1))
        ticks = pd.DataFrame(s.rows)
        ticks.to_parquet(folder / "ticks.parquet", index=False)
        got = ticks[AUCTION_FIELDS].notna().any(axis=1).sum() if len(ticks) else 0
        s.meta["tick_rows"], s.meta["rows_with_auction_fields"] = len(ticks), int(got)
        if got == 0:
            s.meta["errors"].append("no auction fields received - check live US equity market data "
                                    "permissions for generic tick 225")
        if args.scanner:
            sc = await s.scanners()
            if len(sc):
                sc.to_parquet(folder / "scanner.parquet", index=False)
        if args.bars:
            await sleep_until(close + timedelta(minutes=15))
            b = await s.bars(cmap, top)
            if len(b):
                b.to_parquet(folder / "bars.parquet", index=False)
    finally:
        (OUT / s.meta.get("date", "unknown")).mkdir(parents=True, exist_ok=True)
        (OUT / s.meta.get("date", "unknown") / "meta.json").write_text(json.dumps(s.meta, indent=2, default=str))
        ib.disconnect()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=4001, help="4001 IB Gateway live, 7496 TWS live, 4002/7497 paper")
    ap.add_argument("--client-id", type=int, default=17)
    ap.add_argument("--max-lines", type=int, default=90, help="stay under your market-data line limit")
    ap.add_argument("--top-n", type=int, default=90, help="names to record through the close")
    ap.add_argument("--rank-wait", type=float, default=4.0, help="seconds per ranking batch")
    ap.add_argument("--market-data-type", type=int, default=1, help="1 live (needed for auction ticks)")
    ap.add_argument("--scanner", action="store_true", help="also snapshot IB imbalance scanners after the close")
    ap.add_argument("--bars", action="store_true", help="also fetch 1-minute bars for recorded names")
    ap.add_argument("--bars-max", type=int, default=50)
    ap.add_argument("--loop", action="store_true", help="run every trading day until stopped")
    args = ap.parse_args()
    while True:
        start = datetime.now(ET)
        if start.weekday() < 5 and start.hour < 16:
            try:
                asyncio.run(run_day(args))
            except Exception as e:  # noqa: BLE001 - keep the loop alive; error is in meta/log
                print(datetime.now(ET), "session failed:", repr(e))
        if not args.loop:
            break
        nxt = (datetime.now(ET) + timedelta(days=1)).replace(hour=15, minute=30, second=0, microsecond=0)
        while nxt.weekday() >= 5:
            nxt += timedelta(days=1)
        print("next session", nxt)
        time.sleep(max(60, (nxt - datetime.now(ET)).total_seconds()))


if __name__ == "__main__":
    main()
