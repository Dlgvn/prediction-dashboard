# Phase 8: Forecast Context Enrichment - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-24
**Phase:** 08-forecast-context-enrichment
**Areas discussed:** Historical high/low window, YoY basis, card layout

---

## Historical high/low window

| Option | Description | Selected |
|--------|-------------|----------|
| All-time (full history) | Highest/lowest ever recorded | ✓ |
| Trailing 5 years | Excludes stale pre-2020 outliers | |

**User's choice:** All-time (full history).

---

## YoY basis

| Option | Description | Selected |
|--------|-------------|----------|
| Latest actual vs. same month one year ago | Standard YoY definition | ✓ |
| Latest actual vs. exactly 12 rows back | May not match calendar month with data gaps | |

**User's choice:** Same month, one year ago.

---

## Card layout

| Option | Description | Selected |
|--------|-------------|----------|
| Add two more compact lines below existing content | Keep card growing vertically, all existing content preserved | ✓ |
| Replace vs.-latest-actual direction with YoY | Swap out existing indicator | |

**User's choice:** Add two more lines, don't replace anything.

---

## Claude's Discretion

- Exact copy wording for the two new lines (distinct from "Expected range" to avoid ambiguity with the forecast band).
- Whether high/low renders as one combined line or two separate lines.
- diesel_mnt derivation must reuse a shared helper, not add a 3rd/4th duplicate of the formula (per PITFALLS.md).

## Deferred Ideas

- "Drivers"/attribution text — out of scope per REQUIREMENTS.md.
