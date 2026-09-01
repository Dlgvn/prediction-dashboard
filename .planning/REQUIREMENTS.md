# Requirements — Prediction Dashboard (Reflex forecasting app)

No active milestone requirements defined yet. Run `/gsd-new-milestone` to start the next
milestone (questioning → research → requirements → roadmap).

Shipped milestones' requirements (v1 through v2.0) are archived in `.planning/milestones/`.

## Backlog carried forward from v2.0

These items were identified during v2.0 but deliberately not built this milestone. They are
candidates for a future milestone, not commitments:

- **Weekly forecast mode UI** — Phase 17's re-research spike returned a "go"
  (weekly-cadence SARIMAX/ETS candidates beat the monthly VAR benchmark for HDAN/PPAN,
  see `backend_research/REPORT-WEEKLY.md`), but no weekly UI shipped in v2.0 by design.
  Building it needs its own planning cycle: a new weekly-cadence table, a per-series-aware
  dispatcher, and partial-coverage UX design (Diesel/FX/Diesel-MNT stay monthly-only, so the
  UI must handle mixed cadence honestly).
- **Sentiment-adjusted scenario UI (SENT-03..08)** — Phase 16's causality screen returned
  "no-go" for all four series (effective monthly sample size never reached the required
  floor). This branch is closed, not merely deferred — it would need materially more
  sentiment-archive coverage (continuous, commodity/FX-relevant, spanning at least
  `MIN_GRANGER_N=24` overlapping months) before it's worth re-attempting. See
  `backend_research/REPORT-SENTIMENT.md`'s "What would change this result" section.
- Per-series weekly capability badge, weekly-specific MAPE display — depend on the weekly
  UI milestone above shipping first.
- Sentiment trend mini-chart (sent_ema3/sent_ema10/sent_momentum) — moot unless the
  sentiment-adjustment branch above is ever revisited.
- Automatic API data-fetch from external price sources — only relevant if/when the
  "connect to a data API" idea is picked up as its own milestone.

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
