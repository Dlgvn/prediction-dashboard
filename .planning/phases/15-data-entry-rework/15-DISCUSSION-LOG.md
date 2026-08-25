# Phase 15: Data Entry Rework - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-25
**Phase:** 15-data-entry-rework
**Areas discussed:** Date picker scope, error prominence, CSV import scope

---

## Date picker scope

| Option | Description | Selected |
|--------|-------------|----------|
| Both new-row and edit-in-place | Native rx.input(type="date") replaces every date cell, draft and existing rows | ✓ |
| New-row only | Only the "add row" draft date field gets the picker; editing an existing row's date stays free-text | |

**User's choice:** Both — fully eliminates the free-text date bug class everywhere it can occur.

---

## Error prominence

| Option | Description | Selected |
|--------|-------------|----------|
| Keep inline red text, just fix the race | Reuse existing small red text under the cell; fix start_edit's edit_error clobber | ✓ |
| Stronger treatment (banner/toast) | Elevate validation errors to a page-level banner/toast | |

**User's choice:** Keep inline red text — matches current visual language, smaller change.

---

## CSV import scope

| Option | Description | Selected |
|--------|-------------|----------|
| Audit only, fix if trivial | Check csv_import.py's date-error path for the same race class; fix if small, else defer | ✓ |
| Out of scope — defer entirely | Leave CSV import's date handling untouched regardless of findings | |

**User's choice:** Audit only, fix if trivial.

---

## Claude's Discretion

- Exact rx.input(type="date") value-binding approach — confirm against installed Reflex 0.9.8 API before implementing.
- Exact mechanism for fixing start_edit's error-reset race (guard vs. restructure) — write the full state-transition table first (PITFALLS.md requirement).
- Whether the native date input needs an explicit min/max range — default to none unless a clear reason emerges.

## Deferred Ideas

- CSV import date-validation UX redesign, if the D-03 audit finds it needs more than a trivial fix — deferred to a future phase.
