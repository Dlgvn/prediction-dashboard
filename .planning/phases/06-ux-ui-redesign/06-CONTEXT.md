# Phase 6: UX/UI Redesign — Context

**Gathered:** 2026-08-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Redesign the existing single-page Reflex dashboard (`app/app/app.py` + `app/app/state.py`) as a professional financial forecasting terminal. This phase reworks presentation and information architecture on top of the already-working Phase 1-5 functionality (data entry, historical chart, horizon slider, fan chart, base/bull/bear table, Excel export). It does NOT add new capabilities — no file upload (explicitly out of scope per PROJECT.md), no new commodities, no new forecasting logic, no auth, no weekly mode.

In scope: page layout/hierarchy, a new forecast-summary card row, visual/color design system, chart styling, table formatting, error/loading/empty state copy, responsive layout, accessibility pass.
Out of scope (belongs elsewhere or is a non-feature for this app): file upload UX, dark/light theme toggle, scalable N-commodity selector (fixed at 4 series), live news/sentiment scenarios.
</domain>

<decisions>
## Implementation Decisions

### Page structure & hierarchy
- **D-01:** New top section, above everything else: a row of 4 forecast-summary cards (HDAN, PPAN, Diesel-MNT, FX), one per tracked series, shown simultaneously — not a single-series selector. This directly satisfies PROJECT.md's "all four tracked series visible together."
- **D-02:** Below the summary cards: the fan chart (`forecast_chart_figure`), then the base/bull/bear forecast table, then freshness chips / export button — i.e. today's "Forecast" section content, reordered to sit second.
- **D-03:** The editable data-entry table (`data_table()` + `add_row_button()`) and the historical (actuals-only) chart move to the BOTTOM of the page — data entry is a secondary/maintenance task, not the first thing shown. Forecast is the primary value and goes first.
- **D-04:** Overall new order: header → forecast summary cards → horizon control → fan chart → forecast table → freshness chips/export → historical chart → data entry table.

### Visual / color system
- **D-05:** Light, neutral theme — off-white/light-gray background, dark text, ONE restrained accent color (e.g. indigo/blue) for primary actions/highlights/selection state. Red/green (or a colorblind-safe equivalent with ↑/↓ glyphs, not color alone) reserved strictly for price-direction deltas.
- **D-06:** No dark-navy terminal header treatment, no full dark-mode-as-default — go with the calmer "Stock Peer Analysis" / light CRM reference style, not the FY2026 navy-header briefing style.
- **D-07:** No light/dark theme toggle in this phase. Ship one fixed light theme. (Revisit only if the user asks in a later phase — do not build toggle infrastructure now.)

### Chart redesign
- **D-08:** Restyle the EXISTING `forecast_chart_figure` Plotly figure in `state.py` in place — do not restructure how historical vs. forecast traces are built or split the chart into multiple components. Improvements: distinguish historical vs. forecast visually (e.g. solid vs. dashed line, a vertical "forecast start" marker/annotation), clearly shaded bull/bear band, cleaner legend, hover tooltips with formatted numbers, readable date/price axis labels. Same applies to `historical_chart_figure`.
- **D-09:** Same restyle-in-place approach applies to the historical chart figure builder — no data-flow changes, purely presentational.

### Forecast summary cards
- **D-10:** Each card shows: series label, base (expected) forecast value at the END of the currently selected horizon, the bull-bear range as "Lower – Upper", and a direction indicator.
- **D-11:** Direction = base forecast (at selected horizon) vs. the latest actual entered price for that series (i.e., "is the model expecting this to go up or down from where we are today"). Render as ↑/↓ text + supporting color, not color alone.
- **D-12:** Cards are horizon-reactive: dragging `horizon_months` updates all 4 cards to reflect the new horizon-end forecast, in sync with the fan chart/table below (single shared `horizon_months` state var already exists — no new state needed beyond a computed var per card).
- **D-13:** Uncertainty language: describe the bull/bear range as a "range" or "expected range," not a "confidence interval" or "guaranteed price range" — v1 bands are backtested-error-based, not formal statistical confidence intervals (per PROJECT.md's existing framing).

### Claude's Discretion
- Exact spacing scale, typography scale, card border-radius/shadow values, specific accent hex, table number formatting precision, empty/error/loading state copy wording, responsive breakpoints, accessibility contrast tuning — apply the audit brief's general principles (professional, calm, WCAG-conscious, formatted numbers like `1,234.56`) without further user check-in.
- Whether summary cards are a new reusable component function vs. inline — implementation detail for planner/executor.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing UI/state code (primary implementation surface)
- `app/app/app.py` — current page composition (`index()`), all render functions (`data_table`, `historical_chart`, `horizon_control`, `freshness_chips_row`, `export_button`, `forecast_chart`, `forecast_table`, `forecast_section`)
- `app/app/state.py` — `DashboardState`, `SERIES_LABELS`, `FORECAST_SERIES_LABELS`, `FORECAST_TABLE_COLUMNS`, `horizon_months`, `forecast_chart_figure`, `historical_chart_figure`, `forecast_table_rows`, `freshness_chips`, `forecast_all` call site (~line 242), `load_markup_pct`
- `app/app/models.py` — `PriceRow`, `AppSetting` SQLite schema
- `app/app/forecasting.py` — `forecast_all` dispatcher (read-only reference; forecasting logic is NOT in scope for changes)

### Project-level source of truth
- `.planning/PROJECT.md` — Core Value statement, Active/Out-of-Scope requirements (confirms: no file upload in v1, 4 fixed series, no multi-user)
- `docs/plans/2026-08-21-reflex-dashboard-design.md` — original design doc; prior UI decisions (D-01..D-08 codes referenced in app.py docstrings originate here)
- `.planning/ROADMAP.md` — Phase 6 entry (goal statement, depends on Phase 5)

### Reference visual style (user-provided screenshots, not files — described in decisions above)
- Light-neutral SaaS dashboard with KPI cards + line chart + legend (primary style reference)
- Financial-terminal dark-navy header briefing (style REJECTED — do not use navy header)
- Dark-mode CRM dashboard (style REJECTED for this phase — no dark mode)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SERIES_LABELS` / `FORECAST_SERIES_LABELS` dicts in `state.py` — single source of truth for series display names; summary cards should iterate `FORECAST_SERIES_LABELS` (the 4 forecast-eligible series) rather than hardcoding.
- `_freshness_chip()` in `app.py` — existing small-card pattern (box + vstack + border) that can inform the visual language of the new summary cards for consistency.
- `forecast_table_rows` / `forecast_chart_figure` computed vars already carry horizon-reactive base/bull/bear data per series — summary cards can likely derive from the same `forecast_all()` result structure rather than recomputing.

### Established Patterns
- All chart figures are built as Plotly `go.Figure` objects inside `@rx.var`-decorated computed properties on `DashboardState` — restyling means editing these Python figure-builder functions, not touching `rx.plotly()` call sites in `app.py`.
- Render functions in `app.py` are small, composable, one-per-UI-section (`historical_chart()`, `forecast_chart()`, etc.) — new summary-card component should follow the same one-function-per-section pattern, likely `forecast_summary_cards()`.
- `rx.cond` is used throughout for empty/error state branching (e.g. `forecast_table()`'s empty state showing `forecast_error`) — follow this pattern for any new empty/error states rather than introducing a different mechanism.

### Integration Points
- `index()` (app.py ~line 322) is the single composition point — reordering the page is a matter of reordering calls inside this function plus adding one new `forecast_summary_cards()` call.
- Horizon-reactivity for summary cards: `DashboardState.horizon_months` already drives `forecast_chart_figure`/`forecast_table_rows`; a new computed var for card data should read the same `forecast_all()` result at the current horizon.

</code_context>

<specifics>
## Specific Ideas

User provided 5 reference screenshots as visual style anchors:
1. "Stock Peer Analysis" — light background, rounded pill ticker tags, purple accent buttons, best/worst performer stat cards, multi-line comparison chart with dot-legend, small "deep dive" sparkline-pair cards. **Primary style reference.**
2. "FY2026 actual-versus-budget review" — dark navy header bar with metadata chips, light KPI cards below with budget-attainment progress bars, variance bridge/driver-tree. Style (navy header) explicitly rejected; KPI-card-with-delta pattern is useful reference for summary cards.
3. "Relation CRM" (light) — greeting + stat cards with % deltas, area chart, bar chart, data table with status badges. Useful reference for stat-card + delta-badge visual language.
4. "Relation CRM" (dark preview) — same layout, dark theme. Confirms dark mode is NOT wanted for this phase.
5. "Reflex Build" generic dashboard — stat cards with delta arrows, dual-line area chart, data table with status pills.

Common thread the user is pointing at: **stat/KPI cards with clear numeric hierarchy (big number, small delta badge), a clean legend-labeled line chart, and light neutral backgrounds** — this is the visual target for the new forecast summary cards and overall page redesign (D-01 through D-13 above).

</specifics>

<deferred>
## Deferred Ideas

- Light/dark theme toggle — explicitly deferred (D-07); revisit only on future user request.
- Scalable N-commodity selector UI (for >4 series) — not applicable, this app has a fixed set of 4 tracked series per PROJECT.md; noted only in case commodity count ever grows in a future milestone.
- File upload / data-quality-on-upload UX (rows/date-range/missing-values summary from the audit brief) — explicitly out of scope; this app uses manual in-app data entry only (PROJECT.md, confirmed unchanged).

### Reviewed Todos (not folded)
None — discussion stayed within phase scope.

</deferred>

---

*Phase: 6-ux-ui-redesign*
*Context gathered: 2026-08-23*
