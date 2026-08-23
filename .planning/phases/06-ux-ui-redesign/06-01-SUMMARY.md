---
phase: 06-ux-ui-redesign
plan: 01
subsystem: ui
tags: [reflex, plotly, design-tokens, state-management]

# Dependency graph
requires:
  - phase: 05-forecasting-export
    provides: forecast_results computed var, forecast_chart_figure/historical_chart_figure figure builders, FORECAST_SERIES_LABELS
provides:
  - "app/app/theme.py — locked design token module (color/spacing/typography/direction glyphs/number formatting)"
  - "Restyled historical_chart_figure and forecast_chart_figure (forecast-start marker, dashed base line, transparent bg, formatted hover tooltips, Expected range trace name)"
  - "DashboardState.summary_cards computed var — 4 horizon-reactive, foreach-safe forecast summary card dicts"
affects: [06-02 (page composition consumes theme.py and summary_cards)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dependency-free token module (app/theme.py) imported by both state.py and (future) app.py — no Reflex import, no functions, pure constants"
    - "Flat all-string dict list pattern (mirrors freshness_chips) for foreach-safe computed vars — summary_cards follows freshness_chips exactly"
    - "Chart restyle-in-place: figure builders keep trace/data-flow logic unchanged, only presentation (color, hover, layout) touched"

key-files:
  created:
    - app/app/theme.py
    - app/tests/test_theme.py
  modified:
    - app/app/state.py
    - app/tests/test_state.py

key-decisions:
  - "MUTED_TEXT mapped to #71717A (Radix gray.11-equivalent) since UI-SPEC described it qualitatively without a literal hex"
  - "Forecast base trace changed to dashed (was solid) so history-vs-forecast is distinguishable without relying on color alone, per D-08"
  - "Renamed 'Forecast band' trace to 'Expected range' per D-13 copy contract; updated pre-existing test assertion to match"
  - "summary_cards derives latest-actual via a new private helper _latest_actual_for(key) that exactly mirrors forecast_chart_figure's diesel_mnt multiplier convention, avoiding duplicated derivation logic drift"

requirements-completed: [D-05, D-08, D-09, D-10, D-11, D-12, D-13]

# Metrics
duration: 35min
completed: 2026-08-23
---

# Phase 6 Plan 1: Design Foundation Summary

**Locked design-token module plus horizon-reactive, foreach-safe `summary_cards` computed var, with both Plotly figure builders restyled in place to use those tokens.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-08-23T06:33:00Z
- **Completed:** 2026-08-23T07:08:00Z
- **Tasks:** 3
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments
- `app/app/theme.py` — single source of truth for every locked UI-SPEC color/spacing/typography/glyph/number-format value, zero third-party imports
- Both Plotly figure builders (`historical_chart_figure`, `forecast_chart_figure`) restyled in place: theme-token colors, transparent backgrounds, `,.2f`-formatted hover tooltips, `hovermode="x unified"`, and a labelled "Forecast start" `add_vline` marker with a dashed base-forecast line so history and forecast are visually distinguishable without relying on color alone
- New `DashboardState.summary_cards` computed var supplying exactly 4 horizon-reactive, foreach-safe card dicts (HDAN, PPAN, Diesel-MNT, FX) with base/range/direction/delta, derived entirely from the existing `forecast_results` var — no new state field, single `forecast_all` call site preserved

## Task Commits

Each task was committed atomically:

1. **Task 1: Create app/app/theme.py design token module** - `3f6919c` (feat)
2. **Task 2: Restyle both Plotly figure builders in place (D-08/D-09)** - `bc2a05a` (feat)
3. **Task 3: Add horizon-reactive summary_cards computed var (D-10..D-13)** - `2c449f5` (feat)

**Plan metadata:** (pending — this commit)

## Files Created/Modified
- `app/app/theme.py` - Design token module: colors, spacing, typography, direction glyphs, number formats
- `app/tests/test_theme.py` - Token coverage: hex values, spacing multiples-of-4, font sizes/weights, no dark-mode token
- `app/app/state.py` - Theme-token imports; restyled `historical_chart_figure`/`forecast_chart_figure`; new `SUMMARY_CARD_SERIES` constant, `summary_cards` computed var, `_latest_actual_for` helper
- `app/tests/test_state.py` - New/updated tests for chart restyle (marker, hover format, transparent bg, no-confidence-language) and summary_cards (shape, string-typing, horizon reactivity, up/down/flat direction, zero-actual edge case, single-call-site guard)

## Decisions Made
- `MUTED_TEXT` given an explicit hex (`#71717A`, Radix `gray.11`-equivalent) since UI-SPEC only described it qualitatively
- Forecast base-forecast line changed from solid to dashed for D-08's "distinguish historical vs. forecast visually" requirement
- "Forecast band" trace renamed to "Expected range" (D-13); the one pre-existing test asserting the old name was updated in place
- `summary_cards`'s latest-actual lookup factored into a private `_latest_actual_for` helper rather than inlined, so the diesel_mnt derivation convention has one implementation shared conceptually with (but not literally shared code with) `forecast_chart_figure`'s inline version — kept separate per read-only interface contract, but multiplier logic is identical

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `app/app/theme.py` and `DashboardState.summary_cards` are ready for plan 06-02 (page composition: `forecast_summary_cards()` component, page reorder per D-01..D-04)
- Full test suite green: 182/182 tests pass (`cd app && python -m pytest tests/ -q`)
- No blockers for 06-02

---
*Phase: 06-ux-ui-redesign*
*Completed: 2026-08-23*

## Self-Check: PASSED

All key files and task commits verified present on disk / in git log.
