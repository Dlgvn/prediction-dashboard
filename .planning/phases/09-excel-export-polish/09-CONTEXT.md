# Phase 9: Excel Export Polish — Context

**Gathered:** 2026-08-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a second sheet to the Excel export containing forecast data (base/bull/bear per series, per month), alongside the existing actuals-only sheet. This explicitly supersedes the Phase 5 decision recorded in `_export_bytes`'s docstring ("D-08 — the actuals table only, never forecast output") — EXPORT-02 is a deliberate v1.2 scope expansion of that boundary, not an accidental regression.

In scope: a new "Forecast" sheet, renaming both sheets, exporting the currently-selected horizon's data.
Out of scope: native Excel chart embedding (deferred per v1.2 research findings — FEATURES.md flagged this as a nice-to-have differentiator, not required for EXPORT-02), any change to what data is stored or how forecasts are computed.
</domain>

<decisions>
## Implementation Decisions

### Export horizon scope
- **D-01:** The forecast sheet captures the CURRENTLY SELECTED horizon at the moment the user clicks Export — exactly what's on screen in the Forecast table at that time. Not always the full 1-12 month range.

### Sheet layout
- **D-02:** The Forecast sheet mirrors the on-screen forecast table's exact structure — one row per month, columns per `FORECAST_TABLE_COLUMNS` (base/bull/bear × HDAN/PPAN/Diesel-USD/Diesel-MNT/FX). Reuse `forecast_table_rows`'s existing computed structure/values directly rather than re-deriving from `forecast_results`.

### Sheet naming
- **D-03:** The actuals sheet (currently unnamed/default "Sheet1") is renamed to `"Actuals"`. The new sheet is named `"Forecast"`.

### Claude's Discretion
- Exact column header wording for the Forecast sheet (reuse `FORECAST_TABLE_COLUMNS` labels verbatim, consistent with the on-screen table, e.g. "HDAN base", "HDAN bull", "HDAN bear").
- Number formatting in the Excel cells (plain floats vs. Excel number format strings) — match whatever the existing Actuals sheet already does for consistency, no new formatting system.
- Filename: keep the existing `prediction_dashboard_prices.xlsx` filename (no requirement to rename it just because content grew a sheet).
- Edge case: what the Forecast sheet contains when `forecast_table_rows` is empty (insufficient history to forecast) — write an empty sheet with just headers, consistent with the on-screen behavior which shows `forecast_error` text instead of a table in that case.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing code (primary implementation surface)
- `app/app/state.py` — `_export_bytes` (line ~263, the function being extended — note its docstring's stale D-08 constraint needs updating to reflect this phase's supersession), `export_to_excel` (line ~286, the event handler, unchanged otherwise), `forecast_table_rows` (line ~683, the EXACT data structure to reuse for the new sheet), `FORECAST_TABLE_COLUMNS` (line ~123, column header source)
- `app/app/app.py` — `export_button()` — unchanged, but confirm no UI change is needed since this is a data-only enrichment of the existing button's output

### v1.2 milestone research (MANDATORY)
- `.planning/research/FEATURES.md` — confirms multi-sheet Excel export (Data + Forecast) is the recommended differentiator, native chart embedding explicitly deferred
- `.planning/research/ARCHITECTURE.md` — notes Excel export polish is "independent, low risk, touches only `_export_bytes`"
- `.planning/research/STACK.md` — confirms openpyxl (already a dependency) is sufficient for multi-sheet writes via `pd.ExcelWriter`, no new library

### Project-level
- `.planning/REQUIREMENTS.md` — EXPORT-02
- `.planning/ROADMAP.md` — Phase 9 entry
- `.planning/phases/05-forecast-ui-scenario-chart-excel-export/` — original EXPORT-01/D-08 decision being superseded here (if this directory/context exists, reference it for the original rationale)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `forecast_table_rows` already produces one dict per month with all base/bull/bear values as formatted strings — this is likely NOT directly usable for Excel (strings vs. numeric cells) — the new sheet-building code should probably read the same underlying `forecast_results` numeric data that `forecast_table_rows` formats from, to keep Excel cells numeric rather than pre-formatted strings. Planner/executor should verify which is more appropriate against 08-UI-SPEC precedent (numeric cells preferred for a spreadsheet a user might do further math on).
- `pd.DataFrame.to_excel` is already the established pattern (`_export_bytes`) — extend via `pd.ExcelWriter(buffer, engine="openpyxl")` with two `df.to_excel(writer, sheet_name=...)` calls rather than introducing a different Excel-writing approach.

### Established Patterns
- `_export_bytes` is a plain method (not an event handler) specifically so it's unit-testable without Reflex's event machinery — the new forecast-sheet logic should follow the same testability discipline.
- Never writes to disk — BytesIO buffer only. This must remain true for the two-sheet version.

### Integration Points
- `export_to_excel`'s try/except error-handling wrapper is unchanged; if forecast data is unavailable, `_export_bytes` should not raise, matching D-03's discretion note above.

</code_context>

<specifics>
## Specific Ideas

No new visual references — this phase has no UI surface changes at all (the button, its label, and its click behavior are unchanged; only the downloaded file's content grows a sheet).

</specifics>

<deferred>
## Deferred Ideas

- Native Excel chart embedding on the Forecast sheet — deferred per FEATURES.md, a differentiator not required for EXPORT-02.

### Reviewed Todos (not folded)
None — discussion stayed within phase scope.

</deferred>

---

*Phase: 9-excel-export-polish*
*Context gathered: 2026-08-24*
