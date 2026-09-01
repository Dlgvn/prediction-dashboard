# Phase 19: Weekly Schema & Ingestion - Context

**Gathered:** 2026-09-01
**Status:** Ready for planning
**Source:** Direct context capture (roadmap/research already fully specify this backend-only
phase; no UI/design gray areas requiring user interview — see rationale below)

<domain>
## Phase Boundary

Backend-only data layer phase, no UI, no forecasting logic. Delivers genuinely weekly-cadence
historical data for HDAN, PPAN, and FX rate in SQLite, sourced natively (never resampled from
monthly), ready for Phase 20 (FX backtest, parallel) and Phase 21 (forecasting module,
depends on this).

**Why no interactive discussion:** No user-facing surface. `.planning/research/ARCHITECTURE.md`
and `.planning/research/PITFALLS.md` (both read directly against this codebase, not generic
advice) already specify the schema shape, the parsing approach, and the exact pitfalls to
avoid. The only decisions left are technical/implementation, which are Claude's job.
</domain>

<decisions>
## Implementation Decisions

### Schema (locked)
- New `WeeklyPriceRow` table, distinct from the existing monthly `PriceRow` table — never
  commingle weekly rows into `PriceRow` (would corrupt the existing Data Entry tab's row
  counts/history window, per PITFALLS.md Pitfall 7).
- Columns: `date`, `hdan`, `ppan`, `baltic_an`, `fx_rate`. No diesel columns — Diesel-USD/
  Diesel-MNT have no weekly source data and are out of scope for this table entirely (not
  even as NULL columns — the absence itself documents the "monthly only" constraint).
- Add via `reflex db migrate` (Alembic), matching the existing schema-change convention
  (`app/alembic/versions/`) — do not hand-edit SQLite or write raw `CREATE TABLE`.

### Data sources (locked)
- HDAN/PPAN/Baltic AN: parsed **natively** from `AN Data.csv`'s already-weekly rows (~7 days
  apart) — this is the un-resampled counterpart to the existing `load_an_monthly()`-style
  loader in `backend_research/data_loader.py`; that module's `load_an_weekly()` is a working
  precedent to mirror (not import directly — `backend_research/` is offline research code,
  `app/` needs its own seeding script, per the existing `app/app/seed.py` vs
  `backend_research/data_loader.py` separation already established in this project).
- FX rate: parsed from `FX Data.csv`'s **Weekly** column specifically — NOT the Daily or
  Monthly columns in the same file. 865 rows, 2010-01-04 to 2026-07-27, perfect 7-day
  cadence (verified). The Monthly column already powers the existing monthly FX model; the
  Daily column is unused this phase (out of scope).

### FX Data.csv parsing (locked — PITFALLS.md Pitfall 2, 3)
- The file has three independent Date/Value column pairs concatenated column-wise with blank
  spacer columns: `Date,Daily,,Date,Weekly,,Date,Monthly` — NOT row-aligned across cadences.
  A naive `pd.read_csv` + name-based column selection (e.g. `df['Date']` picks only the first
  Date column) will silently grab the wrong cadence or truncate.
- Use positional `.iloc` column slicing to isolate the Weekly pair specifically (columns
  `Date.1`/`Weekly` when pandas auto-dedupes duplicate header names — confirmed by direct
  inspection: `df.columns.tolist()` gives
  `['Date', 'Daily', 'Unnamed: 2', 'Date.1', 'Weekly', 'Unnamed: 5', 'Date.2', 'Monthly']`).
  `.dropna()` independently per cadence pair (each cadence has its own row count/range; do
  not assume they align row-for-row).
- Values use thousands-separator formatting (e.g. `"3,592.73"`) — clean with
  `.astype(str).str.replace(',', '').astype(float)`, the same idiom already used by
  `backend_research/data_loader.py`'s other loaders.
- After loading, verify shape (865 rows) and date range (2010-01-04 to 2026-07-27) as a
  parsing sanity check — this is cheap and catches a silent misparse immediately.

### AN/FX week-ending alignment (locked — PITFALLS.md Pitfall 4)
- `AN Data.csv`'s weekly rows are **Friday-based**; `FX Data.csv`'s Weekly column is
  **Monday-based** — roughly 3 days apart, confirmed by direct sample inspection. These are
  NOT the same week-ending convention.
- Join/align via a **tolerance-based `merge_asof`** (direction and tolerance TBD by the
  executor, but must not be a naive `direction='nearest'` with no tolerance bound — an
  unbounded nearest-match can silently pair rows from adjacent weeks). Mirror
  `backend_research/data_loader.py::merged_weekly()`'s existing tolerance-join pattern
  (`pd.merge_asof(..., direction='nearest', tolerance=pd.Timedelta(days=N))`) as the
  precedent, adapting the tolerance value to accommodate the ~3-day Friday/Monday gap.
- Do NOT forward-fill or interpolate to force alignment — a genuine no-match week should
  remain a gap (NaN / absent row), never manufactured (same "drop, don't fabricate"
  discipline as Phase 16's sentiment loader, per project convention).

### Non-goals
- No forecasting logic in this phase — that's Phase 21.
- No UI changes — that's Phase 22.
- No changes to the existing monthly `PriceRow` table, `app/app/seed.py`, or the monthly
  Data Entry flow — this phase is strictly additive.
- Diesel-USD/Diesel-MNT weekly data does not exist and is not attempted here (confirmed
  no source exists, per REQUIREMENTS.md's standing constraint).

### Claude's Discretion
- Exact `merge_asof` tolerance value (must be justified against the observed ~3-day
  Friday/Monday gap; err toward a tight tolerance that would rather drop a row than
  misalign one).
- Whether the new seeding script lives as `app/app/seed_weekly.py` (standalone, mirroring
  `app/app/seed.py`'s structure) or is folded into a broader module — executor's call,
  but should NOT modify `app/app/seed.py` itself (additive only).
- Exact Alembic migration mechanics (new revision file, autogenerate vs. hand-written) —
  follow whatever `app/alembic/versions/` already establishes as the project's convention.
- Idempotency approach for re-running the weekly seed (the monthly seed uses an "idempotent
  upsert" per Phase 1's history — mirror that discipline for consistency, executor's call
  on exact mechanism).

## Deferred Ideas

None raised — this is a tightly-scoped, pre-specified backend phase with no scope-creep
surface.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` (Phase 19 section) — goal, success criteria, exact requirement
- `.planning/REQUIREMENTS.md` (WKUI-01) — requirement text
- `.planning/research/ARCHITECTURE.md` — `WeeklyPriceRow` schema recommendation, component 1
- `.planning/research/PITFALLS.md` — Pitfalls 2 (CSV layout), 3 (thousands separator),
  4 (week-ending mismatch), 7 (storage commingling), all specific to this phase
- `.planning/research/SUMMARY.md` — Phase A (Schema + Ingestion) synthesis
- `backend_research/data_loader.py` (`load_an_weekly`, `load_weekly_drivers`,
  `merged_weekly`) — precedent parsing/join patterns to mirror (not import — offline
  research code, separate from `app/`)
- `app/app/seed.py` — existing monthly seeding script's structure/conventions to mirror
  for the new weekly seeding script
- `app/app/models.py` — existing `PriceRow`/`AppSetting` schema definitions, the pattern
  `WeeklyPriceRow` should follow
- `FX Data.csv` (repo root) — the new data source, verified structure documented above
</canonical_refs>
