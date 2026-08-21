---
phase: 02-model-research-backtesting
plan: 04
subsystem: model-research
tags: [arima, sarimax, ets, holt, baseline, statsmodels, walk-forward]

# Dependency graph
requires:
  - phase: 02-model-research-backtesting
    provides: "walk_forward.py shared harness and db_loader.py (02-01)"
  - phase: 02-model-research-backtesting
    provides: "causality_screen.shortlist_for() predictor shortlists (02-02)"
provides:
  - "Naive/MovingAverage/SES/HoltDamped baseline walk-forward MAPE per series per horizon (backend_research/results/wf_baseline_ets.json)"
  - "ARIMA (fixed order by AIC) and SARIMAX (causality-selected, lagged exog) walk-forward MAPE, both iterative and direct multi-step, per series per horizon (backend_research/results/wf_arima_sarimax.json)"
affects: [02-07-assemble-report]

# Tech tracking
tech-stack:
  added: []
  patterns: ["All walk-forward slicing delegated to walk_forward_backtest — no bespoke loops", "ARIMA order selected once by AIC and held fixed for the whole walk-forward run, mirroring the hard-coded-order production pattern", "Exog predictors always .shift(lag)-ed before being handed to the harness"]

key-files:
  created: [backend_research/run_baseline_ets.py, backend_research/run_arima_sarimax_wf.py, backend_research/results/wf_baseline_ets.json, backend_research/results/wf_arima_sarimax.json]
  modified: []

key-decisions:
  - "Naive/MovingAverage/SES/Holt-damped baselines fitted on price LEVELS (not pct-change) for direct MAPE comparability with all other families"
  - "seasonal=None on Holt per RESEARCH.md Pattern 4 — insufficient annual cycles for some series"
  - "ARIMA order fixed once per series (AIC on first min_train window), never re-searched per origin (Pitfall 2 cost control, mirrors Phase 3's hard-coded-order plan)"
  - "Direct multi-step variant implemented as an OLS-per-horizon wrapper whose .forecast() dispatches internally, so ALL window slicing stays inside walk_forward_backtest"

requirements-completed: [FCST-07]

# Metrics
duration: 20min
completed: 2026-08-21
---

# Phase 2 Plan 04: Baseline + ARIMA/SARIMAX Walk-Forward Backtests Summary

**Naive/MA/SES/Holt-damped baselines and fixed-order ARIMA/SARIMAX (with causality-selected lagged exog) backtested under walk-forward validation for both iterative and direct multi-step strategies, across all four target series.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2 (auto)
- **Files modified:** 4 created

## Accomplishments

- `run_baseline_ets.py` produces 16 records (4 series x 4 specs: Naive, MovingAverage(3), SES, HoltDamped) via the shared `walk_forward_backtest` harness, each with `mape_by_horizon` (12 keys), `mape_mean_1_12`, and `single_holdout_mape`.
- Naive's h=12 MAPE exceeds h=1 for all four series (9.65->33.50 hdan, 11.81->32.72 ppan, 2.34->7.69 diesel, 0.39->2.98 fx) confirming error grows with horizon (no leakage).
- `run_arima_sarimax_wf.py` produces 12 records: one ARIMA record per series (order fixed by AIC), plus for each series either one SARIMAX-iterative + one Direct-OLS record (when the causality screen found a predictor) or a documented no-predictor record.
- All four series had a non-empty p10 shortlist this run, so all four got both iterative SARIMAX and direct multi-step records — D-06's iterative-vs-direct comparison is fully covered.
- Leakage sanity check implemented and ran clean: no walk-forward MAPE came in dramatically better than REPORT.md's prior single-holdout figures (HDAN 9.4%, PPAN 10.0%, Diesel-USD 3.4%, FX 0.25%) — no "LEAKAGE SUSPECT" lines printed.

## Task Commits

1. **Task 1: Naive / moving-average / exponential-smoothing baselines** - `46f902d` (feat)
2. **Task 2: ARIMA grid search and SARIMAX with causality-selected exog, iterative vs direct** - `5c419c8` (feat)

**Plan metadata:** pending (this commit)

## Files Created/Modified

- `backend_research/run_baseline_ets.py` - `NaiveForecaster`, `MovingAverageForecaster`, SES/Holt wrappers, `main`; all four specs run through `walk_forward_backtest`
- `backend_research/results/wf_baseline_ets.json` - 16 records, one per series x model spec
- `backend_research/run_arima_sarimax_wf.py` - `fit_arima`, `fit_sarimax`, `direct_ols_multistep`, `select_arima_order`, `main`
- `backend_research/results/wf_arima_sarimax.json` - 12 records covering all four series, both `iterative` and `direct` horizon strategies

## Decisions Made

- Baselines fit on price levels, not pct-change, so every family in this phase shares directly comparable MAPE units.
- ARIMA order search (p in 0-2, d in 0-1, q in 0-2 = 18 combos) run ONCE by AIC on the first 36-obs window per series, then held fixed for the entire walk-forward run — avoids re-searching every origin (compute) and matches the "ship a hard-coded order" production plan.
- SARIMAX exog exclusively sourced from `causality_screen.shortlist_for(target, tier="p10")`, each predictor `.shift(lag)`-ed before being handed to the harness so no future/contemporaneous value leaks in.
- Direct multi-step strategy implemented via a `_DirectMultistepWrapper` that fits 12 separate `statsmodels.api.OLS` models (target shifted -h, features = shifted predictors + y's own lags 1-3) internally, so the wrapper's `.forecast(steps)` dispatches to the h-th model while the shared harness still owns all rolling-origin window slicing (the plan's single anti-leakage rule).

## Deviations from Plan

None - plan executed exactly as written. All four series happened to have a non-empty causality shortlist this run (per 02-02's finding that fx_rate now shows real predictors after the expanded predictor set re-test), so no series needed the "AR-only ARIMA is the honest specification" fallback path this time — that code path exists and is exercised by the empty-shortlist branch in `build_sarimax_records`, but was not hit on this dataset.

## Issues Encountered

- A handful of `mape_by_horizon` values at h=12 for the shorter SARIMAX/direct-OLS records came back `null` (e.g. hdan/ppan/diesel SARIMAX and Direct-OLS records) — the exog-shifted + lagged-y frames lose enough rows relative to the AR-only ARIMA series that some walk-forward origins can't reach horizon 12 within the available data. This is expected sample-size behavior (documented in each record's `notes` and the plan's own Direct-OLS note about losing h rows per horizon), not a bug — `mape_mean_1_12` is computed only over the horizons that have data, and remains numeric in every record per the acceptance criteria.
- Several SARIMAX/direct records show WORSE MAPE than the AR-only ARIMA baseline for hdan/ppan/diesel (e.g. hdan SARIMAX h=6 11.44 vs ARIMA 25.56 is actually better, but Direct-OLS h=6 41.66 is much worse than ARIMA). This is an honest research finding, not smoothed over — plan 02-07's report assembler will need to weigh these per-family, per-horizon results rather than assume exog/direct strategies always win.

## Next Phase Readiness

- `wf_baseline_ets.json` gives plan 02-06 (ML models) and 02-05 (VAR/VECM) an honest naive/MA floor to be measured against, per series per horizon.
- `wf_arima_sarimax.json` gives the incumbent statistical family's walk-forward numbers, with both iterative and direct multi-step strategies (D-06) and a documented leakage sanity check (D-07/T-02-07), ready for plan 02-07's report assembly.
- No blockers.

---
*Phase: 02-model-research-backtesting*
*Completed: 2026-08-21*

## Self-Check: PASSED
