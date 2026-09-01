# Phase 21: Weekly Forecasting Module - Context

**Gathered:** 2026-09-01
**Status:** Ready for planning
**Source:** Direct context capture (roadmap already fully specifies this backend-only
infrastructure phase; no UI/design gray areas requiring user interview — see rationale
below)

<domain>
## Phase Boundary

Backend-only infrastructure phase, no UI, no Reflex state. Wires Phase 17's and Phase 20's
already-frozen, already-backtested weekly model constants into a new weekly forecasting
module, mirroring `app/app/forecasting.py`'s existing monthly pattern exactly. Unblocks
Phase 22 (UI), which depends on this phase's function signatures.

**Why no interactive discussion:** No user-facing surface. This phase transcribes already-
decided model constants (from Phase 17/20's frozen JSON results) into `forecasting.py`-style
functions — a mechanical, well-precedented extension of an existing pattern already proven
in this exact codebase. No new design decisions remain.
</domain>

<decisions>
## Winning models to transcribe (locked — read directly from frozen result JSONs)

Per-series best model, selected by lowest `mape_h4` in each frozen JSON (never re-derive
these by re-running a backtest or searching for a "better" model — that would violate the
project's core "no un-backtested model ships" / "frozen constants, never re-search at
runtime" discipline already established across every prior phase):

- **HDAN**: `SARIMAX(0,1,0)+BalticAN(exog, duplicate)` — 7.25% MAPE (h=4), from
  `backend_research/results/weekly_sarimax_ets.json`. Uses `Baltic AN` as an exogenous
  driver (from `AN Data.csv`, already present in `WeeklyPriceRow.baltic_an` per Phase 19's
  ingestion — no new data needed).
- **PPAN**: `SARIMAX(0,1,0)+BalticAN(exog, duplicate)` — 6.96% MAPE (h=4), same source file,
  same exog driver.
- **FX rate**: `ETS-HoltDamped` (trend=add, seasonal=None, damped_trend=True) — 0.86% MAPE
  (h=4), from `backend_research/results/weekly_fx.json`. Note this is a **univariate**
  model — no exog driver, unlike HDAN/PPAN.
- Benchmark figures for `WEEKLY_MODEL_INFO` (the weekly-mode analog to the monthly
  `MODEL_INFO`): HDAN 7.25%, PPAN 6.96%, FX 0.86% — read the exact figures from the frozen
  JSON at implementation time rather than trusting this document's transcription (same
  "verify, don't trust the plan's numbers blindly" discipline PITFALLS.md established for
  earlier phases).

## Architecture (locked — mirror the existing monthly module exactly)

- New functions in `app/app/forecasting.py` (same file, not a new module — the monthly and
  weekly forecasting logic should live together since they share low-level helpers):
  `forecast_weekly_hdan(history, horizon)`, `forecast_weekly_ppan(history, horizon)`,
  `forecast_weekly_fx(history, horizon)`, each returning the same
  `{"base": [...], "bull": [...], "bear": [...]}`-shaped dict the monthly functions
  (`forecast_hdan`, `forecast_fx`, etc.) already return — same return contract, so Phase 22
  can consume weekly and monthly results identically.
- `forecast_all_weekly(history, horizon)` dispatcher, mirroring `forecast_all`'s existing
  shape — but note: weekly has only 3 series (HDAN, PPAN, FX), never Diesel-USD or
  Diesel-MNT (no weekly source data for those, confirmed unavailable). Do NOT add stub/
  placeholder Diesel entries to this dispatcher's output — its key set should be exactly
  `{"hdan", "ppan", "fx_rate"}`, and Phase 22's UI is responsible for rendering Diesel's
  absence honestly, not this module faking a value.
- `WEEKLY_MODEL_INFO: dict[str, tuple[str, float]]` constant, analogous to the existing
  `MODEL_INFO` — same tuple shape `(model_name: str, mape: float)`, but only 3 keys.
- Reuse existing low-level helpers wherever the pattern fits: `_arima_forecast_se` (for the
  SARIMAX-based HDAN/PPAN spread), `_apply_se_spread`, `_naive_forecast` if useful for
  fallback/comparison. Do NOT duplicate these helpers into new weekly-prefixed copies —
  import/call the existing ones. For ETS (FX's winning model, a family not previously used
  in the monthly module), a new spread-generation approach will be needed since
  `_arima_forecast_se` is ARIMA-specific — see Claude's Discretion below.
- `MAX_HORIZON` equivalent for weekly: the backtest only validated up to `horizon=5` weeks
  (`n_origins`/`horizon` fields in the frozen JSON confirm `horizon: 5`). A weekly
  `MAX_HORIZON_WEEKLY = 5` (or similar name) constant should cap what these functions will
  forecast — never silently extrapolate beyond the validated 5-week horizon (this is the
  same "no un-backtested model ships" principle applied to horizon range, not just model
  choice).

## Data source (locked)

- Weekly history comes from `WeeklyPriceRow` (Phase 19's new table), queried the same way
  `DashboardState`/`forecast_all`'s callers already query `PriceRow` — but this phase does
  NOT touch `state.py` or any Reflex code. This phase's functions take a `history: pd.DataFrame`
  parameter (mirroring the monthly functions' existing signature) and are fully testable by
  passing a hand-built or `WeeklyPriceRow`-sourced DataFrame directly — no Reflex session
  dependency, matching the monthly module's existing "independent of the UI, unit-testable"
  discipline (stated explicitly in CLAUDE.md's Constraints section).

## Non-goals

- No Reflex `state.py` changes — that's Phase 22.
- No UI changes — that's Phase 22.
- No changes to the existing monthly `forecast_hdan`/`forecast_ppan_var_system`/
  `forecast_fx`/`forecast_diesel_usd`/`diesel_mnt_forecast`/`forecast_all` functions or
  `MODEL_INFO` — strictly additive to `forecasting.py`.
- No re-backtesting or re-deriving model choices — Phase 17 and Phase 20's frozen results
  are the sole source of truth for which model/constants to transcribe.
- No weekly Diesel-USD/Diesel-MNT forecasting — no weekly source data exists for these,
  confirmed unavailable across this entire milestone.

### Claude's Discretion

- Exact spread/confidence-band generation approach for the ETS-HoltDamped FX model — the
  existing monthly module's spread helpers (`_apply_garch_spread` for HDAN,
  `_apply_se_spread` for ARIMA-based series) are family-specific; ETS wasn't previously
  wired into the monthly module (the monthly FX winner is Naive, not ETS), so this is new
  ground. A reasonable approach: use the ETS model's own prediction interval / standard
  error if `statsmodels`'s `ExponentialSmoothing`/`Holt` exposes one directly, or fall back
  to a walk-forward-backtest-derived empirical error spread (the backtest script already
  computed per-origin errors — those could inform a spread estimate). Executor's call,
  but must be backtest-grounded, not an arbitrary flat percentage.
- Exact module organization within `forecasting.py` (where the new functions/constants are
  placed relative to existing monthly code) — follow whatever reads cleanly, but keep
  weekly and monthly clearly delineated (e.g. a comment banner section, consistent naming
  prefix `_weekly`/`forecast_weekly_*`).
- Whether `forecast_all_weekly` takes a `markup_pct` parameter like the monthly
  `forecast_all` does — likely not needed since there's no weekly Diesel-MNT derivation,
  but confirm by checking whether any downstream Phase 22 need requires it (executor's
  call, informed by not over-building unused parameters).

## Deferred Ideas

None raised — this is a tightly-scoped, pre-specified infrastructure phase with no
scope-creep surface.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` (Phase 21 section) — goal, success criteria (this phase has no
  direct WKUI requirement — pure infrastructure unblocking Phase 22's WKUI-06/07)
- `backend_research/results/weekly_sarimax_ets.json` — frozen HDAN/PPAN weekly model
  candidates (source of the winning constants above)
- `backend_research/results/weekly_fx.json` — frozen FX weekly model candidates (source of
  the winning constant above)
- `backend_research/REPORT-WEEKLY.md` and `backend_research/REPORT-WEEKLY-FX.md` — human-
  readable reports explaining the same frozen results
- `app/app/forecasting.py` — the existing monthly module this phase extends; read in full
  before planning, especially `forecast_hdan` (SARIMAX+exog+GARCH pattern to mirror for
  weekly HDAN/PPAN), `forecast_fx` (simplest existing pattern), `_arima_forecast_se`,
  `_apply_se_spread`, `MODEL_INFO`, `forecast_all`, `MAX_HORIZON`
- `app/app/models.py` — `WeeklyPriceRow` schema (Phase 19), the shape of history data this
  phase's functions will receive
- `.planning/phases/19-weekly-schema-ingestion/19-02-SUMMARY.md` and
  `.planning/phases/20-fx-weekly-backtest/20-01-SUMMARY.md` — what those phases actually
  delivered, for accurate integration
- `CLAUDE.md` — project constraint: "forecasting models must go through a research/backtest
  step before being used in the app — no un-backtested model ships to the dashboard" and
  "independent of the UI... so it can be unit-tested"
</canonical_refs>
