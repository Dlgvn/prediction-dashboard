# Phase 16: Sentiment Data Sufficiency & Causality Research - Context

**Gathered:** 2026-08-31
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase determines whether the `archive/` sentiment dataset has any measurable,
defensible relationship to the app's real forecast targets (HDAN, PPAN, Diesel-USD, FX
rate) — and produces a frozen, documented go/no-go report. It delivers a research
artifact only: no `app/` code changes, no UI, no runtime dependency changes. A "no-go"
result is a valid, complete outcome for this phase, not a failure to be avoided or
re-litigated. Satisfies SENT-01 and SENT-02.

</domain>

<decisions>
## Implementation Decisions

### Significance bar
- **D-01:** Use the same significance tiers as the existing `causality_screen.py`
  pipeline (p<0.05 = "p05", p<0.10 = "p10") — no stricter bar for sentiment predictors
  than for any other candidate predictor already in the codebase. Treat sentiment the
  same as any other predictor; let the small-N floor (D-04) do the work of filtering
  out spurious hits, not an inflated significance threshold.
- **D-02:** A predictor qualifies at its single best (lowest-p) lag — do not require the
  signal to hold across multiple lags (1/2/3). Matches `shortlist_for()`'s existing
  best-lag-per-predictor pattern.
- **D-03:** No directional/sign sanity check required. A qualifying p-value is
  sufficient regardless of whether the correlation sign is economically intuitive —
  matches the existing pipeline's D-04 "no intuition-based pre-filtering" precedent;
  don't let researcher judgment act as a second filter here that isn't applied anywhere
  else in the causality screen.

### Result granularity
- **D-04:** Go/no-go is reported **per series** (HDAN, PPAN, Diesel-USD, FX rate) —
  not one global answer. A go for one series (e.g. Diesel-USD via a macro-risk-proxy
  predictor) does not require or imply a go for the others. Diesel-MNT is explicitly
  out of scope for its own go/no-go row — it's a derived series (Diesel-USD × FX ×
  markup) per `forecasting.py`'s existing pattern; its eventual sentiment-adjustment
  status (if any) follows from Diesel-USD's and FX's results, not a separate test.

### Small-N floor
- **D-05:** Reuse `causality_screen.py`'s existing `MIN_GRANGER_N = 24` (monthly
  observations) as the floor for sentiment predictors too — one consistent bar across
  the whole pipeline, not a sentiment-specific number.
- **D-06:** When resampling daily sentiment to monthly, months with zero articles are
  **dropped** (excluded), not forward-filled or interpolated. This shrinks the
  effective N further but reflects the data's real sparsity honestly rather than
  manufacturing continuity that risks staleness/leakage (per PITFALLS.md finding #3).
- **D-07:** If a resampled monthly sentiment series doesn't clear `MIN_GRANGER_N` for a
  given target, that target gets an **immediate no-go** for that predictor — do not run
  the significance test at all. Matches `causality_screen.py`'s own existing
  "insufficient overlap" skip behavior. Given the archive's ~163 sentiment-days spread
  over ~6 years (91% clustered in the last ~5 months), this is expected to be the
  outcome for most or all target/predictor pairs — plan for the report to legitimately
  say "insufficient data" rather than forcing a p-value out of a degenerate sample.

### Candidate predictor set
- **D-08:** Test three feature families as candidate predictors, screened via the same
  no-pre-filtering discipline as `causality_screen.py`'s existing 12 predictors:
  1. Raw/weighted sentiment score (`weighted_compound`)
  2. Sentiment trend/momentum (`sent_ema3`, `sent_ema10`, `sent_momentum`)
  3. VIX-derived macro risk regime (`vix_regime`) — kept as a distinct candidate
     because it's a plausible macro-risk proxy for Diesel (Brent-linked) and FX (EM
     risk appetite) independent of literal headline sentiment about these commodities
- **D-09:** Exclude columns built for the archive's original equity-forecasting
  purpose — `rolling_corr_60d` (correlation vs. SPY) and the `spy/qqq/dia_return_next1d`
  ML target columns. These are diagnostic/target artifacts of the dataset's original
  scope, not defensible candidate inputs for HDAN/PPAN/Diesel/FX.

### Claude's Discretion
- Exact resampling method for turning daily sentiment into a monthly value (e.g. mean
  vs. median of the non-dropped daily observations within a month) — not discussed;
  pick the standard approach (mean) and note the choice in the phase's research output.
- Report file naming/location and JSON result-artifact structure — follow the existing
  `backend_research/` convention (a new `REPORT-SENTIMENT.md` and
  `results/sentiment_causality_screen.json`, mirroring `causality_screen.json`'s shape)
  rather than inventing a new structure.
- Timezone handling for the daily-to-monthly resample (UTC `published_at` vs. Mongolia
  local, UTC+8) — not explicitly discussed as a user decision; implement per
  PITFALLS.md's guidance (extend `walk_forward.py`'s existing `LeakageError` guard
  rather than a parallel merge path) since this is a correctness detail, not a product
  choice.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Research (this milestone)
- `.planning/research/SUMMARY.md` — synthesized v2.0 milestone research; the critical
  domain-mismatch/sparsity finding and recommended build order live here
- `.planning/research/STACK.md` — confirms no new core dependencies needed; documents
  the archive data's actual row counts/date-range sparsity
- `.planning/research/ARCHITECTURE.md` — recommends this phase live under
  `backend_research/sentiment/`, reusing `walk_forward.py`'s harness, zero `app/`
  changes
- `.planning/research/PITFALLS.md` — the 5 critical pitfalls this phase must guard
  against (domain mismatch, small-N illusion, look-ahead/timezone leakage, correlation-
  vs-predictive-signal conflation, band destabilization — the last is Phase 18's concern)
- `.planning/research/FEATURES.md` — MVP gating: no sentiment UI work starts until this
  phase returns a result

### Project-level
- `.planning/PROJECT.md` — v2.0 milestone goal, Key Decisions table (archive-data-as-
  starting-point decision, weekly-research-is-a-spike precedent this phase mirrors)
- `.planning/REQUIREMENTS.md` — SENT-01/SENT-02 requirement text (this phase's exact
  scope), SENT-03..08 (Phase 18's conditional scope, useful for knowing what a "go"
  result needs to support downstream)
- `.planning/ROADMAP.md` Phase 16 entry — success criteria this phase must satisfy

### Existing codebase (reuse, don't reinvent)
- `backend_research/causality_screen.py` — the exact Granger F-test + tier (p05/p10)
  + `MIN_GRANGER_N` pattern this phase extends to sentiment predictors
- `backend_research/walk_forward.py` — `LeakageError` guard to extend for the daily-to-
  monthly sentiment merge, per D-07's timezone/leakage note
- `backend_research/db_loader.py` — existing `TARGETS`/`PREDICTORS` constants and
  `load_price_history()`/`pct_change_frame()` loaders this phase's target-side data
  should reuse rather than re-implementing
- `backend_research/REPORT.md` — existing report-writing convention/format to mirror
  for the new sentiment go/no-go report

### Data sources
- `archive/README.md` — archive dataset's stated original purpose (context for why the
  domain-mismatch finding exists)
- `archive/news_sentiment_daily.csv` — daily `weighted_compound`, `article_count`
- `archive/ml_features.csv` — `sent_ema3`, `sent_ema10`, `sent_momentum`, `vix_regime`,
  `rolling_corr_60d` (excluded per D-09), equity return targets (excluded per D-09)
- `archive/sentiment_market_panel.csv` — merged sentiment/market panel, useful for
  cross-checking column definitions against `ml_features.csv`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `causality_screen.py::granger_ftest()` — the exact incremental F-test implementation
  to reuse verbatim for sentiment predictors, not reimplement
- `causality_screen.py::_tier()` / `MIN_GRANGER_N` — the tiering and floor logic this
  phase's screen should call directly (or a thin sentiment-specific wrapper around it)
- `walk_forward.py::LeakageError` — the leakage-guard exception class to raise from the
  new daily-to-monthly sentiment merge on any train/forecast boundary violation

### Established Patterns
- Research artifacts live in `backend_research/results/*.json` (frozen, checked-in) plus
  a human-readable `REPORT*.md` — this phase should produce
  `backend_research/results/sentiment_causality_screen.json` and
  `backend_research/REPORT-SENTIMENT.md` following that exact pattern
- "No un-backtested model ships" / "no intuition-based pre-filtering" (D-04 precedent
  from Phase 2) — this phase's screen must test all three candidate feature families
  (D-08) without hand-picking which ones "seem more likely" to matter

### Integration Points
- None into `app/` this phase — the phase is fully contained in `backend_research/`.
  Phase 18 (conditional, future) is the only consumer of this phase's frozen go/no-go
  result.

</code_context>

<specifics>
## Specific Ideas

No specific UI/visual references — this is a research-only phase. The one concrete
methodological choice from discussion: prefer the existing pipeline's exact tier system
and floor (D-01, D-05) over inventing sentiment-specific thresholds, treating "the data
can't clear the bar every other predictor must clear" as itself the answer rather than a
problem to work around.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Weekly-mode UI, sentiment UI differentiators,
and live news API integration were already scoped out of this milestone during
requirements definition; not re-raised here.)

</deferred>

---

*Phase: 16-Sentiment Data Sufficiency & Causality Research*
*Context gathered: 2026-08-31*
