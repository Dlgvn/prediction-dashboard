---
slug: historical-chart-width-fix
status: complete
completed: 2026-08-26
---

Fixed: added `width="100%"` to `historical_section()`'s `rx.vstack(...)`
in `app/app/app.py`, matching the pattern already used by
`forecast_section()` and `_data_entry_tab()`.

Verified: full test suite green (365 passed, 0 failed); confirmed live
in browser that the Data Entry tab's Historical chart now renders
full-width with horizontal date-axis labels, matching the Forecast tab.
