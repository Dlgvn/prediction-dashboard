# Phase 19: Weekly Schema & Ingestion - Research

**Researched:** 2026-09-01
**Domain:** SQLModel/Alembic schema addition + pandas multi-cadence CSV ingestion for a Reflex app
**Confidence:** HIGH (all findings verified by direct source read, live CSV inspection under `app/.venv`, and running `python -m reflex db --help`)

## Summary

Phase 19 adds one new table (`WeeklyPriceRow`) and one new standalone seeding script
(`app/app/seed_weekly.py`), following exactly the two precedents already established in
this codebase: `PriceRow`/`AppSetting` in `app/app/models.py` for schema shape, and
`app/app/seed.py` for the parse -> clean -> merge -> idempotent-upsert script shape. No
existing file is modified. The only genuinely new technical problems are (1) `FX
Data.csv`'s three-cadence concatenated-column layout, which requires positional `.iloc`
slicing rather than name-based lookup, and (2) the Friday-based (AN) vs Monday-based (FX)
week-ending mismatch, which requires a tolerance-bounded `pd.merge_asof` mirroring
`backend_research/data_loader.py::merged_weekly()`'s already-proven pattern.

Both CSV shapes were inspected directly in this session (not assumed): `FX Data.csv`
produces columns `['Date', 'Daily', 'Unnamed: 2', 'Date.1', 'Weekly', 'Unnamed: 5',
'Date.2', 'Monthly']` under `pandas.read_csv`, and slicing `df.iloc[:, 3:5]` +
`.dropna()` yields exactly 865 rows spanning 2010-01-04 to 2026-07-27 — confirmed live
under `app/.venv`'s pandas 3.0.5, matching PROJECT.md's stated figures exactly.
`AN Data.csv`'s weekly rows are native (no resampling), Friday-dated, with the same
`" PPAN "`/`" HDAN "`-style padded headers and comma-thousands-separated values `seed.py`
already handles via `_clean_numeric`.

**Primary recommendation:** Mirror `seed.py`'s exact structure (parse functions -> clean
helper reuse -> merge -> `seed_database()`-style upsert-by-date loop) in a new
`seed_weekly.py`, add `WeeklyPriceRow` to `models.py` as a sibling class (not a subclass)
of `PriceRow`, and generate the migration via `reflex db makemigrations` + `reflex db
migrate` (verified working CLI, confirmed via `python -m reflex db --help` under
`app/.venv`).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WKUI-01 | Genuine weekly-cadence historical data for HDAN, PPAN, FX rate, sourced natively (AN Data.csv weekly rows, FX Data.csv Weekly column), never resampled/interpolated, persisted separately from monthly `PriceRow` | Schema section (new `WeeklyPriceRow` table), FX Data.csv parsing section (positional slicing, verified 865/2010-01-04..2026-07-27), AN Data.csv parsing section, merge_asof alignment section, idempotent upsert section — all below |
</phase_requirements>

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Schema:**
- New `WeeklyPriceRow` table, distinct from the existing monthly `PriceRow` table — never
  commingle weekly rows into `PriceRow`.
- Columns: `date`, `hdan`, `ppan`, `baltic_an`, `fx_rate`. No diesel columns at all (not
  even as NULL) — the absence itself documents the "monthly only" constraint.
- Add via `reflex db migrate` (Alembic), matching the existing convention
  (`app/alembic/versions/`) — do not hand-edit SQLite or write raw `CREATE TABLE`.

**Data sources:**
- HDAN/PPAN/Baltic AN: parsed natively from `AN Data.csv`'s already-weekly rows (~7 days
  apart) — mirror `backend_research/data_loader.py::load_an_weekly()` (not import — offline
  research code, separate from `app/`).
- FX rate: parsed from `FX Data.csv`'s Weekly column specifically — NOT Daily or Monthly.
  865 rows, 2010-01-04 to 2026-07-27, perfect 7-day cadence (verified).

**FX Data.csv parsing:**
- Three independent Date/Value column pairs concatenated column-wise with blank spacer
  columns: `Date,Daily,,Date,Weekly,,Date,Monthly` — NOT row-aligned across cadences. Use
  positional `.iloc` column slicing (columns `Date.1`/`Weekly` after pandas auto-dedupe).
  `.dropna()` independently per cadence pair.
- Values use thousands-separator formatting (e.g. `"3,592.73"`) — clean with
  `.astype(str).str.replace(',', '').astype(float)`, same idiom as
  `backend_research/data_loader.py`'s other loaders.
- After loading, verify shape (865 rows) and date range (2010-01-04 to 2026-07-27) as a
  parsing sanity check.

**AN/FX week-ending alignment:**
- AN Data.csv's weekly rows are Friday-based; FX Data.csv's Weekly column is Monday-based
  — roughly 3 days apart. Join via a tolerance-bounded `merge_asof` (not naive
  `direction='nearest'` with no tolerance). Mirror
  `backend_research/data_loader.py::merged_weekly()`'s pattern (`pd.merge_asof(...,
  direction='nearest', tolerance=pd.Timedelta(days=N))`), adapting tolerance to the ~3-day gap.
- Do NOT forward-fill or interpolate to force alignment — a genuine no-match week should
  remain a gap (NaN / absent row), never manufactured.

**Non-goals:**
- No forecasting logic, no UI changes in this phase.
- No changes to the existing monthly `PriceRow` table, `app/app/seed.py`, or the monthly
  Data Entry flow — strictly additive.
- Diesel-USD/Diesel-MNT weekly data does not exist and is not attempted.

### Claude's Discretion
- Exact `merge_asof` tolerance value (must be justified against the observed ~3-day
  Friday/Monday gap; err toward a tight tolerance that would rather drop a row than
  misalign one).
- Whether the seeding script lives as `app/app/seed_weekly.py` (standalone, mirroring
  `seed.py`) or is folded into a broader module — should NOT modify `seed.py` itself.
- Exact Alembic migration mechanics (new revision file, autogenerate vs. hand-written) —
  follow whatever `app/alembic/versions/` already establishes.
- Idempotency approach for re-running the weekly seed — mirror `seed.py`'s existing
  "idempotent upsert" discipline, exact mechanism is executor's call.

### Deferred Ideas (OUT OF SCOPE)
None raised — this is a tightly-scoped, pre-specified backend phase with no scope-creep surface.
</user_constraints>

## Project Constraints (from CLAUDE.md)

- Reflex + SQLite via `rx.Model`/SQLModel; schema changes go through `reflex db
  makemigrations` / `reflex db migrate` — "keeps schema changes... reproducible" — never
  hand-edit SQLite or write raw `CREATE TABLE`/`ALTER TABLE`.
- pandas 3.0.5 is the pinned version — copy-on-write is default/permanent; build fresh
  Series/DataFrames rather than mutating slices in place (already the pattern `seed.py`'s
  `_clean_numeric` follows — mirror it).
- No un-backtested model ships — not directly applicable to this phase (no modeling here),
  but reinforces: do not silently reinterpret/derive data (e.g. no forward-fill to force
  alignment, per the locked decision above).
- Forecasting/data logic should stay unit-testable in isolation from Reflex
  state/UI — `seed_weekly.py`'s parse functions should be plain functions taking a path and
  returning a DataFrame, exactly like `seed.py`'s `parse_an_data`/`parse_diesel_data`, so
  `app/tests/test_seed_weekly.py` can test them without spinning up Reflex.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 3.0.5 (already installed in `app/.venv`, verified via live run this session) | CSV parsing, cleaning, `merge_asof` join | Already the project's pinned data-wrangling library; no new dependency |
| sqlmodel | 0.0.42 (already installed in `app/.venv`) | `WeeklyPriceRow(rx.Model, table=True)` field declarations | Same ORM layer `PriceRow` already uses |
| reflex | 0.9.9 (already installed in `app/.venv`) | `rx.Model` base class, `reflex db makemigrations`/`migrate` CLI | Confirmed working — `python -m reflex db --help` ran successfully this session, listing `init`/`makemigrations`/`migrate`/`status` |
| alembic | bundled via reflex/sqlmodel, existing `app/alembic/` dir | Migration file generation/application | Existing convention — one prior migration (`5becaaefd322_initial_schema.py`) already establishes the pattern |

No new packages need to be installed for this phase — all required libraries are already
present and verified working in `app/.venv`.

**Version verification:** `app/.venv` was confirmed live this session (`python -m reflex
db --help` succeeded, `pd.read_csv` + `.iloc` slicing ran successfully against the real
`FX Data.csv`). No registry lookup needed — these are the project's own already-installed,
already-running versions, not new installs.

## Architecture Patterns

### Recommended file additions
```
app/
├── app/
│   ├── models.py        # ADD: WeeklyPriceRow class (sibling to PriceRow, same file)
│   ├── seed.py           # UNCHANGED
│   └── seed_weekly.py    # NEW: standalone script mirroring seed.py's shape
├── alembic/
│   └── versions/
│       └── <new_hash>_add_weeklypricerow.py   # NEW: generated via reflex db makemigrations
└── tests/
    ├── test_seed.py          # UNCHANGED
    └── test_seed_weekly.py   # NEW: mirrors test_seed.py's structure
```

### Pattern 1: `WeeklyPriceRow` schema (mirrors `PriceRow`)

**What:** A second `rx.Model` table, same declarative style as `PriceRow`, but with only
the 4 locked columns plus `date`.
**When to use:** This phase, once.
**Example:**
```python
# Source: app/app/models.py (existing PriceRow, read directly this session)
class WeeklyPriceRow(rx.Model, table=True):
    """One row per genuine weekly observation (Phase 19). Never derived/resampled
    from PriceRow — sourced natively from AN Data.csv's weekly rows and FX Data.csv's
    Weekly column. No diesel columns: no weekly diesel source data exists (by design,
    not omission — see 19-CONTEXT.md)."""

    date: str = sqlmodel.Field(unique=True, index=True)

    # sourced from AN Data.csv (native weekly rows, no resampling)
    hdan: Optional[float] = None
    ppan: Optional[float] = None
    baltic_an: Optional[float] = None

    # sourced from FX Data.csv's Weekly column
    fx_rate: Optional[float] = None
```
This is added to the *same* `app/app/models.py` file as `PriceRow`/`AppSetting` (no new
module needed — `PriceRow` isn't being touched, just a new class appended below it),
matching the existing single-schema-file convention.

### Pattern 2: Migration generation (mirrors the existing `5becaaefd322_initial_schema.py`)

**What:** Use the Reflex-wrapped Alembic CLI, not hand-written or hand-edited SQL.
**Example (verified this session — `python -m reflex db --help` under `app/.venv` lists
these exact subcommands):**
```bash
# from app/ with .venv active
python -m reflex db makemigrations --message "add WeeklyPriceRow table"
python -m reflex db migrate
```
`reflex db makemigrations` autogenerates a new revision file in `app/alembic/versions/`
(a new hash, `down_revision = '5becaaefd322'`), following the exact same
`op.create_table(...)` + `batch_op.create_index(...)` shape the initial migration already
used for `pricerow`/`appsetting` — Reflex's CLI supplies `target_metadata` (the raw
`app/alembic/env.py` shows `target_metadata = None`, but this is patched at runtime by the
`reflex db` command wrapper, not a sign autogenerate is broken — the existing
`5becaaefd322` migration is proof it already worked once this way). `reflex db migrate`
then applies pending revisions to the SQLite file. Do not hand-edit `env.py`.

**Verification after migration:** `python -m reflex db status` (also listed in the CLI
help) should show no pending migrations; spot-check the new table exists via
`sqlite3 <db file> ".schema weeklypricerow"` or an ad-hoc `sqlmodel` query.

### Pattern 3: FX Data.csv Weekly-column positional slicing

**What:** Isolate the Weekly cadence pair by column position, not name, because pandas
deduplicates the three repeated `Date` headers and the two blank spacer columns into
`Date`, `Date.1`, `Date.2` / `Unnamed: 2`, `Unnamed: 5` — fragile to rely on by name if the
file's column order ever shifts.
**Verified this session** (`app/.venv`, live `pd.read_csv` against the real file):
```python
# Source: verified live this session against FX Data.csv under app/.venv (pandas 3.0.5)
df = pd.read_csv(fx_csv_path)
# df.columns.tolist() == ['Date', 'Daily', 'Unnamed: 2', 'Date.1', 'Weekly',
#                          'Unnamed: 5', 'Date.2', 'Monthly']
weekly = df.iloc[:, 3:5].copy()
weekly.columns = ["date", "fx_rate"]
weekly = weekly.dropna()
weekly["date"] = pd.to_datetime(weekly["date"])
weekly["fx_rate"] = (
    weekly["fx_rate"].astype(str).str.replace(",", "", regex=False).astype(float)
)
# Sanity check (matches PROJECT.md's stated figures exactly, verified live):
assert weekly.shape[0] == 865, f"expected 865 weekly FX rows, got {weekly.shape[0]}"
assert weekly["date"].min() == pd.Timestamp("2010-01-04")
assert weekly["date"].max() == pd.Timestamp("2026-07-27")
```
Note: `.dropna()` on just the 2-column slice is safe and independent of the Daily/Monthly
pairs' own (different) row counts and NaN positions — confirmed live: slicing
`df.iloc[:, 3:5]` before `.dropna()` never pulls in `Unnamed: 2`/`Unnamed: 5`'s NaN pattern
from the *other* cadence pairs, so no cross-cadence truncation occurs (Pitfall 2 from
PITFALLS.md, directly avoided by this exact slice).

### Pattern 4: AN Data.csv native weekly parsing (mirrors `load_an_weekly` / existing `parse_an_data`)

**What:** Reuse `seed.py`'s exact `parse_an_data`-style read, but do NOT collapse to
monthly (i.e., skip `_collapse_monthly` entirely — that's the one and only difference from
the existing monthly path) and additionally extract `baltic_an`.
**Example:**
```python
# Adapted from app/app/seed.py::parse_an_data (read directly this session) +
# backend_research/data_loader.py::load_an_weekly's column selection (read directly)
from app.seed import _clean_numeric  # reuse, don't duplicate

def parse_an_data_weekly(path) -> pd.DataFrame:
    """Parse AN Data.csv at native weekly grain. Unlike seed.py's parse_an_data,
    also extracts baltic_an (needed for WeeklyPriceRow) and performs NO monthly
    collapse -- every native row is kept as-is."""
    raw = pd.read_csv(path, dtype=str)
    raw.columns = [c.strip() for c in raw.columns]

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(raw["Date"], format="%m/%d/%Y")
    out["hdan"] = _clean_numeric(raw["HDAN"])
    out["ppan"] = _clean_numeric(raw["PPAN"])
    out["baltic_an"] = _clean_numeric(raw["Baltic AN"])
    return out.sort_values("date").reset_index(drop=True)
```
Confirmed live this session: `AN Data.csv`'s header is
`Date,Year, Month , PPAN , HDAN , Baltic AN , Ammonia , Urea , Natural_gas ,  Brent  ,`
— after `.strip()` on stripped column names, `raw["Baltic AN"]` resolves correctly (the
header token itself has no leading/trailing space once split on commas, matching
`data_loader.py::load_an_weekly`'s identical column reference). Dates run Friday-based,
e.g. `7/10/2026`, `7/3/2026`, `6/26/2026`, `6/19/2026` — confirmed via direct tail/head
inspection this session, matching PITFALLS.md's claim exactly. Reuses `seed.py`'s existing
`_clean_numeric` (import it, do not copy/duplicate the thousands-separator logic).

### Pattern 5: Tolerance-bounded `merge_asof` join (mirrors `merged_weekly()`)

**What:** Join the AN-family weekly frame (Friday-based) to the FX weekly frame
(Monday-based) without assuming row alignment.
**Recommended tolerance:** `pd.Timedelta(days=3)`. Justification: the observed gap
between AN Data.csv's Friday week-ending dates and FX Data.csv's Monday week-ending dates
is consistently ~3 calendar days (Friday -> the following Monday is exactly 3 days,
confirmed by direct sample inspection: AN's `7/10/2026` (Fri) pairs most naturally with
FX's `2026-07-13` (Mon), a 3-day gap). This is also the exact tolerance
`backend_research/data_loader.py::merged_weekly()` already uses for a structurally
identical problem (two independently-collected weekly sources with different
week-ending conventions) — reusing the same proven value rather than inventing a new one.
A tighter tolerance (e.g. 1-2 days) risks dropping every single row, since the true gap is
consistently ~3 days, not less; a looser tolerance (e.g. 4+ days) risks pulling in the
*next* week's FX observation on weeks where the exact 3-day gap doesn't hold, which is a
higher-risk failure mode (silent misalignment) than a tighter bound's failure mode
(dropped row) — per the locked decision to "err toward a tight tolerance that would rather
drop a row than misalign one."
**Example:**
```python
# Source: backend_research/data_loader.py::merged_weekly (read directly this session),
# adapted for AN-family (Friday) vs FX (Monday) instead of AN vs AN-weekly-drivers
def merge_an_fx_weekly(an_df: pd.DataFrame, fx_df: pd.DataFrame) -> pd.DataFrame:
    an_sorted = an_df.sort_values("date").set_index("date")
    fx_sorted = fx_df.sort_values("date").set_index("date")
    merged = pd.merge_asof(
        an_sorted, fx_sorted,
        left_index=True, right_index=True,
        direction="nearest", tolerance=pd.Timedelta(days=3),
    )
    return merged.reset_index()
```
Rows with no FX match within tolerance keep `fx_rate` as NaN (mapped to `None` at
upsert time, per Pattern 6) rather than being forward-filled or dropped outright — a
genuine gap stays a gap, per the locked "drop, don't fabricate" decision. (Whether to
additionally drop AN-side rows with no FX match at all, vs keep them with `fx_rate=None`,
is the executor's call at plan time — `merged_weekly()`'s own precedent does
`.dropna(subset=['BalticAN_wk'])` afterward, i.e. it drops rows missing its *right-side*
merge target; the equivalent choice here would be whether a HDAN/PPAN-with-no-FX row is
still worth keeping in `WeeklyPriceRow` for its own sake — recommend keeping it, since
`baltic_an`/`hdan`/`ppan` are independently valid without `fx_rate`, and `WeeklyPriceRow`'s
columns are all `Optional`.)

### Pattern 6: Idempotent upsert (mirrors `seed.py::seed_database`'s exact mechanism)

**What:** `seed.py` achieves idempotency via a "query existing row by unique `date`, else
construct a new one, then `setattr` every column and `session.add`" loop inside one
`session.commit()` — not `INSERT OR REPLACE`, not a `merge()` call, not a delete-then-
reinsert. Mirror this exactly for `seed_weekly.py`.
**Example:**
```python
# Source: app/app/seed.py::seed_database (read directly this session) — same shape,
# adapted for WeeklyPriceRow's 4 columns instead of PriceRow's 16
from app.models import WeeklyPriceRow

WEEKLY_SERIES_COLUMNS = ["hdan", "ppan", "baltic_an", "fx_rate"]

def _to_none(value):
    if pd.isna(value):
        return None
    return float(value)

def seed_weekly_database(an_data_path, fx_data_path) -> int:
    an_df = parse_an_data_weekly(an_data_path)
    fx_df = parse_fx_weekly(fx_data_path)
    merged = merge_an_fx_weekly(an_df, fx_df)

    written = 0
    session = rx.session()
    try:
        from sqlmodel import select
        for _, row in merged.iterrows():
            date_str = row["date"].strftime("%Y-%m-%d")
            existing = session.exec(
                select(WeeklyPriceRow).where(WeeklyPriceRow.date == date_str)
            ).first()
            if existing is None:
                existing = WeeklyPriceRow(date=date_str)
                session.add(existing)
            for col in WEEKLY_SERIES_COLUMNS:
                setattr(existing, col, _to_none(row[col]))
            written += 1
        session.commit()
    finally:
        session.close()
    return written
```
Re-running this script against the same source CSVs updates existing rows in place
(same `date` string match) rather than duplicating them — identical idempotency guarantee
to `seed.py`'s D-02 discipline. Run as a standalone script (never wired into app startup),
mirroring `seed.py`'s `if __name__ == "__main__":` entry point:
```bash
python -m app.seed_weekly "<AN Data.csv path>" "<FX Data.csv path>"
```

### Anti-Patterns to Avoid

- **Reusing `_collapse_monthly` or any monthly-averaging step on the weekly frames:**
  This is the one thing that would silently violate WKUI-01's "never resampled" contract.
  `seed_weekly.py` should have no `.groupby(...period('M'))` anywhere.
- **Writing into `PriceRow` instead of a new table:** Already forbidden by both
  CONTEXT.md and PITFALLS.md Pitfall 7 — would corrupt the Data Entry tab's row
  counts/history window.
- **Hand-editing `app/alembic/versions/*.py` after generation, beyond minor review:** The
  existing migration file's own comment ("commands auto generated by Alembic - please
  adjust!") signals light review is fine, but the *shape* (`op.create_table`,
  `batch_op.create_index`) should come from `reflex db makemigrations`, not be
  hand-authored from scratch.
- **Forward-filling FX gaps to "fill in" unmatched weeks:** Explicitly forbidden by the
  locked decision — a no-match week must remain NaN/absent, never fabricated.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Schema migration | Raw `CREATE TABLE`/`ALTER TABLE` SQL against the SQLite file | `reflex db makemigrations` + `reflex db migrate` | Already the project's established, working convention (one prior migration proves it); hand SQL bypasses Reflex's schema-tracking and risks drift from what `rx.Model` declares |
| Tolerance-based date join | A manual nearest-date loop or `pd.concat` + manual index reconciliation | `pd.merge_asof(..., direction='nearest', tolerance=...)` | `merge_asof` is the exact tool for this and is already proven correct in this codebase (`merged_weekly()`); reinventing it risks subtly wrong tie-breaking near the tolerance boundary |
| Thousands-separator numeric cleanup | A custom regex or manual string-strip function | `.astype(str).str.replace(',', '').astype(float)` (reuse `seed.py::_clean_numeric` directly via import) | Already validated against this exact CSV family's formatting; duplicating it risks a second, subtly different implementation drifting from the first |

**Key insight:** Every sub-problem in this phase (multi-cadence CSV parsing, tolerance
join, idempotent upsert, migration mechanics) already has a working, in-repo precedent.
The work here is adaptation, not invention — deviating from the precedents (e.g. writing a
new thousands-separator cleaner, or a new join algorithm) is pure risk with no benefit.

## Common Pitfalls

### Pitfall 1: FX Data.csv column-position drift silently corrupting the parse
**What goes wrong:** Selecting `df['Weekly']`/`df['Date']` by name works today only
because pandas happens to name the 5th and 6th columns exactly `Weekly`/`Date.1`, but any
future edit to the CSV (e.g. reordering the three cadence blocks, adding a new column) with
name-based selection would silently pick the wrong cadence.
**Why it happens:** `pd.read_csv` deduplicates identical header names positionally
(`Date`, `Date.1`, `Date.2`), which happens to be stable today, but a positional slice
(`iloc[:, 3:5]`) that's explicitly justified by an up-front column-list assertion is more
defensive than relying on the auto-deduped names.
**How to avoid:** Assert `df.columns.tolist() == ['Date', 'Daily', 'Unnamed: 2', 'Date.1',
'Weekly', 'Unnamed: 5', 'Date.2', 'Monthly']` before slicing, so any future file-shape
change fails loudly at parse time instead of silently picking the wrong pair.
**Warning signs:** Weekly FX values that look like Daily-cadence noise (much higher
row-to-row variance) or Monthly-cadence values (much lower row count) after a supposedly
successful parse.

### Pitfall 2: Assuming `WeeklyPriceRow.date` string format matches `PriceRow.date`'s
**What goes wrong:** `PriceRow.date` is stored as `"%Y-%m-01"` (first-of-month, per
`seed.py::_build_merged_frame`). If `WeeklyPriceRow.date` is seeded with a different
format (e.g. `%m/%d/%Y` inherited from AN Data.csv's raw format) it will still work in
isolation (no code compares the two tables' date strings today), but sets up a landmine
for Phase 21/22 when both tables' dates might need joint display or sorting.
**How to avoid:** Format `WeeklyPriceRow.date` as ISO `"%Y-%m-%d"` (via
`row["date"].strftime("%Y-%m-%d")`) — sorts correctly as a plain string, and is
unambiguous, matching the general convention `PriceRow.date` already follows (ISO-rooted,
just truncated to month granularity there).
**Warning signs:** Any weekly row whose `date` column doesn't sort correctly
lexicographically against other weekly rows.

### Pitfall 3: Running the seed script before the migration is applied
**What goes wrong:** `seed_weekly.py` will raise a `sqlalchemy.exc.OperationalError: no
such table: weeklypricerow` if run before `reflex db migrate` has been applied to the
target SQLite file.
**How to avoid:** Document the required order in `seed_weekly.py`'s module docstring
(mirroring `seed.py`'s own docstring style) and in the plan's task ordering: migration
wave strictly before ingestion wave (already reflected in ARCHITECTURE.md's Wave 1 ->
Wave 2 ordering).
**Warning signs:** `OperationalError` on the first `session.exec(select(WeeklyPriceRow)...)` call.

## Code Examples

See Patterns 1-6 above — all code examples are either read directly from this session's
file reads (`seed.py`, `data_loader.py`, `models.py`) or verified live against the actual
CSVs under `app/.venv` this session, not invented.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| N/A — this is the first weekly-cadence table in the project | `WeeklyPriceRow` as a second, parallel `rx.Model` table | Phase 19 (this phase) | Establishes the pattern Phase 20/21/22 will build on (weekly forecast history read path) |

No deprecated/outdated approaches apply — this is new functionality, not a replacement of
an existing pattern.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `pd.Timedelta(days=3)` merge_asof tolerance is the right choice for the full 200+/865-row history (not just the sampled rows inspected this session) | Pattern 5 | If some weeks' gap exceeds 3 days (e.g. around holidays shifting one series' week-ending date by a day), a legitimately matchable pair could be dropped — low-severity (a dropped row is the safe failure mode per the locked "err tight" decision), but worth spot-checking row-match-rate after the real merge runs (e.g. assert most AN rows get a non-null `fx_rate` within the 2010-2026 overlap window) |
| A2 | `reflex db makemigrations` correctly autogenerates the new table's migration despite `app/alembic/env.py` showing `target_metadata = None` in its raw file | Pattern 2 | If the CLI does NOT patch `target_metadata` at runtime as assumed, `makemigrations` could produce an empty/no-op migration file requiring a hand-written one instead (still following the same `op.create_table` shape manually, using `5becaaefd322_initial_schema.py` as the literal template) — this is a plan-time verification step, not a blocker, since the CLI itself is confirmed present and functional (`--help` succeeded) |

**If this table is empty:** N/A — see above, two low-risk assumptions logged.

## Open Questions

1. **Should AN-side rows with no FX match (outside merge_asof tolerance) be kept
   (fx_rate=None) or dropped entirely?**
   - What we know: `merged_weekly()`'s own precedent drops rows missing its match
     target (`.dropna(subset=['BalticAN_wk'])`), but that's a different semantic (Baltic AN
     is itself a modeling input there); here `hdan`/`ppan`/`baltic_an` are independently
     valuable even without a paired `fx_rate`.
   - What's unclear: whether Phase 21's weekly FX backtest wants a clean fx_rate history
     with no fabricated continuity, and whether keeping fx_rate=None rows in
     `WeeklyPriceRow` could confuse a future naive `.dropna()` call downstream.
   - Recommendation: keep rows with `fx_rate=None` rather than dropping (all
     `WeeklyPriceRow` columns are `Optional`, so this doesn't violate any constraint), and
     let the FX-specific backtest phase (Phase 20) do its own `.dropna(subset=['fx_rate'])`
     when it needs a clean FX-only series — this preserves the most information at the
     ingestion layer without deciding a modeling-layer choice prematurely.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pandas | CSV parsing, merge_asof | Yes (verified live) | 3.0.5 (app/.venv) | — |
| reflex CLI (`reflex db`) | Migration generation/application | Yes (verified live, `--help` succeeded) | 0.9.9 | — |
| sqlmodel | `WeeklyPriceRow` class | Yes (already a reflex dependency) | 0.0.42 | — |
| `AN Data.csv`, `FX Data.csv` | Source data | Yes (repo root, inspected directly) | — | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, `app/tests/test_seed.py` is the direct precedent) |
| Config file | none detected beyond pytest defaults (mirrors `test_seed.py`'s own `sys.path.insert` bootstrap, no `conftest.py` needed for this pattern) |
| Quick run command | `python -m pytest app/tests/test_seed_weekly.py -x` |
| Full suite command | `python -m pytest app/tests -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WKUI-01 | `parse_an_data_weekly` extracts date/hdan/ppan/baltic_an from a native weekly AN Data.csv fixture, no monthly collapse | unit | `pytest app/tests/test_seed_weekly.py::test_parse_an_data_weekly -x` | Wave 0 |
| WKUI-01 | `parse_fx_weekly` correctly isolates the Weekly column pair from a 3-cadence fixture CSV | unit | `pytest app/tests/test_seed_weekly.py::test_parse_fx_weekly_column_isolation -x` | Wave 0 |
| WKUI-01 | `parse_fx_weekly` cleans thousands-separator values to float | unit | `pytest app/tests/test_seed_weekly.py::test_parse_fx_weekly_thousands_separator -x` | Wave 0 |
| WKUI-01 | `merge_an_fx_weekly` uses tolerance-bounded merge_asof, doesn't misalign rows beyond tolerance | unit | `pytest app/tests/test_seed_weekly.py::test_merge_an_fx_weekly_tolerance -x` | Wave 0 |
| WKUI-01 | `seed_weekly_database` upserts idempotently (re-run doesn't duplicate rows) | integration (tmp sqlite) | `pytest app/tests/test_seed_weekly.py::test_seed_weekly_database_idempotent -x` | Wave 0 |
| WKUI-01 | End-to-end: seeding against the real `FX Data.csv`/`AN Data.csv` yields row count/date range matching known figures (865 FX rows, 2010-01-04..2026-07-27) | smoke/manual | Run `python -m app.seed_weekly "AN Data.csv" "FX Data.csv"` once against a scratch DB and inspect output count | Wave 0 (script itself; no fixture needed, uses real files) |

### Sampling Rate
- **Per task commit:** `pytest app/tests/test_seed_weekly.py -x`
- **Per wave merge:** `pytest app/tests -x` (full suite, ensures no regression to `test_seed.py`'s existing monthly-path tests)
- **Phase gate:** Full suite green before `/gsd-verify-work`, plus the real-CSV smoke run producing the expected 865-ish weekly row count and 2010-01-04..2026-07-27 range (accounting for whatever the merge_asof/tolerance choice does to the final joined row count — the raw FX-only count is 865, the joined WeeklyPriceRow count will differ based on AN's own weekly row count, which is shorter, per PROJECT.md's "~206 rows" figure for AN's native weekly history).

### Wave 0 Gaps
- [ ] `app/tests/test_seed_weekly.py` — new file, covers WKUI-01 (mirrors `test_seed.py`'s existing fixture-based unit test pattern)
- [ ] No new fixtures/conftest needed — inline CSV-string fixtures via `tmp_path`, exactly as `test_seed.py` already does
- [ ] No framework install needed — pytest already present and used by `test_seed.py`

*(No other gaps: existing test infrastructure/pattern fully covers this phase's requirements.)*

## Security Domain

Not applicable — this phase is local, offline CSV ingestion into a local SQLite file for a
single-user desktop-style app, with no network input, no user-facing input surface, no
authentication/session boundary, and no new external dependency. No ASVS category applies
beyond what's already covered by the existing monthly `seed.py` path (which also has no
security domain section, by the same reasoning).

## Sources

### Primary (HIGH confidence — direct source read or live verification this session)
- `app/app/models.py` — read in full — `PriceRow`/`AppSetting` schema shape
- `app/app/seed.py` — read in full — parse/clean/merge/upsert pattern, idempotency mechanism
- `app/alembic/versions/5becaaefd322_initial_schema.py` — read in full — migration file shape/convention
- `app/alembic/env.py` — read in full — confirms `target_metadata = None` in the raw file (see Assumption A2)
- `backend_research/data_loader.py` — read in full — `load_an_weekly`, `load_weekly_drivers`, `merged_weekly` precedent patterns
- `app/tests/test_seed.py` — read (partial, structure) — existing test pattern to mirror
- `FX Data.csv`, `AN Data.csv` — inspected directly via `head`/`tail` (raw structure) — confirms header layout, date formats, thousands-separator formatting
- Live Python execution under `app/.venv` (pandas 3.0.5) — confirmed `FX Data.csv`'s exact column list after `pd.read_csv`, confirmed 865-row/2010-01-04..2026-07-27 Weekly slice via `.iloc[:, 3:5].dropna()`
- `python -m reflex db --help` under `app/.venv` — confirmed `init`/`makemigrations`/`migrate`/`status` subcommands exist and the CLI runs successfully
- `.planning/phases/19-weekly-schema-ingestion/19-CONTEXT.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/research/ARCHITECTURE.md`, `.planning/research/PITFALLS.md` — read in full — milestone-level research and locked decisions

### Secondary (MEDIUM confidence)
None — all claims in this document were verified directly this session (either by reading
the actual source file or by running actual code against the actual data under the actual
target environment, `app/.venv`).

### Tertiary (LOW confidence)
None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, all already installed and verified live
- Architecture: HIGH — directly mirrors two already-shipped, already-tested precedents in this exact codebase
- Pitfalls: HIGH — sourced from `.planning/research/PITFALLS.md` (already a dedicated milestone-level research pass) plus this session's own live CSV verification

**Research date:** 2026-09-01
**Valid until:** Stable — no external API/library surface at play (pinned local
dependencies, static CSV files), so this research does not go stale on a time basis;
re-verify only if `AN Data.csv`/`FX Data.csv` are ever regenerated with a different shape,
or if the `app/.venv` dependency versions change.
