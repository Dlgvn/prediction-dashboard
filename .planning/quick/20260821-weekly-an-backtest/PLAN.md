---
slug: weekly-an-backtest
created: 2026-08-21
---

# Weekly AN (HDAN/PPAN) backtest — extend backend_research/

## Context

`backend_research/REPORT.md` (Phase 1 research) found VAR(HDAN,PPAN) as the winning model at
9.49%/10.08% MAPE, using `AN Data.csv` **resampled to monthly** (last-of-month). But `AN Data.csv`
is itself already weekly-cadence for HDAN/PPAN (rows ~7 days apart). A second file, `AN price
weekly.csv`, supplies weekly drivers not in the original research: Natural Gas (JKM, Henry Hub,
UK, Netherlands), Corn (US, China), Baltic AN, Middle East Ammonia, Black Sea Urea, China Urea.

This directly addresses the project's data-cadence-gap blocker (.planning/STATE.md): "Baltic AN
proxy for HDAN/PPAN is unvalidated."

## Task

1. Add `load_an_weekly()` to `backend_research/data_loader.py` — native weekly HDAN/PPAN/Baltic
   AN/Ammonia/Urea/Natural_gas/Brent from `AN Data.csv`, indexed by week-ending date, no resampling.
2. Add `load_weekly_drivers()` — parse `AN price weekly.csv` (dates in `YYYY.MM.DD` format,
   descending), forward-fill sparse columns where appropriate, indexed by week-ending date.
3. Add `merged_weekly()` joining the two on nearest week-ending date (allow ±3 day tolerance —
   the two files' week-ending conventions may not align exactly).
4. Write `backend_research/run_weekly_candidates.py`: backtest MAPE (holdout = last 12 weeks,
   one-step-ahead) for HDAN and PPAN using:
   - naive (last value)
   - VAR(HDAN, PPAN) at weekly cadence (mirrors the monthly winner)
   - OLS+Granger with weekly Baltic AN / Ammonia / Urea lags (mirrors existing monthly approach)
   - OLS+Granger extended with the new weekly drivers (gas benchmarks, corn, Middle East Ammonia,
     Black Sea/China Urea) at lags 1-3
   Save results to `backend_research/results/weekly_candidates.json`.
5. Append a "Weekly cadence (Phase 1 follow-up)" section to `backend_research/REPORT.md`:
   comparison table, plain-language synthesis, and an explicit go/no-go recommendation on
   whether the weekly-mode blocker in `.planning/STATE.md` can be lifted.
6. If the recommendation is "go", update the blocker note in `.planning/STATE.md` to reflect
   the new finding (do not remove it — this quick task doesn't re-plan the roadmap).

## Out of scope

- Diesel/FX weekly forecasting (no weekly source data exists for either — blocker stands as-is).
- Any changes to the Reflex app itself (Phase 1 app-skeleton work is separate and untouched).
