---
phase: 21-weekly-forecasting-module
plan: 01
subsystem: forecasting
tags: [statsmodels, sarimax, pandas, pytest, weekly-cadence]

# Dependency graph
requires:
  - phase: 17-weekly-forecast-re-research-spike
    provides: frozen weekly_sarimax_ets.json winning constants (SARIMAX(0,1,0)+BalticAN(exog, duplicate), 7.25%/6.96% MAPE h=4)
  - phase: 19-weekly-schema-ingestion
    provides: WeeklyPriceRow schema (date/hdan/ppan/baltic_an/fx_rate) this module's history DataFrame mirrors
provides:
  - forecast_weekly_hdan(history, horizon) and forecast_weekly_ppan(history, horizon) callable functions
  - shared _forecast_weekly_sarimax_exog engine (SARIMAX(0,1,0) + unlagged baltic_an exog)
  - MAX_HORIZON_WEEKLY=5, MIN_HISTORY_ROWS_WEEKLY=104, WEEKLY_SARIMAX_ORDER, WEEKLY_EXOG_COLUMN, WEEKLY_ARIMA_SE_ORDER constants
  - synthetic_weekly_history pytest fixture (130-row weekly-cadence DataFrame)
affects: [22-weekly-granularity-toggle-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Weekly forecasting mirrors monthly's shared-engine/thin-wrapper pattern (forecast_weekly_hdan/forecast_weekly_ppan delegate to _forecast_weekly_sarimax_exog exactly as forecast_hdan's monthly counterpart does), but the weekly SARIMAX exog convention is UNLAGGED/concurrent baltic_an, not per-predictor lagged like HDAN_PREDICTOR_LAGS -- structurally kept as a separate constant set (WEEKLY_* prefix) so the two conventions can never be accidentally cross-wired."

key-files:
  created: []
  modified:
    - app/app/forecasting.py
    - app/tests/conftest.py
    - app/tests/test_forecasting.py

key-decisions:
  - "Baltic AN is passed to _forecast_predictor as the RAW history[WEEKLY_EXOG_COLUMN] column with no .shift() anywhere in the weekly path -- verified by a monkeypatch spy test (test_forecast_weekly_hdan_uses_unlagged_baltic_an) that captures the exact series argument and asserts it equals the unmodified column, and confirmed load-bearing by temporarily mutating WEEKLY_EXOG_COLUMN to 'hdan' and observing the test fail."
  - "_require_weekly_horizon is a new, additive validator (not a modification of _require_series) because _require_series's horizon check is hardwired to MAX_HORIZON=12, which would silently accept an invalid weekly horizon like 8."
  - "Weekly section appended at the end of forecasting.py behind a banner comment, after forecast_all/_to_rows, to keep the diff purely additive and trivially auditable via git diff --numstat."

patterns-established:
  - "Pattern: WEEKLY_-prefixed constants (WEEKLY_SARIMAX_ORDER, WEEKLY_EXOG_COLUMN, WEEKLY_ARIMA_SE_ORDER, MAX_HORIZON_WEEKLY, MIN_HISTORY_ROWS_WEEKLY) namespace weekly-cadence values completely separately from monthly's ARIMA_SE_ORDER/MAX_HORIZON/MIN_HISTORY_ROWS, preventing any accidental sharing between the two cadences' validation floors/ceilings."

requirements-completed: []

# Metrics
duration: 25min
completed: 2026-09-02
---

# Phase 21 Plan 01: Weekly Forecasting Module Summary

**Added `forecast_weekly_hdan`/`forecast_weekly_ppan` to `app/app/forecasting.py`, transcribing Phase 17's frozen SARIMAX(0,1,0)+BalticAN(exog, unlagged) constants (7.25%/6.96% MAPE h=4) via one shared engine, reusing existing `_arima_forecast_se`/`_apply_se_spread`/`_forecast_predictor` verbatim with zero changes to the monthly module.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-09-01T23:48:00Z
- **Completed:** 2026-09-02T00:13:17Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `forecast_weekly_hdan`/`forecast_weekly_ppan` and shared `_forecast_weekly_sarimax_exog` engine added to `app/app/forecasting.py`, using `baltic_an` at its unlagged/concurrent value as the sole exog driver -- the critical research finding this plan encodes as executable code and a regression test, not just a comment.
- `MAX_HORIZON_WEEKLY=5`/`MIN_HISTORY_ROWS_WEEKLY=104` enforced via a dedicated `_require_weekly_horizon` validator plus `_require_series`'s existing history-floor check.
- 12 new weekly-specific tests added (shape/finite, ordering, band widening, unlagged-exog regression guard, horizon ceiling, history floor, missing-column error, SE-order values, h=1 SE-band wiring), full app test suite grew from 50 to 380 tests total, all green.
- Zero deletions in `app/app/forecasting.py` and `app/tests/conftest.py` across both task commits (confirmed via `git diff --numstat`) -- the monthly module is byte-for-byte unchanged.

## Task Commits

Each task was committed atomically:

1. **Task 1: Weekly constants + shared SARIMAX+exog engine + forecast_weekly_hdan/forecast_weekly_ppan** - `dd75758` (feat)
2. **Task 2: Weekly HDAN/PPAN test coverage** - `3f98fa8` (test)

## Files Created/Modified
- `app/app/forecasting.py` - Added weekly section: `WEEKLY_SARIMAX_ORDER`, `WEEKLY_EXOG_COLUMN`, `WEEKLY_ARIMA_SE_ORDER`, `MAX_HORIZON_WEEKLY`, `MIN_HISTORY_ROWS_WEEKLY` constants; `_require_weekly_horizon`, `_forecast_weekly_sarimax_exog` helpers; `forecast_weekly_hdan`, `forecast_weekly_ppan` public functions
- `app/tests/conftest.py` - Added `synthetic_weekly_history` fixture (130-row weekly-cadence DataFrame with hdan/ppan/baltic_an/fx_rate, well above `MIN_HISTORY_ROWS_WEEKLY`)
- `app/tests/test_forecasting.py` - Added 12 weekly HDAN/PPAN tests covering shape, ordering, band widening, unlagged-exog regression guard, horizon/history error paths, and SE-band wiring

## Decisions Made
- Kept the weekly section fully additive (append-only at end of file behind a banner comment) rather than interleaving with monthly functions, to make the "0 deletions" acceptance criterion trivially true and auditable.
- Did not introduce a `WEEKLY_PREDICTOR_LAGS` dict (verified absent via grep) -- the plan's core finding is that the weekly exog convention has no lag concept at all, so adding an unused lag dict would misleadingly imply otherwise.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' `<action>` code blocks were transcribed verbatim into `app/app/forecasting.py`, `app/tests/conftest.py`, and `app/tests/test_forecasting.py`.

## Issues Encountered

None. All verification commands passed on first run, including the deliberate "break `WEEKLY_EXOG_COLUMN` to `hdan`, confirm the unlagged-exog test fails, then revert" load-bearing-test check from Task 2's acceptance criteria.

## Verification Commands Run

- `cd app && .venv/Scripts/python.exe -c "from app.forecasting import forecast_weekly_hdan, forecast_weekly_ppan, MAX_HORIZON_WEEKLY, MIN_HISTORY_ROWS_WEEKLY, WEEKLY_SARIMAX_ORDER, WEEKLY_EXOG_COLUMN, WEEKLY_ARIMA_SE_ORDER; print('ok')"` -> `ok`
- `cd app && .venv/Scripts/python.exe -m pytest tests/test_forecasting.py -q -k weekly` -> `12 passed`
- `cd app && .venv/Scripts/python.exe -m pytest tests/ -q` -> `380 passed` (baseline was 50 in `app/tests/test_forecasting.py` alone before this plan; full suite includes other test files)
- `git diff --numstat HEAD~2 -- app/app/forecasting.py app/tests/conftest.py app/tests/test_forecasting.py` -> `101 0`, `30 0`, `106 0` (zero deletions across all three files)
- `grep -c "WEEKLY_PREDICTOR_LAGS" app/app/forecasting.py` -> `0`
- `grep -c "HDAN_PREDICTOR_LAGS" app/app/forecasting.py` -> `4` (3 pre-existing monthly usages unchanged + 1 new docstring mention in `_forecast_weekly_sarimax_exog` explicitly documenting that it is NOT imported/applied in the weekly path)
- `grep -c "def test_forecast_weekly_hdan_uses_unlagged_baltic_an" app/tests/test_forecasting.py` -> `1`
- Temporarily changed `WEEKLY_EXOG_COLUMN` from `"baltic_an"` to `"hdan"` and reran the unlagged-exog test -> failed as expected (proves the test is load-bearing), then reverted; `git diff` confirmed a clean revert.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`forecast_weekly_hdan`/`forecast_weekly_ppan` are callable with a plain `pd.DataFrame` (no Reflex import, no `state.py`/UI touch), ready for Phase 22's granularity-toggle UI to consume identically to the existing monthly `forecast_hdan`/`forecast_ppan_var_system` functions. No blockers.

---
*Phase: 21-weekly-forecasting-module*
*Completed: 2026-09-02*

## Self-Check: PASSED

- FOUND: app/app/forecasting.py
- FOUND: app/tests/conftest.py
- FOUND: app/tests/test_forecasting.py
- FOUND: dd75758
- FOUND: 3f98fa8
