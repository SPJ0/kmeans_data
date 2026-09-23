"""Daily archive of leveraged-ETF holdings -> exact prior-close exposure E_{i,t-1}.

Run once per weekday morning (holdings posted before the open reflect the
positions after the previous close's rebalance):

    python -m recorders.holdings                # all active universe funds
    python -m recorders.holdings --tickers TSLL MSTU

Sources, per issuer (native files carry swap notionals):
  Direxion       www.direxion.com/holdings/<T>.csv      shares out + every swap leg in $
  Defiance       <t>-full-holdings page table + fund page (net assets, shares out)
  T-REX (REX)    fund page holdings block (weight, $ value, shares) + shares out / NAV
                 (exposure recorded but flagged untrusted: the page lists stale/duplicate swap rows)
  GraniteShares  product snapshot JSON (AUM, NAV date) + holdings JSON endpoint used by their page
  KraneShares    dated holdings CSV linked from the fund page
  everything else (Tradr, Leverage Shares, ProShares, ...), and any native failure:
                 stockanalysis.com fund page (AUM, shares out, top holdings). Exposure is
                 left blank here because that page's weights are not reliable enough for $.
Tradr's own data widget is behind reCAPTCHA, so it is deliberately not scraped.

Output (one folder per run date, US/Eastern):
  data/holdings/<YYYY-MM-DD>/funds.parquet      one row per fund
  data/holdings/<YYYY-MM-DD>/holdings.parquet   one row per holding
  data/holdings/<YYYY-MM-DD>/raw/*.csv|json     native CSV/JSON as downloaded (small)
"""
from __future__ import annotations

import argparse
import io
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from common.paths import DATA, UNIVERSE

OUT = DATA / "holdings"
ET = ZoneInfo("America/New_York")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
PAUSE = {"www.direxion.com": 0.5, "www.defianceetfs.com": 1.0, "www.rexshares.com": 1.0, "graniteshares.com": 0.7,
         "knockoutv2.azurewebsites.net": 0.7, "kraneshares.com": 1.0, "www.kraneshares.com": 1.0,
         "stockanalysis.com": 1.2}

_session = requests.Session()
_session.headers.update({"User-Agent": UA})
_last: dict[str, float] = {}


def get(url: str, method: str = "GET", **kw) -> requests.Response:
    host = url.split("/")[2]
    wait = _last.get(host, 0) + PAUSE.get(host, 1.0) - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    delay = 2.0
    for attempt in range(4):
        _last[host] = time.monotonic()
        try:
            r = _session.request(method, url, timeout=45, **kw)
            if r.status_code == 200:
                return r
            if r.status_code in (403, 404):
                r.raise_for_status()
        except requests.HTTPError:
            raise
        except requests.RequestException:
            pass
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"failed: {url}")


# ----------------------------------------------------------------------------- parsing helpers
def num(x) -> float | None:
    if x is None:
        return None
    s = str(x).strip().replace(",", "").replace("$", "").replace("%", "")
    mult = 1.0
    if s[-1:] in "KMB" and s[:-1].replace(".", "", 1).replace("-", "", 1).isdigit():
        mult = {"K": 1e3, "M": 1e6, "B": 1e9}[s[-1]]
        s = s[:-1]
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        return float(s) * mult
    except ValueError:
        return None


def classify(name: str, ident: str | None, underlying: str) -> str:
    n = f"{name or ''} {ident or ''}".upper()
    if re.search(r"SWAP|\bTRS\b|TOTAL RETURN|\bCFD\b", n):
        return "swap"
    if ident and str(ident).upper().replace(".", "-") == underlying.upper():
        return "equity"
    if re.search(r"TREASUR|T-BILL|BILL\b|MONEY MARKET|GOVT|GOVERNMENT|CASH|DREYFUS|FIRST AMERICAN|\bUSD\b|"
                 r"DOLLAR|GOLDMAN FINL|JP MORGAN 100|OTHER ASSETS", n):
        return "cash"
    return "other"


@dataclass
class Snapshot:
    ticker: str
    issuer: str
    underlying: str
    L: float
    source: str = ""
    asof: str | None = None
    net_assets: float | None = None
    shares_out: float | None = None
    nav: float | None = None
    holdings: list[dict] = field(default_factory=list)
    raw: tuple[str, bytes] | None = None   # (filename, content) of a small native file
    error: str | None = None

    def add(self, name, ident=None, weight_pct=None, market_value=None, shares=None):
        kind = classify(name, ident, self.underlying)
        # a swap's financing (cash) leg is quoted in dollars: value per "share" ~ $1. Only the
        # equity leg (shares x stock price) is exposure to the underlying.
        if kind == "swap" and market_value and shares and 0.8 < abs(market_value / shares) < 1.25:
            kind = "swap_financing"
        self.holdings.append({"name": name, "identifier": ident, "weight_pct": weight_pct,
                              "market_value": market_value, "shares": shares, "kind": kind})

    def implied_net_assets(self) -> float | None:
        """Net assets implied by holdings rows that carry both $ value and % weight (same as-of date as
        the holdings, unlike page-level stats which can lag or lead by a day)."""
        v = [h["market_value"] / (h["weight_pct"] / 100) for h in self.holdings
             if h["market_value"] and h["weight_pct"] and abs(h["weight_pct"]) >= 1]
        v = sorted(x for x in v if x > 0)
        return v[len(v) // 2] if v else None

    def exposure(self) -> tuple[float | None, float | None]:
        """($ exposure to the underlying, exposure / net assets) from swap + underlying-stock rows."""
        implied = self.implied_net_assets()
        if implied:
            self.net_assets = implied
        rows = [h for h in self.holdings if h["kind"] in ("swap", "equity")]
        if not rows or self.source == "stockanalysis":
            return None, None
        if all(h["market_value"] is not None for h in rows):
            usd = sum(h["market_value"] for h in rows)
        elif self.net_assets and all(h["weight_pct"] is not None for h in rows):
            usd = sum(h["weight_pct"] for h in rows) / 100 * self.net_assets
        else:
            return None, None
        return usd, (usd / self.net_assets if self.net_assets else None)


# ----------------------------------------------------------------------------- issuer adapters
def direxion(s: Snapshot) -> None:
    r = get(f"https://www.direxion.com/holdings/{s.ticker}.csv")
    s.raw = (f"{s.ticker}_direxion.csv", r.content)
    txt = r.text
    m = re.search(r"Shares Outstanding:\s*([\d,]+)", txt)
    s.shares_out = num(m.group(1)) if m else None
    body = txt[txt.find('"TradeDate"'):]
    df = pd.read_csv(io.StringIO(body))
    for _, h in df.iterrows():
        s.add(h["SecurityDescription"], h["StockTicker"] if isinstance(h["StockTicker"], str) else None,
              num(h["HoldingsPercent"]), num(h["MarketValue"]), num(h["Shares"]))
    s.asof = pd.to_datetime(df["TradeDate"].iloc[0]).strftime("%Y-%m-%d") if len(df) else None
    # net assets implied by any positive cash row: value / weight
    for h in s.holdings:
        if h["kind"] == "cash" and (h["weight_pct"] or 0) > 1 and (h["market_value"] or 0) > 0:
            s.net_assets = h["market_value"] / (h["weight_pct"] / 100)
            break
    s.source = "direxion_csv"


def defiance(s: Snapshot) -> None:
    t = s.ticker.lower()
    page = get(f"https://www.defianceetfs.com/{t}/").text
    for label, attr in (("Net Assets", "net_assets"), ("Shares Outstanding", "shares_out"), ("NAV", "nav")):
        m = re.search(label + r"</span>(.{0,300})", page, re.S)
        if m:
            setattr(s, attr, num(re.sub(r"<[^>]+>", " ", m.group(1)).split()[0]))
    html = get(f"https://www.defianceetfs.com/{t}-full-holdings/").text
    tab = pd.read_html(io.StringIO(html[html.lower().find("<table"):]))[0]
    tab.columns = [str(c).strip() for c in tab.columns]
    for _, h in tab.iterrows():
        s.add(h.get("Name"), h.get("Ticker"), num(h.get("ETF Weight")), None, num(h.get("Shares")))
    m = re.search(r"Data as of (\d{2}/\d{2}/\d{4})", html)
    s.asof = pd.to_datetime(m.group(1)).strftime("%Y-%m-%d") if m else None
    s.source = "defiance_page"


def rex(s: Snapshot) -> None:
    page = get(f"https://www.rexshares.com/{s.ticker.lower()}/").text
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page))
    m = re.search(r"Shares Outstanding\s+([\d,]+)", text)
    s.shares_out = num(m.group(1)) if m else None
    m = re.search(r"Net Asset Value\s+\$?([\d.,]+)", text)
    s.nav = num(m.group(1)) if m else None
    if s.nav and s.shares_out:
        s.net_assets = s.nav * s.shares_out
    i = text.find("Fund Holdings:")
    j = text.find("Fund Performance", i)
    block = text[i:j if j > 0 else i + 6000]
    m = re.search(r"As of (\d{2}/\d{2}/\d{4})", block)
    s.asof = pd.to_datetime(m.group(1)).strftime("%Y-%m-%d") if m else None
    block = block.split("Shares Held", 1)[-1]
    for name, ident, w, v, sh in re.findall(
            r"([A-Z][A-Z0-9 .&/\-']+?)\s+(\S+\s+)?(-?[\d.]+)%\s+(-?\$?-?[\d,]+\.\d+)\s+(-?[\d,]+)", block):
        ident = ident.strip() or None
        if ident and not re.search(r"\d", ident):   # a word of the name, not an identifier
            name, ident = f"{name} {ident}", None
        s.add(name.strip(), ident, num(w), num(v), num(sh))
    s.source = "rex_page"


def graniteshares(s: Snapshot) -> None:
    page = get(f"https://graniteshares.com/institutional/us/en-us/etfs/{s.ticker.lower()}/").text
    pid = re.search(r"var PRODUCT_ID = (\d+)", page)
    hurl = re.search(r'var HOLDINGS_URL = "([^"]+)"\s*\+\s*"([^"]+)"', page)
    if not pid or not hurl:
        raise RuntimeError("graniteshares page layout changed")
    snap = get(f"https://graniteshares.com/product/{pid.group(1)}/en-us/").json()
    data = json.loads(snap["Data"]) if isinstance(snap.get("Data"), str) else snap
    s.net_assets, s.nav = num(data.get("AUM")), num(data.get("Nav"))
    s.shares_out = s.net_assets / s.nav if s.net_assets and s.nav else None
    s.asof = str(data.get("NavDate", ""))[:10] or None
    hold = get(hurl.group(1) + hurl.group(2), method="POST",
               json={"ticker": s.ticker, "dataDate": s.asof}).json()
    s.raw = (f"{s.ticker}_graniteshares.json", json.dumps({"snapshot": data, "holdings": hold}).encode())
    for h in hold if isinstance(hold, list) else []:
        s.add(h.get("security"), None, (num(h.get("weight")) or 0) * 100, num(h.get("value")), num(h.get("share")))
    s.source = "graniteshares_api"


def kraneshares(s: Snapshot) -> None:
    page = get(f"https://www.kraneshares.com/{s.ticker.lower()}/").text
    m = re.search(r"https://kraneshares\.com/csv/\d{2}_\d{2}_\d{4}_" + s.ticker.lower() + r"_holdings\.csv", page)
    if not m:
        raise RuntimeError("no holdings csv link")
    r = get(m.group(0))
    s.raw = (f"{s.ticker}_kraneshares.csv", r.content)
    lines = r.text.splitlines()
    d = re.search(r"As of (\d{4}-\d{2}-\d{2})", lines[0])
    s.asof = d.group(1) if d else None
    df = pd.read_csv(io.StringIO("\n".join(lines[1:])))
    for _, h in df.iterrows():
        s.add(f"{h['Company Name']} [{h['Type']}]", h.get("Ticker") if isinstance(h.get("Ticker"), str) else None,
              num(h["% of Net Assets"]), num(h["Market Value($)"]), num(h["Shares Held"]))
    txt = re.sub(r"<[^>]+>", " ", page)
    m = re.search(r"Shares Outstanding\s+([\d,]+)", re.sub(r"\s+", " ", txt))
    s.shares_out = num(m.group(1)) if m else None
    s.source = "kraneshares_csv"


def stockanalysis(s: Snapshot) -> None:
    page = get(f"https://stockanalysis.com/etf/{s.ticker.lower()}/").text
    g = lambda pat: (re.search(pat, page).group(1) if re.search(pat, page) else None)  # noqa: E731
    s.net_assets, s.shares_out = num(g(r'aum:"([^"]+)"')), num(g(r'sharesOut:"([^"]+)"'))
    upd = g(r'updated:"([^"]+)"')
    s.asof = pd.to_datetime(upd, errors="coerce").strftime("%Y-%m-%d") if upd and pd.notna(
        pd.to_datetime(upd, errors="coerce")) else None
    m = re.search(r"holdings:\[(\{n:.*?)\]", page)
    if m:
        for n, w, sh in re.findall(r'\{n:"([^"]*)",as:"([^"]*)",sh:"([^"]*)"\}', m.group(1)):
            s.add(n, None, num(w), None, num(sh))
    s.source = "stockanalysis"


# sources whose exposure checked out against target leverage on the first full run (all within
# ~6%, nearly all within 0.1%). The T-REX pages list stale/duplicate swap rows (2.8-5x on 2x
# funds), so their exposure is recorded but not trusted.
TRUSTED_EXPOSURE = {"direxion_csv", "defiance_page", "graniteshares_api", "kraneshares_csv"}

NATIVE = {"Direxion": direxion, "Defiance": defiance, "T-REX": rex, "GraniteShares": graniteshares,
          "KraneShares": kraneshares}


# ----------------------------------------------------------------------------- run
def funds_to_scrape(tickers: list[str] | None = None) -> pd.DataFrame:
    u = pd.read_csv(UNIVERSE / "single_stock_universe.csv")
    u = u[u["include"] & (u["status"] == "active") & u["ticker"].notna()]
    extra = UNIVERSE / "extra_funds.csv"          # ticker,issuer,underlying,leverage for new launches
    if extra.exists():
        u = pd.concat([u, pd.read_csv(extra)], ignore_index=True).drop_duplicates("ticker", keep="last")
    if tickers:
        u = u[u["ticker"].isin(tickers)]
    return u[["ticker", "issuer", "underlying", "leverage"]]


def scrape_one(f) -> Snapshot:
    s = Snapshot(f.ticker, f.issuer, f.underlying, float(f.leverage))
    fn = NATIVE.get(f.issuer)
    if fn is not None:
        try:
            fn(s)
            if s.holdings or s.net_assets:
                return s
            s.error = "native returned nothing"
        except Exception as e:  # fall back below
            s.error = f"native: {type(e).__name__}: {e}"[:300]
        s.holdings, s.raw = [], None
    try:
        stockanalysis(s)
    except Exception as e:
        s.error = ((s.error + " | ") if s.error else "") + f"fallback: {type(e).__name__}: {e}"[:300]
    return s


def run(tickers: list[str] | None = None, day: str | None = None) -> pd.DataFrame:
    day = day or datetime.now(ET).strftime("%Y-%m-%d")
    folder = OUT / day
    (folder / "raw").mkdir(parents=True, exist_ok=True)
    fetched = datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S")
    frows, hrows = [], []
    todo = funds_to_scrape(tickers)
    for i, f in enumerate(todo.itertuples(index=False)):
        s = scrape_one(f)
        usd, pct = s.exposure()
        frows.append({"run_date": day, "fetched_at_et": fetched, "ticker": s.ticker, "issuer": s.issuer,
                      "underlying": s.underlying, "L_target": s.L, "source": s.source, "asof": s.asof,
                      "net_assets": s.net_assets, "shares_out": s.shares_out, "nav": s.nav,
                      "exposure_usd": usd, "exposure_x": pct, "exposure_trusted": s.source in TRUSTED_EXPOSURE,
                      "n_holdings": len(s.holdings), "error": s.error})
        for h in s.holdings:
            hrows.append({"run_date": day, "ticker": s.ticker, "source": s.source, "asof": s.asof, **h})
        if s.raw:
            (folder / "raw" / s.raw[0]).write_bytes(s.raw[1])
        if i % 25 == 0:
            print(f"{i}/{len(todo)} {s.ticker} {s.source} A={s.net_assets} E/A={pct}", flush=True)
    funds = pd.DataFrame(frows)
    funds.to_parquet(folder / "funds.parquet", index=False)
    pd.DataFrame(hrows).to_parquet(folder / "holdings.parquet", index=False)
    ok = funds["net_assets"].notna().mean()
    print(f"{day}: {len(funds)} funds, net assets for {ok:.0%}, exposure for {funds['exposure_usd'].notna().mean():.0%}; "
          f"sources {funds['source'].value_counts().to_dict()}")
    return funds


def latest(asof_before: str | None = None) -> pd.DataFrame:
    """Most recent funds.parquet (optionally strictly before a date)."""
    days = sorted(p.name for p in OUT.glob("20*") if (p / "funds.parquet").exists())
    if asof_before:
        days = [d for d in days if d < asof_before]
    if not days:
        return pd.DataFrame()
    return pd.read_parquet(OUT / days[-1] / "funds.parquet")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="*")
    ap.add_argument("--date", help="override run-date folder (YYYY-MM-DD)")
    a = ap.parse_args()
    run(a.tickers, a.date)
