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
- Live news/sentiment-driven bull/bear scenario adjustment — explicitly deferred to v2;
  provider selection (news API + LLM scoring vs. a dedicated market-data provider) is an
  open research question, not decided yet
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
| v1 scenarios = base ± statistical spread; live news/sentiment integration deferred to v2 | Keeps v1 scope shippable; news-provider selection is still an open research question | — Pending |
| No file-upload UI in v1 — manual in-app entry + Excel export instead | User explicitly requested this during brainstorming, reversing an earlier upload-first draft | — Pending |

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
*Last updated: 2026-08-21 after initialization*
