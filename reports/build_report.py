"""Build the Phase A1 PDF report: reports/Auction_Flow_Research_Report.pdf
Run from repo root:  python -m reports.make_figures && python -m reports.build_report
"""

from __future__ import annotations

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from universe.build_universe import ROOT

REP = ROOT / "reports"
FIG = REP / "figures"
OUT = REP / "Auction_Flow_Research_Report.pdf"

BLUE = colors.HexColor("#2a78d6")
NAVY = colors.HexColor("#15325c")
INK = colors.HexColor("#0b0b0b")
MUTED = colors.HexColor("#52514e")
RULE = colors.HexColor("#d9d8d2")
TINT = colors.HexColor("#eef4fc")
GOODTINT = colors.HexColor("#e8f6ef")
WARNTINT = colors.HexColor("#fdf1ea")

W, H = letter
M = 0.75 * inch
CW = W - 2 * M

ss = {
    "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=24, leading=29, textColor=NAVY, spaceAfter=6),
    "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=12.5, leading=17, textColor=MUTED, spaceAfter=14),
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=NAVY, spaceBefore=6, spaceAfter=8, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=INK, spaceBefore=10, spaceAfter=5, keepWithNext=1),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=10.5, leading=15, textColor=INK, spaceAfter=7, alignment=TA_LEFT),
    "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=10.5, leading=15, textColor=INK, leftIndent=14,
                             bulletIndent=3, spaceAfter=4),
    "caption": ParagraphStyle("caption", fontName="Helvetica-Oblique", fontSize=9, leading=12.5, textColor=MUTED, spaceAfter=12),
    "box": ParagraphStyle("box", fontName="Helvetica", fontSize=10.5, leading=15, textColor=INK, spaceAfter=5),
    "boxhead": ParagraphStyle("boxhead", fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=NAVY, spaceAfter=6),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=9, leading=12, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=INK),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=9, leading=12.5, textColor=MUTED, spaceAfter=4),
}


def P(t, s="body"):
    return Paragraph(t, ss[s])


def bullets(items, style="bullet"):
    return [Paragraph(t, ss[style], bulletText="•") for t in items]


def fig(name, caption, width=0.88 * CW):
    from PIL import Image as PI

    path = FIG / name
    w, h = PI.open(path).size
    img = Image(str(path), width=width, height=width * h / w)
    return KeepTogether([img, Spacer(1, 3), P(caption, "caption")])


def box(title, lines, tint=TINT, edge=BLUE):
    inner = [P(title, "boxhead")] + [Paragraph(t, ss["box"], bulletText="•") for t in lines]
    t = Table([[inner]], colWidths=[CW])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), tint), ("LINEBEFORE", (0, 0), (0, -1), 3.5, edge),
        ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def table(rows, widths, header=True, zebra=True):
    data = [[Paragraph(str(c), ss["cellb" if (header and i == 0) else "cell"]) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("LINEBELOW", (0, 0), (-1, 0), 0.8, NAVY), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
          ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
          ("LINEBELOW", (0, -1), (-1, -1), 0.5, RULE)]
    if zebra:
        for i in range(1, len(rows)):
            if i % 2 == 0:
                st.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f6f6f3")))
    t.setStyle(TableStyle(st))
    return t


def on_page(c, doc):
    c.saveState()
    c.setStrokeColor(RULE)
    c.setLineWidth(0.6)
    c.line(M, 0.55 * inch, W - M, 0.55 * inch)
    c.setFont("Helvetica", 8.5)
    c.setFillColor(MUTED)
    c.drawString(M, 0.38 * inch, "Auction-flow strategy research  |  Phase A1 findings  |  23 Sep 2026")
    c.drawRightString(W - M, 0.38 * inch, f"Page {doc.page}")
    c.restoreState()


def on_first(c, doc):
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(0, H - 0.32 * inch, W, 0.32 * inch, stroke=0, fill=1)
    c.setFillColor(BLUE)
    c.rect(0, H - 0.38 * inch, W, 0.06 * inch, stroke=0, fill=1)
    c.restoreState()
    on_page(c, doc)


def sim_rows():
    s = pd.read_csv(REP / "letf_premium_sim.csv")
    rows = [["Trigger |e|", "Cost", "Universe", "Events", "Net / event", "P&amp;L total", "P&amp;L 2025", "Sharpe *", "Top-10 days"]]
    keep = ((s.k_bps == 50)) | ((s.cost_bps == 5) & (s.universe == "all funds"))
    s = s[keep].sort_values(["k_bps", "universe", "cost_bps"])
    for _, r in s.iterrows():
        rows.append([f"{r.k_bps:.0f} bps", f"{r.cost_bps:.0f}+1 bps", r.universe, f"{r.n_events:,.0f}",
                     f"{r.net_bps:.1f} ± {1.96 * r.se:.1f}", f"${r.pnl_total / 1e6:.2f}M", f"${r.pnl_2025 / 1e6:.2f}M",
                     f"{r.sharpe_ann:.1f}", f"{r.share_top10_days:.0%}"])
    return rows


def build():
    doc = SimpleDocTemplate(str(OUT), pagesize=letter, leftMargin=M, rightMargin=M, topMargin=0.75 * inch,
                            bottomMargin=0.8 * inch, title="Auction-Flow Strategy Research: Phase A1 Findings",
                            author="Claude (research partner)", subject="Leveraged ETF rebalancing and closing-auction dislocations")
    s = []
    # ---------------------------------------------------------------- cover / summary
    s += [Spacer(1, 6), P("Auction-Flow Strategy Research", "title"),
          P("Phase A1 findings: leveraged-ETF rebalancing flow, and a more promising lead in the ETFs' own closing auctions", "subtitle")]
    s.append(box("Bottom line", [
        "<b>The trade as specified in the handoff does not pass on free data.</b> Fading single-stock leveraged-ETF "
        "rebalancing overnight shows no net reversal by the next close. The price pressure builds from ~1:30 pm and is absorbed "
        "<i>before</i> the close. What's left overnight is small and concentrated in ~10 theme-wide sell-off days.",
        "<b>A promising lead turned up in the leveraged ETFs' own closing prices.</b> On big days the ETF closes away "
        "from its NAV. The part of that gap that forms in the last 30 minutes largely reverses by 10:30 the next morning "
        "(25-37 bps on large events, in every listing venue).",
        "<b>This is the 2007 trade in a new, small venue.</b> Thin ETF closing auctions absorb price-insensitive closing "
        "flow, while fair value (NAV = leverage × the underlying's closing price) is known exactly at 4:00.",
        "<b>The key unknown is executability.</b> Free data cannot tell a real auction imbalance from closing-price noise "
        "(bid-ask bounce in thin ETFs). The next step is cheap: check the bid/ask midpoint at 4:00 via IBKR, then auction prints.",
        "<b>Statistical honesty:</b> ~50 tests run in total. The last six months (from 23 Mar 2026) are held out and untouched.",
    ]))
    s.append(Spacer(1, 14))
    kpi = [["", "Strategy A: fade rebalance overnight", "New lead: LETF closing premium"],
           ["Signal", "Rebalance flow / daily volume", "ETF close vs NAV (premium change)"],
           ["Effect found", "~0 by next close; +6 ± 6 bps overnight ex top-10 days", "25-37 bps reversion by next morning on |e| >= 50 bps"],
           ["Robustness", "Concentrated (72-86% from 10 days); decaying", "All venues, all fund sizes; top-10 days 22-35% of P&amp;L"],
           ["Status", "Does not meet pre-committed bar", "Promising; executability unverified"]]
    s.append(table(kpi, [1.1 * inch, 2.75 * inch, 3.15 * inch]))
    s.append(Spacer(1, 10))
    s.append(P("How to read this report: sections 1-2 cover the data and the test of the original idea; section 3 covers "
               "the new lead; section 4 lists what could make it wrong; section 5 proposes next steps. All figures use "
               "in-sample data only (July 2022 to 20 March 2026).", "small"))
    s.append(PageBreak())

    # ---------------------------------------------------------------- 1. data
    s.append(P("1. What was built", "h1"))
    s.append(P("Everything uses free data (SEC EDGAR, issuer websites, Yahoo Finance). Each piece was validated before use."))
    s += bullets([
        "<b>Fund universe.</b> Built from the SEC's yearly fund lists (2022-2026), including funds that later closed: "
        "<b>286 daily-reset single-stock leveraged/inverse ETFs on 160 stocks</b>. Each fund's leverage was checked by "
        "regressing its daily returns on its stock's. This caught reused tickers (e.g. NVDB, TSLI), SEC ticker errors, and "
        "leverage changes (TSLQ -1x to -2x, MSTX 1.75x to 2x).",
        "<b>Fund assets.</b> 2,062 SEC N-PORT filings give quarter-end assets and monthly flows. GraniteShares and ProShares give "
        "exact daily assets. Against the exact data, the reconstruction's median error is <b>4.6%</b>.",
        "<b>Prices.</b> Daily prices for ~5,700 US stocks; hourly bars from Oct 2023 for the ~160 stocks, 600 comparison "
        "stocks and ~240 leveraged ETFs. 2.7 million stock-days in total.",
        "<b>Guardrails.</b> The six-month hold-out is enforced in code. Earnings days are excluded. Standard errors are "
        "clustered by date (and by stock in regressions).",
    ])
    s.append(fig("aum.png", "Figure 1. Reconstructed assets of US single-stock leveraged ETFs. Growth came mostly after "
                 "mid-2024; TSLA and NVDA funds are about half of the total."))

    # ---------------------------------------------------------------- 2. strategy A
    s.append(PageBreak())
    s.append(P("2. The original idea: fade the rebalance overnight", "h1"))
    s.append(P("Leveraged ETFs must buy after up days and sell after down days, near the close. The hypothesis was that "
               "this pushes closing prices away from fair value and reverses overnight. The test sorted stock-days by "
               "predicted rebalance flow as a fraction of daily volume, controlling for the stock's own move."))
    s.append(fig("event_study.png", "Figure 2. Average price path on the 5% of days with the largest predicted flow (blue) "
                 "vs. equally large moves in stocks with little leveraged-ETF flow (orange), signed in the flow direction "
                 "and relative to 13:30. The extra move happens between 13:30 and 15:30. There is nothing extra in the last "
                 "30 minutes, and no net reversal by the next close. 1,287 events, 45 stocks, Oct 2023 - Mar 2026."))
    s.append(P("Key results", "h2"))
    s.append(table([
        ["Test", "Result", "Verdict"],
        ["Pre-registered: flow predicts overnight / next-day reversal", "t = -1.8 overnight; t = 0.1 next close", "Fails"],
        ["Pressure in last 30 min (15:30 to close)", "t = -0.3", "None"],
        ["Top-decile flow vs same-day matched stocks, overnight", "+20 bps; +6 ± 6 excl. top-10 days", "Concentrated"],
        ["Same stocks, stock-specific slopes, overnight", "t = -3.1 to -3.9, but ~1-2 bps at typical flow", "Tiny"],
        ["Anticipation: flow at 13:30 predicts 13:30-to-close", "t = 2.7 pooled; t = 0.9 within stock", "Not LETF-specific"],
    ], [3.0 * inch, 2.6 * inch, 1.4 * inch]))
    s.append(Spacer(1, 10))
    s.append(fig("overnight.png", "Figure 3. Excess overnight reversal after top-decile flow days vs. same-day matched "
                 "stocks. It is driven by down days and a handful of dates: the ten biggest days were theme-wide sell-offs "
                 "in crypto and AI-infrastructure names (COIN, BMNR, CRCL, CLSK, IREN), a factor the QQQ hedge doesn't "
                 "capture. Without them, the effect is +6 ± 11 bps (95% CI)."))
    s.append(fig("placebo.png", "Figure 4. Placebo: the same stocks before any leveraged ETF existed, given the gamma they "
                 "later had. Afternoon momentum is about as strong without the funds, so it's a trait of volatile "
                 "retail-favorite stocks, not of the rebalance flow."))
    s.append(box("What this tells us", [
        "The rebalance flow is public and anticipated. It gets traded into during the afternoon and absorbed before the close, "
        "consistent with the published literature and heavy sell-side coverage in 2025-26.",
        "This matches how the 2007-2011 closing-cross edge faded: once a flow is widely computed, the pressure moves earlier "
        "and the close stops being the extreme.",
        "One correction during the work: an early run showed strong last-30-minute pressure (t = 6.2). That came entirely "
        "from bad data for ticker B (Barnes Group hourly vs Barrick daily history). After fixing it, the effect is zero.",
    ], tint=WARNTINT, edge=colors.HexColor("#eb6834")))

    # ---------------------------------------------------------------- 3. new lead
    s.append(Spacer(1, 10))
    s.append(P("3. The promising lead: the leveraged ETF's own closing price", "h1"))
    s.append(P("Instead of the stock, look at the ETF. At 4:00 its fair value is known almost exactly: NAV = yesterday's NAV × "
               "(1 + leverage × the stock's return to its official close). If the ETF's own closing price lands away from NAV, "
               "and that gap reverts, a liquidity provider can take the other side of the ETF's closing auction and hedge "
               "with the stock at the same moment. That is structurally the 2007-2011 trade, in a venue far too small for "
               "large firms."))
    s.append(P("The premium is measured exactly for 38 funds with published daily NAV (GraniteShares, ProShares). For all ~240 "
               "funds it uses a proxy, the day's fund return minus leverage × the stock's return, which correlates 0.69 "
               "with the exact measure."))
    s.append(fig("premium_threshold.png", "Figure 5. When the ETF closes at a premium or discount to NAV, the gap reverts the "
                 "next day, almost one-for-one. Exact-NAV funds, July 2022 - March 2026; bars show 95% CI."))
    s.append(fig("premium_intraday.png", "Figure 6. Left: of the day's premium change, the part formed between 15:30 and the "
                 "close is what reverts (52% next day, vs 9% for the part formed earlier). Right: on large events the "
                 "reversion is complete by 10:30 the next morning; nothing happens after. Funds with daily trading >= $20M."))
    s.append(fig("premium_venue.png", "Figure 7. The pattern appears on every listing venue. Cboe BZX listings (mostly T-Rex and "
                 "Defiance funds) dislocate most often. Not stale prices: the premium barely loads on the stock's move after "
                 "15:30 (-0.03 even in the thinnest funds; a stale print would load near -1)."))
    s.append(P("Illustrative P&amp;L", "h2"))
    s.append(P("Rule: when the fund's close is at least <i>k</i> bps rich or cheap relative to leverage × the stock (proxy), take the "
               "other side at the close, hedge with the stock at its close, and unwind at the next close. Size = the smaller of "
               "$1M or 1% of the fund's average daily trading. Costs: 5 or 10 bps on the fund leg plus 1 bp on the hedge. "
               "<b>This assumes you can trade at the official closing prices, which is exactly what is not yet verified.</b>"))
    s.append(fig("premium_pnl.png", "Figure 8. Cumulative P&amp;L of the illustrative rule (|premium change| >= 50 bps). Most of "
                 "the P&amp;L comes from 2025 onward, as the number of small single-stock ETFs exploded."))
    s.append(table(sim_rows(), [x * inch for x in (0.62, 0.62, 1.05, 0.55, 0.95, 0.72, 0.72, 0.6, 0.62)]))
    s.append(P("* Sharpe from daily P&amp;L across all business days, annualized, before hedge basis risk and financing. "
               "Net / event shows ± 95% CI.", "small"))

    # ---------------------------------------------------------------- 4. risks
    s.append(Spacer(1, 10))
    s.append(P("4. What could make the lead wrong", "h1"))
    s += bullets([
        "<b>Executability (the big one).</b> Yahoo's close is the official closing price. For a thin ETF it can be a small "
        "auction print or a last sale at the edge of a wide bid/ask spread. Then the \"reversion\" is just the price bouncing "
        "back to the middle of the spread, and it can't be captured. Everything in section 3 fits a real auction imbalance "
        "<i>and</i> closing-price noise; only the 4:00 bid/ask and the auction prints tell them apart.",
        "<b>Capacity.</b> ETF closing-auction volume is unknown. 1% of daily trading is a guess and may be optimistic for "
        "Cboe-listed funds.",
        "<b>Entry timing.</b> The premium is only known once both auctions print. Live, you'd act on indicative prices from "
        "imbalance feeds with limit or imbalance-only orders, so fill rates and adverse selection need modelling.",
        "<b>NAV basis.</b> Funds that hold options (e.g. MSTU in late 2024) or reset swaps off the close make NAV differ from "
        "leverage × stock, adding hedge risk.",
        "<b>Multiple testing.</b> ~50 tests have been run. The lead was motivated by mechanism (handoff item 10), not found "
        "by a sweep, but it still needs a single, final test on the untouched hold-out.",
    ])
    s.append(P("Handoff claims that were corrected", "h2"))
    s.append(table([
        ["Claim", "What the sources say"],
        ["600+ funds, $41-42B", "That's the whole single-stock channel; leveraged + inverse is ~488 funds / $34B (ETF Action, Sep 2026)"],
        ["$50B/day rebalancing record", "A peak on some days, mostly index funds; ~$20B 10-day average (Barclays)"],
        ["3x single-stock funds", "None exist in the US; SEC pushed back on 3x/5x filings (Dec 2025, Mar 2026)"],
        ["Exposure = leverage × assets", "Often false: MSTR funds were swap-constrained in Nov 2024 and used call options"],
        ["Nasdaq MOC cutoff 3:50", "3:55; Nasdaq imbalance-only orders are repriced to the inside bid/offer"],
        ["IBKR closing orders", "IBKR API has an imbalance-only flag for Nasdaq; no documented NYSE Closing Offset support"],
        ["Yahoo open = opening cross", "Not guaranteed; Yahoo's close is the official close, its open may be the first trade"],
    ], [2.1 * inch, 4.9 * inch]))

    # ---------------------------------------------------------------- 5. next steps
    s.append(P("5. Recommended next steps", "h1"))
    s.append(box("Cheapest first", [
        "<b>1. Bid/ask at 4:00 (free, needs your IBKR session).</b> Pull 1-minute bid/ask bars for ~30 leveraged ETFs on "
        "~50 large-dislocation days. If the premium still shows at the midpoint, it isn't just bounce.",
        "<b>2. Auction prints and imbalances (paid, ask first).</b> Closing-cross prints and imbalance messages for these "
        "ETF tickers (Nasdaq ITCH; Cboe BZX auction feed), e.g. from Databento. They measure auction size and whether our "
        "orders would have filled.",
        "<b>3. Live recorder (when ready).</b> Record closing imbalances for the ETFs <i>and</i> their stocks 3:50-4:00 daily. "
        "This builds the dataset that no historical source provides for free.",
        "<b>4. If it holds up:</b> freeze one simple rule and evaluate it once on the hold-out (23 Mar - 22 Sep 2026). Only "
        "after that, consider paper trading.",
        "<b>5. Natural extension:</b> the same NAV-anchored closing-auction trade in other thin ETFs (single-stock "
        "option-income, buffer, crypto spot ETFs).",
    ], tint=GOODTINT, edge=colors.HexColor("#1baf7a")))
    s.append(Spacer(1, 12))
    s.append(P("Where to find everything", "h2"))
    s.append(P("Code, data caches and the full research log (every variant tried, with results) are in the "
               "<font name='Courier'>kmeans_data</font> repository, branch <font name='Courier'>claude/new-session-0kch95</font>: "
               "<font name='Courier'>RESEARCH_LOG.md</font>, <font name='Courier'>reports/*.csv</font>, "
               "<font name='Courier'>analysis/</font>, <font name='Courier'>flows/</font>, <font name='Courier'>universe/</font>.", "small"))
    doc.build(s, onFirstPage=on_first, onLaterPages=on_page)
    print("wrote", OUT)


if __name__ == "__main__":
    build()
