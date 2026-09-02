---
phase: 22-weekly-granularity-toggle-ui
plan: 03
subsystem: ui
tags: [reflex, segmented-control, plotly, forecast-table, weekly-mode]

# Dependency graph
requires:
  - phase: 22-01
    provides: "DashboardState.granularity/set_granularity, active_horizon/horizon_max/horizon_caption, weekly_forecast_results, _weekly_actual_series_for"
  - phase: 22-02
    provides: "5-card SUMMARY_CARD_SERIES with weekly-mode dimming/provenance (unrelated surface, verified unaffected)"
  - phase: 21-weekly-forecasting-module
    provides: "forecast_all_weekly's shipped row-dict contract, keyed \"week\" (1-indexed), NOT \"month\""
provides:
  - "rx.segmented_control.root Monthly/Weekly toggle in horizon_control(), wired to DashboardState.granularity/set_granularity"
  - "horizon_control()'s slider bound to active_horizon/horizon_max/horizon_caption instead of hardcoded month values"
  - "DashboardState.available_forecast_series_labels -- narrows the Forecast tab's Series select to HDAN/PPAN/FX Rate while Weekly is active"
  - "WEEKLY_FORECAST_TABLE_COLUMNS constant + forecast_table()'s granularity branch (columns + \"Week of\"/\"Month\" header)"
  - "forecast_chart_figure/forecast_table_rows branch onto real week-ending dates via pd.DateOffset(weeks=entry[\"week\"]) while granularity == 'weekly', monthly branch left verbatim"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "if use_weekly: ... else: <verbatim prior body> branching inside forecast_chart_figure/forecast_table_rows, mirroring Plan 22-02's summary_cards branching convention"
    - "Segmented-control on_change wrapped in a lambda (value.to(str)) to bridge Reflex's str|list[str]-typed EventHandler signature down to set_granularity's plain str parameter -- a Reflex event-arg type-check requirement, not a business-logic change"

key-files:
  created: []
  modified:
    - app/app/state.py
    - app/app/app.py
    - app/tests/test_state.py
    - app/tests/test_app_components.py

key-decisions:
  - "forecast_warning's display banner in forecast_table() now also requires granularity == 'monthly' -- forecast_warning is a monthly-only signal (PPAN's stale-feature-anchor check from forecast_all); showing it while viewing the Weekly table would reference an issue the user isn't currently looking at. forecast_warning's own value/computation in state.py is untouched, only this display gate is new (deliberate correctness fix, not scope creep)."
  - "segmented_control's on_change uses a lambda wrapping value.to(str) rather than changing set_granularity's signature -- keeps Plan 22-01's str-only handler contract intact (still usable by any future non-Reflex caller/test) while satisfying Reflex's stricter str|list[str] EventHandler type-check for segmented_control (Radix's segmented control technically supports multi-select, hence the broader declared type)."
  - "forecast_table_rows' weekly branch keeps the row dict's date under the existing \"month\" key (not renamed to \"week\") so forecast_table()'s cell-rendering code stays untouched -- only the header LABEL and column SET branch on granularity, not the row-dict shape."

patterns-established:
  - "Monthly-mode branches are preserved as verbatim else-clauses, never rewritten-to-be-equivalent, so a diff review alone proves no regression -- continuation of the pattern set by Plan 22-02's summary_cards branching."

requirements-completed: [WKUI-03, WKUI-06, WKUI-08]

# Metrics
duration: 35min
completed: 2026-09-02
---

# Phase 22 Plan 03: Granularity Toggle, Weekly Horizon Slider, and Real Weekly Dates Summary

**Wires the Monthly/Weekly `rx.segmented_control.root` toggle into `horizon_control()`, narrows the Forecast tab's Series selector to weekly-capable series, and branches the fan chart + forecast table onto real week-ending calendar dates computed via `pd.DateOffset(weeks=entry["week"])` from Phase 21's shipped weekly forecast contract -- closing Phase 22 pending a live-browser checkpoint.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-09-02 (session continuation from 22-02)
- **Completed:** 2026-09-02 (Tasks 1-2 code/tests; Task 3 checkpoint handed to orchestrator, see below)
- **Tasks:** 2 of 3 completed autonomously; Task 3 is a `checkpoint:human-verify` gate, described below rather than approved (this executor has no browser tooling)
- **Files modified:** 4 (app/app/state.py, app/app/app.py, app/tests/test_state.py, app/tests/test_app_components.py)

## Accomplishments

- `WEEKLY_FORECAST_TABLE_COLUMNS` added to `state.py` (6 columns: hdan/ppan/fx_rate x base/bull/bear), mirroring `FORECAST_TABLE_COLUMNS`' derivation but scoped to `WEEKLY_CAPABLE_SERIES`.
- `available_forecast_series_labels` computed var: returns the 3 weekly-capable labels while `granularity == "weekly"`, the full 5-label list otherwise.
- `forecast_chart_figure` branches its data source (`weekly_forecast_results`/`_weekly_actual_series_for` vs. `forecast_results`/`_actual_series_for`) and date math (`DateOffset(weeks=entry["week"])` vs. `DateOffset(months=entry["month"])`) at the top; every downstream trace-building line is untouched and shared between both branches.
- `forecast_table_rows` branches at the top: the weekly path returns rows keyed by `WEEKLY_FORECAST_TABLE_COLUMNS`' composite keys, with the row's `"month"` key holding a real `YYYY-MM-DD` week-ending date computed from the last weekly actual date; the monthly path is byte-identical to before this plan.
- `horizon_control()` now renders a `rx.segmented_control.root` (Monthly/Weekly) above the horizon slider, which itself now binds `value=[DashboardState.active_horizon]`, `max=DashboardState.horizon_max`, and a `DashboardState.horizon_caption` readout -- fully granularity-aware, no more hardcoded `max=12`/`horizon_months`-only text.
- `forecast_chart()`'s Series `rx.select` now sources its options from `DashboardState.available_forecast_series_labels` (a reactive Var), so the option list itself narrows live when the user toggles to Weekly.
- `forecast_table()` branches its column set and first-column header (`"Week of"` vs `"Month"`) on `granularity`, and its empty-state text on `weekly_forecast_error` vs `forecast_error`; the `forecast_warning` banner is now additionally gated to `granularity == "monthly"` (a monthly-only data-quality signal that shouldn't surface while viewing the Weekly table).
- 11 new tests added (7 in `test_state.py`, 4 in `test_app_components.py`); full suite: 429 passed (baseline 418 before this plan, 425 after Task 1, 429 after Task 2), no regressions.
- Dev server started and confirmed reachable (`http://localhost:3005` returns 200) for the orchestrator's live-browser checkpoint verification.

## Task Commits

Each task was committed atomically:

1. **Task 1: Weekly branching for forecast_chart_figure, forecast_table_rows, and the Series selector** - `09e23b3` (feat)
2. **Task 2: Granularity segmented control in horizon_control(); chart selector + table branching in app.py** - `522d97c` (feat)

_Note: TDD-marked tasks were implemented with behavior-driven tests written alongside the implementation and verified green before commit (both tasks additive/branching over existing verbatim code), rather than a separate strict RED-commit step._

## Files Created/Modified

- `app/app/state.py` - Added `WEEKLY_FORECAST_TABLE_COLUMNS` module constant; `available_forecast_series_labels` computed var (new); `forecast_chart_figure` rewritten with a `use_weekly` branch at the top (data source, historical pairs, axis label, series label, date-offset math), all downstream trace-building code unchanged; `forecast_table_rows` rewritten with a `granularity == "weekly"` early-return branch producing real-date rows, monthly body kept verbatim as the fallthrough.
- `app/app/app.py` - `app.state` import extended with `WEEKLY_FORECAST_TABLE_COLUMNS` (and `FORECAST_SERIES_LABELS` removed as now-unused after the selector switched to a reactive Var); `horizon_control()` rewritten to add the segmented control (wrapped in a `value.to(str)` lambda to satisfy Reflex's `str|list[str]`-typed `on_change` signature) plus the granularity-aware slider/readout; `forecast_chart()`'s `rx.select` options switched to `DashboardState.available_forecast_series_labels`; `forecast_table()` rewritten with a `_table(columns, first_header)` helper, an `rx.cond` branching Weekly/Monthly column sets, the `forecast_warning` banner gated to monthly mode, and empty-state text branching on `weekly_forecast_error`/`forecast_error`.
- `app/tests/test_state.py` - Added `WEEKLY_FORECAST_TABLE_COLUMNS` to the import block; added `test_available_forecast_series_labels_narrows_when_weekly`, `test_available_forecast_series_labels_full_when_monthly`, `test_forecast_chart_figure_weekly_dates_are_week_spaced`, `test_forecast_chart_figure_monthly_unchanged`, `test_forecast_table_rows_weekly_has_no_diesel_columns`, `test_forecast_table_rows_weekly_dates_are_real_calendar_dates`, `test_forecast_table_rows_weekly_empty_when_no_weekly_rows`.
- `app/tests/test_app_components.py` - Added `test_horizon_control_has_segmented_control_toggle`, `test_forecast_chart_selector_uses_available_forecast_series_labels`, `test_forecast_table_branches_on_granularity_for_weekly_columns`, `test_forecast_table_compiles_with_weekly_column_set`.

## Decisions Made

- Gated `forecast_table()`'s `forecast_warning` banner to `granularity == "monthly"` only -- `forecast_warning` (PPAN's stale-feature-anchor check) is computed exclusively from the monthly `forecast_all` path and would be misleading/context-less if shown while the user is looking at the Weekly table. `forecast_warning`'s underlying computation is completely unchanged; only this new display condition was added (Rule 1/2 auto-fix, matches the plan's explicit note).
- Wrapped the segmented control's `on_change` in `lambda value: DashboardState.set_granularity(value.to(str))` rather than changing `set_granularity`'s signature -- Reflex's installed `rx.segmented_control.root` declares `on_change: EventHandler[on_value_change]` with a `Var[str | list[str]]` argument type (Radix's segmented control technically supports multi-select), which fails Reflex's strict event-handler-arg type check against `set_granularity(self, value: str)`. Casting the Var at the call site (not the handler) preserves Plan 22-01's locked `str`-only contract for `set_granularity` untouched. This was necessary to get `horizon_control()` to compile at all -- discovered via `test_horizon_control_compiles_to_component` failing with `EventHandlerArgTypeMismatchError`.
- Removed the now-unused `FORECAST_SERIES_LABELS` import from `app.py`'s `app.state` import block (the Series select's option list now comes from the reactive `available_forecast_series_labels` Var instead of the module-level dict), to keep the import block lint-clean per the project's ruff convention.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] `rx.segmented_control.root`'s `on_change` type mismatch with `set_granularity`**
- **Found during:** Task 2, running `test_horizon_control_compiles_to_component`
- **Issue:** The plan's literal action code (`on_change=DashboardState.set_granularity`) fails to compile: `EventHandlerArgTypeMismatchError: Event handler on_change expects str | list[str] for argument value but got <class 'str'> as annotated in DashboardState.set_granularity instead.` The installed Reflex/Radix `segmented_control` component's `on_value_change` trigger is typed `Var[str | list[str]]` (broader than a single-select toggle needs), while `set_granularity` (Plan 22-01, locked interface) only accepts `str`.
- **Fix:** Wrapped the call site in a lambda casting the Var down to `str` (`lambda value: DashboardState.set_granularity(value.to(str))`), leaving `set_granularity`'s signature and body completely untouched.
- **Files modified:** `app/app/app.py`
- **Commit:** `522d97c`

**2. [Rule 3 - Blocking issue] Unused `FORECAST_SERIES_LABELS` import after selector switched to a reactive Var**
- **Found during:** Task 2, after replacing the hardcoded `list(FORECAST_SERIES_LABELS.values())` selector options with `DashboardState.available_forecast_series_labels`
- **Issue:** `FORECAST_SERIES_LABELS` became an unused import in `app.py` (its only remaining use was the option list this plan replaced).
- **Fix:** Removed it from the `app.state` import block.
- **Files modified:** `app/app/app.py`
- **Commit:** `522d97c`

### Note on a literal acceptance-criteria mismatch

The plan's Task 1 acceptance criteria states `grep -c "WEEKLY_FORECAST_TABLE_COLUMNS" app/app/state.py` should return at least 2 ("definition + usage"). As implemented (following the plan's `<action>` code verbatim), `forecast_table_rows`' weekly branch iterates `WEEKLY_FORECAST_SERIES_LABELS` directly (matching the plan's literal action block), not `WEEKLY_FORECAST_TABLE_COLUMNS` -- so the constant is referenced exactly once in `state.py` (its own definition); its actual "usage" site is `app.py`'s `forecast_table()` (2 occurrences there: import + `rx.cond` usage), which is where the plan's own Task 2 acceptance criteria independently checks for it. This is judged a minor plan-authoring inaccuracy (the two acceptance criteria together correctly cover definition-in-state.py + consumption-in-app.py), not a functional gap -- no code change was made to force an artificial second reference in `state.py`.

## Issues Encountered

None beyond the two auto-fixed Rule-3 items above -- both were compile-time errors caught immediately by the existing `test_horizon_control_compiles_to_component` test, not runtime/logic bugs.

## User Setup Required

None for the code/test tasks. Task 3 (the human-verification checkpoint) requires a browser -- see below.

## Verification Commands Run

```
cd app && .venv/Scripts/python.exe -m pytest tests/test_state.py -q -k "forecast_chart_figure or forecast_table_rows or available_forecast_series_labels"
  -> 11 passed
cd app && .venv/Scripts/python.exe -m pytest tests/test_app_components.py -q -k "horizon_control or forecast_chart or forecast_table"
  -> 10 passed
cd app && .venv/Scripts/python.exe -m pytest tests/ -q
  -> 429 passed (after Task 1: 425 passed; after Task 2: 429 passed)
grep -c "rx.segmented_control.root" app/app/app.py        -> 1
grep -c "DashboardState.active_horizon" app/app/app.py    -> 1
grep -c "DashboardState.horizon_max" app/app/app.py       -> 1
grep -c "DashboardState.available_forecast_series_labels" app/app/app.py -> 1
grep -c "WEEKLY_FORECAST_TABLE_COLUMNS" app/app/app.py    -> 2
grep -c "WEEKLY_FORECAST_TABLE_COLUMNS" app/app/state.py  -> 1 (see note above)
grep -c 'DateOffset(weeks=entry\["week"\])' app/app/state.py -> 1
```

## Task 3: Live Browser Verification Checkpoint (APPROVED 2026-09-02)

This executor has no browser tooling and cannot perform Task 3's live-browser walkthrough. Per the orchestrator's environment notes, the dev server has been started and confirmed reachable, and the plan is otherwise fully coded and unit-tested; the checkpoint is handed off here for the orchestrator (a separate session with browser tooling) to perform.

**Dev server status:** Started via `cd app && REFLEX_USE_NPM=1 .venv/Scripts/python.exe -m reflex run --frontend-port 3005 --backend-port 8005` (backgrounded). Confirmed: `http://localhost:3005` returns HTTP 200. Log shows `App running at: http://localhost:3005/` and `Backend running at: http://0.0.0.0:8005`. The pre-seeded `reflex.db` (206 `WeeklyPriceRow` rows, 2022-08-05 to 2026-07-10, from Phase 19) requires no further setup.

**What to verify (nine checks, per the plan's `<how-to-verify>`):**

1. **Default is Monthly:** Clear localStorage, reload. Summary tab shows 5 cards (including the new Diesel-USD card), none dimmed, no "Monthly data only" badge anywhere.
2. **Monthly mode regression (CRITICAL, blocking):** Forecast tab -- horizon slider still runs 1-12 with "month(s)" readout; Series dropdown lists all 5 series; forecast table's first column header still reads "Month" with all 5 series' base/bull/bear columns.
3. **Toggle to Weekly:** Click "Weekly" in the new segmented control. Horizon slider range changes to 1-5 with "week(s)" readout (drag to confirm the thumb reaches 5). Series dropdown narrows to HDAN/PPAN/FX Rate only.
4. **Diesel cards dim honestly (CRITICAL, blocking):** Summary tab -- Diesel-USD/Diesel-MNT cards still visible, real (non-zero/non-blank) monthly numbers, visually dimmed, with a legible "Monthly data only" badge. HDAN/PPAN/FX Rate cards NOT dimmed, showing different base values than Monthly mode with a weekly model name + MAPE.
5. **Weekly chart/table dates are real:** Forecast tab, Weekly + HDAN selected -- fan chart's x-axis shows real calendar dates ~1 week apart on hover (not "1, 2, 3..." and not monthly-spaced). Forecast table's first column reads "Week of" with real `YYYY-MM-DD` dates; only HDAN/PPAN/FX Rate columns present.
6. **Persistence across reload:** With Weekly active, reload (F5) -- toggle still shows "Weekly", slider still in weeks mode, Diesel cards still dimmed, without re-clicking.
7. **Toggle back to Monthly:** Horizon slider returns to its prior month value (not reset to 1, not carrying over a week-count as a month-count); Diesel cards un-dim; HDAN/PPAN/FX Rate cards show monthly values/provenance again.
8. **Both themes:** Toggle dark mode -- segmented control, badge, and dimmed card content all legible in both light and dark mode.
9. **No console errors:** Throughout, no Reflex/React console errors/warnings, especially no "value did not match any item" warning from the Series `rx.select` on granularity toggle.

**Verification result (orchestrator, live browser at localhost:3005, 2026-09-02):** All 9 checks PASSED, including both CRITICAL/blocking checks.

1. ✅ Default Monthly — 5 cards render, none dimmed, on fresh load.
2. ✅ Monthly regression — horizon slider 1-12 "months", all 5 series in the selector, table header "Month" with 5-series columns; pixel/behavior-identical to pre-Phase-22.
3. ✅ Toggle to Weekly — slider range becomes 1-5 "weeks" (dragged to confirm max=5), Series dropdown narrows to HDAN/PPAN/FX Rate only (Diesel correctly absent).
4. ✅ Diesel cards dim honestly — Diesel-USD/Diesel-MNT stayed in their grid position, real (non-fabricated) monthly numbers, visibly dimmed, "Monthly data only" badge legible; HDAN/PPAN/FX Rate cards showed different (weekly) values with weekly model name + MAPE folding in the monthly comparison (e.g. "SARIMAX+BalticAN(exog) · 7.25% MAPE weekly · 13.3% monthly").
5. ✅ Weekly dates are real — chart x-axis showed real week-ending dates (May 3, May 17, May 31, Jun 14... spaced ~1-2 weeks apart, not relabeled months); axis title read "Week".
6. ✅ Reload persistence — full page reload (navigate) kept Weekly mode active, dimmed cards, weekly numbers, without re-toggling.
7. ✅ Toggle back to Monthly — slider reverted to prior month value (3 months, not reset/carried-over), Diesel cards un-dimmed, HDAN/PPAN/FX Rate cards back to monthly values/provenance.
8. ✅ Both themes — dark mode toggle confirmed legible: segmented control, badges, and dimmed card content all render cleanly in dark mode.
9. ✅ No console errors — `read_console_messages` returned no logs/errors throughout the entire walkthrough.

## Next Phase Readiness

- All code, automated tests (429/429 passing), and the live-browser checkpoint for Phase 22 are complete and approved.
- Phase 22 (Weekly Granularity Toggle & UI) is fully closed. WKUI-03 through WKUI-08 are all satisfied.
- This closes out the v2.1 "Weekly Forecast UI" milestone's roadmap (Phases 19-22, all complete).

---
*Phase: 22-weekly-granularity-toggle-ui*
*Completed: 2026-09-02 (Tasks 1-2; Task 3 checkpoint pending live-browser verification)*

## Self-Check: PASSED

- FOUND: app/app/state.py
- FOUND: app/app/app.py
- FOUND: commit 09e23b3
- FOUND: commit 522d97c
- FOUND: .planning/phases/22-weekly-granularity-toggle-ui/22-03-SUMMARY.md
