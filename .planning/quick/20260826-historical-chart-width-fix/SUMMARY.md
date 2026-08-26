---
slug: historical-chart-width-fix
status: complete
completed: 2026-08-26
---

Fixed: added `width="100%"` to `historical_section()`'s `rx.vstack(...)`
in `app/app/app.py`, matching the pattern already used by
`forecast_section()` and `_data_entry_tab()`.

Verified: full test suite green (365 passed, 0 failed at the time); confirmed
live in browser that the Data Entry tab's Historical chart now renders
full-width with horizontal date-axis labels, matching the Forecast tab.

## Follow-up (same session)

User reported the quick-add form (from the 2026-08-26 quick-add-row
feature) was inconvenient for filling in blank/partial row data, and
asked to revert to the original click-to-edit draft-row flow shown in
the earlier `data-entry-mockup` artifact. Reverted:

- `app/app/state.py`: removed `quick_add_values`/`quick_add_error`/
  `update_quick_add_field`/`submit_quick_add`; restored `draft_rows`,
  `can_add_row`, `_commit_draft_cell`, `add_row`.
- `app/app/app.py`: removed `quick_add_form()`/`_quick_add_field()`;
  restored `add_row_button()`; restored the draft-row `rx.foreach` in
  `data_table()` (kept the sticky-cell styling from the redesign);
  restored `data_entry_section()`'s original structure.
- Test files updated to match (draft-row tests restored, quick-add tests
  removed).
- All redesign work (theme tokens, fonts, gauge-bezel, sticky
  header/date column, chart width fix) preserved untouched.

Verified: full suite green (362 passed, 0 failed); confirmed live in
browser that "Add row" creates an inline draft row, click-to-edit opens
the date picker, and committing a partial row (date + one field, rest
blank) persists correctly.
