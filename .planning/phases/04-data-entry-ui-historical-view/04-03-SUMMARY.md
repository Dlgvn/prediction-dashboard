---
phase: 04-data-entry-ui-historical-view
plan: 03
subsystem: ui
tags: [reflex, editable-table, data-entry]
dependency-graph:
  requires: [04-02]
  provides: [editable-data-table, add-row-button, delete-control]
  affects: [04-04]
tech-stack:
  added: []
  patterns:
    - "Var-level cell-key concatenation inside rx.foreach callback (row.date + ':' + attr) to avoid stale-index row identity bugs"
    - "Scalar edit_error tied to single editing_key, not a dict Var, since only one cell can be in edit mode at a time"
key-files:
  created:
    - app/tests/test_app_components.py
  modified:
    - app/app/app.py
decisions:
  - "Combined Task 1 (_editable_cell/_delete_cell) and Task 2 (data_table/index assembly) edits in a single file pass, but split into two commits (components, then smoke test) to keep the commit history matching plan task boundaries"
  - "border_color on the editing input uses rx.cond(edit_error != \"\", \"red\", None) rather than a full 1px border shorthand, since Radix input already renders a border by default"
metrics:
  duration: 15min
  completed: 2026-08-22
---

# Phase 4 Plan 3: Editable Data Table UI Summary

Turned Phase 1's read-only `data_table()` into a click-to-edit spreadsheet-like table wired to
the `DashboardState` edit machine built in 04-02, adding an "Add row" button, per-row two-click
delete controls, and an empty state — with a component-tree smoke test proving `index()`
compiles without a browser.

## What Was Built

- `_editable_cell(row, attr)` in `app/app/app.py`: renders `rx.cond(editing_key == key, editor,
  display)`, where the cell key is built as a Var-level `row.date + ":" + attr` inside the
  `rx.foreach` callback (never precomputed) so row identity always matches the clicked row.
  The editor shows an `rx.input` bound to `update_draft`/`commit_edit`/`handle_key_down`, plus
  a conditional red error line and red border when `edit_error` is non-empty.
- `_delete_cell(row)`: two-click delete — a ghost trash icon-button (32px min touch target) that
  arms `pending_delete`, then a solid red "Confirm delete?" button (verbatim UI-SPEC copy) that
  fires `request_delete` again to actually delete, or reverts on blur via
  `cancel_pending_delete`.
- `data_table()`: header now has 18 columns (17 data + 1 delete); body renders persisted
  `DashboardState.rows` first, then `DashboardState.draft_rows` (the blank draft row, if any)
  at the bottom, per D-06. The draft row's delete-column cell is an empty `rx.table.cell()`
  since an unsaved draft has no DB row to delete.
- `add_row_button()`: "Add row" button disabled via `~DashboardState.can_add_row` (Var
  negation, not Python `not`).
- `empty_state()`: "No price data yet" heading + "Add a row to start tracking monthly
  actuals." body, verbatim from the UI-SPEC Copywriting Contract.
- `index()`: wraps the table region in `rx.cond((rows.length() + draft_rows.length()) > 0,
  <table>, empty_state())` so an empty DB with an active draft still shows the table, not the
  empty state. `add_row_button()` sits outside that conditional. A trailing `rx.box(height="2rem")`
  reserves the 32px gap for Phase 5's forecast section per UI-SPEC layout order.
- `app/tests/test_app_components.py`: smoke test importing `app.app`, calling `index()`, and
  asserting it returns an `rx.Component` (catches invalid Var operations like bad `.to_string()`
  or `~` at test time); a second test asserts `len(_COLUMNS) == 17`.

## Verification

- `cd app && ./.venv/bin/python -m pytest tests -q` — 111 passed, no regressions.
- `grep -v '^#' app/app/app.py | grep -c "rx.session"` returns 0 — DB access stays in state.py.
- `grep -c "Confirm delete?"` returns exactly 1, matching UI-SPEC copy verbatim.
- `grep -c "Add row"` and `grep -c "No price data yet"` each return 1 (button/heading present).
- `grep -c "draft_rows"` and `grep -c "can_add_row"` each return at least 1 in app.py, confirming
  the draft row is rendered and D-06b's disabled-button wiring is present.

## Deviations from Plan

None - plan executed exactly as written. Task 1 and Task 2 code changes to `app/app/app.py`
were authored in a single edit pass (natural since `_editable_cell`/`_delete_cell` are used by
`data_table()` written in the same file), but committed separately (components first, smoke
test second) to preserve the plan's task-level commit granularity.

## Known Stubs

None - all rendered controls are wired to the DashboardState handlers built and tested in 04-02.

## Threat Flags

None - no new network endpoints, auth paths, or trust-boundary changes; row identity mitigation
(T-04-09) and disabled-button mitigation (T-04-10) implemented exactly as specified in the
plan's threat model.

## Self-Check: PASSED

- FOUND: app/app/app.py (contains `_editable_cell`, `_delete_cell`)
- FOUND: app/tests/test_app_components.py
- FOUND commit f891c54 (feat(04-03): build editable cell and delete-control components)
- FOUND commit 1201ab7 (test(04-03): add component-tree smoke test for index())
