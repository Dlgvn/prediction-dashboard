# Phase 7: Table Pagination / Windowing — Context

**Gathered:** 2026-08-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the Data Entry table's real-world unusability: it currently renders all 167 rows × 17 columns (~2,950 individually editable DOM cells) unpaginated, going back to 2013. This phase adds a windowed default view (recent months only) plus a "show all history" toggle to reveal the full table on demand — without changing any other behavior (edit, delete, add-row, validation, persistence) or touching any data outside the Data Entry table's rendering (charts, forecasts, export, freshness chips all continue to read full history).

In scope: `visible_rows` windowing, the toggle control, edit/delete-state reset on toggle.
Out of scope: SQL-level/server-side pagination (in-memory windowing is sufficient at this data scale per research), any change to `self.rows`, `forecast_results`, chart figures, or export — those must keep seeing the FULL history, unaffected by the table's windowed display.
</domain>

<decisions>
## Implementation Decisions

### Default window
- **D-01:** Data Entry table defaults to showing the most recent 12 months of rows, not all 167.
- **D-02:** A "show all history" toggle reveals the full table; toggling back re-applies the 12-month window.

### Toggle interaction with edit/delete state
- **D-03:** Toggling "show all history" on or off cancels any in-progress cell edit (`editing_key` reset to `""`) and any pending two-click delete confirmation (`pending_delete` reset to `""`). This is the simplest, safest option — avoids any stale-row-reference bug from a row disappearing out of the visible window mid-edit. Mirrors the existing `on_blur` → `cancel_pending_delete` precedent already in the codebase.

### Claude's Discretion
- Toggle control's exact placement, label wording (e.g. "Show all history" / "Show recent months only"), and visual styling — apply the existing `06-UI-SPEC.md` design tokens (buttons/spacing/typography) for consistency, no new design system needed.
- Whether `visible_rows` includes in-progress `draft_rows` (new unsaved rows) regardless of window — new rows should always be visible immediately after `add_row()`, since they represent the current/most-recent entry workflow.
- Empty-state copy when the 12-month window happens to contain zero rows (e.g. a brand new dataset) — reuse existing empty-state pattern from `empty_state()`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing code (primary implementation surface)
- `app/app/state.py` — `DashboardState.rows` (full history, DO NOT slice this directly — see Pitfall below), `editing_key`, `pending_delete`, `draft_rows`, `start_edit`, `commit_edit`, `request_delete`, `cancel_pending_delete`, `add_row` (lines ~117-762)
- `app/app/app.py` — `data_table()`, `_editable_cell()`, `_delete_cell()`, `add_row_button()`, `data_entry_section()` — the render functions this phase modifies
- `app/app/theme.py` — design tokens (buttons, spacing) for the new toggle control, per Phase 6's locked light design system

### v1.2 milestone research (MANDATORY — this phase's specific risk analysis)
- `.planning/research/PITFALLS.md` — **Pitfall: `self.rows` is overloaded** as both table-display source AND the source for `forecast_results`, `historical_chart_figure`, `freshness_chips`, `summary_cards`, `_history_df`. Naive pagination that slices `self.rows` directly would silently corrupt every forecast/chart computation. The fix is a NEW, separate `visible_rows` computed var that windows `self.rows` for display only — `self.rows` itself must never be reassigned to a windowed subset.
- `.planning/research/PITFALLS.md` — Pitfall: the edit/delete state machine (`editing_key`, `pending_delete`, `draft_rows`) has zero awareness of "row currently visible" — a page/window change must explicitly reset this state (see D-03 above) or it goes stale.
- `.planning/research/ARCHITECTURE.md` — integration points: recommends `show_all_history: bool` state field + a `visible_rows` computed var slicing `self.rows` (already date-ascending); existing edit/delete handlers are keyed by `row.date` not index, so windowing the rendered list requires zero changes to those handlers' logic itself, only to what list they iterate over.
- `.planning/research/STACK.md` — confirms no new dependencies needed; `@rx.var(cache=True)` computed vars are the correct Reflex-idiomatic mechanism, not a new library.

### Project-level
- `.planning/PROJECT.md` — Current Milestone: v1.2 section
- `.planning/REQUIREMENTS.md` — DATA-07, DATA-08
- `.planning/ROADMAP.md` — Phase 7 entry (goal, success criteria)
- `.planning/phases/06-ux-ui-redesign/06-UI-SPEC.md` — locked design system (spacing/typography/color tokens) the new toggle control must follow for visual consistency

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `theme.py` tokens (`CARD_RADIUS`, `CARD_BORDER`, spacing/typography constants) — reuse for the toggle control, no new styling system.
- Existing `rx.cond`-based empty-state pattern (`empty_state()` in app.py) — reuse for the "window contains zero rows" edge case.

### Established Patterns
- All computed/derived data in this app is exposed via `@rx.var`-decorated properties on `DashboardState`, never plain Python properties — `visible_rows` must follow this pattern to be reactive.
- Row identity throughout the app is `row.date` (a string), never index — this is why edit/delete handlers can safely operate on a windowed subset without modification.
- `self.rows` is populated once by `load_rows()` and reassigned wholesale (not appended to) — confirms it's safe to add a purely-additive `visible_rows` var without touching the `load_rows` flow.

### Integration Points
- `data_table()` in app.py currently does `rx.foreach(DashboardState.rows, ...)` — must change to `rx.foreach(DashboardState.visible_rows, ...)`.
- `draft_rows` foreach (new unsaved rows) should likely remain always-visible regardless of the window, per Claude's Discretion above.
- New `show_all_history: bool = False` state field + `visible_rows` computed var + a toggle control wired to flip `show_all_history` (and per D-03, also reset `editing_key`/`pending_delete`) are the concrete additions.

</code_context>

<specifics>
## Specific Ideas

No additional specific UI references beyond the already-locked Phase 6 design system — this phase should look like a natural extension of the existing Data Entry section, not a new visual style.

</specifics>

<deferred>
## Deferred Ideas

- SQL-level/server-side (`OFFSET`/`LIMIT`) pagination — flagged in `.planning/research/STACK.md` as a future revisit trigger only if data grows into the thousands of rows; in-memory windowing is sufficient at current (167-row) and foreseeable scale.
- Column-level filtering/search within the Data Entry table — not requested, not in DATA-07/08 scope.

### Reviewed Todos (not folded)
None — discussion stayed within phase scope.

</deferred>

---

*Phase: 7-table-pagination-windowing*
*Context gathered: 2026-08-24*
