# Quick Add-Row Form — Design

*2026-08-26. Ported from a React/shadcn mockup of the Data Entry tab
(`docs/plans/` companion artifacts not tracked; see conversation for the
reference mockup). Replaces the current click-to-edit draft-row flow for
adding a new month's actuals, and carries over two visual-polish items from
the mockup: sticky header/Date column, and restyled CSV import states.*

## 1. What this is

Today, clicking **Add row** on the Data Entry tab (`app/app/app.py`'s
`data_entry_section()`) inserts an empty draft row into the table, which the
user then fills in by clicking each of the 17 cells (Date + 16 series
columns from `SERIES_ATTRS`) one at a time, each commit going through
`start_edit`/`update_draft`/`commit_edit`.

This design replaces that flow with a single **quick add-row form**
rendered above the table: all 17 fields in one compact grid, Date required
and the 16 series fields optional/skippable, one "Save row" button, and a
summary error banner. This matches how the user actually has the data —
one month's worth of numbers from a source spreadsheet, entered together —
rather than one cell at a time.

## 2. Why replace rather than add alongside

Considered keeping both entry paths (form for "enter a full month," draft
row for "quick single-value edit"), but decided against it: the draft-row
mechanism only exists to *add* new rows in the first place (editing
*existing* rows still goes through the same click-to-edit cells it always
has — that's unchanged). Maintaining two ways to create a new row is
duplicate state and duplicate UI for no real benefit once the form covers
the same case better. **Editing an already-saved row's cells is untouched
by this design.**

## 3. State changes (`app/app/state.py`)

Remove:
- `draft_rows` and the draft-row-specific paths through `start_edit` /
  `commit_edit` / `add_row` that exist solely to manage an in-table blank
  row (the click-to-edit machinery itself stays — it's still how existing
  rows get edited).

Add:
- `quick_add_values: dict[str, str] = {}` — one string entry per field
  (`date` + each of `SERIES_ATTRS`), keyed the same way `_COLUMNS`/
  `SERIES_ATTRS` already key everything else. Empty string = field left
  blank.
- `quick_add_error: str = ""` — summary validation message, shown above the
  form. Empty = no error.
- `update_quick_add_field(attr: str, value: str) -> None` — event handler,
  sets one key in `quick_add_values`.
- `submit_quick_add() -> None` — event handler bound to "Save row":
  1. Validates `date` is present and passes `validate_date` (reused from
     `app/app/validators.py` — same validator the click-to-edit cells use).
  2. For each non-empty series field, runs `validate_numeric` (same reuse).
  3. On any failure: sets `quick_add_error` to a single human-readable
     message naming the first offending field (e.g. `"Ammonia: enter a
     number"` or `"Date is required"`), leaves `quick_add_values` as-is
     (nothing is lost), returns without inserting a row.
  4. On success: inserts the row (same insert path `add_row` currently
     uses, minus the empty-draft-row part), clears `quick_add_error`,
     resets `quick_add_values` to all-empty, and **leaves the form open**
     so the user can immediately enter the next month.

`can_add_row` (or equivalent) still gates whether the form/Save button is
usable, same as it currently gates `add_row_button()`.

## 4. UI changes (`app/app/app.py`)

- Remove the `draft_rows` `rx.foreach` block from `data_table()`.
- Add `quick_add_form()`: a compact `rx.grid` (or `rx.hstack`/`rx.wrap`) of
  17 `rx.input`s bound to `DashboardState.quick_add_values[attr]` via
  `on_change=DashboardState.update_quick_add_field(attr, value)`, laid out
  so Date is visually distinguished (e.g. bold label / left position) from
  the 16 optional series fields. Error banner
  (`rx.cond(DashboardState.quick_add_error != "", ...)`) sits above the
  grid, same visual treatment as the existing `forecast_warning`/
  `export_message` banners for consistency. "Save row" button calls
  `submit_quick_add`.
- Replace `add_row_button()`'s role: the form is always visible above the
  table (no separate "Add row" click-to-reveal step), matching the
  mockup's always-present placement.
- **Sticky header/Date column**: `data_table()`'s header row and each
  row's Date cell get `position="sticky"` (`top="0"` for the header,
  `left="0"` for the Date column) plus a background color so content
  doesn't show through while scrolling — needed both vertically (header)
  and horizontally (Date column) given the 16-series table already
  scrolls both ways in `data_entry_section()`'s `overflow_x="auto"` box.
- **CSV import states restyle**: `csv_import_control()`'s four branches
  (idle/preview/error/done) get the mockup's visual treatment (icon +
  color per state — upload-cloud/muted for idle, plain card for preview,
  red icon+border for error, plain card for done). No behavior change, no
  new manual-override switcher — that was mockup-only tooling and has no
  place in the shipped app.

## 5. What's explicitly out of scope

- **Highlighted draft rows** — dropped. There are no more draft rows once
  the form replaces that flow, so this mockup detail no longer applies.
- **CSV manual state override** — dropped per discussion; the real app's
  automatic idle→preview→error/done transitions are the only way those
  states are reached.
- Editing behavior for existing (already-saved) rows — unchanged.

## 6. Testing

- `submit_quick_add`: valid row inserts correctly and clears the form;
  missing date sets `quick_add_error` and does not insert; invalid numeric
  value in one field sets `quick_add_error` naming that field and does not
  insert; values persist in `quick_add_values` after a validation failure
  (nothing the user typed is lost).
- `update_quick_add_field`: updates exactly the targeted key.
- Removal of now-obsolete `draft_rows`-specific tests; any test asserting
  on `add_row` creating a blank draft row gets updated or removed to match
  the new insert-on-submit behavior.
- No changes needed to existing click-to-edit tests for already-saved
  rows — that code path is untouched.
