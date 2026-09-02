# Requirements — Prediction Dashboard (Reflex forecasting app)

No active milestone requirements defined yet. Run `/gsd-new-milestone` to start the next
milestone (questioning → research → requirements → roadmap).

Shipped milestones' requirements (v1 through v2.1) are archived in `.planning/milestones/`.

## Backlog

- **Weekly Data Entry UI** — v2.1 shipped weekly forecast *viewing* only (HDAN/PPAN/FX,
  toggle-driven). Manually entering new weekly actuals in-app was explicitly deferred; the
  existing monthly Data Entry tab remains the only way to add data. Would need its own
  design pass (weekly-cadence table, validation, likely a per-series-aware UI since
  Diesel-USD/Diesel-MNT have no weekly concept at all).
- **Sentiment-adjusted scenario UI (SENT-03..08)** — Phase 16's (v2.0) causality screen
  returned "no-go" for all four series (effective monthly sample size never reached the
  required floor). This branch is closed, not merely deferred — it would need materially
  more sentiment-archive coverage (continuous, commodity/FX-relevant, spanning at least
  `MIN_GRANGER_N=24` overlapping months) before it's worth re-attempting. See
  `backend_research/REPORT-SENTIMENT.md`'s "What would change this result" section.
- Sentiment trend mini-chart (sent_ema3/sent_ema10/sent_momentum) — moot unless the
  sentiment-adjustment branch above is ever revisited.
- Automatic API data-fetch from external price sources — only relevant if/when the
  "connect to a data API" idea is picked up as its own milestone.
- Extending the weekly forecast horizon beyond 5 weeks — needs its own backtest evidence
  first, per the project's "no un-backtested model ships" discipline. Current weekly
  models (HDAN/PPAN from v2.0's Phase 17, FX from v2.1's Phase 20) are validated only to
  h=5 weeks.
- Weekly Daily-cadence data — `FX Data.csv`'s Daily column exists and is unused; no
  stated need for daily-granularity forecasting has come up.

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
- Per-series granularity mixing/override — a single global Monthly/Weekly toggle is the
  locked design (avoids "two reading speeds on one screen")
- Auto-defaulting the dashboard to Weekly mode — default stays Monthly regardless of
  which granularity's models are more accurate

(Full rationale for the v1-v2.0 items in `.planning/milestones/v2.0-REQUIREMENTS.md`'s
"Out of Scope" section, carried forward unchanged.)
