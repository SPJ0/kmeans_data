# Phase A1: Leveraged-ETF Rebalancing Reversal, results on free data

Sample: July 2022 – September 21, 2026 (last trade date with a next-day outcome). Data as of 2026-09-22.
Everything below is reproducible from this repo (see README). All t-stats cluster by date
unless stated otherwise.

## Verdict: stop (kill criteria not met), with one caveat about 2026

| Continue criterion (from handoff) | Result | Pass? |
|---|---|---|
| Top bucket ≥ 10–20 bps beta-adjusted reversal before costs | Top decile of \|FlowRatio\|: **+9.7 bps** overnight (t = 1.72; t = 1.68 two-way clustered date+stock) | **No** (below the bar and not significant) |
| Significant beyond generic short-term reversal | FlowRatio coef. −61 bps per unit (t = −2.04) pooled with date FE; **t = −1.62** once r_t × treated is controlled; −46 (t = −1.85) within treated stocks. Matched placebo gap +15.0 bps (t = 2.19) | **Marginal** |
| Not concentrated in a few days or names | Gross simulated P&L is **negative excluding the top 10 days** (top-10 share = 171%) and **negative excluding the top 5 names** (IONQ, QUBT, HIMS, SMR, RGTI; share = 131%) | **No** |
| Present in the most recent year | 2026 YTD: +14.0 bps (t = 1.90); +22.5 bps vs matched placebo (t = 2.56) | Yes |

The decile pattern is **not monotone** (figure 1). Deciles 4–9 show small *continuation*
(−3 to −7 bps), and only decile 10 reverses. The simulated strategy is flat to negative net
of costs (net Sharpe −0.07 at half-spread + 2 bps; gross Sharpe 0.43).

**Caveat worth knowing.** The effect is concentrated in 2026, when aggregate
single-stock lev-ETF Gamma peaked. It averaged ≈$66B per 100% move, i.e. ≈$0.66B of flow per 1%
move across all names, against ≈$49B in 2025 and ≈$20B in 2024 (figure 4). The gross simulation lost money
steadily from mid-2022 through late 2025, then made all of it back and more in 2026
(figure 3). This fits an effect that only appears once flow is large relative to liquidity.
It also fits one lucky regime in the speculative names (quantum, nuclear, crypto-treasury)
that dominate the top decile. Nine months of data can't tell these apart.

Per the rule ("otherwise stop before paying for data"), **don't buy data**. The only
action I'd consider is the *zero-cost* Phase A2 collection: the IBKR closing-imbalance
logger and a daily holdings scraper. Run them for a quarter, then re-test 2026H2 out of
sample. That's your call; I haven't built them.

## What was built

| Piece | Where | Notes |
|---|---|---|
| Universe | `universe/single_stock_universe.csv` (408 included funds on 237 US-listed stocks; 292 active, **116 closed**) + `universe/index_candidates.csv` (211 index funds) | From SEC series/class files 2022–26 (closed funds included). Leverage/direction/reset parsed from names. Launch proven by N-PORT filings or Yahoo prices. Underlying checked against each fund's N-PORT swap reference instrument (all matched after fixes). |
| Hand verification | `universe/verify_by_hand.csv` (30 funds) | Mostly leverage changes (e.g. TSLL/NVDL/CONL ran at 1.5x in 2023), handled below. Please review. |
| Asset history | `flows/assets.py`, `flows/nport_bulk.py`, `flows/nport_recent.py`, `flows/current_aum.py` | N-PORT quarter-end net assets from the SEC bulk data sets (2022Q3–2026Q2) plus EDGAR filings made since July 2026. Daily path = fund's own daily return × units; units move with N-PORT *monthly* creations/redemptions, log-linearly corrected to hit each anchor. Latest anchor = current AUM (stockanalysis.com; TQQQ cross-checked to ProShares' own page within 1%). |
| Leverage by date | `flows/build_panel.py::snap_leverage` | Per-quarter realized ETF-vs-underlying beta snapped to {±1, 1.25, 1.5, 1.75, 2, 3}. SEC name history is annual and sometimes names a pre-launch registration. |
| Prices | `flows/prices.py` | yfinance daily OHLCV, split/dividend handling, bad-print filters (unadjusted splits, open outside H/L, zero volume, stale bars). |
| Earnings | `flows/earnings.py` | SEC 8-K Item 2.02 dates (yfinance fallback); trade dates D−2…D+1 excluded (113k stock-days). |
| Flow math | `flows/flow.py`, `tests/test_flow.py` | T = L·A_t − E·(1+r); simplified A·L(L−1)·r; stacking, off-target exposure, post-trade exposure = target. 35 tests pass. |
| Analysis | `analysis/run_a1.py`, `analysis/index_check.py` | Everything in `reports/`. |

### Asset reconstruction accuracy (`reports/asset_validation.csv`)
- **Quarter hold-out** (predict each N-PORT anchor from the previous one using the monthly flows):
  median |log error| **4.5%**, dollar-weighted 8.4% (939 fund-quarters > $5M). Ignoring
  creations/redemptions gives 46%, so the flow data matters a lot.
- **Last N-PORT anchor rolled forward to current AUM, no flows:** median error 40%. The last
  3–5 months are only as good as the current-AUM anchor, which is now used.
- Sanity check: reconstructed MSTR flow on 2024-11-21 is **−$2.4B**, matching reports of
  >$2B single-day MSTR rebalancing in Nov 2024. Reconstructed channel assets are ≈$33–40B in
  mid/late 2026, against the ~$41–42B reported; I exclude crypto, private-company and
  non-US underlyings.

## Main results

### 1. Sorts (`t1_*`, `fig1_deciles.png`)
53,526 treated stock-days (237 stocks). Signed reversal = −sign(Flow)·R, bps, overnight
(close_t → open_t+1), beta-adjusted using a trailing 60-day beta to the best-fit benchmark
among SPY/QQQ/SMH/BITO.

| \|FlowRatio\| decile | 1 | 4 | 7 | 9 | **10** |
|---|---|---|---|---|---|
| median \|FlowRatio\| | 0.000 | 0.002 | 0.016 | 0.065 | **0.20** |
| overnight xs, bps (t) | −0.7 (−0.5) | −4.8 (−2.2) | −4.3 (−1.6) | −6.7 (−1.6) | **+9.7 (1.7)** |
| close→close xs, bps (t) | 0.2 | −5.0 | 3.3 | 3.5 | 22.1 (1.7) |
| hit rate | 48% | 50% | 49% | 49% | 53% |

Fixed ex-ante thresholds: \|FR\| in [0.3, 1.0) gives +28.7 bps (t = 2.77, n = 1,328, 55 stocks).
\|FR\| ≥ 1 gives −26 bps (n = 80). Treat the first as a nominal result from one of six bins.

### 2. Generic-reversal control (`t3_regressions.csv`, `fig2_double_sort.png`)
Regression of next overnight beta-adjusted return (bps) on r_t, \|r_t\|, r_{t−1}, r_t × z(log ADV),
r_t × z(vol), and FlowRatio (winsorized 0.5/99.5%), with date fixed effects.
1.55M stock-days, including 1,376 S&P 1500 stocks that never had a lev ETF:

| Spec | FlowRatio coef | t |
|---|---|---|
| A: all stocks, date FE | −60.7 | −2.04 |
| B: A + r_t × treated | −39.9 | −1.62 |
| C: date + stock FE, 2-way cluster | −59.5 | −2.08 |
| D: treated only | −45.7 | −1.88 |
| E: treated only, stock FE | −45.1 | −1.85 |
| G: close→close outcome | −86.2 | −1.57 |

At the top-decile median FlowRatio (0.20), −60 bps per unit is about 12 bps. The double
sort shows no extra reversal: within each \|r_t\| quintile, stocks with high lev-ETF Gamma
do not reverse more than stocks with none.

### 3. Matched placebo (`t4_*`, `fig5_placebo_by_year.png`)
Each top-decile treated stock-day is matched to a same-day, same-sign-move, never-treated
stock, nearest on (r_t, log ADV, 60-day vol). ADV stands in for market cap.
Treated +9.7 bps vs matched −5.2 bps, a **gap of +15.0 bps (t = 2.19)**.
By year: 2024 −25.0 (t −1.2, n = 295), 2025 +4.5 (t 0.4), **2026 +22.5 (t 2.56)**.

### 4. Splits (top decile, `t5_splits_top_decile.csv`)
- Year: 2024 −18.9, 2025 +5.1, 2026 +14.0 bps. Pooled breakpoints put no 2022–23 days in the top decile because flows were small then. The simulation uses trailing thresholds, so it does trade 2022–23.
- Long vs inverse mix: mostly-long +8.6, mixed +14.5, inverse-heavy +20.7 (n = 238).
- ADV tercile: low +4.8, mid +19.9 (t 2.8), high +4.4.
- Direction: sell-flow (down) days +13.5, buy-flow (up) days +5.9.
- Opex: quad-witching +73.5 bps (n = 119, t 1.6), monthly opex −1.0, other days +8.6.
- Day of week: noisy, Thursday best (+21).

None of these is stable enough to build a rule on without overfitting.

### 5. P&L simulation (`t6_*`, `t7_concentration.csv`, `fig3_cum_pnl.png`)
Rules:
- Each day, trade treated names whose \|FlowRatio\| ≥ the trailing-250-day 90th percentile (no look-ahead).
- Size = min(10% × |predicted flow|, $500k), gross capped at $5M.
- Fade at the close, beta-hedge, exit at the next open.
- Costs per round trip: assumed half-spread by ADV bucket (1/2/5/10/20 bps), plus 2 or 5 bps, plus 0.5 bp × |β| hedge.

| | Ann. return on $5M | Sharpe | Max DD | Total P&L |
|---|---|---|---|---|
| Gross | +3.6% | 0.43 | −30% | +$0.75M |
| Half-spread + 2 bps | −0.6% | −0.07 | −34% | −$0.12M |
| Half-spread + 5 bps | −3.5% | −0.41 | −39% | −$0.72M |

Average deployed capital is $2.2M. Size-weighted gross edge is **3.7 bps per trade**, below
the ~4.9 bps assumed cost. P&L by year (gross, $M): 2022 −0.02, 2023 −0.55, 2024 −0.65, 2025 +0.33, 2026 +1.64.

### 6. Index-level secondary check (`t9_index_secondary_check.csv`)
Index lev-ETF families (TQQQ/SQQQ, SOXL/SOXS, UPRO/SPXU, TNA/TZA, FAS/FAZ, LABU/LABD, …),
with flow computed the same way on proxy ETFs, 1,058 days, Newey-West SEs.
Neither standardized flow nor r_t × relative Gamma predicts the next overnight or
close-to-close return. |t| < 2 in 21 of 22 regressions; the exception is FXI, t = −2.0.

## Things that could be wrong (and what they'd do)

- **Flow timing / look-ahead.** Flow uses the full close-to-close r_t; live, you'd estimate it
  at ~3:50 pm. Asset paths between N-PORT dates are interpolated toward *future* quarter-end
  anchors. Both only scale flow and mostly help the signal, so they don't explain a null.
- **Not all flow hits the close.** Swap dealers pre-hedge intraday, and the 10%-of-ADV auction
  proxy is a guess. This is the biggest unknown, and only Phase A2 imbalance data answers it.
  If most flow is absorbed before 3:50, a weak close-to-open reversal is what you'd expect.
- **Survivorship.**
  - 116 closed funds are included. Their daily path uses L × r_t because Yahoo doesn't carry delisted ETFs.
  - 205 registered series never traded and are excluded correctly.
  - The **placebo pool is current S&P 1500 constituents**, which is survivor-biased.
- **Costs.** No free historical quotes, so half-spreads are assumed by ADV bucket.
  Auction-to-auction fills don't pay the spread but do carry adverse selection, which isn't
  modelled. The Abdi-Ranaldo high/low estimator gave a 34 bp median and was discarded as not credible.
- **Market cap.** Proxied by ADV; there's no free point-in-time market-cap history.
- **Yahoo opens** approximate the opening cross.
- **Nothing looks "too good".** The only large numbers are quad-witching (n = 119) and the
  [0.3, 1.0) FlowRatio bin (t = 2.8). With ~30 splits tested, expect one or two at that level by chance.

## Data provenance and what I did not do
- **Paid data:** none bought.
- **Sources used:** SEC EDGAR / DERA (N-PORT bulk data sets, series-class files, submissions API, 8-K items), Yahoo via yfinance, stockanalysis.com (current AUM), Wikipedia (S&P 1500 lists).
- **Blocked sources:**
  - Direxion's site returns 403.
  - Yahoo's quote-summary endpoint (`Ticker.info`) returns 401 from this environment, hence stockanalysis.com for AUM.
- **Not built:** no live-trading code, no IBKR code, nothing in Phase A2.
