# Phase 9: Excel Export Polish - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-24
**Phase:** 09-excel-export-polish
**Areas discussed:** Export horizon scope, sheet layout, sheet naming

---

## Export horizon scope

| Option | Description | Selected |
|--------|-------------|----------|
| Currently selected horizon | Matches exactly what's on screen at export time | ✓ |
| Always full 1-12 months | Complete reference regardless of slider | |

**User's choice:** Currently selected horizon.

---

## Sheet layout

| Option | Description | Selected |
|--------|-------------|----------|
| Mirror the on-screen table exactly | Same columns/rows as the rendered forecast table | ✓ |
| Different layout (one sheet per series) | More sheets, more complexity | |

**User's choice:** Mirror the on-screen table.

---

## Sheet naming

| Option | Description | Selected |
|--------|-------------|----------|
| "Actuals" and "Forecast" | Clear, matches app terminology | ✓ |
| Keep actuals name as-is, only name the new sheet | Avoid touching existing sheet | |

**User's choice:** "Actuals" and "Forecast".

---

## Claude's Discretion

- Column header wording (reuse FORECAST_TABLE_COLUMNS labels).
- Number formatting in Excel cells (match existing Actuals sheet style).
- Filename unchanged.
- Empty-forecast edge case: header-only sheet.

## Deferred Ideas

- Native Excel chart embedding — deferred per FEATURES.md research.
