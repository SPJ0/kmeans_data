"""Parse leveraged/inverse ETF series names into leverage, reset and underlying.

Fund names encode their terms ("Direxion Daily TSLA Bull 2X Shares",
"GraniteShares 2x Short NVDA Daily ETF", "Kurv Apple (AAPL) 1.75x Long Daily ETF",
"ProShares UltraPro Short QQQ"). The parse is heuristic; every row is later
cross-checked against the fund's own N-PORT filing (designated reference
instrument) and flagged for hand verification when the two disagree.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

ISSUERS = [  # (regex on name, brand)
    (r"^Direxion", "Direxion"), (r"^GraniteShares", "GraniteShares"), (r"^T-?REX", "T-REX"),
    (r"^Defiance", "Defiance"), (r"^Tradr", "Tradr"), (r"^Leverage Shares", "Leverage Shares"),
    (r"^KraneShares", "KraneShares"), (r"^ProShares", "ProShares"), (r"^AXS", "AXS"),
    (r"^Tuttle", "Tuttle"), (r"^Roundhill", "Roundhill"), (r"^Kurv", "Kurv"), (r"^Corgi", "Corgi"),
    (r"^ProFund|PROFUND", "ProFunds"), (r"^Rydex|^Guggenheim", "Rydex"), (r"^21Shares", "21Shares"),
    (r"^Teucrium", "Teucrium"), (r"^Volatility Shares|^\d(\.\d+)?x (Bitcoin|Ether|Solana|XRP)", "Volatility Shares"),
    (r"^REX|^Rex", "REX"), (r"^MicroSectors", "MicroSectors"), (r"^Bitwise", "Bitwise"),
    (r"^Valkyrie|^CoinShares", "CoinShares/Valkyrie"), (r"^ETFMG", "ETFMG"), (r"^Elevate", "Elevate Shares"),
    (r"^AdvisorShares", "AdvisorShares"), (r"^USCF", "USCF"), (r"^VistaShares", "VistaShares"),
    (r"^Cyber Hornet", "Cyber Hornet"), (r"^Themes", "Themes"), (r"^Global X", "Global X"),
    (r"^Invesco", "Invesco"), (r"^iShares", "iShares"), (r"^Grayscale", "Grayscale"),
]

EXCLUDE_PRODUCT = re.compile(
    r"income|yield|premium|buffer|capped|accelerated|option|covered|weeklypay|hedge|"
    r"treasur|bond|duration|maturity|muni|tax[- ]free|loan|long[/-]short|bullbear|"
    r"volatility|vix|risk parity|multi-strategy|strategy bull|strategy bear|\bfund\b|portfolio",
    re.I)
NON_DAILY = re.compile(r"\b(weekly|monthly|quarterly)\b", re.I)

# words that are part of the name template, never the underlying
STOP = {
    "DIREXION", "DAILY", "BULL", "BEAR", "SHARES", "ETF", "LONG", "SHORT", "INVERSE", "TARGET",
    "GRANITESHARES", "TRADR", "DEFIANCE", "LEVERAGE", "KRANESHARES", "PROSHARES", "ULTRA",
    "ULTRAPRO", "ULTRASHORT", "AXS", "TUTTLE", "CAPITAL", "ROUNDHILL", "KURV", "CORGI", "T-REX",
    "TREX", "REX", "X", "THE", "FUND", "TRUST", "AND", "&", "OF", "LEVERAGED", "PLUS", "PURE",
    "TR", "SHS", "CL", "A", "INC", "CORP", "NEW",
}


@dataclass
class Parsed:
    issuer: str | None
    leverage: float | None       # signed target leverage
    reset: str                   # daily / weekly / monthly / quarterly / unknown
    underlying_token: str | None  # raw ticker-like token or company-name phrase
    excluded_reason: str | None


def issuer_of(name: str) -> str | None:
    for pat, brand in ISSUERS:
        if re.search(pat, name, re.I):
            return brand
    return None


def _leverage(name: str) -> float | None:
    n = name.replace("–", "-")
    # ProShares naming
    if re.search(r"\bUltraPro Short\b", n, re.I):
        return -3.0
    if re.search(r"\bUltraShort\b", n, re.I):
        return -2.0
    if re.search(r"\bUltraPro\b", n, re.I):
        return 3.0
    mag = None
    m = re.search(r"(-?)\s*(\d+(?:\.\d+)?)\s*[xX]\b", n)
    if m:
        mag = float(m.group(2))
        if m.group(1) == "-":
            return -mag
    elif re.search(r"\bUltra\b", n, re.I):
        mag = 2.0
    neg = re.search(r"\b(bear|short|inverse)\b", n, re.I)
    pos = re.search(r"\b(bull|long)\b", n, re.I)
    if mag is None:
        if neg and re.search(r"\bdaily\b|ProShares Short|Tuttle", n, re.I):
            mag = 1.0
        else:
            return None
    if neg and not pos:
        return -mag
    return mag


def _underlying_token(name: str, issuer: str | None) -> str | None:
    n = re.sub(r"\s*(\(R\)|®|\(TM\)|™)", "", name)
    # explicit ticker in parentheses: "Kurv Apple (AAPL) 1.75x Long Daily ETF"
    m = re.search(r"\(([A-Z][A-Z0-9.\-]{0,6})\)", n)
    if m:
        return m.group(1)
    # strip issuer brand and template words; what remains is the underlying phrase
    n = re.sub(r"-?\d+(\.\d+)?\s*[xX]\b", " ", n)
    words = re.split(r"\s+", n.strip())
    keep = [w for w in words if w.upper().strip(",.") not in STOP and not re.fullmatch(r"-?1X", w, re.I)]
    # drop issuer-brand words at the start
    if issuer:
        brand_words = {w.upper() for w in issuer.replace("-", " ").split()} | {issuer.upper()}
        keep = [w for w in keep if w.upper() not in brand_words]
    phrase = " ".join(keep).strip(" ,.-")
    return phrase or None


def parse_name(name: str) -> Parsed:
    issuer = issuer_of(name)
    lev = _leverage(name)
    reset = "daily"
    m = NON_DAILY.search(name)
    if m:
        reset = m.group(1).lower()
    elif not re.search(r"\bdaily\b", name, re.I) and issuer not in ("ProShares", "ProFunds", "Rydex"):
        reset = "unknown"
    excl = None
    if EXCLUDE_PRODUCT.search(name):
        excl = "product_type"
    elif reset in ("weekly", "monthly", "quarterly"):
        excl = f"reset_{reset}"
    elif lev is None:
        excl = "no_leverage_parsed"
    elif abs(lev) == 1.0 and lev > 0:
        excl = "unlevered"
    return Parsed(issuer, lev, reset, _underlying_token(name, issuer), excl)
