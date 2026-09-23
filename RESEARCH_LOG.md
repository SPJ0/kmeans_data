# Research Log — Auction-Flow Strategies

Newest entries at the bottom. Each entry: what was tried, why, result, what was learned.
Variant counter (for multiple-testing discount): **~50 outcome-bearing tests run so far** (as of 2026-09-23, see entries below).

## Ground rules (fixed 2026-09-23, before any outcome data was examined)

- **Hold-out:** every stock-day with date **≥ 2026-03-23** is held out. No code may compute
  next-day/overnight outcomes on those dates until a final candidate is frozen. Evaluated once.
  (The 2026-09-23 sizing check below used recent AUM, ADV and volatility only, not returns
  conditioned on flow.)
- **Primary spec (pre-registered, to limit forking):** outcome = beta-adjusted close(t)→open(t+1)
  and close(t)→close(t+1) return; signal = predicted rebalance flow / ADV20 (lagged);
  control = own return r_t interacted with volatility; date fixed effects; SEs two-way
  clustered by date and stock (see note 5 below on why date-only clustering is not enough).
  Everything else is a logged variant.

---

## 2026-09-23 — Critical read of the handoff (before writing analysis code)

### The core question: why would this inefficiency still exist?

The handoff frames this as "flow in venues too small or too new for large firms." For
Strategy A that framing mostly **does not hold**, and I think it's the weakest premise:

- The venue is the Nasdaq/NYSE closing auction, the most heavily competed liquidity event in
  US equities. It is the same venue where the 2007–2011 edge was competed away. The underlyings
  (TSLA, NVDA, MSTR, COIN, PLTR…) are among the most liquid and most-watched stocks.
- The flow is **public and trivially computable**. Anyone with fund AUM and the day's return
  can compute it by 3:50 p.m., and sell-side desks publish estimates. A predictable imbalance
  that everyone can compute gets front-run through the afternoon (pressure shows up before
  the close) and faded at the close by professional auction liquidity providers.
- There is an academic literature on exactly this: end-of-day momentum from LETF and option
  hedging, then next-day reversal (see the "Verification" section below). A published,
  well-known effect should mostly be priced.

**A premise that does survive:** the payoff to fading this flow is less an information edge
than **a risk premium for warehousing overnight inventory** in very high-volatility names.
HFT auction liquidity providers are flat-by-close businesses and avoid overnight gap risk in
names like MSTR/COIN (roughly 5% daily σ). If there is a durable edge, it's compensation for
carrying risk they won't carry. That changes what to test for:

- Returns should scale with the **overnight risk** of the position, not only the flow size.
- Expect a bumpy, fat-tailed P&L with correlated gap risk (crypto and AI clusters), not the
  <1% losing-day profile of the 2007 strategy.
- Beta/sector hedging matters more than in the original strategy, and the hedge (e.g. BTC
  proxy for MSTR/COIN) has its own basis risk.

The "too small for big firms" argument does apply to **mid-cap underlyings with young 2x
funds** (e.g. OKLO, IONQ, RGTI, SMCI-type names). But those funds are mostly 2025–26
launches, so the sweet spot has the **least history**. Much of it may fall inside the hold-out.

### Strongest reasons Strategy A might not work

1. **Crowding / anticipation** (above). The close may already be near equilibrium because
   anticipators pushed the price in the last hour. The move to exploit might be *momentum
   into the close* rather than reversal after it. The event study decides this.
2. **Flow is small in most names.** Rough sizing (below): on a 1σ day, rebalance flow is about
   2–3.5% of ADV in MSTR/COIN/OKLO/TSLA, under 1% in NVDA/AMD, and negligible in
   AAPL/AMZN/META/AVGO. A square-root-impact prior (impact ≈ 0.5·σ·√(Q/V)) gives about 50 bps of
   total impact for MSTR on a 1σ day. Only the *temporary* part reverts, and it gets split with
   everyone else fading it. For a 1σ day in NVDA the prior is about 12 bps total, which
   leaves nothing to capture after sharing and costs.
3. **Swap dealers net and pre-hedge.** Single-stock LETFs get exposure through total return
   swaps. The dealer only has to hedge its *net* book (other clients' swaps, its own
   inventory, options) and can hedge over the afternoon. The fund's rebalance is not
   necessarily an MOC order of the same size. Only the imbalance-feed calibration (A2) can
   measure how much actually reaches the auction.
4. **Creations/redemptions offset rebalancing, and the timing differs.** Retail tends to buy
   leveraged-long funds after down days, which offsets rebalancing. Also, LETF market makers
   hedge retail's intraday ETF buying in the underlying *intraday* and then create or redeem
   at the close, so the close-time net is ambiguous. Ivanov & Lenkey-type evidence suggests
   the offset is large for index LETFs.
5. **Identification is hard.** For a given stock, flow is literally `Gamma × r_t`: a scaled
   own return. The "beyond generic reversal" test therefore relies entirely on variation in
   Gamma/ADV across stocks and over time. Gamma/ADV is high exactly in retail-favorite,
   high-volatility, high-option-activity names, which have their *own* reversal and overnight
   return patterns. Matched placebos will be poor, because no untreated stock looks like MSTR.
   **Better design:** within-stock variation from staggered fund **launches and AUM growth**
   (difference-in-differences). Does the same stock's r_t → next-day reversal relationship
   strengthen after LETF AUM appears? We also get free placebo periods (pre-launch years).
6. **Overnight drift confound.** Retail-heavy, high-beta stocks earn most of their return
   overnight (Lou–Polk–Skouras "tug of war"). Fading up-days means shorting into that drift;
   fading down-days means buying with it. Expect a strong up/down asymmetry that isn't
   about LETFs. Report the two sides separately and control for the stock's own average
   overnight return.
7. **Small effective sample.** Material single-stock LETF AUM dates only from about 2024.
   After the 6-month hold-out that leaves roughly 18–24 months, concentrated in about 10–20 names in
   two or three correlated clusters (crypto, AI/semis, TSLA). With overnight idiosyncratic σ
   of ~2–3% and heavy cross-sectional correlation, a 15 bps effect is near the edge of
   detectability (rough SE 5–10 bps). Clustering by date alone overstates precision; we need
   two-way clustering, plus a leave-one-name-out and leave-one-cluster-out check. The
   concentration check is central, not a formality (e.g. Nov 2024 MSTR alone could drive it).
8. **Other mechanical flows are much larger and co-move with r_t.** Options dealer gamma
   hedging (0DTE/weekly in exactly these names), index LETFs (TQQQ/SOXL flow lands on
   NVDA/TSLA via index weights), and covered-call ETFs. Omitting index-LETF flow understates
   Flow for mega-caps. It should be added as a component.
9. **Execution reality.** The trade needs the flow estimate by ~3:50 p.m. (fine, since r_t to
   3:50 is known). It also needs IO/CO order types via IBKR (unverified). Exiting at the open
   cross on the same names that gap is noisy. The overnight hedge (QQQ/SMH/BTC proxy) is
   imperfect.

### What the baseline must show to be encouraging

Pre-committed, before seeing results:

1. **Dose-response:** the reversal rises monotonically with Flow/ADV *conditional on* r_t (and
   r_t × vol), not just across unconditional deciles.
2. **Within-stock:** the effect survives stock fixed effects and shows up in the
   pre/post-launch or AUM-growth comparison. Pre-launch periods should show no "effect" for
   the same hypothetical Gamma.
3. **Magnitude:** ≥ 10–20 bps beta-adjusted reversal in the top bucket before costs (the handoff's
   bar). It should also roughly match the square-root-impact prior. An effect far *larger*
   than the prior is a red flag for a confound.
4. **Where the pressure sits:** the intraday event study shows price moving in the direction of
   the flow in the last 10–30 min (ideally in the auction print itself), then reverting. If
   the pressure builds from 2 p.m. and the close isn't the extreme, the overnight fade is the
   wrong trade (→ assumption #1/#2 in the handoff).
5. **Robustness:** present in both up- and down-move days (or a mechanism explains the
   asymmetry), present in the most recent in-sample year, not dependent on the top 10 days or
   top 5 names, and survives leave-one-cluster-out.
6. **Total search size logged.** Anything found after more than ~10 variants gets a haircut and must
   pass the hold-out once.

What would make me recommend dropping the overnight-fade version (not the whole idea):
reversal ≤ generic-reversal control in the within-stock design, *and* the event study shows no
concentration of pressure at the close.

### Claims in the handoff I believe are wrong or doubtful

(Fact-check details and sources: see "Verification" below.)

- **"Too small/new for large firms"**: doubtful for the main names (see above). True only for
  the mid-cap tail.
- **`E = L × A`**: often false in exactly the interesting periods. In late 2024, MSTR funds ran
  below target leverage because of swap-capacity limits. Leverage targets have also changed
  (e.g. 1.75x → 2x). Holdings-based E matters, and the general formula (already implemented)
  handles it.
- **Yahoo Open ≈ opening cross**: unreliable; Yahoo's open can be the first consolidated trade.
  Use it for exploration, but the close→open leg needs verification against official opening
  cross prices (IBKR or paid data) before trusting bps-level results.
- **`AuctionProxy = 0.10 × ADV`**: the closing-auction share is lower in retail-heavy,
  high-turnover names than the market-wide ~10%. The proxy is probably biased *across* exactly
  the stocks we compare. Primary normalization should be Flow/ADV (where no fraction needs to be
  assumed), with the auction-share version as a variant once real close prints are available.
- **"600+ funds, $41–42B"** counts the whole single-stock channel, options-income funds
  included. Leveraged plus inverse is about **488 funds / $34B**. Half of all leveraged ETFs have under $7M,
  and 63 single-stock leveraged ETFs closed in 2026. The tail is mostly dust.
- **"$50B/day record"** is a peak on some days (Bloomberg's Simon White), mostly index funds, not
  a daily run-rate. A Barclays figure puts the 10-day average near $20B/day.
- **Exit "in the opening cross" and fills "at aggressively favorable prices"**: Nasdaq IO buys
  are repriced to the Nasdaq best bid (sells to the best offer), so "aggressive" is bounded by
  the book at 4:00. MOC entry on Nasdaq runs to **3:55**, not 3:50. IBKR has an `ImbalanceOnly`
  API flag (Nasdaq), but **no documented NYSE Closing Offset support**.
- **Leverage menu**: no 3x single-stock ETFs exist in the US. Rule 18f-4 caps them at about 2x, and the SEC
  pushed back on 3x/5x filings in Dec 2025 and Mar 2026. So the universe is L ∈ {1.25, 1.5,
  1.75, 2, −1, −1.5, −2}, and the multipliers that matter are 2 (2x, −1x) and 6 (−2x).
- **Flow math**: correct. Verified algebraically and in unit tests (`tests/test_rebalance.py`).
  One addition: L=1.25 and 1.5 funds have tiny multipliers (0.31, 0.75), so they barely
  matter. L=1.75 (1.31) matters for MSTX's history.

### Proposed changes to the plan

1. Make the **within-stock launch/AUM-growth design** the primary test of "beyond generic
   reversal." Keep matched placebos as secondary.
2. Add **index-LETF flow allocated by index weight** as a flow component for constituents.
3. Treat **"momentum into the close"** as a co-equal hypothesis, not a fallback. The
   event study runs first, before any P&L sim. Frame the baseline as an out-of-sample
   replication of Barbon et al. on 2024–26 single-stock funds, and check whether the effect scales with
   Flow/ADV the way their index-era estimates imply.
4. Start the **cheap live recorders now** (IBKR closing imbalance 3:50–4:00, daily issuer
   holdings/AUM archive). The historical free data is thin and the sweet-spot names are
   young, so every day of real E and real imbalance collected now is worth more than any
   backfill.
5. Budget flag: a clean answer probably needs **official auction prints and imbalance history**
   (Databento). I won't spend without asking, but I expect to ask after the free-data baseline.

### Verification (2026-09-23)

Three web research passes. Items marked † were only seen in search excerpts or secondary
coverage (paywall or 403), not read in full.

**Market / regulatory**

| Claim | Verdict | Source |
| --- | --- | --- |
| $50B/day rebalancing record mid-2026, 4x start of year | Peak on "some days", not typical† | Benzinga Jul 2026 citing Bloomberg (S. White)† |
| 600+ funds, 18 issuers, $41–42B | Channel-wide; LETF ≈ 488 funds / $34B | ETF Action 17 Sep 2026; Reuters 25 Aug 2026 |
| First US single-stock LETFs | 14 Jul 2022 (AXS) | AXS press release |
| MSTR LETF flows > $2B on single days, Nov 2024 | Confirmed | CoinDesk on JPMorgan note, 5 Dec 2024 |
| MSTR swap-capacity squeeze | Confirmed: MSTU was offered $20–50M of swaps vs ~$1.3B needed, so it used calls. MSTX 1.75x → 2x on 29 Oct 2024 | MSTU N-CSRS; MSTX 497 supplement |
| 3x single-stock funds | None in the US. 18f-4 VaR limit; SEC letters 2 Dec 2025 | SEC letter; Daily Upside Aug 2026 |

**Swap structure.** TSLL uses TRS with BNP, GS, Nomura, BofA, Citi and others, at SOFR + 3.7–4.5%. NVDL uses
mainly Cowen. MSTU (Feb 2025) had $1.87B of swaps on $0.97B of assets with Cantor, Marex and Clear Street,
at financing of **overnight bank rate + 1,500 to 10,000 bps**, which shows how scarce MSTR
swap capacity was. **No public document states whether notional changes are priced at the
close or at the dealer's execution price** (that is in private ISDA terms). The funds only say
they rebalance "at the close." So whether the dealer's hedge is an MOC order is empirical (A2).

**Literature** (all pre-date our sample unless noted)
- Cheng & Madhavan 2009; Tuzun 2013: the flow exists and is concentrated near the close.
- Ivanov & Lenkey 2018 (index LETFs, 2006–14): creations and redemptions **largely offset** rebalancing,
  and the net late-day effect is economically insignificant. This is the strongest prior against us.
- Shum et al. 2016: end-of-day volatility rises with rebalancing demand relative to volume,
  especially on volatile days.
- Baltussen–Da–Lammers–Martens 2021: last-30-minute momentum from short-gamma hedging, which reverts
  over the following days.
- Barbon–Beckmeyer–Buraschi–Moerke (SSRN 3925725): **individual stocks**. LETF demand produces
  last-30-minute momentum that **reverses at the next day's open**. This is the closest existing test of our
  hypothesis, so we should replicate it and ask what's left after its publication.
- Zhao, "Preying on Leveraged ETFs" (arXiv, Aug 2026)†: speculators front-run the close
  rebalance, then sell into it. About 75% of the first-day move reverses by the next close (Korea).
  This supports the mechanism, but it also tells us who's already on the other side.
- Lenkey 2024 survey†: effects are statistically significant but economically small.

**Implication.** Published evidence says the move happens *into* the close and reverts
overnight, so the proposed trade has the sign right. It also says the effect is known.
Our incremental claim has to be about **2024–26 single-stock scale**, where flows relative
to liquidity are far larger than in the index-LETF samples those papers used.

**Data availability (drives the asset-history plan)**
- **N-PORT:** only fiscal-quarter-end reports are public (about a 60-day lag), and the monthly-public
  amendments are delayed to 2027–28. Each quarterly filing does include **monthly flows
  (sales/redemptions for all three months) and monthly returns**, so month-end AUM can be
  rebuilt. Swap notionals give actual E at quarter-end. Pull per-filing XML via EDGAR full-text
  search, not the ~450 MB zips.
- **Daily AUM free:** GraniteShares (NVDL, CONL, PTIR, AMDL…) via its NAV-history API, and
  ProShares via `historical_nav.csv` (53 MB, with shares outstanding and AUM for all funds).
- **No daily history:** Direxion (TSLL, the largest), Defiance, T-Rex/REX, Tradr, Leverage
  Shares. Current-day holdings only, so start archiving now. `direxion.com/holdings/TSLL.csv`
  is curl-accessible.
- **yfinance:** `get_shares_full` returns nothing for ETFs; `.info` gives only the current value.
- **Survivorship:** the SEC's yearly investment-company series/class CSVs (2023–26) plus N-PORT series
  names include closed funds. `company_tickers_mf.json` has current tickers only.
- **Consequence:** daily Gamma will be exact for GraniteShares/ProShares funds, month-end-anchored
  and interpolated for the rest. Since flow = Gamma × r_t and r_t dominates day-to-day
  variation, a few % error in Gamma matters much less than getting E right in episodes
  like Nov 2024. Assumption #4 (restrict to exact-AUM funds) is a natural robustness split.

### Sizing check (2026-09-23, descriptive only)

Current Yahoo `totalAssets` for 30 well-known single-stock LETFs (partial universe, leverage
from fund names, unverified; my first-pass labels already had one error, TSLQ = −2x not −1x).
Flow for a 1σ day = Gamma × σ_daily; ADV = 20-day mean dollar volume.

| Underlying | LETF AUM | Gamma | 1σ day flow / ADV | vs 10%-ADV close proxy |
| --- | --- | --- | --- | --- |
| MSTR | $0.92B | $2.2B | 3.5% | 35% |
| COIN | $0.63B | $1.3B | 3.4% | 34% |
| OKLO | $0.13B | $0.26B | 3.3% | 33% |
| TSLA | $4.2B | $8.6B | 2.2% | 22% |
| IONQ | $0.14B | $0.29B | 1.9% | 19% |
| PLTR | $0.89B | $1.8B | 1.9% | 19% |
| SMCI | $0.16B | $0.32B | 1.3% | 13% |
| NVDA | $4.9B | $10.0B | 0.9% | 9% |
| AMD | $0.90B | $1.8B | 0.8% | 8% |
| GOOGL, MSFT, META, AMZN, AVGO, AAPL | — | — | < 0.5% | < 5% |

Takeaways: a handful of high-vol names carry meaningful flow; mega-cap single-stock LETFs are
irrelevant except NVDA/TSLA; mid-cap names with ~$150M of LETF AUM already reach MSTR-like
ratios. The MSTR fund complex is much smaller now than at its late-2024 peak, so the
cross-section of "treated" names moves around a lot over time. That variation helps
identification.

---

## 2026-09-23 — Data build (no outcome data examined in this entry)

User direction: do everything possible with free data; estimate what can't be collected.

**Universe** (`universe/`): union of SEC investment-company series/class snapshots 2022–2026
(includes closed funds), parsed names → leverage, direction, reset frequency, underlying.
Then verified each fund's leverage by regressing its daily return on the underlying's
(`verify_leverage.py`), and built a per-date leverage schedule (`finalize.py`).
Findings that mattered:
- **Ticker reuse** is common: NVDB (AXS 1.25x → ProShares 2x), TSLI (GraniteShares −1x →
  ProShares 2x), and AMAX/COPL/FORL/MARU/CRML now point at unrelated products. A series only
  owns a ticker within its N-PORT activity window.
- **SEC ticker errors**: T-REX inverse AMD/PLTR are listed under Direxion's −1x tickers.
- **Leverage changes** detected from returns: TSLQ −1x → −2x, CONI, NVDS; MSTX 1.75x → 2x.
- Two bond funds slipped in through "ultra-short" wording; excluded.
- Final: **286 daily-reset single-stock series on 160 underlyings**, 240 with attributable
  prices. Weekly/monthly-reset funds excluded (they don't rebalance daily).

**Fund assets** (`flows/assets.py`): 2,062 N-PORT filings (324 series) via EDGAR full-text
search; exact daily AUM from GraniteShares' API (34 funds) and ProShares' history file.
- N-PORT monthly *returns* are unreliable (decimals vs percent; not split-adjusted, e.g. MULL
  −95% in a month its assets grew 8x). So: quarter-end net assets → share-count anchors,
  monthly N-PORT dollar flows shape the path between anchors, NAV from our own price proxy.
- **Validation vs exact issuer AUM** (37 funds): AUM-weighted median |log error| **4.6%**;
  90th percentile ~28%, concentrated in months of explosive fund growth. N-PORT's
  month 1/2/3 ordering was confirmed empirically (reversed order: 14.7% error; no flows: 9.6%).
- 38% of fund-day AUM is exact, 58% interpolated, 4% extrapolated.
- Reconstructed total single-stock LETF AUM: $2B (end-2023) → $19B (end-2024) → $28B
  (end-2025) → $21B (Mar 2026). Big funds check out (TSLL $6.1B, NVDL $4.7B end-2025).
- Issuer AUM changes correlate −0.07 to −0.23 with the *prior* day's NAV change: creations
  and redemptions lean contrarian, as expected (partial offset to rebalancing).

**Prices**: Yahoo daily for LETFs, underlyings and ~5,700 listed common stocks (control
universe, current listings only). Yahoo 60-minute bars reach back to Oct 2023 (more than the
documented 730 days). The last hourly bar's close is the last trade before 16:00, 2–3 bps from
the official close; so official close = daily close, and "15:30 price" = open of the 15:30 bar.
- Data bug found and fixed: ticker **B** has Barnes Group hourly history but Barrick daily
  history before 2025. Rule: drop hourly data on any day where the 15:30 bar's close is >3% from
  the daily close.

**Panel** (`analysis/panel.py`): 2.7M stock-days (3,499 stocks with ADV ≥ $20M, 2019 → hold-out),
with **hold-out masking enforced in code**: any outcome whose window reaches 2026-03-23 is NaN.
Flow = Gamma × r_t with Gamma = Σ A_{t−1} L(L−1) (known before the open).
Earnings days ±1 excluded for treated names (Yahoo calendar; after-close reports assigned to
the next session).

---

## 2026-09-23 — Baseline (Phase A1) and first iteration

All in-sample (t ≤ 2026-03-19); hold-out untouched. Beta-adjusted with QQQ (60-day, lagged).
Treated stock-days ≈ 29.8k (2022-07 → 2026-03), earnings ±1 day excluded.
Tests run in this entry: ~34 (listed below). Treat any single t-stat accordingly.

### 1. Pre-registered primary spec (overnight / next-close reversal)
`on1_x`, `cc1_x` ~ flow/ADV20 + r_t + |r_t| + r_t·vol60, date FE, 2-way clustered (date, stock),
full cross-section (3,007 stocks):
- overnight: coef −0.065 per ADV of flow, **t = −1.8**
- close→next close: +0.011, **t = 0.1**; open→close t+1: +0.079, t = 1.0; 5-day: t = −0.1
→ **Fails.** Nothing reverses by the next close.

### 2. Variants on the reversal
- Within-stock (stock-specific r_t slopes, treated names only): overnight **t = −3.9**; next close t = −0.7.
  Survives dropping the top-10 dates (t = −3.1) and crypto-linked names (t = −2.9).
  But the magnitude is tiny: 1–2 bps at a typical top-decile flow (1–2% of ADV).
- Top-decile |flow| vs same-date untreated stocks matched on sign and |r_t|/vol60:
  overnight excess **+19.7 bps (t ≈ 2.9)**, but:
  - asymmetric: down days +34 bps, up days +4;
  - by year: 2024 −1, 2025 +14, 2026 +38 (54 dates);
  - **72–86% of the total comes from the top 10 dates**; excluding them: **+5.8 ± 5.5 bps**;
  - top dates are theme-wide sell-offs in crypto/AI-infra names (COIN, BMNR, CRCL, CLSK, IREN,
    APLD), i.e. a factor QQQ-beta doesn't hedge;
  - next close: +3 bps (t ≈ 0.2).
- Pre-launch placebo (same stocks before any LETF existed, fake gamma = their later gamma):
  overnight −20 bps (continuation) vs +19 real. Supports *some* LETF-specific overnight effect,
  but the pre-launch window is earlier (2022–24 regime) and next-close is indistinguishable.
- **Caveat:** "overnight reversal then next-day continuation" is also the signature of noisy
  opening prints; Yahoo's open is not the official opening cross price.

### 3. Where is the pressure? (hourly event study, Oct 2023 →; `reports/event_study_hourly.png`)
Top 5% |flow predicted at 15:30| (1,287 events, 45 names) vs same-size moves in low-gamma names:
- 13:30→15:30: +80 bps in the flow direction vs +40 (excess **+40 bps**)
- 15:30→close: **no excess**. Overnight dip ~−19 bps, fully recovered on t+1; t+1 close +50 bps excess.
- **The close is not the extreme; the pressure builds from early afternoon.** (Handoff assumptions #1/#2.)
- Pressure regression (15:30→close on flow at 15:30): t = −0.3.
  **Correction:** a first run showed t = +6.2, driven entirely by the ticker-B hourly/daily
  mismatch. Fixed; the t = 6.2 result was an artifact.

### 4. Anticipation variant (signal knowable at 13:30)
`r(13:30→close)` ~ gamma·r(close[t−1]→13:30)/ADV + controls, 741 stocks with hourly data:
- pooled **t = 2.7** (all of it 13:30→15:30, t = 3.2; last 30 min t = −0.6)
- **within-stock t = 0.9** (not robust)
- top-5% matched excess: **+18.8 bps (t ≈ 2.5)**; by year 2024 +50 (5 names, mostly MSTR),
  2025 +22, **2026 +1** → decaying; top 10 days = 71%, top 5 names (MSTR, SMR, QBTS, ASTS, IREN) = 68%
- **pre-launch placebo: +13.8 ± 13.4 bps vs +18.8 real → indistinguishable.**
  Afternoon momentum looks like a property of volatile retail names, not of LETF flow.

### What I learned
1. The single-stock LETF close flow is **absorbed before and at the close**. There's no residual
   pressure in the last 30 minutes and no net reversal by t+1's close. This is consistent with a
   crowded, anticipated flow (the literature and the 2025–26 press coverage).
2. The one LETF-specific result (within-stock overnight reversal) is statistically robust but
   economically ~1–2 bps at typical flows, and possibly a Yahoo-open artifact.
3. The strongest raw patterns (overnight rebound after big down days; afternoon momentum)
   belong to the *type of stock*: speculative retail/crypto/AI-infra names on theme-wide move days.

### Verdict against the pre-committed criteria
Magnitude — fails at typical flows. Concentration — fails (top-10 days dominate).
Net reversal by next close — absent. Recent data — the anticipation effect is decaying (2026 ≈ 0).
**The overnight-fade version of Strategy A does not pass on free data.** Remaining unexamined:
official open/close prints and actual imbalances (paid/IBKR), and the LETF's own price vs NAV
(handoff item 10), which is testable for free.

---

## 2026-09-23 — Item 10: the LETF's own closing price vs NAV (new candidate)

User direction: skip the imbalance recorder for now; test item 10; if it fails, propose a pivot.
Tests in this entry: ~16 (cumulative ~50). This candidate was motivated by mechanism (handoff item 10),
not found by sweeping, but it's still the ~40th+ thing looked at, so it needs the hold-out.

**Data.** Exact premium = ln(Yahoo close / NAV) for GraniteShares and ProShares funds (38 funds).
Proxy for all 240 attributable funds: e_t = ln(1+r_fund) − ln(1+L·r_und), i.e. the change in premium
plus fee/financing drift. Proxy vs exact ΔPremium correlation: **0.69**.
(Yahoo Close is not dividend-adjusted; LETF distribution days add noise, biasing reversion *down*.)

**Findings (in-sample, 2022-07 → 2026-03-19)**
1. Closing premiums are small and transient: median |premium| 9.5 bps, p90 30 bps; median AR(1) 0.09.
2. Big premiums revert almost fully the next day. Exact premium ≥25 bps → 37 bps reversion;
   ≥50 → 64; ≥100 → 125 (SEs 1–10 bps). Proxy slope of e_{t+1} on e_t: −0.22 overall, −0.39 on big-move days.
   Most events are in small funds (AUM < $50M: 76–92% of exact-premium events).
3. **Not stale prints:** loading of e_t on L·(underlying 15:30→close move) is only −0.03 even in the
   thinnest quartile (a stale print would load near −1). Reversion persists in the most liquid quartile
   (fund ADV ~$112M): 23 bps for |e| ≥ 50 bps.
4. **The dislocation forms in the closing process and is gone by next morning** (hourly split,
   `letf_premium_intraday.py`). For funds with ADV ≥ $20M:
   - the 15:30→close part of e_t reverts at slope −0.52 (t = −20);
   - the pre-15:30 part reverts at only −0.09;
   - 64% of the last-30-min part is gone by 10:30 on t+1.
   Events with |e| ≥ 50 bps: ~30% of the premium change forms after 15:30; reversion 25–31 bps,
   **all by 10:30 t+1**, nothing after.
5. **By listing venue:** Cboe BZX listings have 22% event rate and 37 bps reversion; NYSE Arca
   14% and 29 bps; Nasdaq 7% and 29 bps.
6. Rough P&L (`letf_premium_sim.py`):
   - rule: fade |e_t| ≥ k at the close with an L·underlying hedge, exit next close;
   - size: min($1M, 1% of fund ADV); cost 5–10 bps + 1 bp hedge;
   - result: net **+5 to +26 bps per event** depending on threshold, cost and universe;
     **$0.5–2M/yr in 2025**; daily Sharpe 1.5–4.6; top 10 days 22–74% of P&L (lower thresholds
     are less concentrated).

**Why this could be real.** It's the user's 2007 trade in a new, small venue:
- LETF closing auctions (especially Cboe BZX listings) are thin and absorb price-insensitive retail
  MOC and closing flow;
- fair value (NAV = L × the underlying's closing-auction price) is known exactly at 4:00;
- the size is too small for large firms, and the dislocation clears by the next morning.

**Why it may not be, in order of importance:**
1. **Executability.** Yahoo's close is the official closing price. For a thin ETF with no or small cross
   it may be a last sale or a tiny auction print. If the print is at the edge of a wide spread, the
   "reversion" is bid-ask bounce, which can't be captured. Everything above is consistent with close-price
   noise *or* with a real auction imbalance; only closing-auction prints/volumes and NBBO at 16:00
   distinguish them.
2. **Capacity.** LETF closing-auction volume is unknown. 1% of fund ADV is a guess, and for Cboe listings
   the closing auction may be much smaller.
3. **Entry timing.** The premium is only known after both auctions print. Live, you'd act on indicative
   prices (imbalance feeds for the LETF and the underlying) with limit or imbalance-only orders. Fill rates
   and adverse selection need modelling from imbalance data.
4. **NAV basis.** Funds holding options (e.g. MSTU in late 2024) or with swap resets off the close
   make NAV ≠ L × underlying intraday. Proxy noise, but also hedge basis risk.
5. **Multiple testing.** ~50 tests so far in total. Needs the hold-out once executability is settled.

**Proposed next steps (for this candidate):**
- (free) The 1-minute NBBO at 15:59–16:00 for a sample of LETFs from IBKR historical data (BID_ASK bars).
  This tells whether the closing premium exists at the *mid*, which separates bounce from real
  dislocation. Needs the user's IBKR session; I can write the script.
- (cheap/paid, ask first) Closing-cross prints and imbalance messages for LETF tickers: Nasdaq ITCH for
  Nasdaq listings, Cboe BZX auction feed for Cboe listings (Databento). Measures auction size and whether
  our limit orders would have filled.
- The live imbalance recorder (skipped for now) becomes directly relevant here: record LETF *and*
  underlying closing imbalances 15:50–16:00.

## 2026-09-23 — Item 4: fallback directions (proposal only, nothing built)

Item 10 did not fail, so these are held in reserve, ranked by fit with the core principle
(scheduled, price-insensitive, computable flow in a venue too small for big firms):
1. **Other thin ETF closing auctions against known NAV.** The same trade in non-leveraged niche ETFs:
   single-stock option-income (YieldMax et al.), buffer ETFs on reset days, crypto spot ETFs on big BTC
   days. Same data pipeline; natural extension if the LETF result holds up.
2. **Buffer/defined-outcome ETF reset days.** Monthly/quarterly resets roll large FLEX option
   positions on known dates. The flow is in index options, so we'd need options data (not free, and
   outside the IBKR equity setup).
3. **Smaller index reconstitutions** (S&P SmallCap 600 / MidCap 400 adds and deletes, CRSP, sector-fund
   rebalances). Known dates and names, closing-auction flow in small caps. Crowded at the Russell level,
   less so for smaller indexes. Needs historical constituent-change lists (partly free from press releases).
4. **Option-income ETFs' scheduled call writing** on single stocks. Pressure is in options, not the stock,
   so it fits our tools poorly.
