---
phase: 15-data-entry-rework
plan: 01
subsystem: state
tags: [reflex, state-machine, validation, testing]

requires: []
provides:
  - "start_edit guard preventing edit_error clobber on click-away to a different cell"
  - "State-transition-table comment documenting the full edit/draft/toggle/delete/import lifecycle"
  - "D-03 audit conclusion: csv_import.py's import_error path has no clobber-race bug"
affects: [15-data-entry-rework]

tech-stack:
  added: []
  patterns:
    - "Guard clause in start_edit: ignore click-away when a real edit_error is pending on a different cell; Escape and window-toggle remain unconditional overrides"

key-files:
  created: []
  modified:
    - app/app/state.py
    - app/tests/test_state.py

key-decisions:
  - "Guard only applies inside start_edit; cancel_edit, commit_edit, _commit_draft_cell, and toggle_show_all_history are unchanged and remain unconditional where the plan requires it"
  - "D-03 audit concluded no code change needed in csv_import.py — import_error/import_stage are only touched by single-shot, user-initiated actions (handle_csv_upload, _reset_import via cancel_import/dismiss_import), structurally isolated from the edit machine"

patterns-established:
  - "Pattern: when adding a state-machine guard, ignore-and-return is preferred over swallowing the newer intent, provided an explicit override (Escape, window toggle) still exists to unblock the UI"

requirements-completed: [DATA-09]

duration: 15min
completed: 2026-08-25
---

# Phase 15 Plan 01: start_edit Error-Clobber Race Fix Summary

**Guarded `start_edit` so a click-away to a different cell can no longer silently wipe a pending `DATE_DUPLICATE_ERROR` before the user sees it, with a full state-transition-table comment and 5 new regression tests.**

## Performance

- **Duration:** ~15 min
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Fixed the `start_edit` clobber race: `start_edit` now no-ops (leaves `editing_key`/`edit_error`/`draft_value` untouched) when a genuine error is pending on a cell other than the one being opened; re-opening the same errored cell or opening any cell with no pending error behaves exactly as before.
- Added a state-transition-table comment above `start_edit` covering all 8 triggers (normal edit, draft-row date/non-date entry, Escape, commit success/failure, window toggle, delete-arm) and their effect on `editing_key`/`draft_value`/`edit_error`/`draft_rows`/`pending_delete`.
- Completed the D-03 audit of `csv_import.py`'s `import_error` path: documented in a code comment near `import_error`'s declaration and here — no clobber-race bug exists, no fix applied.
- Added 5 regression tests covering the guard, same-cell reopen, no-pending-error passthrough, window-toggle override, and CSV-import non-interaction with the edit machine while an error is pending.

## Task Commits

1. **Task 1: Write the state-transition table, fix the start_edit race, complete the D-03 audit** - `27ffb21` (fix)

## Files Created/Modified
- `app/app/state.py` - `start_edit` guard against clobbering a pending different-cell `edit_error`; state-transition-table comment; D-03 audit conclusion comment near `import_error`
- `app/tests/test_state.py` - 5 new tests: `test_start_edit_does_not_clobber_pending_error_on_different_cell`, `test_start_edit_on_same_errored_cell_clears_error_and_reopens`, `test_start_edit_with_no_pending_error_behaves_as_before`, `test_toggle_show_all_history_clears_pending_error_from_different_cell`, `test_handle_csv_upload_does_not_touch_edit_error_or_editing_key`

## Decisions Made
- Guard condition is `edit_error != "" and editing_key != "" and key != editing_key` — deliberately narrow so it only fires on a genuinely pending, unrendered error, not on ordinary cell-to-cell navigation.
- No changes made to `commit_edit`, `_commit_draft_cell`, `cancel_edit`, or `toggle_show_all_history`, per the plan's explicit scope boundary.

## D-03 Audit Conclusion

Grepped every assignment site of `import_error` and `import_stage` in `state.py`. `import_error` is set only inside `handle_csv_upload`'s explicit failure branches and cleared only by `_reset_import()`, which is called from `handle_csv_upload`'s start, `cancel_import`, and `dismiss_import` — all single-shot, user-initiated actions. None of `start_edit`, `commit_edit`, `_commit_draft_cell`, or `toggle_show_all_history` touch `import_error`/`import_stage`, and the reverse is also true (confirmed structurally and by the existing/extended `test_handle_csv_upload_does_not_touch_edit_error_or_editing_key` test, which now also asserts `editing_key`/`draft_value`/`draft_rows` are untouched by a CSV upload while a real edit_error is pending). **Conclusion: no clobber-race bug exists in the CSV import path; no fix needed.** `csv_import.py` was not modified.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Wave 1 complete; the `start_edit` race is closed and the D-03 audit is documented, unblocking the picker-swap work in Plan 15-02 which depends on the duplicate-date error reliably rendering.
- All 144 tests in `app/tests/test_state.py` pass (139 pre-existing + 5 new).

---
*Phase: 15-data-entry-rework*
*Completed: 2026-08-25*
