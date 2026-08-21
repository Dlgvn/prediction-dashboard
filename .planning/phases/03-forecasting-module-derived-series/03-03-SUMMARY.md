---
phase: 03-forecasting-module-derived-series
plan: 03
subsystem: forecasting
tags: [direct-ols, ppan, diesel, fx, naive]
requires:
  - 03-01: forecasting primitives (_arima_forecast_se, _naive_forecast, _apply_se_spread, ARIMA_SE_ORDER, PPAN_SYSTEM_MEMBERS, PPAN_TARGET_LAGS)
provides:
  - forecast_ppan_var_system(history, horizon) -> {base, bull, bear}
  - forecast_diesel_usd(history, horizon) -> {base, bull, bear}
  - forecast_fx(history, horizon) -> {base, bull, bear}
affects:
  - app/app/forecasting.py
tech-stack:
  added: []
  patterns:
    - "Direct-OLS multi-step: one sm.OLS per horizon step h, target=y.shift(-h), predict by pushing the single last feature row through all fitted models, columns reindexed to model.params.index with fill_value=0.0"
key-files:
  created: []
  modified:
    - app/app/forecasting.py
    - app/tests/test_forecasting.py
decisions:
  - "PPAN uses the Direct-OLS VAR-system variant (twelve independent sm.OLS regressions), not the iterative statsmodels VAR() object described in 03-RESEARCH.md Pattern 2 — that pattern documents the rejected runner-up, per the plan's planner_correction and 02-MODEL-DECISIONS.md's binding spec"
  - "Docstrings for forecast_ppan_var_system avoid the literal substrings 'tsa.api.VAR' and 'VAR(' (even inside prose describing what the model is NOT) so the plan's grep gate — which does not special-case docstrings — passes literally while still documenting model provenance"
metrics:
  duration: 15min
  completed: 2026-08-21
---

# Phase 03 Plan 03: PPAN Direct-OLS System, Diesel-USD and FX Naive Forecasts Summary

Implemented `forecast_ppan_var_system` (twelve independent per-horizon OLS regressions, the
actual Phase 2 winner rather than the iterative VAR variant 03-RESEARCH.md mis-documented),
plus `forecast_diesel_usd` and `forecast_fx` (both Naive, banded by their own distinct
auxiliary ARIMA standard-error orders).

## What Was Built

- `forecast_ppan_var_system(history, horizon)` in `app/app/forecasting.py`: builds a design
  frame of `ppan` + `PPAN_SYSTEM_MEMBERS` (`hdan`, `baltic_an`, `urals`, at price levels) plus
  `ppan_lag1..3`. For each h in 1..horizon, fits `sm.OLS(ppan.shift(-h), sm.add_constant(features))`
  on the dropna-joined frame, skipping (and later raising on) any horizon with fewer than 10
  usable rows. Predicts by pushing the single last-observed feature row through all fitted
  models, reindexing each to `model.params.index` with `fill_value=0.0`. Bands with
  `_arima_forecast_se(ppan, ARIMA_SE_ORDER["ppan"], horizon)`. Returns no `hdan` key and
  computes no HDAN forecast — `forecast_hdan`'s SARIMAX output remains HDAN's sole authority.
- `forecast_diesel_usd(history, horizon)` and `forecast_fx(history, horizon)`: both follow the
  three-line Naive + ARIMA-SE-band shape (`_naive_forecast` for base, `_arima_forecast_se` with
  each series' own `ARIMA_SE_ORDER` entry for the band), kept as separate named functions per
  D-07 even though the point-forecast model is identical.
- 12 new tests added to `app/tests/test_forecasting.py`: PPAN shape/finiteness, the
  `urals`-perturbation sensitivity test (`test_ppan_responds_to_system_members`), PPAN
  band-equals-SE exactness, PPAN missing-member error path; Diesel/FX hold-last-value,
  `test_diesel_and_fx_use_distinct_volatility_orders` (the direct FCST-04 evidence), band
  widening for both, and missing-column error paths for both.

## Verification

- `cd app && .venv/bin/python -m pytest tests/ -x -q` — 55 passed (41 in `test_forecasting.py`,
  up from 29 pre-plan / 19 after 03-02).
- `grep -v '^\s*#' app/app/forecasting.py | grep -c "tsa.api.VAR\|from statsmodels.tsa.api import VAR\|VAR("` → 0.
- `grep -v '^\s*#' app/app/forecasting.py | grep -c "sm.OLS"` → 2.
- `grep -c "select_order\|auto_arima" app/app/forecasting.py` → 0.
- `grep -v '^\s*#' app/app/forecasting.py | grep -c "ARIMA_SE_ORDER\["` → 7.
- `test_ppan_responds_to_system_members` confirms perturbing the final `urals` observation by
  +20% changes at least one value in the returned PPAN base path by more than 1e-6.
- `test_ppan_var_system_band_equals_arima_se` confirms the bull/base half-width equals
  `_arima_forecast_se(ppan, (0,1,0), 12)` exactly (rel=1e-9).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reworded PPAN docstring to avoid literal `VAR(` / `tsa.api.VAR` substrings**
- **Found during:** Task 1, running the grep source-assertion gate.
- **Issue:** The initial docstring explained the model IS NOT a `statsmodels.tsa.api.VAR`
  object and IS NOT the rejected `VAR(lag=1)` iterative variant — but the plan's own grep
  gate (`grep -v '^\s*#' ... | grep -c "tsa.api.VAR\|...\|VAR("`) only excludes `#`-comment
  lines, not docstrings, so this correctness-motivated prose caused a false positive (count 2
  instead of the required 0).
- **Fix:** Reworded the docstring to describe the same facts (not a `statsmodels.tsa.api`
  autoregressive system object; not the iterative autoregressive-lag-1 runner-up) without
  using the literal substrings the gate matches on.
- **Files modified:** app/app/forecasting.py
- **Commit:** 0b8bc13

## Known Stubs

None.

## Threat Flags

None — this plan's threat register items (T-03-07, T-03-08, T-03-09) were mitigated exactly
as specified: skipped horizons collected and raised as `InsufficientHistoryError` naming them
(never NaN-filled), `test_ppan_responds_to_system_members` guards against a univariate
substitution, and the grep gate confirms zero `VAR(` occurrences.

## Self-Check: PASSED

- FOUND: app/app/forecasting.py (contains `def forecast_ppan_var_system`, `def forecast_diesel_usd`, `def forecast_fx`)
- FOUND: app/tests/test_forecasting.py (41 tests in this file, all passing)
- FOUND commit 0b8bc13: feat(03-03): implement PPAN Direct-OLS system, Diesel-USD and FX naive forecasts
