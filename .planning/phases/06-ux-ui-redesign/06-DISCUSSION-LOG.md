# Phase 6: UX/UI Redesign - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-23
**Phase:** 06-ux-ui-redesign
**Areas discussed:** Page structure & hierarchy, Visual/color system, Chart redesign, Forecast summary cards

---

## Page structure & hierarchy

| Option | Description | Selected |
|--------|-------------|----------|
| Summary cards first, above everything | Header → summary cards → fan chart → forecast table → historical chart → data entry at bottom | ✓ |
| Summary cards inside existing Forecast section | Keep data entry/historical chart at top; only restyle Forecast section in place | |

**User's choice:** Summary cards first, above everything.
**Notes:** Follow-up questions confirmed: all 4 series shown as cards simultaneously (not one-at-a-time selector), and the data-entry table moves to the bottom of the page.

| Sub-question | Option | Selected |
|--------------|--------|----------|
| Summary scope | All 4 series as cards side-by-side | ✓ |
| Summary scope | One series at a time via selector | |
| Data entry position | Move to the bottom | ✓ |
| Data entry position | Keep near the top | |

---

## Visual/color system

| Option | Description | Selected |
|--------|-------------|----------|
| Light neutral, one accent color | Off-white/gray bg, dark text, one accent, red/green deltas only | ✓ |
| Dark navy header + light body | Financial-terminal navy top bar, light card body below | |
| Full dark mode as default | Dark bg throughout, light text | |

**User's choice:** Light neutral, one accent color.

| Sub-question | Option | Selected |
|--------------|--------|----------|
| Theme toggle | One fixed theme for now | ✓ |
| Theme toggle | Add a light/dark toggle | |

---

## Chart redesign

| Option | Description | Selected |
|--------|-------------|----------|
| Restyle in place | Keep existing Plotly figure/data flow, improve colors/legend/hover/marker | ✓ |
| Restructure data flow | Bigger change to how historical vs. forecast traces are built | |

**User's choice:** Restyle in place.

---

## Forecast summary cards

| Sub-question | Option | Selected |
|--------------|--------|----------|
| Direction basis | Base forecast vs. latest actual price | ✓ |
| Direction basis | Horizon-end vs. horizon-start forecast | |
| Card horizon | End of selected horizon | ✓ |
| Card horizon | Always next month | |

**User's choice:** Base forecast vs. latest actual for direction; cards reflect end of the currently selected horizon.

---

## Claude's Discretion

- Exact spacing/typography scale, card border-radius/shadow, accent hex value, number formatting precision, empty/error/loading copy wording, responsive breakpoints, accessibility contrast tuning.
- Whether summary cards are implemented as a new reusable component function or inline in `index()`.

## Deferred Ideas

- Light/dark theme toggle — deferred, no toggle built in this phase.
- Scalable N-commodity selector — not applicable (fixed 4-series app); noted for a hypothetical future milestone only.
- File upload / upload-data-quality UX — out of scope per PROJECT.md (manual in-app entry only, no file upload in v1).
