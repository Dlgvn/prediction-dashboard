# Phase 1: App Skeleton & Data Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-21
**Phase:** 1-App Skeleton & Data Layer
**Areas discussed:** Schema shape, Seed merge strategy, Skeleton UI scope

---

## Schema shape

| Option | Description | Selected |
|--------|-------------|----------|
| Wide table, one row per month | One row per calendar month, column per series — matches Excel Input tab | ✓ |
| Normalized/tidy table | One row per (date, series_name, value) | |

**User's choice:** Wide table, one row per month
**Notes:** Matches statsmodels' need for aligned time-indexed series.

| Option | Description | Selected |
|--------|-------------|----------|
| Single global markup setting | One editable value, like Excel's `Markup_%` cell | ✓ |
| Per-row markup value | Stored per month, allows historical variation | |

**User's choice:** Single global setting

| Option | Description | Selected |
|--------|-------------|----------|
| Unique date constraint + nullable fields | Date unique, upsert on conflict, any column nullable | ✓ |
| No uniqueness constraint | Simpler but risks duplicate months | |

**User's choice:** Unique date constraint + nullable fields

---

## Seed merge strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Keep full history, blank AN columns before 2022-08 | Rows from 2020-02 onward; AN columns NULL until real data starts | ✓ |
| Trim to shortest common range | Only seed rows where all series have data | |

**User's choice:** Keep full history, blank AN columns before 2022-08

| Option | Description | Selected |
|--------|-------------|----------|
| Take last entry of each month | Matches earlier implementation plan's `.last()` approach | |
| Average all entries within the month | Smooths intra-month volatility | ✓ |

**User's choice:** Average all entries within the month
**Notes:** Overrides the `.last()` approach sketched in the earlier (pre-GSD) implementation plan.

**Follow-up:** User asked to also check `AN price weekly.csv` in this context.

| Option | Description | Selected |
|--------|-------------|----------|
| Leave it for Phase 2 research | Doesn't map onto monthly schema; relevant to weekly-mode/proxy question | ✓ |
| Seed it now into a separate weekly table | Gets raw data into SQLite early for Phase 2 | |

**User's choice:** Leave it for Phase 2 research

---

## Skeleton UI scope

| Option | Description | Selected |
|--------|-------------|----------|
| Read-only table of seeded data | Makes seed success visibly verifiable in the running app | ✓ |
| Bare placeholder page | Just confirms the app runs | |

**User's choice:** Read-only table of seeded data

---

## Claude's Discretion

User selected "no preference" on a follow-up round covering:
- Column naming/mapping — decided: snake_case matching the design doc's `PriceRow` model
- Python environment setup — decided: virtualenv in `app/`, loose-but-sane version ranges
- Seed script re-run behavior — decided: upsert on date conflict

## Deferred Ideas

None — discussion stayed within Phase 1's boundary.
