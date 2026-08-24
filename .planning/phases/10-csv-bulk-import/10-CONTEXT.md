# Phase 10: CSV Bulk Import — Context

**Gathered:** 2026-08-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Let the user bulk-import historical price rows via CSV upload, as a faster alternative to entering rows one at a time in the Data Entry table. Fixed schema only (matching the app's own export format), no column mapping, no fuzzy header matching. A preview-and-confirm step runs before any row is written to storage, and rows whose date already exists are skipped, never overwritten.

In scope: CSV upload control, parsing, per-row validation reusing existing validators, a summary-style preview, a confirm step that batch-writes only valid+new rows, and an import-result summary (added vs. skipped counts with reasons).
Out of scope (per REQUIREMENTS.md Out of Scope, already decided): column-mapping UI, fuzzy header matching, overwrite-on-duplicate-date semantics.
</domain>

<decisions>
## Implementation Decisions

### CSV schema
- **D-01:** Expected CSV columns are exactly `date` + the 16 `SERIES_ATTRS` columns, matching the app's own Excel export "Actuals" sheet format byte-for-byte in column order/naming. This enables the natural round-trip: export → edit in Excel → save as CSV → re-import.

### Invalid row handling
- **D-02:** Rows that fail validation (per the existing `validate_numeric`/`validate_date` rules) are SKIPPED, not rejected wholesale — the import proceeds with valid rows only. The preview/result summary reports skip reasons per row (or per reason-category count).

### Duplicate date handling (already locked at milestone-discussion time)
- **D-03:** CSV rows whose date already exists in storage are skipped — existing data is never overwritten by import (IMPORT-02, confirmed again here). This is naturally implemented by reusing `validate_date`'s existing duplicate-month rejection (`DATE_DUPLICATE_ERROR`), which already treats "duplicate month" as a validation failure — no new duplicate-detection logic needed, just correct labeling in the summary (distinguish "duplicate" skip reason from "invalid value" skip reason for clearer user-facing counts).

### Preview UI
- **D-04:** Preview is summary-style, not a full row-by-row grid: counts of "N rows will be added" / "M rows skipped (duplicate date)" / "K rows skipped (invalid value)", not a rendered table of every parsed row. Matches the "Data Quality" summary pattern from the broader UX audit brief without requiring a new paginated-table component.

### Placement
- **D-05:** The CSV import control (upload button/dropzone) sits next to the existing "Add row" button in the Data Entry section — bulk import is a Data Entry concern, not a separate page section.

### Malformed file handling
- **D-06:** If the uploaded file's headers don't match the expected `date` + 16-`SERIES_ATTRS` schema, or the file isn't parseable as CSV at all, reject with a clear error message before attempting any row-level parsing or preview. No partial parsing of a fundamentally wrong file.

### Claude's Discretion
- Exact upload control UI (drag-and-drop zone vs. a simple file-picker button) — use Reflex's `rx.upload` component per the STACK.md research recommendation; styling follows existing `theme.py` tokens.
- File size / row count cap — pick a reasonable limit (research flagged this as unresolved; a sensible default like a few thousand rows / a few MB is more than sufficient at this app's realistic data scale).
- Exact wording of the summary/result messages and the two-step "preview → confirm" interaction (e.g. does confirm require a second explicit click, or does the preview appear and auto-commit on a subsequent "Import" click) — follow the existing two-click delete-confirm precedent's spirit (an explicit confirm step, not a silent auto-commit) without necessarily copying its exact mechanic.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing code (primary implementation surface)
- `app/app/validators.py` — `validate_numeric`, `validate_date` (with `DATE_DUPLICATE_ERROR`, `DATE_INVALID_ERROR`, `NUMERIC_ERROR`) — MUST be reused for CSV row validation, not reimplemented (per PITFALLS.md's explicit warning about NOT reusing these being the biggest CSV-import risk)
- `app/app/state.py` — `SERIES_ATTRS` (16 column names), `add_row`/`commit_edit`/`commit_draft_row` (the existing single-row write patterns to follow for the batch write), `load_rows` (reload-after-write pattern), `rx.session()` usage (the app's sole DB-access boundary — CSV import writes must also go through `DashboardState`, no new session call site outside it)
- `app/app/app.py` — `add_row_button()`, `data_entry_section()` — where the new upload control is inserted per D-05
- `app/app/models.py` — `PriceRow` schema

### v1.2 milestone research (MANDATORY)
- `.planning/research/STACK.md` — confirms `rx.upload` + `rx.upload_files(upload_id=...)` is the Reflex-idiomatic pattern; async backend handler receiving `files: list[UploadFile]`; parse with `pandas.read_csv(io.BytesIO(await file.read()))`; explicitly rejected hosted CSV-import SaaS (CSVBox) as overkill for a single local user
- `.planning/research/PITFALLS.md` — CSV import's biggest risk is NOT reusing `validate_numeric`/`validate_date`, and reusing the wrong error-reporting shape (`edit_error` is a single scalar by design, useless for a multi-row import — a new state shape is needed for the import summary, not a repurposed `edit_error`)
- `.planning/research/FEATURES.md` — confirms fixed-schema CSV import (no column mapping) is correctly scoped for this single-user app; explicitly rejects enterprise SaaS import patterns (fuzzy AI mapping, resumable wizards) as anti-features here
- `.planning/research/ARCHITECTURE.md` — flags CSV import as "highest complexity, needs its own phase, sequence last" — this phase depends on Phase 7 (windowing patterns, since a bulk import could push row count well past the visible window) and Phase 9 (export format, since D-01 mirrors it)

### Project-level
- `.planning/REQUIREMENTS.md` — IMPORT-01, IMPORT-02, and the Out of Scope section's explicit CSV-related exclusions (no column mapping, no overwrite-on-duplicate)
- `.planning/ROADMAP.md` — Phase 10 entry (depends on Phase 7 AND Phase 9, both now complete)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `validate_numeric`/`validate_date` — pure, dependency-free functions already unit-tested; CSV row validation should call these per-cell/per-row exactly as the manual edit path does, not write parallel validation logic.
- `SERIES_ATTRS` tuple — single source of truth for the 16 column names; CSV header validation (D-06) should check the uploaded file's header row against this exact tuple (plus `"date"`).

### Established Patterns
- All DB writes go through `rx.session()` calls that live exclusively in `state.py` — the CSV import's batch-write handler must follow this same boundary discipline, no new session call site elsewhere.
- `load_rows()` is called after any DB mutation to refresh `self.rows` — the import confirm handler must call this too so the newly-imported rows appear immediately (and are reflected in Phase 7's `visible_rows` window, Phase 8's `summary_cards`/high-low/YoY, and Phase 9's export, all of which read `self.rows`).
- Two-click confirm precedent exists for delete (`pending_delete` armed state) — a similar "preview state, then explicit confirm" shape is appropriate for import, per D-04's Claude's Discretion note, though the exact mechanic doesn't need to be identical.

### Integration Points
- New upload control lives in `data_entry_section()`, next to `add_row_button()` (D-05).
- New state needed: an uploaded-file-parse-result holding area (counts + skip reasons) distinct from `edit_error`, per PITFALLS.md's explicit warning against reusing that scalar field.
- Batch write should reuse the same validate-then-write flow as `commit_draft_row`, but iterated over parsed CSV rows rather than a single draft.

</code_context>

<specifics>
## Specific Ideas

No new visual references — reuses the Phase 6 design system throughout (light theme, existing button styling, muted-text summary copy pattern already established for freshness chips / summary card captions).

</specifics>

<deferred>
## Deferred Ideas

- Column-mapping UI / fuzzy header matching — explicitly out of scope per REQUIREMENTS.md (enterprise SaaS pattern, disproportionate for this app).
- Overwrite-on-duplicate-date import mode — explicitly out of scope per REQUIREMENTS.md; skip-only behavior is final for v1.2.
- Full row-by-row preview grid — deferred in favor of the summary-count preview (D-04); could be revisited in a future milestone if users report needing to inspect individual skipped rows before confirming.

### Reviewed Todos (not folded)
None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-csv-bulk-import*
*Context gathered: 2026-08-24*
