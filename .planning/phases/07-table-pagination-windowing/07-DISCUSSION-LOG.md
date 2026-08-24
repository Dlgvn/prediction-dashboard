# Phase 7: Table Pagination / Windowing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-24
**Phase:** 07-table-pagination-windowing
**Areas discussed:** Default window size, Toggle interaction with edit/delete state

---

## Default window size

| Option | Description | Selected |
|--------|-------------|----------|
| Last 12 months | Matches monthly-entry workflow, ~200 cells instead of ~2,950 | ✓ |
| Last 24 months | Two years visible by default | |

**User's choice:** Last 12 months.

---

## Toggle interaction with edit/delete state

| Option | Description | Selected |
|--------|-------------|----------|
| Cancel in-progress edit/delete on toggle | Resets editing_key/pending_delete on any toggle, simplest and safest | ✓ |
| Preserve if row still visible after toggling | More seamless, more edge cases | |

**User's choice:** Cancel in-progress edit/delete on toggle.

---

## Claude's Discretion

- Toggle control placement, label wording, visual styling (per existing 06-UI-SPEC.md design tokens).
- Whether draft_rows (new unsaved rows) stay always-visible regardless of window.
- Empty-state copy when the windowed view has zero rows.

## Deferred Ideas

- SQL-level/server-side pagination — deferred until data scale grows into the thousands of rows.
- Column-level filtering/search within the table — not requested.
