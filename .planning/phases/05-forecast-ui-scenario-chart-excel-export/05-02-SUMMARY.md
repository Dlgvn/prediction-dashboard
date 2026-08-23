---
phase: 05-forecast-ui-scenario-chart-excel-export
plan: 02
subsystem: forecast-state-presentation
tags: [reflex, state, plotly, forecast]
dependency-graph:
  requires: ["05-01"]
  provides: ["freshness_chips", "forecast_chart_figure", "forecast_table_rows", "FORECAST_TABLE_COLUMNS"]
  affects: ["05-03"]
tech-stack:
  added: []
  patterns:
    - "fan-chart 4-trace pattern (Historical / Bear / Forecast band fill=tonexty / Base forecast) mirroring 05-RESEARCH.md Pattern 2"
    - "single-call-site guard: all presentation vars read self.forecast_results, never re-invoke forecast_all"
key-files:
  created: []
  modified:
    - app/app/state.py
    - app/tests/test_state.py
decisions:
  - "diesel_mnt historical values in forecast_chart_figure use the exact same diesel_usd*fx*(1+markup_pct/100) multiplier convention as forecasting.py's diesel_mnt_forecast, confirmed by reading that function before implementing"
  - "forecast_chart_figure and forecast_table_rows both key off self.forecast_results directly (not a second forecast_all call), enforced by the grep -c 'forecast_all(' == 1 real-call-site gate"
  - "FORECAST_TABLE_COLUMNS built as a comprehension over FORECAST_SERIES_LABELS x scenario names, not a hand-written 15-entry literal"
metrics:
  duration: 25min
  completed: 2026-08-23
---

# Phase 05 Plan 02: Forecast Presentation Computed Vars Summary

Added three `@rx.var`s to `DashboardState` — `freshness_chips`, `forecast_chart_figure`, and
`forecast_table_rows` — turning the `forecast_results` computed var (built in 05-01) into the
exact presentation-ready data shapes the Phase 5 UI (05-03) will render, all built purely from
in-memory state with no additional DB reads and no second `forecast_all()` call.

## What Was Built

**Task 1 — `freshness_chips` (DATA-06 / D-07):** Returns a list of 4 flat dicts
(`{"label", "date", "has_data"}`), one per `FRESHNESS_SERIES` entry (HDAN, PPAN, Diesel-USD,
FX), computed as `max(row.date for row in self.rows if getattr(row, attr) is not None)`. Series
with no non-null values get `date=""`, `has_data="no"`. Pure over `self.rows`, no `rx.session`
call — verified by both a source-inspection test and a monkeypatched-session-raises test.

**Task 2 — `forecast_chart_figure` (VIS-02 / D-04 / D-05):** A 4-trace `go.Figure` fan chart, in
exact order: `Historical` (12 trailing months, gray `#697177`) → `Bear` (invisible boundary,
width 0, `showlegend=False`) → `Forecast band` (`fill="tonexty"`,
`fillcolor="rgba(59,130,246,0.15)"`) → `Base forecast` (solid accent `#3B82F6`, width 2, drawn
last so it renders on top). The forecast x-axis is built by adding `pd.DateOffset(months=month)`
to the last historical date, keeping the whole axis continuous datetimes (never mixing dates
with integer month indices). Each of the three forecast traces is bridged with the last
historical (date, value) point prepended, so the band/base line visually starts at the last
actual rather than floating one month away. `diesel_mnt`'s historical segment is derived
in-line using the same `diesel_usd_ton * fx_rate * (1 + markup_pct/100)` convention as
`forecasting.py`'s `diesel_mnt_forecast`, confirmed by reading that function first so history and
forecast stay on the same scale. Empty/insufficient-history state returns a bare `go.Figure()`
with the UI-SPEC's exact copy, "No forecast available for this series yet."

**Task 3 — `forecast_table_rows` (FCST-06 / VIS-03):** Transposes `self.forecast_results`
(series-major) into one flat, preformatted (`f"{value:,.2f}"`) row per horizon month, with
composite keys `f"{series_key}_{scenario}"` (e.g. `hdan_base`, `diesel_mnt_bear`) for all 5
series x 3 scenarios simultaneously — this is what satisfies VIS-03's "all four tracked series
visible together" requirement (D-03's resolution: the table, not the chart). Added a matching
module-level `FORECAST_TABLE_COLUMNS: list[tuple[str, str]]`, built as a comprehension over
`FORECAST_SERIES_LABELS x ("base", "bull", "bear")` so plan 05-03's table component can iterate
headers without risk of drifting from the row keys. Returns `[]` when `forecast_results` has no
data for any series, matching the UI-SPEC's empty-state copy driven by `forecast_error`.

## Verification

- `cd app && ./.venv/bin/python -m pytest tests/ -q` — 147 passed (56 in `test_state.py`, up from
  39 before this plan).
- `grep -n "forecast_all(" app/app/state.py` — exactly one real call site (line 242, inside
  `forecast_results`); the other 3 matches are docstring/comment mentions.
- `grep -c "tozeroy\|toself" app/app/state.py` — 0 (band uses `fill="tonexty"` only, per VIS-02's
  explicit rejection of the wrong fill modes).
- `git diff --stat 6afc618 HEAD -- app/app/app.py` — empty (app.py untouched by this plan, as
  required).
- `grep -n "FORECAST_TABLE_COLUMNS" app/app/state.py` — comprehension over
  `FORECAST_SERIES_LABELS`, 15 entries (5 series x 3 scenarios).

## Deviations from Plan

None — plan executed exactly as written. The synthetic-history test fixture used by
`test_forecast_results_shape`/etc. already existed from 05-01 and required no changes.

## Requirements Coverage

This plan's frontmatter lists `[DATA-06, FCST-06, VIS-02, VIS-03]`. All four are covered at the
state-layer/computed-var level by this plan:
- DATA-06: `freshness_chips` — done.
- VIS-02: `forecast_chart_figure` — done (4-trace fan chart, filled band not crisp lines).
- FCST-06 + VIS-03: `forecast_table_rows` — done (month-major, all-5-series table data).

These vars are not yet rendered in `app.py` — that wiring is plan 05-03's scope per the plan's
own objective ("all figure/table construction belongs in state... `app.py` would run once at
compile time"). Do not mark these requirements fully "shipped" in user-facing terms until 05-03
renders them; this plan satisfies the state-layer half only, consistent with 05-01's precedent
for FCST-01/EXPORT-01.

## Known Stubs

None. All three vars are fully wired to `self.rows`/`self.forecast_results` with real data, no
hardcoded placeholders.

## Threat Flags

None. This plan only reads existing state (`self.rows`, `self.forecast_results`,
`self.markup_pct`) and constructs server-side Plotly figures / preformatted strings; no new
network surface, auth path, or schema change was introduced.

## Self-Check: PASSED

- `app/app/state.py` contains `def forecast_chart_figure` — FOUND.
- `app/tests/test_state.py` contains `test_forecast_chart_figure_traces` — FOUND.
- Commit `c82fc37` (freshness_chips) — FOUND in `git log --oneline`.
- Commit `fa6c93f` (forecast_chart_figure) — FOUND in `git log --oneline`.
- Commit `2565368` (forecast_table_rows) — FOUND in `git log --oneline`.
