---
status: resolved
trigger: >
  Excel export silently swallows all exceptions from forecast computation in
  app/app/state.py around lines 412-415 (_export_bytes). The pattern is
  `except Exception: forecast_records = []` -- if forecast_all() raises
  (e.g. a statsmodels convergence failure, or another failure mode besides
  the recently-fixed PPAN stale-anchor warning case), the export silently
  produces a completed Excel file with an empty Forecast sheet and no error
  surfaced to the user.
updated: 2026-08-26
---

## Symptoms

- Expected behavior: When forecast_all() raises an unexpected exception
  during export, the user should be told the Forecast sheet is
  incomplete/missing and why, ideally still completing the export with
  actuals data (not blocking the user). When history is legitimately
  insufficient for forecasting (not an error), export should proceed
  silently with actuals-only, matching existing UX for "no forecast" cases.
- Actual behavior: `_export_bytes` in app/app/state.py (~lines 412-415)
  does `except Exception: forecast_records = []` for ALL exceptions,
  indiscriminately. This masks both legitimate empty-forecast cases and
  genuine bugs/failures the same way -- silently.
- Error messages: none surfaced to UI; only whatever swallowed exception
  message would have been available.
- Timeline: present since export forecast integration was added; sibling
  issue in forecasting.py's PPAN VAR staleness anchor was just fixed by
  adding a `forecast_warning` field threaded through forecast_all ->
  state.py -> app.py -- same threading pattern should apply here.
- Reproduction: call `forecast_all()` in a way that raises (e.g. mock a
  statsmodels convergence failure) during `_export_bytes`/`export_to_excel`
  and observe export completes with an empty Forecast sheet and no
  export_failed/export_message signal.

## Current Focus

status: resolved -- see Resolution below.

reasoning_checkpoint:
  hypothesis: "_export_bytes's blanket `except Exception: forecast_records
    = []` was never actually needed to handle the legitimate
    'not-enough-history' case -- that case is already fully absorbed
    upstream, one layer earlier, by the `forecast_results` computed var
    (state.py ~line 444-472), which catches `InsufficientHistoryError`/
    `ValueError` from `forecast_all()` and returns the empty 5-key P-02
    shape with no exception ever propagating. Therefore the except in
    _export_bytes exists purely to catch genuinely unexpected failures
    (e.g. a statsmodels/VAR bug), and it was masking them identically to
    the (already-handled-elsewhere) empty case, with total silence."
  confirming_evidence:
    - "state.py forecast_results (~L444-472): `try: result =
      forecast_all(...) except (InsufficientHistoryError, ValueError):
      self.forecast_error = ...; return empty_result` -- insufficient
      history never raises out of this var; it always resolves to the
      5-key empty-list shape."
    - "state.py forecast_table_rows (~L840-864) reads forecast_results and
      returns [] early if all series are empty -- again, no exception,
      just an empty list, for the legitimate case."
    - "state.py _forecast_export_records (~L370-385) reads
      self.forecast_table_rows (not forecast_all directly), so by the time
      _export_bytes's try/except runs, the insufficient-history path has
      already been fully resolved to [] two layers upstream -- the
      except-Exception in _export_bytes can therefore ONLY ever fire for a
      genuine unhandled bug (e.g. RuntimeError from a statsmodels
      convergence/VAR failure), never for routine empty-forecast."
    - "Reproduced directly: monkeypatched app.state.forecast_all to raise
      RuntimeError with real synthetic history (not empty rows) --
      _export_bytes previously would silently produce an empty Forecast
      sheet with zero signal to the user; confirmed via
      test_export_bytes_still_produces_actuals_when_forecast_raises_unexpectedly."
  falsification_test: "If insufficient-history rows (state.rows = [])
    triggered the except-Exception branch in _export_bytes (rather than
    resolving via forecast_results/forecast_table_rows returning []
    beforehand), the hypothesis would be wrong. Verified false: existing
    test_export_with_no_history_writes_header_only_forecast_sheet and new
    test_export_with_no_history_succeeds_silently both pass with
    export_failed staying False -- confirming that path never reaches the
    except branch at all."
  fix_rationale: "Root cause is that the except-Exception branch conflated
    two categories that don't actually overlap in practice (legitimate
    empty case never reaches it; only genuine bugs do), and silently
    discarded the second category. Fix keeps forecast_records = [] as a
    fallback (export must still complete with actuals data -- that
    behavior was correct) but adds a distinguishing flag
    (_last_export_forecast_failed) set only when the except branch
    actually fires, which export_to_excel reads to decide whether to
    surface an export_message/export_failed=True banner. This addresses
    the root cause (silent, undifferentiated swallowing) rather than a
    symptom, and reuses the project's existing export_message/export_failed
    UI-surfacing mechanism instead of adding a new field, matching how
    export_failed is used elsewhere (a non-blocking banner color signal,
    not a gate on rx.download)."
  blind_spots: "Have not tested every possible statsmodels/VAR exception
    type explicitly (only a generic RuntimeError simulating a convergence
    failure) -- but the except-Exception clause is intentionally broad by
    design (any unexpected failure should be caught, not just specific
    types), so this is consistent with the design intent, not a gap in the
    fix itself."
next_action: none -- resolved, tests passing (358/358), ready to archive.
tdd_checkpoint: null

## Evidence

- timestamp: 2026-08-26
  checked: state.py forecast_results computed var (~L444-472)
  found: Insufficient-history / ValueError cases from forecast_all() are
    already caught HERE, one layer above _export_bytes, and resolved to an
    empty 5-key result with self.forecast_error set -- no exception ever
    reaches _export_bytes for this case.
  implication: The except-Exception in _export_bytes cannot be serving the
    "not enough history" case at all; it can only ever catch genuinely
    unexpected failures.

- timestamp: 2026-08-26
  checked: state.py _forecast_export_records (~L370-385) and
    forecast_table_rows (~L840-864)
  found: _forecast_export_records reads self.forecast_table_rows (which
    reads forecast_results), not forecast_all directly -- confirming two
    layers of insulation from InsufficientHistoryError/ValueError before
    _export_bytes's try/except is ever reached.
  implication: The except-Exception clause in _export_bytes is dead weight
    for its apparent original purpose and was purely masking real bugs.

- timestamp: 2026-08-26
  checked: app.py export_button() rendering of export_message/export_failed
    (~L300-324)
  found: export_failed only controls text color (destructive vs muted) on
    the export_message banner; it does not gate/block the rx.download call
    (that's triggered unconditionally by returning the event from
    export_to_excel).
  implication: Safe to set export_failed=True for the "forecast sheet
    incomplete" case while still returning rx.download(...) -- matches the
    "detect and surface, don't block" pattern used for forecast_warning in
    the sibling ppan-stale-feature-anchor fix.

- timestamp: 2026-08-26
  checked: git show 80bb518 (ppan-stale-feature-anchor fix, style reference)
  found: That fix threaded a `warning` key through forecast_all's return
    dict (a forecast-computation-flow signal), not an exception-based
    mechanism -- confirming that forecast_all does NOT raise for its
    non-fatal issues either; this current bug is specifically about
    _export_bytes's own except-Exception, an export-flow concern distinct
    from forecast-computation-flow, so reusing export_message/export_failed
    (not a new forecast_warning-style field) is the correct-scoped fix.
  implication: No new state field needed; existing export_message/
    export_failed pattern is sufficient and correctly scoped.

- timestamp: 2026-08-26
  checked: Ran full test suite after fix
    (`.venv/bin/python -m pytest tests/ -q`)
  found: 358 passed, 0 failed (10 export-specific tests, including 3 new
    ones added for this fix).
  implication: Fix does not regress existing export/forecast/UI behavior.

## Eliminated

- hypothesis: forecast_all() raises directly on insufficient history, and
    _export_bytes's except-Exception is the ONLY thing handling that case.
  evidence: forecast_results (state.py ~L444-472) already catches
    InsufficientHistoryError/ValueError one layer above _export_bytes and
    resolves to an empty result before _export_bytes is ever involved --
    confirmed by tracing the call chain _export_bytes ->
    _forecast_export_records -> forecast_table_rows -> forecast_results ->
    forecast_all, and by test_export_with_no_history_succeeds_silently
    passing with export_failed=False.
  timestamp: 2026-08-26

## Resolution

root_cause: >
  `_export_bytes`'s `except Exception: forecast_records = []` (state.py,
  formerly ~L412-415) was written as if it needed to handle the
  "not-enough-history-to-forecast" case, but that case is already fully
  resolved one (and effectively two) layers upstream by the
  `forecast_results` computed var, which catches
  `InsufficientHistoryError`/`ValueError` from `forecast_all()` and returns
  an empty 5-key result with no exception propagating. As a result, the
  except-Exception in `_export_bytes` could only ever fire for genuinely
  unexpected failures (e.g. a statsmodels convergence failure or VAR system
  failure), and it silently discarded those with zero signal to the user --
  export would complete with an empty Forecast sheet and no indication
  anything had gone wrong.
fix: >
  Added a backend-only var `_last_export_forecast_failed: bool = False` on
  DashboardState. `_export_bytes` sets it to `True` only when
  `_forecast_export_records()` actually raises (the legitimate
  insufficient-history path still resolves to `[]` upstream without ever
  hitting this branch, so it stays `False` for that case, preserving silent
  actuals-only export). `export_to_excel()` reads this flag immediately
  after calling `_export_bytes()`: if set, it still returns the
  `rx.download(...)` event (export is not blocked -- actuals data is still
  delivered) but sets `export_failed = True` and populates `export_message`
  with a message stating the Forecast sheet is empty due to an unexpected
  error. This reuses the existing export_message/export_failed
  UI-surfacing mechanism (rendered in app.py's `export_button()`) rather
  than introducing a new field, matching its existing non-blocking-banner
  semantics.
verification: >
  Added three new tests in app/tests/test_state.py:
  (1) test_export_with_no_history_succeeds_silently -- confirms
  export_to_excel() with empty rows leaves export_failed=False and shows
  the normal "Downloaded..." message (no false-positive failure signal for
  the legitimate case).
  (2) test_export_surfaces_message_when_forecast_computation_raises_unexpectedly
  -- monkeypatches app.state.forecast_all to raise RuntimeError with real
  synthetic history; confirms export_to_excel() still returns a download
  event AND sets export_failed=True with an export_message mentioning both
  "Forecast" and "Downloaded".
  (3) test_export_bytes_still_produces_actuals_when_forecast_raises_unexpectedly
  -- confirms the Actuals sheet is still fully populated and
  _last_export_forecast_failed is True when forecast_all raises.
  Full suite run: `.venv/bin/python -m pytest tests/ -q` -> 358 passed, 0
  failed (includes all 10 export-related tests, old and new).
files_changed:
  - app/app/state.py
  - app/tests/test_state.py
