---
phase: 05-forecast-ui-scenario-chart-excel-export
plan: 01
subsystem: forecast-state
tags: [reflex, state, forecasting, excel-export]
requires: []
provides:
  - DashboardState.horizon_months / forecast_series triad
  - DashboardState.forecast_results (5-key P-02 shape)
  - DashboardState.export_to_excel / _export_bytes
affects:
  - app/app/state.py
  - app/tests/test_state.py
tech-stack:
  added: []
  patterns:
    - "forecast_results is the single @rx.var call site for forecast_all() (Pitfall 2 guard)"
    - "_export_bytes/_history_df are plain (non-event) methods for unit-testability"
key-files:
  created: []
  modified:
    - app/app/state.py
    - app/tests/test_state.py
decisions:
  - "Empty/error forecast_results shape is {key: [] for key in FORECAST_SERIES_LABELS} — chart/table code in 05-02 can index all 5 keys unconditionally"
  - "row.model_dump() misbehaves on this SQLModel instance during export (returns non-dict field values) — _export_bytes builds records manually from date + SERIES_ATTRS instead, mirroring the existing _commit_draft_cell pattern"
metrics:
  duration: 35min
  completed: 2026-08-22
---

# Phase 5 Plan 1: Forecast State Core Summary

Extended `DashboardState` with horizon selection, an independent forecast-series
selector, live `markup_pct` loading from `AppSetting`, a single `forecast_results`
computed var wrapping `forecast_all()`, and an in-memory Excel export handler —
built with tests first (TDD) for the two behavior-adding tasks.

## What Was Built

**Task 1 — Horizon state, forecast-series selector, history DataFrame, markup_pct load**
(`app/app/state.py`):
- `FORECAST_SERIES_LABELS` / `FORECAST_LABEL_TO_ATTR` module-level maps (5 keys:
  hdan, ppan, diesel_usd_ton, diesel_mnt, fx_rate) and `FRESHNESS_SERIES` tuple
  (excludes diesel_mnt per D-07, reserved for plan 05-02).
- State vars: `horizon_months` (default 3), `forecast_series` (default "hdan"),
  `markup_pct` (default 0.0), `forecast_error`, `export_message`, `export_failed`.
- `set_horizon(value: list[int])` — unwraps the Radix slider's list-valued payload,
  clamps server-side with `max(1, min(MAX_HORIZON, ...))` (T-05-01), ignores an
  empty list.
- `select_forecast_series(label)` / `forecast_series_label` @rx.var — independent
  triad from Phase 4's `selected_series`/`series_label`.
- `load_markup_pct()` — reads `AppSetting(key="markup_pct")`, defaults to 0.0 if
  absent (defence-in-depth only; the row is confirmed seeded by Phase 1).
- `_history_df()` — builds a plain `pd.DataFrame` from `self.rows`, date-indexed
  and sorted ascending, matching `forecast_all`'s caller contract.

**Task 2 — `forecast_results` computed var** (TDD, `app/app/state.py` +
`app/tests/test_state.py`):
- `@rx.var forecast_results` calls `forecast_all(history, horizon_months,
  markup_pct)` exactly once per access, inside try/except `InsufficientHistoryError`
  / `ValueError`. On failure or empty `self.rows`, sets `forecast_error` to the
  UI-SPEC's Copywriting Contract string and returns the 5-key empty-list shape.
- Six new tests: horizon clamping, valid-history shape, empty-history error path,
  short-history error path, markup_pct threading (diesel_mnt differs by markup),
  and a call-counting monkeypatch proving `forecast_all` is invoked exactly once.

**Task 3 — `export_to_excel` / `_export_bytes`** (TDD, `app/app/state.py` +
`app/tests/test_state.py`):
- `_export_bytes()` — plain method, builds records from `date` + `SERIES_ATTRS`
  (not `row.model_dump()` — see Deviations), writes to `io.BytesIO()` via
  `df.to_excel(buffer, engine="openpyxl", index=False)`, never touches disk.
- `export_to_excel()` — event handler, calls `_export_bytes()` once, returns
  `rx.download(data=..., filename="prediction_dashboard_prices.xlsx")` on success;
  sets `export_failed`/`export_message` on any exception.
- Four new tests: round-trip via `pd.read_excel`, id-column exclusion, empty-rows
  no-raise, and actuals-not-forecast value fidelity.

## Verification

- `cd app && ./.venv/bin/python -m pytest tests/ -q` → 130 passed, 0 failures
  (120 pre-existing + 10 new).
- `grep -c "forecast_all(" app/app/state.py` → 1 real call site (other matches
  are comments/docstrings referencing `forecast_all()`).
- `grep -c "background=True" app/app/state.py` → 0.
- `grep -c 'engine="openpyxl"' app/app/state.py` → 1.
- `git diff --stat` confirms `app/app/forecasting.py` is unmodified — only
  `state.py` and `test_state.py` changed.

## TDD Gate Compliance

Both `tdd="true"` tasks followed RED → GREEN:
- Task 2: `test(05-01): add failing tests for forecast_results computed var`
  (cde3c78, confirmed failing before commit) → `feat(05-01): implement
  forecast_results computed var...` (eb73ce6).
- Task 3: `test(05-01): add failing tests for _export_bytes round-trip`
  (f508950, confirmed failing before commit) → `feat(05-01): implement
  export_to_excel handler...` (e393a80).

No REFACTOR commits were needed — GREEN implementations required no follow-up
cleanup beyond the model_dump fallback applied during GREEN itself.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `row.model_dump()` does not produce a plain dict for this SQLModel/rx.Model instance**
- **Found during:** Task 3 GREEN implementation, first test run.
- **Issue:** `PriceRow.model_dump()` raised `AttributeError: 'tuple' object has
  no attribute 'pop'` — Pydantic serialization on this model returns unexpected
  values for some fields (a `PydanticSerializationUnexpectedValue` warning on
  `_sa_instance_state` confirmed the SQLAlchemy-tracking field was leaking
  through). This is exactly the risk flagged in 05-RESEARCH.md's Assumption A3.
- **Fix:** Used the RESEARCH-recommended safe fallback — build the export record
  manually from `date` + `SERIES_ATTRS` via `getattr`, mirroring the proven
  pattern already used in `_commit_draft_cell`.
- **Files modified:** `app/app/state.py`.
- **Commit:** e393a80.

No other deviations — plan executed as written otherwise.

## Known Stubs

None. All state members added are fully wired to real DB reads and the real
`forecast_all()`/`to_excel()` calls; no placeholder data.

## Threat Flags

None — this plan's surface (slider clamp, AppSetting read, in-memory .xlsx
generation) was fully anticipated in the plan's `<threat_model>` (T-05-01,
T-05-02, T-05-03) and implemented per its disposition. No new endpoints, auth
paths, or schema changes introduced.

## Self-Check: PASSED

- `app/app/state.py` — FOUND (modified, contains `def export_to_excel`,
  `def forecast_results`... verified via grep above).
- `app/tests/test_state.py` — FOUND (130 tests collected and passing).
- Commit 3c97213 — FOUND in `git log`.
- Commit cde3c78 — FOUND in `git log`.
- Commit eb73ce6 — FOUND in `git log`.
- Commit f508950 — FOUND in `git log`.
- Commit e393a80 — FOUND in `git log`.
