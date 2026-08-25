# Phase 12: Fan Chart Legend/Axis Fix - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-24
**Phase:** 12-fan-chart-legend-axis-fix
**Areas discussed:** Legend position, chart scope

---

## Legend position

| Option | Description | Selected |
|--------|-------------|----------|
| Horizontal legend below the plot area | Moves legend fully out of the collision zone | ✓ |
| Legend top-left/top-right outside the plot | Stays near the chart, anchored outside axis area | |

**User's choice:** Horizontal legend below the plot.

---

## Chart scope

| Option | Description | Selected |
|--------|-------------|----------|
| Both charts, for consistency | Apply same layout treatment to historical + forecast charts | ✓ |
| Only the fan chart | Scope strictly to the reported bug | |

**User's choice:** Both charts.

---

## Claude's Discretion

- Exact y/margin pixel values for the legend.
- Whether the "Forecast start" vline annotation needs repositioning now that the legend moved.

## Deferred Ideas

None — phase scope is narrow.
