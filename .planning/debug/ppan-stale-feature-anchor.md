---
status: resolved
trigger: >
  PPAN forecast can silently use stale feature data in
  forecast_ppan_var_system (app/app/forecasting.py:373-386). It selects the
  most recent row where all VAR system-member features (hdan/baltic_an/urals)
  are non-null via complete_features.iloc[[-1]], but doesn't check how old
  that row is relative to "now" or relative to the PPAN series' own latest
  date. If any system-member column (e.g. urals) has a recent gap while
  ppan/hdan are up to date, the forecast silently anchors on a stale row
  with no warning surfaced to the UI -- the chart implies the forecast is
  current when it is actually built from outdated levels.
updated: 2026-08-26
---

## Symptoms

- Expected behavior: When a VAR system-member column (hdan/baltic_an/urals)
  has a recent gap (NaN) while ppan itself is up to date, the forecast
  should either warn the user that it anchored on a stale row, or otherwise
  surface the staleness -- not silently present a forecast as current.
- Actual behavior: `forecast_ppan_var_system` selects
  `complete_features.iloc[[-1]]` -- the most recent row where ALL system
  members are simultaneously non-null -- with no check against the PPAN
  series' own latest date or "now". No warning is threaded to
  app/app/state.py or the UI.
- Error messages: none (silent).
- Timeline: present since `forecast_ppan_var_system` was implemented
  (Phase 4/5 forecasting module).
- Reproduction: construct a `history` DataFrame where `urals` (or any system
  member) has a NULL in the most recent row(s) while `ppan`/`hdan` are
  populated through the latest date; call `forecast_ppan_var_system` and
  observe it silently uses an older row's feature values with no signal.

## Current Focus

hypothesis: complete_features.iloc[[-1]] picks the latest row with fully
  populated system-member features, which can be strictly older than
  history's/ppan's own latest observed row when any single member has a
  recent gap; the function has no comparison between the anchor row's date
  and the latest available date, so this is unconditionally silent.
next_action: reproduce with a synthetic DataFrame (gap in urals only) and
  confirm forecast_ppan_var_system anchors on a stale row silently; then
  implement staleness detection (compare complete_features anchor row's
  index/date to design's/history's latest index) and thread a warning
  through forecast_all -> state.py -> UI.
reasoning_checkpoint: null
tdd_checkpoint: null

## Evidence

- timestamp: 2026-08-26
  checked: reproduced with synthetic_history-style DataFrame, NaN'd `urals`
    for the last 2 rows, called forecast_ppan_var_system directly.
  found: complete_features.iloc[[-1]] anchor date was 2025-10-01 while
    history's/design's latest row was 2025-12-01 (2-month stale). Forecast
    returned normally with only {base, bull, bear} -- no warning field, no
    exception, no log line.
  implication: confirms the hypothesis exactly -- silent staleness with no
    signal anywhere in the return path (forecasting.py -> forecast_all ->
    state.py -> app.py).

- timestamp: 2026-08-26
  checked: app/app/state.py forecast_results computed var and app/app/app.py
    forecast_table() for existing UI-facing message patterns.
  found: forecast_error: str = "" is read directly by forecast_table()'s
    rx.cond empty-state branch (app.py ~365-409). No equivalent field exists
    for a "forecast succeeded but is degraded" signal.
  implication: established the precedent to follow -- add a parallel
    forecast_warning: str field, populated from forecast_all()'s result
    without disturbing the existing forecast_error contract (empty history /
    InsufficientHistoryError paths).

## Eliminated

(none -- first hypothesis confirmed on first reproduction attempt)

## Resolution

root_cause: >
  In forecast_ppan_var_system (app/app/forecasting.py), the anchor row used
  for prediction (`complete_features = design[feature_cols].dropna();
  last_features = complete_features.iloc[[-1]]`) is the most recent row
  where ALL PPAN VAR system-member features (hdan, baltic_an, urals) plus
  ppan's own lags are simultaneously non-null. When any single member
  column (e.g. urals) has a gap in its most recent observation(s) while
  ppan/hdan remain current, this anchor row is strictly older than the
  latest row in `design`/`history`. The function had no comparison between
  the anchor row's date and history's latest date, so the forecast silently
  used stale feature levels with zero signal surfaced anywhere in the
  return path.
fix: >
  forecast_ppan_var_system now compares complete_features.index[-1]
  (anchor date) against design.index[-1] (latest available date). When
  they differ, it builds a `warning` string naming the stale system-member
  column(s) (those NaN at the latest date) and how far back the anchor is,
  and adds it as a `warning` key to its return dict (empty string when
  current). This does NOT change `base`/`bull`/`bear` -- the same anchor
  row is still used for prediction; only detection/surfacing was added, per
  the "detect and warn, don't block" requirement.

  forecast_all (app/app/forecasting.py) now includes this as a sixth,
  additive `warning` key in its return dict (`ppan_fc.get("warning", "")`),
  documented in its docstring as non-breaking for existing `.get()`/`[...]`
  callers.

  app/app/state.py: added `forecast_warning: str = ""` field (parallel to
  the existing `forecast_error` pattern) and populated it from
  `result.get("warning", "")` inside the `forecast_results` computed var
  (cleared to "" on both empty-history and InsufficientHistoryError
  branches, matching forecast_error's reset behavior).

  app/app/app.py: forecast_table() now renders a small amber warning banner
  (rx.hstack with a "triangle-alert" icon + rx.text bound to
  DashboardState.forecast_warning) above the table/empty-state, shown only
  when forecast_warning is non-empty, following the existing
  csv_import_control() error-banner pattern (icon + colored text) already
  used elsewhere in app.py.
verification: >
  Ran the full test suite (`.venv/bin/python -m pytest app/tests/ -q`):
  359 passed, 0 failed, 0 regressions. Specifically:
  - app/tests/test_forecasting.py (50 tests): updated 3 pre-existing tests
    that asserted exact key sets on forecast_ppan_var_system/forecast_all
    output (now `series_keys | {"warning"}`) or iterated result.items()
    assuming all values were row-lists; added 3 new tests
    (test_ppan_var_system_warns_on_stale_anchor_row,
    test_ppan_var_system_no_warning_when_anchor_is_current,
    test_forecast_all_surfaces_ppan_warning) exercising a urals NaN gap and
    asserting both (a) forecast still returns valid numeric output at the
    requested horizon and (b) warning is non-empty and names "urals".
  - app/tests/test_state.py (145 tests): updated
    test_forecast_results_shape for the additive warning key; added
    test_forecast_results_surfaces_stale_ppan_warning verifying
    state.forecast_warning is populated end-to-end from a PriceRow-based
    history with a urals gap, while state.forecast_error stays empty (the
    forecast itself succeeded).
  Manual reproduction script (same one used to confirm root cause) re-run
  after the fix: result now includes
  `warning: "PPAN forecast anchored on data from 2025-10-01 instead of the
  latest available 2025-12-01 because urals has a more recent gap..."`.
files_changed:
  - app/app/forecasting.py
  - app/app/state.py
  - app/app/app.py
  - app/tests/test_forecasting.py
  - app/tests/test_state.py
