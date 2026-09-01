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
- [x] **Phase 16: Sentiment Data Sufficiency & Causality Research** - A documented go/no-go on whether a sentiment-driven scenario adjustment is viable against the app's real series
- [ ] **Phase 17: Weekly Forecast Re-Research Spike** - A documented go/no-go on new weekly-cadence candidates for HDAN/PPAN, compared against the prior no-go benchmark
- [ ] **Phase 18: Sentiment-Adjusted Scenario UI (conditional on Phase 16 go)** - User sees an additive, honestly-labeled sentiment band on the fan chart with provenance and a toggle

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

### Phase 16: Sentiment Data Sufficiency & Causality Research

**Goal**: Determine, via a rigorous causality/correlation backtest run against the app's actual HDAN/PPAN/Diesel-USD/FX series (not equities), whether a sentiment-driven scenario adjustment is viable enough to build — with a documented, frozen go/no-go result as the deliverable. A "no-go" is a complete, valid outcome for this phase, not a failure to fix.
**Depends on**: Nothing (independent research phase; reuses Phase 2's `walk_forward.py`/causality-screen discipline)
**Requirements**: SENT-01, SENT-02
**Success Criteria** (what must be TRUE):

  1. A causality/correlation screen has been run against the app's actual HDAN/PPAN/Diesel-USD/FX series (mirroring `causality_screen.py`'s pattern, not against equities like SPY/QQQ/VIX)
  2. The screen's output explicitly reports the effective monthly sample size (not raw daily row counts) so a small-N illusion cannot pass as sufficient evidence
  3. A frozen, documented go/no-go result exists (e.g. `results/sentiment_backtest.json` + a written report) stating pass/fail against a defined significance bar, mirroring the project's "no un-backtested model ships" discipline
  4. The result closes SENT-01/SENT-02 regardless of outcome — a "no-go" report is accepted as complete and unblocks nothing further in this milestone; a "go" report specifies which adjustment approach cleared the bar, scoping Phase 18

**Plans**: 2 plans

Plans:
**Wave 1**

- [x] 16-01-PLAN.md — Monthly sentiment predictor loader (UTC+8-corrected) and leakage-guarded merge helper with tests (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 16-02-PLAN.md — Run the causality screen against the real HDAN/PPAN/Diesel-USD/FX series, freeze `results/sentiment_causality_screen.json` and generate `REPORT-SENTIMENT.md` (wave 2)

### Phase 17: Weekly Forecast Re-Research Spike

**Goal**: Re-research weekly-cadence HDAN/PPAN forecasting with genuinely new candidate variables and/or model families (not a rerun of the prior weekly-VAR-on-Baltic-AN/Ammonia/Urea/Natural-Gas no-go), and produce a documented go/no-go comparison against the prior spike's exact benchmark (9.49%/10.08% monthly MAPE). No weekly UI ships in this milestone regardless of the outcome — this phase is research-only.
**Depends on**: Nothing (independent of Phase 16; reuses the existing walk-forward, horizon-matched backtest methodology)
**Requirements**: WKLY-01, WKLY-02
**Success Criteria** (what must be TRUE):

  1. The re-research backtest tests candidate variables and/or model families not used in the prior spike (e.g. SARIMAX/ExponentialSmoothing at weekly cadence, Baltic-AN dedup resolution), using the same walk-forward, horizon-matched methodology as before
  2. A documented go/no-go report exists with an explicit side-by-side comparison against the prior spike's exact benchmark figures (9.49%/10.08% monthly MAPE)
  3. The report closes WKLY-01/WKLY-02 regardless of outcome; no `app/` code changes occur in this phase and no weekly UI ships this milestone even if the result is a go

**Plans**: 2 plans

Plans:
**Wave 1**

- [x] 17-01-PLAN.md — Patch data_loader.py to repo-root-relative paths and resolve the Baltic-AN dedup question with a frozen verdict (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 17-02-PLAN.md — Run weekly-cadence SARIMAX/ExponentialSmoothing candidates via the shared walk-forward harness, freeze `results/weekly_sarimax_ets.json` and generate `REPORT-WEEKLY.md` with the go/no-go comparison against the 9.49%/10.08% benchmark (wave 2)

### Phase 18: Sentiment-Adjusted Scenario UI (conditional on Phase 16 go)

**Goal**: If Phase 16 returns a go, surface a sentiment-adjusted bull/bear band on the existing fan chart with honest provenance, staleness/coverage warnings, and a toggle — strictly additive to, and never mutating or replacing, the existing backtested statistical band. If Phase 16 returns a no-go, this phase is dropped from the milestone rather than built in a degraded form.
**Depends on**: Phase 16 (requires a "go" result; not started otherwise)
**Requirements**: SENT-03, SENT-04, SENT-05, SENT-06, SENT-07, SENT-08
**Success Criteria** (what must be TRUE):

  1. User sees a sentiment-adjusted bull/bear band on the existing fan chart, visually distinguished (e.g. dashed) from the statistical band, which is never mutated or replaced
  2. A provenance line near the chart shows the sentiment score's date range, article count, and mean/weighted score, honestly labeled "general market sentiment" — never presented as commodity- or Mongolia-specific news
  3. A staleness/coverage warning appears when the sentiment data doesn't cover the requested period or is stale
  4. User can view the top 3-5 headlines by absolute sentiment score behind a given sentiment adjustment, and a sample-size confidence flag appears when scores are based on very few articles
  5. User can toggle between a statistical-only view and a statistical+sentiment view of the scenario bands

**Plans**: TBD
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
| 16. Sentiment Data Sufficiency & Causality Research | 0/0 | Not started | - |
| 17. Weekly Forecast Re-Research Spike | 0/0 | Not started | - |
| 18. Sentiment-Adjusted Scenario UI (conditional) | 0/0 | Not started | - |

---
*Roadmap created: 2026-08-21*
*v1.2 phases (7-10) added: 2026-08-24*
*v1.3 phases (11-15) added: 2026-08-24*
*v2.0 phases (16-18) added: 2026-08-31*
*Granularity: coarse*
