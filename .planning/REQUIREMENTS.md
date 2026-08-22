# Requirements — Prediction Dashboard (Reflex forecasting app)

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
- [ ] **DATA-06**: Each series (HDAN, PPAN, Diesel-USD, FX) shows an "as of" / last-updated
      date so the user knows whether the data feeding the forecast is current

### Forecasting & Scenarios

- [ ] **FCST-01**: User can select a forecast horizon from 1 to 12 months
- [x] **FCST-02**: For the selected horizon, the app computes a base (point), bull, and
      bear forecast value for each month, for HDAN, PPAN, Diesel-USD, and FX rate
- [x] **FCST-03**: Diesel purchasing price in MNT is computed as a derived series
      (Diesel-USD forecast × FX forecast × markup) at each horizon step, not modeled
      independently
- [x] **FCST-04**: Bull/bear spread is computed per series from that series' own
      backtested error/volatility (not one flat percentage applied to every series)
- [x] **FCST-05**: Bull/bear spread widens as the horizon extends further out, rather than
      staying a fixed percentage regardless of how many months ahead the forecast is
- [ ] **FCST-06**: Forecast values are shown in a table (exact numbers per month, per
      series, per scenario) in addition to any chart — not chart-only
- [x] **FCST-07**: Forecasting models are selected via a research/backtest process before
      being used — no un-backtested model is used in the shipped app (see Model Research
      phase)

### Visualization

- [ ] **VIS-01**: User can view a historical chart of actual prices (no forecast) for each
      series, to see the trend the forecast is based on
- [ ] **VIS-02**: User can view a forecast chart showing base/bull/bear as a shaded
      confidence band (not three unstyled crisp lines) across the selected horizon
- [ ] **VIS-03**: All four tracked series (HDAN, PPAN, Diesel-MNT, FX) are visible together
      on a single dashboard page, not requiring the user to switch between separate pages
      or tabs to see each one

### Data Portability

- [ ] **EXPORT-01**: User can export the current stored price table to an `.xlsx` file

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
- File-upload / bulk CSV import UI — may return if the API-connection idea is picked up,
  since ingestion design would change together at that point.

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

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 4 | Complete |
| DATA-02 | Phase 4 | Complete |
| DATA-03 | Phase 4 | Complete |
| DATA-04 | Phase 4 | Complete |
| DATA-05 | Phase 4 | Complete |
| DATA-06 | Phase 5 | Pending |
| FCST-01 | Phase 5 | Pending |
| FCST-02 | Phase 3 | Pending (HDAN done in 03-02; PPAN/Diesel/FX in 03-03; dispatcher in 03-04) |
| FCST-03 | Phase 3 | Complete |
| FCST-04 | Phase 3 | Pending (HDAN done in 03-02; PPAN/Diesel/FX in 03-03; dispatcher in 03-04) |
| FCST-05 | Phase 3 | Pending (HDAN done in 03-02; PPAN/Diesel/FX in 03-03; dispatcher in 03-04) |
| FCST-06 | Phase 5 | Pending |
| FCST-07 | Phase 2 | Complete |
| VIS-01 | Phase 4 | Pending |
| VIS-02 | Phase 5 | Pending |
| VIS-03 | Phase 5 | Pending |
| EXPORT-01 | Phase 5 | Pending |

---
*Requirements defined: 2026-08-21*
