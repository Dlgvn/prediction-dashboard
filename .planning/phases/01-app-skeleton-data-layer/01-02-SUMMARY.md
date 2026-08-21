---
phase: 01-app-skeleton-data-layer
plan: 02
subsystem: database
tags: [pandas, sqlmodel, reflex, sqlite, etl]

# Dependency graph
requires:
  - phase: 01-app-skeleton-data-layer (plan 01)
    provides: PriceRow/AppSetting SQLModel schema with 16-series wide-table shape (D-01/D-05b/D-05c)
provides:
  - "app/app/seed.py: parse_an_data, parse_an_weekly, parse_diesel_data, seed_database"
  - "164 monthly rows of real historical price data seeded into SQLite (2013-01 through 2026-08)"
affects: [phase-02-model-research, phase-03-forecasting, phase-04-data-entry-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CSV parse -> _clean_numeric coercion -> monthly mean collapse (D-06b) -> outer merge -> reindex over contiguous period_range -> upsert-by-date"
    - "Standalone seed script (python -m app.seed), never imported by app startup"

key-files:
  created:
    - app/app/seed.py
    - app/tests/test_seed.py
  modified: []

key-decisions:
  - "D-06b averaging (not .last()) applied uniformly to both AN Data.csv and AN price weekly.csv multi-entry months"
  - "AN price weekly.csv seeded this phase as the authoritative 10-column source per D-07b, including both urea benchmarks kept separate per D-05c"
  - "AN Data.csv retired to hdan/ppan only per D-05b; brent now sourced from Diesel Data.csv"

patterns-established:
  - "NaN -> None conversion before ORM assignment (prevents float('nan') being stored as a non-NULL DB value)"

requirements-completed: []

# Metrics
duration: 25min
completed: 2026-08-21
---

# Phase 1 Plan 2: Historical Data Seed Summary

**Three-source CSV seed script (AN Data.csv, AN price weekly.csv, Diesel Data.csv) with D-06b monthly-mean collapse and D-02 upsert, loading exactly 164 monthly rows (2013-01 through 2026-08) into SQLite.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-08-21T04:15:00Z (approx, per STATE.md session continuity)
- **Completed:** 2026-08-21
- **Tasks:** 3 completed
- **Files modified:** 2 (app/app/seed.py, app/tests/test_seed.py)

## Accomplishments
- `app/app/seed.py` exports `parse_an_data`, `parse_an_weekly`, `parse_diesel_data`, `seed_database`
  matching the exact D-05b/D-05c column contract (16 series columns across 3 sources).
- Monthly averaging collapse (D-06b) applied uniformly to both multi-entry sources, overriding
  the prior implementation sketch's `.last()` approach.
- Three-way outer merge on calendar month, reindexed over the full contiguous period range so
  missing months are impossible by construction rather than by coincidence.
- Idempotent upsert-by-date (D-02): re-running the seed script updates existing rows in place.
- Real CSV files seeded and every precomputed row-shape assertion from the plan's `<interfaces>`
  block verified to hold exactly.

## Task Commits

Each task was committed atomically:

1. **Task 1: Three CSV parsers with whitespace, comma and blank-row handling** - `59234e1` (test, RED) then implemented in `a0dad53` (feat, GREEN, combined with Task 2)
2. **Task 2: Monthly averaging collapse, three-way outer merge, and idempotent upsert** - `a0dad53` (feat)
3. **Task 3: Seed the real CSVs and assert the expected row shape** - verification-only, no code changes; no commit required (see below)

**Plan metadata:** committed with this SUMMARY.

_Note: Tasks 1 and 2 were implemented together in a single GREEN commit (`a0dad53`) after the
combined RED commit (`59234e1`) covering both tasks' fixture tests, since both tasks target the
same file (`app/app/seed.py`) and were designed and verified as one coherent implementation
pass. All 16 behavior-item tests from both tasks pass. Task 3 is a real-data verification task
per the plan (no `files_modified` beyond the already-committed `seed.py`); it ran the seed
script against the actual CSVs and confirmed the shape assertions, producing no diff to commit._

## Files Created/Modified
- `app/app/seed.py` - Three CSV parsers, `_clean_numeric`, `_collapse_monthly`,
  `_build_merged_frame`, `seed_database`, and a `python -m app.seed` CLI entry point.
- `app/tests/test_seed.py` - 16 fixture-based tests covering header cleaning, numeric coercion,
  D-06b monthly averaging (including the NaN-skip and all-NaN-stays-NaN cases), the three-way
  merge with contiguous reindex, month-start date string format, and idempotent upsert with
  NaN->None conversion.

## Decisions Made
- Confirmed D-06b overrides the `.last()` collapse in
  `docs/plans/2026-08-21-reflex-dashboard-implementation.md` line 259 — averaging now applies to
  both `AN Data.csv` and `AN price weekly.csv`, not only the former.
- `_get_session()` wraps `rx.session()` behind a module-level function so tests can monkeypatch
  it with the isolated in-memory `conftest.py` session fixture without touching the real
  `reflex.db`.
- Reworded a docstring line referencing the retired `.last()` approach so it doesn't collide with
  the plan's `grep -c "\.last()"` verification gate (the gate is not comment-aware for docstring
  prose, only for lines starting with `#`).

## Deviations from Plan

None - plan executed exactly as written. The only adjustment was the docstring wording noted
above, which is a documentation-only change made to satisfy the plan's own automated verify gate
(`grep -c "\.last()"` must return 0) — not a deviation from the plan's intended behavior.

## Issues Encountered

None. All fixture tests passed on first implementation, and the real-CSV verification in Task 3
matched every precomputed assertion (164 rows, per-column NULL counts, coverage-window boundaries,
the two internal NULL anomalies, and the 2022-08-01 spot-check) without requiring any correction
to the parsing or merge logic.

## Seeded Data Shape (real CSVs, verified 2026-08-21)

- **Row count:** 164, spanning `2013-01-01` through `2026-08-01`, no month gaps.
- **Per-column NULL counts:** hdan 116, ppan 116, baltic_an 3, ammonia 0, urea_black_sea 50,
  urea_china 37, natural_gas_jkm 2, natural_gas_henry_hub 2, natural_gas_uk 19,
  natural_gas_netherlands 19, corn_us 3, corn_china 3, diesel_usd_ton 87, urals 88, fx_rate 87,
  brent 87.
- **Two preserved internal holes (not leading-window NULLs, not interpolated):**
  - `baltic_an` is NULL at **2022-04-01** even though the weekly file's coverage otherwise starts
    2013-03 — a genuine no-quote week/month in the source.
  - `urals` is NULL at **2025-03-01** even though Diesel Data.csv otherwise covers that month for
    its other three columns — a blank source cell.
- **D-05c urea resolution:** `Black Sea Urea` and `China Urea` from `AN price weekly.csv` are kept
  as two separate schema columns (`urea_black_sea`, `urea_china`), never merged into a single
  `urea` column and neither dropped. Verified at 2022-08-01: `urea_black_sea` == 567.375,
  `urea_china` == 475.0.
- **Series discontinuity vs. pre-D-05b expectations (recorded, not "corrected"):** the earlier
  plan draft expected 2022-08 `urea` == 511.50 and `ammonia` == 770.00, sourced from
  `AN Data.csv`. Under D-05b those columns now come from `AN price weekly.csv` instead —
  `urea_black_sea` reads 567.375 and `ammonia` reads 925.00. These are different underlying
  benchmarks (Black Sea Urea / Middle East Ammonia vs. AN Data.csv's now-retired Urea/Ammonia
  columns), not a parsing error, and the old 511.50/770.00 figures are obsolete.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The `PriceRow` table now holds real, queryable historical data across all 16 series columns,
  satisfying ROADMAP success criterion 2 for Phase 1 ("historical price data ... loaded into
  SQLite and queryable").
- Phase 2 (Model Research) can query this table directly for backtesting; the two documented
  internal NULL holes (baltic_an 2022-04, urals 2025-03) should be handled by whatever
  gap-tolerant approach Phase 2's model research settles on — they are legitimate source gaps
  per D-03, not defects to fix here.
- Plan 01-03 (the read-only skeleton UI, D-08) can now render this seeded table.

---
*Phase: 01-app-skeleton-data-layer*
*Completed: 2026-08-21*

## Self-Check: PASSED

All created files and referenced commits verified present:
- FOUND: app/app/seed.py
- FOUND: app/tests/test_seed.py
- FOUND: .planning/phases/01-app-skeleton-data-layer/01-02-SUMMARY.md
- FOUND: 59234e1 (RED commit)
- FOUND: a0dad53 (GREEN commit)
