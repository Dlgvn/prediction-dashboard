# Roadmap — Prediction Dashboard

## Phases

- [x] **Phase 1: App Skeleton & Data Layer** - Running Reflex app with seeded historical price data in SQLite (completed 2026-08-21)
- [x] **Phase 2: Model Research & Backtesting** - Forecasting models chosen and validated via holdout backtest, per series (completed 2026-08-21)
- [x] **Phase 3: Forecasting Module & Derived Series** - Base/bull/bear forecasts and derived Diesel-MNT computed from validated models (completed 2026-08-22)
- [x] **Phase 4: Data Entry UI & Historical View** - User manages monthly actuals in-app with validation and persistence (completed 2026-08-22)
- [x] **Phase 5: Forecast UI, Scenario Chart & Excel Export** - User views horizon-based scenario forecasts and exports data (completed 2026-08-23)
- [ ] **Phase 6: UX/UI Redesign — Financial Forecasting Terminal** - Dashboard redesigned so a finance/procurement user grasps price, forecast, and range within 10-20 seconds

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
- [x] 02-05-PLAN.md — VAR systems and VECM where cointegrated, walk-forward (wave 3)
- [x] 02-06-PLAN.md — RandomForest/GradientBoosting baselines with overfitting diagnostics (wave 3)
- [x] 02-07-PLAN.md — Rank all candidates, name winners, write report and Phase 3 hand-off (wave 4)

### Phase 3: Forecasting Module & Derived Series
**Goal**: Given historical data and a chosen horizon, the system produces base/bull/bear forecasts for each series and the derived Diesel-MNT series, using the models validated in Phase 2.
**Depends on**: Phase 2
**Requirements**: FCST-02, FCST-03, FCST-04, FCST-05
**Success Criteria** (what must be TRUE):
  1. Given historical data and a horizon, the system computes base, bull, and bear values for HDAN, PPAN, Diesel-USD, and FX
  2. Diesel purchasing price in MNT is computed as a derived series (Diesel-USD forecast × FX forecast × markup), not modeled independently
  3. Bull/bear spread is computed per-series from that series' own backtested error/volatility, not one flat percentage for all series
  4. Bull/bear spread widens as the horizon extends further out
**Plans**: 4 plans

Plans:
- [x] 03-01-PLAN.md — Frozen Phase 2 constants, shared forecast primitives, test fixtures (wave 1)
- [x] 03-02-PLAN.md — HDAN SARIMAX(0,1,0)+exog with lag-aware future exog and GARCH band (wave 2)
- [x] 03-03-PLAN.md — PPAN Direct-OLS multi-step system, Diesel-USD/FX Naive with ARIMA-SE bands (wave 3)
- [x] 03-04-PLAN.md — forecast_all dispatcher, derived Diesel-MNT, FCST-02..05 test suite (wave 4)

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
**Plans**: 4 plans

Plans:
- [x] 04-01-PLAN.md — D-01/D-02 validators (numeric + unique-month date) with tests (wave 1)
- [x] 04-02-PLAN.md — DashboardState write path: inline edit, deferred-persist draft row, two-click delete (wave 2)
- [x] 04-03-PLAN.md — Editable table UI, Add row button, delete control, empty state (wave 3)
- [x] 04-04-PLAN.md — Historical chart with 16-series selector + human verification (wave 4)

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
**Plans**: 4 plans

Plans:
- [x] 05-01-PLAN.md — Forecast state core: horizon, history DataFrame, markup_pct, forecast_results, Excel export handler (wave 1)
- [x] 05-02-PLAN.md — Freshness chips, fan-chart figure, all-series forecast table data (wave 2)
- [x] 05-03-PLAN.md — Slider, chips, fan chart, forecast table and export button wired into index() (wave 3)
- [x] 05-04-PLAN.md — Regression run, human verification of the full flow, v1 requirements close-out (wave 4)

**UI hint**: yes

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. App Skeleton & Data Layer | 3/3 | Complete   | 2026-08-21 |
| 2. Model Research & Backtesting | 7/7 | Complete   | 2026-08-21 |
| 3. Forecasting Module & Derived Series | 4/4 | Complete   | 2026-08-22 |
| 4. Data Entry UI & Historical View | 4/4 | Complete   | 2026-08-22 |
| 5. Forecast UI, Scenario Chart & Excel Export | 4/4 | Complete   | 2026-08-23 |
| 6. UX/UI Redesign — Financial Forecasting Terminal | 0/3 | Planned       | — |

### Phase 6: UX/UI Redesign — Financial Forecasting Terminal
**Goal**: The dashboard is redesigned as a professional financial forecasting terminal — information architecture, forecast summary, chart, three-scenario display, horizon selector, upload/error/loading states, design system, color system, and accessibility all rework so a finance/procurement user grasps current price, forecast, and range within 10-20 seconds.
**Depends on**: Phase 5
**Requirements**: D-01..D-13 (06-CONTEXT.md decisions) + 06-UI-SPEC.md design contract — no formal REQUIREMENTS.md line items for this presentational phase
**Success Criteria** (what must be TRUE):
  1. Four forecast summary cards (HDAN, PPAN, Diesel MNT, FX Rate) are visible together at the top of the page, each showing base forecast, expected range, and direction vs. the latest actual
  2. Dragging the horizon slider updates the cards, fan chart, and forecast table in sync, with no new state variable
  3. The page reads header -> summary cards -> horizon -> fan chart -> forecast table -> freshness/export -> Historical -> Data Entry
  4. The fan chart visually separates history from forecast (forecast-start marker) and formats hover values as 1,234.56
  5. One fixed light theme with a single blue accent ships; no dark mode and no theme toggle exist
  6. Uncertainty is described as an "expected range" — the words "confidence interval" and "guaranteed" appear nowhere in the UI
  7. Cards reflow across viewport widths without page-level horizontal scroll, and all text/background pairings meet WCAG AA contrast (machine-verified)
**Plans**: 3 plans

Plans:
- [x] 06-01-PLAN.md — Design token module, in-place Plotly restyle, horizon-reactive summary_cards var (wave 1)
- [x] 06-02-PLAN.md — forecast_summary_cards() component, page reorder, light design system applied (wave 2)
- [ ] 06-03-PLAN.md — Responsive + accessibility pass, UI-SPEC sign-off, human verification (wave 3)

---
*Roadmap created: 2026-08-21*
*Granularity: coarse*
