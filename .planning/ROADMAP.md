# Roadmap — Prediction Dashboard

## Phases

- [x] **Phase 1: App Skeleton & Data Layer** - Running Reflex app with seeded historical price data in SQLite (completed 2026-08-21)
- [ ] **Phase 2: Model Research & Backtesting** - Forecasting models chosen and validated via holdout backtest, per series
- [ ] **Phase 3: Forecasting Module & Derived Series** - Base/bull/bear forecasts and derived Diesel-MNT computed from validated models
- [ ] **Phase 4: Data Entry UI & Historical View** - User manages monthly actuals in-app with validation and persistence
- [ ] **Phase 5: Forecast UI, Scenario Chart & Excel Export** - User views horizon-based scenario forecasts and exports data

## Phase Details

### Phase 1: App Skeleton & Data Layer
**Goal**: A running Reflex application backed by a SQLite schema covering all tracked fields, seeded from the existing CSV source data, ready for further development.
**Depends on**: Nothing (first phase)
**Requirements**: None directly (foundation phase — unblocks all others)
**Success Criteria** (what must be TRUE):
  1. Running the app locally starts a Reflex dashboard page without errors
  2. Historical price data from `AN Data.csv` and `Diesel Data.csv` is loaded into SQLite and queryable
  3. A database schema exists covering Date, HDAN, PPAN, Baltic_AN, Ammonia, Urea, Natural_Gas, Brent, Diesel_USD_ton, Urals, and FX_rate
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Scaffold Reflex app in `app/` and define the PriceRow + AppSetting SQLite schema (wave 1)
- [x] 01-02-PLAN.md — Seed 78 monthly rows from AN/Diesel CSVs with monthly-average collapse and idempotent upsert (wave 2)
- [x] 01-03-PLAN.md — DashboardState read path and read-only data table on the index page (wave 3)

**UI hint**: yes

### Phase 2: Model Research & Backtesting
**Goal**: Forecasting models for HDAN, PPAN, Diesel-USD, and FX are selected through a research/backtest process, not pre-chosen — no un-backtested model reaches the app.
**Depends on**: Phase 1
**Requirements**: FCST-07
**Success Criteria** (what must be TRUE):
  1. Candidate models (ARIMA/SARIMAX/VAR plus at least one ML baseline) have been fit and backtested per series against genuine holdout data
  2. A research report names the winning model per series along with its backtested error (e.g. MAPE)
  3. No model reaches the shipped forecasting module without having gone through this backtest process
**Plans**: 7 plans

Plans:
- [x] 02-01-PLAN.md — SQLite data loader, shared walk-forward harness, leakage unit tests (wave 1)
- [x] 02-02-PLAN.md — Granger causality + cointegration screen across the full predictor set (wave 2)
- [x] 02-03-PLAN.md — `arch` legitimacy gate and GARCH volatility per series (wave 2)
- [x] 02-04-PLAN.md — Naive/MA/ETS baselines and ARIMA/SARIMAX walk-forward, iterative vs direct (wave 3)
- [ ] 02-05-PLAN.md — VAR systems and VECM where cointegrated, walk-forward (wave 3)
- [ ] 02-06-PLAN.md — RandomForest/GradientBoosting baselines with overfitting diagnostics (wave 3)
- [ ] 02-07-PLAN.md — Rank all candidates, name winners, write report and Phase 3 hand-off (wave 4)

### Phase 3: Forecasting Module & Derived Series
**Goal**: Given historical data and a chosen horizon, the system produces base/bull/bear forecasts for each series and the derived Diesel-MNT series, using the models validated in Phase 2.
**Depends on**: Phase 2
**Requirements**: FCST-02, FCST-03, FCST-04, FCST-05
**Success Criteria** (what must be TRUE):
  1. Given historical data and a horizon, the system computes base, bull, and bear values for HDAN, PPAN, Diesel-USD, and FX
  2. Diesel purchasing price in MNT is computed as a derived series (Diesel-USD forecast × FX forecast × markup), not modeled independently
  3. Bull/bear spread is computed per-series from that series' own backtested error/volatility, not one flat percentage for all series
  4. Bull/bear spread widens as the horizon extends further out
**Plans**: TBD

### Phase 4: Data Entry UI & Historical View
**Goal**: The user can manage monthly actual price data directly in the dashboard, with entries validated and reliably persisted.
**Depends on**: Phase 1
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, VIS-01
**Success Criteria** (what must be TRUE):
  1. User can add a new row of monthly actual prices directly in the dashboard
  2. User can edit an existing row's values inline in the data table, and delete a row after confirming
  3. Invalid values (non-numeric input, negative prices, negative FX rate) are rejected before they reach storage
  4. Entered/edited/deleted rows are still present after the app is restarted or the page is refreshed
  5. User can view a historical chart of actual prices (no forecast) for each series
**Plans**: TBD
**UI hint**: yes

### Phase 5: Forecast UI, Scenario Chart & Excel Export
**Goal**: The user can select a forecast horizon, see base/bull/bear scenarios for all tracked series on one page, and export the stored data to Excel.
**Depends on**: Phase 3, Phase 4
**Requirements**: DATA-06, FCST-01, FCST-06, VIS-02, VIS-03, EXPORT-01
**Success Criteria** (what must be TRUE):
  1. User can select a forecast horizon from 1 to 12 months
  2. Dashboard shows base/bull/bear forecast values for HDAN, PPAN, Diesel-USD, FX, and derived Diesel-MNT in a table, in addition to a chart
  3. Forecast chart renders base/bull/bear as a shaded confidence band across the selected horizon
  4. All four tracked series (HDAN, PPAN, Diesel-MNT, FX) are visible together on a single dashboard page
  5. Each series shows an "as of" / last-updated date, and the user can export the stored price table to an `.xlsx` file
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. App Skeleton & Data Layer | 3/3 | Complete   | 2026-08-21 |
| 2. Model Research & Backtesting | 4/7 | In Progress|  |
| 3. Forecasting Module & Derived Series | 0/? | Not started | - |
| 4. Data Entry UI & Historical View | 0/? | Not started | - |
| 5. Forecast UI, Scenario Chart & Excel Export | 0/? | Not started | - |

---
*Roadmap created: 2026-08-21*
*Granularity: coarse*
