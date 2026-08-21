---
phase: 03-forecasting-module-derived-series
plan: 02
subsystem: forecasting
tags: [sarimax, exog, garch, hdan]
requires:
  - 03-01: forecasting primitives (_forecast_predictor, _apply_garch_spread, _require_series, HDAN constants)
provides:
  - forecast_hdan(history, horizon) -> {base, bull, bear}
  - _build_future_exog(history, horizon) -> pd.DataFrame
affects:
  - app/app/forecasting.py
tech-stack:
  added: []
  patterns:
    - "lag-aware future exog: extended = concat([observed, forecast_path]); index at t_last + h - lag"
key-files:
  created: []
  modified:
    - app/app/forecasting.py
    - app/tests/test_forecasting.py
decisions:
  - "Ammonia's lag-3 predictor uses the last 3 observed actuals for future steps 1-3, only switching to the forecasted path at step 4+ — 03-RESEARCH.md Pattern 1 was wrong to generalize the lag-1 case to all predictors"
  - "forecast_hdan reproduces Phase 2's exact SARIMAX fit kwargs (enforce_stationarity=False, enforce_invertibility=False) with an inline comment forbidding changes"
metrics:
  duration: 20min
  completed: 2026-08-21
---

# Phase 03 Plan 02: HDAN SARIMAX+exog Forecast with GARCH Band Summary

Implemented `forecast_hdan`, HDAN's winning SARIMAX(0,1,0)+six-lagged-exog model with a
GARCH-derived bull/bear band, driven by a lag-aware future-exog constructor that correctly
handles ammonia's non-standard lag-3 predictor relationship.

## What Was Built

- `_build_future_exog(history, horizon)` in `app/app/forecasting.py`: for each of HDAN's six
  predictors, forecasts the predictor forward via `_forecast_predictor`, concatenates it onto
  the observed tail, and indexes into that combined array at `t_last + h - lag_p` for each
  future step `h`. This correctly reproduces the fit-time `shift(lag)` convention from
  `backend_research/run_arima_sarimax_wf.py::build_sarimax_records`. Columns are reindexed to
  `HDAN_PREDICTORS` order before returning.
- `forecast_hdan(history, horizon)` in `app/app/forecasting.py`: fits
  `sm.tsa.SARIMAX(y, exog=x, order=(0,1,0), enforce_stationarity=False,
  enforce_invertibility=False)` on history with lag-shifted exog (dropna-joined, guarded
  against under-`MIN_HISTORY_ROWS` shrinkage), forecasts with `_build_future_exog`'s future
  exog frame, and applies `_apply_garch_spread` to the SARIMAX point forecast for the
  bull/bear band.
- 8 new tests added to `app/tests/test_forecasting.py`: future-exog shape/order/no-NaN,
  lag-1 predictor correctness, the ammonia lag-3 regression test
  (`test_future_exog_respects_ammonia_lag_3`), short-history error path, and
  `forecast_hdan` shape/finiteness, GARCH unit-conversion pinning, bull>base>bear ordering,
  band-widening (FCST-05), and missing-column error handling.

## Verification

- `cd app && python -m pytest tests/ -q` — 45 passed (19 in `test_forecasting.py`, up from 11).
- `grep -v '^\s*#' app/app/forecasting.py | grep -c "HDAN_PREDICTOR_LAGS\["` → 2 (lag consulted).
- `grep -v '^\s*#' app/app/forecasting.py | grep -c "enforce_stationarity=False"` → 1.
- `grep -c "^import arch\|from arch" app/app/forecasting.py` → 0.
- `grep -n "predicted_mean" app/app/forecasting.py` → only inside `forecast_hdan` (line 289)
  and a docstring in `_arima_forecast_se` explaining why it does NOT use `predicted_mean`.
- Half-width at h=1 pinned to `base[0] * 12.532726174302507 / 100` exactly (rel=1e-9) —
  proves the GARCH percent-return unit conversion is correct in both directions.

## Deviations from Plan

None — plan executed as written. The `<planner_correction>` block's ammonia lag-3 guidance
was followed exactly as specified (not the flawed 03-RESEARCH.md Pattern 1 generalization).

## Known Stubs

None.

## Threat Flags

None — this plan's threat register items (T-03-04, T-03-05, T-03-06) were all mitigated
exactly as specified: `MIN_HISTORY_ROWS` post-join guard, ammonia lag-3 regression test, and
the GARCH unit-conversion pin test.

## Self-Check: PASSED

- FOUND: app/app/forecasting.py (contains `def forecast_hdan`, `def _build_future_exog`)
- FOUND: app/tests/test_forecasting.py (19 tests, all passing)
- FOUND commit a42542d: feat(03-02): add lag-aware future-exog constructor for HDAN
- FOUND commit 090d9f4: feat(03-02): implement forecast_hdan with SARIMAX+exog and GARCH band
