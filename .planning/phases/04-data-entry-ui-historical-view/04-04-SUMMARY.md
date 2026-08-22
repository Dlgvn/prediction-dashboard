---
phase: 04-data-entry-ui-historical-view
plan: 04
subsystem: ui
tags: [reflex, plotly, historical-chart, series-selector]
dependency-graph:
  requires: [04-02, 04-03]
  provides: [historical-chart-figure, series-selector, single-source-series-labels]
  affects: []
tech-stack:
  added: []
  patterns:
    - "SERIES_LABELS/LABEL_TO_ATTR in state.py as the single source of truth for series display
      labels, consumed by app.py to rebuild _COLUMNS instead of hardcoding labels twice"
    - "historical_chart_figure as an @rx.var computed entirely from self.rows/self.selected_series
      with no rx.session() call, so switching the series selector never re-queries SQLite"
    - "Empty-state figure returns a valid go.Figure with an annotation instead of None, since
      rx.plotly requires a figure object in every state"
key-files:
  created: []
  modified:
    - app/app/state.py
    - app/app/app.py
    - app/tests/test_state.py
    - app/tests/test_app_components.py
decisions:
  - "Fixed a bug found during human verification: start_edit was wrapping cell values in
    to_string() which quote-wrapped them (e.g. '\"\"' instead of ''), so the blank draft row's
    Date input opened pre-filled with a literal empty-string-with-quotes instead of a truly
    empty input. Fixed by removing the redundant to_string() call (Rule 1 - bug)."
metrics:
  duration: 55min
  completed: 2026-08-22
---

# Phase 4 Plan 4: Historical Actuals Chart & Series Selector Summary

Added the last uncovered Phase 4 requirement (VIS-01): a single `rx.plotly` line chart driven by
a 16-entry "Series" dropdown, built entirely from in-memory state so switching series never hits
SQLite, then closed the phase with a full human-verified pass over add/edit/delete/persist/chart.

## What Was Built

- `SERIES_LABELS: dict[str, str]` and `LABEL_TO_ATTR: dict[str, str]` in `app/app/state.py`:
  promoted the label mapping (previously only in app.py's `_COLUMNS`) to a single source of
  truth, in the same order as the original 16-column table.
- `DashboardState.selected_series: str = "hdan"`, `select_series(self, label)` (label -> attr via
  `LABEL_TO_ATTR`, ignoring unknown labels — mitigates T-04-12), and `@rx.var series_label` for
  the `rx.select` `value` prop.
- `@rx.var historical_chart_figure(self) -> go.Figure`: builds x/y from `self.rows` filtered to
  non-None values for `self.selected_series`, plots with `plotly.express.line(markers=True)`,
  neutral gray line (`#697177`), no legend, `xaxis_title="Date"`/`yaxis_title=<series label>`.
  When all values are None, returns an empty figure annotated "No data for this series yet."
  (verbatim UI-SPEC copy). No `rx.session()` call anywhere in the computed var — mitigates
  T-04-14 (DoS via rapid selector changes forcing DB round trips).
- `app/app/app.py`: `_COLUMNS` rebuilt from `state.SERIES_LABELS` (still 17 entries, same order).
  New `historical_chart()` component: `rx.vstack` with a "Series" label + `rx.select` bound to
  `series_label`/`select_series`, and `rx.plotly(data=historical_chart_figure, width="100%",
  height="360px")`, wrapped in a `padding="1.5rem"` box. Inserted in `index()` after
  `add_row_button()` and before the reserved Phase 5 gap.
- Tests added to `app/tests/test_state.py`: series switching updates the figure's y data, null
  values are skipped, empty series shows the annotation, unknown labels are ignored, and a
  DB-free path proof (monkeypatched `reflex.session` raises, figure access still succeeds).
  `test_app_components.py` extended to assert `historical_chart()` builds without raising.
- Bug fix (found during Task 3 human verification): `start_edit` in `state.py` called
  `.to_string()` on cell values before assigning to `draft_value`, which quote-wrapped strings
  (`'""'` instead of `''`), breaking the blank draft row's Date input. Removed the redundant
  conversion.

## Verification

- `cd app && ./.venv/bin/python -m pytest tests -q` — 120 passed, no regressions.
- `grep -c "rx.plotly"` and `grep -c "rx.select"` in `app.py` each return exactly 1.
- `python -c "from app.state import SERIES_LABELS; assert len(SERIES_LABELS)==16"` exits 0.
- `python -c "import app.app as m; assert len(m._COLUMNS)==17; m.historical_chart(); m.index()"`
  exits 0.
- Human checkpoint (Task 3) approved by the user after live verification in the browser,
  including direct SQLite queries confirming persistence across restart (DATA-05) and correct
  chart re-rendering across HDAN/FX Rate/NG JKM series switches (VIS-01). Full defect list found
  and fixed during that pass: the `to_string()` quote-wrapping bug above.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed quote-wrapped cell value in start_edit**
- **Found during:** Task 3 human verification (blank draft row's Date cell opened as `'""'`
  instead of an empty input)
- **Issue:** `state.py`'s `start_edit` called `.to_string()` on the cell value before setting
  `draft_value`, adding literal quote characters around empty/string values
- **Fix:** Removed the redundant `.to_string()` call so `draft_value` holds the raw value
- **Files modified:** `app/app/state.py`
- **Commit:** 5f2d431

## Known Stubs

None — the chart is fully wired to live SQLite-backed `DashboardState.rows`; no mock or
placeholder data.

## Threat Flags

None — no new network endpoints or trust boundaries. T-04-12 (tampering via selector) and
T-04-14 (DoS via selector-driven DB load) mitigations implemented exactly as specified in the
plan's threat model; T-04-13 (information disclosure) accepted per single-user local-app scope.

## Self-Check: PASSED

- FOUND: app/app/state.py (contains `SERIES_LABELS`, `historical_chart_figure`)
- FOUND: app/app/app.py (contains `def historical_chart`)
- FOUND: app/tests/test_state.py, app/tests/test_app_components.py
- FOUND commit 6eed100 (feat(04-04): add selected_series state and historical chart figure)
- FOUND commit b624554 (feat(04-04): render historical chart block on the dashboard page)
- FOUND commit 5f2d431 (fix(04-04): stop quote-wrapping cell values passed to start_edit)
