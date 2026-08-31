# Prediction Dashboard

## What This Is

A Reflex (Python) web dashboard that forecasts commodity and FX prices — ammonium
nitrate (HDAN, PPAN), imported diesel purchasing price (MNT), and the USD/MNT exchange
rate — for one person doing procurement or budgeting, who wants to know "what am I
likely to pay, N months (or weeks) from now, and with what range of outcomes?" It's a
companion to (not a replacement for) an existing live-formula Excel workbook
(`AN_HDAN_PPAN_Diesel_FX_Forecast_Model.xlsx`) that already does this forecasting job in
spreadsheet form; this project adds a web UI with adjustable horizon, bull/base/bear
scenario charting, in-app data entry, and Excel export.

## Core Value

The user can enter a month's actuals, pick a forecast horizon (1-12 months, or N weeks),
and see a chart with three price scenarios (bull/base/bear) for each of the four
tracked series — without opening Excel.

## Requirements

### Validated

- ✓ Forecasting HDAN, PPAN, Diesel-USD, and USD/MNT FX from historical monthly data using
  statistical models (VAR for HDAN/PPAN, AR-lag-2-on-Brent for Diesel, AR(1) for FX) —
  proven in the existing Excel workbook and its `backend_research/` backtests (HDAN 9.4%
  MAPE, PPAN 10.0%, Diesel-USD 3.4%, FX 0.25%, 12-month holdout)
- ✓ Deriving Diesel purchasing price in MNT as Diesel-USD forecast × FX forecast ×
  markup — existing workbook formula, backtested markup of 2.82%

### Active

- [ ] User can add/edit rows of monthly actual prices directly in the dashboard UI (no
      file upload in v1)
- [ ] User can export the stored price table to an Excel (.xlsx) file
- [ ] User can pick a forecast horizon from 1-12 months
- [ ] User can (in a later phase, pending weekly-data-gap research) pick weekly instead
      of monthly granularity
- [ ] Dashboard shows base/bull/bear forecast values for HDAN, PPAN, Diesel-USD, FX rate,
      and derived Diesel-MNT, out to the chosen horizon
- [ ] Dashboard renders the three scenario lines on a chart across the horizon
- [ ] v1 bull/bear = base ± a statistical spread (backtest error/volatility), not a fixed
      band
- [ ] Forecasting models are chosen via a research-first process (test ARIMA/SARIMAX/VAR
      via statsmodels plus at least one ML baseline, backtest per product, pick winners) —
      not pre-selected in this document
- [ ] Data persists across sessions (SQLite), not re-entered each time

### Out of Scope

- File-upload UI for bulk CSV import — v1 is manual in-app entry only; may return in a
  future milestone if the "connect to a data API" idea gets picked up
- Multi-user authentication — single local user, matching how the existing Excel
  workbook is used
- Automatic API data-fetch from external price sources — user's "might connect an API in
  future" note is a future milestone, not v1
- Porting the Excel workbook's exact model coefficients — this project does fresh model
  selection/research rather than reusing the workbook's specific VAR/AR coefficients
  (though it may land on similar model families)

## Context

- **Existing system**: a live-formula Excel workbook (5 tabs: Input, PctChange,
  Regression, Forecast, Dashboard) already forecasts these same four series one month
  ahead, built and documented in `README.md`, `PROJECT_VISION.md`, and `MANUAL.md`. Its
  research phase (`backend_research/`) already prototyped ARIMA/VAR/SARIMAX candidates in
  Python and produced a backtest report (`backend_research/REPORT.md`) — useful prior art
  even though this project chooses its own models rather than porting the workbook's.
- **Source data**: `AN Data.csv` (weekly-cadence entries, AN-family series from 2022-08),
  `Diesel Data.csv` (monthly, Diesel/FX/crude series from 2020-02), and `AN price
  weekly.csv` (true weekly cadence, but covers Baltic AN/Ammonia/Urea/Natural Gas — not
  HDAN/PPAN directly, and no weekly Diesel/FX exists at all). This is a known gap for
  weekly-mode forecasting that needs resolving during model research before weekly mode
  can ship (see design doc §6).
- **Prior design work**: this project was scoped through a full brainstorming session
  before GSD was invoked. Design doc: `docs/plans/2026-08-21-reflex-dashboard-design.md`.
  Task-by-task implementation plan: `docs/plans/2026-08-21-reflex-dashboard-implementation.md`.
  Both were written via the brainstorming/writing-plans skills, not GSD, but capture real
  decisions and should be treated as authoritative source material, not just background.
- **Deployment/usage pattern**: single user, occasional (roughly monthly) use — this
  shapes architecture choices (SQLite over Postgres, one Reflex process rather than a
  split frontend/backend service).

## Constraints

- **Tech stack**: Reflex (Python-only web framework), SQLite via Reflex's `rx.Model`,
  statsmodels for forecasting, pandas/openpyxl for data handling and Excel export — chosen
  during brainstorming for single-process simplicity matching single-user scale.
- **Data cadence mismatch**: source data mixes weekly (AN-family) and monthly
  (Diesel/FX) cadence; weekly forecasting mode is blocked on research into whether a
  usable proxy relationship exists (design doc §6).
- **Model provenance**: forecasting models must go through a research/backtest step
  (mirroring `backend_research/`) before being used in the app — no un-backtested model
  ships to the dashboard.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Reflex + SQLite single-process monolith (not split FastAPI service, not Postgres) | Matches single-user, occasional-use scale; simplest to run/deploy | — Pending |
| Fresh model design/research rather than porting the Excel workbook's exact coefficients | User explicitly chose this during brainstorming over reusing the workbook's VAR/AR models | — Pending |
| No file-upload UI in v1 — manual in-app entry + Excel export instead | User explicitly requested this during brainstorming, reversing an earlier upload-first draft | — Pending |
| v2 weekly-forecast-mode work is a research spike (re-research before shipping), not a committed build | v1.2-era backtest was a no-go: weekly-native VAR underperformed monthly (10.35%/16.01% vs 9.49%/10.08% MAPE) and no weekly Diesel/FX data exists at all — must clear a new backtest bar before any weekly UI ships | — Pending |
| v2 news/sentiment scenario feature builds on the existing `archive/` dataset (news_sentiment_daily.csv, sentiment_market_panel.csv, ml_features.csv, raw news dump) rather than researching a provider from scratch | User confirmed this data was prepared for this purpose | — Pending |

## Milestone History

### v1.2 Data Entry Fix & Forecast Enrichment (complete)
Fixed the Data Entry table's usability at real data scale (12-month default window + "show all history" toggle), added historical high/low + YoY context to summary cards, added a Forecast sheet to Excel export, and added CSV bulk import with preview/confirm and duplicate-date skipping.

### v1.3 Dashboard Polish & Data-Entry Rework (complete)
Fixed the transparent html/body background bug (black margins on wide/dark-mode viewports), added a persisted dark/light toggle, added a tab/nav bar between page sections, showed per-series model name + backtest accuracy near the forecast, fixed the fan chart's overlapping axis label/legend, and reworked Data Entry to root-cause and fix the silent-validation bug (native date picker + click-away race fix).

## Current Milestone: v2.0 News/Sentiment Scenarios & Weekly Forecast Research

**Goal:** Add live news/sentiment-driven bull/bear scenario adjustment on top of the existing statistical-spread scenarios, and resolve whether weekly-granularity forecasting can clear a real backtest bar before building any weekly UI.

**Target features:**
- Research and backtest a news/sentiment-driven adjustment to the bull/bear scenario bands, built on the `archive/` dataset (news_sentiment_daily.csv, sentiment_market_panel.csv, ml_features.csv, raw news dump)
- Surface the sentiment-adjusted scenarios in the existing forecast chart/UI, with provenance (what's driving the adjustment) shown to the user
- Re-research weekly-granularity forecasting as a spike: try new approaches/data for HDAN/PPAN (which have real weekly data) and confirm whether Diesel/FX remain permanently monthly-only; only proceed to a shipped weekly UI mode if a new backtest actually beats the prior no-go result

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-31 at start of v2.0 milestone*
