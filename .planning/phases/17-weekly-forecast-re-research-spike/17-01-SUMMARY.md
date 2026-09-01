---
phase: 17-weekly-forecast-re-research-spike
plan: 01
subsystem: research
tags: [pandas, data-loader, dedup, path-fix, backend_research]

# Dependency graph
requires:
  - phase: 16-model-research
    provides: backend_research/ scripting conventions (flat modules, sys.path shims, house test style)
provides:
  - Working backend_research/data_loader.py on Windows (repo-root-relative paths)
  - backend_research/weekly/baltic_an_dedup.py measured Baltic-AN duplicate/independent comparison
  - Frozen results/baltic_an_dedup.json verdict for Plan 02's SARIMAX+exog driver-set variant
affects: [17-02-weekly-model-runs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_REPO_ROOT = Path(__file__).resolve().parent.parent for repo-root-relative CSV paths (mirrors db_loader.py's DB_PATH)"
    - "verdict_from_stats() factored out as a pure function so a duplicate/independent decision is unit-testable on synthetic fixtures, not hardwired"
    - "Frozen JSON verdict pattern: script writes a measured result to results/*.json once, downstream plans consume the frozen file rather than re-deriving"

key-files:
  created:
    - backend_research/weekly/baltic_an_dedup.py
    - backend_research/weekly/test_baltic_an_dedup.py
    - backend_research/results/baltic_an_dedup.json
  modified:
    - backend_research/data_loader.py

key-decisions:
  - "Baltic-AN columns verdict: DUPLICATE (corr=0.983, MAPE=2.70%, n=206) — AN Data.csv's 'Baltic AN' is the preferred single exogenous predictor; BalticAN_wk should not be added as a separate driver"
  - "verdict_from_stats thresholds: corr > 0.9 AND mape < 10.0 => duplicate, else independent (strict boundary — exactly-at-threshold falls to independent)"

patterns-established:
  - "Path(__file__)-relative module constants for all backend_research CSV/JSON I/O, no hardcoded absolute paths"

requirements-completed: [WKLY-01]

# Metrics
duration: 12min
completed: 2026-09-01
---

# Phase 17 Plan 01: Data Loader Path Fix and Baltic-AN Dedup Resolution Summary

**Patched data_loader.py's hardcoded macOS paths to repo-root-relative constants (fixing a live FileNotFoundError on Windows) and resolved the Baltic-AN dedup question with a measured correlation/MAPE comparison (verdict: duplicate, corr=0.983), frozen to results/baltic_an_dedup.json for Plan 02.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-09-01T02:46:00Z (approx)
- **Completed:** 2026-09-01T02:58:17Z
- **Tasks:** 2
- **Files modified:** 4 (1 patched, 3 created)

## Accomplishments
- `backend_research/data_loader.py`'s three CSV path constants now resolve via `Path(__file__).resolve().parent.parent`, matching `db_loader.py`'s existing `DB_PATH` pattern — all loader functions (`load_an_monthly`, `load_diesel_monthly`, `load_an_weekly`, `load_weekly_drivers`, `merged_weekly`, `merged_monthly`) now run successfully on this Windows machine with unchanged row counts (48/77/206/711).
- Built `backend_research/weekly/baltic_an_dedup.py`, which merges `AN Data.csv`'s `Baltic AN` column and `AN price weekly.csv`'s `BalticAN_wk` column via `merge_asof` (nearest, ±3 days), computes real correlation and mean-absolute-percentage-difference, and derives a `"duplicate"`/`"independent"` verdict through the pure, unit-tested `verdict_from_stats()` function.
- Measured result: **n=206, corr=0.983, mean_abs_pct_diff=2.70%, verdict=duplicate**. Preferred column: `AN Data.csv (Baltic AN)`.
- Verdict frozen to `backend_research/results/baltic_an_dedup.json`, confirmed byte-identical across reruns (deterministic, no wall-clock content).
- 6 new tests in `test_baltic_an_dedup.py` prove the verdict branches correctly on synthetic near-duplicate, synthetic independent, boundary, and "high-corr-but-high-MAPE" fixtures, plus validate the real-data comparison and the frozen-JSON contract. Full `backend_research/` suite: 30/30 passing (24 pre-existing + 6 new).

## Task Commits

1. **Task 1: Patch data_loader.py to repo-root-relative paths** - `87d1233` (fix)
2. **Task 2: Baltic-AN dedup comparison script and non-hardwired verdict tests** - `35fef06` (feat)

**Plan metadata:** (this commit, pending)

## Files Created/Modified
- `backend_research/data_loader.py` - Three hardcoded macOS-absolute CSV path constants replaced with `_REPO_ROOT`-relative `Path(__file__)` constants; no parsing/cleaning logic touched.
- `backend_research/weekly/baltic_an_dedup.py` - New: `compare_baltic_an()`, `verdict_from_stats()`, `main()`, writes frozen JSON to `results/baltic_an_dedup.json`.
- `backend_research/weekly/test_baltic_an_dedup.py` - New: 6 tests covering synthetic duplicate/independent/boundary cases, real-data comparison, and frozen JSON contract.
- `backend_research/results/baltic_an_dedup.json` - New: frozen verdict record (`{"n": 206, "corr": 0.983, "mean_abs_pct_diff": 2.697, "verdict": "duplicate", "preferred_column": "AN Data.csv (Baltic AN)", "duplicate_corr_threshold": 0.9, "duplicate_mape_threshold": 10.0}`).

## Decisions Made
- Baltic-AN columns are a **duplicate** signal (corr=0.983, MAPE=2.70%, well past the 0.9/10.0 thresholds) — Plan 02's SARIMAX+exog driver-set variant should use `AN Data.csv`'s `Baltic AN` column only, not both.
- Thresholds (`corr > 0.9 and mape < 10.0`) chosen as named constants per the plan's explicit "not magic numbers inline" instruction, with the boundary case (exactly at threshold) resolving to `"independent"` (strict `>`/`<`, not `>=`/`<=`).

## Deviations from Plan

None - plan executed exactly as written. Added one extra test beyond the plan's minimum (`test_verdict_high_corr_but_high_mape_is_independent`) to more thoroughly exercise the "both conditions required" branch of `verdict_from_stats`; this is within the plan's stated behavior contract, not a deviation.

## Issues Encountered

A cosmetic `DeprecationWarning` about NumPy's "generic" timedelta unit appears from `pd.Timedelta(days=3)` under this pandas 2.2.3/numpy combination — pre-existing pandas/numpy interaction, not introduced by this plan's code, does not affect correctness, and was left as-is per the scope-boundary rule (out-of-scope pre-existing warning).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `data_loader.py` is now fully functional on this Windows machine; Plan 02's weekly model runs can call `load_an_weekly()`/`load_weekly_drivers()`/`merged_weekly()` without any path errors.
- `results/baltic_an_dedup.json` is frozen and ready for Plan 02 to consume as the documented choice: use `AN Data.csv`'s `Baltic AN` column, not `BalticAN_wk`, in the SARIMAX+exog driver-set variant.
- No blockers.

---
*Phase: 17-weekly-forecast-re-research-spike*
*Completed: 2026-09-01*

## Self-Check: PASSED

All created files and both task commits verified present.
