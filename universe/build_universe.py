"""Build the leveraged/inverse ETF universe from SEC series/class snapshots.

Union of the yearly SEC investment-company series/class files (2022-2026) so
funds that later closed are included. Leverage, direction, reset frequency and
underlying are parsed from fund names; ``verify_leverage.py`` later checks them
against realized returns.

Output: universe/letf_universe_raw.csv (one row per SEC series).
"""

from __future__ import annotations

import glob
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SEC = ROOT / "data" / "raw" / "sec"

LEV_HINT = re.compile(
    r"(?:\b\d+(?:\.\d+)?\s?x\b|\bbull\b|\bbear\b|\binverse\b|\bultra|\bshort\b|\blong\b|leverag|daily target)",
    re.I,
)
# Names that match LEV_HINT but are not leveraged/inverse products.
EXCLUDE = re.compile(
    r"(?:option income|income strategy|ultra[- ]short\b|t-bill|fixed income|weeklypay|premium income|covered call|buffer|bullbear|"
    r"\bbond\b|treasur|short[- ]term|short duration|ultra[- ]?short (?:bond|income|duration|term)|"
    r"ultrashort (?:bond|income|duration|term)|long/short|long-short|long short|municipal|"
    r"floating|\bmuni\b|money market|government|credit|mortgage|\bcds\b|dividend|"
    r"target date|target maturity|\bcapped accelerated\b|autocallable|defined outcome)",
    re.I,
)
# Tokens that look like tickers but are not the underlying.
STOP = {
    "ETF", "ETFS", "ETN", "AXS", "REX", "USD", "US", "X", "DAILY", "LONG", "SHORT", "BULL", "BEAR",
    "TARGET", "INVERSE", "SHARES", "TRUST", "FUND", "THE", "OF", "AND", "II", "III", "IV", "AI",
    "S&P", "MSCI", "FTSE", "NYSE", "SPDR", "ULTRA", "PRO", "T", "TREX", "T-REX", "K-1", "FREE",
    "LEVERAGE", "LEVERAGED", "CAPPED", "WEEKLY", "MONTHLY", "QUARTERLY", "NASDAQ", "DOW", "ADR",
    "2X", "3X", "1X", "1.5X", "1.25X", "1.75X", "TUTTLE", "CAPITAL", "DEFIANCE", "TRADR", "KURV",
    "CORGI", "GRANITESHARES", "DIREXION", "PROSHARES", "INC", "CORP", "CO", "PLUS", "A", "I",
}
# Funds named after the company rather than the ticker.
NAME_TO_TICKER = {
    "tesla": "TSLA", "nvidia": "NVDA", "microstrategy": "MSTR", "strategy": "MSTR", "coinbase": "COIN",
    "palantir": "PLTR", "apple": "AAPL", "amazon": "AMZN", "alphabet": "GOOGL", "google": "GOOGL",
    "microsoft": "MSFT", "meta": "META", "netflix": "NFLX", "advanced micro": "AMD", "amd": "AMD",
    "broadcom": "AVGO", "super micro": "SMCI", "supermicro": "SMCI", "robinhood": "HOOD",
    "gamestop": "GME", "amc": "AMC", "rivian": "RIVN", "lucid": "LCID", "nike": "NKE", "pfizer": "PFE",
    "paypal": "PYPL", "intel": "INTC", "micron": "MU", "eli lilly": "LLY", "berkshire": "BRK-B",
    "boeing": "BA", "disney": "DIS", "uber": "UBER", "shopify": "SHOP", "snowflake": "SNOW",
    "marathon digital": "MARA", "mara": "MARA", "riot": "RIOT", "arm holdings": "ARM",
    "taiwan semiconductor": "TSM", "tsmc": "TSM", "oracle": "ORCL", "salesforce": "CRM",
    "ionq": "IONQ", "rigetti": "RGTI", "oklo": "OKLO", "hims": "HIMS", "sofi": "SOFI",
    "crowdstrike": "CRWD", "snap": "SNAP", "zoom": "ZM", "moderna": "MRNA", "exxon": "XOM",
    "jpmorgan": "JPM", "alibaba": "BABA", "baidu": "BIDU", "nio": "NIO", "draftkings": "DKNG",
    "penn": "PENN", "nikola": "NKLA", "cloudflare": "NET", "roku": "ROKU", "block": "XYZ",
    "circle": "CRCL", "applovin": "APP", "reddit": "RDDT", "unitedhealth": "UNH",
    "asml": "ASML", "qualcomm": "QCOM", "adobe": "ADBE", "mercadolibre": "MELI",
}
# Ticker tokens missing from the current SEC operating-company list (delisted,
# foreign filers, share-class spellings) that are known single-stock underlyings.
TOKEN_ALIASES = {"BRKB": "BRK-B", "TWTR": "TWTR", "SMLR": "SMLR", "BITF": "BITF", "BULL": "BULL", "SATS": "SATS"}
# Non-stock underlyings: crypto, commodities, indexes, sectors, countries. Anything
# matching these is classed as "index/other", never "single_stock".
NON_STOCK = re.compile(
    r"(?:s&p|nasdaq|qqq|dow|russell|midcap|mid-cap|smallcap|small-cap|small cap|msci|ftse|"
    r"semiconductor|technology|financial|energy|biotech|health|real estate|regional bank|"
    r"homebuilder|retail|industrial|utilities|materials|consumer|transport|aerospace|"
    r"gold|silver|miners|oil|natural gas|crude|copper|platinum|palladium|wheat|corn|soybean|sugar|"
    r"bitcoin|ether|solana|xrp|dogecoin|cardano|chainlink|stellar|sui\b|bnb|xdc|litecoin|crypto|"
    r"volatility|vix|yen|euro|dollar|china|japan|brazil|mexico|india|korea|europe|emerging|"
    r"magnificent|fang|innovation|cloud|software|internet|cyber|drone|ai computing|robotics|"
    r"quantum|nuclear|uranium|clean energy|solar|cannabis|treasury|20\+|7-10|high yield|"
    r"large cap|total market|equal weight|pharma|airline|travel|gaming|metaverse|space|"
    r"\bbank|\bmedia|\bsector|\bindex|mega)",
    re.I,
)


def load_series_class() -> pd.DataFrame:
    frames = []
    for f in sorted(glob.glob(str(SEC / "investment-company-series-class-20*.csv"))):
        year = int(re.search(r"(20\d\d)", Path(f).name).group(1))
        d = pd.read_csv(f, dtype=str, encoding="utf-8-sig")
        d["year"] = year
        frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    d = d.replace({"[NULL]": pd.NA, "": pd.NA})
    return d


def stock_tickers() -> set[str]:
    j = json.load(open(SEC / "company_tickers_exchange_2026-09-23.json"))
    return {row[2] for row in j["data"] if row[2]}


def parse_leverage(name: str) -> tuple[float | None, str]:
    """Signed target leverage from a fund name, plus a parse note."""
    n = name.lower()
    inverse = bool(re.search(r"\b(bear|inverse|short)\b|ultrashort|ultrapro short", n))
    m = re.search(r"(-?\d+(?:\.\d+)?)\s?x\b", n)
    if m:
        mag = abs(float(m.group(1)))
        note = "number"
    elif "ultrapro" in n:
        mag, note = 3.0, "proshares ultrapro"
    elif "ultrashort" in n or re.search(r"\bultra\b", n):
        mag, note = 2.0, "proshares ultra"
    elif inverse:
        mag, note = 1.0, "inverse no number"
    else:
        return None, "no leverage found"
    return (-mag if inverse else mag), note


def reset_frequency(name: str) -> str:
    n = name.lower()
    for k in ("weekly", "monthly", "quarterly"):
        if k in n:
            return k
    return "daily"


def parse_underlying(name: str, tickers: set[str]) -> tuple[str | None, str]:
    # 1) explicit ticker-like tokens (upper case in the original name)
    toks = re.findall(r"\b[A-Z][A-Z0-9.\-]{0,5}\b", name)
    cands = [TOKEN_ALIASES.get(t, t) for t in toks if t not in STOP and (t in tickers or t in TOKEN_ALIASES)]
    if len(cands) == 1:
        return cands[0], "ticker token"
    if len(cands) > 1:
        return cands[0], "ambiguous:" + ",".join(cands)
    # 2) company names
    n = name.lower()
    for key in sorted(NAME_TO_TICKER, key=len, reverse=True):
        if re.search(r"\b" + re.escape(key) + r"\b", n):
            return NAME_TO_TICKER[key], "company name"
    # 3) all-caps names like "T-REX 2X LONG OKLO DAILY TARGET ETF"
    if name.isupper():
        cands = [t for t in re.findall(r"\b[A-Z]{1,5}\b", name) if t not in STOP and t in tickers]
        if cands:
            return cands[0], "ticker token (caps name)"
    return None, "unresolved"


def build() -> pd.DataFrame:
    d = load_series_class()
    tickers = stock_tickers()
    series = (
        d.sort_values("year")
        .groupby("Series ID")
        .agg(
            series_name=("Series Name", "last"),
            all_names=("Series Name", lambda s: " | ".join(dict.fromkeys(s.dropna()))),
            trust=("Entity Name", "last"),
            cik=("CIK Number", "last"),
            ticker=("Class Ticker", lambda s: s.dropna().iloc[-1] if s.notna().any() else pd.NA),
            all_tickers=("Class Ticker", lambda s: " | ".join(dict.fromkeys(s.dropna()))),
            first_year=("year", "min"),
            last_year=("year", "max"),
        )
        .reset_index()
        .rename(columns={"Series ID": "series_id"})
    )
    names = series["all_names"]
    keep = names.str.contains(LEV_HINT) & ~names.str.contains(EXCLUDE)
    s = series[keep].copy()

    parsed = s["series_name"].apply(parse_leverage)
    s["leverage_parsed"] = [p[0] for p in parsed]
    s["leverage_note"] = [p[1] for p in parsed]
    s = s[s["leverage_parsed"].notna() & (s["leverage_parsed"] != 1.0)]
    s["reset"] = s["series_name"].apply(reset_frequency)

    und = s["series_name"].apply(lambda n: parse_underlying(n, tickers))
    s["underlying"] = [u[0] for u in und]
    s["underlying_note"] = [u[1] for u in und]
    non_stock = s["series_name"].str.contains(NON_STOCK)
    s["category"] = "index_other"
    s.loc[~non_stock & s["underlying"].notna(), "category"] = "single_stock"
    s.loc[~non_stock & s["underlying"].isna(), "category"] = "unresolved"
    s["active_2026"] = s["last_year"] == s["last_year"].max()
    s["has_ticker"] = s["ticker"].notna()
    return s.sort_values(["category", "underlying", "leverage_parsed"]).reset_index(drop=True)


if __name__ == "__main__":
    u = build()
    out = ROOT / "universe" / "letf_universe_raw.csv"
    u.to_csv(out, index=False)
    print(u.groupby(["category", "has_ticker"]).size())
    print(f"wrote {out}")
