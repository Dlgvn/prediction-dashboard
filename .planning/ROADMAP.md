# Roadmap — Prediction Dashboard

## Phases

- [x] **Phase 1: App Skeleton & Data Layer** - Running Reflex app with seeded historical price data in SQLite (completed 2026-08-21)
- [x] **Phase 2: Model Research & Backtesting** - Forecasting models chosen and validated via holdout backtest, per series (completed 2026-08-21)
- [x] **Phase 3: Forecasting Module & Derived Series** - Base/bull/bear forecasts and derived Diesel-MNT computed from validated models (completed 2026-08-22)
- [x] **Phase 4: Data Entry UI & Historical View** - User manages monthly actuals in-app with validation and persistence (completed 2026-08-22)
- [x] **Phase 5: Forecast UI, Scenario Chart & Excel Export** - User views horizon-based scenario forecasts and exports data (completed 2026-08-23)
- [x] **Phase 6: UX/UI Redesign — Financial Forecasting Terminal** - Dashboard redesigned so a finance/procurement user grasps price, forecast, and range within 10-20 seconds (completed 2026-08-23)
- [x] **Phase 7: Table Pagination / Windowing** - Data Entry table defaults to recent months, with a toggle to show full history, without hanging the browser (completed 2026-08-24)
- [x] **Phase 8: Forecast Context Enrichment** - Forecast summary cards show historical high/low and year-over-year % change (completed 2026-08-24)
- [x] **Phase 9: Excel Export Polish** - Excel export includes a forecast sheet (base/bull/bear) alongside the existing actuals sheet (completed 2026-08-24)
- [x] **Phase 10: CSV Bulk Import** - User can bulk-import historical prices via CSV with preview, confirm, and duplicate-date skipping (completed 2026-08-24)
- [x] **Phase 11: Background Fix + Theme Toggle** - Dashboard renders correctly at every viewport with a persisted dark/light mode toggle (completed 2026-08-24)
- [x] **Phase 12: Fan Chart Legend/Axis Fix** - Fan chart legend and axis labels no longer overlap at any viewport (completed 2026-08-25)
- [x] **Phase 13: Model Provenance Display** - Each forecast shows which model produced it and its backtested accuracy (completed 2026-08-25)
- [x] **Phase 14: Tab/Nav Bar** - User switches between Summary/Forecast/Data Entry via tabs without losing in-progress state (completed 2026-08-25)
- [x] **Phase 15: Data Entry Rework** - Date entry reliably accepts valid input with visible errors and no format memorization (completed 2026-08-25)
- [x] **Phase 16: Sentiment Data Sufficiency & Causality Research** - A documented go/no-go on whether a sentiment-driven scenario adjustment is viable against the app's real series (completed 2026-09-01, no-go)
- [x] **Phase 17: Weekly Forecast Re-Research Spike** - A documented go/no-go on new weekly-cadence candidates for HDAN/PPAN, compared against the prior no-go benchmark (completed 2026-09-01, go — no UI shipped, out of scope this milestone)
- ~~Phase 18: Sentiment-Adjusted Scenario UI~~ — dropped, Phase 16 returned no-go (see [v2.0 archive](milestones/v2.0-ROADMAP.md))
- [x] **Phase 19: Weekly Schema & Ingestion** - Genuine weekly-cadence historical data for HDAN, PPAN, and FX rate is persisted separately from the monthly table
- [x] **Phase 20: FX Weekly Backtest** - A backtested weekly FX forecasting model exists with a documented, frozen go/no-go verdict against the monthly benchmark (completed 2026-09-01)
- [x] **Phase 21: Weekly Forecasting Module** - `forecast_all_weekly` and per-series weekly forecast functions exist, unit-testable in isolation from the UI
 (completed 2026-09-02)
- [x] **Phase 22: Weekly Granularity Toggle & UI** - User can toggle Monthly/Weekly, see weekly forecasts for HDAN/PPAN/FX with correct provenance and dates, and see Diesel honestly marked monthly-only (completed 2026-09-02)

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

**Plans**: 3 plans

Plans:

- [x] 10-01-PLAN.md — Reflex-free CSV parse + validator-reusing row validation core with schema fail-fast (wave 1)
- [x] 10-02-PLAN.md — DashboardState upload/preview/confirm/cancel handlers, insert-only batch write + load_rows refresh (wave 2)
- [x] 10-03-PLAN.md — rx.upload dropzone, summary preview panel, Confirm/Cancel UI + human verification (wave 3)

**UI hint**: yes

### Phase 11: Background Fix + Theme Toggle

**Goal**: The dashboard renders a correct, mode-aware background at every viewport width, and the user can toggle between light and dark mode with the choice persisting across visits.
**Depends on**: Phase 6
**Requirements**: THEME-01, THEME-02, THEME-03, THEME-04
**Success Criteria** (what must be TRUE):

  1. No transparent margins or unstyled black areas appear outside the page content at any viewport width, in either light or dark mode
  2. User can toggle between light and dark mode from a visible control in the dashboard UI
  3. The chosen theme mode is still active after reloading the page or returning in a new visit
  4. Every existing color token (cards, charts, text, accent) has a correct, legible dark-mode counterpart — no illegible text or un-styled element in dark mode

**Plans**: 3 plans

Plans:

- [x] 11-01-PLAN.md — Dual-tokenize theme.py with a bespoke DARK palette, tokens(mode) lookup, and WCAG contrast tests (wave 1)
- [x] 11-02-PLAN.md — Set rx.Config(default_color_mode="light"), add persisted DashboardState.theme_mode + mode-resolved color vars, make both Plotly figures mode-aware (wave 2)
- [x] 11-03-PLAN.md — Bind html/body background to state, add the header toggle, convert every app.py color prop, browser-verify both themes (wave 3)

**UI hint**: yes

### Phase 12: Fan Chart Legend/Axis Fix

**Goal**: The fan chart's legend and axis labels are readable and never overlap, at any supported viewport width.
**Depends on**: Phase 11
**Requirements**: VIS-04
**Success Criteria** (what must be TRUE):

  1. The fan chart's legend does not visually overlap its axis labels at any supported viewport width
  2. The fix is applied consistently to both the historical chart and the forecast chart

**Plans**: 1 plan
**UI hint**: yes

Plans:

- [x] 12-01-PLAN.md — Move chart legends below the plot area, widen bottom margin, add layout regression tests + human viewport check (wave 1)

### Phase 13: Model Provenance Display

**Goal**: Each series' forecast section shows which model produced it and its backtested accuracy, sourced from a single existing source of truth.
**Depends on**: Phase 12
**Requirements**: VIS-05
**Success Criteria** (what must be TRUE):

  1. Each series' forecast section displays the model name that produced it (e.g. "SARIMAX", "Direct-OLS VAR", "Naive")
  2. Each series' forecast section displays its backtested accuracy (e.g. MAPE)
  3. The displayed model name and accuracy are sourced from the existing model-selection constants, not a second hand-typed copy

**Plans**: 2 plans
**UI hint**: yes

Plans:

- [x] 13-01-PLAN.md — MODEL_INFO constant in forecasting.py + model_label/model_text on summary_cards (wave 1)
- [x] 13-02-PLAN.md — Model line in _summary_card, extended aria_label, component tests + human verification (wave 2)

### Phase 14: Tab/Nav Bar

**Goal**: The user navigates between Summary, Forecast, and Data Entry sections via a tab/nav bar instead of one long scroll, without losing in-progress work.
**Depends on**: Phase 13
**Requirements**: NAV-01
**Success Criteria** (what must be TRUE):

  1. User can switch between Summary, Forecast, and Data Entry sections via a visible tab/nav bar
  2. Switching sections does not trigger a full page reload
  3. In-progress edits (e.g. a draft row) are preserved when switching away from Data Entry and back
  4. An in-progress CSV import preview is preserved when switching away from Data Entry and back

**Plans**: 2 plans

Plans:

- [x] 14-01-PLAN.md — active_section state field, set_active_section handler, and state-preservation regression tests (wave 1)
- [x] 14-02-PLAN.md — nav_bar() Radix tab bar and tabbed index() restructure, with live-browser verification (wave 2)

**UI hint**: yes

### Phase 15: Data Entry Rework

**Goal**: The user can reliably enter a new row's date, with immediate visible feedback on invalid input and no need to remember an exact date format.
**Depends on**: Phase 14
**Requirements**: DATA-09, DATA-10
**Success Criteria** (what must be TRUE):

  1. Entering a new row's date with invalid or incomplete input shows a visible, immediate error instead of silently failing
  2. Valid date input is reliably accepted and the row is added
  3. The date entry control does not require the user to type or recall an exact date format from memory
  4. Existing shared state behavior (windowing toggle, CSV import) continues to work correctly after the date-entry rework

**Plans**: 2 plans

Plans:

- [x] 15-01-PLAN.md — start_edit race-guard fix, state-transition table, D-03 CSV-import audit (wave 1)
- [x] 15-02-PLAN.md — Native rx.input(type="date") swap in _editable_cell + human verification (wave 2)

## Milestone v2.0 (archived)

Phases 16-17 shipped 2026-09-01 (Phase 18 dropped — gated on Phase 16's "go", not met).
Full detail: [.planning/milestones/v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md).

## Milestone v2.1 Weekly Forecast UI

### Phase 19: Weekly Schema & Ingestion

**Goal**: Genuine weekly-cadence historical data for HDAN, PPAN, and FX rate exists in SQLite, sourced natively from `AN Data.csv` and `FX Data.csv`'s Weekly column, persisted separately from the existing monthly `PriceRow` table — never resampled or interpolated from monthly data.
**Depends on**: Nothing new (builds on Phase 1's data layer; zero risk to the existing monthly path)
**Requirements**: WKUI-01
**Success Criteria** (what must be TRUE):

  1. A `WeeklyPriceRow` table (or equivalent) exists, distinct from the monthly `PriceRow` table, storing HDAN/PPAN/Baltic AN/FX at true weekly grain
  2. Weekly HDAN/PPAN rows are parsed directly from `AN Data.csv`'s native weekly cadence, not derived from the monthly table
  3. Weekly FX rows are parsed from `FX Data.csv`'s Weekly column (865 rows, 2010-01-04 to 2026-07-27) using positional column slicing that correctly isolates the Weekly cadence from the file's Daily/Monthly columns
  4. AN-family (Friday-based) and FX (Monday-based) weekly rows are joined/aligned via a tolerance-based join (e.g. `merge_asof`), not naive row alignment, so no silent date misalignment is introduced
  5. Row counts and date ranges after seeding match the source CSVs (spot-checkable against the known 865-row/2010-01-04..2026-07-27 FX range)

**Plans**: 2 plans

Plans:

- [x] 19-01-PLAN.md — WeeklyPriceRow schema + Alembic migration (wave 1)
- [x] 19-02-PLAN.md — seed_weekly.py native AN/FX parsing, tolerance merge_asof, idempotent upsert (wave 2)

### Phase 20: FX Weekly Backtest

**Goal**: A backtested weekly-cadence FX forecasting model exists, with a documented, frozen go/no-go verdict against the existing monthly FX benchmark (1.72% MAPE, AR(1)/Naive) — a "no-go" is a complete, valid outcome, not a blocker.
**Depends on**: Nothing new (uses the existing `walk_forward_backtest` harness; can run in parallel with Phase 19 — no shared state)
**Requirements**: WKUI-02
**Success Criteria** (what must be TRUE):

  1. A dedicated FX weekly backtest script exists (not a clone of the HDAN/PPAN weekly runner) with its own examined `MIN_TRAIN_WEEKLY` and benchmark constants for FX
  2. At least SARIMAX and ETS weekly candidates for FX have been walk-forward backtested using the shared harness
  3. A frozen results artifact (e.g. `results/weekly_fx.json`) records each candidate's backtested MAPE
  4. A documented go/no-go verdict exists, comparing the best weekly FX candidate against the 1.72% MAPE monthly benchmark
  5. If the verdict is "no-go", FX weekly forecasting is explicitly excluded from Phase 22's UI scope rather than shipped un-backtested

**Plans**: 1 plan

Plans:

- [x] 20-01-PLAN.md — Dedicated FX weekly SARIMAX/ETS backtest, examined MIN_TRAIN_WEEKLY, computed go/no-go vs. 1.72% benchmark, REPORT-WEEKLY-FX.md (wave 1)

### Phase 21: Weekly Forecasting Module

**Goal**: A forecasting module exists that produces weekly base/bull/bear forecasts for HDAN, PPAN, and (if Phase 20 is a "go") FX, using frozen, transcribed model constants — fully unit-testable in isolation from the UI, mirroring the existing monthly `forecasting.py` pattern.
**Depends on**: Phase 19 (weekly data), Phase 20 (FX model spec/verdict)
**Requirements**: None directly (infrastructure phase — unblocks Phase 22's UI; validated indirectly via WKUI-06/WKUI-07 in Phase 22)
**Success Criteria** (what must be TRUE):

  1. `forecast_weekly_hdan`/`forecast_weekly_ppan` functions exist using Phase 17's frozen SARIMAX/ETS constants, transcribed (not re-derived via runtime search)
  2. A `forecast_weekly_fx` function exists using Phase 20's frozen winning constants, present only if Phase 20 returned "go"
  3. A `forecast_all_weekly` dispatcher and a `WEEKLY_MODEL_INFO` constant (model name + MAPE per weekly series) exist, analogous to the monthly module's `MODEL_INFO`
  4. All weekly forecasting functions are callable and unit-testable with no dependency on Reflex state or the UI layer

**Plans**: 2 plans

Plans:

- [x] 21-01-PLAN.md — forecast_weekly_hdan/forecast_weekly_ppan: shared SARIMAX(0,1,0)+BalticAN(unlagged exog) engine (wave 1)
- [x] 21-02-PLAN.md — forecast_weekly_fx (ETS-HoltDamped + simulate()-based spread), WEEKLY_MODEL_INFO, forecast_all_weekly dispatcher (wave 2)

### Phase 22: Weekly Granularity Toggle & UI

**Goal**: The user can toggle the dashboard between Monthly and Weekly forecast granularity, see correctly-dated, correctly-attributed weekly forecasts for HDAN/PPAN/FX, and see Diesel-USD/Diesel-MNT honestly marked monthly-only rather than hidden or faked.
**Depends on**: Phase 21
**Requirements**: WKUI-03, WKUI-04, WKUI-05, WKUI-06, WKUI-07, WKUI-08
**Success Criteria** (what must be TRUE):

  1. A single global Monthly/Weekly toggle drives both the Forecast tab chart and Summary cards together — not independent per-series toggles
  2. The selected granularity is still active after reloading the page or returning in a new visit
  3. When Weekly is selected, Diesel-USD and Diesel-MNT cards show an explicit, always-visible "monthly only" disabled/muted state — never hidden, never showing fabricated weekly data
  4. When Weekly is selected, the horizon control is denominated in weeks (not a relabeled month slider), capped to the range actually covered by the weekly backtest(s)
  5. When Weekly is selected, each weekly-capable series' summary card shows the correct weekly model name and its backtested MAPE, not a stale monthly figure
  6. Weekly forecast chart/table dates show real week-ending dates, not relabeled monthly tick marks

**Plans**: 3 plans

Plans:

- [x] 22-01-PLAN.md — Granularity toggle state + weekly data loading + independent horizon-weeks controls (wave 1)
- [x] 22-02-PLAN.md — Diesel-USD summary card + Diesel dimming/badge + weekly model provenance on summary cards (wave 2)
- [ ] 22-03-PLAN.md — Granularity toggle UI + weekly chart/table date branching + human verification (wave 3)

**UI hint**: yes

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. App Skeleton & Data Layer | 3/3 | Complete   | 2026-08-21 |
| 2. Model Research & Backtesting | 7/7 | Complete   | 2026-08-21 |
| 3. Forecasting Module & Derived Series | 4/4 | Complete   | 2026-08-22 |
| 4. Data Entry UI & Historical View | 4/4 | Complete   | 2026-08-22 |
| 5. Forecast UI, Scenario Chart & Excel Export | 4/4 | Complete   | 2026-08-23 |
| 6. UX/UI Redesign — Financial Forecasting Terminal | 3/3 | Complete   | 2026-08-23 |
| 7. Table Pagination / Windowing | 2/2 | Complete   | 2026-08-24 |
| 8. Forecast Context Enrichment | 2/2 | Complete   | 2026-08-24 |
| 9. Excel Export Polish | 1/1 | Complete   | 2026-08-24 |
| 10. CSV Bulk Import | 3/3 | Complete   | 2026-08-24 |
| 11. Background Fix + Theme Toggle | 3/3 | Complete   | 2026-08-24 |
| 12. Fan Chart Legend/Axis Fix | 1/1 | Complete   | 2026-08-25 |
| 13. Model Provenance Display | 2/2 | Complete   | 2026-08-25 |
| 14. Tab/Nav Bar | 2/2 | Complete   | 2026-08-25 |
| 15. Data Entry Rework | 2/2 | Complete   | 2026-08-25 |
| 16. Sentiment Data Sufficiency & Causality Research | 2/2 | Complete   | 2026-09-01 |
| 17. Weekly Forecast Re-Research Spike | 2/2 | Complete   | 2026-09-01 |
| 18. Sentiment-Adjusted Scenario UI | — | Dropped (Phase 16 no-go) | - |
| 19. Weekly Schema & Ingestion | 1/2 | In Progress|  |
| 20. FX Weekly Backtest | 1/1 | Complete   | 2026-09-01 |
| 21. Weekly Forecasting Module | 2/2 | Complete   | 2026-09-02 |
| 22. Weekly Granularity Toggle & UI | 3/3 | Complete   | 2026-09-02 |

---
*Roadmap created: 2026-08-21*
*v1.2 phases (7-10) added: 2026-08-24*
*v1.3 phases (11-15) added: 2026-08-24*
*v2.0 phases (16-18) added: 2026-08-31*
*v2.0 archived: 2026-09-01 — see .planning/milestones/v2.0-ROADMAP.md*
*v2.1 phases (19-22) added: 2026-09-01*
*Granularity: coarse*
