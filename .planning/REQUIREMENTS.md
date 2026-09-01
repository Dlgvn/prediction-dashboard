# Requirements — Prediction Dashboard (Reflex forecasting app)

## v2.1 Requirements

### Weekly Data Foundation

- [ ] **WKUI-01**: The app has genuine weekly-cadence historical data for HDAN, PPAN, and
      FX rate — sourced from `AN Data.csv` (native weekly) and `FX Data.csv`'s Weekly
      column, never resampled/interpolated from monthly data — persisted separately from
      the existing monthly `PriceRow` table
- [ ] **WKUI-02**: A backtested weekly-cadence FX forecasting model exists, compared
      explicitly against the existing monthly FX benchmark (1.72% MAPE, AR(1)/Naive), with
      a documented, frozen go/no-go verdict — a "no-go" is a valid, complete outcome (FX
      stays monthly-only in the UI if so), not a blocker to closing this requirement

### Weekly Forecast UI

- [ ] **WKUI-03**: User can toggle between Monthly and Weekly forecast granularity from the
      dashboard, with the toggle driving both the Forecast tab chart and Summary cards
      together (a single global setting, not independent per-series toggles)
- [ ] **WKUI-04**: The selected granularity persists across page reloads/visits
- [ ] **WKUI-05**: When Weekly is selected, Diesel-USD and Diesel-MNT cards show an
      explicit, always-visible "monthly only" disabled/muted state — never hidden, never
      showing fabricated or interpolated weekly data for these series
- [ ] **WKUI-06**: When Weekly is selected, the forecast horizon is controlled in weeks
      (not a relabeled month slider), capped to the range actually covered by the weekly
      backtest(s)
- [ ] **WKUI-07**: When Weekly is selected, each weekly-capable series' summary card shows
      the correct weekly model name and its backtested MAPE (not a stale monthly figure)
- [ ] **WKUI-08**: Weekly forecast chart/table dates use real week-ending dates, not
      relabeled monthly tick marks

## Backlog carried forward from v2.0

- **Sentiment-adjusted scenario UI (SENT-03..08)** — Phase 16's causality screen returned
  "no-go" for all four series (effective monthly sample size never reached the required
  floor). This branch is closed, not merely deferred — it would need materially more
  sentiment-archive coverage (continuous, commodity/FX-relevant, spanning at least
  `MIN_GRANGER_N=24` overlapping months) before it's worth re-attempting. See
  `backend_research/REPORT-SENTIMENT.md`'s "What would change this result" section.
- Sentiment trend mini-chart (sent_ema3/sent_ema10/sent_momentum) — moot unless the
  sentiment-adjustment branch above is ever revisited.
- Automatic API data-fetch from external price sources — only relevant if/when the
  "connect to a data API" idea is picked up as its own milestone.

## v2.1+ Requirements (Deferred)

- Weekly Data Entry UI (manual weekly actuals for HDAN/PPAN/FX) — this milestone is
  forecast-viewing only; the existing monthly Data Entry tab is unaffected and unchanged.
- Per-series granularity mixing/override — a single global Monthly/Weekly toggle is the
  locked design (avoids "two reading speeds on one screen"); per-series overrides are an
  anti-feature per FEATURES.md research.
- Extending the weekly forecast horizon beyond what's actually backtested — any future
  horizon extension needs its own backtest evidence first, per the project's "no
  un-backtested model ships" discipline.
- Auto-defaulting the dashboard to Weekly mode — default stays Monthly; Weekly is an
  opt-in toggle, not a replacement default, even if weekly models prove more accurate.

## Out of scope (standing, not milestone-specific)

- Live/auto-refreshing news polling for sentiment
- SHAP or other formal explainability tooling
- Full in-app article reader / news browser
- Open-ended multi-granularity picker beyond Monthly/Weekly
- Auto-interpolating synthetic weekly points for series without weekly source data
- Multi-user accounts / authentication
- Configurable/pluggable model selection in the UI
- Real-time/streaming price updates
- Fully general interactive charting toolbox (pan/zoom/brush/drill-down)
- Porting the Excel workbook's exact model coefficients
- CSV import column-mapping UI or fuzzy header matching
- CSV import overwrite-on-duplicate-date
- "Drivers" / forecast-attribution explanation text

(Full rationale for each in `.planning/milestones/v2.0-REQUIREMENTS.md`'s "Out of Scope"
section, carried forward unchanged.)

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| WKUI-01 | Phase 19 | Pending |
| WKUI-02 | Phase 20 | Pending |
| WKUI-03 | Phase 22 | Pending |
| WKUI-04 | Phase 22 | Pending |
| WKUI-05 | Phase 22 | Pending |
| WKUI-06 | Phase 22 | Pending |
| WKUI-07 | Phase 22 | Pending |
| WKUI-08 | Phase 22 | Pending |

---
*Requirements defined: 2026-08-21 (v1 baseline); v2.1 requirements added: 2026-09-01*
*Shipped milestones' requirements (v1 through v2.0) archived in `.planning/milestones/`.*
*v2.1 traceability mapped to Phases 19-22: 2026-09-01*
