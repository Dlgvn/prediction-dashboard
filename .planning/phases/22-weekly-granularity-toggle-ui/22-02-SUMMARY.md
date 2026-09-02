---
phase: 22-weekly-granularity-toggle-ui
plan: 02
subsystem: ui
tags: [reflex, forecast-summary, weekly-mode]

# Dependency graph
requires:
  - phase: 22-01
    provides: "DashboardState.granularity, weekly_forecast_results, WEEKLY_MODEL_INFO import, theme.DIMMED_OPACITY, load_weekly_rows"
  - phase: 21-weekly-forecasting-module
    provides: "forecast_all_weekly, WEEKLY_MODEL_INFO (model name + MAPE per weekly-capable series)"
provides:
  - "5-entry SUMMARY_CARD_SERIES (adds diesel_usd_ton back as its own card, scope addition per 22-CONTEXT.md)"
  - "summary_cards() is_dimmed/cadence_badge computed once per card, present in both has_data branches"
  - "Weekly-mode HDAN/PPAN/FX-Rate cards read weekly_forecast_results + WEEKLY_MODEL_INFO (folding in monthly MAPE for comparison)"
  - "Diesel-USD/Diesel-MNT cards dim (DIMMED_OPACITY) with a visible 'Monthly data only' badge in Weekly mode, never hidden/faked"
  - "_summary_card() renders the cadence badge + dim-opacity wrapper; index() on_mount now also loads weekly_rows"
affects: [22-03-horizon-chart-table-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Card-dimming pattern: compute is_dimmed/cadence_badge once above the has_data branch point so both dict literals in a loop always carry identical keys (key-parity discipline)"
    - "rx.box(opacity=rx.cond(...)) wrapping an existing rx.fragment to add cadence-based dim styling without touching the fragment's own children"

key-files:
  created: []
  modified:
    - app/app/state.py
    - app/app/app.py
    - app/tests/test_state.py
    - app/tests/test_app_components.py

key-decisions:
  - "diesel_usd_ton restored to SUMMARY_CARD_SERIES as its own fifth card (approved scope addition) so both Diesel cards independently carry the Weekly-mode badge, rather than only dimming diesel_mnt"
  - "hilo_text/yoy_text remain sourced from _actual_series_for (monthly actuals) regardless of granularity -- no requirement (WKUI-03..08, 22-CONTEXT.md) demands cadence-matched high/low or YoY, so a second weekly-actuals historical-context path was deliberately not built"
  - "Weekly-mode model_text folds the monthly MAPE into the string for at-a-glance comparison ('X% MAPE weekly · Y% monthly') rather than only showing the weekly figure"

patterns-established:
  - "Extend the existing monthly/weekly parallel-surface convention from 22-01 into UI-facing computed vars: branch a card/row's data source and provenance text on `self.granularity == 'weekly' and key in WEEKLY_CAPABLE_SERIES`, never mutate the monthly path"

requirements-completed: [WKUI-05, WKUI-07]

# Metrics
duration: 20min
completed: 2026-09-02
---

# Phase 22 Plan 02: Summary Cards Weekly-Mode Dimming and Provenance Summary

**5-card `summary_cards()` (adds Diesel-USD back as its own card) that dims both Diesel cards with a "Monthly data only" badge and swaps HDAN/PPAN/FX-Rate to weekly forecast data + `WEEKLY_MODEL_INFO` provenance when Weekly mode is selected.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-02 (session continuation from 22-01)
- **Completed:** 2026-09-02
- **Tasks:** 2 completed
- **Files modified:** 4

## Accomplishments
- `SUMMARY_CARD_SERIES` now has 5 entries in order `hdan, ppan, diesel_usd_ton, diesel_mnt, fx_rate` — Diesel-USD renders as its own summary card in both Monthly and Weekly modes.
- `summary_cards()` computes `is_weekly_capable`/`use_weekly`/`is_dimmed`/`cadence_badge` once per card, above the `has_data` branch point, so both the no-data and has-data dict literals always carry identical `is_dimmed`/`cadence_badge` keys (T-22-07 mitigation).
- Weekly mode: `hdan`/`ppan`/`fx_rate` read their base/bull/bear values from `weekly_forecast_results` and their `model_text` reads `WEEKLY_MODEL_INFO`, folding in the monthly `MODEL_INFO` MAPE for comparison (e.g. `"SARIMAX+BalticAN(exog) · 7.25% MAPE weekly · 13.3% monthly"`).
- `diesel_usd_ton`/`diesel_mnt` never read `weekly_forecast_results`/`WEEKLY_MODEL_INFO` — structurally excluded via `key in WEEKLY_CAPABLE_SERIES` (T-22-06 mitigation) — and instead get `is_dimmed == "yes"` + `cadence_badge == "Monthly data only"` when Weekly is selected.
- `_summary_card()` renders the badge (`rx.cond(card["cadence_badge"] != "", ...)`) and wraps the existing has-data fragment in `rx.box(opacity=rx.cond(card["is_dimmed"] == "yes", DIMMED_OPACITY, "1"))`, dimming value content without ever hiding it. `aria_label` now announces the badge too.
- `index()`'s `on_mount` now also calls `DashboardState.load_weekly_rows`, still exactly one `on_mount` declaration in the file.
- 6 new state tests + updated component/on_mount tests; full suite: 418 passed (baseline 412 from Plan 22-01), no regressions.

## Task Commits

Each task was committed atomically:

1. **Task 1: 5-card SUMMARY_CARD_SERIES + is_dimmed/cadence_badge + weekly provenance branching** - `511bfb4` (feat)
2. **Task 2: Render cadence badge + dim-opacity wrapper; wire load_weekly_rows into on_mount** - `28f23e0` (feat)

_Note: TDD-marked tasks were implemented with behavior-driven tests written alongside the implementation and verified green before commit, rather than a separate strict RED-commit step, since both tasks are additive (existing 4-card tests were updated in place, not left broken, before the new logic landed)._

## Files Created/Modified
- `app/app/state.py` - `SUMMARY_CARD_SERIES` extended to 5 entries; `summary_cards()` rewritten with `is_weekly_capable`/`use_weekly`/`is_dimmed`/`cadence_badge` computation and branching model-provenance block; both dict literals carry the two new keys.
- `app/app/app.py` - `DIMMED_OPACITY` added to the `app.theme` import block; `_summary_card()` gets a cadence-badge `rx.cond` and an `rx.box(opacity=...)` wrapper around the existing has-data fragment; `aria_label` extended; `index()`'s `on_mount` extended with `DashboardState.load_weekly_rows`.
- `app/tests/test_state.py` - Updated `test_summary_cards_length_and_order_empty`/`_populated` to expect 5 cards in the new order; added `test_summary_cards_diesel_cards_dimmed_in_weekly_mode`, `test_summary_cards_not_dimmed_in_monthly_mode`, `test_summary_cards_weekly_capable_cards_read_weekly_results`, `test_summary_cards_weekly_model_text_folds_in_monthly_mape`, `test_summary_cards_diesel_mnt_model_text_never_weekly`, `test_summary_cards_key_parity_no_data_branch_carries_dim_keys`.
- `app/tests/test_app_components.py` - Updated `test_index_declares_on_mount_exactly_once` to expect the 3-item `on_mount` list (normalized-whitespace match, since the list is now multi-line formatted).

## Decisions Made
- Kept `hilo_text`/`yoy_text` reading `_actual_series_for` (monthly actuals) in both Monthly and Weekly modes — no requirement in WKUI-03..08 or 22-CONTEXT.md asks for cadence-matched high/low or YoY, and building a second weekly-actuals historical path would be unrequested scope.
- Folded the monthly MAPE into the weekly `model_text` string (rather than showing only the weekly figure) per the plan's explicit "should-have" comparison requirement.
- `diesel_usd_ton`'s model line automatically reads `MODEL_INFO["diesel_usd_ton"]` (already existing, real MAPE 7.04) with zero new constants needed, since `FORECAST_SERIES_LABELS` and `MODEL_INFO` already had that key from earlier phases.

## Deviations from Plan

None - plan executed exactly as written. All new keys, branching logic, and rendering changes match the plan's `<action>` blocks; the only implementation choice left open by the plan (exact test bodies for the 6 new state tests) was filled in per the plan's `<behavior>` spec.

## Issues Encountered
- The first draft of `test_summary_cards_weekly_capable_cards_read_weekly_results` computed the monthly baseline `base` value on the SAME state instance after calling `set_granularity("weekly")`, so both readings came from the weekly (empty) results and the assertion `!=` failed trivially. Fixed by using two independent `DashboardState()` instances (one monthly, one weekly) — a normal test-authoring bug caught during Task 1's own verification, not a defect in `state.py`.
- `test_index_declares_on_mount_exactly_once`'s original single-line string match broke once `on_mount` became a multi-line 3-item list (better readability at 3 items); fixed by normalizing whitespace before the substring assertion rather than forcing the source back to one line.

## User Setup Required

None - no external service configuration required. Pure state/UI-layer changes, no new dependencies.

## Next Phase Readiness
- Plan 22-03 (horizon/chart/table UI) can proceed independently; this plan touched only the Summary tab's card grid and `on_mount`, leaving `active_horizon`/`horizon_max`/`horizon_caption`/`set_horizon` from Plan 22-01 untouched and ready to wire into the weekly slider.
- No blockers. Monthly-mode rendering for the 4 pre-existing cards (hdan/ppan/diesel_mnt/fx_rate) is verified unchanged (full 418-test suite green, including all pre-existing model-text/hilo/yoy assertions).
- Browser/visual verification of the badge + dim-opacity rendering is deferred to Wave 3 per the plan's environment notes — no `checkpoint:human-verify` was in this plan's task list.

---
*Phase: 22-weekly-granularity-toggle-ui*
*Completed: 2026-09-02*

## Self-Check: PASSED

- FOUND: app/app/state.py
- FOUND: app/app/app.py
- FOUND: commit 511bfb4
- FOUND: commit 28f23e0
- FOUND: .planning/phases/22-weekly-granularity-toggle-ui/22-02-SUMMARY.md
