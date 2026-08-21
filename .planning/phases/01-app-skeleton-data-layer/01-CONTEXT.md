# Phase 1: App Skeleton & Data Layer - Context

**Gathered:** 2026-08-21
**Status:** Ready for planning

<domain>
## Phase Boundary

A running Reflex application backed by a SQLite schema covering all tracked
fields (Date, HDAN, PPAN, Baltic_AN, Ammonia, Urea, Natural_Gas, Brent,
Diesel_USD_ton, Urals, FX_rate), seeded from the existing CSV source data
(`AN Data.csv`, `Diesel Data.csv`), with a minimal page that makes the seeded
data visibly verifiable. This is a foundation phase — it doesn't do
forecasting, editing, or scenario display; it only proves the app runs and
the data layer is populated correctly.

</domain>

<decisions>
## Implementation Decisions

### Schema shape
- **D-01:** Wide table, one row per calendar month, one column per series
  (matches the Excel Input tab and the earlier implementation-plan `PriceRow`
  model) — not a normalized/tidy `(date, series_name, value)` table. Chosen
  because statsmodels wants aligned, time-indexed series per column, and this
  keeps Phase 3's forecasting code and Phase 4's editing UI simple.
- **D-02:** `Date` has a unique constraint; seeding/editing upserts on
  conflict rather than allowing duplicate months.
- **D-03:** Any series column may be `NULL` when that value isn't known yet
  for a given month — matches the Excel workbook's "leave blank if unknown"
  convention. Do not require every column to be populated on every row.

### Markup handling
- **D-04:** `Markup_%` is a single global setting (one editable value), not a
  per-row field — matches the Excel workbook's `Input!M2` cell. This value is
  consumed in Phase 3 for the Diesel-MNT derived series but the setting/table
  for it should be created in this phase alongside the main schema.

### Seed merge strategy

**SUPERSEDED 2026-08-21, mid-planning (after 01-01/01-02/01-03 PLAN.md were
already written once) — see below.** D-05/D-06/D-07 as originally written are
replaced by D-05b/D-06b/D-07b. The change: `AN price weekly.csv` (true
weekly cadence, history back to 2013-01) has meaningfully longer history for
the non-HDAN/PPAN AN-family series than `AN Data.csv` does, so those columns
now come from the weekly file instead. Plans 01-01 and 01-02 need to be
amended to reflect this before execution.

- **D-05b (supersedes D-05):** Three source files feed the seed, each
  contributing only the columns it's authoritative for:
  - `AN Data.csv` → **only** `hdan`, `ppan` (this file's other columns —
    Baltic AN, Ammonia, Urea, Natural_gas — are no longer used; superseded
    by the weekly file's longer history for those series)
  - `AN price weekly.csv` → `baltic_an`, `ammonia`, `urea`,
    `natural_gas_jkm`, `natural_gas_henry_hub`, `natural_gas_uk`,
    `natural_gas_netherlands`, `corn_us`, `corn_china` (9 columns; history
    back to 2013-01-11 per its earliest row, far longer than AN Data.csv's
    2022-08 start)
  - `Diesel Data.csv` → `diesel_usd_ton`, `urals`, `fx_rate`, `brent` (Brent
    now sourced here instead of from AN Data.csv, since Diesel Data.csv's
    Brent history starts 2020-02 vs. AN Data.csv's 2022-08 — more history
    for Phase 2's Diesel-on-Brent-lag model)
  - Full available history is kept per source (still no trimming to a
    shortest-common range); each column is `NULL` for any month before its
    source file's coverage begins, per D-03.
  - **Schema impact:** the wide table now has 4 natural-gas columns instead
    of 1, plus `corn_us`/`corn_china` — 15 series columns total instead of
    the original 10 (`Date` + 10 in the original CONTEXT.md's canonical_refs
    list). Update D-01's understanding of the schema accordingly; the shape
    (wide, one row per month) is unchanged, only the column list grew.
- **D-06b (supersedes D-06):** Both `AN Data.csv` and `AN price weekly.csv`
  have multiple entries within some months. Collapse to one row per month by
  **averaging** all entries within that month for both sources — D-06's
  averaging rule now applies uniformly across all multi-entry source files,
  not just `AN Data.csv`.
- **D-07b (supersedes D-07):** `AN price weekly.csv` **is** seeded in this
  phase after all — it's now a primary source for 9 of the schema's columns,
  not deferred to Phase 2. (D-07's original reasoning — "doesn't map onto the
  schema, no HDAN/PPAN" — is now moot since D-05b only ever sources
  HDAN/PPAN from `AN Data.csv`, not the weekly file.)

### Skeleton UI scope
- **D-08:** Phase 1's page shows a **read-only table of the seeded data** —
  not a bare placeholder. This makes "seed data loaded and queryable"
  (success criterion 2) visibly verifiable in the running app, not just via a
  direct DB query, and gives Phase 4 a real (if minimal) page to extend with
  editing.

### Claude's Discretion
User had no preference on the following — use judgment, consistent with the
existing design docs:
- **Column naming:** use snake_case names matching the design doc's `PriceRow`
  model (`baltic_an`, `natural_gas`, `diesel_usd_ton`, etc.), not the source
  CSVs' raw messy headers (`"Baltic AN"`, `" Natural_gas "` with stray
  whitespace). Strip/clean during the seed parse step, same as the earlier
  implementation plan's `parse_an_data`/`parse_diesel_data` approach.
- **Python environment/dependency pinning:** set up a virtualenv in `app/`
  with `requirements.txt`; loose-but-sane version ranges are fine (exact pins
  not required).
- **Seed script re-run behavior:** re-running the seed script should upsert
  (update existing rows by date, insert new ones) rather than fail on
  duplicates or blindly append — consistent with D-02's unique-date
  constraint.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design & requirements
- `docs/plans/2026-08-21-reflex-dashboard-design.md` — overall architecture,
  data flow, and the weekly-mode data gap (§6) this phase deliberately defers
- `docs/plans/2026-08-21-reflex-dashboard-implementation.md` §Task 1-3 — prior
  sketch of app skeleton, `PriceRow` model, and seed script; **note D-06
  above overrides its `.last()` collapse approach with averaging**
- `.planning/PROJECT.md` — project context, core value, constraints
- `.planning/REQUIREMENTS.md` — v1 requirement list (this phase maps to no
  requirements directly; it's a foundation phase per ROADMAP.md)
- `.planning/research/STACK.md` — confirms Reflex 0.9.8, `rx.Model`/SQLModel,
  pandas 3.0.5 (copy-on-write default change — check before writing the CSV
  parse/seed code), openpyxl
- `.planning/research/ARCHITECTURE.md` — component boundaries; confirms
  `forecasting.py` (Phase 3, not this phase) must have zero `import reflex`,
  and that `research/` stays separate from `app/app/` — relevant context even
  though this phase doesn't touch forecasting yet, since it sets up the
  directory structure those boundaries depend on
- `.planning/research/PITFALLS.md` — "State reflects DB, DB is source of
  truth" pattern should be established starting in this phase's data layer,
  before Phase 4 builds data-entry UI on top of it

### Source data (this phase seeds from these)
- `AN Data.csv` — HDAN/PPAN/Baltic_AN/Ammonia/Urea/Natural_Gas/Brent, from
  2022-08, multiple entries per month in places (see D-06)
- `Diesel Data.csv` — Diesel_USD_ton/Urals/FX_rate/etc., from 2020-02, one row
  per month
- `AN price weekly.csv` — explicitly NOT seeded this phase (see D-07)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None yet — this is the first phase of the Reflex app (`app/` subfolder does
  not exist before this phase creates it). The Excel-workbook side of the
  project (`scripts/build_workbook.py`, `backend_research/`) is a separate,
  untouched system; nothing there is directly reusable code, though
  `backend_research/data_loader.py` may be a useful reference for CSV-parsing
  patterns (whitespace/comma stripping) even though it wasn't written for
  this schema.

### Established Patterns
- None yet in `app/` — this phase establishes the first patterns (schema
  shape, seed approach) that later phases build on.

### Integration Points
- Phase 2 (Model Research) will query this phase's seeded SQLite table
  directly for backtesting.
- Phase 3 (Forecasting Module) reads historical series from this schema.
- Phase 4 (Data Entry UI) extends this phase's read-only table into an
  editable one, reusing the same schema and the "DB is source of truth"
  pattern.

</code_context>

<specifics>
## Specific Ideas

No specific UI/styling references given — open to standard Reflex patterns
for the read-only data table (D-08).

</specifics>

<deferred>
## Deferred Ideas

None raised outside phase scope — discussion stayed within Phase 1's
boundary (schema, seed data, minimal UI).

</deferred>

---

*Phase: 1-App Skeleton & Data Layer*
*Context gathered: 2026-08-21*
