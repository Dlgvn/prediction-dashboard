---
phase: 17-weekly-forecast-re-research-spike
plan: 02
subsystem: research
tags: [statsmodels, sarimax, ets, walk-forward, backend_research, weekly]

# Dependency graph
requires:
  - phase: 17-01
    provides: repo-root-relative data_loader.py paths; frozen backend_research/results/baltic_an_dedup.json verdict (duplicate)
provides:
  - Weekly-cadence SARIMAX/ExponentialSmoothing/SARIMAX+exog backtests for HDAN/PPAN via the shared walk_forward_backtest harness
  - backend_research/results/weekly_sarimax_ets.json (6 frozen records)
  - backend_research/REPORT-WEEKLY.md (deterministic go/no-go report)
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Weekly-cadence wrapper classes (_SARIMAXWrapper, _HoltDampedWrapper) re-derived at MIN_TRAIN_WEEKLY=104/HORIZON_WEEKLY=5 rather than importing the monthly-cadence modules -- same pattern as run_arima_sarimax_wf.py/run_baseline_ets.py but never imported directly since MIN_TRAIN/HORIZON differ"
    - "beats_benchmark() factored out as a standalone pure function so tests can exercise the live go/no-go comparison directly, not just observe it embedded in a record"
    - "write_report(records) takes the already-computed records list from run_all() rather than re-running backtests, guaranteeing report/JSON parity and enabling byte-identical reruns"
    - "Deterministic report generation: no wall-clock timestamp/duration anywhere in REPORT-WEEKLY.md, mirroring REPORT-SENTIMENT.md's discipline"

key-files:
  created:
    - backend_research/weekly/run_weekly_sarimax_ets.py
    - backend_research/weekly/test_weekly_sarimax_ets.py
    - backend_research/results/weekly_sarimax_ets.json
    - backend_research/REPORT-WEEKLY.md
  modified: []

key-decisions:
  - "Overall verdict: GO. All 6 candidates (HDAN/PPAN x {SARIMAX, ETS-HoltDamped, SARIMAX+BalticAN(exog,duplicate)}) beat the fixed monthly VAR benchmark (9.49%/10.08%) at h=4: HDAN best 7.25% (SARIMAX+exog), PPAN best 6.96% (SARIMAX+exog)"
  - "SARIMAX+exog variant consumes Plan 01's duplicate verdict: only AN Data.csv's single 'Baltic AN' column used as exog, not both Baltic-AN columns"
  - "WKLY-01/WKLY-02 closed by this report; no weekly UI ships this milestone regardless of the go verdict, per Phase 17's explicit research-only scope -- weekly UI remains deferred to its own future milestone (REQUIREMENTS.md v2.1+)"

patterns-established:
  - "Weekly-cadence model runners live under backend_research/weekly/, importing walk_forward.py/data_loader.py unmodified via a one-directory-up sys.path shim, same as Plan 01's baltic_an_dedup.py"

requirements-completed: [WKLY-01, WKLY-02]

# Metrics
duration: 22min
completed: 2026-09-01
---

# Phase 17 Plan 02: Weekly SARIMAX/ETS Re-Research and Go/No-Go Summary

**Backtested weekly-cadence SARIMAX, Exponential Smoothing, and a Baltic-AN-deduped SARIMAX+exog variant for HDAN/PPAN through the shared walk_forward_backtest harness (MIN_TRAIN=104, HORIZON=5); all 6 candidates beat the fixed monthly VAR benchmark (9.49%/10.08%) at h=4, closing WKLY-01/WKLY-02 with an overall GO verdict, documented in a deterministic REPORT-WEEKLY.md.**

## Performance

- **Duration:** ~22 min
- **Tasks:** 3
- **Files modified:** 4 (all created)

## Accomplishments

- `backend_research/weekly/run_weekly_sarimax_ets.py`: weekly-cadence `_SARIMAXWrapper`/`_HoltDampedWrapper` (seasonal=None), `select_arima_order` (AIC grid search, same p/d/q bounds as the monthly script), `beats_benchmark()` as a standalone live comparison against `BENCHMARK_MAPE = {"HDAN": 9.49, "PPAN": 10.08}`, `load_dedup_choice()` (hard dependency on Plan 01's frozen JSON, fails loudly if missing), `build_univariate_records()` and `build_exog_sarimax_record()` both run through `walk_forward.walk_forward_backtest` (min_train=104, horizon=5, step=1, refit_every=1) — never a hand-rolled loop.
- Measured result: all 6 records beat the benchmark at h=4. HDAN: SARIMAX(0,1,0) 7.32%, ETS-HoltDamped 7.72%, SARIMAX+BalticAN(exog,duplicate) 7.25% (best), vs. benchmark 9.49%. PPAN: SARIMAX(0,1,0) 7.17%, ETS-HoltDamped 7.95%, SARIMAX+BalticAN(exog,duplicate) 6.96% (best), vs. benchmark 10.08%. n_origins=102 for every candidate, failed_origins=0.
- 11 new tests in `test_weekly_sarimax_ets.py`: order-selection bounds, clean 5-step forecasts from both wrapper classes, a smooth-vs-injected-jump synthetic-series pair proving `mape_h4` is computed (not hardcoded), `beats_benchmark` exercised in both directions plus the `None` case, `load_dedup_choice`'s `FileNotFoundError` gate, and the frozen JSON's structural contract (6 records, required keys, correct per-series benchmark) without pinning today's real-world numbers. Full `backend_research/` suite: 41/41 passing (30 pre-existing + 11 new).
- `write_report()` builds `REPORT-WEEKLY.md` from the same `records` list `run_all()` just froze (no second backtest run) with sections: provenance, prior-spike recap, go/no-go-at-a-glance table, computed overall verdict, horizon-matched methodology, Baltic-AN dedup resolution (read fresh from `results/baltic_an_dedup.json`), per-series detail tables, and a WKLY-01/WKLY-02 closing statement. Confirmed byte-identical `results/weekly_sarimax_ets.json` and `REPORT-WEEKLY.md` across two consecutive runs.

## Task Commits

1. **Task 1: Weekly-cadence SARIMAX + ETS wrappers, walk-forward runs, frozen JSON** - `beea58c` (feat)
2. **Task 2: Regression tests -- record shape, computed horizon extraction, non-hardwired go/no-go** - `0cdf6ee` (test)
3. **Task 3: Deterministic REPORT-WEEKLY.md go/no-go generation** - `0fa1625` (docs)

## Files Created/Modified

- `backend_research/weekly/run_weekly_sarimax_ets.py` - New: weekly SARIMAX/ETS wrappers, `run_all()`, `write_report()`, all constants (`MIN_TRAIN_WEEKLY`, `HORIZON_WEEKLY`, `BENCHMARK_MAPE`, `RESULTS_JSON`, `REPORT_PATH`).
- `backend_research/weekly/test_weekly_sarimax_ets.py` - New: 11 tests proving computed (not hardcoded) MAPE and a load-bearing `beats_benchmark` comparison.
- `backend_research/results/weekly_sarimax_ets.json` - New: 6 frozen records (HDAN/PPAN x {SARIMAX, ETS-HoltDamped, SARIMAX+exog}).
- `backend_research/REPORT-WEEKLY.md` - New: deterministic go/no-go report, verified byte-identical across reruns.

## Decisions Made

- Overall verdict computed as GO: at least one record for each of HDAN and PPAN beats the benchmark at h=4 (in fact all 6 do).
- SARIMAX+exog uses only `AN Data.csv`'s "Baltic AN" column (Plan 01's duplicate verdict), never both Baltic-AN columns.
- WKLY-01/WKLY-02 close via this report regardless of the go result; per the phase's explicit research-only scope and REQUIREMENTS.md's v2.1+ deferred section, no weekly UI ships this milestone despite the favorable verdict — weekly UI is deferred to its own future milestone.

## Deviations from Plan

None functionally — plan executed as written. One documentation note: the plan's literal acceptance-criteria grep `grep -vE "^\s*#" ... | grep -cE "VAR\(|OLS\+Granger|backtest_ols"` returns 5 (expected 0) because the module docstring and `write_report()`'s report-text strings legitimately name the prior spike's "VAR(HDAN,PPAN)" benchmark and recap its 10.35%/16.01% figures — content the same task's own instructions require ("state the prior spike's ... rollup figures", "the benchmark being compared against is the fixed monthly-native VAR(HDAN,PPAN) figures"). No `VAR(...)` model is actually called or re-tested anywhere in the file (`walk_forward_backtest` is the only backtest entry point, called 6 times; confirmed by the `grep -c "walk_forward_backtest"` >= 3 criterion passing at 7). Treated as a documented false positive of a blunt heuristic rather than a code issue.

## Issues Encountered

Non-stationary/non-invertible starting-parameter warnings and occasional `ConvergenceWarning` from statsmodels' SARIMAX fits during the tests' small synthetic series (~120-130 rows) — expected for random-walk-like synthetic data with `enforce_stationarity=False`/`enforce_invertibility=False`, does not affect correctness, matches the same warning-suppression pattern (`warnings.filterwarnings("ignore")`) used by the monthly scripts and left as-is.

## User Setup Required

None.

## Next Phase Readiness

- Phase 17 is complete. WKLY-01/WKLY-02 are closed with a GO verdict, but no weekly UI ships this milestone per the phase's explicit scope boundary and REQUIREMENTS.md's v2.1+ deferred section — a future milestone would need its own planning cycle to build the weekly-cadence UI (new table, per-series dispatcher, partial-coverage UX).
- Phase 16 (sentiment) already returned no-go; Phase 18 (sentiment UI) is dropped from the v2.0 milestone per its go-gated dependency. With Phase 17 also complete, the v2.0 milestone's research phases are both closed — Phase 18 does not proceed.
- No blockers.

---
*Phase: 17-weekly-forecast-re-research-spike*
*Completed: 2026-09-01*

## Self-Check: PASSED

Verified below.
