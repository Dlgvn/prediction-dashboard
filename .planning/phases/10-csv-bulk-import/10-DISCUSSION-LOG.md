# Phase 10: CSV Bulk Import - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-24
**Phase:** 10-csv-bulk-import
**Areas discussed:** CSV schema, invalid row handling, preview UI, import placement, malformed file handling

---

## CSV schema

| Option | Description | Selected |
|--------|-------------|----------|
| Match the app's own Excel export format exactly | date + 16 SERIES_ATTRS, natural export/edit/re-import round-trip | ✓ |
| A simpler/different fixed format | Alternative column set | |

**User's choice:** Match the export format exactly.

---

## Invalid row handling

| Option | Description | Selected |
|--------|-------------|----------|
| Skip invalid rows, import the valid ones | Preview shows valid vs. invalid with reasons | ✓ |
| Reject the whole file if any row is invalid | Simpler, stricter | |

**User's choice:** Skip invalid rows.

---

## Preview scope

| Option | Description | Selected |
|--------|-------------|----------|
| Summary counts + list of skipped rows with reasons | Concise, matches Data Quality summary pattern | ✓ |
| Full row-by-row table preview | More thorough, more UI | |

**User's choice:** Summary counts.

---

## Import placement

| Option | Description | Selected |
|--------|-------------|----------|
| Next to "Add row" in Data Entry section | Bulk import is a Data Entry concern | ✓ |
| New standalone section | Separate from manual table | |

**User's choice:** Next to Add row.

---

## Malformed file handling

Only one sensible option was presented (not a forced-choice question): reject with a clear error before any preview, no partial parsing attempt. Locked as D-06 without a formal AskUserQuestion (single viable path).

---

## Claude's Discretion

- Upload control UI style (rx.upload dropzone vs. file picker).
- File size / row count cap.
- Exact preview→confirm interaction mechanic and message wording.

## Deferred Ideas

- Column-mapping UI, fuzzy header matching — out of scope per REQUIREMENTS.md.
- Overwrite-on-duplicate-date — out of scope, skip-only is final.
- Full row-by-row preview grid — deferred in favor of summary counts.
