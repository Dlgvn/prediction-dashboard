---
phase: 12-fan-chart-legend-axis-fix
plan: 01
subsystem: ui
tags: [plotly, reflex, charts, layout, accessibility]

# Dependency graph
requires:
  - phase: 11-background-fix-theme-toggle
    provides: "tokens(mode) color resolution used unchanged by all four chart layout blocks"
provides:
  - "Non-overlapping fan chart legend/axis layout at desktop, tablet, and mobile viewport widths"
  - "Regression tests pinning legend orientation/position/anchors and bottom margin across all four figure code paths"
affects: [dashboard-polish, future-chart-work]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Plotly legend.y is a plot-domain fraction, not an absolute pixel offset — margin.b alone cannot fix cross-viewport legend/axis-title overlap when the legend wraps to multiple rows at narrow widths; legend.y must be tuned to the worst-case (narrowest) viewport."

key-files:
  created: []
  modified:
    - app/app/state.py
    - app/tests/test_state.py

key-decisions:
  - "Legend anchored below the plot (orientation='h', y=-0.55, yanchor='top', x=0.5, xanchor='center') instead of the previous unanchored top-of-plot default, applied identically to all four update_layout blocks (both figures, populated + empty-state branches)."
  - "Bottom margin widened from b=40 to b=140 to accommodate a 2-row-wrapped legend plus rotated tick labels at mobile width without clipping."
  - "legend.y iterated through -0.25 -> -0.45 -> -0.55 during human verification because it is a plot-domain fraction: growing margin.b shrinks the plot's data area, so the same y-fraction yields less absolute pixel separation at narrower/shorter viewports. Only -0.55 produced a safe (12px+) buffer at 390px without clipping at any breakpoint."
  - "Regression test floor for margin.b tightened from >= 80 to >= 130 to match the final b=140 value with headroom for future tuning."

requirements-completed: [VIS-04]

# Metrics
duration: 55min
completed: 2026-08-25
---

# Phase 12 Plan 01: Fan Chart Legend/Axis Fix Summary

**Fan chart legend repositioned below the plot (legend.y=-0.55, margin.b=140) across both chart figures, closing VIS-04 after three rounds of human-verified viewport tuning at 1440px/768px/390px.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-08-25T00:10:00Z
- **Completed:** 2026-08-25T01:05:00Z
- **Tasks:** 3 (2 auto + 1 checkpoint)
- **Files modified:** 2

## Accomplishments
- Legend in `historical_chart_figure` and `forecast_chart_figure` now renders horizontally centered below the x-axis, never overlapping tick labels or the axis title, at desktop, tablet, and mobile widths (human-verified with DOM bounding-rect measurements at each breakpoint)
- Bottom margin widened and legend.y tuned to survive a 2-row legend wrap at 390px with a safe ~12px buffer, not just a single pixel of clearance
- Five new regression tests pin legend orientation/x/y/anchors and margin.b across all four figure code paths (populated + empty-state, both charts)
- Zero color, trace, copy, or `app.py` regressions — confirmed via automated hex-literal grep and a live dark/light theme toggle during human verification (legend color matched `DARK["MUTED_TEXT"]` exactly)

## Task Commits

Each task was committed atomically, with three additional deviation-driven fix commits from the Task 3 human-verification checkpoint:

1. **Task 1: Move legend below plot area and widen bottom margin in both figure builders** - `22ba9c3` (fix)
2. **Task 2: Add regression tests pinning legend position and bottom margin for all four figure paths** - `4225038` (test)
3. **Task 3 checkpoint iteration — margin.b 90 -> 140** - `cc29ab7` (fix) — mobile-width legend wrap overlapped x-axis title with b=90
4. **Task 3 checkpoint iteration — legend.y -0.25 -> -0.45** - `525ec1e` (fix) — margin.b alone didn't move the legend far enough; root-caused to plot-domain-fraction semantics
5. **Task 3 checkpoint iteration — legend.y -0.45 -> -0.55** - `31b6e01` (fix) — -0.45 left only a 1.1px buffer at 390px, too fragile against font-rendering variance

**Plan metadata:** (this commit) `docs: complete 12-01 plan`

## Files Created/Modified
- `app/app/state.py` - All four `figure.update_layout(...)` blocks (historical empty/populated, forecast empty/populated) now set `legend=dict(orientation="h", y=-0.55, yanchor="top", x=0.5, xanchor="center")` and `margin=dict(l=40, r=16, t=16, b=140)`
- `app/tests/test_state.py` - Five new tests under "Phase 12: fan chart legend / axis non-overlap (VIS-04)" pinning legend orientation/y/anchors, margin.b >= 130, empty-state parity, and continued existence of the "Forecast start" annotation

## Decisions Made
- Kept the `legend=dict(...)` literal duplicated inline in all four blocks rather than extracting a shared constant, per 12-CONTEXT.md's guidance to match existing duplication level and avoid a new abstraction / shared-mutable-dict aliasing risk
- Did not touch `annotation_position="top left"` on the "Forecast start" vline — human verification confirmed no collision at any breakpoint after the legend moved below the plot, so the escape-hatch tuning path in Task 3 was not needed for the annotation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] margin.b=90 insufficient at mobile width (390px)**
- **Found during:** Task 3 (human-verify checkpoint, first pass)
- **Issue:** At 390px the legend wraps to 2 rows (32px -> 74px tall) because three legend labels don't fit on one line; with `margin.b=90` the wrapped legend overlapped the x-axis title ("Base forecast" text rendered on top of "Month" axis title)
- **Fix:** Widened `margin.b` from 90 to 140 in all four `update_layout` blocks
- **Files modified:** `app/app/state.py`
- **Verification:** Re-tested at 390px; overlap persisted (see deviation 2) — this fix alone was necessary but not sufficient
- **Committed in:** `cc29ab7`

**2. [Rule 1 - Bug] margin.b increase alone did not resolve mobile overlap**
- **Found during:** Task 3 (human-verify checkpoint, second pass)
- **Issue:** After widening margin.b to 140, the mobile-width overlap was essentially unchanged (buffer went from -27.5px to -28.0px). Root cause: Plotly's `legend.y=-0.25` is a plot-domain fraction, not an absolute pixel offset — growing `margin.b` shrinks the plot's data-area height, so the same y-fraction produces proportionally less absolute pixel separation at narrower/shorter viewports, offsetting the margin gain
- **Fix:** Moved `legend.y` from -0.25 to -0.45 in all four blocks (the correct lever — pushes the legend further below the axis regardless of plot height)
- **Files modified:** `app/app/state.py`
- **Verification:** Re-tested at all three widths; desktop/tablet passed comfortably (43.9px buffer), mobile buffer improved to +1.1px — technically non-overlapping but too fragile against font-rendering variance
- **Committed in:** `525ec1e`

**3. [Rule 1 - Bug] legend.y=-0.45 left only a 1.1px buffer at mobile width**
- **Found during:** Task 3 (human-verify checkpoint, third pass)
- **Issue:** A 1.1px buffer between the legend and x-axis title is not a durable fix — normal cross-browser/OS font-rendering or zoom-level differences could flip it back to overlapping for some users
- **Fix:** Moved `legend.y` from -0.45 to -0.55 in all four blocks, targeting a 15-20px minimum buffer
- **Files modified:** `app/app/state.py`
- **Verification:** Re-tested at all three widths; mobile buffer measured at 12.3px with no clipping (legend.bottom=1598.7 vs container.bottom=1611.4); tablet and desktop confirmed no clipping either; dark/light theme toggle confirmed no color regression; historical chart confirmed to still render no legend with all x-axis ticks visible. Human verification approved.
- **Committed in:** `31b6e01`

**4. [Rule 1 - Bug] Regression test floor loosened to match tuning**
- **Found during:** alongside deviations 1 and 3
- **Issue:** The Task 2 test asserted `margin.b >= 80`; as the human-verification loop pushed margin.b to 140, the test needed tightening so it would actually catch a future regression toward the original 40-90 range
- **Fix:** Updated the assertion to `margin.b >= 130`
- **Files modified:** `app/tests/test_state.py`
- **Verification:** Full test suite (130 tests) still passes
- **Committed in:** `cc29ab7`

---

**Total deviations:** 4 auto-fixed (all Rule 1 - bug fixes surfaced by the plan's own Task 3 human-verification escape hatch)
**Impact on plan:** All deviations were anticipated by the plan itself ("If the user reports a failure, re-tune the legend.y value, margin.b value... re-run this check") and stayed within the explicitly permitted tuning scope — no architectural changes, no new colors/tokens/packages/copy, no `app.py` changes. Three iterations were needed because the first two fixes (margin.b alone, then legend.y=-0.45) undershot the required buffer; each iteration was measured and verified before proceeding.

## Issues Encountered
- Plotly's `legend.y` domain-fraction semantics were non-obvious: increasing `margin.b` (which most intuitively "makes room" for the legend) does not reliably increase the absolute pixel gap between the legend and the x-axis title, because it simultaneously shrinks the plot's data-area height that `y` is fractional against. This was root-caused during the second human-verification pass and is now documented as a project pattern for future chart-layout work.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- VIS-04 closed; fan chart legend/axis layout is stable and regression-tested across all four figure code paths
- Phase 12 (Fan Chart Legend/Axis Fix) is now complete — this was the only plan in the phase
- No blockers for Phase 13

---
*Phase: 12-fan-chart-legend-axis-fix*
*Completed: 2026-08-25*

## Self-Check: PASSED

- FOUND: app/app/state.py
- FOUND: app/tests/test_state.py
- FOUND: .planning/phases/12-fan-chart-legend-axis-fix/12-01-SUMMARY.md
- FOUND: 22ba9c3, 4225038, cc29ab7, 525ec1e, 31b6e01 (all task/deviation commits verified in git log)
