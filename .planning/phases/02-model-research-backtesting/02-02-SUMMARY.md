---
phase: 02-model-research-backtesting
plan: 02
subsystem: forecasting-research
tags: [statsmodels, granger-causality, cointegration, VAR, VECM, scipy]

requires:
  - phase: 02-model-research-backtesting
    provides: "db_loader.py (SQLite-backed TARGETS/PREDICTORS loader) and walk_forward.py harness from plan 02-01"
provides:
  - "causality_screen.py: Granger F-test sweep + Engle-Granger cointegration sweep over the full 12-predictor set, no intuition-based pre-filtering"
  - "results/causality_screen.json: 180 target/predictor/lag records with F/p/n/tier"
  - "results/cointegration.json: 60 target/predictor level-pair records with t_stat/p/cointegrated"
  - "shortlist_for(target) API bounding downstream walk-forward search space to <=6 data-derived predictors"
  - "VECM_CANDIDATES module constant flagging cointegrated target pairs for plan 02-05"
affects: ["02-04", "02-05", "02-06"]

tech-stack:
  added: []
  patterns:
    - "Two-framing predictor screen: Granger causality on stationary pct-change data vs. Engle-Granger cointegration on raw levels, kept as separate sweep functions rather than conflated"
    - "shortlist_for() as the single chokepoint downstream runners use instead of re-implementing predictor selection"

key-files:
  created:
    - backend_research/causality_screen.py
    - backend_research/results/causality_screen.json
    - backend_research/results/cointegration.json
  modified: []

key-decisions:
  - "Cross-checked the manual incremental F-test against statsmodels grangercausalitytests only at lag=1, since statsmodels' ssr_ftest at higher lags is a joint test over lags 1..k while ours is a single-lag-added test — the two only test the same hypothesis at lag=1, so higher-lag divergence is expected, not a bug"
  - "fx_rate was NOT special-cased: against the expanded 12-predictor + cross-target set, fx_rate now shows several p<0.10 predictors (diesel_usd_ton, natural_gas_uk, urea_china, urea_black_sea, natural_gas_netherlands, etc.), overturning the prior session's 'FX has no predictors' finding under the broader D-05 predictor set"
  - "No target-pair cointegration found at p<0.05 (checked hdan/ppan/diesel_usd_ton/fx_rate combinations) — VECM_CANDIDATES is empty; plan 02-05 should proceed with plain VAR, not VECM"

requirements-completed: [FCST-07]

duration: 25min
completed: 2026-08-21
---

# Phase 02 Plan 02: Predictor Causality & Cointegration Screen Summary

**Granger causality (F-test, lags 1-3) and Engle-Granger cointegration sweep across all 4 targets x 12 predictors + cross-targets, with a capped data-derived shortlist API and an empty VECM candidate list.**

## Performance

- **Duration:** 25 min
- **Tasks:** 2
- **Files modified:** 3 (1 script, 2 result JSONs)

## Accomplishments
- Full D-04/D-05 compliant Granger sweep: 180 records covering every target x (12 predictors + 3 cross-targets) x lag(1-3) combination, no intuition-based exclusions
- fx_rate's "no predictor" finding from the prior session was explicitly re-tested (not assumed) against the expanded predictor set — it now has several p<0.10/p<0.05 candidates
- Engle-Granger cointegration sweep on raw levels (60 records) with explicit VECM candidacy reporting — no target pairs cointegrated at p<0.05, so VECM_CANDIDATES is empty and printed as "No cointegrated target pairs found"
- `shortlist_for(target)` gives downstream runners (02-04/02-05/02-06) a bounded, auditable predictor set (<=6, capped for the walk-forward compute-explosion concern in RESEARCH.md Pitfall 2)

## Task Commits

1. **Task 1: Granger sweep across the full 12-predictor set (D-04/D-05)** - `b355081` (feat)
2. **Task 2: Engle-Granger cointegration sweep on levels and the VECM flag** - `9e9af44` (feat)

**Plan metadata:** pending (this commit)

## Files Created/Modified
- `backend_research/causality_screen.py` - Granger F-test sweep, cointegration sweep, shortlist_for(), VECM_CANDIDATES
- `backend_research/results/causality_screen.json` - 180 target/predictor/lag records with F/p/n/tier
- `backend_research/results/cointegration.json` - 60 target/predictor level-pair records with t_stat/p/cointegrated

## Decisions Made
- Cross-check with statsmodels' `grangercausalitytests` restricted to lag=1 only, since the library's joint multi-lag F-test and our single-lag incremental F-test are mathematically different hypotheses at lag>1 (documented as a code comment in `causality_screen.py`, not a bug)
- Kept the p<0.10 tier consistent with prior art (`causality_matrix.py`) per RESEARCH.md Assumption A3, reporting both p05/p10 tiers rather than a single hard cutoff

## Deviations from Plan

None - plan executed exactly as written. One design ambiguity (which lag(s) to attach the statsmodels crosscheck to) was resolved by narrowing to lag=1 only, since that's the only lag where the two Granger test formulations are directly comparable — this is a clarification of an underspecified detail, not a deviation from the plan's stated acceptance criteria (the hdan/baltic_an record still carries `p_statsmodels_crosscheck` within 0.05 of `p`, exactly as required).

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `shortlist_for(target)` is ready for plans 02-04 (ARIMA/SARIMAX/Holt-Winters), 02-05 (VAR/VECM), and 02-06 (ML baseline) to import and bound their predictor search space
- `VECM_CANDIDATES` (empty list) tells 02-05 to skip VECM and use plain VAR
- fx_rate's revised predictor set (diesel_usd_ton, natural_gas_uk, urea_china, urea_black_sea, natural_gas_netherlands) should feed 02-04/02-05's FX model candidates instead of falling back to AR-only, since the expanded screen found real signal this session

---
*Phase: 02-model-research-backtesting*
*Completed: 2026-08-21*

## Self-Check: PASSED
