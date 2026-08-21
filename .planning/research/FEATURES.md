# Feature Research

**Domain:** Single-user commodity/FX price forecasting dashboard (procurement/budgeting tool)
**Researched:** 2026-08-21
**Confidence:** MEDIUM (grounded in project docs + general dashboard/data-table UX literature; no direct competitor product had this exact combination of scenario forecasting + manual entry + single-user scope, so feature landscape is synthesized from adjacent categories: commodity forecast platforms, budgeting tools, procurement dashboards, and data-grid UX patterns)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist in any small-scale forecasting/tracking dashboard. Missing these makes the tool feel broken or less useful than the Excel workbook it's replacing.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| View current/latest values at a glance | Any tracker's first job — "what's the price now" | LOW | Summary cards/header row above the chart, one per series (HDAN, PPAN, Diesel-MNT, FX) |
| Historical price chart (actuals only, no forecast) | Users expect to see the trend that produced the forecast, not just the forecast | LOW | Reuses same chart component as forecast view; table stakes for trusting the model |
| Add a new data row (manual entry) | Direct replacement for "add a row to Input tab in Excel" — this is the core workflow being ported | MEDIUM | Form or inline-add row; must validate types (dates, numeric prices) before insert |
| Edit an existing row | Corrections happen (data entry mistakes, revised actuals) — a tracker that can't fix a typo without DB surgery is unusable | MEDIUM | Inline edit is expected UX (see Differentiators) but even a modal edit-form satisfies table stakes |
| Delete/void a row | Bad entries need removal, not just correction | LOW | Soft-delete not required for v1; hard delete with a confirm step is sufficient |
| Data persists across sessions | Table stakes for literally any tool beyond a demo | LOW | Already scoped: SQLite via `rx.Model` |
| Export data to Excel | Explicit requirement — user's workflow depends on Excel elsewhere (sharing, workbook cross-check) | LOW-MEDIUM | openpyxl; straightforward given tabular SQLite data |
| Forecast horizon selector | The one differentiator vs. the Excel workbook (which only did next-month) is *worthless* without a way to control it — this is the mechanism, not the feature | LOW | Slider or dropdown 1–12 (months); simple UI, but forecast recompute logic behind it is the real cost |
| Per-product forecast values in a table (numbers, not just chart) | Procurement/budgeting users need to copy a number into a purchase order or budget line — a chart alone doesn't answer "what do I write down" | LOW | Table below/beside chart showing base/bull/bear values per horizon month |
| Basic input validation on entry | Prevents a single bad row from corrupting a VAR/AR model silently | MEDIUM | Type checks, plausible-range checks (e.g., FX rate isn't negative); doesn't need to be sophisticated |
| Loading/empty states | Any real dashboard needs to not look broken with zero data or during forecast compute | LOW | Especially relevant on first run before seed data is loaded |

### Differentiators (Competitive Advantage)

Not required for the tool to be usable, but this is where the project earns its "better than the Excel workbook" claim. Should map to the Core Value in PROJECT.md: adjustable horizon + bull/base/bear scenarios + in-app entry, all without opening Excel.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Adjustable multi-month horizon (1–12) with live recompute | The single named differentiator over the Excel workbook, which only forecasts one month ahead | MEDIUM | Already scoped. Cost is mostly in the forecasting backend (must support N-step-ahead forecasting, not just 1-step), not the UI control itself |
| Bull/base/bear scenario visualization as 3 lines/bands on one chart | Turns a single point forecast into a decision-support view — user sees range of "what I might pay," not false precision | MEDIUM | v1 = base ± statistical spread (backtest error/volatility), computed dynamically. Rendering as a shaded band (not 3 flat lines) is a further UX upgrade — see below |
| Confidence band styling (shaded area) vs. 3 discrete lines | Industry-standard forecast dashboards (commodity outlook platforms, e.g. Citigroup/CRU-style) use shaded probability bands rather than 3 crisp lines, because it visually communicates "this is a range, not 3 discrete predicted paths" | LOW-MEDIUM | Recharts/similar in Reflex supports area+line composition; this is a rendering choice on top of the same base±spread data, low incremental cost once scenario math exists |
| Inline (in-row) editing of the data table, not modal-per-field | Reduces friction vs. Excel's own inline-cell editing, which is the workflow being replaced — if editing requires a multi-click modal, it's a downgrade from Excel, not an upgrade | MEDIUM | Reflex has a Data Table Editor template pattern (searchable/editable grid) that fits this directly |
| Derived series shown automatically (Diesel-MNT from Diesel-USD × FX × markup) | User doesn't have to compute the derived value themselves — a small but real time-save vs. Excel formulas | LOW | Already a validated requirement; purely a display/compute feature once the two source forecasts exist |
| Multi-series dashboard in one view (HDAN, PPAN, Diesel-MNT, FX side by side) | Excel workbook is tab-based (Input/PctChange/Regression/Forecast/Dashboard) — a single-page view of all 4 series' forecasts is a genuine UX improvement over tab-switching | MEDIUM | Grid of 4 small charts, or a per-series toggle on one chart; layout decision, not a data decision |
| "As of" / last-updated indicator per series | Useful for a monthly-cadence, occasional-use tool — user needs to know if data is stale before trusting a forecast | LOW | Simple metadata display; cheap to add, meaningfully increases trust |

### Anti-Features (Commonly Requested, Often Problematic)

Features that sound good for a forecasting dashboard but would add disproportionate complexity or actively work against this project's single-user, occasional-use, "companion not replacement" positioning. These are already explicitly out of scope in PROJECT.md; documented here with the *why*, not just the *what*.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| File upload / bulk CSV import UI | Feels efficient for "catching up" months of missed data at once | Adds file-parsing, schema-validation, and error-recovery UX for a workflow that happens rarely (single monthly entry) — high build cost for a low-frequency action; also masks bad data behind a black-box import rather than a reviewable row-by-row entry | Manual in-app entry (already scoped); revisit only if data-API integration becomes real, at which point the ingestion path is different anyway (API, not CSV) |
| Live news/sentiment-driven scenario adjustment | Sounds like it would make bull/bear "smarter" and more current | Requires picking and maintaining a news/LLM provider, handling Mongolia/MNT-specific coverage gaps, and risks producing scenario swings that aren't backed by the same backtested rigor as the statistical model — undermines trust in the tool for a single procurement user who needs a stable, explainable number | v1 ships with base ± statistical spread only (backtest error/volatility); treat sentiment as a v2 research question, not a v1 feature |
| Multi-user accounts / auth / roles | Standard SaaS-dashboard assumption, easy to over-apply by default | Single local user matches the Excel workbook's actual usage pattern — auth adds real complexity (sessions, access control) with zero value for one person on one machine | None needed; if sharing is required later, Excel export already covers that use case |
| Automatic API data-fetch from external price sources | Removes manual entry step, feels "modern" | Requires selecting/paying for/maintaining a market-data provider, handling API downtime, and building trust that fetched data matches the user's actual purchasing reality (which is negotiated, not always market-rate) — real scope and cost for a monthly-cadence, single-user tool | Manual entry stays authoritative; flagged as a distinct future milestone if it's ever pursued, not bolted onto v1 |
| Fully general chart with pan/zoom/tooltips/drill-down toolbox | "Nice, polished dashboards have rich interactive charts" | Over-engineering for 4 series and 12 data points at most (12-month horizon) — a full charting toolbox (zoom, brush, export-as-image, per-point tooltips with drill-down) is disproportionate effort for a chart a single user glances at monthly | Simple line/area chart with basic hover tooltip; skip zoom/brush/drill-down unless a real need surfaces |
| Real-time/streaming price updates | "Dashboard" often implies live-updating data | This is a monthly-cadence, manually-entered dataset — there is no live feed to stream from, and building any polling/websocket infrastructure for data that changes once a month is pure waste | Static page, refreshed on user action (data entry, horizon change) — no push/streaming needed |
| Configurable/pluggable model selection in the UI (user picks ARIMA vs VAR vs ML from a dropdown) | Feels powerful and "researcher-friendly" | Model selection is explicitly a backend research/backtest decision (per PROJECT.md), not a per-session user toggle — exposing it in the UI implies the user should evaluate model quality, which isn't the target user's job or expertise | Model selection happens once, offline, during the research phase; UI only exposes the horizon and scenario outputs, not model internals |

## Feature Dependencies

```
Manual data entry (add/edit row)
    └──requires──> Input validation
                       └──enhances──> Model reliability (bad rows corrupt VAR/AR fits)

Forecast horizon selector (1-12 months)
    └──requires──> N-step-ahead forecasting backend (not just 1-step, unlike Excel workbook)
                       └──requires──> Model research/backtest phase (per PROJECT.md, no un-backtested model ships)

Bull/base/bear scenario display
    └──requires──> Forecast horizon selector (scenarios are computed per horizon step)
    └──requires──> Base forecast + statistical spread (backtest error/volatility)

Confidence-band chart rendering ──enhances──> Bull/base/bear scenario display
    (same underlying data, different visual treatment — can ship after 3-line version if time-constrained)

Excel export
    └──requires──> Data persistence (SQLite table must exist and be populated)
    (independent of forecasting — can ship before or after forecast features)

Derived Diesel-MNT series
    └──requires──> Diesel-USD forecast AND FX forecast
                       (both must exist before the derived series can be computed/displayed)

Inline in-row table editing ──enhances──> Manual data entry
    (not a separate feature — an implementation-quality upgrade to "edit an existing row")

Multi-series single-page dashboard ──enhances──> Per-product forecast display
    (layout decision on top of already-computed forecasts, not a new data dependency)
```

### Dependency Notes

- **Forecast horizon selector requires N-step-ahead forecasting backend:** the Excel workbook only ever forecasts one month ahead; supporting a 1–12 month slider means the backend models (VAR/AR/whatever wins backtesting) must be able to produce a full path of predictions, not a single next-step number. This is a backend research/design cost, not a UI cost — flag for the research/planning phase, not treated as "just add a slider."
- **Bull/base/bear requires horizon selector:** scenarios are meaningless without a horizon to spread across — these two features must land in the same phase or scenario data has nothing to render against.
- **Derived Diesel-MNT requires both Diesel-USD and FX forecasts:** if these two source forecasts are built in different phases, Diesel-MNT display must wait for whichever lands second — sequence FX and Diesel-USD model work before exposing the derived series in the UI.
- **Excel export conflicts with nothing and depends only on persistence:** it can be built early (even against seed data) and is a good low-risk phase-1 candidate to validate the SQLite schema before forecasting logic is built on top of it.
- **Confidence-band rendering enhances but doesn't block bull/base/bear:** ship the simpler 3-line version first if needed; band styling is a low-cost visual upgrade that can land in a later phase without touching the underlying scenario math.

## MVP Definition

### Launch With (v1)

Minimum viable product — validates "can I see a real forecast with a range, for a horizon I choose, without opening Excel."

- [ ] Manual add/edit/delete of data rows, persisted in SQLite — replaces the Excel Input tab workflow
- [ ] Basic input validation on entry (types, plausible ranges) — protects model integrity from day one
- [ ] Historical price chart per series (actuals) — establishes trust before forecasts are shown
- [ ] Forecast horizon selector (1–12 months) — the core differentiator, must exist for scenarios to mean anything
- [ ] Base/bull/bear forecast values (base ± statistical spread) for HDAN, PPAN, Diesel-USD, FX, and derived Diesel-MNT — the stated Core Value
- [ ] Scenario chart (3 lines minimum; shaded band is a nice-to-have, not required for v1) across the chosen horizon
- [ ] Forecast values also shown as a table (not chart-only) — procurement/budgeting users need copyable numbers
- [ ] Excel export of the stored data table
- [ ] Loading/empty states so the app doesn't look broken pre-seed or mid-compute

### Add After Validation (v1.x)

Features to add once the core loop (enter data → pick horizon → see scenario forecast) is working and trusted.

- [ ] Confidence-band (shaded area) chart styling — upgrade from 3 discrete lines once the base scenario math is proven correct
- [ ] Inline in-row table editing (vs. modal/form edit) — once the data-entry workflow is validated, tighten the UX to match/beat Excel's inline editing
- [ ] Multi-series single-page dashboard layout (all 4 series visible together) — once individual series views are working, consolidate for at-a-glance use
- [ ] "As of" / last-updated freshness indicator per series — small trust-building addition once real monthly usage begins

### Future Consideration (v2+)

Explicitly deferred per PROJECT.md — do not pull forward without a new decision.

- [ ] Weekly forecast mode — blocked on resolving the AN-family vs. Diesel/FX weekly data-cadence gap (design doc §6); needs its own research pass before scoping
- [ ] Live news/sentiment-driven bull/bear adjustment — provider selection (news API + LLM scoring vs. dedicated market-data provider) is an open research question, not decided
- [ ] Automatic API data-fetch from external price sources — only relevant if/when the "connect to a data API" idea is picked up as its own milestone
- [ ] File-upload/bulk CSV import — may return if the API-connection idea is picked up, since ingestion design would change together

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|----------------------|----------|
| Manual data entry (add/edit/delete row) | HIGH | MEDIUM | P1 |
| Forecast horizon selector (1-12mo) | HIGH | MEDIUM (backend-heavy) | P1 |
| Bull/base/bear scenario values + chart | HIGH | MEDIUM | P1 |
| Forecast values table (numbers) | HIGH | LOW | P1 |
| Excel export | HIGH | LOW-MEDIUM | P1 |
| Historical actuals chart | MEDIUM | LOW | P1 |
| Input validation | MEDIUM (protects model quality) | MEDIUM | P1 |
| Derived Diesel-MNT display | HIGH | LOW (once inputs exist) | P1 |
| Confidence-band (shaded) chart styling | MEDIUM | LOW-MEDIUM | P2 |
| Inline in-row editing | MEDIUM | MEDIUM | P2 |
| Multi-series single-page layout | MEDIUM | MEDIUM | P2 |
| "As of" freshness indicator | LOW-MEDIUM | LOW | P2 |
| Weekly forecast mode | MEDIUM (user-requested, gated) | HIGH (data gap unresolved) | P3 |
| Live news/sentiment scenarios | MEDIUM | HIGH | P3 |
| Automatic API data-fetch | LOW (for single occasional user) | HIGH | P3 |
| Bulk CSV upload | LOW (rare-frequency action) | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor/Analogue Feature Analysis

No direct competitor combines manual single-user entry + multi-horizon commodity forecasting + bull/base/bear scenarios in one small tool; the closest analogues are institutional commodity-outlook platforms (scenario forecasting, no manual entry) and personal budgeting/data-grid tools (manual entry, no forecasting). Comparison synthesizes patterns from both categories.

| Feature | Institutional commodity outlook platforms (e.g., Citigroup, CRU Group style) | Personal budgeting/data-entry tools (spreadsheet-replacement category) | Our Approach |
|---------|-------------------------------------------------------------------------------|--------------------------------------------------------------------------|--------------|
| Scenario/range display | Shaded probability bands or explicit bull/base/bear cases with stated probabilities, presented as authoritative institutional research | Rarely present — these tools track actuals/budgets, not forward scenarios | v1: base ± statistical spread rendered as 3 lines; v1.x: shaded band styling once proven |
| Data entry | None — data is provider-curated, read-only for the end user | Core feature — inline/grid editing is standard, often with keyboard-navigable cells (Excel-like) | Manual add/edit/delete row in v1, upgraded to inline in-row editing in v1.x |
| Horizon control | Fixed report horizons (quarterly/annual outlooks), not user-adjustable | N/A — not forecast-oriented | User-adjustable 1-12 month slider, the project's stated differentiator |
| Export | Often PDF/report download, not editable data export | Excel/CSV export is table stakes for spreadsheet-replacement tools | Excel export of the underlying data table (matches budgeting-tool convention, not report-PDF convention) |

## Sources

- Project context: `/Users/dlgvnbyr/Desktop/Prediction Dashboard/.planning/PROJECT.md` (validated/active/out-of-scope requirements, core value statement)
- Design doc: `/Users/dlgvnbyr/Desktop/Prediction Dashboard/docs/plans/2026-08-21-reflex-dashboard-design.md` (architecture, scenario design v1/v2 split, weekly-mode data gap)
- [Data Table Design UX Patterns & Best Practices — Pencil & Paper](https://www.pencilandpaper.io/articles/ux-pattern-analysis-enterprise-data-tables) (MEDIUM confidence — general enterprise data-table UX, applied here to a smaller-scale case)
- [Best Practices for Inline Editing in Table Design — UX Design World](https://uxdworld.com/inline-editing-in-tables-design/) (MEDIUM confidence — supports "inline editing reduces friction" claim used for the in-row editing differentiator)
- [Reflex Data Table Editor Template](https://reflex.dev/templates/data-table-editor/) (MEDIUM confidence — confirms Reflex has first-party support/patterns for editable data grids, relevant to feasibility of the inline-editing differentiator)
- [Editable Data Tables in Streamlit — Streamlit Community](https://discuss.streamlit.io/t/editable-data-tables-in-streamlit/529) and [Interactively editable data table in streamlit](https://discuss.streamlit.io/t/interactively-editable-data-table-in-streamlit/5200) (LOW-MEDIUM confidence, adjacent-framework analogue, used only to confirm editable-grid patterns are a common expectation in small Python-dashboard tools generally)
- Commodity scenario/outlook framing (bull/base/bear as an institutional convention): [Citigroup Commodities Market Outlook 4Q'25](https://www.citigroup.com/global/insights/commodities-market-outlook-4q-25), [CRU Group — Navigate Commodity Markets with Scenarios & Forecasts](https://www.crugroup.com/en/insight/forecasts-and-scenarios/) (MEDIUM confidence — confirms bull/base/bear with probability framing is an established convention in commodity forecasting, supporting the project's chosen scenario model)

---
*Feature research for: single-user commodity/FX price forecasting dashboard*
*Researched: 2026-08-21*
