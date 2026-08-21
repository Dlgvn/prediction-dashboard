# Phase 3: Forecasting Module & Derived Series - Context

**Gathered:** 2026-08-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Given historical data (from Phase 1's SQLite table) and a chosen horizon (1-12 months),
the system produces base/bull/bear forecasts for HDAN, PPAN, Diesel-USD, and FX using
the specific models Phase 2 validated (`02-MODEL-DECISIONS.md`), plus the derived
Diesel-MNT series (Diesel-USD × FX × markup). This phase implements the forecasting
module itself — a framework-independent Python module Phase 4/5's Reflex state layer
will call. It does NOT touch the UI (Phase 4/5) and does NOT introduce any model Phase 2
didn't validate.

</domain>

<decisions>
## Implementation Decisions

### HDAN's missing future exog values
- **D-01:** HDAN's winning model (SARIMAX+exog) needs future values of 6 predictors
  (ppan, urea_china, urea_black_sea, ammonia, baltic_an, corn_us) to forecast beyond
  horizon step 1. Phase 3 must forecast each of these 6 predictors with its own simple
  model first, then feed those forecasted paths into HDAN's SARIMAX as exog — standard
  practice for SARIMAX-with-exog multi-step forecasting, not a shortcut.
- **D-02:** The 6 predictor sub-models use a simple ARIMA(1,1,0)-style fit each (or the
  closest sensible order per predictor's actual behavior) — one consistent lightweight
  statistical approach for all 6, fit at request time. These do NOT need Phase 2's full
  backtest rigor (they're inputs to HDAN's forecast, not this phase's own deliverable),
  but they should be real fitted models, not held-flat-at-last-value naive projections.
- **D-03 (conflict resolution):** PPAN's winning model is a VAR system over
  [ppan, hdan, baltic_an, urals], which forecasts HDAN jointly as a byproduct of
  forecasting PPAN. HDAN also has its own separate winning model (SARIMAX+exog).
  **HDAN's own SARIMAX forecast is authoritative everywhere the app displays "the" HDAN
  number** — the VAR system's internal hdan forecast is used only internally to make
  PPAN's VAR system self-consistent (VAR forecasts its whole system jointly and needs no
  external exog), not surfaced or compared against SARIMAX's HDAN output.

### Bull/bear spread confidence level
- **D-04:** Bull/bear = base ± 1 standard deviation of the volatility source named per
  series in `02-MODEL-DECISIONS.md` (GARCH sigma for HDAN, ARIMA forecast SE for PPAN/
  Diesel-USD/FX) — an approximately 68% band, not a 95% band. Matches the Excel
  workbook's simpler ±MAPE-style band philosophy (an approximate range communicated
  honestly, not a formal statistical claim) rather than a wider 95% interval that
  `PROJECT_VISION.md` already flagged as under-covering its stated target on this data.
- **D-05:** Per FCST-05 (already a locked requirement) and Phase 2's GARCH findings, the
  spread must widen with horizon using each series' actual per-horizon sigma/SE value
  (already present in `02-MODEL-DECISIONS.md`'s h=1/h=6/h=12 walk-forward numbers) — not
  a single fixed spread applied flat across all 12 months.

### Refit cadence
- **D-06:** Models refit on every forecast request, fitting on whatever's currently in
  the SQLite `PriceRow` table — no caching or cache-invalidation logic. Justified by
  scale: ~164 rows per series, simple model orders (SARIMAX(0,1,0), small VAR, Naive),
  single occasional user — fit cost is milliseconds, not a real latency concern. Do not
  add caching infrastructure preemptively.

### Module boundaries & organization
- **D-07:** Per-series functions behind one dispatch function — `forecast_hdan()`,
  `forecast_ppan_var_system()`, `forecast_diesel_usd()` / `forecast_fx()` (both Naive,
  may share one function), each implementing that series' actual winning model's logic
  as validated in Phase 2. A single `forecast_all(rows, horizon)` orchestrates all four,
  computes bull/bear from the correct volatility source per series (D-04/D-05), and
  derives `diesel_mnt` (existing requirement FCST-03) from the Diesel-USD and FX
  forecasts plus the global `markup_pct` `AppSetting` (from Phase 1's schema). Rejected a
  single generic `forecast_series(history, horizon, model_config)` — the config dict
  would encode very different things per series (VAR needs a system list, SARIMAX needs
  predictor forecasts, Naive needs neither), producing a fake-uniform interface that
  hides real complexity rather than clarifying it.
- **D-08:** This module has zero `import reflex` (per `ARCHITECTURE.md`'s established
  boundary) — unit-testable independent of the UI, called by Phase 4/5's Reflex state
  layer, not by anything in `app/app/app.py` directly.

### Claude's Discretion
None flagged this round — all four presented gray areas were explicitly decided, several
with follow-up rounds.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Model specifications (binding)
- `.planning/phases/02-model-research-backtesting/02-MODEL-DECISIONS.md` — the exact
  per-series winning model, horizon strategy, predictor set, walk-forward MAPE, and
  volatility source this phase must implement. Includes an explicit "Phase 3 must not"
  section (no runtime order search/auto_arima, no flat spread, no un-backtested model).
- `backend_research/REPORT-PHASE2.md` — full backtest detail if `02-MODEL-DECISIONS.md`
  is insufficient for any specific parameter
- `backend_research/results/winners.json` — machine-readable version of the same
  decisions, useful for programmatic reference

### Requirements & architecture
- `.planning/REQUIREMENTS.md` — FCST-02 through FCST-06 are this phase's requirements
  (base/bull/bear per series, Diesel-MNT derivation, per-series/horizon-scaled spread,
  forecast values in table form — though the table itself is Phase 5's UI, this phase
  must produce data in a shape Phase 5 can render as a table)
- `.planning/research/ARCHITECTURE.md` — confirms the `forecasting.py`
  zero-`import reflex` boundary (D-08) and that `research/`/`backend_research/` stays
  separate from `app/app/`
- `.planning/PROJECT.md` — project context, core value

### Prior phase context
- `.planning/phases/01-app-skeleton-data-layer/01-CONTEXT.md` — `PriceRow`/`AppSetting`
  schema (16 series columns + markup_pct) this phase reads from
- `.planning/phases/02-model-research-backtesting/02-CONTEXT.md` — D-06/D-07 (walk-forward
  validation, both horizon strategies tested) that produced the winning models this phase
  implements

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/app/models.py` — `PriceRow` (16-column schema), `AppSetting` (markup_pct) —
  Phase 3's data source
- `backend_research/run_arima_sarimax_wf.py`, `backend_research/run_var_vecm_wf.py`,
  `backend_research/run_baseline_ets.py` — Phase 2's research scripts already implement
  working fit/forecast logic for each winning model family; Phase 3's production module
  should reference these for correct statsmodels API usage (order specifications, VAR
  system setup) but is a fresh, production-quality implementation — not a copy-paste,
  since the research scripts were built for walk-forward backtesting, not live
  request-time forecasting from the current DB state.
- `backend_research/walk_forward.py` — the leakage-safe windowing logic; not directly
  reused (Phase 3 forecasts forward from all available data, no held-out testing) but
  useful reference for correct statsmodels fit/predict call patterns.

### Established Patterns
- Phase 1 established "SQLite is the source of truth" — Phase 3's `forecast_all` should
  read fresh from `PriceRow` on every call (consistent with D-06's refit-every-request
  decision), not from any cached/passed-in DataFrame that might be stale.

### Integration Points
- Phase 4/5's Reflex `DashboardState` will call `forecast_all(rows, horizon)` — the
  return shape should be something Phase 5's UI can directly render as both a chart and
  a table (per FCST-06) without further transformation, though the exact dict/dataclass
  shape is Phase 3's planner's call to make (not decided in this discussion).

</code_context>

<specifics>
## Specific Ideas

None beyond the decisions above — no additional styling/behavioral references given.

</specifics>

<deferred>
## Deferred Ideas

None raised outside phase scope — discussion stayed within Phase 3's boundary (model
implementation, exog handling, spread computation, refit cadence, module organization).

</deferred>

---

*Phase: 3-Forecasting Module & Derived Series*
*Context gathered: 2026-08-21*
