# Phase 2: Model Research & Backtesting - Context

**Gathered:** 2026-08-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Forecasting models for HDAN, PPAN, Diesel-USD, and FX rate are selected through a
research/backtest process against the full seeded history (164 monthly rows,
2013-01 through 2026-08, from Phase 1) — no un-backtested model reaches the shipped
forecasting module (FCST-07). This phase produces a research report naming the
winning model per series with backtested error, plus a horizon-strategy decision
(iterative vs. direct multi-step) per series. It does NOT implement the forecasting
module itself (that's Phase 3) and does NOT investigate weekly-mode forecasting.

</domain>

<decisions>
## Implementation Decisions

### Method scope
- **D-01:** Test methods from three families, chosen deliberately over the user's
  full taxonomy (naive, technical/market-based, and Delphi/scenario-planning were
  considered and excluded from this phase — see below):
  - **Time-series (statistical):** Naive/moving-average as the baseline every other
    model must beat, Exponential Smoothing (SES, Holt-Winters), ARIMA, and GARCH
    (for volatility/uncertainty — feeds Phase 3's bull/bear spread, not just the
    point forecast).
  - **Causal/econometric:** Regression, VAR, plus Granger-causality and
    cointegration tests — used to decide which predictors actually earn a place in
    a model rather than being included by intuition (see D-02/D-03).
  - **Machine learning:** Random forest and gradient boosting, included as a
    comparison point despite real overfitting risk on ~48-164 monthly rows per
    series — the research report should explicitly flag this risk when reporting
    ML results, not present them at face value against the simpler models.
- **D-02 (scope exclusion):** Technical/market-based methods (momentum,
  support/resistance) are NOT tested this phase — user did not select this family;
  it's a poorer fit for monthly fundamentals-driven commodity data than for
  intraday trading.
- **D-03 (scope exclusion, important):** Scenario planning / Delphi-style
  qualitative judgment is explicitly OUT of Phase 2's scope. It isn't
  backtestable against history the way the other methods are. **This is the
  mechanism REQUIREMENTS.md already reserves for v2's live news/sentiment-driven
  bull/bear adjustment** — Phase 2's research report should note this connection
  explicitly (so Phase 3/v2 planners see the throughline) but Phase 2 does not
  build or test anything for it.

### Predictor candidates
- **D-04:** For HDAN and PPAN: test the full predictor set from Phase 1's schema
  (Baltic AN, Ammonia, both Urea series, all 4 natural gas benchmarks, Brent,
  both Corn series, plus each product's own lagged values and the other AN
  product's lagged value for VAR). Do not pre-filter by intuition — run Granger
  causality across the whole set and let the data decide which predictors earn a
  place, same rigor as the original `backend_research/causality_matrix.py`.
- **D-05:** For Diesel-USD and FX rate: test Brent AND Urals (two crude
  benchmarks now available, vs. the original Excel workbook's Brent-only), plus
  natural gas and the full AN-family series as candidate predictors — broader
  search than the existing workbook's Diesel-on-Brent-lag-2 approach, even
  though there's no obvious economic mechanism for AN-family series to predict
  diesel/FX. Let backtesting/Granger tests decide, don't assume the answer is no.

### Multi-step horizon approach
- **D-06:** Test BOTH iterative/recursive forecasting (fit a 1-step model, feed
  each forecast back in as the next input for steps 2-12) AND direct multi-step
  models (a separate model fit per horizon) — compare backtest accuracy per
  horizon and let the results decide which approach wins per series, rather than
  committing to one upfront. Report which approach wins for which series/horizon
  range; it's fine if the answer differs by series.

### Backtest split strategy
- **D-07:** Use walk-forward / rolling-origin validation — repeatedly train on
  data up to month N, forecast N+1..N+12, roll forward, repeat — rather than a
  single fixed holdout. This differs from the original Excel workbook's
  single 12-month-holdout MAPE methodology (still worth reporting for
  comparability) but better matches both the horizon-compounding question (D-06)
  and how the shipped app will actually be used (refit as new months arrive).

### Weekly-mode proxy — explicitly deferred
- **D-08:** Do NOT investigate whether Baltic AN (weekly data) can proxy for
  HDAN/PPAN (no weekly data) in this phase, despite the original Phase 1
  CONTEXT.md flagging "Phase 2 or later." Weekly forecast mode is v2/deferred
  scope per REQUIREMENTS.md; this phase stays focused on the monthly models
  FCST-07 actually requires. Revisit only when/if weekly mode is picked up as
  its own milestone.

### Claude's Discretion
None flagged this round — all four presented gray areas were explicitly decided.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & prior decisions
- `.planning/PROJECT.md` — project context, core value, constraints
- `.planning/REQUIREMENTS.md` — FCST-07 (this phase's requirement), v2 deferred
  list (weekly mode, live news/sentiment scenarios — D-03/D-08 connect to these)
- `.planning/phases/01-app-skeleton-data-layer/01-CONTEXT.md` — Phase 1's D-05b/c
  seed-source decisions; defines exactly which 16 columns exist and where each
  came from (needed to know what's a legitimate predictor vs. derived/reference
  data)
- `.planning/research/PITFALLS.md` — small-sample overfitting risk (HDAN/PPAN
  ~48-164 points), "bands should widen with horizon" finding (relevant to D-06
  and GARCH's role in D-01), weekly-mode gap already flagged as high-risk if
  handled via silent interpolation (reinforces D-08's deferral)
- `.planning/research/STACK.md` — statsmodels 0.14.6 confirmed (ARIMA/SARIMAX/
  VAR/GARCH all available), pmdarima/scikit-learn flagged as research-phase-only
  tools, not for production wiring

### Prior art (reference, not to be blindly copied — schema and scope changed)
- `backend_research/causality_matrix.py` — prior Granger-causality approach for
  the original 2-file/10-column schema; structure is a useful reference for
  D-04's "test the full predictor set" approach, but must be adapted for the
  new 16-column schema and 3-file provenance
- `backend_research/model_harness.py`, `run_var_candidates.py`,
  `run_single_series_candidates.py`, `run_sarimax_tuned.py` — prior single-split
  backtest harness; D-07 changes the split strategy to walk-forward, so these
  need adaptation, not reuse as-is
- `backend_research/REPORT.md` — original workbook's model choices and 12-month
  holdout MAPEs (HDAN 9.4%, PPAN 10.0%, Diesel-USD 3.4%, FX 0.25%) — useful
  comparison baseline even though Phase 2 uses a different split strategy and
  expanded predictor set

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/app/models.py` — `PriceRow` schema (17 columns incl. date) this phase
  queries for training data
- `backend_research/data_loader.py` — prior CSV-loading pattern; not directly
  reusable (different schema) but shows prior whitespace/comma-stripping
  conventions worth being consistent with

### Established Patterns
- Phase 1 established SQLite (`reflex.db`) as the source of truth for price
  history — Phase 2's research scripts should read from there, not re-parse the
  CSVs directly, to stay consistent with whatever's actually been entered/edited
  since seeding.

### Integration Points
- Phase 2's research report is the direct input to Phase 3 (Forecasting Module),
  which implements whatever models/predictors/horizon-strategy this phase names
  as winners.

</code_context>

<specifics>
## Specific Ideas

User provided a detailed taxonomy of forecasting method families (time-series,
causal/econometric, machine learning, technical/market-based, qualitative/
judgment-based) with the underlying assumption each family bets on. This
taxonomy is captured verbatim in D-01/D-02/D-03's scoping decisions above and
should inform how the research report frames its findings (organize by "which
assumption won," not just by raw MAPE ranking).

</specifics>

<deferred>
## Deferred Ideas

- Weekly-mode Baltic AN → HDAN/PPAN proxy research (D-08) — belongs to a future
  weekly-mode milestone, not Phase 2.
- Scenario planning / Delphi-style qualitative override mechanism (D-03) — this
  is the mechanism for v2's live news/sentiment-driven scenario adjustment
  (REQUIREMENTS.md v2 list), not Phase 2/3 work.
- Technical/market-based methods (D-02) — not selected by the user; could be
  revisited if a specific reason emerges, but no current driver.

### Reviewed Todos (not folded)
None — no pending todos matched this phase.

</deferred>

---

*Phase: 2-Model Research & Backtesting*
*Context gathered: 2026-08-21*
