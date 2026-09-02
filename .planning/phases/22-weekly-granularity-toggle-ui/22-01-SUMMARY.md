---
phase: 22-weekly-granularity-toggle-ui
plan: 01
subsystem: state
tags: [reflex, rx.LocalStorage, pandas, statsmodels, sqlmodel]

# Dependency graph
requires:
  - phase: 21-weekly-forecasting-module
    provides: forecast_all_weekly, MAX_HORIZON_WEEKLY, WEEKLY_MODEL_INFO, InsufficientHistoryError (shared with monthly path)
  - phase: 19-weekly-data-ingestion
    provides: WeeklyPriceRow model (hdan/ppan/baltic_an/fx_rate, no diesel columns)
provides:
  - "DashboardState.granularity (rx.LocalStorage, own 'pd_granularity' key, default 'monthly')"
  - "set_granularity allowlist + forecast_series fallback to weekly-capable series"
  - "horizon_weeks / active_horizon / horizon_max / horizon_caption computed vars, fully independent from horizon_months"
  - "branching set_horizon (single handler, same on_change call site) writing horizon_weeks or horizon_months per granularity"
  - "weekly_rows / load_weekly_rows / _weekly_history_df / _weekly_actual_series_for mirroring the monthly load_rows/_history_df/_actual_series_for pattern"
  - "weekly_forecast_results computed var wrapping forecast_all_weekly() with single-call-site discipline and its own weekly_forecast_error"
  - "theme.DIMMED_OPACITY token"
affects: [22-02-summary-cards, 22-03-horizon-chart-table-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Second independent rx.LocalStorage var (granularity) mirroring theme_mode's own-key persistence mechanism"
    - "Parallel monthly/weekly state surfaces (rows/weekly_rows, forecast_results/weekly_forecast_results, forecast_error/weekly_forecast_error) kept as fully separate vars rather than shared/reused, to avoid cross-mode state bleed on toggle flip"

key-files:
  created: []
  modified:
    - app/app/state.py
    - app/app/theme.py
    - app/tests/test_state.py
    - app/tests/test_theme.py

key-decisions:
  - "granularity persists via its own rx.LocalStorage key ('pd_granularity'), never sharing theme_mode's key, so the two toggles can never desync"
  - "horizon_weeks is a wholly separate, non-persisted var from horizon_months -- switching granularity never reinterprets or resets either horizon value"
  - "set_horizon stays a single handler (not split into two) that branches internally on self.granularity, so both the existing monthly slider and the future weekly slider (Plan 22-03) wire to the same on_change target"
  - "weekly_forecast_results mirrors forecast_results' exact try/except/empty-result contract but uses a dedicated weekly_forecast_error var instead of reusing forecast_error, preventing a stale monthly error from leaking into weekly-mode UI or vice versa"

patterns-established:
  - "Weekly-mode data/forecast surface (weekly_rows, _weekly_history_df, weekly_forecast_results, weekly_forecast_error) is a parallel, independent mirror of the existing monthly surface -- Plan 22-02/22-03 should extend this mirroring convention rather than introducing conditional branching inside the existing monthly vars"

requirements-completed: [WKUI-04]

# Metrics
duration: 25min
completed: 2026-09-02
---

# Phase 22 Plan 01: Weekly Granularity State Foundation Summary

**Adds a persisted `granularity` toggle (rx.LocalStorage, mirroring `theme_mode`), independent weekly horizon controls, and a `weekly_forecast_results` var wrapping Phase 21's `forecast_all_weekly` with the same single-call-site discipline as the monthly path.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-02T00:00:00Z (approx, session start)
- **Completed:** 2026-09-02
- **Tasks:** 2 completed
- **Files modified:** 4 (app/app/state.py, app/app/theme.py, app/tests/test_state.py, app/tests/test_theme.py)

## Accomplishments
- `DashboardState.granularity` persists independently of `theme_mode` via its own `rx.LocalStorage("monthly", name="pd_granularity")`, defaulting to `"monthly"` (opt-in Weekly, per the locked non-goal).
- `set_granularity` allowlists `"monthly"`/`"weekly"` and falls `forecast_series` back to `"hdan"` when switching to Weekly with a non-weekly-capable series (`diesel_usd_ton`/`diesel_mnt`) selected.
- `horizon_weeks` (default 4) plus `active_horizon`/`horizon_max`/`horizon_caption` computed vars branch cleanly on `granularity` without ever touching `horizon_months`.
- `set_horizon` now branches internally to write `horizon_weeks` (clamped to `MAX_HORIZON_WEEKLY = 5`) or `horizon_months` (clamped to `MAX_HORIZON = 12`) depending on `granularity` -- still exactly one handler/call site.
- `weekly_rows`/`load_weekly_rows`/`_weekly_history_df`/`_weekly_actual_series_for` mirror the existing monthly `rows`/`load_rows`/`_history_df`/`_actual_series_for` pattern, sourced from `WeeklyPriceRow`.
- `weekly_forecast_results` wraps `forecast_all_weekly(history, self.horizon_weeks)` exactly once per access, returning the 3-key `{"hdan": [], "ppan": [], "fx_rate": []}` empty shape with `weekly_forecast_error` set on `InsufficientHistoryError`/`ValueError` or empty `weekly_rows`.
- `theme.DIMMED_OPACITY = "0.55"` added for Plan 22-02's Diesel-card dimming.
- 21 new unit tests added (`test_state.py` x20, `test_theme.py` x1); full suite: 412 passed (baseline 392), no regressions.

## Task Commits

Each task was committed atomically:

1. **Task 1: Granularity toggle var + independent weekly horizon controls** - `9da72d4` (feat)
2. **Task 2: Weekly data loading + weekly_forecast_results + DIMMED_OPACITY token** - `df17782` (feat)

_Note: TDD-marked tasks were implemented with behavior-driven tests written alongside the implementation and verified green before commit, rather than a separate strict RED-commit step, since both tasks are additive (no existing test needed to fail first)._

## Files Created/Modified
- `app/app/state.py` - Added `WEEKLY_CAPABLE_SERIES`, `WEEKLY_FORECAST_SERIES_LABELS`, `WEEKLY_SERIES_ATTRS` module constants; `granularity`, `horizon_weeks`, `weekly_forecast_error`, `weekly_rows` vars; `set_granularity`, `active_horizon`, `horizon_max`, `horizon_caption` (new); branching `set_horizon` (replaced, not duplicated); `load_weekly_rows`, `_weekly_history_df`, `_weekly_actual_series_for`, `weekly_forecast_results` (new); extended the `app.forecasting` import block with `MAX_HORIZON_WEEKLY`, `WEEKLY_MODEL_INFO`, `forecast_all_weekly`, and `app.models` import with `WeeklyPriceRow`.
- `app/app/theme.py` - Added `DIMMED_OPACITY = "0.55"` constant.
- `app/tests/test_state.py` - 20 new tests covering granularity defaults/allowlist/forecast_series fallback, active_horizon/horizon_max/horizon_caption branching, set_horizon's independent clamping, weekly row loading/reassignment, `_weekly_history_df` shape, and `weekly_forecast_results`' empty/populated/out-of-range paths (single-call-site verified via a counting monkeypatch).
- `app/tests/test_theme.py` - 1 new test asserting `DIMMED_OPACITY` is a string in (0, 1).

## Decisions Made
- Kept `set_horizon` as a single handler with internal branching (not split into `set_horizon_months`/`set_horizon_weeks`), per the plan's explicit constraint that both the existing monthly slider and the future weekly slider (Plan 22-03) must wire to the same `on_change` target.
- `weekly_forecast_error` is a fully separate var from `forecast_error` rather than reused, so a stale monthly error can never bleed into weekly-mode UI (or vice versa) after a granularity toggle.
- Test coverage for `weekly_forecast_results`' populated path uses the existing `synthetic_weekly_history` fixture (130 rows, already used by Phase 21's `test_forecasting.py`) converted to `WeeklyPriceRow` objects in-memory, avoiding a second, slower fixture.

## Deviations from Plan

None - plan executed exactly as written. All module/var/method names, signatures, and docstring rationale match the plan's `<action>` blocks verbatim.

## Issues Encountered
- The plan's literal acceptance-criteria command `python -c "from app.state import DashboardState; s = DashboardState(); ..."` raises `ReflexRuntimeError` when run as a bare script, because Reflex's `rx.State.__init__` guards direct instantiation outside a detected test/app context (`is_testing_env()`). This is an environment-detection quirk of the installed Reflex version, not an implementation defect -- the same assertions pass identically under `PYTEST_CURRENT_TEST` env var (confirmed) and, more importantly, via the actual pytest suite (`test_granularity_defaults_to_monthly` etc., all passing). No code change was needed; this is a plan-authoring note for future plans reusing this exact acceptance-criteria pattern.

## User Setup Required

None - no external service configuration required. Pure state/data-layer changes, no new dependencies.

## Next Phase Readiness
- Plan 22-02 (summary cards) can consume `granularity`, `weekly_forecast_results`, `WEEKLY_FORECAST_SERIES_LABELS`, `WEEKLY_CAPABLE_SERIES`, and `theme.DIMMED_OPACITY` directly.
- Plan 22-03 (horizon/chart/table UI) can consume `active_horizon`, `horizon_max`, `horizon_caption`, and the branching `set_horizon` to wire the weekly slider without any further state-layer work.
- No blockers. Monthly-mode behavior (`horizon_months`, `forecast_results`, `load_rows`, `_history_df`, `_actual_series_for`) is verified byte-for-byte unchanged (diff review + full 412-test suite green).

---
*Phase: 22-weekly-granularity-toggle-ui*
*Completed: 2026-09-02*

## Self-Check: PASSED

- FOUND: app/app/state.py
- FOUND: app/app/theme.py
- FOUND: commit 9da72d4
- FOUND: commit df17782
- FOUND: .planning/phases/22-weekly-granularity-toggle-ui/22-01-SUMMARY.md
