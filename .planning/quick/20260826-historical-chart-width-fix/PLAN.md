---
slug: historical-chart-width-fix
created: 2026-08-26
---

Fix the Data Entry tab's "Historical" chart rendering at ~125-175px width
instead of full width, with cramped/rotated axis labels.

## Root cause

`historical_section()` in `app/app/app.py` wraps `historical_chart()` in
an `rx.vstack(...)` with no `width="100%"` prop, unlike every sibling
wrapper (`forecast_section()`, `_data_entry_tab()`). Radix's `rx.vstack`
defaults `align-items` to `flex-start` (not `stretch`), so this one
un-widthed vstack shrinks to fit its content instead of filling the 880px
available from its parent. This creates a circular sizing collapse with
`historical_chart()`'s inner `rx.plotly(width="100%")`, landing at
~125-175px. Confirmed via live DOM inspection (`getBoundingClientRect`
chain comparison against the working Forecast-tab chart).

## Fix

Add `width="100%"` to `historical_section()`'s `rx.vstack(...)` call.

## Verification

- Start the dev server, confirm the Historical chart on Data Entry
  renders full-width with horizontal (not rotated) date labels, matching
  the Forecast tab's chart.
- Full test suite passes.
