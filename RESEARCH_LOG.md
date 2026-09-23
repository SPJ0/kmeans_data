# Research Log — Auction-Flow Strategies

Newest entries at the bottom. Each entry: what was tried, why, result, what was learned.
Variant counter (for multiple-testing discount): **0 outcome-bearing tests run so far.**

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
- **Market context figures** ($50B/day record, 600+ funds, $41–42B AUM, >$2B MSTR days):
  see verification table. My own training data ends before mid-2026, so I can't confirm the
  2026 numbers from memory.
- **Flow math**: correct. Verified algebraically and in unit tests (`tests/test_rebalance.py`).
  One addition: L=1.25 and 1.5 funds have tiny multipliers (0.31, 0.75), so they barely
  matter. L=1.75 (1.31) matters for MSTX's history.

### Proposed changes to the plan

1. Make the **within-stock launch/AUM-growth design** the primary test of "beyond generic
   reversal." Keep matched placebos as secondary.
2. Add **index-LETF flow allocated by index weight** as a flow component for constituents.
3. Treat **"momentum into the close"** as a co-equal hypothesis, not a fallback. The
   event study runs first, before any P&L sim.
4. Start the **cheap live recorders now** (IBKR closing imbalance 3:50–4:00, daily issuer
   holdings/AUM archive). The historical free data is thin and the sweet-spot names are
   young, so every day of real E and real imbalance collected now is worth more than any
   backfill.
5. Budget flag: a clean answer probably needs **official auction prints and imbalance history**
   (Databento). I won't spend without asking, but I expect to ask after the free-data baseline.

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
