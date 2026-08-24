---
phase: 10-csv-bulk-import
plan: 01
subsystem: data-import
tags: [csv, pandas, validation, bulk-import]

# Dependency graph
requires:
  - phase: 04-price-entry-table
    provides: validators.py (validate_numeric, validate_date) and PriceRow schema
provides:
  - Reflex-free parse_import_csv() + ImportParseResult for bulk CSV import
  - Header/schema gate (fail-fast, D-06) before any row parsing
  - Duplicate-date vs invalid-value skip counters (D-04)
affects: [10-02-csv-import-write-path, 10-ui-spec-dropzone]

# Tech tracking
tech-stack:
  added: []
  patterns: ["pure-module dependency discipline (no Reflex/ORM imports, mirrors validators.py)"]

key-files:
  created: [app/app/csv_import.py, app/tests/test_csv_import.py]
  modified: []

key-decisions:
  - "Reused validate_numeric/validate_date verbatim from validators.py — zero reimplemented date/numeric parsing in csv_import.py, enforced by grep in acceptance criteria and a source-level test guard"
  - "Header/row-count/size gates run strictly before row-level validation, so a malformed or oversized file never triggers per-row work"
  - "Duplicate-date skip (via DATE_DUPLICATE_ERROR) and invalid-value skip are counted separately per D-04, since the UI renders them as distinct summary lines"

requirements-completed: [IMPORT-01, IMPORT-02]

# Metrics
duration: 20min
completed: 2026-08-24
---

# Phase 10 Plan 01: CSV Import Parsing Core Summary

**Pure, Reflex-free `parse_import_csv()` that gates malformed/oversized CSVs before parsing and reuses existing validators for every cell, returning added/duplicate/invalid counts and writable row dicts.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2
- **Files modified:** 2 (both created)

## Accomplishments
- `app/app/csv_import.py`: header-exact-match gate, size cap (5 MB), row cap (5,000), and a row loop that delegates 100% of date/numeric decisions to `validators.py`
- `ImportParseResult` dataclass with `added_count`, `duplicate_count`, `invalid_count`, and a `total_skipped` property
- `app/tests/test_csv_import.py`: 18 tests covering header mismatch (missing/extra/reordered columns), unparseable bytes, oversized files, row cap, blank cells, duplicate-date vs invalid-value classification, in-file duplicate months, and a source-level regression guard proving validator reuse

## Task Commits

1. **Task 1: Write app/app/csv_import.py — schema gate plus validator-reusing row parser** - `b4342a6` (feat)
2. **Task 2: Write app/tests/test_csv_import.py covering the four guard behaviors** - `b283fba` (test)

**Plan metadata:** (this commit)

## Files Created/Modified
- `app/app/csv_import.py` - Pure CSV parse + per-row validation, no Reflex/ORM imports, exports `parse_import_csv`, `ImportParseResult`, and the documented error/limit constants
- `app/tests/test_csv_import.py` - 18 unit tests; imports `SERIES_ATTRS` from `app.state` (works fine inside the project venv with Reflex installed) with a fallback to deriving the tuple from `PriceRow.model_fields` if that import ever fails

## Decisions Made
- Used `app.state.SERIES_ATTRS` directly in tests (confirmed importable in this venv) rather than the `PriceRow.model_fields` fallback the plan allowed for — documented the fallback in code as a `try/except` for resilience, but the primary path is the real 16-tuple.
- The unparseable-bytes test uses a malformed-quote CSV payload (`pandas.errors.ParserError` trigger) rather than raw binary garbage — raw binary garbage was found during implementation to often parse successfully as a single-column header under pandas' C parser, which would have made the test assert the wrong failure mode (header mismatch, not unparseable). This is a Rule 1 fix to the test itself (bug in test design caught before commit, not a deviation in the shipped module).

## Deviations from Plan

None — plan executed as written except for the in-repo test-design correction to the "unparseable bytes" fixture described above, which was made before the task's commit and does not affect `csv_import.py`.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `parse_import_csv` and `ImportParseResult` are ready to be called from `app/app/state.py` in plan 10-02 for the actual DB batch-write path.
- No import cycle exists: `csv_import.py` never imports `app.state`, `app.models`, or `reflex` (verified by grep and the standalone `python -c` import check).
- Full test suite (`app/tests/`) remains green at 263 passed after adding this module's 18 tests (245 + 18).

---
*Phase: 10-csv-bulk-import*
*Completed: 2026-08-24*

## Self-Check: PASSED
