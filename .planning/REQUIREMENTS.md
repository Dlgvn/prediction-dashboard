# Requirements — Prediction Dashboard (Reflex forecasting app)

## v1.2 Requirements

### Data Entry & Persistence

- [x] **DATA-07**: Data Entry table defaults to showing only the recent months (not all
      167+ rows since 2013), fixing the unusable/hanging table found at real data scale
      (167 rows × 17 columns = ~2,950 editable DOM cells)
- [x] **DATA-08**: User can toggle "show all history" to reveal the full table when they
      need to edit older rows, without permanently degrading performance for the common case

### Forecast Context

- [x] **FCST-08**: Each forecast summary card shows the series' historical high and low
      (computed from stored actuals), giving the user range context beyond just the
      forecast band
- [x] **FCST-09**: Each forecast summary card shows a year-over-year percentage change
      alongside the existing vs.-latest-actual direction indicator

### Data Portability

- [x] **EXPORT-02**: Excel export includes a forecast sheet (base/bull/bear values at the
      selected horizon) in addition to the existing actuals-only sheet, not actuals-only
- [ ] **IMPORT-01**: User can bulk-import historical price data via CSV upload, with a
      preview-and-confirm step before any row is written to storage
- [ ] **IMPORT-02**: CSV rows whose date already exists in storage are skipped on import
      (existing data is never overwritten by a bulk import) — the import summary tells the
      user how many rows were added vs. skipped

## v1 Requirements

### Data Entry & Persistence

- [x] **DATA-01**: User can add a new row of monthly actual prices (Date, HDAN, PPAN,
      Baltic_AN, Ammonia, Urea, Natural_Gas, Brent, Diesel_USD_ton, Urals, FX_rate)
      directly in the dashboard
- [x] **DATA-02**: User can edit an existing row's values inline, in the data table
      itself, without opening a separate modal or form
- [x] **DATA-03**: User can delete a row (with a confirm step) from the dashboard
- [x] **DATA-04**: Entered values are validated on save — numeric fields reject
      non-numeric input and implausible values (e.g. negative prices, negative FX rate)
      before they reach storage
- [x] **DATA-05**: All entered/edited/deleted rows persist in SQLite and are visible again
      after the app is restarted or the page is refreshed
- [x] **DATA-06**: Each series (HDAN, PPAN, Diesel-USD, FX) shows an "as of" / last-updated
      date so the user knows whether the data feeding the forecast is current

### Forecasting & Scenarios

- [x] **FCST-01**: User can select a forecast horizon from 1 to 12 months
- [x] **FCST-02**: For the selected horizon, the app computes a base (point), bull, and
      bear forecast value for each month, for HDAN, PPAN, Diesel-USD, and FX rate
- [x] **FCST-03**: Diesel purchasing price in MNT is computed as a derived series
      (Diesel-USD forecast × FX forecast × markup) at each horizon step, not modeled
      independently
- [x] **FCST-04**: Bull/bear spread is computed per series from that series' own
      backtested error/volatility (not one flat percentage applied to every series)
- [x] **FCST-05**: Bull/bear spread widens as the horizon extends further out, rather than
      staying a fixed percentage regardless of how many months ahead the forecast is
- [x] **FCST-06**: Forecast values are shown in a table (exact numbers per month, per
      series, per scenario) in addition to any chart — not chart-only
- [x] **FCST-07**: Forecasting models are selected via a research/backtest process before
      being used — no un-backtested model is used in the shipped app (see Model Research
      phase)

### Visualization

- [x] **VIS-01**: User can view a historical chart of actual prices (no forecast) for each
      series, to see the trend the forecast is based on
- [x] **VIS-02**: User can view a forecast chart showing base/bull/bear as a shaded
      confidence band (not three unstyled crisp lines) across the selected horizon
- [x] **VIS-03**: All four tracked series (HDAN, PPAN, Diesel-MNT, FX) are visible together
      on a single dashboard page, not requiring the user to switch between separate pages
      or tabs to see each one

### Data Portability

- [x] **EXPORT-01**: User can export the current stored price table to an `.xlsx` file

## v2 Requirements (Deferred)

- Weekly forecast mode — blocked on resolving the AN-family vs. Diesel/FX weekly
  data-cadence gap; the weekly source file (`AN price weekly.csv`) lacks HDAN/PPAN
  directly and there is no weekly Diesel/FX data at all. Needs its own research pass to
  either validate a Baltic AN → HDAN/PPAN proxy or scope weekly mode down to only the
  series that actually have weekly data.
- Live news/sentiment-driven bull/bear scenario adjustment — provider selection (news API
  + LLM sentiment scoring vs. a dedicated market-data provider) is an open research
  question, not decided. Ships as a fast-follow milestone after the core dashboard works.
- Automatic API data-fetch from external price sources — only relevant if/when the
  "connect to a data API" idea is picked up as its own milestone.

## Out of Scope

- Multi-user accounts / authentication — single local user matches the existing Excel
  workbook's actual usage pattern; no value for one person on one machine.
- Configurable/pluggable model selection in the UI (user picking ARIMA vs. VAR vs. ML from
  a dropdown) — model selection is a backend research/backtest decision made once, offline,
  not a per-session user toggle.
- Real-time/streaming price updates — this is a monthly-cadence, manually-entered dataset;
  there is no live feed to poll or stream.
- Fully general interactive charting toolbox (pan/zoom/brush/drill-down) — disproportionate
  for 4 series and at most 12 data points per horizon; a simple chart with basic hover
  tooltip is sufficient.
- Porting the Excel workbook's exact model coefficients — this project does fresh model
  selection/research rather than reusing the workbook's specific VAR/AR coefficients.
- CSV import column-mapping UI or fuzzy header matching — v1.2's CSV import uses a fixed
  schema matching the app's own export format; column mapping is an enterprise SaaS pattern
  disproportionate to this single-user app (v1.2 research finding).
- CSV import overwrite-on-duplicate-date — v1.2 explicitly skips duplicate dates rather than
  overwriting; overwrite semantics were considered and rejected in favor of the simpler,
  safer "never silently overwrite existing data via bulk import" behavior.
- "Drivers" / forecast-attribution explanation text — deferred; would require either a
  static per-series caption (low value) or real model-coefficient attribution (a forecasting
  research question, not a v1.2 stack/UI question) per v1.2 research findings.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 4 | Complete |
| DATA-02 | Phase 4 | Complete |
| DATA-03 | Phase 4 | Complete |
| DATA-04 | Phase 4 | Complete |
| DATA-05 | Phase 4 | Complete |
| DATA-06 | Phase 5 | Complete |
| FCST-01 | Phase 5 | Complete |
| FCST-02 | Phase 3 | Complete |
| FCST-03 | Phase 3 | Complete |
| FCST-04 | Phase 3 | Complete |
| FCST-05 | Phase 3 | Complete |
| FCST-06 | Phase 5 | Complete |
| FCST-07 | Phase 2 | Complete |
| VIS-01 | Phase 4 | Complete |
| VIS-02 | Phase 5 | Complete |
| VIS-03 | Phase 5 | Complete (resolved per CONTEXT D-03 via the combination of the selector-driven forecast chart and the all-series forecast table, not by the chart alone) |
| EXPORT-01 | Phase 5 | Complete |
| DATA-07 | Phase 7 | Not started |
| DATA-08 | Phase 7 | Not started |
| FCST-08 | Phase 8 | Not started |
| FCST-09 | Phase 8 | Not started |
| EXPORT-02 | Phase 9 | Complete |
| IMPORT-01 | Phase 10 | In Progress (parsing core + DB write path done, UI + human verification pending) |
| IMPORT-02 | Phase 10 | In Progress (parsing core + DB write path done, UI + human verification pending) |

---
*Requirements defined: 2026-08-21*
