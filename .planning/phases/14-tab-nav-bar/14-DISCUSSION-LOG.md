# Phase 14: Tab/Nav Bar - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-24
**Phase:** 14-tab-nav-bar
**Areas discussed:** Tab mapping, tab UI/behavior, default tab

---

## Tab mapping

| Option | Description | Selected |
|--------|-------------|----------|
| Data Entry tab = Historical chart + Data Entry table | 3 tabs total, groups raw-actuals concerns together | ✓ |
| 4 tabs, one per existing section | Keeps 1:1 mapping, adds a 4th tab beyond phase goal | |

**User's choice:** 3 tabs, Data Entry merges historical + entry.

---

## Tab UI / behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Sticky tab bar below header, scroll-to-top on switch | Real tabbed-app behavior, conditional render | ✓ |
| Anchor-style nav, all content stays mounted | Simpler, less tab-like, no clutter reduction | |

**User's choice:** Sticky tab bar with conditional rendering.

---

## Default tab

| Option | Description | Selected |
|--------|-------------|----------|
| Summary | Matches "10-20 second answer" design goal | ✓ |
| Forecast | Shows chart/table first | |

**User's choice:** Summary.

---

## Claude's Discretion

- Exact tab component (rx.tabs vs custom hstack+cond).
- Exact tab label text.
- Whether active_section persists across reloads (default: no, always resets to Summary).

## Deferred Ideas

None — phase scope fully covered.
