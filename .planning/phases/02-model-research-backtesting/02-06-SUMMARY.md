---
phase: 02-model-research-backtesting
plan: 06
subsystem: forecasting-research
tags: [scikit-learn, RandomForest, GradientBoosting, walk-forward-backtest, overfitting-diagnostics]

requires:
  - phase: 02-model-research-backtesting
    provides: "walk_forward.py harness (02-01), causality_screen.py shortlist_for (02-02), wf_baseline_ets.json naive MAPE (02-03)"
provides:
  - "RandomForest/GradientBoosting walk-forward backtest for all four targets, direct + iterative multi-step (D-06)"
  - "D-01-mandated overfitting diagnostics (naive margin, feature importances, lag1 share, overfit_flags) attached to every ML record as data"
affects: [02-07]

tech-stack:
  added: []
  patterns:
    - "Direct multi-step: one regressor per horizon 1-12, dispatched by a .forecast(steps) wrapper, matching plan 02-04/02-05's _DirectMultistepWrapper shape"
    - "Iterative multi-step: single 1-step regressor recursed, own-lag features cascade the prediction, non-target predictor features hold their last observed value across the recursion"
    - "Overfitting evidence computed once per record and shipped inline in the JSON, not left to report-writing prose"

key-files:
  created:
    - backend_research/run_ml_baseline.py
    - backend_research/results/wf_ml_baseline.json
  modified: []

key-decisions:
  - "min_train shrunk per series from the plan's nominal 48 down to min(48, max(24, n_rows-2)) since hdan/ppan's ~48-row raw series drops to 45 rows after lag-shift + dropna, which is infeasible against a fixed min_train=48 — the resulting thin-origin runs are exactly what the small_sample overfit_flag exists to surface"
  - "suspiciously_strong check reads wf_arima_sarimax.json and wf_var_vecm.json if present and skips with a note otherwise, per plan ordering not guaranteeing those files exist first"
  - "Both tasks (direct-strategy model + iterative-strategy/diagnostics) implemented and committed together since the diagnostics function operates identically over both strategies and splitting would have meant writing then immediately rewriting the same file"

requirements-completed: [FCST-07]

duration: 25min
completed: 2026-08-21
---

# Phase 02 Plan 06: ML Baseline (RandomForest/GradientBoosting) Walk-Forward Backtest Summary

**RandomForest and GradientBoosting backtested under the shared walk-forward harness in both direct and iterative multi-step form for all four targets, with D-01's mandated overfitting diagnostics (naive-margin, feature importances, lag1 dominance, overfit_flags) attached to every record as machine-readable evidence rather than left to report prose.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `build_feature_frame(history, target)`: target's own lags 1-3 plus `shortlist_for(target, tier="p10")` predictors at their screen-selected lag, all `.shift()`-ed for the anti-leakage rule shared with plans 02-04/02-05. Column names follow `{col}_lag{n}` so feature importances are self-describing in the JSON.
- `fit_direct_ml` / `_DirectMLWrapper`: one regularised regressor per horizon 1-12 (deliberately shallow — `max_depth=4`/`2`, `min_samples_leaf=3`, `random_state=42` on both model classes for reproducibility), same shape as the existing `_DirectMultistepWrapper` pattern from plans 02-04/02-05.
- `fit_iterative_ml` / `_IterativeMLWrapper`: single 1-step regressor recursed to 12 steps; own-lag features cascade the model's own prior prediction into lag1 (lag2 <- old lag1, lag3 <- old lag2); non-target predictor features hold their last observed (already-lagged) value across the recursion since their future values are not known at the origin — documented in `notes` as the honest production scenario.
- Every one of the 16 output records carries all five D-01 diagnostic keys: `naive_mape_mean_1_12` (from `wf_baseline_ets.json`'s `Naive` record), `margin_over_naive_pct_points`, `feature_importances` (top 10, from a full-history refit), `lag1_importance_share`, and `overfit_flags` populated from `lag1_dominant` (>0.5 share), `marginal_over_naive` (<1.0pp margin), `small_sample` (<80 usable rows), and `suspiciously_strong` (>30% better than the best statistical-family MAPE on disk).
- `main()` prints a per-record summary line plus a closing "OVERFITTING CAVEATS" block whenever any record carries flags, so the report author cannot miss them when assembling plan 02-07.
- Actual run results: hdan/ppan RandomForest posted large naive-margins (15-20pp) but are flagged `small_sample` (and RandomForest additionally `suspiciously_strong` vs. the statistical families); diesel/fx ML models did NOT beat naive (`marginal_over_naive`, negative margins) — the ML family is not a clean winner anywhere once the diagnostics are read, which is exactly D-01's expected posture toward this family.

## Task Commits

1. **Task 1 + Task 2 (combined): direct ML models + iterative variant/overfitting diagnostics** - `459209c` (feat)

Both tasks were implemented and committed together: the diagnostics function (`_attach_diagnostics`) is written once and applied identically to both direct- and iterative-strategy records, and the two model classes' hyperparameters/wrappers are defined side by side in the same module — splitting into two commits would have meant committing an incomplete/undiagnosed record shape and then immediately rewriting the same lines, which is not a meaningful intermediate state.

**Plan metadata:** pending (this commit)

## Files Created/Modified
- `backend_research/run_ml_baseline.py` - `build_feature_frame`, `_DirectMLWrapper`/`fit_direct_ml`, `_IterativeMLWrapper`/`fit_iterative_ml`, `_attach_diagnostics`, `build_ml_records`, `main`
- `backend_research/results/wf_ml_baseline.json` - 16 records (RandomForest + GradientBoosting x direct + iterative x hdan/ppan/diesel_usd_ton/fx_rate), each with `mape_by_horizon`, `single_holdout_mape`, and the five D-01 diagnostic keys

## Decisions Made
- `min_train` shrunk adaptively per series (documented above) rather than leaving the plan's nominal `min_train=48` hard-coded, since it is infeasible against hdan/ppan's post-dropna row count; the shrinkage itself is recorded in each record's `notes` field.
- `suspiciously_strong` reads `wf_arima_sarimax.json`/`wf_var_vecm.json` defensively (both exist on disk at this point in the wave, but the code degrades gracefully with a note if either is absent) rather than hard-requiring plan ordering.
- Feature importances are computed from a full-history refit (not averaged across walk-forward origins) — cheaper and matches how the report will describe "what the model actually learned," while the walk-forward MAPE itself remains the leakage-safe number.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `min_train=48` infeasible against hdan/ppan's post-dropna row count**
- **Found during:** Task 1, first script run
- **Issue:** `walk_forward_backtest` raised `LeakageError: min_train=48 >= len(series)=45` for hdan (and would have for ppan) — the plan's harness parameter `min_train=48` assumed the raw series length (~48 rows), but the lag-shifted feature frame loses `max(own_lags)` rows to `dropna()`, leaving only 45 usable rows.
- **Fix:** Added `effective_min_train = min(MIN_TRAIN, max(24, n_rows - 2))` computed per series from the post-dropna feature-frame length, with the shrinkage recorded in `notes`. hdan/ppan now run with fewer walk-forward origins (thin but functional), which the pre-existing `small_sample` overfit_flag already exists to surface.
- **Files modified:** backend_research/run_ml_baseline.py
- **Verification:** re-ran `python run_ml_baseline.py` — all four series produce 4 records each (16 total), no LeakageError.
- **Committed in:** 459209c

---

**Total deviations:** 1 auto-fixed (1 bug — required to make hdan/ppan runnable at all; no scope creep, well within the plan's own `small_sample` diagnostic design).
**Impact on plan:** None on scope; the fix is a direct enabler of the plan's own stated acceptance criterion ("results for all four series").

## Issues Encountered
- hdan/ppan's ~48-row history yields very few walk-forward origins (2-3) once `min_train` is shrunk to fit — the resulting MAPE numbers for these two series are correspondingly noisy and should be read alongside `n_origins`/`failed_origins` in the JSON, not as a precise estimate. This is flagged via `small_sample` on every hdan/ppan record.
- No `lag1_dominant` flag fired in the actual run (max `lag1_importance_share` was 0.50 for fx_rate GradientBoosting, just at the 0.5 threshold but not exceeding it) — the ML models are not simply memorising a random walk through their own lag-1 feature, though fx_rate's heavy reliance (0.40-0.50 share) on it is close enough to be worth calling out in the report even without the flag.
- No auth gates or checkpoints encountered — plan is fully autonomous.

## Next Phase Readiness
- `wf_ml_baseline.json` is ready for plan 02-07's cross-family ranking alongside `wf_arima_sarimax.json` (02-04), `wf_baseline_ets.json` (02-03), and `wf_var_vecm.json` (02-05).
- The overfitting caveats (particularly hdan/ppan RandomForest's `suspiciously_strong` flag and diesel/fx's failure to beat naive) must be surfaced explicitly in 02-07's report per D-01's instruction — the data is already attached to make that unavoidable.

---
*Phase: 02-model-research-backtesting*
*Completed: 2026-08-21*

## Self-Check: PASSED
- FOUND: backend_research/run_ml_baseline.py
- FOUND: backend_research/results/wf_ml_baseline.json
- FOUND: commit 459209c
