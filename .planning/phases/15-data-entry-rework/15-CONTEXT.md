# Phase 15: Data Entry Rework — Context

**Gathered:** 2026-08-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the manual data-entry date bug: date input silently fails to commit when
invalid/incomplete, and the free-text field requires the user to know/type an exact
ISO date format from memory. Root cause is already diagnosed (not to be re-derived
by research): validation is blur/Enter-gated with no live/format feedback, and
`start_edit`'s unconditional `edit_error = ""` reset can clobber a genuinely-set
error from a near-simultaneous focus-change race. The fix direction is locked by
prior research: replace the free-text date field with a native
`rx.input(type="date")` control, which eliminates the format-guessing/fuzzy-parsing
problem at the root rather than patching validation messaging around it.

In scope: the date cell/field in both the "add new row" draft flow and in-place
editing of an existing row's date; fixing the `start_edit` error-clobber race;
auditing (and fixing if trivial) CSV import's separate date-validation path.
Out of scope: any change to numeric-column validation/editing, any change to the
windowing/CSV-import state machines beyond what's needed to not regress them, any
new capability beyond DATA-09/DATA-10.
</domain>

<decisions>
## Implementation Decisions

### Date picker scope
- **D-01:** The native `rx.input(type="date")` control replaces the date cell in
  BOTH places a date is entered/edited: the "add new row" draft flow (`draft_rows`
  → `_commit_draft_cell`) and in-place editing of an existing row's date
  (`editing_key` → `commit_edit`'s `column == "date"` branch). Both code paths
  currently share `_editable_cell` in app.py and `validate_date` in state.py — the
  picker must work through both without diverging the edit machine into two
  parallel mechanisms (PITFALLS.md guardrail).

### Error prominence
- **D-02:** Keep the existing small inline red text under the cell (matches
  current visual language, reuses the single `edit_error` scalar — no new state
  field, per PITFALLS.md's explicit warning against introducing a second
  error-display field). The fix is behavioral: `start_edit` must no longer
  unconditionally reset `edit_error = ""` in a way that can race away a
  genuinely-set error from a different, near-simultaneous edit-session close.
  A native date picker only returns valid ISO dates or empty — so the remaining
  error case still needing this fix is the "duplicate month" validation error
  (`DATE_DUPLICATE_ERROR`), not malformed-format errors (those become
  structurally impossible with `type="date"`).

### CSV import scope
- **D-03:** Audit `csv_import.py`'s date-validation/error-surfacing path (it calls
  the same `validators.validate_date` but has its own result plumbing through
  `ImportParseResult`/`import_error`). If the same race/clobber class of bug
  exists there and the fix is small, include it in this phase. If it needs a
  genuine UX/design decision (e.g., a different picker/format affordance for
  bulk CSV rows, which doesn't make sense for a file-based flow), defer that to
  its own future phase and document why in the plan.

### Claude's Discretion
- Exact `rx.input(type="date")` value-binding approach (whether `draft_value`
  stores the ISO string directly from the native picker's `on_change`, or whether
  a small adapter is needed) — confirm against the installed Reflex 0.9.8 API
  before implementing (PITFALLS.md already flags "don't guess Reflex API shape
  without checking docs first" as a project-wide pattern).
  - **Note:** during research/planning, if `rx.input(type="date")` is a real
    passthrough of the HTML5 `<input type="date">` element (it should be, per
    Reflex's design as a thin `rx.el.input` wrapper), it emits ISO `YYYY-MM-DD`
    strings on change/blur natively — no client-side format parsing needed.
- Exact wording/placement fix for `start_edit`'s error-reset race — options include
  guarding the reset with a check, or restructuring so `commit_edit`'s failure path
  is what governs `edit_error` lifetime rather than `start_edit`'s entry path. Write
  the full state-transition table (PITFALLS.md's explicit ask) before choosing.
- Whether the native date input needs an explicit min/max date range prop, or
  should accept any valid calendar date (existing duplicate-month check already
  guards data integrity) — default to no artificial range restriction unless a
  clear reason emerges during planning.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing code (primary implementation surface)
- `app/app/state.py` — `start_edit` (line ~896), `commit_edit` (line ~938),
  `_commit_draft_cell` (line ~979), `cancel_edit` (line ~915),
  `toggle_show_all_history` (line ~920, calls `cancel_edit`/`cancel_pending_delete`
  — must keep working), `handle_key_down` (line ~1024), `add_row` (line ~1030)
- `app/app/app.py` — `_editable_cell` (line ~36, the shared date/numeric cell
  renderer: `on_click=start_edit`, `on_blur=commit_edit`,
  `on_key_down=handle_key_down`, inline error `rx.cond` at line ~66)
- `app/app/validators.py` — `validate_date` (D-02 decision, must not change its
  signature/behavior — only how/when it's invoked and how its error surfaces),
  `DATE_INVALID_ERROR`/`DATE_DUPLICATE_ERROR` constants
- `app/app/csv_import.py` — separate `parse_import_csv` date-validation call site
  (D-03 audit target)

### v1.3 milestone research (MANDATORY)
- `.planning/research/PITFALLS.md` lines 129-143 (Pitfall: "Data Entry rework
  phase" — full state-transition audit requirement, reuse `edit_error` not a new
  field, regression-test windowing toggle + CSV import interaction) and line 205
  (risk register entry for this exact phase)
- `.planning/research/ARCHITECTURE.md` lines 52-54 (verdict: no render-conditional
  defect, the bug is behavioral — blur/Enter-gated validation, easily-missed/
  racily-cleared error, strict ISO-only text input) and lines 113-116 (explicit
  anti-pattern: do NOT "fix" this by only restructuring the `rx.cond` — the real
  fix is a real date-input affordance + the `start_edit` race fix)
- `.planning/research/FEATURES.md` line 38 (native `rx.input(type="date")` is the
  recommended fix; freeform-text + fuzzy parsing is an explicit anti-feature —
  "ambiguous formats silently resolve to the *wrong* date rather than erroring,
  which is worse than a visible rejection") and lines 69-76 (dependency note:
  must be scoped considering CSV import's separate date parsing and the existing
  stored-date format in SQLite)

### Prior phase precedent
- `.planning/phases/07-table-pagination-windowing/` — `toggle_show_all_history`'s
  `cancel_edit()`/`cancel_pending_delete()` calls are the existing precedent for
  "a shared state machine change must not orphan an in-progress edit"; this
  phase's fix must preserve that same guarantee
- `.planning/phases/10-csv-bulk-import/` — established `import_error` as CSV
  import's own separate error scalar (deliberately not reusing `edit_error` per
  that phase's own PITFALLS note) — the D-03 audit works within that existing
  separation, not by merging the two error fields

### Project-level
- `.planning/REQUIREMENTS.md` — DATA-09, DATA-10
- `.planning/ROADMAP.md` — Phase 15 entry (Success Criteria 1-4)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `edit_error: str` (single scalar) — reuse as-is per D-02, do not add a second
  error field.
- `validators.validate_date` — reuse as-is; only its call sites' error-lifecycle
  handling changes, not its logic/signature.

### Established Patterns
- `editing_key` format `f"{row_date}:{column}"` with `row_date == ""` meaning "the
  single draft row" — both `commit_edit` and `_commit_draft_cell` branch on this,
  and both currently call the same `validate_date` for the `column == "date"` case.
  The date-picker swap must work through this shared dispatch, not fork it.
- `DashboardState` is the sole `rx.session()`/ORM boundary — no new state class,
  per the project-wide convention re-confirmed in ARCHITECTURE.md's anti-patterns
  section.

### Integration Points
- `_editable_cell(row, attr)` in app.py currently renders one `rx.input` (text)
  for every column including "date". Needs an `rx.cond`/branch so the "date"
  column renders `rx.input(type="date", ...)` while every other column keeps the
  existing text `rx.input` — do not change the numeric-column rendering path.
- `draft_rows`'s single draft-row date field goes through the same
  `_editable_cell` component (attr="date", row_date=""), so the picker swap
  naturally covers both D-01 targets if wired through the shared component rather
  than a duplicated one-off.

</code_context>

<specifics>
## Specific Ideas

No new visual references — the native browser date-picker UI is used as-is
(no custom calendar component to design/build). Error text keeps the existing
small red inline treatment per D-02.

</specifics>

<deferred>
## Deferred Ideas

- CSV import date-validation UX redesign (a real design decision beyond a small
  race fix) — deferred to its own future phase if the D-03 audit finds it needs
  more than a trivial fix. Not committed to landing in this phase.

### Reviewed Todos (not folded)
None — discussion stayed within phase scope.

</deferred>

---

*Phase: 15-data-entry-rework*
*Context gathered: 2026-08-25*
