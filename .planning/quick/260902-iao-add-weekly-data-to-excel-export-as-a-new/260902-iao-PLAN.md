---
quick_task: 260902-iao-add-weekly-data-to-excel-export-as-a-new
type: execute
autonomous: true
files_modified:
  - app/app/state.py
  - app/tests/test_state.py
must_haves:
  truths:
    - "Exported workbook has a third sheet named 'Weekly' alongside the existing Actuals and Forecast sheets"
    - "Weekly sheet contains date + WEEKLY_SERIES_ATTRS columns (hdan, ppan, baltic_an, fx_rate) populated from self.weekly_rows"
    - "Weekly sheet is header-only (zero data rows) when self.weekly_rows is empty, without raising"
    - "Existing Actuals and Forecast sheet content/behavior is unchanged"
  artifacts:
    - path: "app/app/state.py"
      provides: "_export_bytes() writes a third 'Weekly' sheet from self.weekly_rows"
    - path: "app/tests/test_state.py"
      provides: "Tests for Weekly sheet existence, column shape, data round-trip, and Actuals/Forecast regression"
  key_links:
    - from: "DashboardState._export_bytes"
      to: "self.weekly_rows / WEEKLY_SERIES_ATTRS"
      via: "manual record-building loop (mirrors actuals_df pattern)"
      pattern: "weekly_df.*WEEKLY_SERIES_ATTRS"
---

<objective>
Add weekly HDAN/PPAN/Baltic AN/FX Rate data to the Excel export as a new "Weekly" sheet,
alongside the existing "Actuals" (monthly) and "Forecast" sheets in the same workbook.

Purpose: The app already has weekly data loaded via `load_weekly_rows()`/`self.weekly_rows`
(Phase 19-22, `WeeklyPriceRow` table) but the Excel export (`export_to_excel`) only ever
wrote the monthly Actuals + Forecast sheets. Users exporting the workbook currently get no
weekly data at all.

Output: `_export_bytes()` writes a three-sheet workbook (Actuals, Forecast, Weekly); the
"Weekly" sheet is additive only — no changes to Actuals/Forecast sheet content, the
`export_to_excel()` event handler, or the download filename.

Locked decision: Weekly data ships as a **separate new sheet** named "Weekly" — never
merged into the existing Actuals sheet rows.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@app/app/state.py
@app/app/models.py
@app/tests/test_state.py

<interfaces>
<!-- Existing code the executor must mirror exactly. No exploration needed. -->

From app/app/state.py (constants, already defined — reuse verbatim, do not redefine):
```python
WEEKLY_SERIES_ATTRS: tuple[str, ...] = ("hdan", "ppan", "baltic_an", "fx_rate")
```

From app/app/models.py:
```python
class WeeklyPriceRow(rx.Model, table=True):
    date: str
    hdan: Optional[float] = None
    ppan: Optional[float] = None
    baltic_an: Optional[float] = None
    fx_rate: Optional[float] = None
```

From app/app/state.py — `self.weekly_rows: list[WeeklyPriceRow]` is already populated by
`load_weekly_rows()` elsewhere in the app; `_export_bytes()` should read it directly
(same pattern as `self.rows` for actuals), NOT call `load_weekly_rows()` itself.

Existing `_export_bytes()` body (app/app/state.py, current lines ~500-547) to be extended,
NOT rewritten — only add a `weekly_df` build block plus one more `.to_excel()` call:

```python
def _export_bytes(self) -> bytes:
    records = []
    for row in self.rows:
        # row.model_dump() misbehaves on this SQLModel/rx.Model instance ...
        record = {"date": row.date}
        for attr in SERIES_ATTRS:
            record[attr] = getattr(row, attr)
        records.append(record)

    actuals_df = pd.DataFrame(records, columns=["date", *SERIES_ATTRS])

    try:
        forecast_records = self._forecast_export_records()
        self._last_export_forecast_failed = False
    except Exception:
        forecast_records = []
        self._last_export_forecast_failed = True

    forecast_columns = ["Month", *[label for _, label in FORECAST_TABLE_COLUMNS]]
    forecast_df = pd.DataFrame(forecast_records, columns=forecast_columns)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        actuals_df.to_excel(writer, sheet_name="Actuals", index=False)
        forecast_df.to_excel(writer, sheet_name="Forecast", index=False)
    buffer.seek(0)
    return buffer.getvalue()
```

House test style (app/tests/test_state.py, mirror exactly — `WeeklyPriceRow` and
`WEEKLY_SERIES_ATTRS` are already imported at the top of this test file):

```python
def test_export_has_actuals_and_forecast_sheets(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = [PriceRow(date="2026-01-01", hdan=9.5, ppan=8.25)]

    data = state._export_bytes()
    xl = pd.ExcelFile(io.BytesIO(data), engine="openpyxl")

    assert xl.sheet_names == ["Actuals", "Forecast"]
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add Weekly sheet to _export_bytes and update the export docstring</name>
  <files>app/app/state.py, app/tests/test_state.py</files>
  <behavior>
    - Weekly sheet present: `_export_bytes()` on a state with `weekly_rows` populated
      produces a workbook whose `pd.ExcelFile(...).sheet_names` includes `"Weekly"` as a
      third sheet (in addition to unchanged `"Actuals"`, `"Forecast"`), i.e.
      `xl.sheet_names == ["Actuals", "Forecast", "Weekly"]`.
    - Weekly sheet columns: reading the "Weekly" sheet with `pd.read_excel(..., sheet_name="Weekly")`
      yields columns `["date", *WEEKLY_SERIES_ATTRS]` exactly (`date`, `hdan`, `ppan`,
      `baltic_an`, `fx_rate`).
    - Weekly sheet data round-trip: given `state.weekly_rows = [WeeklyPriceRow(date="2026-01-02", hdan=1.1, ppan=2.2, baltic_an=3.3, fx_rate=3450.0), ...]`,
      the "Weekly" sheet has the same row count as `weekly_rows` and each cell value matches
      the source row (e.g. `df.iloc[0]["hdan"] == 1.1`).
    - Empty weekly_rows: with `state.weekly_rows = []`, `_export_bytes()` does not raise, and
      the "Weekly" sheet exists with 0 data rows and the correct header columns.
    - Regression: existing Actuals/Forecast sheet tests (`test_export_to_excel_roundtrip`,
      `test_export_excludes_id_column`, `test_export_empty_rows_does_not_raise`,
      `test_export_actuals_sheet_values`, `test_forecast_sheet_matches_dashboard_table`,
      `test_forecast_sheet_honours_selected_horizon`, `test_forecast_sheet_headers_match_table_columns`,
      `test_export_with_no_history_writes_header_only_forecast_sheet`,
      `test_export_does_not_add_forecast_all_call_site`, `test_export_with_no_history_succeeds_silently`,
      `test_export_surfaces_message_when_forecast_computation_raises_unexpectedly`,
      `test_export_bytes_still_produces_actuals_when_forecast_raises_unexpectedly`)
      must all still pass unmodified — this feature is purely additive. Update ONLY
      `test_export_has_actuals_and_forecast_sheets`'s assertion (it currently asserts
      `xl.sheet_names == ["Actuals", "Forecast"]`, which must become
      `["Actuals", "Forecast", "Weekly"]` since that's a direct, correct consequence of
      the new sheet, not a workaround) — rename it to
      `test_export_has_actuals_forecast_and_weekly_sheets` for clarity, or add the Weekly
      assertion inline; either is fine as long as the old two-sheet assertion is corrected
      to reflect the new three-sheet reality.
  </behavior>
  <action>
    In app/app/state.py, extend `_export_bytes()` (do not touch `_forecast_export_records`,
    `export_to_excel`, or the Actuals/Forecast build blocks):

    1. After the `forecast_df` construction and before the `buffer = io.BytesIO()` line, add
       a weekly-records build block that mirrors the existing `actuals_df` pattern exactly
       (manual record-building from `self.weekly_rows` + `WEEKLY_SERIES_ATTRS`, avoiding
       `row.model_dump()` for the same documented reason `self.rows` does):

       ```python
       weekly_records = []
       for row in self.weekly_rows:
           record = {"date": row.date}
           for attr in WEEKLY_SERIES_ATTRS:
               record[attr] = getattr(row, attr)
           weekly_records.append(record)

       weekly_df = pd.DataFrame(weekly_records, columns=["date", *WEEKLY_SERIES_ATTRS])
       ```

    2. Inside the existing `with pd.ExcelWriter(...) as writer:` block, add a third
       `.to_excel()` call after the Forecast sheet write:

       ```python
       weekly_df.to_excel(writer, sheet_name="Weekly", index=False)
       ```

    3. Update `_export_bytes()`'s docstring: change "two-sheet export workbook" to
       "three-sheet export workbook", and add one sentence noting the Weekly sheet is
       sourced from `self.weekly_rows`/`WEEKLY_SERIES_ATTRS` and is additive (does not
       affect Actuals/Forecast). Keep all existing docstring content about the D-01/D-02/D-03
       history otherwise intact.

    4. `WEEKLY_SERIES_ATTRS` is already imported/defined at module level in state.py — do
       not redefine it locally.

    In app/tests/test_state.py, within the "Excel export (EXPORT-01, EXPORT-02)" section
    (near the existing `test_export_has_actuals_and_forecast_sheets` test around line 1200):

    5. Update `test_export_has_actuals_and_forecast_sheets` — change its final assertion
       from `assert xl.sheet_names == ["Actuals", "Forecast"]` to
       `assert xl.sheet_names == ["Actuals", "Forecast", "Weekly"]`. Rename the test to
       `test_export_has_actuals_forecast_and_weekly_sheets`.

    6. Add `test_export_weekly_sheet_columns` — build `state.weekly_rows` with 1-2
       `WeeklyPriceRow` instances (not persisted via session, same in-memory pattern as
       `test_export_to_excel_roundtrip` uses for `state.rows`), call `_export_bytes()`,
       read `sheet_name="Weekly"` with `pd.read_excel`, assert
       `list(df.columns) == ["date", *WEEKLY_SERIES_ATTRS]`.

    7. Add `test_export_weekly_sheet_data_roundtrip` — build `state.weekly_rows` with known
       values (e.g. `WeeklyPriceRow(date="2026-01-02", hdan=1.1, ppan=2.2, baltic_an=3.3, fx_rate=3450.0)`),
       call `_export_bytes()`, read the "Weekly" sheet, assert row count matches and
       `df.iloc[0]["hdan"] == 1.1` (and similarly for the other three attrs).

    8. Add `test_export_weekly_sheet_empty_does_not_raise` — `state.weekly_rows = []`, call
       `_export_bytes()` (must not raise), read "Weekly" sheet, assert `len(df) == 0` and
       columns still equal `["date", *WEEKLY_SERIES_ATTRS]`.

    9. Add `test_export_actuals_and_forecast_unaffected_by_weekly_addition` — set both
       `state.rows` (from `synthetic_history` fixture, matching `test_forecast_sheet_matches_dashboard_table`'s
       pattern) AND `state.weekly_rows` (non-empty) simultaneously, call `_export_bytes()`,
       and assert the Actuals sheet row count still equals `len(state.rows)` and the
       Forecast sheet still has the expected `Month`/column shape — proving the Weekly
       addition doesn't perturb the other two sheets when all three are populated together.

    Import `WEEKLY_SERIES_ATTRS` and `WeeklyPriceRow` in test_state.py only if not already
    imported at module level — check first; per the interfaces block above they already are
    (line 13 `WeeklyPriceRow`, line 23 `WEEKLY_SERIES_ATTRS`), so no new imports should be
    needed.
  </action>
  <verify>
    <automated>cd app && .venv/Scripts/python -m pytest tests/test_state.py -k "export" -v</automated>
  </verify>
  <done>
    All export-related tests pass, including the 4 new/updated Weekly tests. `_export_bytes()`
    produces a workbook with `sheet_names == ["Actuals", "Forecast", "Weekly"]` whose Weekly
    sheet has columns `["date", "hdan", "ppan", "baltic_an", "fx_rate"]`, correctly round-trips
    weekly row data, and degrades gracefully (header-only) when `weekly_rows` is empty.
  </done>
</task>

<task type="auto">
  <name>Task 2: Full regression run</name>
  <files>app/app/state.py, app/tests/test_state.py</files>
  <action>
    Run the full test suite to confirm the addition is genuinely non-breaking across the
    whole app (not just the export tests targeted in Task 1), per the constraint that the
    431/431 baseline must only go up, never down. No code changes expected in this task —
    it is a verification-only step. If any unrelated test fails, investigate and fix within
    the scope of app/app/state.py's Weekly-sheet addition only (do not touch unrelated
    subsystems); if the failure is pre-existing and unrelated to this change, report it
    rather than silently patching unrelated code.
  </action>
  <verify>
    <automated>cd app && .venv/Scripts/python -m pytest -q</automated>
  </verify>
  <done>
    Full suite passes with a count >= 431 + (number of new tests added in Task 1), 0
    failures, 0 errors.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|--------------|
| DashboardState -> local .xlsx download | Server-generated file handed to the user's own browser download; no network/external input crosses this boundary |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-quick-01 | Information Disclosure | Weekly sheet in exported workbook | accept | Same trust level as existing Actuals/Forecast sheets — single local user exporting their own DB data to their own machine; no new data source or auth boundary introduced |
| T-quick-02 | Denial of Service | `_export_bytes()` weekly-records loop | accept | `self.weekly_rows` is bounded by the same single-user, low-hundreds-of-rows scale as `self.rows` (Phase 19-02 seeded 206 rows); no unbounded/attacker-controlled growth path |
</threat_model>

<verification>
1. `cd app && .venv/Scripts/python -m pytest tests/test_state.py -k "export" -v` — all export tests pass, including the 4 new/updated Weekly-sheet tests.
2. `cd app && .venv/Scripts/python -m pytest -q` — full suite green, count >= prior baseline (431) plus new tests, 0 regressions.
3. Manually inspect the diff of `_export_bytes()` in app/app/state.py — confirm only additive lines were introduced (no changes to `actuals_df`/`forecast_df` construction, `export_to_excel()`, or the download filename).
</verification>

<success_criteria>
- Exported workbook has exactly 3 sheets in this order: Actuals, Forecast, Weekly.
- Weekly sheet columns are exactly `date, hdan, ppan, baltic_an, fx_rate`.
- Weekly sheet correctly reflects `self.weekly_rows` contents, including the empty case (header-only, no error).
- Every previously passing test still passes; no reduction in the 431-test baseline.
- No changes to `export_to_excel()`'s event-handler behavior, download filename, or the Actuals/Forecast sheets' existing content/columns.
</success_criteria>

<output>
After completion, create `.planning/quick/260902-iao-add-weekly-data-to-excel-export-as-a-new/260902-iao-SUMMARY.md`
</output>
