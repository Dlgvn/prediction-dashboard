---
phase: 02-model-research-backtesting
plan: 01
subsystem: research-infra
tags: [sqlite, pandas, statsmodels-agnostic-harness, pytest, walk-forward, backtesting]

# Dependency graph
requires:
  - phase: 01-app-skeleton-data-layer
    provides: PriceRow SQLite schema (app/reflex.db, 16-column wide monthly table)
provides:
  - "backend_research/db_loader.py: load_price_history() reading PriceRow from SQLite (read-only)"
  - "backend_research/walk_forward.py: model-agnostic rolling-origin backtest harness with LeakageError guard"
  - "backend_research/test_walk_forward.py: leakage-prevention unit tests (6 passing)"
  - "backend_research/ENV.md: confirmed installed versions vs STACK.md pins"
affects: [02-02, 02-03, 02-04, 02-05, 02-06, 02-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single shared walk_forward_backtest() harness reused by every model-family runner script (no per-script re-slicing)"
    - "Read-only SQLite URI connection (file:...?mode=ro) for research scripts reading app/reflex.db"

key-files:
  created:
    - backend_research/db_loader.py
    - backend_research/walk_forward.py
    - backend_research/test_walk_forward.py
    - backend_research/ENV.md
  modified: []

key-decisions:
  - "Confirmed environment is pandas 2.2.3 / scikit-learn 1.7.2 / statsmodels 0.14.6 / pytest 9.0.2 — pandas/sklearn lag behind STACK.md's aspirational pins; code written to pandas 2.2.3 semantics (no reliance on pandas-3.0-only copy-on-write default)."
  - "LeakageError raised eagerly both for the degenerate min_train>=len(series) case and per-origin if train window max date is not strictly before the first forecast target date."

patterns-established:
  - "Pattern: walk-forward harness stays model-agnostic (zero statsmodels/sklearn/arch imports) so all Phase 2 runner scripts (naive/ETS, ARIMA/SARIMAX, VAR, GARCH, ML) share one slicing implementation."

requirements-completed: [FCST-07]

# Metrics
duration: 12min
completed: 2026-08-21
---

# Phase 02 Plan 01: SQLite Data Loader & Walk-Forward Harness Summary

**SQLite-backed PriceRow loader plus a shared, leakage-guarded rolling-origin backtest harness (walk_forward_backtest/mape_by_horizon/single_holdout_mape) that every Phase 2 model runner will import.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-21T05:52:07Z
- **Completed:** 2026-08-21T05:54:28Z
- **Tasks:** 2 completed
- **Files modified:** 4 (all created)

## Accomplishments
- `load_price_history()` reads all 164 rows / 16 columns directly from `app/reflex.db` via a read-only SQLite URI connection, no CSV re-parsing
- `walk_forward_backtest()` provides one shared, tested rolling-origin slicing implementation with a load-bearing `LeakageError` guard (not a comment) that fires before any fit if the training window would touch the forecast target
- `mape_by_horizon()` and `single_holdout_mape()` give every future runner script both the D-07 walk-forward metric and a D-07-comparability figure against `backend_research/REPORT.md`'s prior single-holdout baselines
- `ENV.md` resolves RESEARCH.md Open Question #2: pandas 2.2.3 / scikit-learn 1.7.2 installed, not the STACK.md-pinned 3.0.5/1.9.0 — documented so later plans write pandas-2.x-safe code

## Task Commits

1. **Task 1: Record the actual environment and add the SQLite data loader** - `64e2e79` (feat)
2. **Task 2: Write leakage tests, then the shared walk-forward harness** - `c267b5b` (test, RED) + `0dcb6de` (feat, GREEN)

**Plan metadata:** pending (this commit)

_Note: Task 2 is a TDD task — RED (failing tests) and GREEN (implementation) committed separately._

## Files Created/Modified
- `backend_research/ENV.md` - installed vs. pinned package versions table
- `backend_research/db_loader.py` - `load_price_history()`, `pct_change_frame()`, `TARGETS`, `PREDICTORS`, `DB_PATH`
- `backend_research/walk_forward.py` - `walk_forward_backtest()`, `mape_by_horizon()`, `single_holdout_mape()`, `LeakageError`
- `backend_research/test_walk_forward.py` - 6 leakage/correctness unit tests

## Decisions Made
- Kept pandas/scikit-learn version mismatch as a documented fact rather than upgrading packages mid-plan (plan explicitly forbids installing/upgrading to force a match) — flagged in ENV.md for downstream plans.
- `walk_forward_backtest` records `origin_date` as the *last observed* period (`series.index[origin - 1]`), matching the plan's interface spec and RESEARCH.md Pattern 1's convention.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected test_mape_by_horizon's own expected-value arithmetic during GREEN**
- **Found during:** Task 2 (TDD GREEN phase)
- **Issue:** Test asserted `result.loc[1] == 15.0` but the hand-built fixture (forecasts 110/90 vs actual 100/100) actually yields a mean APE of 10.0, not 15.0 — the test's own expected value was arithmetically wrong, not the implementation.
- **Fix:** Corrected the test assertion to `10.0` after confirming `mape_by_horizon`'s groupby-mean-APE logic was correct by hand-calculation.
- **Files modified:** backend_research/test_walk_forward.py
- **Verification:** `pytest test_walk_forward.py -x -q` → 6 passed
- **Committed in:** 0dcb6de (Task 2 GREEN commit)

**2. [Rule 1 - Bug] Rephrased a walk_forward.py docstring line to avoid a false-positive source-assertion match**
- **Found during:** Task 2 acceptance-criteria verification
- **Issue:** The module docstring mentioned "statsmodels/sklearn/arch" by name to explain the model-agnostic design, which caused the required grep check (`grep -cE "statsmodels|sklearn|arch"` == 0) to fail even though no actual import exists.
- **Fix:** Reworded the docstring to "no model-fitting-library imports here" — same meaning, passes the source assertion.
- **Files modified:** backend_research/walk_forward.py
- **Verification:** `grep -v '^#' backend_research/walk_forward.py | grep -cE "statsmodels|sklearn|arch"` → 0
- **Committed in:** 0dcb6de (Task 2 GREEN commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - bug fixes within Task 2, no scope creep)
**Impact on plan:** Both fixes were self-contained corrections needed to meet the plan's own stated acceptance criteria; no architectural or behavioral changes.

## Issues Encountered
None beyond the two auto-fixed items above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `db_loader.py` and `walk_forward.py` match the plan's `<interfaces>` contract exactly; plans 02-02 through 02-07 (per-model-family runners) can import both without reading source.
- No runner script exists yet — intentional per this plan's scope; Phase 2's model-fitting work starts in the next plan.
- `arch` package (GARCH) is not yet installed — flagged [SUS] by slopcheck in 02-RESEARCH.md as a name-similarity false positive; the plan that adds GARCH must still route its install through a `checkpoint:human-verify` gate per protocol.

---
*Phase: 02-model-research-backtesting*
*Completed: 2026-08-21*

## Self-Check: PASSED

All created files verified present; all task commit hashes (64e2e79, c267b5b, 0dcb6de) verified in git log.
