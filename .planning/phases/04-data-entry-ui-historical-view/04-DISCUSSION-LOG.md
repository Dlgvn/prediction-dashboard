# Phase 4: Data Entry UI & Historical View - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-22
**Phase:** 4-Data Entry UI & Historical View
**Areas discussed:** Validation rules per field, Historical chart scope (VIS-01), Inline editing UX, Delete confirmation UX

---

## Validation rules per field

| Option | Description | Selected |
|--------|-------------|----------|
| Non-negative only, uniform across all 16 columns | Simple, catches obvious mistakes | ✓ |
| Tighter, series-specific plausible ranges | Catches more errors, needs domain-knowledge bounds | |

**User's choice:** Non-negative only, uniform across all 16 columns

| Option | Description | Selected |
|--------|-------------|----------|
| Valid date + no duplicate month | Matches Phase 1's unique-date schema constraint | ✓ |
| Just "is it a valid date", allow duplicates to upsert | More forgiving, less transparent | |

**User's choice:** Valid date + no duplicate month

---

## Historical chart scope (VIS-01)

| Option | Description | Selected |
|--------|-------------|----------|
| 4 headline series only | Matches Core Value, what's actually forecasted | |
| All 16 columns | Full parity with Phase 1's table | ✓ |

**User's choice:** All 16 columns

**Follow-up:** 16 series have wildly different scales — layout clarification needed.

| Option | Description | Selected |
|--------|-------------|----------|
| Grid of 16 small individual charts | Avoids scale-mismatch, all-at-a-glance | |
| One chart with a series selector/toggle | More interactive, one series at a time | ✓ |

**User's choice:** One chart with a series selector/toggle

---

## Inline editing UX

| Option | Description | Selected |
|--------|-------------|----------|
| Click-to-edit per cell | Spreadsheet feel | ✓ |
| Explicit edit-mode toggle per row | More deliberate, more clicks | |

**User's choice:** Click-to-edit per cell

**Follow-up:** Add-row UX given click-to-edit cells.

| Option | Description | Selected |
|--------|-------------|----------|
| "Add row" button appends a blank editable row | Consistent with click-to-edit | ✓ |
| Separate add-row form | Distinct UI from editing | |

**User's choice:** "Add row" button appends a blank editable row

---

## Delete confirmation UX

| Option | Description | Selected |
|--------|-------------|----------|
| Click delete again to confirm | No modal, stays in flow | ✓ |
| Modal confirmation dialog | Standard pattern, heavier UX | |

**User's choice:** Click delete again to confirm

## Claude's Discretion

None — all presented gray areas were explicitly decided by the user, with follow-up rounds on chart layout and add-row UX.

## Deferred Ideas

None — discussion stayed within Phase 4's boundary.
