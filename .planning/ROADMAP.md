# Roadmap — Prediction Dashboard

## Phases

- [x] **Phase 1: App Skeleton & Data Layer** - Running Reflex app with seeded historical price data in SQLite (completed 2026-08-21)
- [x] **Phase 2: Model Research & Backtesting** - Forecasting models chosen and validated via holdout backtest, per series (completed 2026-08-21)
- [x] **Phase 3: Forecasting Module & Derived Series** - Base/bull/bear forecasts and derived Diesel-MNT computed from validated models (completed 2026-08-22)
- [x] **Phase 4: Data Entry UI & Historical View** - User manages monthly actuals in-app with validation and persistence (completed 2026-08-22)
- [x] **Phase 5: Forecast UI, Scenario Chart & Excel Export** - User views horizon-based scenario forecasts and exports data (completed 2026-08-23)
- [x] **Phase 6: UX/UI Redesign — Financial Forecasting Terminal** - Dashboard redesigned so a finance/procurement user grasps price, forecast, and range within 10-20 seconds (completed 2026-08-23)
- [ ] **Phase 7: Table Pagination / Windowing** - Data Entry table defaults to recent months, with a toggle to show full history, without hanging the browser
- [x] **Phase 8: Forecast Context Enrichment** - Forecast summary cards show historical high/low and year-over-year % change (completed 2026-08-24)
- [x] **Phase 9: Excel Export Polish** - Excel export includes a forecast sheet (base/bull/bear) alongside the existing actuals sheet (completed 2026-08-24)
- [ ] **Phase 10: CSV Bulk Import** - User can bulk-import historical prices via CSV with preview, confirm, and duplicate-date skipping

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
- [x] 06-03-PLAN.md — Responsive + accessibility pass, UI-SPEC sign-off, human verification (wave 3)

### Phase 7: Table Pagination / Windowing
**Goal**: The Data Entry table is usable at real data scale — it defaults to showing recent months only, with an explicit toggle to reveal full history, and never hangs the browser regardless of row count.
**Depends on**: Phase 4
**Requirements**: DATA-07, DATA-08
**Success Criteria** (what must be TRUE):
  1. The Data Entry table shows only recent months by default, not all 167+ rows since 2013
  2. The table renders and responds without hanging at the reported real-data scale (167 rows × 17 columns)
  3. User can toggle "show all history" to reveal the full table when they need to edit older rows
  4. Every other page feature that depends on full history (forecasts, charts, freshness chips, export) continues to reflect the complete dataset, not just the visible window
**Plans**: 2 plans

Plans:
- [x] 07-01-PLAN.md — `visible_rows` display-only window, `show_all_history` field, D-03 toggle handler + self.rows integrity tests (wave 1)
- [x] 07-02-PLAN.md — `rx.switch` toggle control, `data_table()` repointed to `visible_rows`, component tests + human verification (wave 2)

**UI hint**: yes

### Phase 8: Forecast Context Enrichment
**Goal**: Each forecast summary card gives the user more range context — historical high/low and year-over-year change — beyond just the forecast band and current-vs-latest-actual direction.
**Depends on**: Phase 7
**Requirements**: FCST-08, FCST-09
**Success Criteria** (what must be TRUE):
  1. Each forecast summary card shows the series' historical high and low, computed from stored actuals
  2. Each forecast summary card shows a year-over-year percentage change alongside the existing direction indicator
  3. High/low and YoY figures are derived from the same underlying data and helper logic as the rest of the dashboard, so they never disagree with other displayed numbers
**Plans**: 2 plans

Plans:
- [x] 08-01-PLAN.md — Shared `_actual_series_for` diesel_mnt helper, all-time high/low and calendar-month YoY keys on `summary_cards` (wave 1)
- [x] 08-02-PLAN.md — Two new `_summary_card()` lines, extended `aria_label`, component tests + human verification (wave 2)

**UI hint**: yes

### Phase 9: Excel Export Polish
**Goal**: The Excel export becomes a more complete data-portability artifact — it includes forecast values, not just actuals.
**Depends on**: Phase 7
**Requirements**: EXPORT-02
**Success Criteria** (what must be TRUE):
  1. The exported `.xlsx` file includes a forecast sheet with base/bull/bear values at the selected horizon, in addition to the existing actuals sheet
  2. The existing actuals-only sheet remains present and unchanged in the export
  3. Forecast values in the exported sheet match what the dashboard displays for the same horizon at export time
**Plans**: 1 plan

Plans:
- [x] 09-01-PLAN.md — Two-sheet `_export_bytes` (Actuals + Forecast) reusing `forecast_table_rows`, with parity and single-call-site tests (wave 1)

### Phase 10: CSV Bulk Import
**Goal**: The user can bulk-import historical price data via CSV instead of entering it row by row, with a safe preview-and-confirm step that never silently overwrites existing data.
**Depends on**: Phase 7, Phase 9
**Requirements**: IMPORT-01, IMPORT-02
**Success Criteria** (what must be TRUE):
  1. User can upload a CSV file of historical price data matching the app's expected schema
  2. Before any row is written to storage, the user sees a preview of the parsed rows with per-row validation status
  3. User can confirm the import to commit only valid rows in a single batch write
  4. CSV rows whose date already exists in storage are skipped, and existing data is never overwritten
  5. The import summary tells the user how many rows were added vs. skipped
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. App Skeleton & Data Layer | 3/3 | Complete   | 2026-08-21 |
| 2. Model Research & Backtesting | 7/7 | Complete   | 2026-08-21 |
| 3. Forecasting Module & Derived Series | 4/4 | Complete   | 2026-08-22 |
| 4. Data Entry UI & Historical View | 4/4 | Complete   | 2026-08-22 |
| 5. Forecast UI, Scenario Chart & Excel Export | 4/4 | Complete   | 2026-08-23 |
| 6. UX/UI Redesign — Financial Forecasting Terminal | 3/3 | Complete   | 2026-08-23 |
| 7. Table Pagination / Windowing | 0/2 | Not started | — |
| 8. Forecast Context Enrichment | 2/2 | Complete   | 2026-08-24 |
| 9. Excel Export Polish | 0/1 | Not started | — |
| 10. CSV Bulk Import | 0/? | Not started | — |

---
*Roadmap created: 2026-08-21*
*v1.2 phases (7-10) added: 2026-08-24*
*Granularity: coarse*
