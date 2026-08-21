# Reflex Forecasting Dashboard — Design

*2026-08-21. Companion project to the existing Excel workbook
(`AN_HDAN_PPAN_Diesel_FX_Forecast_Model.xlsx`, see `PROJECT_VISION.md`). This is a
deliberate scope expansion — a web dashboard, not a replacement for the workbook —
built with a fresh (not ported) model design, per the roadmap's "decide, don't drift"
principle.*

## 1. What this is

A Reflex (Python-only web framework) dashboard, for the same single procurement/budgeting
user, that forecasts the same four deliverables — **HDAN, PPAN, Diesel purchasing price
(MNT), USD/MNT FX rate** — but adds three things the Excel workbook doesn't have:

- **Adjustable horizon**: user picks 1–12 months ahead (or N weeks, in weekly mode),
  not just next-month.
- **Three scenario lines per forecast**: base / bull / bear, not a single point + band.
- **In-app data entry and Excel export**, replacing "open Excel, add a row" with a
  dashboard table the user edits directly, with an export button for portability.

## 2. Architecture

Single Reflex app in `app/` (new subfolder in this project), one Python process serving
both UI and backend — no separate API service. SQLite via Reflex's built-in model layer
for persistence. Forecasting logic lives in its own Python module(s), independent of the
UI, so it can be unit-tested and so models can be swapped as research (§4) picks winners.

**Why not a split frontend/backend (FastAPI) or Postgres:** single user, occasional use —
matches the existing project's scale. Revisit only if multi-user or cloud-hosting becomes
a real requirement, not preemptively.

## 3. Data flow

1. **Seed once**: `AN price weekly.csv`, `AN Data.csv`, and `Diesel Data.csv` are loaded
   into SQLite at setup time to bootstrap history and to train/backtest candidate models
   during research (§4). This is a one-time import script, not an ongoing upload feature.
2. **Ongoing entry — manual only, in-dashboard**: a data table on the dashboard lets the
   user add or edit rows of actual prices directly (Date, HDAN, PPAN, Baltic_AN, Ammonia,
   Urea, Natural_Gas, Brent, Diesel_USD_ton, Urals, FX_rate) — mirrors the Excel workbook's
   "add one row per month to Input" workflow, done in-app instead. **No file-upload UI in
   v1** — that's explicitly deferred, not an oversight.
3. **Export**: a button exports the current stored table to `.xlsx`, so data stays
   portable/shareable outside the app even without an upload path back in.
4. **Forecast**: user picks a horizon (1–12 months, or N weeks in weekly mode) and
   triggers a run against the stored table; backend computes base/bull/bear per product
   out to that horizon.
5. **Display**: a chart renders the three scenario lines across the horizon; a table below
   shows the same numbers.

## 4. Forecasting engine — research-first, not pre-selected

Per your request, the model isn't picked in this design doc. The next phase repeats the
`backend_research/` pattern that produced the Excel workbook's models: candidates
(statsmodels ARIMA/SARIMAX/VAR — same family already prototyped there — plus at least one
ML baseline such as gradient boosting) get backtested per product on holdout months, and
the winner(s) get used. This is a research task in planning/execution, not a decision made
here.

## 5. Scenarios (bull / base / bear)

- **v1 (ships first)**: base = model point forecast; bull/bear = base ± a statistical
  spread (backtest error or historical volatility) — same spirit as the workbook's ±MAPE
  band, computed dynamically instead of pasted from a static report.
- **v2 (fast-follow, not required for v1)**: live news/sentiment integration adjusts
  bull/bear based on external factors (e.g. market news, industry perspective). News
  source/provider is an open research question — leading candidate is a news API + LLM
  sentiment scoring, but MNT/Mongolia-specific and commodity-specific coverage needs
  checking before committing to a provider. **v1 does not depend on this.**

## 6. Weekly mode — known data gap

`AN price weekly.csv` has Baltic AN, Ammonia, Urea, Natural Gas — **not** HDAN/PPAN
directly — and there is no weekly Diesel/FX data at all. Weekly mode therefore needs one
of:

- (a) a proxy relationship (Baltic AN → HDAN/PPAN) validated during model research, or
- (b) weekly mode scoped to only the products that actually have weekly data, with
  Diesel/FX staying monthly-only regardless of the mode the user picks.

This gets resolved during research/planning, not guessed here — flagged so it isn't
discovered as a surprise mid-build.

## 7. What v1 explicitly does not include

- No file-upload UI (data entry is manual/in-app only; upload may return in a later
  milestone if the "future API connection" idea gets picked up).
- No live news/sentiment integration (v2 fast-follow, §5).
- No multi-user auth — single local user, matching the existing workbook's usage pattern.
- No automatic API data-fetch — the user's "might connect an API in future" note is a
  future milestone, not v1 scope.

## 8. Relationship to the existing Excel workbook

The workbook is untouched and remains the live, formula-based reference. This dashboard
is a separate, parallel deliverable with its own (to-be-researched) models — not a port,
not a replacement. Both read from the same underlying source data but maintain independent
storage (workbook's `Input` tab vs. this app's SQLite table).
