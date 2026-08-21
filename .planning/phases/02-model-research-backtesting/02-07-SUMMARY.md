---
phase: 02-model-research-backtesting
plan: 07
subsystem: model-research
tags: [forecasting, backtest, model-selection, report]
dependency-graph:
  requires: ["02-03", "02-04", "02-05", "02-06"]
  provides: ["winners.json", "REPORT-PHASE2.md", "02-MODEL-DECISIONS.md"]
  affects: ["phase-3-forecasting-module"]
tech-stack:
  added: []
  patterns:
    - "Report/decisions files are generated deterministically from results/*.json by assemble_report_v2.py, never hand-written"
    - "ML winners are adjudicated against overfit_flags (lag1_dominant, marginal_over_naive) before being crowned, per D-01"
key-files:
  created:
    - backend_research/assemble_report_v2.py
    - backend_research/results/winners.json
    - backend_research/REPORT-PHASE2.md
    - .planning/phases/02-model-research-backtesting/02-MODEL-DECISIONS.md
  modified:
    - .planning/REQUIREMENTS.md
decisions:
  - "HDAN winner: SARIMAX(0,1,0)+exog, iterative, mean MAPE 1-12 = 13.33%, volatility from GARCH"
  - "PPAN winner: Direct-OLS VAR-system(h=1..12) [ppan, hdan, baltic_an, urals], direct strategy, mean MAPE 1-12 = 23.8%, volatility from ARIMA forecast SE (GARCH not viable)"
  - "Diesel-USD winner: Naive, iterative, mean MAPE 1-12 = 7.04%, volatility from ARIMA forecast SE"
  - "FX winner: Naive, iterative, mean MAPE 1-12 = 1.72%, volatility from ARIMA forecast SE"
  - "Human reviewer approved REPORT-PHASE2.md and 02-MODEL-DECISIONS.md as binding Phase 3 input (Task 3 checkpoint)"
metrics:
  duration: 5 min
  completed: 2026-08-21
---

# Phase 2 Plan 07: Assemble Winners, Report and Phase 3 Hand-off Summary

Ranked every backtested candidate family per series, adjudicated ML winners against their own
overfitting diagnostics, and produced the FCST-07 deliverable: `winners.json`, `REPORT-PHASE2.md`,
and a concise `02-MODEL-DECISIONS.md` hand-off — accepted by human review.

## What Was Built

Tasks 1 and 2 (code + report generation) were completed and committed in a prior session
(commit `1f4bb34`, `feat(02-07): assemble FCST-07 winners.json, REPORT-PHASE2.md and Phase 3
hand-off`). This session executed Task 3, the blocking human-verify checkpoint, and closes out
the plan.

- `backend_research/assemble_report_v2.py` — loads all `results/wf_*.json` records, ranks
  candidates per series, adjudicates ML winners against `overfit_flags`, attaches volatility
  source (GARCH where viable, ARIMA forecast SE fallback otherwise), and writes both
  `winners.json` and the ten-section `REPORT-PHASE2.md`.
- `backend_research/results/winners.json` — machine-readable per-series winner: model, family,
  predictors, horizon strategy, MAPE by horizon, volatility source, runner-up, caveats.
- `backend_research/REPORT-PHASE2.md` (262 lines, 10 `## ` sections) — full ranked study:
  winners at a glance, which assumption won, per-series ranking tables, iterative-vs-direct
  (D-06), predictor screen (D-04/D-05), cointegration/VECM, GARCH volatility source, ML
  overfitting caveats, comparison to the prior single-holdout study, and out-of-scope items
  (D-02/D-03/D-08).
- `.planning/phases/02-model-research-backtesting/02-MODEL-DECISIONS.md` (53 lines) — concise
  Phase 3 hand-off naming each series' winning model spec, predictors, horizon strategy, MAPE,
  volatility source, caveats, and a "Phase 3 must not" list.
- `.planning/REQUIREMENTS.md` — FCST-07 marked complete (checkbox + status row).

## Winners at a Glance

| Series | Winner | Strategy | Mean MAPE 1-12 | Volatility source |
|---|---|---|---|---|
| HDAN | SARIMAX(0,1,0)+exog | iterative | 13.33% | garch |
| PPAN | Direct-OLS VAR-system [ppan, hdan, baltic_an, urals] | direct | 23.8% | arima_forecast_se |
| Diesel-USD | Naive | iterative | 7.04% | arima_forecast_se |
| FX | Naive | iterative | 1.72% | arima_forecast_se |

## Human Acceptance (Task 3)

Reviewer read `REPORT-PHASE2.md` in full and approved without rework requests. Specific points
confirmed during review:

- The `MIN_ML_ORIGINS=5` thin-sample exclusion (a deviation from the plan's literal
  `lag1_dominant`/`marginal_over_naive`-only rule) was reviewed and approved — `n_origins=2`
  RandomForest results at 4.79%/12.14% MAPE are not statistically meaningful walk-forward
  backtests and would not have been caught by the two documented flags alone.
- Section 9 confirms no leakage red flag: walk-forward MAPEs are equal-to-worse than the prior
  single-holdout study's numbers for every series, as expected since walk-forward is a harder
  test.
- Section 5 states the FX predictor finding honestly (11 predictor/lag pairs clear the p<0.10
  screen, but Naive still wins on backtest MAPE — no predictor was forced onto FX for symmetry).
- Section 8 confirms no ML model was crowned on lag-1-dominant fits.
- `02-MODEL-DECISIONS.md` per-series specs are concrete enough for Phase 3 to hard-code without
  re-running any search.

## Deviations from Plan

None in this session — Task 3 was a pure human-verify checkpoint with no code changes. The
`MIN_ML_ORIGINS=5` deviation was introduced and documented during Task 1/2 execution (prior
session) and is not re-documented here beyond the reviewer's explicit sign-off above.

## Verification

```
cd backend_research && python assemble_report_v2.py
```
regenerates `winners.json`, `REPORT-PHASE2.md`, and `02-MODEL-DECISIONS.md` deterministically.
All four series have a named winner with a backtested error. Human acceptance recorded above.

## Self-Check: PASSED

- FOUND: backend_research/assemble_report_v2.py
- FOUND: backend_research/results/winners.json
- FOUND: backend_research/REPORT-PHASE2.md
- FOUND: .planning/phases/02-model-research-backtesting/02-MODEL-DECISIONS.md
- FOUND: commit 1f4bb34 (feat(02-07): assemble FCST-07 winners.json, REPORT-PHASE2.md and Phase 3 hand-off)
- FOUND: FCST-07 marked `[x]` and "Complete" in .planning/REQUIREMENTS.md
