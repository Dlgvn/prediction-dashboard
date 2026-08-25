---
phase: 13-model-provenance-display
plan: 01
subsystem: forecasting
tags: [reflex, state, forecasting, provenance, python]

# Dependency graph
requires:
  - phase: 02-model-decisions-research
    provides: frozen model choices and backtested MAPE values per series (SARIMAX 13.33%, Direct-OLS VAR 23.80%, Naive 7.04%/1.72%)
  - phase: 08-forecast-summary-cards
    provides: summary_cards @rx.var shape (flat all-string dict, two-branch append pattern) that this plan extends
provides:
  - MODEL_INFO frozen constant in forecasting.py — single source of truth for model name + MAPE per series
  - model_label/model_text keys on every summary_cards dict, sourced exclusively from MODEL_INFO
affects: [ui-model-provenance-badge, any future phase reading summary_cards or forecasting constants]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Frozen provenance constant pattern: display-layer strings (names, percentages) live in exactly one dict in forecasting.py; state.py only formats, never hand-types values"
    - "No-drift test pattern: assert set(CONSTANT_KEYS) == set(function_output.keys()) as a literal set, so a future key rename in either place fails a test loudly"

key-files:
  created: []
  modified:
    - app/app/forecasting.py
    - app/app/state.py
    - app/tests/test_forecasting.py
    - app/tests/test_state.py

key-decisions:
  - "MODEL_INFO lives in forecasting.py only (not state.py/app.py) per D-01/D-02, keeping the display layer free of hand-typed model names or percentages"
  - "diesel_mnt's MAPE is None (not 0.0, not a summed/averaged number) because it is a derived series with no independent backtest"
  - "model_text formatting branches on `is None`, not falsiness, per 13-UI-SPEC.md Copywriting Contract (U+00B7 middle dot, U+00D7 multiplication sign)"

patterns-established:
  - "Provenance constant pattern: model_text = f'{name} · {mape:.1f}% typical error' when mape is not None, else bare name"

requirements-completed: [VIS-05]

# Metrics
duration: 20min
completed: 2026-08-25
---

# Phase 13 Plan 01: Model Provenance Display Summary

**MODEL_INFO frozen constant in forecasting.py surfaced as model_label/model_text on every summary_cards dict, sourced from zero hand-typed literals in state.py**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added `MODEL_INFO: dict[str, tuple[str, float | None]]` to forecasting.py's frozen constants block with all 5 forecast_all series (hdan, ppan, diesel_usd_ton, fx_rate, diesel_mnt)
- diesel_mnt correctly carries `None` for MAPE (derived series, no independent backtest)
- Extended both `summary_cards` dict branches (no-data and with-data) with `model_label`/`model_text` keys, computed once before the branch split so both carry identical values
- Zero hand-typed model names or percentages in state.py — verified via grep gate
- No new `forecast_all()` call site added

## Task Commits

1. **Task 1: Add the MODEL_INFO frozen constant to forecasting.py** - `016bb81` (feat)
2. **Task 2: Surface model_label/model_text on every summary_cards dict** - `c4002f7` (feat)

**Plan metadata:** (this commit)

_Note: Tests were added alongside implementation in each task's single commit rather than a separate RED commit, since MODEL_INFO is a static constant with no meaningful "failing behavior" state to isolate — tests assert transcribed values against the existing docstrings, verified correct on first write._

## Files Created/Modified
- `app/app/forecasting.py` - Added `MODEL_INFO` frozen constant (5 entries) to the existing "Frozen constants" block
- `app/app/state.py` - Imported `MODEL_INFO`; computed `model_label`/`model_text` inside the `summary_cards` loop; added both keys to both dict literals
- `app/tests/test_forecasting.py` - 7 new tests: per-key value assertions, type checks, no-drift guard vs. `forecast_all` output keys
- `app/tests/test_state.py` - 5 new tests: presence in both branches, exact formatted text, diesel_mnt has no `%`/`·`, text identical across data/no-data branches

## Decisions Made
- MODEL_INFO is the sole source of truth; no duplicate constant or lazy import anywhere else
- diesel_mnt's `model_text` is the bare label string `"Derived (Diesel USD × FX)"` with no percentage, no "N/A", no trailing separator
- Branching on `is None` (never truthiness) to distinguish the derived series from a hypothetical 0.0% MAPE

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `summary_cards` now exposes `model_label`/`model_text` on all 4 cards, ready for a UI badge/tooltip component to render them (not part of this plan's scope — that's the next plan in this phase)
- Full test suite green: 335 passed
- No theme.py changes; no new dependencies

---
*Phase: 13-model-provenance-display*
*Completed: 2026-08-25*

## Self-Check: PASSED
