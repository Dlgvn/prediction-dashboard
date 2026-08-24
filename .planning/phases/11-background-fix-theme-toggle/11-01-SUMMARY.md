---
phase: 11-background-fix-theme-toggle
plan: 01
subsystem: ui
tags: [theme, design-tokens, dark-mode, wcag, contrast, reflex]

requires:
  - phase: 06-ux-ui-redesign
    provides: "Flat LIGHT-only theme.py constants and 06-UI-SPEC.md contrast methodology"
provides:
  - "theme.LIGHT / theme.DARK dicts with full 10-key parity"
  - "theme.tokens(mode) mode-resolution lookup (dark iff mode == 'dark', else light)"
  - "Locked dark hex values transcribed verbatim from 11-UI-SPEC.md with amendment-comment provenance"
  - "test_theme_tokens.py: key-parity + WCAG 2.1 contrast-ratio regression coverage"
affects: [11-02, 11-03]

tech-stack:
  added: []
  patterns:
    - "Dual-mode design token dict (LIGHT/DARK) resolved via tokens(mode), consumed by state.py/app.py in later Phase 11 plans"
    - "Local WCAG 2.1 relative-luminance contrast helper duplicated in test file (not imported from theme.py) to keep theme.py dependency-free"

key-files:
  created:
    - app/tests/test_theme_tokens.py
  modified:
    - app/app/theme.py
    - app/tests/test_theme.py

key-decisions:
  - "LIGHT dict entries reference the existing flat constants (not re-typed literals) so there is exactly one source-of-truth literal per light color"
  - "Removed test_no_dark_mode_or_theme_toggle_token — it encoded a Phase 6 scope boundary (no dark mode) that Phase 11 intentionally lifts"
  - "Contrast helper lives in test_theme_tokens.py, not theme.py, preserving theme.py's zero-import/dependency-free contract"

patterns-established:
  - "Amendment comments above DARK entries follow the Task 06-03 convention: candidate -> measured ratio -> threshold -> final value"

requirements-completed: [THEME-04]

duration: 25min
completed: 2026-08-24
---

# Phase 11 Plan 01: Dual-Tokenize theme.py Summary

**theme.py now exposes LIGHT/DARK dicts and a `tokens(mode)` lookup with bespoke dark hex values from 11-UI-SPEC.md, each backed by a measured WCAG 2.1 contrast ratio enforced by an automated regression test.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-08-24T00:00:00Z (approx)
- **Completed:** 2026-08-24
- **Tasks:** 2 completed
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- Added `LIGHT`/`DARK` 10-key dicts and `tokens(mode)` lookup to `theme.py`, with zero new imports (module stays dependency-free)
- Locked dark hex values transcribed verbatim from 11-UI-SPEC.md, each dark text/boundary token documented with its measured contrast ratio in a Task-06-03-style amendment comment
- Removed the now-obsolete Phase 6 "no dark mode" guard test
- Added `test_theme_tokens.py` with key-parity, contrast-table (reproducing 11-UI-SPEC.md ratios within 0.05 tolerance), rejected-candidate regression guard, DOWN==DESTRUCTIVE parity, and mode-fallback tests
- Manually verified the contrast assertions are load-bearing (temporarily reverting BORDER dark to the rejected `#52525B` candidate fails the test suite, as expected)

## Task Commits

1. **Task 1: Dual-tokenize theme.py with LIGHT/DARK dicts and tokens() lookup** - `87e07b9` (feat)
2. **Task 2: Replace the obsolete no-dark-mode guard and add token parity + WCAG contrast tests** - `5995a6b` (test)

**Plan metadata:** (this commit)

## Files Created/Modified
- `app/app/theme.py` - Added `LIGHT`/`DARK` 10-key dicts and `tokens(mode)` lookup; flat constants unchanged
- `app/tests/test_theme.py` - Removed obsolete `test_no_dark_mode_or_theme_toggle_token`; removed now-unused `re` import
- `app/tests/test_theme_tokens.py` - New: key parity, contrast table vs 11-UI-SPEC.md, regression guard, DOWN/DESTRUCTIVE parity, mode fallback

## Decisions Made
- `LIGHT` dict entries reference existing flat constants rather than duplicating literals, keeping exactly one source-of-truth value per light color
- Contrast-ratio helper duplicated locally in `test_theme_tokens.py` instead of imported from `theme.py`, preserving `theme.py`'s dependency-free/zero-import contract
- Docstring wording adjusted ("out of this single Python module" instead of "from this single Python module") to avoid a false-positive match against the plan's grep-based zero-import acceptance check (the check treats lines starting with `from ` as import statements; the real dependency-free guarantee is enforced by the AST-based `test_theme_module_imports_with_no_third_party_dependency` test, which was already passing before and after this change)

## Deviations from Plan

None - plan executed exactly as written. The docstring rewording above is a minor same-task wording tweak to satisfy the plan's own acceptance criterion, not a deviation from planned behavior.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `theme.tokens(mode)` is the published contract Plans 11-02 (state.py Plotly figures) and 11-03 (app.py/html-body background, toggle control) will consume.
- No consumer files (`app.py`, `state.py`) were touched in this plan — confirmed via `git diff --name-only` showing only `theme.py` and the two test files.
- Full test suite green (300 passed).

---
*Phase: 11-background-fix-theme-toggle*
*Completed: 2026-08-24*

## Self-Check: PASSED
