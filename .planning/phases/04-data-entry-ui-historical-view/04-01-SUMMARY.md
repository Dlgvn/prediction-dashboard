---
phase: 04-data-entry-ui-historical-view
plan: 01
subsystem: validation
tags: [validators, tdd, data-entry]
requires: []
provides:
  - validate_numeric
  - validate_date
affects:
  - app/app/state.py (Plan 04-02 will import these functions for the write path)
tech-stack:
  added: []
  patterns:
    - "Pure stdlib validators with no Reflex/model coupling, importable from both state.py and tests"
key-files:
  created:
    - app/app/validators.py
    - app/tests/test_validators.py
  modified: []
decisions:
  - "D-01/D-02 implemented exactly per 04-CONTEXT.md and 04-RESEARCH.md reference implementation, with added nan/inf rejection via math.isfinite (beyond the RESEARCH sketch, needed because float() parses 'nan'/'inf' as valid but they are not usable prices)"
metrics:
  duration: 10 min
  completed: 2026-08-22
---

# Phase 04 Plan 01: Validators Summary

Created `app/app/validators.py` with `validate_numeric` (D-01 uniform numeric rule) and
`validate_date` (D-02 valid + non-duplicate-month rule) as pure, dependency-free functions,
following strict TDD: failing tests written first (RED, confirmed via ModuleNotFoundError),
then implementation to green (25/25 tests passing, full suite 90/90 passing with no regression).

## What Was Built

- `validate_numeric(raw: str) -> tuple[bool, float | None, str]`: strips whitespace, treats
  blank as `(True, None, "")` (NULL), parses via `float()` in try/except, rejects negative
  values and non-finite values (`nan`/`inf`) with `NUMERIC_ERROR`. Takes exactly one
  positional parameter — no column-specific branching, verified by an `inspect.signature`
  regression guard in the test suite.
- `validate_date(raw, existing_dates, own_original_date) -> tuple[bool, str, str]`: parses
  via `date.fromisoformat` in try/except (covers both unparseable strings and impossible
  calendar days like 2026-02-30), checks the candidate's `YYYY-MM` month key against the set
  of occupied months (excluding `own_original_date` so in-place edits don't self-collide),
  returns `DATE_DUPLICATE_ERROR` on collision or the normalized ISO date on success.
- Three module-level error constants (`NUMERIC_ERROR`, `DATE_INVALID_ERROR`,
  `DATE_DUPLICATE_ERROR`) matching the UI-SPEC Copywriting Contract verbatim, including the
  em dash in the duplicate-month message.

## TDD Gate Compliance

- RED gate: `test(04-01): add failing tests for validate_numeric and validate_date` (b577e34)
  — confirmed failing with `ModuleNotFoundError: No module named 'app.validators'`.
- GREEN gate: `feat(04-01): implement validate_numeric and validate_date (D-01/D-02)` (a7ac003)
  — all 25 new tests pass; full suite (90 tests) passes with no regressions.
- No REFACTOR commit needed — implementation was clean on first pass.

## Deviations from Plan

None — plan executed exactly as written. The `math.isfinite` nan/inf guard was explicitly
called for in the plan's `<behavior>` section, not an unplanned addition.

## Verification

- `cd app && ./.venv/bin/python -m pytest tests -q` → 90 passed.
- `grep -v '^#' app/app/validators.py | grep -c "import reflex"` → 0.
- `grep -v '^#' app/app/validators.py | grep -cE "if +column|column *=="` → 0.

## Known Stubs

None — both functions are fully implemented, no placeholders.

## Self-Check: PASSED

- FOUND: app/app/validators.py
- FOUND: app/tests/test_validators.py
- FOUND commit b577e34 (test)
- FOUND commit a7ac003 (feat)
