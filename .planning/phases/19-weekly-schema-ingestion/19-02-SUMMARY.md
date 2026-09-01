---
phase: 19-weekly-schema-ingestion
plan: 02
subsystem: database
tags: [pandas, sqlmodel, ingestion, merge_asof]

# Dependency graph
requires: ["19-01"]
provides:
  - "app/app/seed_weekly.py: parse_an_data_weekly, parse_fx_weekly, merge_an_fx_weekly, seed_weekly_database"
  - "206 rows populated in app/reflex.db's weeklypricerow table, 2022-08-05..2026-07-10, 100% non-null fx_rate"
affects: [21-weekly-forecasting-module]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Weekly-cadence ingestion scripts isolate a specific CSV column pair by verified position (not name) and fail loudly (ValueError) on layout drift, per T-19-03"
    - "Cross-cadence joins (Friday-based AN vs Monday-based FX) use pd.merge_asof with an explicit pd.Timedelta tolerance, never a naive/unbounded nearest match"

key-files:
  created:
    - app/app/seed_weekly.py
    - app/tests/test_seed_weekly.py
  modified: []

key-decisions:
  - "Added a _get_session() indirection (mirroring seed.py's pattern) rather than calling rx.session() inline, so tests can monkeypatch the session the same way test_seed.py already does -- keeps the idempotency test isolated from any real DB file"

patterns-established:
  - "Weekly ingestion scripts stay standalone (python -m app.seed_weekly <AN path> <FX path>), never wired into app startup, consistent with seed.py"

requirements-completed: [WKUI-01]

# Metrics
duration: 20min
completed: 2026-09-01
---

# Phase 19 Plan 02: Weekly Ingestion Summary

**Built `app/app/seed_weekly.py`, joining AN Data.csv's native weekly HDAN/PPAN/Baltic AN rows with FX Data.csv's Weekly-column FX rate via a 3-day-tolerance `merge_asof`, and seeded 206 rows into `weeklypricerow` (2022-08-05 to 2026-07-10) with 100% non-null `fx_rate`.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-09-01T06:00:00Z
- **Completed:** 2026-09-01T06:20:00Z
- **Tasks:** 2 completed
- **Files modified:** 2 (both created)

## Accomplishments
- `parse_an_data_weekly`: parses `AN Data.csv`'s native weekly rows (date, hdan, ppan, baltic_an) with no monthly collapse anywhere in the code path — row count in equals row count out
- `parse_fx_weekly`: isolates `FX Data.csv`'s Weekly Date/Value pair via verified positional slicing (`df.iloc[:, 3:5]`), guarded by a `FX_EXPECTED_COLUMNS` assertion that raises `ValueError` on layout drift (T-19-03 mitigation)
- `merge_an_fx_weekly`: joins AN (Friday-based) and FX (Monday-based) frames via `pd.merge_asof(..., tolerance=pd.Timedelta(days=3))` — matched pairs get `fx_rate`, out-of-tolerance pairs correctly stay NaN rather than being misaligned
- `seed_weekly_database`: idempotent upsert into `WeeklyPriceRow`, mirroring `seed.py::seed_database`'s exact query-then-setattr-then-commit mechanism (not `INSERT OR REPLACE`/`session.merge()`)
- 6 unit tests covering parsing, column isolation (Daily/Monthly values proven not to leak into Weekly output), thousands-separator cleaning, unexpected-layout rejection, tolerance-join matched/unmatched cases, and idempotent re-run with an in-place value update
- Full test suite (368 tests, including all pre-existing `test_seed.py` monthly-path tests) passes with no regressions
- Real end-to-end smoke run against the actual `AN Data.csv`/`FX Data.csv` at repo root, seeding `app/reflex.db`'s `weeklypricerow` table: **206 rows, date range 2022-08-05 to 2026-07-10, 206/206 (100%) rows have a non-null `fx_rate`** — confirms the tolerance/Friday-Monday assumption holds for the full real dataset, not just fixtures
- Re-ran the smoke script a second time against the same CSVs: row count stayed at 206 (idempotent, no duplication)
- Verified `app/app/seed.py` and `app/app/models.py` are byte-for-byte unchanged (`git diff --stat` empty); `pricerow` table's row count (164) unaffected

## Task Commits

Both tasks were implemented together in `app/app/seed_weekly.py` (the parsing/join functions from Task 1 and the upsert/entry-point from Task 2 form one cohesive module) and committed as a single atomic commit, with both tasks' test coverage included in the same commit:

1. **Tasks 1 & 2: parsing/join functions + idempotent upsert + entry point** - `1b1a2ec` (feat)

**Plan metadata:** (this commit, following)

## Files Created/Modified
- `app/app/seed_weekly.py` - New standalone ingestion script: `parse_an_data_weekly`, `parse_fx_weekly`, `merge_an_fx_weekly`, `seed_weekly_database`, `__main__` entry point. Imports `_clean_numeric` from `app/app/seed.py` (reused, not duplicated).
- `app/tests/test_seed_weekly.py` - 6 unit tests covering all four functions in isolation, using the shared `session` fixture from `conftest.py` for the idempotency test.

## Decisions Made
- **Combined Task 1 and Task 2 into a single file write and a single commit** rather than two separate commits. The plan's own code blocks for both tasks compose one coherent module (parsing functions feed directly into the upsert function defined right after), and splitting the commit would have meant committing a temporarily-incomplete/untested file. Both tasks' RED-then-GREEN TDD cycles were still followed within the single implementation pass — all tests were written and run against the target behavior before considering either task done.
- **Added `_get_session()` indirection** (not explicitly specified in the plan's code block, which called `rx.session()` inline) to mirror `seed.py`'s exact testability pattern, enabling `monkeypatch.setattr(seed_weekly_mod, "_get_session", lambda: session)` in the idempotency test — consistent with how `test_seed.py` isolates the DB session.

## Deviations from Plan

None - plan executed as written, with the one non-functional decision above (session indirection helper, matching an existing project pattern already used by `seed.py`/`test_seed.py`).

## Real-CSV Smoke Run Results

```
weeklypricerow: COUNT=206, MIN(date)=2022-08-05, MAX(date)=2026-07-10
fx_rate non-null: 206 / 206 (100%)
pricerow (unaffected): COUNT=164
```

This is the AN Data.csv-native weekly row count (not the FX-only 865 figure) — AN Data.csv's own weekly history is the shorter, limiting series here, consistent with 19-RESEARCH.md's expectation. 100% fx_rate match rate confirms the Friday/Monday 3-day tolerance assumption (RESEARCH.md Assumption A1) holds across the entire real dataset, not just a sample.

## Issues Encountered
- `reflex.Model has been deprecated` warning prints on every script run (pre-existing Reflex 0.9.9 deprecation notice, unrelated to this plan's code, matches the same warning `seed.py` already triggers) — informational only, does not affect execution or output.

## User Setup Required

None - no external service configuration required. The script is run standalone via `python -m app.seed_weekly <AN Data.csv path> <FX Data.csv path>` and has already been run once against the real CSVs as part of this plan's execution.

## Next Phase Readiness
- `weeklypricerow` is now populated with 206 real weekly rows (2022-08-05 to 2026-07-10), ready for Phase 21's weekly forecasting module to consume.
- Phase 19 (Weekly Schema Ingestion) is now complete: Plan 01 delivered the schema, Plan 02 delivered the ingestion. `WKUI-01` requirement fully satisfied — weekly-cadence data is natively sourced (never resampled), persisted separately from `PriceRow`, and its row count/date range are verified against the source CSVs.

---
*Phase: 19-weekly-schema-ingestion*
*Completed: 2026-09-01*

## Self-Check: PASSED
- FOUND: app/app/seed_weekly.py
- FOUND: app/tests/test_seed_weekly.py
- FOUND: commit 1b1a2ec
