import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from recorders import holdings as H
from recorders.imbalance_recorder import ET, Session, ib_symbol, parse_liquid_hours
from recorders.live_flow import predicted_flows

FIX = Path(__file__).parent / "fixtures"


# ----------------------------------------------------------------------------- holdings parsers
class FakeResp:
    def __init__(self, content: bytes):
        self.content, self.text = content, content.decode("utf-8", "replace")

    def json(self):
        import json
        return json.loads(self.text)


def _patch_get(monkeypatch, mapping):
    def fake_get(url, method="GET", **kw):
        for key, body in mapping.items():
            if key in url:
                return FakeResp(body)
        raise AssertionError(f"unexpected url {url}")
    monkeypatch.setattr(H, "get", fake_get)


def test_direxion_long_fixture(monkeypatch):
    _patch_get(monkeypatch, {"TSLL.csv": (FIX / "TSLL_direxion.csv").read_bytes()})
    s = H.Snapshot("TSLL", "Direxion", "TSLA", 2.0)
    H.direxion(s)
    usd, x = s.exposure()
    assert s.shares_out > 1e6 and s.asof
    assert x == pytest.approx(2.0, abs=0.05)            # swap legs + stock = 2x net assets
    assert {h["kind"] for h in s.holdings} >= {"swap", "equity", "cash"}


def test_direxion_bear_fixture(monkeypatch):
    _patch_get(monkeypatch, {"NVDD.csv": (FIX / "NVDD_direxion.csv").read_bytes()})
    s = H.Snapshot("NVDD", "Direxion", "NVDA", -1.0)
    H.direxion(s)
    usd, x = s.exposure()
    assert usd < 0 and x == pytest.approx(-1.0, abs=0.05)


def test_kraneshares_fixture(monkeypatch):
    page = b'<a href="https://kraneshares.com/csv/09_22_2026_kmli_holdings.csv">x</a> Shares Outstanding 675,002'
    _patch_get(monkeypatch, {"kraneshares.com/kmli": page,
                             "kmli_holdings.csv": (FIX / "KMLI_kraneshares.csv").read_bytes()})
    s = H.Snapshot("KMLI", "KraneShares", "MELI", 2.0)
    H.kraneshares(s)
    usd, x = s.exposure()
    assert s.asof == "2026-09-22" and x == pytest.approx(2.0, abs=0.05)


def test_rex_block_parser(monkeypatch):
    html = (b"<div>Shares Outstanding</div><div>1,000,000</div><div>Net Asset Value</div><div>$10.00</div>"
            b"<h2>Fund Holdings:</h2> As of 09/22/2026 Symbol Name Security Identifier Weighting Net Value Shares Held "
            b"CASH AND CASH EQUIVALENTS 100.00% $10,000,000.00 10000000 "
            b"RECV MSTU TRS MSTR US EQ 120.00% $12,000,000.00 70000 "
            b"RECV STRG TRS MSTR EQ 80.00% $8,000,000.00 46000 Fund Performance:")
    _patch_get(monkeypatch, {"rexshares.com/mstu": html})
    s = H.Snapshot("MSTU", "T-REX", "MSTR", 2.0)
    H.rex(s)
    usd, x = s.exposure()
    assert s.asof == "2026-09-22" and len(s.holdings) == 3
    assert usd == pytest.approx(20e6) and x == pytest.approx(2.0)


def test_num_and_classify():
    assert H.num("$1.5B") == 1.5e9 and H.num("(2,000)") == -2000 and H.num("-67.2%") == -67.2
    assert H.classify("TSLA SWAP ASSET LEG", None, "TSLA") == "swap"
    assert H.classify("TESLA INC", "TSLA", "TSLA") == "equity"
    assert H.classify("DREYFUS GOVT CASH MAN INS", None, "TSLA") == "cash"


def test_stockanalysis_gives_no_exposure():
    s = H.Snapshot("APPX", "Tradr", "APP", 2.0, source="stockanalysis", net_assets=60e6)
    s.add("Cfd Applovin", None, 200.0, None, 1)
    assert s.exposure() == (None, None)


# ----------------------------------------------------------------------------- live flow
def test_predicted_flows_uses_holdings_exposure():
    state = pd.DataFrame({"ticker": ["A2", "A-2"], "underlying": ["X", "X"], "L": [2.0, -2.0],
                          "A_prev": [100.0, 50.0], "E_prev": [190.0, -100.0]})
    out = predicted_flows(state, pd.Series({"X": 0.10}), pd.Series({"X": 1000.0}))
    # long: A=119 -> 238 - 209 = 29 ; inverse: A=40 -> -80 - (-110) = 30
    assert out.loc["X", "flow"] == pytest.approx(59.0)
    assert out.loc["X", "flow_ratio"] == pytest.approx(59.0 / 100.0)


# ----------------------------------------------------------------------------- recorder
def test_parse_liquid_hours():
    lh = "20261127:0930-20261127:1300;20261128:CLOSED;20261130:0930-20261130:1600"
    o, c = parse_liquid_hours(lh, datetime(2026, 11, 27, tzinfo=ET))
    assert (c.hour, c.minute) == (13, 0) and c.tzinfo is not None
    assert parse_liquid_hours(lh, datetime(2026, 11, 28, tzinfo=ET)) is None
    assert parse_liquid_hours(lh, datetime(2026, 11, 30, tzinfo=ET))[1].hour == 16


def test_ib_symbol():
    assert ib_symbol("BRK-B") == "BRK B" and ib_symbol("NVDA") == "NVDA"


class FakeEvent:
    def __init__(self):
        self.handlers = []

    def __iadd__(self, h):
        self.handlers.append(h)
        return self

    def __isub__(self, h):
        self.handlers.remove(h)
        return self


class FakeIB:
    """Minimal stand-in for ib_async.IB: tickers update when requested."""

    def __init__(self, prices):
        self.prices, self.active, self.max_active = prices, set(), 0
        self.pendingTickersEvent = FakeEvent()

    def reqMktData(self, contract, generic, snapshot, regulatory):
        last, close = self.prices[contract.symbol]
        self.active.add(contract.symbol)
        self.max_active = max(self.max_active, len(self.active))
        tk = SimpleNamespace(contract=contract, last=last, close=close, lastSize=1, bid=last, bidSize=1,
                             ask=last, askSize=1, volume=10, auctionVolume=None, auctionPrice=None,
                             auctionImbalance=None, regulatoryImbalance=None, marketPrice=lambda: last)
        if generic == "225":
            tk.auctionImbalance, tk.auctionPrice, tk.auctionVolume = 5000.0, last, 20000.0
            for h in self.pendingTickersEvent.handlers:
                h([tk])
        return tk

    def cancelMktData(self, contract):
        self.active.discard(contract.symbol)


def test_ranking_pass_respects_line_limit_and_computes_returns():
    prices = {f"S{i}": (110.0, 100.0) for i in range(25)}
    ib = FakeIB(prices)
    sess = Session(ib, SimpleNamespace(max_lines=10, rank_wait=0.0))
    cmap = {t: SimpleNamespace(symbol=t) for t in prices}
    px = asyncio.run(sess.ranking_pass(cmap))
    assert ib.max_active <= 10 and not ib.active
    assert px["r"].astype(float).round(6).eq(0.1).all() and len(px) == 25


def test_record_logs_auction_fields_and_cancels():
    ib = FakeIB({"X": (50.0, 49.0), "Y": (20.0, 21.0)})
    sess = Session(ib, SimpleNamespace())
    cmap = {t: SimpleNamespace(symbol=t) for t in ("X", "Y")}
    asyncio.run(sess.record(cmap, ["X", "Y"], datetime.now(ET) + timedelta(seconds=1.5)))
    df = pd.DataFrame(sess.rows)
    assert not ib.active and not ib.pendingTickersEvent.handlers
    assert set(df["kind"]) == {"event", "heartbeat"}
    assert df["auctionImbalance"].notna().all() and set(df["symbol"]) == {"X", "Y"}
