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
- **D-05:** Seeded rows keep full available history from both source files —
  from `Diesel Data.csv`'s 2020-02 start — not trimmed to the shortest
  common range. AN-family columns (HDAN, PPAN, Baltic_AN, Ammonia, Urea,
  Natural_Gas, Brent) are `NULL` for months before `AN Data.csv`'s coverage
  begins (2022-08), per D-03.
- **D-06:** `AN Data.csv` has multiple entries within some months (weekly-ish
  cadence). Collapse to one row per month by **averaging** all entries within
  that month — not taking the last entry. (Note: this differs from the
  approach sketched in the earlier `docs/plans/2026-08-21-reflex-dashboard-implementation.md`
  Task 3, which used `.last()` — this phase's seed script should average
  instead; update or ignore that earlier plan's specific code sample
  accordingly.)
- **D-07:** `AN price weekly.csv` is explicitly **not** seeded in this phase.
  It doesn't map onto the monthly wide-table schema (different columns, no
  HDAN/PPAN) and is only relevant to the weekly-mode/Baltic-AN-proxy research
  question, which belongs to Phase 2 (or later, since weekly mode itself is
  v2/deferred scope per REQUIREMENTS.md). Leave the CSV file where it is;
  Phase 2's research can read it directly if needed.

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
