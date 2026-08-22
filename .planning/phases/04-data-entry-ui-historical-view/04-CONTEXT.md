# Phase 4: Data Entry UI & Historical View - Context

**Gathered:** 2026-08-22
**Status:** Ready for planning

<domain>
## Phase Boundary

The user can manage monthly actual price data directly in the dashboard — add, inline-edit,
and delete rows, with validation and reliable SQLite persistence (DATA-01 through DATA-05) —
and view a historical (actuals-only, no forecast) chart covering all 16 series columns
(VIS-01). This phase extends Phase 1's read-only seeded-data table into a fully editable
one and adds the historical chart. It does NOT touch forecasting (Phase 3, done) or the
forecast-scenario chart/horizon selector/export (Phase 5).

</domain>

<decisions>
## Implementation Decisions

### Validation rules
- **D-01:** Numeric validation is uniform and simple across all 16 series columns:
  reject non-numeric input, reject negative values, allow blank/null. No tighter
  series-specific plausible-range checks (e.g. no FX-rate-specific ceiling) — those would
  need domain knowledge that could go stale and risk rejecting legitimate unusual values.
- **D-02:** Date field validation: must be a valid date, AND must not duplicate an
  existing row's calendar month (matches Phase 1's D-02 unique-date-per-month schema
  constraint). Adding a row for a month that already exists is rejected — editing the
  existing row is the correct path, not creating a second row for the same month.

### Historical chart scope (VIS-01)
- **D-03:** The historical chart covers all 16 series columns (not just the 4 headline
  series HDAN/PPAN/Diesel-USD/FX) — full parity with Phase 1's read-only table, letting
  the user inspect predictor trends (natural gas, urea, corn, etc.) as well as the
  headline series.
- **D-04:** Given the 16 columns have wildly different scales (FX ~3500 vs. natural gas
  ~2-20) which would make a single overlaid multi-line chart unreadable, the historical
  view is ONE chart with a series selector/toggle (dropdown or similar) — not a grid of
  16 small individual charts, and not one single mega-chart with all lines overlaid.
  Each series gets its own y-axis scale implicitly by only ever showing one at a time.

### Inline editing UX
- **D-05:** Click-to-edit per cell: clicking a table cell turns it into an editable
  input; blur or Enter commits the change. No explicit per-row edit-mode toggle, no
  separate Save/Cancel buttons per row — closest to a spreadsheet feel.
- **D-06:** Adding a new row: an "Add row" button appends a blank row at the bottom of
  the table, whose cells behave exactly like existing rows' cells (click-to-edit) — no
  separate add-row form UI. The new row's Date cell must satisfy D-02 (valid, not a
  duplicate month) before the row can be considered saved/persisted; until a valid date
  is entered, the row is not yet written to SQLite (avoid writing a row with no date).

### Delete confirmation UX
- **D-07:** Click-delete-again-to-confirm pattern: the first click on a row's delete
  control changes it into a "confirm?" state (e.g. relabeled/recolored) rather than
  opening a modal; a second click within that state actually deletes the row. No modal
  dialog — stays in the flow, matches D-05/D-06's lightweight inline-editing philosophy.

### Claude's Discretion
None flagged this round — all four presented gray areas were explicitly decided, with
follow-up rounds on chart layout and add-row UX.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & prior decisions
- `.planning/REQUIREMENTS.md` — DATA-01 through DATA-05 and VIS-01 are this phase's
  requirements
- `.planning/phases/01-app-skeleton-data-layer/01-CONTEXT.md` — D-01 (wide table, one
  row per month), D-02 (unique date constraint, upsert on conflict, nullable columns),
  D-05b/c (the 16-column list and their sources), D-08 (read-only table this phase
  extends into editable)
- `.planning/research/FEATURES.md` — table-stakes/differentiator research on data-entry
  and inline-editing UX patterns (validated by this discussion's D-05/D-06/D-07)
- `.planning/research/PITFALLS.md` — "State reflects DB, DB is source of truth" pattern
  Phase 1 already established; this phase's edits must write through to SQLite
  immediately, not just hold state in the Reflex session
- `.planning/research/STACK.md` — confirms `rx.plotly` as the recommended charting
  component for this project (relevant to implementing D-04's series-selector chart)

### Existing code (this phase extends, doesn't replace)
- `app/app/models.py` — `PriceRow` (17 columns incl. date), `AppSetting`
- `app/app/state.py` — `DashboardState` with `load_rows()`, the existing DB read path
  this phase extends with write operations (add/edit/delete)
- `app/app/app.py` — the existing read-only `data_table()`/`index()` this phase makes
  editable and adds the historical chart to
- `app/app/forecasting.py` — Phase 3's forecasting module; NOT touched by this phase,
  but its `forecast_hdan`/`forecast_ppan_var_system`/etc. functions read from the same
  `PriceRow` data this phase writes, so correctness of Phase 4's writes matters for
  Phase 3's (already-built) forecasts and Phase 5's (future) forecast display

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/app/state.py`'s `DashboardState.load_rows()` — the read path this phase's
  add/edit/delete operations must keep in sync with (re-load or locally update `rows`
  after each write, per the "DB is source of truth" pattern)
- `app/app/app.py`'s `data_table()` — the read-only table component this phase extends;
  reuse its column list/ordering (16 series + date) rather than redefining it

### Established Patterns
- Phase 1 established SQLite as the source of truth and a 16-column wide-table schema
  with a unique date constraint — this phase's writes must respect that constraint
  (D-02) and go through `rx.session()` the same way Phase 1's seed script did.

### Integration Points
- Phase 5 (Forecast UI, Scenario Chart & Export) depends on this phase's editable table
  and will add the horizon selector / forecast chart / export button alongside what this
  phase builds — Phase 4's UI additions should leave room on the dashboard page for
  Phase 5's additions, not assume the page is "done" after this phase.

</code_context>

<specifics>
## Specific Ideas

No specific visual/styling references given beyond the decisions above — open to standard
Reflex/Plotly patterns for the series-selector chart and click-to-edit cells.

</specifics>

<deferred>
## Deferred Ideas

None raised outside phase scope — discussion stayed within Phase 4's boundary (data entry,
validation, historical chart).

</deferred>

---

*Phase: 4-Data Entry UI & Historical View*
*Context gathered: 2026-08-22*
