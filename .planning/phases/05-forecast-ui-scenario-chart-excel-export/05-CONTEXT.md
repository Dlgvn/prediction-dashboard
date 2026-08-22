# Phase 5: Forecast UI, Scenario Chart & Excel Export - Context

**Gathered:** 2026-08-22
**Status:** Ready for planning

<domain>
## Phase Boundary

The user can select a forecast horizon (1-12 months), see base/bull/bear scenarios for all
tracked series on the dashboard page, view a freshness indicator per series, and export the
stored actuals table to Excel. This is the final phase — it builds on Phase 3's forecasting
module (`forecast_all()`) and Phase 4's data entry UI/page, adding the last UI section
(horizon slider, forecast chart, forecast table, freshness labels, export button) below
what Phase 4 already built. It does NOT change Phase 3's forecasting logic or Phase 4's
data-entry/historical-chart UI.

</domain>

<decisions>
## Implementation Decisions

### Horizon selector
- **D-01:** A slider (not dropdown, not stepper) selects the horizon, range 1-12 months.
- **D-02:** The forecast recomputes live on every slider change (no explicit "Forecast"
  button) — justified by Phase 3's D-06, which established models refit in milliseconds
  at this data scale, so live recompute has no perceptible lag.

### Multi-series forecast layout (VIS-03 resolution)
- **D-03 (resolves a real VIS-03 wording tension, not just a UI preference):** The
  forecast chart uses ONE chart with a series selector/toggle, matching Phase 4's
  historical-chart pattern — only one series' scenario band is visible on the chart at a
  time. This appears to conflict with VIS-03's literal wording ("all four tracked series
  visible together... not requiring the user to switch"), but is resolved by FCST-06's
  forecast table: the table lists ALL FOUR series' base/bull/bear numbers together,
  simultaneously, satisfying VIS-03's spirit (all four "visible together") through the
  table rather than the chart. This was an explicit, discussed trade-off — not an
  oversight. Downstream planner should treat VIS-03 as satisfied by the combination of
  (selector-chart + all-series table), not by the chart alone.

### Confidence band rendering (VIS-02)
- **D-04:** Bull/bear renders as a filled/shaded area (two boundary traces with
  `fill='tonexty'`-style fill between them), with a solid base-forecast line drawn on top
  — the standard fan-chart pattern. Not 3 separate crisp lines (which VIS-02 explicitly
  rejects), and not a fill-only band without a visible base line (would lose the readable
  point-forecast number).
- **D-05:** The forecast chart includes 12 months of recent historical actuals leading
  into the forecast band, not a forecast-only view — gives visual continuity/context for
  judging whether the forecast looks plausible against the recent trend. This chart is
  separate from Phase 4's historical chart (which shows full history, all 16 series); this
  one is scoped to the 4 forecast series with a 12-month trailing window plus the horizon.

### Page layout & freshness indicator
- **D-06:** Phase 5's new UI sections append below Phase 4's existing content, in build
  order: data table → historical chart (Phase 4) → horizon slider → forecast chart →
  forecast table → export button (Phase 5). No tabs, no reorganization of Phase 4's
  layout — matches the natural top-to-bottom narrative (enter/review data, see history,
  see forecasts, export).
- **D-07:** DATA-06's "as of" freshness date appears as a small label above the forecast
  section, one per series (e.g. "HDAN as of 2026-07-01") — shown where the user is about
  to trust a forecast built from that data, not buried in Phase 4's data table.

### Export (EXPORT-01) — no gray area, confirming existing design
- **D-08:** Export produces an `.xlsx` file of the currently stored actuals table (the
  same data Phase 4's editable table shows) — not a forecast export. This matches the
  original project design doc's intent (`docs/plans/2026-08-21-reflex-dashboard-design.md`
  §3) and wasn't re-litigated as a gray area since no conflicting interpretation was
  raised.

### Claude's Discretion
None flagged this round — all four presented gray areas were explicitly decided, with
follow-up rounds on VIS-03's wording tension and the historical-context window size.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & prior decisions
- `.planning/REQUIREMENTS.md` — DATA-06, FCST-01, FCST-06, VIS-02, VIS-03, EXPORT-01 are
  this phase's requirements; note D-03 above documents how VIS-03 is actually satisfied
  (selector-chart + table), which the planner should carry forward rather than
  re-interpreting VIS-03 literally
- `.planning/phases/03-forecasting-module-derived-series/03-CONTEXT.md` — D-06/D-06b
  (refit-on-every-request is cheap; GARCH uses static values) underpins D-02's live-
  recompute decision here
- `.planning/phases/04-data-entry-ui-historical-view/04-CONTEXT.md` and `04-UI-SPEC.md` —
  D-03/D-04 (series-selector historical chart pattern) is the direct precedent for D-03's
  forecast-chart selector; this phase's UI-SPEC (once generated) should stay visually
  consistent with Phase 4's approved spacing/color/typography contract rather than
  introducing a new design language
- `.planning/research/STACK.md` — confirms `rx.plotly` as the charting component (already
  used in Phase 4, same library for the fan-chart band)

### Existing code (this phase extends, doesn't replace)
- `app/app/forecasting.py` — `forecast_all(history, horizon, markup_pct)` is the function
  this phase's UI calls; returns `dict[str, list[{"month","base","bull","bear"}]]` for
  `hdan`, `ppan`, `diesel_usd_ton`, `fx_rate`, `diesel_mnt` (per Phase 3's P-02 decision)
- `app/app/state.py` — `DashboardState` (rows, historical chart state from Phase 4) this
  phase extends with horizon state, forecast results, and export logic
- `app/app/app.py` — the existing page (`index()`) this phase appends new sections to
- `app/app/models.py` — `AppSetting` holds `markup_pct`, needed as an argument to
  `forecast_all()`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 4's series-selector pattern (`selected_series` state var + `rx.select` +
  `rx.plotly` figure as a computed `@rx.var`) is directly reusable for D-03's forecast
  chart selector — same mechanism, different data source and figure construction (fan
  chart instead of a single line)
- Phase 4's `_editable_cell`/table-building helpers are not reusable here (forecast table
  is read-only, not editable) but the general `rx.table` structure/styling should stay
  consistent

### Established Patterns
- "DB is source of truth" — forecasting reads fresh from `self.rows` (already loaded from
  SQLite), consistent with Phase 3's D-06 refit-every-request and Phase 4's write-through
  pattern
- Phase 1/4's UI-SPEC-driven approach — Phase 5 should get its own UI-SPEC.md via
  `/gsd-ui-phase 5` before planning, per the project's established workflow for UI-bearing
  phases

### Integration Points
- This is the last phase — after Phase 5, the dashboard's full v1 scope (per
  REQUIREMENTS.md) is complete. No downstream phase depends on this one.

</code_context>

<specifics>
## Specific Ideas

No specific visual/styling references given beyond the decisions above — open to standard
Reflex/Plotly patterns consistent with Phase 4's approved UI-SPEC.

</specifics>

<deferred>
## Deferred Ideas

None raised outside phase scope — discussion stayed within Phase 5's boundary (horizon
selector, forecast layout, band rendering, page layout, freshness indicator).

</deferred>

---

*Phase: 5-Forecast UI, Scenario Chart & Excel Export*
*Context gathered: 2026-08-22*
