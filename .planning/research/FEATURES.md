# Feature Research

**Domain:** Single-user financial/commodity forecasting dashboard — export/import UX, forecast context enrichment, large-table UX
**Researched:** 2026-08-24
**Confidence:** MEDIUM (WebSearch-verified against multiple sources; no Context7-eligible library for these UX patterns — this is a domain/UX question, not an API question)

## Framing

This app has **one user**, monthly-cadence data entry, ~167 rows today growing by ~1 row/series/month (~12-48 rows/year across 4 series depending on table shape). This is *not* a multi-tenant SaaS import pipeline or a BI tool serving many analysts. Recommendations below are filtered hard against that reality — most "enterprise CSV import" and "BI dashboard" patterns found in research are explicitly downgraded to anti-features here because they solve problems this app doesn't have (many users, adversarial/dirty data sources, huge row counts).

---

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Excel export retains one clean, formula-free data sheet (current raw price table) | Baseline already shipped; "garbage in, garbage out" — export must be trustworthy as a record, not just a dump | LOW (already exists) | Keep as Tab 1 (`Data_Raw`) in any multi-sheet redesign — no formulas, no merged cells, plain tabular data so it can be re-opened, re-sorted, or fed into the existing Excel workbook if needed. |
| Export includes column headers + units (MNT, USD, etc.) and consistent number formatting | Finance/procurement users copy these numbers into other documents; ambiguous units or raw floats erode trust | LOW | Cheap win: set `number_format` per column in openpyxl (e.g. `#,##0.00`) instead of leaving default General format. |
| CSV/bulk import validates before committing, and *shows* what will change | Standard expectation across all import UX research: users need a preview before data is written, not a silent success/fail | MEDIUM | Even a single-user app benefits from "show me the diff before you touch my 167-row history." A one-shot silent import risks corrupting the only copy of the data. |
| Import gives row-level error messages, not just "import failed" | Universal finding across CSV import UX sources — vague failures force users to guess-and-recheck the whole file | MEDIUM | For this app's scale (a handful of rows per import), a simple in-page table listing "Row 3: PPAN value is not numeric" is sufficient — no need for a downloadable error-report file at this volume. |
| Table shows recent history by default with a way to see everything | Already decided/in-scope in this milestone (recent-months default + "show all" toggle) — listed here only because it's the precondition every other table-scale feature below assumes | LOW (already scoped separately) | Not part of this research's export/import/context/scale scope, but forecast-context features (below) should reuse whatever date-range state this introduces rather than inventing a second filter. |
| Historical high/low and % change vs. last period on the forecast summary cards | Nearly universal on financial/commodity dashboards — "where does today sit relative to history" is the single most common piece of context added beyond a raw forecast number | LOW-MEDIUM | Cheap to compute from existing SQLite data (`MAX`/`MIN`/`first row - last row` over the loaded history) — no new data source needed. Natural extension of the four existing summary cards. |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Excel export with a real multi-sheet workbook (Data / Summary-or-Pivot / Forecast) mirroring the existing `AN_HDAN_PPAN_Diesel_FX_Forecast_Model.xlsx` structure | User already has mental model of a 5-tab workbook (Input/PctChange/Regression/Forecast/Dashboard); an export that echoes that structure (Data, Forecast-with-scenarios, maybe a light Dashboard-style summary sheet) is *more* useful to them than a flat table, and directly serves the "companion, not replacement" positioning in PROJECT.md | MEDIUM | openpyxl supports multiple sheets and native Excel charts (`openpyxl.chart.LineChart`) in one file — no extra library needed. Embedding a real Excel-native line chart (not just a pasted image) lets the user keep exploring the forecast fan chart offline in Excel itself, which is a genuine differentiator over "export = CSV dump." |
| YoY / period-over-period % change context alongside MoM | Standard on finance forecasting dashboards per research (YoY trend context improves forecast interpretability); for a procurement user asking "what will I pay N months from now," "vs. this time last year" is often more decision-relevant than vs. last month, since commodity/FX prices are seasonal | LOW-MEDIUM | Same computation pattern as high/low — subtract row from ~12 months back in the same series. Works cleanly with monthly-cadence data already in SQLite; do not attempt for weekly mode until that data-cadence question (already flagged in PROJECT.md as blocked) is resolved. |
| "Drivers" explanation text (e.g. "Diesel-MNT forecast driven primarily by FX and Brent-linked Diesel-USD trend") | Plain-language explanation of *why* a forecast moved, using the model's own known structure (VAR for HDAN/PPAN, AR-lag-2-on-Brent for Diesel, AR(1) for FX) rather than a generic BI "anomaly detection" feature | MEDIUM | This can be templated, not ML-generated: since the model families are fixed and known (per PROJECT.md), a short static/templated sentence per series ("Diesel-MNT = Diesel-USD forecast × FX forecast × markup") is honest, cheap, and matches how the Excel workbook already documents its logic. Avoid dynamic LLM-generated driver text — no LLM dependency exists yet in this app (explicitly deferred to v2 per PROJECT.md), and templated text is more auditable for a finance use case anyway. |
| CSV import with column-mapping UI (map arbitrary header names to the app's canonical columns) | Reduces friction if the source file's headers don't exactly match the DB schema (e.g. re-exports from the Excel workbook, or copy-pasted data with slightly different column names) | MEDIUM-HIGH | Worth doing only if import sources are genuinely variable. Given this app's only plausible import source is the user's own Excel workbook (fixed, known column layout) or a re-export of this app's own Excel export (round-trip), a *fixed* expected-column-order import with clear validation errors is likely sufficient — see Anti-Features below. Only add full fuzzy column-mapping if the user confirms multiple differently-shaped source files in practice. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Fuzzy/AI-powered column auto-mapping for CSV import (as seen in tools like Dromo/CSVBox) | Looks impressive, commonly cited as "modern" import UX | Built for multi-tenant SaaS ingesting files from many different unknown external users/systems. This app has exactly one user importing from at most 1-2 known, fixed-shape sources (their own Excel workbook or this app's own export). Fuzzy mapping adds a new dependency/complexity for a mapping problem that barely exists here. | A fixed expected-column-order template (documented, maybe downloadable as a starter CSV) with clear "column X missing/misnamed" validation errors. |
| Streaming/chunked validation for large file uploads (100MB+ CSV handling patterns) | Common CSV-import-best-practices advice | This app's entire historical dataset is ~167 rows across 4 series — a full import is a few KB, not tens of MB. Streaming validation infrastructure solves a scale problem that will not occur here for years, if ever, given monthly-cadence data entry. | Validate the whole (small) file synchronously in memory; show all row errors in one pass. |
| Infinite scroll for the price-entry table | Feels "modern," common on consumer feeds | Research is consistent: infinite scroll is for discovery/feed content, not analytical/reference tables — it breaks scannability, loses position on refresh, and is harder to reconcile against "which row am I editing" in a data-entry context. Also conflicts with the already-decided recent-months-default approach for this milestone. | Recent-months default + explicit "show all history" toggle (already decided) ± a simple date-range filter if "show all" ever becomes sluggish again; add pagination only if row count grows into the thousands, which is not expected for a monthly-cadence single-series dataset for years. |
| Automated anomaly detection / "predictive dashboarding" style AI insights on forecast variance | Appears in generic BI/forecasting-dashboard best-practice lists | Requires either an ML component beyond the backtested statsmodels models already scoped, or an LLM dependency — both explicitly out of scope/deferred per PROJECT.md ("Live news/sentiment-driven bull/bear scenario adjustment... explicitly deferred to v2"). Building ad hoc anomaly detection here duplicates that already-deferred, not-yet-researched work. | Use the templated "drivers" explanation (above) instead — cheap, honest, and grounded in the already-known/backtested model structure rather than a new inference layer. |
| Real-time/auto-refreshing dashboard updates | Standard BI-dashboard checklist item | User enters data ~monthly and views the dashboard occasionally — there is no live external data feed to refresh against yet (API auto-fetch is explicitly out of scope for v1 per PROJECT.md). A refresh mechanism with nothing changing underneath it is complexity with zero payoff. | Static page reflecting current SQLite state; re-render on data entry/import as already happens. |
| Resumable/multi-step wizard-style bulk import flow with saved partial progress | Common in enterprise import UX guides (Dromo, CSVBox) for large multi-minute imports | A single-user monthly import is a handful of rows and takes seconds to review — a multi-step wizard with resumable state adds UI surface area and session-state complexity disproportionate to the task size. | Single-page: upload → preview/validate table → confirm → commit. No wizard, no resume-later state. |

---

## Feature Dependencies

```
Excel export "Data_Raw" sheet (already shipped)
    └──extended-by──> Multi-sheet Excel export (Data + Forecast-with-chart)
                           └──requires──> existing forecast module output (base/bull/bear per series, already built)

Recent-months-default table (already decided, separate scope)
    └──enables──> Date-range-aware high/low & YoY context
                      (context stats should read from full history in DB,
                       not just the currently-displayed recent-months slice)

CSV bulk import (validate → preview → commit)
    └──requires──> existing rx.Model schema (already defined for price-entry table)
    └──conflicts-with──> fuzzy column auto-mapping (unneeded complexity, see Anti-Features)

"Drivers" explanation text
    └──requires──> known, fixed model family per series (VAR / AR-lag-2-on-Brent / AR(1))
                    (already decided in PROJECT.md — do NOT build if model selection
                     research is still in flux for a given series)

YoY % change
    └──requires──> ≥ 1 full year of monthly history already in SQLite (available: data since 2013/2020)
    └──blocked-for──> weekly-mode series until the weekly data-cadence gap (PROJECT.md §6) is resolved
```

### Dependency Notes

- **Multi-sheet Excel export requires the forecast module's existing base/bull/bear output** — no new forecasting logic needed, purely a presentation/export-layer change reusing data the app already computes for the on-screen forecast table.
- **High/low and YoY context should query full history from SQLite, not the currently-rendered "recent months" table slice** — keep the context-stat computation independent of whatever windowing the data-entry table UI applies, so the two features (table UX fix vs. forecast context) don't get coupled by accident.
- **"Drivers" text depends on model family being fixed and known** — since PROJECT.md states models must go through backtesting before shipping, drivers text should be written per confirmed model, not written speculatively ahead of the research/backtest step.
- **YoY is blocked for weekly-cadence series** — same open gap PROJECT.md already flags for weekly forecasting (§6); don't build YoY logic assuming weekly data exists.
- **CSV import explicitly conflicts with fuzzy auto-mapping** — pick the fixed-schema approach; revisit only if real usage proves multiple import source shapes exist.

---

## MVP Definition (for this milestone, v1.2)

### Launch With (v1.2)

- [ ] Excel export gains a second sheet with the base/bull/bear forecast table (reusing existing forecast output) — low effort, directly extends an already-shipped feature
- [ ] Number formatting (units, decimals, thousands separators) applied to all exported columns — cheap correctness fix
- [ ] Forecast summary cards gain historical high/low and % change vs. same-period-last-year (where ≥12 months of history exists) — reuses existing SQLite data, no new inputs
- [ ] Simple CSV bulk import: fixed expected column order, in-page preview + row-level validation errors, explicit confirm-to-commit step — no wizard, no fuzzy mapping

### Add After Validation (v1.x)

- [ ] Native Excel line-chart embedded in the export's forecast sheet (vs. a plain data table) — do after confirming users actually open exports in Excel and want to interact with the chart there, not just view the numbers
- [ ] Templated "drivers" explanation text per series — do once model family per series is fully confirmed post-backtest, so text doesn't need rewriting if model selection changes

### Future Consideration (v2+)

- [ ] Column-mapping UI for CSV import — only if a second real import source with a different column layout actually materializes
- [ ] Any anomaly-detection or AI-generated forecast commentary — depends on the explicitly-deferred news/LLM provider research (PROJECT.md, out of scope)
- [ ] Weekly-cadence YoY/context stats — blocked on the weekly data-cadence gap research (PROJECT.md §6)

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Historical high/low + YoY % change on summary cards | HIGH | LOW | P1 |
| Multi-sheet Excel export (Data + Forecast) | HIGH | MEDIUM | P1 |
| Number formatting in export | MEDIUM | LOW | P1 |
| CSV bulk import (fixed schema, validated preview) | MEDIUM-HIGH | MEDIUM | P1 |
| Embedded native Excel chart in export | MEDIUM | MEDIUM | P2 |
| Templated drivers explanation | MEDIUM | MEDIUM | P2 |
| Column-mapping UI for import | LOW (for this user) | HIGH | P3 |
| Anomaly detection / AI commentary | LOW (out of scope) | HIGH | P3 (defer) |

**Priority key:**
- P1: In scope for this milestone's research-informed requirements
- P2: Reasonable v1.x follow-up, not blocking
- P3: Explicitly deferred, tied to other blocked/out-of-scope decisions

---

## Sources

- [Financial Dashboard Template - Excel Dashboard School](https://exceldashboardschool.com/financial-dashboard-template/) — MEDIUM confidence, generic Excel dashboard structure advice (3-tab Data/Calculation/Dashboard pattern), consistent with multiple other sources in this search
- [Best UX flow for spreadsheet imports - CSVBox Blog](https://blog.csvbox.io/spreadsheet-import-ux/) — MEDIUM confidence, file → map → validate → submit flow; vendor content but pattern is corroborated by other CSV-import UX sources
- [How To Design Bulk Import UX (+ Figma Prototypes) — Smart Interface Design Patterns](https://smart-interface-design-patterns.com/articles/bulk-ux/) — MEDIUM confidence, general bulk-import UX patterns (preview, row-level errors)
- [Best Practices for Handling Large CSV Files Efficiently](https://dromo.io/blog/best-practices-handling-large-csv-files) — MEDIUM confidence; explicitly noted here as describing a *different scale problem* than this app has (large-file streaming) — used as a negative reference to justify an anti-feature
- [Key Features: Driver-Based Forecast Design | Medium](https://medium.com/@joshrapkin1/key-features-driver-based-forecast-design-b1b062045451) — LOW-MEDIUM confidence, single-author piece, but corroborates the general "driver-based" forecasting context pattern seen elsewhere
- [Year-Over-Year (YOY) Growth: How to Calculate in Excel](https://www.xelplus.com/yoy-excel/) — MEDIUM confidence, standard YoY calculation approach, straightforward and uncontroversial
- [The Ultimate Guide to Year-Over-Year Analysis](https://www.oneadvanced.com/resources/the-ultimate-guide-to-year-over-year-analysis/) — MEDIUM confidence, corroborates YoY as standard forecasting-context practice
- [Data table design: Best practices for better UX - LogRocket Blog](https://blog.logrocket.com/ux-design/data-table-design-best-practices/) — MEDIUM confidence, corroborates pagination-over-infinite-scroll for analytical/reference tables
- [Pagination UI design: Offset vs keyset vs infinite scroll | Setproduct Blog](https://www.setproduct.com/blog/pagination-ui-design) — MEDIUM confidence, corroborates pagination as the right pattern for structured/analytical data vs. feeds
- Project files: `.planning/PROJECT.md` — source of hard constraints (single user, no LLM/news dependency yet, weekly-mode data gap, fixed backtested model families) used to filter generic research findings down to what's actually applicable here

---
*Feature research for: single-user commodity/FX forecasting dashboard — export/import UX, forecast context, large-table UX*
*Researched: 2026-08-24*
