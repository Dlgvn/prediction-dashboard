---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: complete
stopped_at: v1 complete — Phase 5 (final phase) closed out, all 6 requirements verified end-to-end
last_updated: "2026-08-23T06:10:06.419Z"
last_activity: 2026-08-23
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 22
  completed_plans: 22
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-21)

**Core value:** The user can enter a month's actuals, pick a forecast horizon (1-12 months),
and see a chart with three price scenarios (bull/base/bear) for each of the four tracked
series — without opening Excel.

**Current focus:** v1 COMPLETE — all 5 phases shipped, human-verified end to end

## Current Position

Phase: 05 (Forecast UI, Scenario Chart & Excel Export) — COMPLETE (final phase of v1)
Plan: 4 of 4
Status: v1 fully complete. All 5 phases done, all v1 requirements verified in a live
running app via the Phase 5 acceptance-gate checkpoint (horizon slider, freshness chips,
shaded fan chart, all-series forecast table, Excel export, no Phase 1-4 regression).
Last activity: 2026-08-23

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: - min
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01 P01 | 35min | 3 tasks | 9 files |
| Phase 01 P02 | 25min | 3 tasks | 2 files |
| Phase 02 P01 | 12min | 2 tasks | 4 files |
| Phase 02 P02 | 25min | 2 tasks | 3 files |
| Phase 02-model-research-backtesting P03 | 12min | 2 tasks | 3 files |
| Phase 02-model-research-backtesting P04 | 20min | 2 tasks | 4 files |
| Phase 02-model-research-backtesting P05 | 35min | 2 tasks | 2 files |
| Phase 02-model-research-backtesting P06 | 25min | 2 tasks | 2 files |
| Phase 02-model-research-backtesting P07 | 5min | 3 tasks | 4 files |
| Phase 03-forecasting-module-derived-series P01 | 25min | 2 tasks | 3 files |
| Phase 03 P02 | 20min | 2 tasks | 2 files |
| Phase 03 P03 | 15min | 2 tasks | 2 files |
| Phase 03 P04 | 40min | 3 tasks | 2 files |
| Phase 04 P01 | 10 | 2 tasks | 2 files |
| Phase 04 P02 | 15min | 3 tasks | 2 files |
| Phase 04 P03 | 15min | 2 tasks | 2 files |
| Phase 04 P04 | 55min | 3 tasks | 4 files |
| Phase 05 P01 | 35min | 3 tasks | 2 files |
| Phase 05 P02 | 25min | 3 tasks | 2 files |
| Phase 05 P03 | 20min | 3 tasks | 2 files |
| Phase 05 P04 | 10min | 3 tasks | 1 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Init: Reflex + SQLite single-process monolith (not split FastAPI service, not Postgres)
- Init: Fresh model design/research rather than porting the Excel workbook's exact coefficients
- Init: v1 scenarios = base ± statistical spread; live news/sentiment integration deferred to v2
- Init: No file-upload UI in v1 — manual in-app entry + Excel export instead
- [Phase ?]: 01-01: markup_pct lives in AppSetting key/value table, never on PriceRow (D-04)
- [Phase ?]: 01-01: 16-series PriceRow schema per D-05b/D-05c supersession (natural_gas split into 4 named benchmarks, urea split into black_sea/china)
- [Phase ?]: 01-02: D-06b averaging (not .last()) applied uniformly to both AN Data.csv and AN price weekly.csv
- [Phase ?]: 01-02: AN price weekly.csv seeded as authoritative 10-column source per D-07b, both urea benchmarks kept separate per D-05c
- [Phase ?]: NULL-to-blank rendering uses rx.cond(value != None, value, '') per-cell — a Var-level conditional, since Reflex renders Vars client-side
- [Phase ?]: DB-access boundary held entirely within state.py — DashboardState is the app's sole rx.session() call site
- [Phase 02-01]: pandas 2.2.3/scikit-learn 1.7.2 installed, not STACK.md's 3.0.5/1.9.0 pins — research code written to pandas 2.x semantics
- [Phase 02-01]: walk_forward.py is the single shared rolling-origin harness (model-agnostic) reused by every Phase 2 model runner; LeakageError raised eagerly, not just commented
- [Phase ?]: 02-02: fx_rate re-tested (not assumed) against expanded predictor set — now shows real p<0.10/p<0.05 predictors, overturning prior no-predictor finding
- [Phase ?]: 02-02: no target-pair cointegration found at p<0.05 — VECM_CANDIDATES empty, plan 02-05 proceeds with plain VAR
- [Phase ?]: arch==8.0.0 approved at package-legitimacy checkpoint after manual PyPI/GitHub verification; SUS flag was a false positive
- [Phase ?]: GARCH(1,1) only per Assumption A4, no EGARCH/GJR sweep
- [Phase 02-04]: Baselines fitted on price levels not pct-change; ARIMA order fixed once by AIC and held fixed for the whole walk-forward run
- [Phase ?]: 02-05: VECM_CANDIDATES empty per 02-02 finding; wrote explicit non-applicability record instead of skipping the family
- [Phase ?]: 02-05: iterative VAR family shows explosive MAPE at long horizons for several series due to short-overlap predictor data; direct-OLS VAR variant stays bounded and is likely the safer family choice
- [Phase ?]: 02-06: ML baseline (RandomForest/GradientBoosting) does not clearly beat naive on diesel/fx and is flagged suspiciously_strong/small_sample on hdan/ppan; overfitting diagnostics attached as data per D-01
- [Phase 02-07]: Final winners accepted by human review: HDAN=SARIMAX(0,1,0)+exog (13.33% MAPE, GARCH vol), PPAN=Direct-OLS VAR-system [ppan,hdan,baltic_an,urals] (23.8% MAPE, ARIMA-SE vol), Diesel-USD=Naive (7.04% MAPE), FX=Naive (1.72% MAPE); MIN_ML_ORIGINS=5 thin-sample exclusion approved as an addition to the plan's literal overfit-flag rule
- [Phase 02-07]: Phase 2 complete — FCST-07 satisfied; Phase 3 must hard-code these winners from 02-MODEL-DECISIONS.md, no re-search at runtime
- [Phase ?]: 03-01: forecasting.py primitives complete; provenance comments intentionally kept despite literal-grep conflicts (see SUMMARY deviations)
- [Phase 03-02]: Ammonia lag-3 predictor uses last 3 observed actuals for future steps 1-3, only switching to forecast path at step 4+ (03-RESEARCH.md Pattern 1 was wrong to generalize the lag-1 case)
- [Phase ?]: PPAN uses Direct-OLS VAR-system (twelve per-horizon OLS regressions), not iterative statsmodels VAR() -- per 02-MODEL-DECISIONS.md binding spec and 03-03-PLAN.md planner_correction
- [Phase ?]: 03-04: forecast_ppan_var_system now selects the last row with all system-member features observed (dropna), not the literal last calendar row
- [Phase ?]: 04-02: SERIES_ATTRS tuple in state.py is single source of truth for 16 series columns, reused by draft-row promotion and future chart selector (04-04)
- [Phase ?]: 04-03: Combined Task1/Task2 edits in one app.py pass, committed separately to preserve plan task-level commit granularity
- [Phase 04-04]: SERIES_LABELS/LABEL_TO_ATTR promoted to state.py as single source of truth for series display labels; app.py rebuilds _COLUMNS from it instead of hardcoding
- [Phase 04-04]: Phase 4 complete — VIS-01 and DATA-05 satisfied; human checkpoint approved full add/edit/delete/persist/chart flow, including a to_string() quote-wrapping bug fixed during verification
- [Phase 05]: 05-01: forecast_results empty/error shape is {key: [] for key in FORECAST_SERIES_LABELS} — 05-02 indexes all 5 keys unconditionally
- [Phase 05]: 05-01: row.model_dump() misbehaves on PriceRow during export; _export_bytes builds records manually from date+SERIES_ATTRS instead
- [Phase ?]: 05-02: diesel_mnt historical values in forecast_chart_figure use the exact same diesel_usd*fx*(1+markup_pct/100) convention as forecasting.py's diesel_mnt_forecast
- [Phase ?]: 05-02: FORECAST_TABLE_COLUMNS derived programmatically from FORECAST_SERIES_LABELS x scenario names
- [Phase ?]: 05-03: Task 1+2 combined into one app.py commit per 04-03 precedent; test_index_on_mount_loads_markup_pct uses inspect.getsource since render() doesn't surface on_mount
- [Phase ?]: 05-04: Human-verified v1 acceptance gate approved in-browser; Phase 5 requirements ledger closed out, marking v1 scope fully complete

### Pending Todos

None yet.

### Blockers/Concerns

- Weekly forecast mode is explicitly deferred to v2. Update 2026-08-21: the data-availability
  half of this blocker is resolved — `AN Data.csv` is native weekly for HDAN/PPAN, and
  `AN price weekly.csv` adds real weekly drivers (Middle East Ammonia, Black Sea/China Urea, gas
  benchmarks). But the backtest (backend_research/REPORT.md, "Weekly cadence" section) is a
  no-go: weekly-native VAR rolled 4 weeks forward underperforms the existing monthly VAR
  (10.35%/16.01% vs 9.49%/10.08% MAPE), so the deferral stands. No weekly Diesel/FX data exists
  at all, unchanged.

- Model family selection (ARIMA/SARIMAX/VAR vs. ML baseline) is genuinely open — Phase 2 must
  produce real backtest results, not a formality, before Phase 3 forecasting logic is built.

- Confidence-band methodology (backtest MAPE vs. model-native forecast SE) needs a concrete
  design decision during Phase 3 planning.

## Session Continuity

Last session: 2026-08-23T06:10:06.413Z
Stopped at: Phase 5 planned (4 plans, 4 waves)
Resume file: None
