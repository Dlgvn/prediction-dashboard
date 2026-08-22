# Phase 5: Forecast UI, Scenario Chart & Excel Export - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-22
**Phase:** 5-Forecast UI, Scenario Chart & Excel Export
**Areas discussed:** Horizon selector UI, Multi-series forecast layout (VIS-03), Confidence band rendering (VIS-02), Page layout & freshness indicator placement

---

## Horizon selector UI

| Option | Description | Selected |
|--------|-------------|----------|
| Slider | Visually communicates range, exploratory feel | ✓ |
| Dropdown/select (1-12) | Consistent with Phase 4's Series dropdown | |
| Number input with steppers | Precise, keyboard-friendly | |

**User's choice:** Slider

| Option | Description | Selected |
|--------|-------------|----------|
| Live, on every change | Instant feedback, models refit in milliseconds | ✓ |
| On explicit "Forecast" button | More deliberate | |

**User's choice:** Live, on every change

---

## Multi-series forecast layout (VIS-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Grid of 4 small charts | Genuinely all-at-a-glance | |
| One chart with a series selector, like Phase 4 | Consistent pattern, but conflicts with VIS-03 wording | ✓ (initial) |

**User's choice (initial):** One chart with a series selector

**Follow-up:** Flagged the conflict with VIS-03's literal wording ("all four visible together... not requiring the user to switch").

| Option | Description | Selected |
|--------|-------------|----------|
| Selector chart + combined forecast table shows all 4 | Satisfies VIS-03's spirit via the table | ✓ |
| Revise VIS-03 wording formally | Scope change outside Phase 5 discussion | |
| Switch to grid-of-4 instead | Keep VIS-03 literal | |

**User's choice:** Selector chart + combined forecast table shows all 4

---

## Confidence band rendering (VIS-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Filled area between bull/bear + solid base line on top | Standard fan-chart pattern | ✓ |
| Filled area only, no base line | Simpler, loses explicit point-forecast number | |

**User's choice:** Filled area + base line

| Option | Description | Selected |
|--------|-------------|----------|
| Include recent historical actuals leading into the band | Visual continuity/context | ✓ |
| Forecast-only | Simpler, relies on Phase 4's separate historical chart | |

**User's choice:** Include recent historical actuals

**Follow-up:** How many months of history?

| Option | Description | Selected |
|--------|-------------|----------|
| 12 months | Balanced, roughly matches max horizon | ✓ |
| 24 months | More context, busier chart | |
| 6 months | Minimal context | |

**User's choice:** 12 months

---

## Page layout & freshness indicator placement

| Option | Description | Selected |
|--------|-------------|----------|
| Append below Phase 4's content, in build order | Natural top-to-bottom narrative, no restructuring | ✓ |
| Reorganize into sections/tabs | Cleaner separation, requires restructuring | |

**User's choice:** Append below, in build order

| Option | Description | Selected |
|--------|-------------|----------|
| Small label above forecast section, one per series | Visible right where user trusts the forecast | ✓ |
| Inline in existing data table header | Near raw data, less visible when viewing forecast | |

**User's choice:** Small label above forecast section

## Claude's Discretion

None — all presented gray areas were explicitly decided by the user, with follow-up rounds resolving the VIS-03 wording tension and the historical-context window size.

## Deferred Ideas

None — discussion stayed within Phase 5's boundary.
