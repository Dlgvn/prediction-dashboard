# Pitfalls Research

**Domain:** Adding a news/sentiment scenario-adjustment layer + weekly-forecast re-research spike to an already-shipped Reflex forecasting dashboard
**Researched:** 2026-08-31
**Confidence:** HIGH (grounded in direct inspection of `archive/*.csv`, `backend_research/REPORT.md`, and the prior `20260821-weekly-an-backtest` quick-task result — not generic ML folklore)

## Critical Pitfalls

### Pitfall 1: The `archive/` sentiment dataset was built for a different prediction problem entirely

**What goes wrong:**
The team treats `archive/` as "pre-prepared sentiment data for this project" and wires it into the forecast without re-checking what it actually measures. Direct inspection shows `sentiment_market_panel.csv` and `ml_features.csv` were built to predict **next-day SPY/QQQ/DIA returns** from **VADER sentiment on general NewsAPI financial headlines** (`spy_return_next1d`, `spy_up_next1d` are the literal regression/classification targets — see header row). Nothing in the pipeline references ammonium nitrate, diesel, Brent, or USD/MNT. `rolling_corr_60d` in the panel is the correlation between sentiment and **SPY**, not any series this app forecasts. Separately, `News_Category_Dataset_v3.json` (87MB) is the well-known Kaggle "News Category Dataset" — general HuffPost topic-classification data (POLITICS/COMEDY/WELLNESS/etc., confirmed by sampling), not finance or commodity news, and its date coverage (2012–2022 per its known provenance; confirmed 2020–2022 in a 5k-row sample) doesn't even overlap the live 2026 forecasting window.
**Why it happens:** The file names ("news_sentiment", "market_panel") sound domain-relevant, and PROJECT.md's Key Decisions table already states the milestone "builds on the existing `archive/` dataset ... rather than researching a provider from scratch" — creating pressure to treat the data as fit-for-purpose without re-verifying the fit.
**How to avoid:** Before any backtest work, explicitly document what target variable each archive file was built for, and run a fresh Granger-causality/correlation screen (mirroring `backend_research/causality_screen.py`'s existing pattern) between the sentiment aggregates (`weighted_compound`, `sent_ema10`, `sent_momentum`) and each of the app's actual four series (HDAN, PPAN, Diesel-USD, FX_rate) at monthly resample — not equities. Treat "general market sentiment might carry macro risk-appetite signal relevant to Brent-linked Diesel or risk-off FX moves" as an unproven hypothesis to test, not a given. Exclude `News_Category_Dataset_v3.json` from the pipeline entirely unless a concrete use for it (e.g., training a topic classifier) is identified — it has no date overlap with current forecasting needs and no finance labeling.
**Warning signs:** Any backtest script that merges archive columns onto price data using date-join alone, without a documented causality/correlation check against the *actual* target series; any PR description that says "sentiment score" without stating what it was validated against.
**Phase to address:** Backtest/leakage-check phase (before any UI work) — this is a go/no-go gate, same posture as the Phase 2 model-research process already used for VAR/SARIMAX.

---

### Pitfall 2: Sparse historical coverage makes any sentiment backtest a small-N illusion

**What goes wrong:**
`news_sentiment_daily.csv` has only 164 rows total, but they are wildly non-uniform: 1–4 rows per year from 2020–2025 (mostly single-headline days, `article_count=1`), then 148 rows concentrated in the last ~5 months (Mar–Aug 2026) — a direct artifact of NewsAPI's free-tier 28-day lookback window (confirmed in `archive/README.md`: "last 28 days per run"). Any monthly-resampled merge against the ~44-month HDAN/PPAN/Diesel/FX price history will have real (dense, multi-article) sentiment coverage for only ~5 of those months. A backtest run naively against this will effectively be "trained and tested" on a handful of overlapping months, then padded with statistically meaningless single-headline outliers from unrelated years.
**Why it happens:** The daily/panel/ml_features CSVs *look* like a continuous 6-year time series (2020–2026 date range spans years), which invites treating row count or date range as a proxy for sample size, when the effective sample size for anything resampled to monthly cadence is much smaller.
**How to avoid:** Report effective monthly sample size explicitly (months with ≥N articles of coverage) before running any backtest, and apply the same small-sample discipline the project already established in Phase 2 (`MIN_ML_ORIGINS=5` thin-sample exclusion, `suspiciously_strong/small_sample` flags in `02-07-PLAN.md`'s findings). If effective N is too small to run genuine walk-forward validation, say so explicitly and do not ship an adjustment based on it — this is the same "no un-backtested model ships" rule PROJECT.md already states.
**Warning signs:** A backtest report that cites row counts from the CSV files (164, 119, 117) as if they were monthly sample sizes; "the sentiment-adjusted band looks better" conclusions drawn from fewer than ~12 genuinely independent monthly observations.
**Phase to address:** Backtest/leakage-check phase.

---

### Pitfall 3: Look-ahead bias in the date-join between daily sentiment and monthly price entries

**What goes wrong:**
Merging a daily/rolling sentiment feature onto a monthly price observation is a classic leakage point. Two concrete mechanisms exist in this data specifically: (1) `news_sentiment_raw.csv`'s `published_at` is UTC; Mongolia is UTC+8, so a headline timestamped late UTC-day is already the next local day — matching by the raw `date` column without a timezone-aware cutoff can pull in "tomorrow's" news for "today's" forecast origin. (2) Several `ml_features.csv`/`sentiment_market_panel.csv` columns (`sent_quantile_60d`, `rolling_corr_60d`, `*_rolling_mean_5/10/20d`) are windowed statistics — if the resample-to-monthly step naively averages a whole calendar month's sentiment (including days after the user's actual forecast-origin/data-entry date) into "this month's sentiment," the adjustment is trained on information that wouldn't have existed at forecast time.
**Why it happens:** Point-in-time correctness across cadence mismatches (daily sentiment vs. monthly price entries, entered by the user at an irregular, "roughly monthly" cadence — not always month-end) is easy to get right for the *price* series (already solved via `backend_research/walk_forward.py`'s rolling-origin harness) but easy to re-break when a new, differently-cadenced feature is bolted on, because it requires its own cutoff logic rather than reusing the existing harness unmodified.
**How to avoid:** Reuse `backend_research/walk_forward.py`'s existing rolling-origin harness (already has a `LeakageError` per STATE.md's Phase 02-01 decision) and extend it — do not write a parallel, separate merge path for sentiment. Define the sentiment cutoff as "all articles published strictly before the forecast-origin date, converted to the same reference timezone as price entry," and unit-test it the same way `test_walk_forward.py` already tests leakage.
**Warning signs:** A new sentiment-merge function that doesn't import or extend `walk_forward.py`; any pandas `resample('M').mean()` call on sentiment without an explicit as-of cutoff parameter.
**Phase to address:** Backtest/leakage-check phase.

---

### Pitfall 4: Correlation-with-equities conflated with predictive signal for commodities/FX

**What goes wrong:**
The archive dataset's own internal validation (`rolling_corr_60d`) measures correlation between sentiment and *SPY*, and even for its intended purpose, correlation ≠ next-day prediction (could be contemporaneous, not lead-lag). If this correlation is cited as evidence sentiment "works" and then applied to HDAN/PPAN/Diesel/FX without its own out-of-sample backtest, that's conflating a different domain's correlation with this domain's predictive validity. Compounding this: the project's own existing research already found FX_rate shows **no significant relationship (p<0.10) with any other series in the causality matrix**, including Brent-linked drivers (`backend_research/REPORT.md`, "Cross-series causality" section) — a strong prior that a generic equity-sentiment score is unlikely to move FX_rate either, and any backtest result suggesting otherwise deserves extra scrutiny before being trusted.
**Why it happens:** "The dataset shows sentiment correlates with market moves" is an easy, plausible-sounding justification to reach for once the data is already loaded, especially under time pressure to ship a "provenance" story for the UI.
**How to avoid:** Require the same walk-forward, held-out MAPE/coverage comparison used for every other model family in this project (Phase 2 precedent) before any sentiment adjustment ships — "with sentiment" vs. "without sentiment" on the actual target series, not a borrowed equities correlation number.
**Warning signs:** A PR or research note that cites `rolling_corr_60d` or any SPY-related metric as justification for shipping the AN/Diesel/FX adjustment.
**Phase to address:** Backtest/leakage-check phase.

---

### Pitfall 5: Sentiment adjustment silently destabilizes an already-calibrated, backtested bull/bear spread

**What goes wrong:**
The existing bull/bear bands are a validated, backtested statistical spread (per-series MAPE/volatility, e.g. HDAN SARIMAX 13.33% MAPE, PPAN Direct-OLS VAR-system 23.8% MAPE per `.planning/STATE.md`'s Phase 02-07 decision). Sentiment scores in this dataset are noisy and occasionally extreme (single-headline days with `compound` as low as −0.94), and if the sentiment layer is applied as a direct multiplier/additive shift on the band without bounds, one volatile-news day can blow the band far outside anything the backtest calibrated for — undermining the very thing PROJECT.md says v1's bands already got right ("bull/bear = base ± a statistical spread ... not a fixed band").
**Why it happens:** It's tempting to implement "sentiment adjustment" as a simple UI-layer scalar (e.g., `band_width *= (1 + k * sentiment_score)`) because it's easy to code and demo, without re-validating that the *combined* (statistical spread + sentiment) band is still well-calibrated (e.g., empirical coverage — how often the actual price falls inside the band — no worse than the unadjusted spread).
**How to avoid:** Clip/cap sentiment's influence (e.g., a bounded multiplier, not an unbounded raw score pass-through), and explicitly backtest empirical coverage of the *combined* band against the unadjusted band's coverage — the adjustment should not be shipped if it makes the calibrated spread worse. Treat this as a new model requiring the same research/backtest gate as any other model family in this project, not a UI tweak exempt from that discipline (this is the specific way PROJECT.md's "no un-backtested model ships" rule could get silently bypassed — by relabeling a model as "just an adjustment").
**Warning signs:** Sentiment-adjustment code that lives entirely in `rx.State`/UI code with no corresponding research/backtest artifact; a demo where one bad-news day makes the band visually much wider than any prior month without a stated cap.
**Phase to address:** Backtest/leakage-check phase (methodology + cap), then UI phase (wire in the already-validated, bounded adjustment).

---

### Pitfall 6: "Live" sentiment provenance misleads a single-user, monthly-cadence app

**What goes wrong:**
PROJECT.md's target feature explicitly wants "provenance (what's driving the adjustment) shown to the user." But this app is used by one person, roughly monthly (per STACK.md/PROJECT.md's stated usage pattern), with no background job scheduler (single Reflex process, no Celery/cron). If the sentiment score is fetched once and cached, then shown weeks later as if current, the user could make a procurement decision believing the adjustment reflects "today's news" when it's stale. Separately, NewsAPI's free tier only returns the **trailing 28 days** — there is no way to backfill sentiment for a gap month if the user skips a session, so a returning user's "provenance" display could silently have a hole (or worse, silently reuse the last cached score without flagging it as stale).
**Why it happens:** "News/live-driven" framing in the milestone goal implies real-time freshness, but the app's actual usage cadence and architecture (single-process, occasional use, no scheduler) can't genuinely deliver that without extra plumbing that wasn't scoped.
**How to avoid:** Show an explicit "sentiment as of [fetch date]" timestamp next to the adjustment (not just "live news says..."), and fetch fresh on each session load rather than caching indefinitely, given the low usage frequency makes per-session fetch cheap. Document explicitly that the trailing-28-day NewsAPI limitation means gaps longer than 28 days between sessions cannot be backfilled — degrade gracefully (fall back to unadjusted statistical spread with a visible note) rather than silently reusing a stale score.
**Warning signs:** No timestamp visible next to the sentiment-driven scenario; a code path that reuses a cached sentiment value with no expiry/staleness check.
**Phase to address:** UI/provenance phase.

---

### Pitfall 7: Re-running the same weekly VAR family with the same proxy inputs reproduces the same no-go

**What goes wrong:**
The prior spike (`.planning/quick/20260821-weekly-an-backtest/SUMMARY.md`) already found weekly-native VAR underperforms monthly VAR at the horizon-matched comparison (10.35%/16.01% vs. 9.49%/10.08% MAPE), and diagnosed *why*: the one-step weekly model's R² was only 0.03–0.04, meaning almost all of its apparent accuracy was persistence/naive, not real signal from the weekly driver variables (Middle East Ammonia, Black Sea/China Urea, gas benchmarks — proxies, not HDAN/PPAN's actual Mongolian domestic price drivers). If the v2.0 re-research spike re-fits VAR (or another autoregressive family) on the *same* proxy variables, it will very likely reproduce the same low-R² result, wasting the spike's budget without genuinely testing a new hypothesis.
**Why it happens:** VAR is the project's known-good model family for the monthly case (it's the Phase 2 winner shape for HDAN), so there's a natural pull toward "try VAR again but weekly" as the default first move, without first asking whether the *input variables* — not the model family — were the actual bottleneck.
**How to avoid:** Before refitting any model, run the equivalent of `backend_research/causality_screen.py` against candidate new weekly variables to check they actually lead/explain HDAN/PPAN at weekly granularity (not just correlate) — this project already has that harness; reuse it rather than jumping straight to VAR. Treat "same model family, different data" and "different model family, same data" as two genuinely different experiments, and don't call the spike complete unless at least the *data/variable* side has changed meaningfully from what the prior spike already ruled out.
**Warning signs:** A new backtest script that imports the same `load_weekly_drivers()` predictor set from the prior spike unchanged; a re-research summary whose R² is still in the 0.03–0.06 range without commentary on why that's different this time.
**Phase to address:** Weekly re-research spike phase (design step, before any backtest run).

---

### Pitfall 8: False confidence from a non-comparable backtest window or horizon

**What goes wrong:**
The prior weekly spike used a horizon-matched comparison (rolled 4-week-ahead weekly forecasts up against the monthly benchmark) specifically so the MAPE numbers were apples-to-apples. A re-attempt that evaluates 1-week-ahead weekly MAPE against the 1-month-ahead monthly benchmark (9.49%/10.08%), or that uses a single train/test split instead of the existing walk-forward harness (`walk_forward.py`, `run_var_vecm_wf.py`), can produce a misleadingly good number that doesn't reflect genuine improvement — especially since only ~5 more months of weekly data exist now (this spike is ~1.5 weeks after the prior one, per dates) than when the prior no-go was recorded, so there isn't much genuinely new data to shift the conclusion on its own.
**Why it happens:** A smaller, more favorable-looking MAPE is an easy thing to declare victory on, especially under pressure to "unblock" a deferred feature; horizon mismatches and window-selection effects are subtle and easy to miss without deliberately cross-checking against the prior report's exact methodology.
**How to avoid:** Any new weekly backtest must use the same walk-forward, horizon-matched methodology as the prior spike (same rollup-to-4-weeks-ahead comparison) so results are directly comparable to the existing 9.49%/10.08% monthly benchmark recorded in `.planning/STATE.md`. If the new spike's data window barely differs from the prior one (same source files, few extra weeks), say so explicitly rather than implying a fresh, independent result.
**Warning signs:** A new report whose comparison table doesn't cite the prior spike's exact MAPE figures side-by-side; use of a single fixed holdout instead of rolling-origin validation.
**Phase to address:** Weekly re-research spike phase.

---

### Pitfall 9: Partial weekly coverage creates an inconsistent, confusing UI if only some series clear the bar

**What goes wrong:**
No weekly Diesel/FX data exists at all (confirmed unchanged in both PROJECT.md and STATE.md), so even in the best case, only HDAN/PPAN could ever get weekly mode — Diesel-MNT (a derived series requiring both Diesel-USD *and* FX) can never be weekly-native. The existing UI was built around one global horizon/granularity picker across all four series simultaneously (per Phase 5's "Forecast UI, Scenario Chart" and the single `forecast_results` dict keyed by all series). If a future phase ships weekly mode for HDAN/PPAN only, naively reusing the current single-toggle UI would either (a) force Diesel/FX to silently stay monthly while the chart x-axis/labels imply weekly for everything, or (b) block weekly mode entirely behind "all series must support it," wasting a validated win on 2 of 4 series.
**Why it happens:** The existing granularity/horizon selector is a single global control by design (simpler UI, matches the current all-monthly reality) — extending it to a mixed-granularity world isn't a natural fallout of the current component structure and is easy to bolt on incorrectly under time pressure.
**How to avoid:** If any series clears the new backtest bar, design the granularity toggle as per-series-aware from the start (e.g., disable/gray weekly for Diesel/FX with an explicit "weekly data unavailable for this series" label, rather than silently degrading), and treat this as a UI/UX design decision requiring its own explicit spec — not an afterthought bolted onto the existing single-toggle component. This should only be built at all if the backtest bar is actually cleared (per Pitfall 7/8) — don't build the mixed-granularity UI speculatively ahead of a validated result.
**Warning signs:** A UI mock or implementation that has one horizon dropdown silently changing behavior per-series without a visible label explaining why; Diesel-MNT chart lines that jump or look stale in weekly mode without explanation.
**Phase to address:** UI phase (conditional — only if weekly re-research spike returns a go).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|--------------------|-----------------|------------------|
| Wiring `archive/` sentiment columns straight into a UI adjustment without a causality/backtest gate | Fast demo of "provenance" UI | Violates the project's own "no un-backtested model ships" rule; risks shipping noise as signal on a domain-mismatched dataset | Never |
| Caching a single sentiment fetch indefinitely to avoid NewsAPI rate limits | Simple, no API-key management complexity | Silently stale "live" provenance shown to the user across sessions weeks apart | Only with an explicit staleness timestamp and a visible "last fetched" label — never silent |
| Re-running the exact prior weekly VAR script with a slightly longer date range and calling it "re-research" | Cheap, fast to execute | Reproduces the already-diagnosed low-R² no-go, burns spike budget with no new information | Never — the milestone explicitly frames this as re-research, not a rerun |
| Treating the 87MB `News_Category_Dataset_v3.json` as in-scope just because it's in `archive/` | Avoids a scoping conversation | Wastes engineering time trying to extract signal from a topically and temporally irrelevant dataset | Never, unless a concrete distinct use (e.g. training a separate classifier) is identified first |
| Single train/test split for the weekly spike instead of reusing `walk_forward.py` | Faster to write | Not comparable to the existing walk-forward-validated 9.49%/10.08% benchmark; risk of a falsely favorable number | Never for the go/no-go decision itself; fine only for very early, throwaway exploration clearly labeled as such |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|-----------------|-------------------|
| NewsAPI (via `archive/README.md`'s documented free-tier limits) | Assuming historical backfill is available for any gap in the user's usage cadence | Free tier only returns the trailing 28 days; design the feature to degrade gracefully (visible "unavailable" state) for older gaps rather than assuming continuous coverage |
| VADER sentiment scoring | Treating `compound` score magnitude as meaningful signal strength rather than a rough sentiment polarity heuristic | Use it as one weak input among several (article volume, source weighting, momentum), not a standalone predictive feature — and validate against the actual target series, not just report it |
| Timezone handling between `published_at` (UTC) and Mongolia-local price-entry dates | Naive string-date join across the two, causing off-by-one-day leakage at merge boundaries | Convert explicitly to a consistent reference timezone with a documented as-of cutoff before merging, and unit-test the boundary case |
| Reusing `backend_research/walk_forward.py` for a new, differently-cadenced feature (daily sentiment vs. monthly price) | Writing a parallel, ad hoc merge/backtest path that doesn't inherit the existing `LeakageError` guard | Extend the existing harness rather than duplicating merge logic outside it |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Loading the 87MB `News_Category_Dataset_v3.json` into memory in a single-process Reflex app "just in case" | Slow app startup, memory bloat on a single-user local deployment | Don't load it at all unless a concrete, scoped use is defined (see Pitfall 1) | Immediately noticeable on a modest local machine given the app's single-process, no-worker architecture |
| Re-fetching/re-scoring sentiment on every page load without caching *within* a session | Redundant NewsAPI calls, possible rate-limit exhaustion during dev/testing | Cache within a session, refresh only on new session/explicit refresh, with a visible timestamp (ties to Pitfall 6) | Noticeable once NewsAPI daily quota is hit during iterative development/testing |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Hardcoding a NewsAPI (or equivalent) API key in source rather than environment config | Key leakage if the repo is ever shared/pushed publicly | Load from environment/`.env` (already how the project should be handling any external credentials — confirm no key lands in a committed file) |
| Rendering raw article titles/URLs from `news_sentiment_raw.csv` (or a live fetch) directly into the UI without sanitization | XSS if headline text ever contains unexpected markup (low risk with Reflex's default escaping, but worth confirming for any `rx.html`/raw-HTML usage) | Stick to Reflex's default text rendering (auto-escaped); avoid `dangerously_set_inner_html`-style patterns for headline text |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| Showing a sentiment-driven adjustment with no explanation of *what* news domain it's drawn from (general financial/equity headlines, not AN/diesel/Mongolia-specific) | User may over-trust an adjustment that has no demonstrated connection to their actual commodities, undermining the "provenance" feature's whole purpose | Explicitly label the sentiment source and scope in the UI ("general market sentiment, not commodity-specific") so the user can calibrate trust appropriately |
| Sentiment adjustment silently shifting the bull/bear band with no visible delta vs. the pre-sentiment statistical band | User can't tell whether/how much the adjustment mattered, undermining trust and debuggability | Show both the base statistical band and the sentiment-adjusted band (or at least a clear "+/− X% from sentiment" delta), consistent with the project's existing "model provenance" display precedent (Phase 13) |
| Weekly mode available for only 2 of 4 series with no visual distinction | User assumes weekly mode "just works" for everything and gets confused by stale/mismatched Diesel-MNT figures | Per-series-aware granularity control with explicit unavailability messaging (see Pitfall 9) |

## "Looks Done But Isn't" Checklist

- [ ] **Sentiment backtest:** Often missing a genuine causality/correlation check against the *actual* target series (HDAN/PPAN/Diesel/FX) rather than the archive's own SPY-focused validation — verify a fresh Granger/correlation screen was run against this project's series specifically.
- [ ] **Sentiment backtest:** Often missing an explicit statement of effective monthly sample size (not raw CSV row count) — verify the report states how many months had real (multi-article) sentiment coverage.
- [ ] **Sentiment leakage check:** Often missing a timezone-aware, as-of cutoff in the daily-to-monthly merge — verify the merge logic (not just the model) was unit-tested for leakage, reusing `walk_forward.py`'s existing guard.
- [ ] **Sentiment UI:** Often missing a visible "as of [date]" timestamp on the sentiment-driven adjustment — verify staleness is never silently hidden from the user.
- [ ] **Sentiment band calibration:** Often missing an empirical coverage check ("combined band still contains the actual price at least as often as the unadjusted band") — verify this was backtested, not just eyeballed.
- [ ] **Weekly spike:** Often missing a side-by-side comparison table against the prior spike's exact figures (9.49%/10.08% monthly, 10.35%/16.01% prior weekly) — verify the new report cites and compares against these, not just its own numbers in isolation.
- [ ] **Weekly spike:** Often missing confirmation that walk-forward (not a single split) validation was used — verify the harness matches the prior spike's methodology.
- [ ] **Weekly UI (if shipped):** Often missing explicit per-series unavailability messaging for Diesel/FX — verify the UI never silently shows monthly data under a "weekly" label.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|-----------------|------------------|
| Sentiment adjustment shipped without a real backtest, later found to be noise-driven | MEDIUM | Feature-flag/disable the sentiment layer, fall back to the existing pure-statistical band (already validated), then run the proper backtest before re-enabling — the existing bands are unaffected since the adjustment should be additive/layered, not a replacement |
| Weekly mode shipped on a re-attempt that turns out to reuse the same flawed proxy variables (silent repeat of the no-go) | LOW–MEDIUM | Revert to monthly-only mode (prior, already-shipped behavior); re-run the spike with genuinely different candidate variables, using `causality_screen.py` first this time |
| Discover mid-development that `News_Category_Dataset_v3.json` was accidentally load-bearing in a pipeline | LOW | Since it has no demonstrated connection to any shipped feature per this research, remove the dependency and re-verify the pipeline still produces the same output — should be a no-op if unused as expected |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|--------------------|----------------|
| 1. Domain-mismatched sentiment data | Backtest/leakage-check phase | Written causality/correlation screen against HDAN/PPAN/Diesel/FX (not SPY) exists before any UI work starts |
| 2. Small-N illusion from sparse coverage | Backtest/leakage-check phase | Report states effective monthly sample size and applies the project's existing thin-sample exclusion rule |
| 3. Look-ahead bias in daily→monthly merge | Backtest/leakage-check phase | Merge logic extends `walk_forward.py`; leakage unit test exists for the sentiment merge specifically |
| 4. Correlation/predictive-signal conflation | Backtest/leakage-check phase | Backtest report compares "with sentiment" vs "without" on the target series' own MAPE/coverage, not a borrowed SPY correlation |
| 5. Sentiment destabilizing the calibrated spread | Backtest/leakage-check phase, then UI phase | Empirical coverage of combined band backtested and bounded/capped before UI wiring |
| 6. Stale "live" provenance | UI/provenance phase | Visible as-of timestamp and graceful degradation on >28-day gaps confirmed in a live browser check |
| 7. Repeating the same failed weekly model family | Weekly re-research spike phase (design step) | Spike design doc names what's *actually* different (variables, not just model family) vs. the prior no-go before any backtest is run |
| 8. Non-comparable backtest window/horizon | Weekly re-research spike phase | New report's comparison table cites the prior spike's exact figures side-by-side, using the same walk-forward/horizon-matched methodology |
| 9. Partial-coverage UI inconsistency | UI phase (conditional on a go decision) | Per-series granularity control with explicit unavailability messaging, human-verified in browser, only built if the backtest bar was actually cleared |

## Sources

- Direct inspection of `archive/README.md`, `archive/news_sentiment_daily.csv`, `archive/sentiment_market_panel.csv`, `archive/ml_features.csv`, `archive/market_prices.csv`, `archive/news_sentiment_raw.csv`, `archive/News_Category_Dataset_v3.json` (this session, 2026-08-31) — HIGH confidence, primary source
- `backend_research/REPORT.md` ("Cross-series causality" section — FX_rate shows no significant relationship with any driver) — HIGH confidence, project's own prior research
- `.planning/quick/20260821-weekly-an-backtest/SUMMARY.md` (prior weekly VAR no-go result and its diagnosed root cause) — HIGH confidence, project's own prior research
- `.planning/STATE.md` (Phase 02-07 model winners, MIN_ML_ORIGINS/suspiciously_strong small-sample precedent, weekly-mode blocker note) — HIGH confidence, project's own decision record
- `.planning/PROJECT.md` (v2.0 milestone scope, "no un-backtested model ships" constraint, "single local user, roughly monthly use" pattern) — HIGH confidence, project's own scope document
- General knowledge that the NewsAPI free tier restricts historical article access to a trailing ~28-30 day window, and that the "News Category Dataset" (Kaggle, Rishabh Misra) is a general HuffPost topic-classification corpus spanning roughly 2012–2022 — MEDIUM confidence (training-data knowledge, consistent with and corroborated by the in-repo `archive/README.md` wording and the sampled JSON contents, but not independently re-verified against NewsAPI's current live terms/pricing page in this session)

---
*Pitfalls research for: Sentiment scenario-adjustment layer + weekly-forecast re-research spike (Prediction Dashboard v2.0)*
*Researched: 2026-08-31*
